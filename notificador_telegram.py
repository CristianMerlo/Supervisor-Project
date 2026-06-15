import urllib.request
import urllib.parse
import time
import uuid
import requests

def enviar_alerta(mensaje, agente="Antigravity"):
    """Envía un mensaje de alerta a Telegram a través del Userbot local."""
    if any(tag in mensaje for tag in ["[Hermes]", "[Goose]", "[Antigravity]"]):
        pass
    else:
        # Reemplazar tags antiguos si existen
        if "[Antigravity]" in mensaje:
            mensaje = mensaje.replace("[Antigravity]", "").strip()
            mensaje = f"🛠️ [Antigravity] {mensaje}"
        elif "[Supervisor]" in mensaje:
            mensaje = mensaje.replace("[Supervisor]", "").strip()
            mensaje = f"🧠 [Hermes] {mensaje}"
        else:
            if agente == "Hermes":
                mensaje = f"🧠 [Hermes] {mensaje}"
            elif agente == "Goose":
                mensaje = f"🪿 [Goose] {mensaje}"
            else:
                mensaje = f"🛠️ [Antigravity] {mensaje}"
    url = "http://127.0.0.1:8088/notify"
    try:
        data = mensaje.encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "text/plain; charset=utf-8"},
            method="POST"
        )
        # Timeout de 5 segundos para evitar bloquear la ejecución si el listener estuviera inactivo
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"[TELEGRAM] Alerta enviada con éxito: {mensaje[:60]}...")
                return True
            else:
                print(f"[TELEGRAM] Error al enviar alerta. Status: {response.status}")
    except Exception as e:
        print(f"[TELEGRAM] No se pudo enviar alerta a Telegram: {e}")
    return False

def solicitar_aprobacion(mensaje, timeout=3600):
    """
    Solicita aprobación interactiva a través de botones en Telegram.
    Espera de forma síncrona hasta recibir 'approved', 'rejected' o alcanzar el timeout.
    """
    if "[Antigravity]" not in mensaje and "[Hermes]" not in mensaje:
        mensaje = f"🛠️ [Antigravity] {mensaje}"
        
    req_id = str(uuid.uuid4())[:8]
    url_ask = "http://127.0.0.1:8088/ask_approval"
    payload = {
        "message": mensaje,
        "request_id": req_id
    }
    
    try:
        res = requests.post(url_ask, json=payload, timeout=10)
        res.raise_for_status()
        print(f"[TELEGRAM] Solicitud de aprobación enviada (ID: {req_id})")
    except Exception as e:
        print(f"[TELEGRAM] Error al solicitar aprobación: {e}")
        return "error"
        
    url_check = f"http://127.0.0.1:8088/check_approval/{req_id}"
    inicio = time.time()
    
    print("[TELEGRAM] Esperando decisión del usuario...")
    while time.time() - inicio < timeout:
        try:
            check_res = requests.get(url_check, timeout=5)
            if check_res.status_code == 200:
                data = check_res.json()
                status = data.get("status")
                if status in ["approved", "rejected"]:
                    print(f"[TELEGRAM] Decisión recibida: {status.upper()}")
                    return status
        except Exception:
            pass
        time.sleep(3) # Polling cada 3 segundos
        
    print("[TELEGRAM] Timeout esperando aprobación.")
    return "timeout"
