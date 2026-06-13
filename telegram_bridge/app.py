import os
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTIGRAVITY_URL = os.getenv("ANTIGRAVITY_API_URL", "http://localhost:8000/v1/chat/completions")
MAIN_GROUP_ID = os.getenv("MAIN_GROUP_ID")

import base64
import json

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else ""
STATE_FILE = "/home/cristian/Documentos/Supervisor/telegram_bridge/bridge_state.json"

def cargar_estado():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando estado: {e}")
    return {}

def guardar_estado(estado):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(estado, f)
    except Exception as e:
        print(f"Error guardando estado: {e}")

def limpiar_estado():
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception as e:
            print(f"Error eliminando estado: {e}")

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

def transcribir_y_guardar_imagen(image_path, md_path):
    try:
        import requests
        with open(image_path, "rb") as img_file:
            files = {"file": (os.path.basename(image_path), img_file, "image/jpeg")}
            res = requests.post("http://localhost:8000/v1/transcribe", files=files, timeout=90)
            if res.status_code == 200:
                markdown_content = res.json().get("markdown", "")
                if markdown_content:
                    with open(md_path, "w", encoding="utf-8") as md_file:
                        md_file.write(markdown_content)
                    print(f"✅ Transcripción guardada exitosamente en {md_path}")
                else:
                    print("⚠️ La API de transcripción devolvió contenido vacío.")
            else:
                print(f"❌ La API de transcripción devolvió status: {res.status_code}")
    except Exception as e:
        print(f"❌ Error transcribiendo imagen en segundo plano: {e}")

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

    # Cargar estado actual de la conversación
    estado = cargar_estado()

    # Interceptar respuesta de texto si hay un flujo interactivo activo para este chat
    mensaje = datos["message"].get("text", "")
    
    if estado.get("chat_id") == chat_id and mensaje:
        status = estado.get("status")
        files = estado.get("files", [])
        
        if status == "waiting_manual_confirm":
            respuesta_clean = mensaje.lower().strip()
            if respuesta_clean.startswith("s") or respuesta_clean in ["yes", "ok", "bueno", "dale"]:
                # Cambiar de estado y pedir el nombre del equipo
                estado["status"] = "waiting_equipment_name"
                guardar_estado(estado)
                responder_a_telegram(chat_id, f"☕ *¿Cómo le llaman regularmente a este equipo o máquina en el día a día?* (Ej: Cafetera Iberital, Molino Compak, Termotanque)\n\n*(Se aplicará a los {len(files)} archivos cargados)*")
                return jsonify({"status": "ok"}), 200
            elif respuesta_clean.startswith("n") or respuesta_clean in ["no", "cancelar", "cancela"]:
                # Eliminar archivos temporales y limpiar estado
                for f in files:
                    temp_path = f.get("temp_path")
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                limpiar_estado()
                responder_a_telegram(chat_id, f"❌ Operación cancelada. Se descartó el lote de {len(files)} archivos.")
                return jsonify({"status": "ok"}), 200
            else:
                nombres = ", ".join([f"`{f['file_name']}`" for f in files])
                responder_a_telegram(chat_id, f"Por favor, responde con *Sí* o *No* para confirmar si el lote de archivos ({nombres}) son manuales.")
                return jsonify({"status": "ok"}), 200
                
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
                    except Exception as e:
                        print(f"Error moviendo archivo {f_name}: {e}")
                        fallidos.append(f_name)
                else:
                    fallidos.append(f_name)
                    
            limpiar_estado()
            
            if exitosos:
                archivos_str = "\n".join([f"• `{name}`" for name in exitosos])
                msg = f"✅ *Manuales guardados y clasificados con éxito*:\n• *Equipo:* `{equipo}`\n• *Archivos clasificados:*\n{archivos_str}"
                if fallidos:
                    msg += f"\n\n⚠️ No se pudieron mover: {', '.join(fallidos)}"
                responder_a_telegram(chat_id, msg)
            else:
                responder_a_telegram(chat_id, "⚠️ Ocurrió un error al intentar mover los archivos del lote.")
            return jsonify({"status": "ok"}), 200

    # Soporte de Fotos (Imágenes de Telegram comprimidas)
    is_photo = "photo" in datos["message"]
    is_doc = "document" in datos["message"]
    
    if is_photo or is_doc:
        if is_photo:
            photos = datos["message"]["photo"]
            photo = photos[-1]  # La de mayor tamaño
            file_id = photo["file_id"]
            file_name = f"foto_{file_id[-8:]}.jpg"
        else:
            doc = datos["message"]["document"]
            file_name = doc.get("file_name", "")
            file_id = doc["file_id"]
            
            # Si es un reporte estándar de Mostaza
            if file_name.upper().startswith("MTZ_") and file_name.upper().endswith(".PDF"):
                dest_dir = "/home/cristian/Documentos/Supervisor/entrantes"
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, file_name)
                
                success = descargar_documento_telegram(file_id, dest_path)
                if success:
                    responder_a_telegram(chat_id, f"📥 *Reporte PDF Recibido:* `{file_name}`.\nEntrando en cola de procesamiento...")
                    return jsonify({"status": "ok"}), 200
                else:
                    responder_a_telegram(chat_id, f"⚠️ Error al descargar el archivo `{file_name}`. Por favor, reintenta.")
                    return jsonify({"status": "error_descarga"}), 200

        # Es un manual potencial (documento no estándar o foto/imagen)
        temp_dir = "/tmp/tg_manuals_temp"
        os.makedirs(temp_dir, exist_ok=True)
        dest_path = os.path.join(temp_dir, file_name)
        
        success = descargar_documento_telegram(file_id, dest_path)
        if success:
            is_image = is_photo or file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))
            tipo_desc = "la imagen" if is_image else "el documento"
            
            # Si ya hay un lote en curso esperando confirmación
            if estado.get("chat_id") == chat_id and estado.get("status") == "waiting_manual_confirm":
                if "files" not in estado:
                    estado["files"] = []
                estado["files"].append({
                    "temp_path": dest_path,
                    "file_name": file_name
                })
                guardar_estado(estado)
                responder_a_telegram(chat_id, f"📥 Agregado `{file_name}` al lote actual (Total: {len(estado['files'])} archivos).\n¿Se trata de manuales técnicos para el sistema? Responde con *Sí* o *No*.")
            else:
                # Iniciar nuevo lote
                nuevo_estado = {
                    "chat_id": chat_id,
                    "status": "waiting_manual_confirm",
                    "files": [{
                        "temp_path": dest_path,
                        "file_name": file_name
                    }]
                }
                guardar_estado(nuevo_estado)
                responder_a_telegram(chat_id, f"📥 He recibido {tipo_desc} `{file_name}`.\n¿Se trata de un manual técnico para el sistema? Responde con *Sí* o *No*.")
            return jsonify({"status": "ok"}), 200
        else:
            responder_a_telegram(chat_id, f"⚠️ Error al descargar `{file_name}`. Por favor, reintenta.")
            return jsonify({"status": "error_descarga"}), 200

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
