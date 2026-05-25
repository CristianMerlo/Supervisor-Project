# Paquete de Despliegue: Paso A (Pipeline de Ingesta Automática)

**Instrucciones para el Antigravity de la máquina destino:**
Hola equipo. Excelente trabajo implementando la Sábana. Ahora vamos a dotar al sistema de sus "ojos" para atrapar los reportes automáticamente, tanto desde Gmail como desde Telegram.

A continuación te paso los dos módulos necesarios para completar el **Paso A**.

---

## 1. PASO PREVIO: Interacción Humana (Contraseña de Aplicación Gmail)
Pídele al usuario (Cristian) que realice estos pasos en el navegador para autorizar la lectura de correos IMAP sin comprometer la contraseña principal del supervisor:

1. Ingresar a la **Cuenta de Google** del correo del supervisor (Abre gmail.com, clic en la foto de perfil -> "Administrar tu cuenta de Google").
2. En el menú de la izquierda, seleccionar la pestaña **"Seguridad"**.
3. Buscar la sección *"Cómo accedes a Google"* y asegurarse de que la **Verificación en dos pasos** esté **Activada** (es requisito obligatorio).
4. Hacer clic en **"Verificación en dos pasos"**. Bajar hasta el final de la página y buscar **"Contraseñas de aplicación"** (App Passwords).
5. En el campo "Nombre de la aplicación", escribir `Antigravity-Ingestor` y hacer clic en **Crear**.
6. Google generará una **contraseña de 16 letras** en un recuadro amarillo. Cópiala y dale a "Hecho".
7. (Para Antigravity): Configura esa contraseña de 16 letras como variable de entorno `GMAIL_APP_PASSWORD` y el correo como `GMAIL_USER` en tu servidor Ubuntu.

---

## 2. Módulo Recolector IMAP y Orquestador (`ingestor_automatico.py`)

Crea el archivo `ingestor_automatico.py` en el mismo directorio donde tienes `motor_supervisor.py` y `fase3_sheets.py`. Este script es el que configurarás en tu Cron Job (`schedule` cada 5 minutos).

```python
import os
import time
import imaplib
import email
from email.header import decode_header
import shutil
from pathlib import Path

# Importar los módulos que ya construimos
import motor_supervisor
import fase3_sheets

# Configuración IMAP (Gmail)
IMAP_SERVER = "imap.gmail.com"
# El usuario debe configurar estas variables de entorno en el SO
EMAIL_USER = os.getenv("GMAIL_USER", "usuario@gmail.com")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "password_de_aplicacion")

# Carpetas de trabajo
DIR_ENTRANTES = Path("entrantes")
DIR_PROCESADOS = Path("procesados")
DIR_ERRORES = Path("errores")

# Asegurar que los directorios existen
for d in [DIR_ENTRANTES, DIR_PROCESADOS, DIR_ERRORES]:
    d.mkdir(exist_ok=True)

# URL de la Sábana en Google Sheets
SHEET_URL = os.getenv("SHEETS_SABANA_URL", "PEGAR_AQUI_LA_URL_DE_LA_SABANA")

def descargar_adjuntos_gmail():
    """Se conecta por IMAP y descarga PDFs MTZ_ de correos no leídos."""
    try:
        # Conexión al servidor IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
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
        return
        
    for pdf_path in pdfs:
        try:
            print(f"\\n--- [ORQUESTADOR] Iniciando {pdf_path.name} ---")
            # 1. Fase 1 y 2 (Parser y Reglas)
            datos_extraidos, alertas_negocio = motor_supervisor.procesar_reporte(str(pdf_path))
            
            # 2. Fase 3 (Google Sheets)
            fase3_sheets.inyectar_en_sabana(datos_extraidos, alertas_negocio, SHEET_URL)
            
            # 3. Mover a procesados
            shutil.move(str(pdf_path), str(DIR_PROCESADOS / pdf_path.name))
            print(f"[✓] Archivo movido a procesados.")
            
        except Exception as e:
            print(f"[ERROR] Falla al procesar {pdf_path.name}: {e}")
            shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))

if __name__ == "__main__":
    print("Iniciando Ingestor Automático...")
    descargar_adjuntos_gmail()
    procesar_carpeta_entrantes()
    print("Ciclo finalizado.")
```

---

## 2. Instrucciones de Integración para Telegram (`app.py`)

Para que la ingesta vía Telegram funcione, solo tienes que ir al script que maneja el webhook del bot (`app.py` en el servidor local) y agregar la lógica de descarga en el manejador de documentos.

**Modificación requerida en `app.py`:**
Cuando el webhook reciba una actualización tipo `document`, debes descargar el archivo y **guardarlo directamente en la carpeta `entrantes/`**.
De esta manera, el bot de Telegram hace de simple recolector, y deja el trabajo pesado al `ingestor_automatico.py` (que pasa por la carpeta cada 5 minutos).

Ejemplo conceptual para el código de Telegram:
```python
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    if 'message' in update and 'document' in update['message']:
        document = update['message']['document']
        file_name = document.get('file_name', '')
        
        # Filtro de seguridad
        if file_name.upper().startswith("MTZ_") and file_name.upper().endswith(".PDF"):
            file_id = document['file_id']
            # Lógica típica de telegram para descargar el archivo
            file_path = descargar_archivo_telegram(file_id) 
            
            # Guardarlo en la carpeta compartida
            destino = os.path.join("entrantes", file_name)
            os.rename(file_path, destino)
            
            enviar_mensaje_telegram(chat_id, "PDF Recibido. Entrando en cola de procesamiento...")
    # ... resto del código ...
```

**Conclusión:**
Pide al usuario que genere una "App Password" de 16 dígitos en su Gmail (Buscando "Contraseñas de aplicación" en su cuenta de Google) y configura las variables de entorno. Luego de eso, programa el cronjob para `ingestor_automatico.py`. ¡Éxitos!
