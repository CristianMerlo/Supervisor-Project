import os
import sqlite3
import sys
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv

import logging

logging.basicConfig(filename='userbot.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

# Cargar variables de entorno
load_dotenv()

api_id_env = os.getenv("TELEGRAM_API_ID")
api_hash_env = os.getenv("TELEGRAM_API_HASH")
phone_env = os.getenv("TELEGRAM_PHONE")

if not api_id_env or not api_hash_env or not phone_env:
    print("❌ ERROR: TELEGRAM_API_ID, TELEGRAM_API_HASH o TELEGRAM_PHONE no configurados en .env")
    print("Por favor, edita tu archivo .env y completa estos campos antes de iniciar el userbot.")
    sys.exit(1)

try:
    API_ID = int(api_id_env)
except ValueError:
    print(f"❌ ERROR: TELEGRAM_API_ID debe ser un número entero válido. Valor actual: '{api_id_env}'")
    sys.exit(1)

API_HASH = api_hash_env
PHONE = phone_env
MI_TELEGRAM_ID = 215173956  # ID de Telegram de Cristian

# Inicializar cliente de Telethon (Userbot)
client = TelegramClient('supervisor', API_ID, API_HASH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
from pathlib import Path
DIR_AUDIOS = Path("temp_audios")
DIR_AUDIOS.mkdir(exist_ok=True)

def transcribir_audio_groq(audio_path):
    if not GROQ_API_KEY:
        return "[Error: Falta GROQ_API_KEY]"
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        with open(audio_path, "rb") as audio_file:
            files = {
                "file": (os.path.basename(audio_path), audio_file, "audio/ogg"),
                "model": (None, "whisper-large-v3"),
                "language": (None, "es")
            }
            response = requests.post(url, headers=headers, files=files)
            if response.status_code == 200:
                return response.json().get("text", "")
    except Exception as e:
        logging.info(f"[ERROR AUDIO] Falla: {e}")
    return "[Error en la API de transcripción]"

import datetime

BOT_USER_ID = None

def obtener_lista_locales():
    try:
        conn = sqlite3.connect("supervisor_local.db")
        cursor = conn.cursor()
        cursor.execute("SELECT sigla, nombre FROM locales")
        filas = cursor.fetchall()
        conn.close()
        locales = []
        for sigla, nombre in filas:
            if sigla:
                locales.append(sigla.lower())
            if nombre:
                locales.append(nombre.lower())
        return locales
    except Exception as e:
        logging.info(f"[ERROR DB locales] No se pudo cargar: {e}")
        return []

def guardar_mensaje_aprendizaje(remitente_id, remitente_nombre, mensaje, es_grupo):
    log_path = "grupo_aprendizaje.log"
    fecha_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tipo_chat = "Grupo" if es_grupo else "Privado"
    log_line = f"[{fecha_str}] [{tipo_chat}] ID: {remitente_id} ({remitente_nombre}) -> {mensaje}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        logging.info(f"[ERROR APRENDIZAJE LOG] {e}")

from aiohttp import web

async def notify_handler(request):
    try:
        message = ""
        if request.has_body:
            try:
                data = await request.post()
                message = data.get("message", "").strip()
            except Exception:
                pass
            if not message:
                message = (await request.text()).strip()
        
        if message:
            logging.info(f"[UPS ALERTA LOCAL] Enviando: {message}")
            await client.send_message(MI_TELEGRAM_ID, f"🔌 [Supervisor UPS] {message}")
            return web.Response(text="Enviado con éxito\n")
        else:
            return web.Response(text="Mensaje vacío\n", status=400)
    except Exception as e:
        logging.info(f"[ERROR NOTIFICACIÓN LOCAL] {e}")
        return web.Response(text=f"Error: {e}\n", status=500)

async def start_notification_server():
    app = web.Application()
    app.router.add_post('/notify', notify_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8088)
    await site.start()
    logging.info("--- [SERVER LOCAL] Notificador local escuchando en 127.0.0.1:8088/notify ---")

def buscar_direccion_local(termino):
    conn = sqlite3.connect("supervisor_local.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, direccion FROM locales WHERE sigla = ? OR nombre LIKE ?", (termino.upper(), f"%{termino}%"))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def buscar_pendientes_local(termino):
    conn = sqlite3.connect("supervisor_local.db")
    cursor = conn.cursor()
    # Buscar pendientes por sigla o nombre del local
    cursor.execute("""
        SELECT p.detalle, p.fecha 
        FROM pendientes p 
        JOIN locales l ON p.sigla = l.sigla 
        WHERE l.sigla = ? OR l.nombre LIKE ?
    """, (termino.upper(), f"%{termino}%"))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def consultar_api_local(mensaje_usuario, chat_id):
    """Consulta la API local de Supervisor para obtener respuestas asistidas por IA de Gemini"""
    try:
        url = "http://127.0.0.1:8000/v1/chat/completions"
        payload = {
            "model": "gemini-2.0-flash",
            "messages": [
                {"role": "user", "content": mensaje_usuario}
            ],
            "user": str(chat_id)
        }
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logging.info(f"⚠️ Error de conexión con API local: {e}")
    return None

def filtrar_palabras(mensaje):
    """Limpia y filtra palabras muy cortas o vacías para evitar falsos positivos en las búsquedas"""
    palabras = mensaje.split()
    palabras_filtradas = []
    stop_words = {'de', 'del', 'la', 'las', 'el', 'los', 'con', 'para', 'una', 'uno', 'unos', 'unas', 'por', 'que', 'como', 'este', 'esta'}
    for p in palabras:
        p_clean = p.strip().lower()
        # Eliminar signos de puntuación comunes al final
        p_clean = p_clean.rstrip(',.?!;:')
        if len(p_clean) > 2 and p_clean not in stop_words:
            palabras_filtradas.append(p_clean)
    return palabras_filtradas

@client.on(events.NewMessage(incoming=True))
async def on_new_message(event):
    # En Telethon, event.is_channel es True tanto para canales de difusión como para supergrupos.
    # Queremos ignorar canales de difusión, pero SÍ procesar supergrupos.
    if event.is_channel and not event.is_group:
        return

    remitente_id = event.sender_id
    
    mensaje = ""
    if event.message.media and hasattr(event.message.media, 'document') and event.message.voice:
        logging.info("Descargando nota de voz...")
        archivo = await event.message.download_media(file=DIR_AUDIOS)
        texto = transcribir_audio_groq(archivo)
        logging.info(f"Transcripción: {texto}")
        mensaje = texto.strip()
        try:
            os.remove(archivo)
        except:
            pass
    else:
        mensaje = event.text.strip() if event.text else ""

    if not mensaje:
        return
        
    logging.info(f"💬 Mensaje recibido de ID {remitente_id}: '{mensaje}'")

    es_grupo = event.is_group
    m_lower = mensaje.lower()

    # Obtener nombre del remitente y guardar para aprendizaje pasivo
    remitente_nombre = "Usuario desconocido"
    try:
        sender = await event.get_sender()
        if sender:
            first_name = getattr(sender, 'first_name', '') or ''
            last_name = getattr(sender, 'last_name', '') or ''
            username = getattr(sender, 'username', '') or ''
            parts = [p for p in [first_name, last_name] if p]
            remitente_nombre = " ".join(parts)
            if username:
                remitente_nombre += f" (@{username})"
    except Exception as e:
        logging.info(f"[ERROR OBTENER SENDER] {e}")

    guardar_mensaje_aprendizaje(remitente_id, remitente_nombre, mensaje, es_grupo)

    # 1. IDENTIDAD DUAL: Cristian (Solicita herramientas de Antigravity)
    if remitente_id == MI_TELEGRAM_ID:
        if mensaje.startswith("/status"):
            await event.respond("⚡ [Antigravity] Servidor local operativo. Todo en orden, Cristian.")
            return
        elif mensaje.startswith("/buscar"):
            await event.respond("🔍 [Antigravity] Iniciando barrido web de novedades...")
            return
            
    # 2. IDENTIDAD DUAL: Técnico / General (Habla Supervisor)
    # Detectar mención o respuesta al bot
    global BOT_USER_ID
    me_menciono = False
    if event.message.mentioned:
        me_menciono = True
    elif event.is_reply:
        try:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.sender_id == BOT_USER_ID:
                me_menciono = True
        except Exception as e:
            logging.info(f"[ERROR VERIFICAR REPLY] {e}")

    if "supervisor" in m_lower or "hermes" in m_lower:
        me_menciono = True

    # Cargar lista de locales dinámicos
    locales_conocidos = obtener_lista_locales()
    palabras_clave = filtrar_palabras(mensaje)
    menciona_local = any(p in locales_conocidos for p in palabras_clave)

    # Filtro flexible para intervenir en el grupo
    if es_grupo:
        # Si fue mencionado o respondido directamente, respondemos
        if me_menciono:
            debe_responder = True
        else:
            # Pregunta de dirección (local específico + palabra de dirección/pregunta, o palabras clave de dirección)
            palabras_direccion = {"direccion", "dirección", "queda", "ubicación", "ubicacion", "dire", "direc"}
            palabras_pregunta_dir = {"alguien", "conocen", "saben", "dónde", "donde", "cuál", "cual", "pasa", "pasame", "pásame", "pasar", "dirección", "direccion"}
            
            tiene_kw_direccion = any(w in m_lower for w in palabras_direccion)
            tiene_kw_pregunta_dir = any(w in m_lower for w in palabras_pregunta_dir)
            
            pregunta_direccion = menciona_local and (tiene_kw_direccion or tiene_kw_pregunta_dir)
            pregunta_direccion_generica = tiene_kw_direccion and tiene_kw_pregunta_dir
            
            # Pregunta de falla/error técnico
            palabras_tecnicas = {"error", "falla", "roto", "no anda", "no funciona", "alarma", "problema", "cimbali", "ablandador", "filtrando", "pérdida", "manómetro", "presión", "presion", "caldera", "temperatura"}
            palabras_pregunta_tecnica = {"alguien", "sabe", "saben", "cómo", "como", "quién", "quien", "ayuda", "conoce", "solución", "solucion", "limpiar", "purga", "reparar", "arreglar", "que le pasa", "qué le pasa"}
            
            tiene_kw_tecnica = any(w in m_lower for w in palabras_tecnicas)
            tiene_kw_pregunta_tecnica = any(w in m_lower for w in palabras_pregunta_tecnica)
            
            pregunta_falla = tiene_kw_tecnica and tiene_kw_pregunta_tecnica
            
            debe_responder = pregunta_direccion or pregunta_direccion_generica or pregunta_falla

        if not debe_responder:
            return  # Silencio en el grupo
            
    # Filtrar palabras significativas para buscar local (ya definido arriba)
    
    # Nivel 1: Consulta Estática (Dirección de locales)
    if "direccion" in m_lower or "dirección" in m_lower or "donde queda" in m_lower or "dónde queda" in m_lower:
        for palabra in palabras_clave:
            res = buscar_direccion_local(palabra)
            if res:
                await event.respond(f"📍 [Supervisor] La dirección de {res[0]} es: {res[1]}")
                return
        await event.respond("📍 [Supervisor] No encontré el local solicitado. ¿Me indicas la sigla o nombre?")
        return
        
    # Nivel 2: Consulta Dinámica (Pendientes)
    elif "pendiente" in m_lower or "pendientes" in m_lower or "tarea" in m_lower or "tareas" in m_lower:
        for palabra in palabras_clave:
            pendientes = buscar_pendientes_local(palabra)
            if pendientes:
                respuesta = f"📋 [Supervisor] Pendientes registrados para {palabra.upper()}:\n"
                for p in pendientes:
                    respuesta += f"- {p[0]} (Registrado: {p[1]})\n"
                await event.respond(respuesta)
                return
        await event.respond("📋 [Supervisor] No hay pendientes críticos registrados para ese local en este momento.")
        return

    # Nivel 3: Consultas Complejas / Errores técnicos (Manuales / RAG)
    elif "error" in m_lower or "falla" in m_lower or "cimbali" in m_lower or "ablandador" in m_lower:
        msg_espera = await event.respond("🛠️ [Supervisor] Buscando en los manuales de servicio. Aguarda un instante...")
        
        # Intentar usar la API local inteligente (Gemini)
        respuesta_ia = consultar_api_local(mensaje, remitente_id)
        if not respuesta_ia:
            # Fallback estático en caso de fallo
            respuesta_ia = "El error indica problemas de presión en la caldera o filtro saturado. Por favor, realiza la purga de la válvula de entrada y verifica el manómetro."
        
        await msg_espera.edit(f"🛠️ [Supervisor] {respuesta_ia}")
        return

    # Nivel 4: Asistente General (Solo en privado y solo para el Jefe)
    if not es_grupo and remitente_id == MI_TELEGRAM_ID:
        respuesta_ia = consultar_api_local(mensaje, remitente_id)
        if respuesta_ia:
            await event.respond(f"🧠 [Supervisor] {respuesta_ia}")
        return

async def main():
    global BOT_USER_ID
    logging.info("Iniciando conexión con Telegram MTProto...")
    await client.start(phone=PHONE)
    
    # Iniciar el servidor local de notificaciones
    await start_notification_server()
    
    try:
        me = await client.get_me()
        BOT_USER_ID = me.id
        logging.info(f"--- [CONECTADO] El Supervisor (ID: {BOT_USER_ID}) está escuchando chats de forma activa ---")
    except Exception as e:
        logging.info(f"Error al obtener ID propio: {e}")
        logging.info("--- [CONECTADO] El Supervisor está escuchando chats de forma activa ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
