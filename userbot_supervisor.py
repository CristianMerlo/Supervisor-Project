import os
import sqlite3
import sys
import requests
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv

import logging

logging.basicConfig(filename='userbot.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

def transcribir_y_guardar_imagen(image_path, md_path):
    try:
        with open(image_path, "rb") as img_file:
            files = {"file": (os.path.basename(image_path), img_file, "image/jpeg")}
            res = requests.post("http://localhost:8000/v1/transcribe", files=files, timeout=90)
            if res.status_code == 200:
                markdown_content = res.json().get("markdown", "")
                if markdown_content:
                    with open(md_path, "w", encoding="utf-8") as md_file:
                        md_file.write(markdown_content)
                    logging.info(f"✅ Transcripción guardada exitosamente en {md_path}")
                else:
                    logging.info("⚠️ La API de transcripción devolvió contenido vacío.")
            else:
                logging.info(f"❌ La API de transcripción devolvió status: {res.status_code}")
    except Exception as e:
        logging.info(f"❌ Error transcribiendo imagen en segundo plano: {e}")

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
import threading
import json
STATE_FILE = "/home/cristian/Documentos/Supervisor/telegram_bridge/bridge_state.json"
DB_PATH_MASTER = "/home/cristian/Documentos/Supervisor/supervisor_local.db"

def cargar_estado():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.info(f"Error cargando estado: {e}")
    return {}

def guardar_estado(estado):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(estado, f)
    except Exception as e:
        logging.info(f"Error guardando estado: {e}")

def limpiar_estado():
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception as e:
            logging.info(f"Error eliminando estado: {e}")

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

def cargar_mapa_locales():
    """Carga un mapeo completo de siglas de sistema, siglas de tickets y nombres hacia la sigla oficial y nombre real."""
    mapa = {}
    csv_path = "/home/cristian/Documentos/Supervisor/locales.csv"
    if not os.path.exists(csv_path):
        csv_path = "/home/cristian/PROYECTOS/Supervisor-Project/locales.csv"
        
    if os.path.exists(csv_path):
        try:
            import csv
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    sigla_sistema = row.get("SIGLA SISTEMA", "").strip().upper()
                    sigla_tickets = row.get("SIGLA TICKETS", "").strip().upper()
                    nombre_local = row.get("LOCAL", "").strip()
                    
                    # Sigla oficial será sigla_sistema, o sigla_tickets si la de sistema es '-'
                    sigla_oficial = sigla_sistema
                    if not sigla_oficial or sigla_oficial == "-":
                        sigla_oficial = sigla_tickets
                    
                    if not sigla_oficial:
                        continue
                        
                    datos = {
                        "sigla": sigla_oficial,
                        "nombre": nombre_local,
                        "direccion": row.get("DIRECCION", "").strip(),
                        "supervisor": row.get("SUPERVISOR (GTE ZONA)", "").strip()
                    }
                    
                    # Registrar bajo sigla de sistema
                    if sigla_sistema and sigla_sistema != "-":
                        mapa[sigla_sistema] = datos
                    # Registrar bajo sigla de tickets
                    if sigla_tickets and sigla_tickets != "-":
                        mapa[sigla_tickets] = datos
                    # Registrar bajo nombre del local (normalizado)
                    if nombre_local:
                        mapa[nombre_local.lower()] = datos
        except Exception as e:
            logging.info(f"[ERROR cargar_mapa_locales] {e}")
            
    # Fallback con base de datos si el CSV falla
    try:
        conn = sqlite3.connect(DB_PATH_MASTER)
        cursor = conn.cursor()
        cursor.execute("SELECT sigla, nombre, direccion, supervisor FROM locales")
        for row in cursor.fetchall():
            sigla = row[0].strip().upper()
            nombre = row[1].strip()
            datos = {
                "sigla": sigla,
                "nombre": nombre,
                "direccion": row[2],
                "supervisor": row[3]
            }
            if sigla not in mapa:
                mapa[sigla] = datos
            if nombre.lower() not in mapa:
                mapa[nombre.lower()] = datos
        conn.close()
    except Exception as e:
        logging.info(f"[ERROR DB fallback locales] {e}")
        
    return mapa

def buscar_local_criterio_amplio(mensaje, mapa_locales):
    """Busca un local en el mensaje usando coincidencia de siglas o nombre completo, con tolerancia a errores simples."""
    m_clean = mensaje.upper().strip()
    
    # 1. Buscar coincidencia exacta de siglas (palabras sueltas en el mensaje)
    palabras = [p.strip().upper().rstrip(',.?!;:') for p in mensaje.split()]
    for p in palabras:
        if p in mapa_locales:
            return mapa_locales[p]
            
    # 2. Buscar coincidencia en el nombre del local completo (ej: "Villa del Parque" en el mensaje)
    m_lower = mensaje.lower()
    candidato = None
    max_len = 0
    for key, datos in mapa_locales.items():
        # Evitar buscar por siglas cortas de menos de 3 letras en el texto completo para evitar falsos positivos
        if len(key) < 3:
            continue
        if key in m_lower:
            # Elegir la coincidencia más larga para evitar que "Laferrere 2" coincida solo con "Laferrere"
            if len(key) > max_len:
                candidato = datos
                max_len = len(key)
                
    if candidato:
        return candidato
        
    # 3. Tolerancia simple (coincidencia parcial de palabras largas)
    for key, datos in mapa_locales.items():
        if len(key) > 5 and key in m_lower:
            return datos
            
    return None

async def esperar_respuesta_timeout(chat_id_str, expected_status, timeout_seconds=600):
    await asyncio.sleep(timeout_seconds)
    estado_actual = cargar_estado()
    if estado_actual.get("chat_id") == chat_id_str and estado_actual.get("status") == expected_status:
        files = estado_actual.get("files", [])
        desc_files = ""
        if files:
            desc_files = ", ".join([f"`{f.get('file_name')}`" for f in files])
        else:
            ruta_descarga = estado_actual.get("ruta_descarga")
            if ruta_descarga:
                desc_files = f"`{os.path.basename(ruta_descarga)}`"
                
        limpiar_estado()
        
        sender_name = estado_actual.get("sender_name", "Un técnico")
        chat_title = estado_actual.get("chat_title", "un grupo")
        aviso = (
            f"⚠️ *[Aviso de Confirmación Pendiente]*\n"
            f"El técnico {sender_name} en '{chat_title}' subió archivos ({desc_files or 'Multimedia'}) "
            f"pero no respondió a la pregunta de confirmación en los últimos 10 minutos.\n"
            f"El estado fue liberado. Puedes retomar el tema con él más tarde."
        )
        try:
            await client.send_message(MI_TELEGRAM_ID, aviso)
        except Exception as e_aviso:
            logging.info(f"Error enviando aviso de timeout a Cristian: {e_aviso}")

def obtener_lista_locales():
    try:
        mapa = cargar_mapa_locales()
        vistos = set()
        locales = []
        for key, datos in mapa.items():
            sigla = datos["sigla"]
            nombre = datos["nombre"]
            identificador = f"{sigla}: {nombre}"
            if identificador not in vistos:
                vistos.add(identificador)
                locales.append(identificador)
        return locales
    except Exception as e:
        logging.info(f"[ERROR DB locales] No se pudo cargar: {e}")
        return []

def obtener_contexto_cronograma(sender):
    try:
        import json
        import os
        
        nombre_completo = ""
        if sender:
            fn = getattr(sender, "first_name", "") or ""
            ln = getattr(sender, "last_name", "") or ""
            nombre_completo = f"{fn} {ln}".strip().lower()
            
        tecnicos_map = {
            "fernando": "Fernando Soria",
            "soria": "Fernando Soria",
            "anabella": "Anabella Guerrero",
            "ana": "Anabella Guerrero",
            "guerrero": "Anabella Guerrero",
            "tomas": "Tomas Vera",
            "tomy": "Tomas Vera",
            "vera": "Tomas Vera",
            "francisco": "Francisco Rametta",
            "rametta": "Francisco Rametta"
        }
        
        tecnico_detectado = None
        for key, val in tecnicos_map.items():
            if key in nombre_completo:
                tecnico_detectado = val
                break
                
        if not tecnico_detectado:
            return ""
            
        cronograma_path = "/home/cristian/PROYECTOS/Supervisor-Project/cronograma_tecnicos.json"
        if not os.path.exists(cronograma_path):
            return ""
            
        with open(cronograma_path, "r", encoding="utf-8") as f:
            cronograma = json.load(f)
            
        import datetime
        dias_semana = {
            0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves", 
            4: "viernes", 5: "sabado", 6: "domingo"
        }
        dia_hoy = dias_semana[datetime.datetime.now().weekday()]
        
        locales_hoy = cronograma.get(tecnico_detectado, {}).get(dia_hoy, [])
        if locales_hoy:
            if "OFF" in locales_hoy or not locales_hoy:
                return f"El técnico {tecnico_detectado} hoy ({dia_hoy}) tiene franco (OFF) o no tiene asignación."
            return f"El técnico {tecnico_detectado} hoy ({dia_hoy}) tiene asignados los siguientes locales en su ruta: {', '.join(locales_hoy)}."
    except Exception as e:
        logging.info(f"Error cargando cronograma: {e}")
    return ""


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

pending_approvals = {}
modo_chat = {}

async def ask_approval_handler(request):
    try:
        data = await request.json()
        mensaje = data.get("message", "Solicitud de aprobación sin mensaje")
        req_id = data.get("request_id")
        if req_id:
            pending_approvals[req_id] = "pending"
            # Formato de Telegram para copiar con un toque (si la app lo soporta)
            mensaje_con_botones = f"{mensaje}\n\n👉 Responde con uno de estos comandos copiando el ID:\n`/aprobar {req_id}`\n`/rechazar {req_id}`"
            await client.send_message(MI_TELEGRAM_ID, mensaje_con_botones)
            return web.json_response({"status": "ok"})
        return web.json_response({"error": "No request_id"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def check_approval_handler(request):
    req_id = request.match_info.get('req_id')
    status = pending_approvals.get(req_id, "unknown")
    return web.json_response({"status": status})

async def notify_handler(request):
    try:
        message = ""
        chat_id = MI_TELEGRAM_ID
        if request.has_body:
            try:
                data = await request.json()
                message = data.get("message", "").strip()
                if "chat_id" in data:
                    chat_id = int(data["chat_id"])
            except Exception:
                try:
                    data = await request.post()
                    message = data.get("message", "").strip()
                except Exception:
                    pass
            if not message:
                message = (await request.text()).strip()
        
        if message:
            logging.info(f"[UPS ALERTA LOCAL] Enviando a {chat_id}: {message}")
            # Si ya contiene un tag de agente con formato unificado, lo enviamos directo
            if any(tag in message for tag in ["[Hermes]", "[Goose]", "[Antigravity]"]):
                await client.send_message(chat_id, message)
            else:
                await client.send_message(chat_id, f"🔌 [Supervisor UPS] {message}")
            return web.Response(text="Enviado con éxito\n")
        else:
            return web.Response(text="Mensaje vacío\n", status=400)
    except Exception as e:
        logging.info(f"[ERROR NOTIFICACIÓN LOCAL] {e}")
        return web.Response(text=f"Error: {e}\n", status=500)

async def notify_file_handler(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        if not field:
            return web.Response(status=400, text="No file uploaded")
            
        filename = field.filename
        content = await field.read()
        
        chat_id = MI_TELEGRAM_ID
        if 'chat_id' in request.query:
            chat_id = int(request.query['chat_id'])
            
        import tempfile
        import os
        fd, temp_path = tempfile.mkstemp(suffix=filename)
        with open(fd, 'wb') as f:
            f.write(content)
            
        caption = "📄 Reporte Adjunto"
        if 'caption' in request.query:
            caption = request.query['caption']
        
        await client.send_file(chat_id, temp_path, caption=caption)
        os.remove(temp_path)
        return web.Response(text="Archivo enviado con éxito")
    except Exception as e:
        logging.info(f"[ERROR SEND_FILE] {e}")
        return web.Response(text=f"Error: {e}\n", status=500)

async def start_notification_server():
    app = web.Application()
    app.router.add_post('/notify', notify_handler)
    app.router.add_post('/notify_file', notify_file_handler)
    app.router.add_post('/ask_approval', ask_approval_handler)
    app.router.add_get('/check_approval/{req_id}', check_approval_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8088)
    await site.start()
    logging.info("--- [SERVER LOCAL] Notificador local escuchando en 127.0.0.1:8088/notify ---")

def buscar_direccion_local(termino):
    conn = sqlite3.connect(DB_PATH_MASTER)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, direccion FROM locales WHERE sigla = ? OR nombre LIKE ?", (termino.upper(), f"%{termino}%"))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def buscar_pendientes_local(termino):
    conn = sqlite3.connect(DB_PATH_MASTER)
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

def guardar_mensaje_memoria(chat_id, rol, mensaje):
    try:
        conn = sqlite3.connect(DB_PATH_MASTER)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memoria_conversacional (chat_id, rol, mensaje) VALUES (?, ?, ?)", (str(chat_id), rol, mensaje))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error guardando memoria: {e}")

def obtener_historial(chat_id, limite=10):
    try:
        conn = sqlite3.connect(DB_PATH_MASTER)
        cursor = conn.cursor()
        cursor.execute("SELECT rol, mensaje FROM memoria_conversacional WHERE chat_id = ? ORDER BY id DESC LIMIT ?", (str(chat_id), limite))
        resultados = cursor.fetchall()
        conn.close()
        resultados.reverse()
        return [{"role": row[0], "content": row[1]} for row in resultados]
    except Exception as e:
        logging.error(f"Error obteniendo memoria: {e}")
        return []

def consultar_api_local(mensaje_usuario, chat_id, system_prompt=None, guardar_historial=True, mensaje_original=None):
    """Consulta la API local de Supervisor para obtener respuestas asistidas por IA de Gemini"""
    try:
        url = "http://127.0.0.1:8000/v1/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        if guardar_historial:
            historial = obtener_historial(chat_id, limite=10)
            messages.extend(historial)
            
            texto_a_guardar = mensaje_original if mensaje_original else mensaje_usuario
            guardar_mensaje_memoria(chat_id, "user", texto_a_guardar)
            
        messages.append({"role": "user", "content": mensaje_usuario})

        payload = {
            "model": "gemini-2.0-flash",
            "messages": messages,
            "user": str(chat_id)
        }
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            respuesta = data["choices"][0]["message"]["content"]
            if guardar_historial:
                guardar_mensaje_memoria(chat_id, "assistant", respuesta)
            return respuesta
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
async def handler(event):
    import os
    import shutil
    import asyncio
    if event.is_private and event.sender_id != MI_TELEGRAM_ID:
        return

    remitente_id = event.sender_id
    remitente_nombre = "Usuario"
    
    if event.sender:
        remitente_nombre = getattr(event.sender, "first_name", "Usuario") or getattr(event.sender, "username", "Usuario")

    mensaje = event.text or ""
    
    # NUEVO: Procesar audio ANTES de revisar comandos
    if event.message.media and hasattr(event.message.media, 'document') and getattr(event.message, 'voice', False):
        logging.info("Descargando nota de voz al inicio del handler...")
        try:
            archivo = await event.message.download_media(file=DIR_AUDIOS)
            texto = transcribir_audio_groq(archivo)
            if texto:
                mensaje = texto.strip()
                logging.info(f"Transcripción inicial: {mensaje}")
            import os
            os.remove(archivo)
        except Exception as e:
            logging.info(f"Error procesando audio: {e}")

    # NUEVO: Análisis de Visión Computacional (Skill 16)
    if event.media:
        if getattr(event.media, "photo", None):
            try:
                ruta_descarga = await event.download_media(file="/tmp/")
                if ruta_descarga:
                    import analizador_imagenes
                    import subidor_evidencias
                    import seguimiento_ppm
                    
                    # Recuperar contexto si la foto no tiene caption
                    contexto_mensaje = mensaje
                    if not contexto_mensaje:
                        try:
                            # Buscar en los últimos 5 mensajes del mismo chat/usuario para recuperar contexto
                            mensajes_recientes = await client.get_messages(event.chat_id, limit=5)
                            textos_contexto = []
                            for msg in mensajes_recientes:
                                if msg.sender_id == remitente_id and msg.text:
                                    textos_contexto.append(msg.text)
                            if textos_contexto:
                                contexto_mensaje = " | ".join(textos_contexto)
                                logging.info(f"[VISION CONTEXTO] Recuperado del chat: {contexto_mensaje}")
                        except Exception as e_context:
                            logging.info(f"Error recuperando contexto de mensajes: {e_context}")
                    
                    locales_db = obtener_lista_locales()
                    contexto_cronograma = obtener_contexto_cronograma(event.sender)
                    if contexto_cronograma:
                        logging.info(f"[VISION CRONOGRAMA] Contexto: {contexto_cronograma}")
                    resultado_ia = analizador_imagenes.analizar_foto(ruta_descarga, contexto_mensaje, locales_db, contexto_cronograma)
                    
                    es_evidencia = resultado_ia.get("es_evidencia_tecnica", False)
                    descripcion_ia = resultado_ia.get("descripcion_tecnica", "")
                    sigla_encontrada = resultado_ia.get("local_detectado", None)
                    
                    if not es_evidencia:
                        logging.info("La foto no califica como evidencia técnica relevante (remito, selfie, etc.). Ignorando de forma silenciosa.")
                        import os
                        if os.path.exists(ruta_descarga):
                            os.remove(ruta_descarga)
                    else:
                        if sigla_encontrada:
                            url_foto = subidor_evidencias.subir_evidencia(ruta_descarga)
                            if url_foto:
                                exito, msj_excel = seguimiento_ppm.adjuntar_evidencia_visual(sigla_encontrada, descripcion_ia, url_foto)
                                if exito:
                                    await event.respond(f"✅ [Hermes] Foto analizada y adjuntada como evidencia al local {sigla_encontrada}.\nDiagnóstico:\n{descripcion_ia}")
                                else:
                                    await event.respond(f"⚠️ [Hermes] Foto analizada pero hubo un error en Excel: {msj_excel}")
                            else:
                                await event.respond(f"⚠️ [Hermes] Foto analizada pero falló la subida a Drive.")
                            
                            import os
                            if os.path.exists(ruta_descarga):
                                os.remove(ruta_descarga)
                        else:
                            chat_id_str = str(event.sender_id)
                            estado_tmp = cargar_estado()
                            estado_tmp["chat_id"] = chat_id_str
                            estado_tmp["status"] = "waiting_evidence_local"
                            estado_tmp["ruta_descarga"] = ruta_descarga
                            estado_tmp["descripcion_ia"] = descripcion_ia
                            
                            # Info para watchdog
                            estado_tmp["sender_name"] = remitente_nombre
                            chat = await event.get_chat()
                            chat_title = "Grupo"
                            if chat and hasattr(chat, 'title') and chat.title:
                                chat_title = chat.title
                            estado_tmp["chat_title"] = chat_title
                            
                            guardar_estado(estado_tmp)
                            await event.respond(f"📸 Recibí la evidencia visual, pero no detecto el local.\n¿De qué local estás hablando? (Ej: 9 de julio o FM9JU)")
                            asyncio.create_task(esperar_respuesta_timeout(chat_id_str, "waiting_evidence_local", 600))
                            return
                    
                    mensaje = f"{mensaje}\n\n[IMAGEN ADJUNTA] {descripcion_ia}".strip()
            except Exception as e:
                logging.info(f"Error analizando imagen: {e}")

    if not mensaje and not event.media:
        return
        
    # COMANDOS DIRECTOS (Bypass de Groq)
    if mensaje and mensaje.lower().strip() == "/excel":
        await event.respond("⏳ Construyendo el reporte analítico en Excel (bypassing Groq)...")
        try:
            import agentic_loop
            resultado = agentic_loop.tool_generar_excel_kpi()
            if "[ARCHIVO_ADJUNTO]" in resultado:
                partes = resultado.split("[ARCHIVO_ADJUNTO]")
                texto = partes[0].strip()
                ruta = partes[1].strip()
                await client.send_file(event.chat_id, ruta, caption=texto)
            else:
                await event.respond(f"Error interno: {resultado}")
        except Exception as e:
            await event.respond(f"❌ Fallo crítico armando el Excel: {e}")
        return
        
    # LÓGICA DE ANTIGRAVITY Y ESTADO DE CHAT
    if mensaje.lower().strip() in ["/hermes", "@hermes", "hermes"]:
        modo_chat[remitente_id] = "hermes"
        await event.respond("🧠 [Hermes] He vuelto al control. ¿En qué te ayudo?")
        return

    es_comando_ag = (
        mensaje.lower().startswith("/antigravity") or 
        mensaje.lower().startswith("@antigravity") or 
        mensaje.lower().startswith("arroba antigravity") or
        mensaje.lower().startswith("antigravity")
    )
    
    if es_comando_ag:
        if modo_chat.get(remitente_id) != "antigravity":
            modo_chat[remitente_id] = "antigravity"
            await event.respond("✨ [AntiGravity] Control asumido. Seguiré respondiendo hasta que digas `/hermes`.")
            
    if modo_chat.get(remitente_id) == "antigravity":
        try:
            import google.generativeai as genai
            import os
            from dotenv import load_dotenv
            load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                consulta = mensaje.lower().replace("/antigravity", "").replace("@antigravity", "").replace("arroba antigravity", "").replace("antigravity", "").strip()
                if not consulta:
                    return
                prompt = f"Eres AntiGravity, la IA base que programó a Hermes. El usuario dice: {consulta}. Responde de forma clara y directa."
                respuesta = model.generate_content(prompt).text.strip()
                await event.respond(f"✨ [AntiGravity]\n{respuesta}")
            else:
                await event.respond("❌ Falta GEMINI_API_KEY en .env")
        except Exception as e:
            await event.respond(f"❌ Error de AntiGravity: {e}")
        return

    # LOGICA DE APROBACIÓN POR COMANDOS (SOLUCIONES WIKI)
    if mensaje and mensaje.startswith("/aprobar "):
        req_id = mensaje.split(" ")[1].strip()
        try:
            conn = sqlite3.connect(DB_PATH_MASTER)
            c = conn.cursor()
            c.execute("SELECT maquina, falla, solucion FROM soluciones_pendientes WHERE id = ? AND estado = 'PENDIENTE'", (req_id,))
            row = c.fetchone()
            if row:
                c.execute("UPDATE soluciones_pendientes SET estado = 'APROBADO' WHERE id = ?", (req_id,))
                conn.commit()
                # Registrar en la Wiki
                import agentic_loop
                # Llamar a la herramienta original para registrar
                from obsidian_bridge import ObsidianVault
                vault = ObsidianVault()
                maquina, falla, solucion = row
                titulo = f"Solución - {maquina} - {falla[:30]}"
                contenido = f"**Falla reportada:** {falla}\n\n**Solución confirmada por técnicos:**\n{solucion}"
                enlaces = [maquina.replace(" ", "_")]
                link = vault.crear_nota_wiki(titulo, contenido, enlaces)
                await event.respond(f"✅ Has aprobado la solución {req_id}.\nSe ha registrado permanentemente en la Wiki: {link}")
            else:
                await event.respond("❌ ID de solución no encontrado, o ya fue procesada.")
            conn.close()
        except Exception as e:
            await event.respond(f"Error procesando aprobación: {e}")
        return
        
    if mensaje and mensaje.startswith("/rechazar "):
        req_id = mensaje.split(" ")[1].strip()
        try:
            conn = sqlite3.connect(DB_PATH_MASTER)
            c = conn.cursor()
            c.execute("UPDATE soluciones_pendientes SET estado = 'RECHAZADO' WHERE id = ? AND estado = 'PENDIENTE'", (req_id,))
            if c.rowcount > 0:
                await event.respond(f"🚫 Has rechazado la solución {req_id}. No se agregará a la Wiki.")
            else:
                await event.respond("❌ ID de solución no encontrado, o ya fue procesada.")
            conn.commit()
            conn.close()
        except Exception as e:
            pass
        return

    remitente_id = event.sender_id
    chat_id_str = str(remitente_id)
    
    # Cargar estado actual
    estado = cargar_estado()

    # Interceptar respuesta de texto si hay un flujo interactivo activo para este chat
    mensaje = event.text.strip() if event.text else ""
    
    if estado.get("chat_id") == chat_id_str and mensaje:
        status = estado.get("status")
        files = estado.get("files", [])
        
        if status == "waiting_manual_confirm":
            respuesta_clean = mensaje.lower().strip()
            if respuesta_clean.startswith("s") or respuesta_clean in ["yes", "ok", "bueno", "dale"]:
                # Cambiar de estado y pedir el nombre del equipo
                estado["status"] = "waiting_equipment_name"
                guardar_estado(estado)
                await event.respond(f"☕ *¿Cómo le llaman regularmente a este equipo o máquina en el día a día?* (Ej: Cafetera Iberital, Molino Compak, Termotanque)\n\n*(Se aplicará a los {len(files)} archivos cargados)*")
                return
            elif respuesta_clean.startswith("n") or respuesta_clean in ["no", "cancelar", "cancela"]:
                # En lugar de cancelar, preguntamos si es un reporte de local
                chat = await event.get_chat()
                chat_title = "Grupo"
                if chat and hasattr(chat, 'title') and chat.title:
                    chat_title = chat.title

                estado["status"] = "waiting_report_confirm"
                estado["sender_name"] = remitente_nombre
                estado["chat_title"] = chat_title
                guardar_estado(estado)
                nombres = ", ".join([f"`{f['file_name']}`" for f in files])
                await event.respond(f"📋 Los archivos ({nombres}) no son manuales.\n¿Se trata de un *Informe o Remito técnico* de un local? Responde con *Sí* o *No*.")
                asyncio.create_task(esperar_respuesta_timeout(chat_id_str, "waiting_report_confirm", 600))
                return
            else:
                nombres = ", ".join([f"`{f['file_name']}`" for f in files])
                await event.respond(f"Por favor, responde con *Sí* o *No* para confirmar si el lote de archivos ({nombres}) son manuales.")
                return
                
        elif status == "waiting_equipment_name":
            equipo = mensaje.strip()
            # Crear nombre seguro para el archivo
            safe_equipo = "".join(c for c in equipo if c.isalnum() or c in " _-")
            if not safe_equipo:
                safe_equipo = "Equipo"
            
            # Directorio final
            dest_dir = "/home/cristian/Documentos/Supervisor/brain/manuales"
            os.makedirs(dest_dir, exist_ok=True)
            
            exitosos = []
            fallidos = []
            
            for f in files:
                f_name = f.get("file_name")
                temp_path = f.get("temp_path")
                nuevo_nombre = f"{safe_equipo} - {f_name}"
                dest_path = os.path.join(dest_dir, nuevo_nombre)
                
                if temp_path and os.path.exists(temp_path):
                    try:
                        import shutil
                        shutil.move(temp_path, dest_path)
                        exitosos.append(f_name)
                        
                        # Si es una imagen, transcribirla a .md en segundo plano
                        is_img = nuevo_nombre.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))
                        if is_img:
                            nombre_sin_ext = os.path.splitext(dest_path)[0]
                            md_dest_path = f"{nombre_sin_ext}.md"
                            t = threading.Thread(target=transcribir_y_guardar_imagen, args=(dest_path, md_dest_path))
                            t.start()
                            
                        # Si es un PDF, extraerlo usando PyPDF2 (llamando al script de forma asíncrona)
                        is_pdf = nuevo_nombre.lower().endswith('.pdf')
                        if is_pdf:
                            t = threading.Thread(target=lambda: os.system("python3 /home/cristian/PROYECTOS/Supervisor-Project/convertir_pdfs_a_md.py"))
                            t.start()
                    except Exception as e:
                        logging.info(f"Error moviendo archivo {f_name} en userbot: {e}")
                        fallidos.append(f_name)
                else:
                    fallidos.append(f_name)
                    
            limpiar_estado()
            
            if exitosos:
                archivos_str = "\n".join([f"• `{name}`" for name in exitosos])
                msg = f"✅ *Manuales guardados y clasificados con éxito*:\n• *Equipo:* `{equipo}`\n• *Archivos clasificados:*\n{archivos_str}"
                if fallidos:
                    msg += f"\n\n⚠️ No se pudieron mover: {', '.join(fallidos)}"
                await event.respond(msg)
            else:
                await event.respond("⚠️ Ocurrió un error al intentar mover los archivos del lote.")
            return

        elif status == "waiting_report_confirm":
            respuesta_clean = mensaje.lower().strip()
            if respuesta_clean.startswith("s") or respuesta_clean in ["yes", "ok", "bueno", "dale"]:
                chat = await event.get_chat()
                chat_title = "Grupo"
                if chat and hasattr(chat, 'title') and chat.title:
                    chat_title = chat.title

                estado["status"] = "waiting_local_name"
                estado["sender_name"] = remitente_nombre
                estado["chat_title"] = chat_title
                guardar_estado(estado)
                await event.respond(f"📍 *¿A qué local corresponde este informe?*\n(Ingresa la sigla exacta o el nombre, ej: FVDP o Villa del Parque)")
                asyncio.create_task(esperar_respuesta_timeout(chat_id_str, "waiting_local_name", 600))
                return
            elif respuesta_clean.startswith("n") or respuesta_clean in ["no", "cancelar", "cancela"]:
                for f in files:
                    temp_path = f.get("temp_path")
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                limpiar_estado()
                await event.respond(f"❌ Operación cancelada. Se descartó el lote de {len(files)} archivos.")
                return
            else:
                await event.respond(f"Por favor, responde con *Sí* o *No* para confirmar si el lote es un reporte.")
                return

        elif status == "waiting_local_name":
            local = mensaje.strip()
            # Validar local con criterio amplio
            mapa_locales = cargar_mapa_locales()
            res_mapa = buscar_local_criterio_amplio(local, mapa_locales)
            
            if not res_mapa:
                # Intentar buscar locales con nombres parecidos para sugerir
                sugerencias = []
                for key, datos in mapa_locales.items():
                    if len(key) > 3 and (key in local.lower() or local.lower() in key):
                        sugerencia = f"{datos['nombre']} ({datos['sigla']})"
                        if sugerencia not in sugerencias:
                            sugerencias.append(sugerencia)
                
                msg_sug = ""
                if sugerencias:
                    msg_sug = f"\n¿Tal vez quisiste decir alguno de estos?: " + ", ".join(sugerencias)
                    
                await event.respond(f"⚠️ No encontré el local '{local}'.{msg_sug}\nPor favor, intenta de nuevo escribiendo la sigla exacta o cancela enviando 'no'.")
                return
                
            sigla_real = res_mapa["sigla"]
            nombre_real = res_mapa["nombre"]
            
            dest_dir = "/home/cristian/Documentos/Supervisor/entrantes"
            os.makedirs(dest_dir, exist_ok=True)
            
            import shutil
            import datetime
            fecha_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            exitosos = []
            
            for i, f in enumerate(files):
                f_name = f.get("file_name")
                temp_path = f.get("temp_path")
                ext = os.path.splitext(f_name)[1]
                nuevo_nombre = f"MTZ_{sigla_real}_{fecha_str}_{i}{ext}"
                dest_path = os.path.join(dest_dir, nuevo_nombre)
                
                if temp_path and os.path.exists(temp_path):
                    try:
                        shutil.move(temp_path, dest_path)
                        exitosos.append(nuevo_nombre)
                    except Exception as e:
                        logging.info(f"Error moviendo a entrantes: {e}")
            
            limpiar_estado()
            if exitosos:
                arch_str = "\n".join([f"• `{n}`" for n in exitosos])
                await event.respond(f"✅ *Reporte asignado exitosamente a {nombre_real} ({sigla_real})*.\nArchivos enviados a la cola de Ingesta Automática:\n{arch_str}")
            else:
                await event.respond("⚠️ Ocurrió un error al enviar los archivos a la cola de ingesta.")
            return

        elif status == "waiting_evidence_local":
            local = mensaje.strip()
            
            # Validar local con criterio amplio
            mapa_locales = cargar_mapa_locales()
            res_mapa = buscar_local_criterio_amplio(local, mapa_locales)
            
            import os
            
            if not res_mapa:
                respuesta_clean = local.lower()
                if respuesta_clean.startswith("n") or respuesta_clean in ["no", "cancelar", "cancela"]:
                    ruta_descarga = estado.get("ruta_descarga")
                    if ruta_descarga and os.path.exists(ruta_descarga):
                        try:
                            os.remove(ruta_descarga)
                        except Exception:
                            pass
                    limpiar_estado()
                    await event.respond("❌ Operación cancelada. Evidencia visual descartada.")
                    return
                    
                # Intentar buscar locales con nombres parecidos para sugerir
                sugerencias = []
                for key, datos in mapa_locales.items():
                    if len(key) > 3 and (key in local.lower() or local.lower() in key):
                        sugerencia = f"{datos['nombre']} ({datos['sigla']})"
                        if sugerencia not in sugerencias:
                            sugerencias.append(sugerencia)
                
                msg_sug = ""
                if sugerencias:
                    msg_sug = f"\n¿Tal vez quisiste decir alguno de estos?: " + ", ".join(sugerencias)
                    
                await event.respond(f"⚠️ No encontré el local '{local}'.{msg_sug}\nPor favor, intenta de nuevo escribiendo la sigla exacta o cancela enviando 'cancelar'.")
                return
                
            sigla_real = res_mapa["sigla"]
            
            ruta_descarga = estado.get("ruta_descarga")
            descripcion_ia = estado.get("descripcion_ia", "Sin descripción")
            
            if not ruta_descarga or not os.path.exists(ruta_descarga):
                limpiar_estado()
                await event.respond("⚠️ Error: No se encontró la foto temporal. Por favor, vuelve a enviarla.")
                return
                
            import subidor_evidencias
            import seguimiento_ppm
            
            url_foto = subidor_evidencias.subir_evidencia(ruta_descarga)
            if url_foto:
                exito, msj_excel = seguimiento_ppm.adjuntar_evidencia_visual(sigla_real, descripcion_ia, url_foto)
                if exito:
                    await event.respond(f"✅ [Hermes] Foto analizada y adjuntada como evidencia al local {sigla_real}.\nDiagnóstico:\n{descripcion_ia}")
                else:
                    await event.respond(f"⚠️ [Hermes] Foto analizada pero hubo un error en Excel: {msj_excel}")
            else:
                await event.respond(f"⚠️ [Hermes] Foto analizada pero falló la subida a Drive.")
                
            try:
                os.remove(ruta_descarga)
            except Exception:
                pass
                
            limpiar_estado()
            return

    # Soporte de Videos (Análisis de fallas en video)
    is_video = (event.message.video is not None) or (event.message.media and hasattr(event.message.media, 'document') and (event.message.media.document.mime_type or "").startswith("video/"))
    if is_video:
        file_name = f"video_{event.message.id}.mp4"
        for attr in event.message.media.document.attributes:
            if hasattr(attr, 'file_name'):
                file_name = attr.file_name
                break
        if not file_name.lower().endswith(('.mp4', '.mov', '.avi', '.3gp', '.webm', '.mkv')):
            file_name += ".mp4"
            
        temp_dir = "/tmp/tg_videos_temp"
        os.makedirs(temp_dir, exist_ok=True)
        dest_path = os.path.join(temp_dir, file_name)
        
        is_private = event.is_private
        
        # Si es chat privado (Cristian haciendo pruebas), le respondemos con progreso en el chat
        msg_espera = None
        if is_private:
            msg_espera = await event.respond("🛠️ [Supervisor] He recibido tu video. Estoy descargándolo y analizándolo, por favor aguarda...")
        
        async def procesar_video_async():
            print("🎬 Iniciando procesar_video_async...", flush=True)
            try:
                # Obtener info de remitente y grupo antes de procesar
                sender = await event.get_sender()
                sender_name = "Técnico Desconocido"
                if sender:
                    if hasattr(sender, 'username') and sender.username:
                        sender_name = f"@{sender.username}"
                    elif hasattr(sender, 'first_name') and sender.first_name:
                        sender_name = sender.first_name
                        if hasattr(sender, 'last_name') and sender.last_name:
                            sender_name += f" {sender.last_name}"
                
                chat = await event.get_chat()
                chat_title = "Grupo"
                if chat and hasattr(chat, 'title') and chat.title:
                    chat_title = chat.title
                
                archivo = await event.message.download_media(file=dest_path)
                if not archivo:
                    print("❌ download_media no devolvió archivo", flush=True)
                    if is_private and msg_espera:
                        await msg_espera.edit("⚠️ No se pudo descargar el video para su análisis.")
                    else:
                        await client.send_message(MI_TELEGRAM_ID, f"⚠️ *[Falla de Video]* No se pudo descargar el video subido por {sender_name} en '{chat_title}' para su análisis.")
                    return
                
                print(f"🎬 Video descargado en: {dest_path}, enviando a API...", flush=True)
                import requests
                with open(dest_path, "rb") as f:
                    files = {"file": (file_name, f, "video/mp4")}
                    res = requests.post("http://localhost:8000/v1/analyze_video", files=files, timeout=180)
                    
                print(f"🎬 API respondió con código: {res.status_code}", flush=True)
                if res.status_code == 200:
                    diagnosis = res.json().get("diagnosis", "No se obtuvo diagnóstico.")
                    if is_private:
                        if msg_espera:
                            await msg_espera.delete()
                        await event.respond(diagnosis)
                    else:
                        # Enviar el diagnóstico únicamente a Cristian por privado
                        msg_privado = (
                            f"📹 *[Video en Grupo]* El técnico {sender_name} subió un video en el grupo '{chat_title}'.\n"
                            f"Aquí tienes el análisis automático de Hermes:\n\n"
                            f"{diagnosis}"
                        )
                        await client.send_message(MI_TELEGRAM_ID, msg_privado)
                else:
                    if is_private and msg_espera:
                        await msg_espera.edit(f"⚠️ Ocurrió un error en los servidores al procesar tu video (código {res.status_code}).")
                    else:
                        await client.send_message(MI_TELEGRAM_ID, f"⚠️ *[Falla de Video]* El video subido por {sender_name} en '{chat_title}' falló en el servidor con código {res.status_code}.")
            except Exception as e:
                import traceback
                print(f"❌ Excepción en procesar_video_async: {e}", flush=True)
                traceback.print_exc()
                logging.info(f"Error procesando video en userbot: {e}")
                if is_private and msg_espera:
                    await msg_espera.edit("⚠️ Ocurrió un error inesperado al analizar el video.")
                else:
                    await client.send_message(MI_TELEGRAM_ID, f"⚠️ *[Falla de Video]* Ocurrió una excepción procesando el video de {sender_name} en '{chat_title}': {e}")
            finally:
                if os.path.exists(dest_path):
                    try:
                        os.unlink(dest_path)
                    except:
                        pass
                        
        asyncio.create_task(procesar_video_async())
        return

    # Soporte de Fotos e Imágenes
    is_photo = event.message.photo is not None
    is_doc = event.message.media and hasattr(event.message.media, 'document') and not event.message.voice
    
    if is_photo or is_doc:
        if is_photo:
            file_name = f"foto_{event.message.id}.jpg"
        else:
            file_name = "documento.bin"
            for attr in event.message.media.document.attributes:
                if hasattr(attr, 'file_name'):
                    file_name = attr.file_name
                    break
                    
            # Si es un reporte estándar de Mostaza
            if file_name.upper().startswith("MTZ_") and file_name.upper().endswith(".PDF"):
                dest_dir = "/home/cristian/Documentos/Supervisor/entrantes"
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, file_name)
                
                # Descargar y guardar en entrantes/
                await event.respond(f"📥 Descargando reporte `{file_name}`...")
                archivo = await event.message.download_media(file=dest_path)
                if archivo:
                    await event.respond(f"📥 *Reporte PDF Recibido:* `{file_name}`.\nEntrando en cola de procesamiento...")
                else:
                    await event.respond(f"⚠️ Error al descargar el archivo `{file_name}`. Por favor, reintenta.")
                return

        # Es un manual potencial (documento no estándar o foto/imagen)
        temp_dir = "/tmp/tg_manuals_temp"
        os.makedirs(temp_dir, exist_ok=True)
        dest_path = os.path.join(temp_dir, file_name)
        
        await event.respond(f"📥 Descargando archivo `{file_name}`...")
        archivo = await event.message.download_media(file=dest_path)
        if archivo:
            is_image = is_photo or file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))
            tipo_desc = "la imagen" if is_image else "el documento"
            
            chat = await event.get_chat()
            chat_title = "Grupo"
            if chat and hasattr(chat, 'title') and chat.title:
                chat_title = chat.title

            # Si ya hay un lote en curso esperando confirmación
            if estado.get("chat_id") == chat_id_str and estado.get("status") == "waiting_manual_confirm":
                if "files" not in estado:
                    estado["files"] = []
                estado["files"].append({
                    "temp_path": dest_path,
                    "file_name": file_name
                })
                estado["sender_name"] = remitente_nombre
                estado["chat_title"] = chat_title
                guardar_estado(estado)
                await event.respond(f"📥 Agregado `{file_name}` al lote actual (Total: {len(estado['files'])} archivos).\n¿Se trata de manuales técnicos para el sistema? Responde con *Sí* o *No*.")
            else:
                # Iniciar nuevo lote
                nuevo_estado = {
                    "chat_id": chat_id_str,
                    "status": "waiting_manual_confirm",
                    "files": [{
                        "temp_path": dest_path,
                        "file_name": file_name
                    }],
                    "sender_name": remitente_nombre,
                    "chat_title": chat_title
                }
                guardar_estado(nuevo_estado)
                await event.respond(f"📥 He recibido {tipo_desc} `{file_name}`.\n¿Se trata de un manual técnico para el sistema? Responde con *Sí* o *No*.")
                asyncio.create_task(esperar_respuesta_timeout(chat_id_str, "waiting_manual_confirm", 600))
        else:
            await event.respond(f"⚠️ Error al descargar el archivo `{file_name}`. Por favor, reintenta.")
        return

    pass
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
        elif mensaje.startswith("/reporte"):
            instruccion = mensaje.replace("/reporte_semanal", "").replace("/reporte", "").strip()
            if not instruccion:
                instruccion = "Reporte general por local"
            
            await event.respond(f"📊 [Hermes Analytics] Iniciando generación del reporte dinámico: '{instruccion}'. Aguarda unos segundos...")
            import asyncio
            # Correr en un hilo separado para no bloquear el event loop
            from motor_reportes_supervisor import ReportSupervisor
            loop = asyncio.get_running_loop()
            supervisor_reportes = ReportSupervisor()
            ruta_excel = await loop.run_in_executor(None, supervisor_reportes.generar_reporte_dinamico, instruccion)
            
            if ruta_excel and os.path.exists(ruta_excel):
                await event.respond(file=ruta_excel, message="✅ Aquí tienes tu reporte consolidado.")
            else:
                await event.respond("❌ Ocurrió un error al generar el reporte o faltan credenciales de Google Sheets.")
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

    # Cargar lista de locales dinámicos con criterio amplio
    mapa_locales = cargar_mapa_locales()
    local_detectado = buscar_local_criterio_amplio(mensaje, mapa_locales)
    menciona_local = local_detectado is not None

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
            
            import re
            tiene_error_numero = re.search(r'\berror\s+\d+\b', m_lower) is not None
            
            tiene_kw_tecnica = any(w in m_lower for w in palabras_tecnicas)
            tiene_kw_pregunta_tecnica = any(w in m_lower for w in palabras_pregunta_tecnica)
            
            pregunta_falla = (tiene_kw_tecnica and tiene_kw_pregunta_tecnica) or tiene_error_numero
            
            debe_responder = pregunta_direccion or pregunta_direccion_generica or pregunta_falla

        if not debe_responder:
            return  # Silencio en el grupo
            
    # Filtrar palabras significativas para buscar local (ya definido arriba)
    # 3. Agentic Loop para Consultas Inteligentes (Reemplaza Niveles 1-4)
    # Solo procesa si debe responder en grupo, o si es privado
    if not es_grupo or debe_responder:
        from agentic_loop import consultar_agentic_loop
        
        system_prompt = """Eres Hermes, el "Supervisor" principal del sistema y asistente experto en mantenimiento operativo.
Tienes acceso a múltiples herramientas para consultar datos de locales, pendientes, manuales técnicos y reportes analizados.
REGLAS ESTRICTAS:
1. Siempre sé profesional, resolutivo y analítico.
2. NUNCA respondas que "no tienes la capacidad" o "no encuentras" algo ANTES de usar las herramientas. Úsalas para buscar siglas, información o reportes.
3. Si la herramienta de buscar local te dice que no encontró el local, pide amablemente aclaración. Si te devuelve una sigla (ej. FSJU), usa ESA SIGLA para buscar reportes o pendientes.
4. Si hay fallas técnicas, usa la herramienta de buscar manuales. Si es algo de código o infraestructura que falla, usa la herramienta de contactar a AntiGravity.
5. Inicia tu respuesta final con el emoji 🤖 [Hermes] (a menos que el usuario esté pidiendo ayuda de otro agente, pero Hermes siempre coordina).
"""
        
        # Mostrar "Escribiendo..." en Telegram
        async with client.action(event.chat_id, 'typing'):
            # Cargar historial
            historial = obtener_historial(remitente_id, limite=10)
            
            # Consultar Agentic Loop
            respuesta_ia = consultar_agentic_loop(mensaje, historial, system_prompt)
            
            # Guardar en memoria local del userbot
            guardar_mensaje_memoria(remitente_id, "user", mensaje)
            guardar_mensaje_memoria(remitente_id, "assistant", respuesta_ia)
        if respuesta_ia:
            if "[ARCHIVO_ADJUNTO]" in respuesta_ia:
                partes = respuesta_ia.split("[ARCHIVO_ADJUNTO]")
                mensaje_texto = partes[0].strip()
                ruta_archivo = partes[1].strip()
                
                if mensaje_texto:
                    await event.respond(mensaje_texto)
                if os.path.exists(ruta_archivo):
                    await client.send_file(event.chat_id, ruta_archivo)
                else:
                    await event.respond(f"❌ Error: El archivo generado no se encontró en {ruta_archivo}")
            else:
                await event.respond(respuesta_ia)
        return
async def watchdog_loop():
    logging.info("--- [WATCHDOG] Iniciando perro guardián de conexión Telegram ---")
    while True:
        await asyncio.sleep(300)  # Verificar cada 5 minutos
        try:
            if not client.is_connected():
                logging.info("--- [WATCHDOG] Detectado: Cliente no conectado localmente. Forzando reinicio... ---")
                os._exit(1)
            # Ping ligero a Telegram
            await client.get_me()
            logging.info("[WATCHDOG] Conexión validada con éxito.")
        except Exception as e:
            logging.info(f"--- [WATCHDOG ERROR] Falló validación de conexión: {e}. Forzando reinicio... ---")
            os._exit(1)

async def main():
    global BOT_USER_ID
    logging.info("Iniciando conexión con Telegram MTProto...")
    await client.start(phone=PHONE)
    
    # Iniciar el servidor local de notificaciones
    await start_notification_server()
    
    # Iniciar el perro guardián de conexión
    asyncio.create_task(watchdog_loop())
    
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
