import os
import time
import json
import shutil
import logging
import imaplib
import email
from email.header import decode_header
from pathlib import Path
import socket
import datetime
import re
import subprocess

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# Establecer timeout por defecto de 15 segundos para evitar cuelgues de red
socket.setdefaulttimeout(15)

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

# Importar los módulos que ya construimos
import notificador_telegram
import motor_supervisor
import fase3_sheets
import archivador_drive
import gestion_locales
import ingestor_formulario
import motor_whatsapp_web

# Configuración IMAP (Gmail)
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.getenv("GMAIL_USER", "usuario@gmail.com")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "password_de_aplicacion")

# Carpetas de trabajo
BASE_DIR = Path(__file__).parent
DIR_ENTRANTES = BASE_DIR / "entrantes"
DIR_PROCESADOS = BASE_DIR / "procesados"
DIR_ERRORES = BASE_DIR / "errores"

# Archivos de estado
WHATSAPP_STATE_FILE = BASE_DIR / "whatsapp_last_run.json"

# Asegurar que los directorios existen
for d in [DIR_ENTRANTES, DIR_PROCESADOS, DIR_ERRORES]:
    d.mkdir(exist_ok=True)

# URL de la Sábana en Google Sheets
SHEET_URL = os.getenv("SHEETS_SABANA_URL", "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing")

def descargar_adjuntos_gmail():
    """Se conecta por IMAP y descarga PDFs MTZ_ de correos no leídos."""
    if EMAIL_USER == "usuario@gmail.com" or EMAIL_PASS == "password_de_aplicacion":
        logger.warning("[IMAP] Gmail no configurado (GMAIL_USER y GMAIL_APP_PASSWORD no establecidas). Omitiendo descarga.")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=15)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        status, mensajes = mail.search(None, 'UNSEEN')
        if status != "OK" or not mensajes[0]:
            logger.info("[IMAP] No hay correos nuevos.")
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
                    logger.info(f"[IMAP] PDF Descargado exitosamente: {filename}")
                    pdf_descargado = True
            
            if not pdf_descargado:
                mail.store(num, '-FLAGS', '\\Seen')
                
        mail.logout()
    except Exception as e:
        logger.error(f"[ERROR IMAP] Falla al conectar o leer correos: {e}")

def procesar_carpeta_entrantes():
    """Lee la carpeta local, ejecuta el motor y sube a Sheets."""
    pdfs = list(DIR_ENTRANTES.glob("MTZ_*.pdf"))
    if not pdfs:
        logger.info("[ORQUESTADOR] No hay archivos PDF pendientes en la carpeta 'entrantes'.")
        return
        
    for pdf_path in pdfs:
        try:
            logger.info(f"--- [ORQUESTADOR] Iniciando {pdf_path.name} ---")
            
            import gestor_hashes
            es_dup, hash_val, info_reg = gestor_hashes.es_reporte_duplicado(pdf_path)
            if es_dup:
                origen_previo = info_reg.get("origen", "otro canal") if info_reg else "otro canal"
                logger.info(f"[SKIP-HASH-DUPLICATE] El archivo {pdf_path.name} ya fue procesado previamente vía {origen_previo}. Hash SHA-256: {hash_val[:10]}")
                if pdf_path.exists():
                    pdf_path.unlink()
                continue

            # 1. Fase 1 y 2 (Parser y Reglas) - Retorna ahora también el texto extraído
            datos_extraidos, alertas_negocio, texto_pdf = motor_supervisor.procesar_reporte(str(pdf_path))
            
            # 2. Fase 3 (Google Sheets)
            fase3_sheets.inyectar_en_sabana(datos_extraidos, alertas_negocio, SHEET_URL)
            
            sigla = datos_extraidos.get("sigla", "")
            
            # Registrar firma SHA-256
            gestor_hashes.registrar_reporte(str(pdf_path), origen="Gmail / Automático", sigla=sigla)
            if sigla:
                try:
                    import seguimiento_ppm
                    logger.info(f"   [SHEETS] Actualizando Sistema Hídrico en Agua Seguimiento para {sigla}...")
                    seguimiento_ppm.actualizar_datos_hidricos(sigla, datos_extraidos)
                except Exception as e_hidrico:
                    logger.error(f"   [!] Error actualizando Agua Seguimiento: {e_hidrico}")
            
            # 3. Archivar en Google Drive y autolimpieza
            exito_drive = False
            if sigla:
                exito_drive = archivador_drive.archivar_reporte_en_drive(str(pdf_path), sigla)
            
            if exito_drive:
                logger.info(f"[✓] Archivo subido a Google Drive y eliminado localmente.")
                
                # Actualizar ficha local re-usando el texto ya extraído (Eficiencia I/O)
                try:
                    estado_caf = ingestor_formulario.extraer_estado_cafetera(texto_pdf)
                    sn_match = re.search(r"SN:\s*(\w+)", texto_pdf)
                    
                    gestion_locales.actualizar_ficha_local(
                        sigla=sigla,
                        nombre_local=datos_extraidos.get("local", ""),
                        tecnico=datos_extraidos.get("tecnico", ""),
                        ticket=datos_extraidos.get("ticket", ""),
                        ppm=datos_extraidos.get("ppm", 0),
                        shots=datos_extraidos.get("shots", 0),
                        maquina=datos_extraidos.get("maquina", ""),
                        sn=sn_match.group(1) if sn_match else "",
                        estado_cafetera=estado_caf,
                        estado_general=alertas_negocio.get("estado_general", "VERDE_NORMAL"),
                        repuestos=datos_extraidos.get("repuestos", ""),
                        fecha_reporte=datos_extraidos.get("fecha", None)
                    )
                    
                    # Sincronización a NotebookLM
                    logger.info(f"[NOTEBOOKLM] Iniciando actualización en la nube para {sigla}...")
                    script_nlm = str(Path(__file__).parent / "actualizar_notebook_local.py")
                    subprocess.Popen(["python3", script_nlm, sigla])
                    
                except Exception as e_ficha:
                    logger.error(f"[ORQUESTADOR] Error al actualizar ficha local de {sigla}: {e_ficha}")
            else:
                msg_err = f"⚠️ [Ingestor] Alerta: No se pudo subir el archivo {pdf_path.name} a Google Drive (o no se detectó la sigla del local). Se movió a 'errores/' para resguardo manual."
                logger.warning(msg_err)
                notificador_telegram.enviar_alerta(msg_err)
                if pdf_path.exists():
                    shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))
            
        except Exception as e:
            msg_err = f"❌ [Ingestor] ERROR al procesar reporte {pdf_path.name}: {e}"
            logger.error(msg_err)
            notificador_telegram.enviar_alerta(msg_err)
            if pdf_path.exists():
                shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))

