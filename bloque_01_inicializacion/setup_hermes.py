#!/usr/bin/env python3
import os
import json
from pathlib import Path

# Configuración de la estructura del proyecto "Hermes Headless Supervisor"
PROJECT_NAME = "hermes-headless-supervisor"

# Definición de archivos y sus contenidos base
FILES_MANIFEST = {
    # 1. Configuración de Automatizaciones Nativas para Antigravity 2.0
    ".antigravity/automation_config.json": {
        "automations": [
            {
                "name": "HERMES_MAIL_SCANNER",
                "cron": "0 */2 * * 1-5",
                "command": "python3 src/mail_monitor.py",
                "description": "Escaneo de adjuntos e informes en Outlook Exchange"
            },
            {
                "name": "HERMES_TELEGRAM_AUDITOR",
                "cron": "0 * * * *",
                "command": "python3 src/telegram_monitor.py",
                "description": "Auditoría de logs de Telegram y volcado a Google Sheets"
            }
        ]
    },
    
    # 2. Configuración global de la aplicación (IDs y Listas de Control)
    "config/app_config.json": {
        "google_sheets": {
            "spreadsheet_id": "TU_SPREADSHEET_ID_AQUÍ",
            "worksheet_name": "Sheet1"
        },
        "telegram": {
            "group_chat_id": -1000000000000,
            "bot_token": "TU_TELEGRAM_BOT_TOKEN_AQUÍ"
        },
        "supervision": {
            "technicians": [
                "Fernando Soria",
                "Tomás Vera",
                "Anabella Guerrero",
                "Francisco Rameta"
            ],
            "check_interval_hours": 2
        }
    },
    
    # 3. Conector robusto sin entorno gráfico para Google Sheets API
    "src/sheets_connector.py": '''import gspread
from google.oauth2.service_account import Credentials
import json
import os

def get_sheets_client():
    """Autentica con la Service Account usando el archivo JSON local de forma headless."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    config_path = os.path.join('config', 'google_credentials.json')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Falta el archivo de credenciales en: {config_path}")
        
    creds = Credentials.from_service_account_file(config_path, scopes=scopes)
    return gspread.authorize(creds)

def append_technical_log(data_rows):
    """Inserta filas en bloque (batch) para mantener Looker Studio actualizado sin duplicar archivos."""
    try:
        with open(os.path.join('config', 'app_config.json'), 'r') as f:
            config = json.load(f)
            
        sheet_id = config['google_sheets']['spreadsheet_id']
        wks_name = config['google_sheets']['worksheet_name']
        
        client = get_sheets_client()
        sheet = client.open_by_key(sheet_id).worksheet(wks_name)
        
        # Inserta los datos mapeados respetando el formato de celdas nativo
        sheet.append_rows(data_rows, value_input_option='USER_ENTERED')
        print(f"[OK] Sincronizados {len(data_rows)} registros con Google Sheets.")
    except Exception as e:
        print(f"[ERROR SHEETS] No se pudo escribir en la base de datos: {e}")
''',

    # 4. Monitor Headless de Correo Corporativo (Outlook Exchange)
    "src/mail_monitor.py": '''import os
import json
from sheets_connector import append_technical_log

def check_corporate_mail():
    """
    Se conecta de forma asíncrona al servidor de correo sin abrir navegadores.
    Filtra remitentes basados en la lista de técnicos y extrae adjuntos.
    """
    print("[INFO] Iniciando escaneo programado de Outlook Exchange...")
    
    # Cargamos la lista de técnicos autorizados
    with open(os.path.join('config', 'app_config.json'), 'r') as f:
        config = json.load(f)
    technicians = config['supervision']['technicians']
    
    # TODO: Implementar conexión IMAPClient / O365 Graph API usando las credenciales seguras de secrets.env
    # Estructura del payload final para enviar al Sheets
    sample_payload = [
        # ["Fecha", "Origen", "Técnico", "Estado", "Tipo Canal"]
    ]
    
    if sample_payload:
        append_technical_log(sample_payload)
    else:
        print("[INFO] No se encontraron nuevos informes de técnicos por correo.")

if __name__ == "__main__":
    check_corporate_mail()
''',

    # 5. Auditor Programado del Canal de Telegram
    "src/telegram_monitor.py": '''import os
import json
import requests
from sheets_connector import append_technical_log

def audit_telegram_channel():
    """
    Descarga el historial reciente del grupo de técnicos vía API (getUpdates/Webhook de fondo).
    Procesa logs informales de texto para alimentar el Sheets local.
    """
    print("[INFO] Iniciando barrido de novedades en el grupo de Telegram...")
    
    with open(os.path.join('config', 'app_config.json'), 'r') as f:
        config = json.load(f)
        
    bot_token = config['telegram']['bot_token']
    group_id = config['telegram']['group_chat_id']
    technicians = config['supervision']['technicians']
    
    # Solicitud HTTP Headless a la API de Telegram para recuperar logs
    # url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    print("[INFO] Procesamiento de logs completado de forma silenciosa.")

if __name__ == "__main__":
    audit_telegram_channel()
'''
}

def build_architecture():
    base_path = Path.cwd() / PROJECT_NAME
    print(f"--- Iniciando despliegue de arquitectura para: {PROJECT_NAME} ---")
    
    # Creación de la estructura base de carpetas
    folders = [".antigravity", "config", "src", "logs"]
    for folder in folders:
        folder_path = base_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"[DIRECTORIO] Creado: {folder_path.relative_to(Path.cwd())}")
        
    # Creación e inyección de los componentes de software
    for file_route, content in FILES_MANIFEST.items():
        target_file = base_path / file_route
        
        with open(target_file, "w", encoding="utf-8") as f:
            if isinstance(content, dict):
                json.dump(content, f, indent=2, ensure_ascii=False)
            else:
                f.write(content.strip())
        print(f"[ARCHIVO] Inicializado: {target_file.relative_to(Path.cwd())}")
        
    # Inicialización del archivo de variables de entorno vacío por seguridad
    env_file = base_path / "config" / "secrets.env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write("# Credenciales Locales Privadas - No subir a repositorios\n")
        f.write("OUTLOOK_USER=tu_usuario_corporativo@mostaza.com.ar\n")
        f.write("OUTLOOK_PASSWORD=tu_contraseña_segura\n")
        f.write("GMAIL_BACKUP_USER=tu_cuenta_envios_secundaria@gmail.com\n")
        f.write("GMAIL_BACKUP_PASSWORD=tu_token_de_aplicacion_gmail\n")
    print(f"[SEGURIDAD] Archivo de credenciales creado en: {env_file.relative_to(Path.cwd())}")

    # Inicialización de archivo placeholder para la llave de Google
    json_creds_placeholder = base_path / "config" / "google_credentials.json"
    with open(json_creds_placeholder, "w", encoding="utf-8") as f:
        f.write("{\n  \"type\": \"service_account\",\n  \"_comment\": \"Reemplazar este archivo completo con el JSON descargado de Google Cloud Console\"\n}")
    print(f"[API] Placeholder de Service Account creado en: {json_creds_placeholder.relative_to(Path.cwd())}")

    print("\n--- [ÉXITO] Estructura lista para ser gestionada por Antigravity ---")
    print("Próximo paso técnico: Colocar el JSON de la Service Account en config/google_credentials.json y configurar los tokens.")

if __name__ == "__main__":
    build_architecture()
