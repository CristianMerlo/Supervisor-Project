import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

BASE_DIR = Path(__file__).parent

def cargar_env():
    ruta_env = BASE_DIR / ".env"
    env_vars = {}
    if ruta_env.exists():
        with open(ruta_env, "r") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars

def enviar_correo(asunto, cuerpo_texto):
    """Envía un correo de alerta usando las credenciales de Gmail en .env."""
    env = cargar_env()
    gmail_user = env.get("GMAIL_USER")
    gmail_pass = env.get("GMAIL_APP_PASSWORD")
    destinatario = env.get("CORREO_CORPORATIVO", gmail_user) # Enviar a correo corporativo o a sí mismo

    if not gmail_user or not gmail_pass:
        print("[MAIL] No se puede enviar correo: GMAIL_USER o GMAIL_APP_PASSWORD no configurados.")
        return False

    try:
        if "[Antigravity]" not in asunto and "[Supervisor]" not in asunto and "Antigravity" not in asunto:
            asunto = f"[Antigravity] {asunto}"
            
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = destinatario
        msg['Subject'] = asunto

        msg.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))

        # Conectar a Gmail SMTP por puerto 587 con STARTTLS
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, destinatario, msg.as_string())
        server.quit()
        print(f"[MAIL] Correo enviado con éxito a {destinatario}.")
        return True
    except Exception as e:
        print(f"[MAIL] Error enviando correo: {e}")
        return False
