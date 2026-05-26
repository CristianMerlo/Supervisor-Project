import os
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTIGRAVITY_URL = os.getenv("ANTIGRAVITY_API_URL", "http://localhost:8000/v1/chat/completions")
MAIN_GROUP_ID = os.getenv("MAIN_GROUP_ID")

import base64

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else ""

def descargar_audio_telegram(file_id):
    """Descarga el archivo de audio desde Telegram y lo devuelve en Base64."""
    try:
        # Obtener ruta del archivo
        res = requests.get(f"{BASE_URL}/getFile?file_id={file_id}", timeout=10)
        res.raise_for_status()
        file_path = res.json()["result"]["file_path"]
        
        # Descargar archivo binario
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        audio_res = requests.get(file_url, timeout=30)
        audio_res.raise_for_status()
        
        # Codificar en Base64
        return base64.b64encode(audio_res.content).decode("utf-8")
    except Exception as e:
        print(f"Error descargando audio de Telegram: {e}")
        return None

def descargar_documento_telegram(file_id, dest_path):
    """Descarga un documento desde Telegram y lo guarda en la ruta especificada."""
    try:
        # Obtener ruta del archivo
        res = requests.get(f"{BASE_URL}/getFile?file_id={file_id}", timeout=10)
        res.raise_for_status()
        file_path = res.json()["result"]["file_path"]
        
        # Descargar archivo binario
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        doc_res = requests.get(file_url, timeout=60)
        doc_res.raise_for_status()
        
        # Guardar localmente
        with open(dest_path, "wb") as f:
            f.write(doc_res.content)
        print(f"[Telegram] Documento guardado en: {dest_path}")
        return True
    except Exception as e:
        print(f"Error descargando documento de Telegram: {e}")
        return False

def enviar_a_antigravity(mensaje, chat_id, audio_base64=None):
    try:
        print(f"🔄 Enviando a Antigravity — chat_id={chat_id}, url={ANTIGRAVITY_URL}", flush=True)
        if audio_base64:
            content_parts = [
                {"type": "text", "text": mensaje or "Analiza este audio por favor."},
                {"type": "input_audio", "input_audio": {"data": audio_base64, "format": "ogg"}}
            ]
        else:
            content_parts = mensaje

        payload = {
            "model": "supervisor-agent",
            "messages": [{"role": "user", "content": content_parts}],
            "user": str(chat_id)
        }
        res = requests.post(ANTIGRAVITY_URL, json=payload, timeout=60)
        res.raise_for_status()
        
        respuesta = res.json().get("choices", [{}])[0].get("message", {}).get("content", "Sin respuesta del agente.")
        print(f"✅ Respuesta recibida del API ({len(respuesta)} chars)", flush=True)
        responder_a_telegram(chat_id, respuesta)
    except Exception as e:
        import traceback
        print(f"❌ Error en hilo async: {e}", flush=True)
        traceback.print_exc()
        responder_a_telegram(chat_id, "⚠️ Ocurrió un error al procesar tu solicitud con el Supervisor.")

def responder_a_telegram(chat_id, texto):
    if not BASE_URL:
        return
    
    # Telegram tiene un límite de 4096 caracteres por mensaje
    MAX_LEN = 4096
    partes = [texto[i:i+MAX_LEN] for i in range(0, len(texto), MAX_LEN)]
    
    url = f"{BASE_URL}/sendMessage"
    for parte in partes:
        payload = {
            "chat_id": chat_id,
            "text": parte,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            if not res.ok:
                # Retry sin Markdown si falla el formato
                payload.pop("parse_mode")
                res = requests.post(url, json=payload, timeout=10)
            print(f"📤 Enviado a Telegram ({len(parte)} chars) — status: {res.status_code}", flush=True)
        except Exception as e:
            print(f"❌ Error al enviar mensaje a Telegram: {e}", flush=True)

ALLOWED_CHAT_IDS = os.getenv("ALLOWED_CHAT_IDS", "").split(",")

@app.route("/webhook", methods=["POST"])
def webhook():
    datos = request.get_json()
    
    if not datos or "message" not in datos:
        return jsonify({"status": "ignored"}), 200
        
    chat_id = str(datos["message"]["chat"]["id"])
    
    # 1. Filtro y Validación de Grupo/Usuario (Lista Blanca) - Ejecutado primero por seguridad
    if not os.getenv("ALLOWED_CHAT_IDS"):
        print(f"⚠️ ALLOWED_CHAT_IDS no configurado. Recibido mensaje de Chat ID: {chat_id}", flush=True)
        responder_a_telegram(chat_id, f"⚠️ Tu Chat ID para la lista blanca es: `{chat_id}`. Configuralo en el .env como ALLOWED_CHAT_IDS={chat_id}")
    elif chat_id not in ALLOWED_CHAT_IDS:
        print(f"🚫 Acceso denegado: Mensaje ignorado de Chat ID no autorizado ({chat_id})")
        responder_a_telegram(chat_id, f"🚫 Acceso denegado. Tu Chat ID es `{chat_id}`. Agregalo a ALLOWED_CHAT_IDS en el .env separado por coma si querés acceso.")
        return jsonify({"status": "unauthorized"}), 200

    # Soporte de Documentos (PDFs de la PWA)
    if "document" in datos["message"]:
        doc = datos["message"]["document"]
        file_name = doc.get("file_name", "")
        if file_name.upper().startswith("MTZ_") and file_name.upper().endswith(".PDF"):
            file_id = doc["file_id"]
            dest_dir = "/home/cristian/Documentos/Supervisor/entrantes"
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, file_name)
            
            # Descargar y guardar en entrantes/
            success = descargar_documento_telegram(file_id, dest_path)
            if success:
                responder_a_telegram(chat_id, f"📥 *Reporte PDF Recibido:* `{file_name}`.\nEntrando en cola de procesamiento...")
                return jsonify({"status": "ok"}), 200
            else:
                responder_a_telegram(chat_id, f"⚠️ Error al descargar el archivo `{file_name}`. Por favor, reintenta.")
                return jsonify({"status": "error_descarga"}), 200

    mensaje = datos["message"].get("text", "")
    
    # Soporte de Audio / Voice Notes
    audio_base64 = None
    if "voice" in datos["message"]:
        file_id = datos["message"]["voice"]["file_id"]
        audio_base64 = descargar_audio_telegram(file_id)
    elif "audio" in datos["message"]:
        file_id = datos["message"]["audio"]["file_id"]
        audio_base64 = descargar_audio_telegram(file_id)
        
    if not mensaje and not audio_base64:
        # No es texto ni audio
        return jsonify({"status": "ignored"}), 200


    # 2. Procesamiento Asíncrono (Evita bloqueos de Telegram)
    hilo = threading.Thread(target=enviar_a_antigravity, args=(mensaje, chat_id, audio_base64))
    hilo.start()
    
    return jsonify({"status": "ok"}), 200

def set_webhook():
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if WEBHOOK_URL and BASE_URL:
        url = f"{BASE_URL}/setWebhook?url={WEBHOOK_URL}"
        try:
            res = requests.get(url, timeout=10)
            if res.json().get("ok"):
                print(f"🚀 Webhook configurado con éxito en: {WEBHOOK_URL}")
            else:
                print(f"❌ Error al configurar Webhook: {res.json()}")
        except Exception as e:
            print(f"❌ Error de red al hacer setWebhook: {e}")

if __name__ == "__main__":
    # Solo intentamos registrar el webhook si tenemos las variables necesarias
    if os.getenv("WEBHOOK_URL"):
        set_webhook()
    app.run(host="0.0.0.0", port=5000)
