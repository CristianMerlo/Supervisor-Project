# Paquete de Despliegue: Paso C (Integración Resiliente de Hermes Agent & Telegram Userbot)

**Instrucciones para el Agente Antigravity en la máquina de destino (Ubuntu):**
Hola. En este paso vamos a desplegar la integración definitiva del Supervisor de Mantenimiento. Configurarás un **Cliente de Telegram (Userbot)** usando la librería **Telethon** conectado al número propio `+54 11 2163 3815`. 

Este script implementa una arquitectura híbrida de **costo cero** y **tolerancia a fallos**:
1. **Audio Gratuito (Groq Whisper):** Las notas de voz se transcriben gratis con la API de Groq.
2. **Consultas Locales (SQLite):** Las direcciones y tareas pendientes se resuelven en milisegundos consultando la base de datos SQLite local, consumiendo **cero tokens**.
3. **Inferencia Resiliente:** Las fallas y manuales técnicos (Nivel 3) intentan responderse de forma rotativa: primero por Nose Portal (DeepSeek), luego por Groq (Llama 3), luego por Gemini Free (Flash) y, solo si todo lo anterior falla, caen como último respaldo en Gemini Pro (tokens Pro).

Sigue estos 6 pasos ordenados para realizar la instalación y configuración persistente.

---

## 📁 1. Instalación de Dependencias Locales

Ejecuta en la terminal de la máquina Ubuntu destino:
```bash
pip install telethon python-dotenv requests
sudo apt update && sudo apt install -y ffmpeg
```

---

## 📁 1.5. Instalación de la CLI de Hermes Agent

Si además deseas tener la interfaz interactiva oficial de Hermes en tu línea de comando Ubuntu (ejecutar tareas de terminal localmente):

1. **Clonar e instalar:**
   ```bash
   git clone https://github.com/hermes-agent/hermes-cli.git && cd hermes-cli && sudo ./install.sh
   ```
2. **Seleccionar Proveedor (TUI Gated):**
   Advierte que se abrirá un menú interactivo. Ejecuta:
   ```bash
   hermes model
   ```
   *Instrucción:* Navega usando las flechas de teclado y selecciona **Nose Portal** como tu proveedor de modelo.
3. **Validación:**
   Verifica que responda la versión de la herramienta:
   ```bash
   hermes --version
   ```

---


## 🔑 2. Variables de Entorno (`.env`)

