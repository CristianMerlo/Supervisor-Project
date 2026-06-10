import urllib.request
import urllib.parse

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
