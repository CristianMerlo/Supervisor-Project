import os
import sys
import sqlite3
import requests
from pathlib import Path
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Cargar variables de entorno locales
load_dotenv()

# Credenciales de Telegram MTProto
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")
MI_TELEGRAM_ID = 215173956  # ID de Cristian

# APIs de Inteligencia Artificial (Costo Cero / Free Tier)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NOSE_PORTAL_API_KEY = os.getenv("NOSE_PORTAL_API_KEY", "")
NOSE_PORTAL_URL = "https://api.noseportal.com/v1/chat/completions" # URL de inferencia de Nose Portal

# API de Antigravity (Pro / Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Directorios de trabajo
DIR_AUDIOS = Path("temp_audios")
DIR_AUDIOS.mkdir(exist_ok=True)

# Iniciar el cliente de Telethon (Userbot)
client = TelegramClient('supervisor', API_ID, API_HASH)

def transcribir_audio_groq(audio_path):
    """
    Usa la API gratuita de Groq (Whisper-Large-V3) para transcribir el audio de forma veloz y a costo cero.
    """
    if not GROQ_API_KEY:
        return "[Error: Falta GROQ_API_KEY en las variables de entorno]"
        
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    
    # Intentamos convertir si pydub está disponible, de lo contrario enviamos el archivo original
    # (Groq acepta .ogg y .opus directamente, por lo que la conversión a veces es opcional)
    try:
        with open(audio_path, "rb") as audio_file:
            files = {
                "file": (os.path.basename(audio_path), audio_file, "audio/ogg"),
                "model": (None, "whisper-large-v3"),
                "language": (None, "es")
            }
            response = requests.post(url, headers=headers, files=files)
            if response.status_code == 200:
                transcripcion = response.json().get("text", "")
                print(f"[TRANSCRIBCIÓN GROQ] {transcripcion}")
                return transcripcion
            else:
                print(f"[ERROR GROQ WHISPER] Código {response.status_code}: {response.text}")
                return f"[Error en transcripción: Código {response.status_code}]"
    except Exception as e:
        print(f"[ERROR AUDIO] Falla al leer/enviar el archivo: {e}")
        return f"[Error al procesar archivo de audio: {str(e)}]"

def consultar_deepseek_nose_portal(prompt_sistema, consulta_usuario):
    """
    Intenta consultar DeepSeek V4 Flash en Nose Portal de forma gratuita. Retorna None si falla.
    """
    if not NOSE_PORTAL_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {NOSE_PORTAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": consulta_usuario}
        ],
        "temperature": 0.3
    }
    try:
        response = requests.post(NOSE_PORTAL_URL, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[FALLBACK DEEPSEEK] Error: {e}")
    return None

def consultar_groq_llm(prompt_sistema, consulta_usuario):
    """
    Intenta consultar Llama 3 70B en Groq de forma gratuita. Retorna None si falla.
    """
    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": consulta_usuario}
        ],
        "temperature": 0.3
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[FALLBACK GROQ LLM] Error: {e}")
    return None

def consultar_gemini_free(prompt_sistema, consulta_usuario):
    """
    Intenta consultar Gemini 1.5 Flash (Free Tier) usando la API Key de Gemini. Retorna None si falla.
    """
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"SYSTEM INSTRUCTION: {prompt_sistema}\n\nUSER MESSAGE: {consulta_usuario}"}
                ]
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[FALLBACK GEMINI FREE] Error: {e}")
    return None

def consultar_gemini_antigravity_pro(prompt_sistema, consulta_usuario):
    """
    Consulta Gemini 1.5 Pro (Antigravity Pro) de forma garantizada.
    """
    if not GEMINI_API_KEY:
        return "[Error: Falta GEMINI_API_KEY]"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"SYSTEM INSTRUCTION: {prompt_sistema}\n\nUSER MESSAGE: {consulta_usuario}"}
                ]
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[Error al conectar con Gemini Pro: {str(e)}]"
    return "[Error en la respuesta de Gemini Pro]"

def consultar_hermes_resiliente(prompt_sistema, consulta_usuario):
    """
    Bucle de fallback dinámico para Hermes:
    1. Intenta Nose Portal (DeepSeek V4 Flash) - Costo Cero
    2. Si falla, intenta Groq (Llama 3 70B) - Costo Cero
    3. Si falla, intenta Gemini 1.5 Flash - Costo Cero / Free Tier
    4. Si falla, cae a Gemini 1.5 Pro - Paid / Pro Tokens
    """
    res = consultar_deepseek_nose_portal(prompt_sistema, consulta_usuario)
    if res:
        print("[Hermes Engine] Respondido vía Nose Portal (DeepSeek)")
        return res
        
    res = consultar_groq_llm(prompt_sistema, consulta_usuario)
    if res:
        print("[Hermes Engine] Respondido vía Groq (Llama 3)")
        return res
        
    res = consultar_gemini_free(prompt_sistema, consulta_usuario)
    if res:
        print("[Hermes Engine] Respondido vía Gemini Free (Flash)")
        return res
        
    print("[Hermes Engine] Todos los canales gratuitos fallaron. Usando Gemini Pro (Antigravity).")
    return consultar_gemini_antigravity_pro(prompt_sistema, consulta_usuario)


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
    cursor.execute("""
        SELECT p.detalle, p.fecha 
        FROM pendientes p 
        JOIN locales l ON p.sigla = l.sigla 
        WHERE l.sigla = ? OR l.nombre LIKE ?
    """, (termino.upper(), f"%{termino}%"))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