def deberia_ejecutar_whatsapp():
    """Verifica si pasaron 20 minutos usando persistencia de timestamp."""
    try:
        if WHATSAPP_STATE_FILE.exists():
            with open(WHATSAPP_STATE_FILE, "r") as f:
                data = json.load(f)
                ultimo_run = data.get("last_run_timestamp", 0)
        else:
            ultimo_run = 0
            
        ahora = time.time()
        # 20 minutos = 1200 segundos
        if (ahora - ultimo_run) >= 1200:
            return True
        return False
    except Exception as e:
        logger.error(f"Error verificando timestamp de WhatsApp: {e}")
        return True # Si falla la lectura, ejecutamos por seguridad

def actualizar_timestamp_whatsapp():
    try:
        with open(WHATSAPP_STATE_FILE, "w") as f:
            json.dump({"last_run_timestamp": time.time()}, f)
    except Exception as e:
        logger.error(f"Error guardando timestamp de WhatsApp: {e}")

if __name__ == "__main__":
    logger.info("=======================================")
    logger.info("Iniciando Ingestor Automático...")
    
    # 1. Ejecutar Ingestor de Formulario Google
    try:
        logger.info("--- Ejecutando Ingestor de Formulario Google ---")
        ingestor_formulario.ejecutar_ingesta_formulario()
    except Exception as e:
        logger.error(f"Falla en Ingestor de Formulario Google: {e}")
        
    # 2. Ejecutar Motor WhatsApp Web (Desactivado en cron para evitar conflictos con whatsapp-bridge.service)
    # El escaneo de WhatsApp se delega completamente al servicio del sistema.
    logger.info("--- Omitiendo Motor WhatsApp Web (Delegado a whatsapp-bridge.service) ---")

    # 3. Descargar correos de Gmail
    try:
        logger.info("--- Revisando Bandeja de Entrada de Gmail ---")
        descargar_adjuntos_gmail()
    except Exception as e:
        logger.error(f"Falla al revisar correos de Gmail: {e}")

    # 4. Procesar todos los archivos acumulados en /entrantes
    try:
        logger.info("--- Procesando Carpeta Entrantes ---")
        procesar_carpeta_entrantes()
    except Exception as e:
        logger.error(f"Falla al procesar carpeta de entrantes: {e}")
        
    logger.info("Ciclo finalizado.")
    logger.info("=======================================\n")
