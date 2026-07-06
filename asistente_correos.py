import os
import sys
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import sqlite3
import datetime
from pathlib import Path
import google.generativeai as genai
import re

BASE_DIR = Path("/home/cristian/PROYECTOS/Supervisor-Project")
sys.path.append(str(BASE_DIR))
import notificador_telegram

def cargar_env():
    ruta_env = BASE_DIR / ".env"
    if ruta_env.exists():
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                os.environ[k.strip()] = v.strip()

cargar_env()

IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.getenv("GMAIL_USER")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

DB_PATH = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")

def obtener_locales():
    locales = []
    base_locales = Path("/home/cristian/PROYECTOS/Supervisor-Project/brain/locales")
    if base_locales.exists():
        for f in base_locales.glob("*.md"):
            sigla = f.stem
            # We don't have the full name, just use the sigla as name
            locales.append({"sigla": sigla, "nombre": f"Local {sigla}"})
    return locales

def parse_header(header_text):
    if not header_text: return ""
    decoded = decode_header(header_text)
    res = ""
    for frag, enc in decoded:
        if isinstance(frag, bytes):
            res += frag.decode(enc or 'utf-8', errors='ignore')
        else:
            res += str(frag)
    return res

def extraer_cuerpo(msg):
    cuerpo = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    cuerpo += part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            cuerpo = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        except:
            pass
    return cuerpo.strip()

def procesar_con_ia(asunto, remitente, cuerpo, locales):
    import llm_fallback
    
    locales_str = "\n".join([f"- {l['sigla']}: {l['nombre']}" for l in locales])
    prompt = f"""Analiza el siguiente correo electrónico:
Asunto: {asunto}
Remitente: {remitente}
Cuerpo:
{cuerpo}

1. Identifica si este correo habla sobre un local en particular de la siguiente lista:
{locales_str}
2. Escribe un resumen breve y profesional del correo (máximo 3 oraciones).

Responde EXACTAMENTE con este formato, sin markdown ni comillas:
SIGLA: [SIGLA_DEL_LOCAL o "GENERAL" si no aplica ninguno]
RESUMEN: [Tu resumen aquí]
"""
    try:
        response_text = llm_fallback.generar_texto(prompt)
        sigla = "GENERAL"
        resumen = "Resumen no disponible"
        
        for line in response_text.split('\n'):
            if line.startswith("SIGLA:"):
                sigla = line.replace("SIGLA:", "").strip()
            elif line.startswith("RESUMEN:"):
                resumen = line.replace("RESUMEN:", "").strip()
                
        # Validar sigla
        if sigla != "GENERAL" and not any(l['sigla'] == sigla for l in locales):
            sigla = "GENERAL"
            
        return sigla, resumen
    except Exception as e:
        print(f"Error IA: {e}")
        return "GENERAL", "Error al procesar con IA."

def guardar_archivo_local(sigla, asunto, remitente, fecha, cuerpo):
    if sigla == "GENERAL":
        return
        
    # Guardar en Documentos/Supervisor/Locales/[SIGLA]/Reportes
    base_locales = Path("/home/cristian/Documentos/Supervisor/Locales")
    carpeta_local = None
    if base_locales.exists():
        for d in base_locales.iterdir():
            if d.is_dir() and f"[{sigla}]" in d.name:
                carpeta_local = d
                break
                
    if carpeta_local:
        carpeta_reportes = carpeta_local / "Reportes"
        carpeta_reportes.mkdir(exist_ok=True)
        
        safe_asunto = re.sub(r'[^a-zA-Z0-9_\- ]', '', asunto).strip()[:30].replace(" ", "_")
        fecha_str = fecha.strftime("%Y%m%d_%H%M%S")
        filename = f"Correo_{fecha_str}_{safe_asunto}.md"
        
        filepath = carpeta_reportes / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Correo: {asunto}\n")
            f.write(f"**Fecha:** {fecha}\n")
            f.write(f"**De:** {remitente}\n\n")
            f.write(cuerpo)
        print(f"Guardado en {filepath}")

def main():
    print(f"=== Iniciando Asistente de Correos ({datetime.datetime.now()}) ===")
    if not EMAIL_USER or not EMAIL_PASS:
        print("Credenciales IMAP no configuradas.")
        return
        
    locales = obtener_locales()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=30)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Buscar correos no leídos
        status, mensajes = mail.search(None, 'UNSEEN')
        if status != "OK" or not mensajes[0]:
            print("No hay correos nuevos.")
            mail.logout()
            return
            
        for num in mensajes[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            if status != "OK": continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Obtener Message-ID
            message_id = msg.get("Message-ID", f"no-id-{datetime.datetime.now().timestamp()}")
            
            # Verificar si ya existe en la DB
            c.execute("SELECT id FROM correos WHERE message_id = ?", (message_id,))
            if c.fetchone():
                continue # Ya procesado
                
            asunto = parse_header(msg.get("Subject"))
            remitente = parse_header(msg.get("From"))
            destinatarios = parse_header(msg.get("To"))
            fecha_str = msg.get("Date")
            try:
                fecha_obj = parsedate_to_datetime(fecha_str) if fecha_str else datetime.datetime.now()
            except:
                fecha_obj = datetime.datetime.now()
                
            cuerpo = extraer_cuerpo(msg)
            
            # Ignorar correos puramente adjuntos sin texto real
            if not cuerpo or len(cuerpo.strip()) < 10:
                print(f"Correo {asunto} ignorado (Sin texto suficiente).")
                # Si tiene PDF MTZ, se encarga ingestor_automatico
                mail.store(num, '-FLAGS', '\\Seen')
                continue
            
            print(f"Procesando correo: {asunto}")
            sigla, resumen = procesar_con_ia(asunto, remitente, cuerpo, locales)
            
            # Guardar en DB
            c.execute('''INSERT INTO correos 
                        (message_id, remitente, destinatarios, asunto, fecha, cuerpo, sigla_local, resumen) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                      (message_id, remitente, destinatarios, asunto, fecha_obj, cuerpo, sigla, resumen))
            conn.commit()
            
            # Guardar archivo en carpeta
            guardar_archivo_local(sigla, asunto, remitente, fecha_obj, cuerpo)
            
            # Enviar notificación a Telegram
            tag = f"[{sigla}]" if sigla != "GENERAL" else "[General]"
            mensaje_tg = f"📧 *NUEVO CORREO RECIBIDO* {tag}\n"
            mensaje_tg += f"👤 *De:* {remitente}\n"
            mensaje_tg += f"📌 *Asunto:* {asunto}\n\n"
            mensaje_tg += f"🤖 *Resumen:* _{resumen}_"
            
            # Enviar notificación a Telegram (Chat Privado por defecto)
            notificador_telegram.enviar_alerta(mensaje_tg, agente="Hermes")
            
            # Marcar como leído
            mail.store(num, '+FLAGS', '\\Seen')
            
        mail.logout()
    except Exception as e:
        print(f"Error procesando correos: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