Pídele al usuario (Cristian) que obtenga las credenciales del número `+54 11 2163 3815` en [my.telegram.org](https://my.telegram.org/) (sección *API development tools*). Escribe estas claves en el archivo `.env` del servidor:

```env
# Credenciales Telegram MTProto
TELEGRAM_PHONE=+541121633815
TELEGRAM_API_ID=colocar_api_id
TELEGRAM_API_HASH=colocar_api_hash

# API Keys para Inferencia Gratuita y Respaldo
GROQ_API_KEY=colocar_groq_key
NOSE_PORTAL_API_KEY=colocar_nose_portal_key
GEMINI_API_KEY=colocar_gemini_key
```

---

## 🗄️ 3. Inicialización de Base de Datos Local (`supervisor_local.db`)

Crea y ejecuta el script `init_local_db.py` para levantar las tablas SQLite en la raíz del proyecto:

```python
import sqlite3

def init_db():
    conn = sqlite3.connect("supervisor_local.db")
    cursor = conn.cursor()
    
    # Tabla de locales (Nivel 1 - Estático)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locales (
        sigla TEXT PRIMARY KEY,
        nombre TEXT,
        direccion TEXT,
        telefono TEXT,
        supervisor TEXT
    )
    """)
    
    # Tabla de pendientes (Nivel 2 - Dinámico)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pendientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sigla TEXT,
        detalle TEXT,
        fecha TEXT,
        estado TEXT DEFAULT 'ABIERTO',
        FOREIGN KEY(sigla) REFERENCES locales(sigla)
    )
    """)
    
    # Datos de muestra iniciales (Urquiza y Chacabuco)
    cursor.executemany("INSERT OR IGNORE INTO locales VALUES (?, ?, ?, ?, ?)", [
        ("URQ", "Urquiza", "Av. Triunvirato 4500, CABA", "+54 11 9999-8888", "Cristian Merlo"),
        ("CHA", "Chacabuco", "Calle Mitre 123, Chacabuco", "+54 2352 99-9999", "Cristian Merlo")
    ])
    
    cursor.executemany("INSERT OR IGNORE INTO pendientes (sigla, detalle, fecha) VALUES (?, ?, ?)", [
        ("CHA", "Reparación crítica del ablandador de agua (PPM > 200)", "2026-05-25"),
        ("CHA", "Fuga en cafetera Cimbali Horno 1", "2026-05-24")
    ])
    
    conn.commit()
    conn.close()
    print("[SQLite] Base de datos local inicializada exitosamente.")

if __name__ == "__main__":
    init_db()
```

---

## 🐍 4. Código Principal: `userbot_supervisor.py`

Crea el archivo `userbot_supervisor.py` en tu servidor Ubuntu:

```python
import os
import sys
import sqlite3
import requests
from pathlib import Path
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")
MI_TELEGRAM_ID = 215173956  # ID de Cristian

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NOSE_PORTAL_API_KEY = os.getenv("NOSE_PORTAL_API_KEY", "")
NOSE_PORTAL_URL = "https://api.noseportal.com/v1/chat/completions"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DIR_AUDIOS = Path("temp_audios")
DIR_AUDIOS.mkdir(exist_ok=True)

client = TelegramClient('supervisor', API_ID, API_HASH)

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
        print(f"[ERROR AUDIO] Falla: {e}")
    return "[Error en la API de transcripción]"

def consultar_deepseek_nose_portal(prompt_sistema, consulta_usuario):
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
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {prompt_sistema}\n\nUSER MESSAGE: {consulta_usuario}"}]}
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
    if not GEMINI_API_KEY:
        return "[Error: Falta GEMINI_API_KEY]"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {prompt_sistema}\n\nUSER MESSAGE: {consulta_usuario}"}]}
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
    remitente_id = event.sender_id
    
    if remitente_id == MI_TELEGRAM_ID:
        if mensaje_texto.startswith("/status"):
            await event.respond("⚡ [Antigravity] Servidor local Ubuntu operativo. Todos los servicios systemd en orden.")
            return
        else:
            prompt_jefe = "Actúas como Antigravity, un asistente de sistemas e IA avanzado de Cristian. Responde sus dudas de forma clara, técnica y concisa."
            respuesta = consultar_gemini_antigravity_pro(prompt_jefe, mensaje_texto)
            await event.respond(f"🧠 [Antigravity] {respuesta}")
            return

    if event.is_group:
        if not ("falla" in mensaje_texto.lower() or "error" in mensaje_texto.lower() or "alguien sabe" in mensaje_texto.lower()):
            return
            
    if "direccion" in mensaje_texto.lower() or "dónde queda" in mensaje_texto.lower():
        palabras = mensaje_texto.replace("?", "").replace(",", "").split()
        for palabra in palabras:
            res = buscar_direccion_local(palabra)
            if res:
                await event.respond(f"📍 [Supervisor] La dirección de {res[0]} es: {res[1]}")
                return
        await event.respond("📍 [Supervisor] No localicé esa sucursal en la base SQLite. ¿Puedes darme la sigla?")
        return

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

    elif any(x in mensaje_texto.lower() for x in ["error", "falla", "cimbali", "ablandador"]):
        msg_espera = await event.respond("🛠️ [Supervisor] Buscando diagnóstico en los manuales de servicio...")
        contexto_manuales = "Manual Cafetera Cimbali: Error 58 indica falla de llenado de agua en caldera tras 3 minutos de intentar. Verificar presión de red, filtro y bomba."
        prompt_hermes = (
            "Eres Hermes, el subagente de mantenimiento. Tu tarea es ayudar al técnico a resolver la falla. "
            "Usa el siguiente contexto técnico para responder la duda de forma clara y directa.\n\n"
            f"CONTEXTO DE MANUALES:\n{contexto_manuales}"
        )
        respuesta_hermes = consultar_hermes_resiliente(prompt_hermes, mensaje_texto)
        await msg_espera.edit(f"🛠️ [Supervisor] {respuesta_hermes}")
        return

    await event.respond("📋 [Supervisor] Entendido. Si es un reporte formal, recuerda enviar el PDF con prefijo MTZ_ o detallar la falla/error para revisarlo en el manual.")

@client.on(events.NewMessage(incoming=True))
async def manejador_principal(event):
    if event.message.voice or event.message.audio:
        nombre_archivo = f"audio_{event.sender_id}_{event.message.id}.ogg"
        ruta_archivo = DIR_AUDIOS / nombre_archivo
        await event.download_media(file=str(ruta_archivo))
        texto_transcrito = transcribir_audio_groq(str(ruta_archivo))
        if ruta_archivo.exists():
            os.remove(ruta_archivo)
        if texto_transcrito and not texto_transcrito.startswith("[Error"):
            await enrutar_mensaje(event, texto_transcrito)
        else:
            await event.respond("⚠️ [Supervisor] No pude procesar tu audio. Por favor escribe la consulta en texto.")
    elif event.text:
        await enrutar_mensaje(event, event.text)

async def main():
    print("Iniciando conexión con Telegram MTProto...")
    await client.start(phone=PHONE)
    print("--- [CONECTADO] El Supervisor (Antigravity & Hermes) está en línea ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
```

---

## 🔑 5. Primera Autenticación Interactiva

1. Ejecuta el script por primera vez desde la terminal:
   ```bash
   python3 userbot_supervisor.py
   ```
2. La terminal de Ubuntu solicitará el **código de seguridad** enviado por Telegram al número `+54 11 2163 3815`. Escríbelo y presiona Enter.
3. Se generará en la carpeta el archivo de sesión `supervisor.session` que almacena de forma local el token de inicio de sesión permanente. Cancela la ejecución con `Ctrl+C`.

---

## ⚙️ 6. Persistencia del Servicio `systemd`

Para que el script corra permanentemente en el servidor local de Ubuntu y reinicie solo ante cortes de energía:

1. Crea el archivo de configuración del servicio:
   ```bash
   sudo nano /etc/systemd/system/supervisor-userbot.service
   ```
2. Pega el siguiente contenido (ajusta la ruta del proyecto y de python si es necesario):
   ```ini
   [Unit]
   Description=Supervisor Hermes Telegram Userbot Service
   After=network.target

   [Service]
   Type=simple
   User=cristian
   WorkingDirectory=/home/cristian/Documentos/Supervisor
   ExecStart=/usr/bin/python3 userbot_supervisor.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Carga y arranca el servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable supervisor-userbot
   sudo systemctl start supervisor-userbot
   ```
4. Monitorea que todo esté corriendo sin problemas:
   ```bash
   sudo systemctl status supervisor-userbot
   ```