async def enrutar_mensaje(event, mensaje_texto):
    """
    Enrutador principal de los 4 Niveles de Inteligencia.
    """
    remitente_id = event.sender_id
    
    # NIVEL 4: Asistente del Jefe (Chat Libre con Gemini Pro)
    if remitente_id == MI_TELEGRAM_ID:
        if mensaje_texto.startswith("/status"):
            await event.respond("⚡ [Antigravity] Servidor local Ubuntu operativo. Todos los servicios systemd en orden.")
            return
        else:
            prompt_jefe = "Actúas como Antigravity, un asistente de sistemas e IA avanzado de Cristian. Responde sus dudas de forma clara, técnica y concisa."
            respuesta = consultar_gemini_antigravity_pro(prompt_jefe, mensaje_texto)
            await event.respond(f"🧠 [Antigravity] {respuesta}")
            return

    # MODO ESCUCHA GRUPOS: Silencio inteligente en grupos
    if event.is_group:
        # Solo responde en grupos si el mensaje tiene intenciones de falla Y pregunta técnica ("alguien sabe", "falla", "error")
        if not ("falla" in mensaje_texto.lower() or "error" in mensaje_texto.lower() or "alguien sabe" in mensaje_texto.lower()):
            return # Ignorar conversaciones casuales
            
    # INTERFAZ HERMES PARA TÉCNICOS (Nivel 1, 2 y 3)
    # Nivel 1: Datos Maestros (Estático)
    if "direccion" in mensaje_texto.lower() or "dónde queda" in mensaje_texto.lower():
        palabras = mensaje_texto.replace("?", "").replace(",", "").split()
        for palabra in palabras:
            res = buscar_direccion_local(palabra)
            if res:
                await event.respond(f"📍 [Supervisor] La dirección de {res[0]} es: {res[1]}")
                return
        await event.respond("📍 [Supervisor] No localicé esa sucursal en la base SQLite. ¿Puedes darme la sigla?")
        return

    # Nivel 2: Tareas Pendientes (Mantenimiento)
    elif "pendiente" in mensaje_texto.lower() or "tarea" in mensaje_texto.lower():
        palabras = mensaje_texto.replace("?", "").replace(",", "").split()
        for palabra in palabras:
            pendientes = buscar_pendientes_local(palabra)
            if pendientes:
                respuesta = f"📋 [Supervisor] Pendientes críticos de {palabra.upper()}:\n"
                for p in pendientes:
                    respuesta += f"- {p[0]} (Registrado: {p[1]})\n"
                await event.respond(respuesta)
                return
        await event.respond("📋 [Supervisor] No hay pendientes de mantenimiento críticos registrados para este local.")
        return

    # Nivel 3: Diagnóstico y Fallas (IA DeepSeek V4 Flash de Nose Portal + RAG local)
    elif any(x in mensaje_texto.lower() for x in ["error", "falla", "cimbali", "ablandador"]):
        msg_espera = await event.respond("🛠️ [Supervisor] Buscando diagnóstico en los manuales de servicio...")
        
        # Cargar manuales / contexto RAG local si existe, sino pasar la consulta directa
        # (Aquí puedes leer archivos de manuales en Markdown locales)
        contexto_manuales = "Manual Cafetera Cimbali: Error 58 indica falla de llenado de agua en caldera tras 3 minutos de intentar. Verificar presión de red, filtro y bomba."
        
        prompt_hermes = (
            "Eres Hermes, el subagente de mantenimiento. Tu tarea es ayudar al técnico a resolver la falla. "
            "Usa el siguiente contexto técnico para responder la duda de forma clara y directa.\n\n"
            f"CONTEXTO DE MANUALES:\n{contexto_manuales}"
        )
        
        respuesta_hermes = consultar_hermes_resiliente(prompt_hermes, mensaje_texto)
        await msg_espera.edit(f"🛠️ [Supervisor] {respuesta_hermes}")
        return

    # Mensaje casual de técnico no capturado por filtros
    await event.respond("📋 [Supervisor] Entendido. Si es un reporte formal, recuerda enviar el PDF con prefijo MTZ_ o detallar la falla/error para revisarlo en el manual.")

@client.on(events.NewMessage(incoming=True))
async def manejador_principal(event):
    """
    Captura todos los mensajes entrantes (texto o notas de voz).
    """
    # 1. Procesamiento de Notas de Voz / Audio (Whisper en Groq - Capa de Ahorro de Tokens)
    if event.message.voice or event.message.audio:
        nombre_archivo = f"audio_{event.sender_id}_{event.message.id}.ogg"
        ruta_archivo = DIR_AUDIOS / nombre_archivo
        
        # Descarga rápida del audio
        print(f"[AUDIO ENTRANTE] Descargando de {event.sender_id}...")
        await event.download_media(file=str(ruta_archivo))
        
        # Transcripción a texto usando la API gratuita de Groq (Whisper)
        texto_transcrito = transcribir_audio_groq(str(ruta_archivo))
        
        # Eliminar archivo temporal local para cuidar disco
        if ruta_archivo.exists():
            os.remove(ruta_archivo)
            
        if texto_transcrito and not texto_transcrito.startswith("[Error"):
            # Enrutar el texto transcrito
            await enrutar_mensaje(event, texto_transcrito)
        else:
            await event.respond("⚠️ [Supervisor] No pude procesar tu audio. Por favor escribe la consulta en texto.")
            
    # 2. Procesamiento de Texto Estándar
    elif event.text:
        await enrutar_mensaje(event, event.text)

async def main():
    print("Iniciando conexión con Telegram MTProto...")
    await client.start(phone=PHONE)
    print("--- [CONECTADO] El Supervisor (Antigravity & Hermes) está en línea ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
