import os
import time
import imaplib
import email
from email.header import decode_header
import shutil
from pathlib import Path
import socket
import notificador_telegram

# Establecer timeout por defecto de 15 segundos para evitar cuelgues de red
socket.setdefaulttimeout(15)

# Importar los módulos que ya construimos
import motor_supervisor
import fase3_sheets
import archivador_drive
import motor_whatsapp_web
import motor_outlook_web


# Carga de variables de entorno locales desde archivo .env si existe
def cargar_env():
    ruta_env = Path(__file__).parent / ".env"
    if ruta_env.exists():
        with open(ruta_env, "r") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                os.environ[k.strip()] = v.strip()

cargar_env()

# Configuración IMAP (Gmail)
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.getenv("GMAIL_USER", "usuario@gmail.com")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "password_de_aplicacion")

# Carpetas de trabajo
BASE_DIR = Path(__file__).parent
DIR_ENTRANTES = BASE_DIR / "entrantes"
DIR_PROCESADOS = BASE_DIR / "procesados"
DIR_ERRORES = BASE_DIR / "errores"

# Asegurar que los directorios existen
for d in [DIR_ENTRANTES, DIR_PROCESADOS, DIR_ERRORES]:
    d.mkdir(exist_ok=True)

# URL de la Sábana en Google Sheets
SHEET_URL = os.getenv("SHEETS_SABANA_URL", "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing")

def descargar_adjuntos_gmail():
    """Se conecta por IMAP y descarga PDFs MTZ_ de correos no leídos."""
    # Si no se configuraron las variables, omitimos para evitar fallos continuos de login
    if EMAIL_USER == "usuario@gmail.com" or EMAIL_PASS == "password_de_aplicacion":
        print("[IMAP] Gmail no configurado (GMAIL_USER y GMAIL_APP_PASSWORD no establecidas). Omitiendo descarga.")
        return

    try:
        # Conexión al servidor IMAP con timeout de 15 segundos
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=15)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Buscar correos no leídos
        status, mensajes = mail.search(None, 'UNSEEN')
        if status != "OK" or not mensajes[0]:
            print("[IMAP] No hay correos nuevos.")
            return

        for num in mensajes[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            if status != "OK":
                continue
                
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            pdf_descargado = False
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename and filename.upper().startswith("MTZ_") and filename.upper().endswith(".PDF"):
                    filepath = DIR_ENTRANTES / filename
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    print(f"[IMAP] PDF Descargado: {filename}")
                    pdf_descargado = True
            
            # Si no descargó un PDF de este correo, lo vuelve a marcar como no leído para evitar perder correos importantes
            if not pdf_descargado:
                mail.store(num, '-FLAGS', '\\Seen')
                
        mail.logout()
    except Exception as e:
        print(f"[ERROR IMAP] Falla al conectar o leer correos: {e}")

def procesar_carpeta_entrantes():
    """Lee la carpeta local, ejecuta el motor y sube a Sheets."""
    pdfs = list(DIR_ENTRANTES.glob("MTZ_*.pdf"))
    if not pdfs:
        print("[ORQUESTADOR] No hay archivos PDF pendientes en la carpeta 'entrantes'.")
        return
        
    for pdf_path in pdfs:
        try:
            print(f"\n--- [ORQUESTADOR] Iniciando {pdf_path.name} ---")
            # 1. Fase 1 y 2 (Parser y Reglas)
            datos_extraidos, alertas_negocio = motor_supervisor.procesar_reporte(str(pdf_path))
            
            # 2. Fase 3 (Google Sheets)
            fase3_sheets.inyectar_en_sabana(datos_extraidos, alertas_negocio, SHEET_URL)
            
            # 3. Archivar en Google Drive y autolimpieza (Paso B.1)
            sigla = datos_extraidos.get("sigla", "")
            exito_drive = False
            if sigla:
                exito_drive = archivador_drive.archivar_reporte_en_drive(str(pdf_path), sigla)
            
            if exito_drive:
                print(f"[✓] Archivo subido a Google Drive y eliminado localmente.")
            else:
                msg_err = f"⚠️ [Ingestor] Alerta: No se pudo subir el archivo {pdf_path.name} a Google Drive (o no se detectó la sigla del local). Se movió a 'errores/' para resguardo manual."
                print(msg_err)
                notificador_telegram.enviar_alerta(msg_err)
                # Asegurar que el archivo de origen sigue existiendo antes de moverlo
                if pdf_path.exists():
                    shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))
            
        except Exception as e:
            msg_err = f"❌ [Ingestor] ERROR al procesar reporte {pdf_path.name}: {e}"
            print(msg_err)
            notificador_telegram.enviar_alerta(msg_err)
            if pdf_path.exists():
                shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))

if __name__ == "__main__":
    print("Iniciando Ingestor Automático...")
    
    try:
        print("\n--- Ejecutando IMAP (Gmail) ---")
        descargar_adjuntos_gmail()
    except Exception as e:
        print(f"[ERROR] Falla en motor IMAP Gmail: {e}")
        
    try:
        print("\n--- Ejecutando Motor WhatsApp Web ---")
        motor_whatsapp_web.ejecutar_motor()
    except Exception as e:
        print(f"[ERROR] Falla en Motor WhatsApp Web: {e}")
        
    try:
        print("\n--- Ejecutando Motor Outlook Web ---")
        motor_outlook_web.ejecutar_scraping_outlook()
    except Exception as e:
        print(f"[ERROR] Falla en Motor Outlook Web: {e}")
        
    try:
        print("\n--- Procesando Carpeta Entrantes ---")
        procesar_carpeta_entrantes()
    except Exception as e:
        print(f"[ERROR] Falla al procesar carpeta de entrantes: {e}")
        
    print("\nCiclo finalizado.")
