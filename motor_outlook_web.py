import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
CORREO_CORPORATIVO = os.getenv("CORREO_CORPORATIVO")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
AGENDAS_DIR = os.path.join(PROJECT_ROOT, "agendas_contactos")
PERFIL_FILE = os.path.join(PROJECT_ROOT, "perfil_respuestas_cristian.md")

# Asegurar que el directorio exista
os.makedirs(AGENDAS_DIR, exist_ok=True)

# -------------------------------------------------------------
# 1. HERRAMIENTAS DE CONOCIMIENTO (AGENDA Y PERFIL)
# -------------------------------------------------------------

def leer_perfil():
    try:
        with open(PERFIL_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Responde de forma clara y directa."

def leer_agenda_contacto(remitente):
    nombre_archivo = remitente.replace(" ", "_").replace("<", "").replace(">", "").replace("@", "_") + ".md"
    ruta = os.path.join(AGENDAS_DIR, nombre_archivo)
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    return "No hay historial previo con este contacto."

def guardar_agenda_contacto(remitente, nuevo_contenido):
    nombre_archivo = remitente.replace(" ", "_").replace("<", "").replace(">", "").replace("@", "_") + ".md"
    ruta = os.path.join(AGENDAS_DIR, nombre_archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

# -------------------------------------------------------------
# 2. IA Y GENERACIÓN DE BORRADORES
# -------------------------------------------------------------

def procesar_con_ia(remitente, asunto, cuerpo):
    agenda_actual = leer_agenda_contacto(remitente)
    perfil = leer_perfil()
    
    prompt = f"""
Actúas como Cristian, un Supervisor Técnico y Operativo. Acabas de leer el siguiente correo.

-- DATOS DEL CORREO --
Remitente: {remitente}
Asunto: {asunto}
Mensaje: {cuerpo}

-- CONTEXTO PREVIO (AGENDA DE ESTE CONTACTO) --
{agenda_actual}

-- TU ESTILO DE ESCRITURA --
{perfil}

TAREA:
1. Evalúa si el correo requiere una respuesta tuya o si es solo informativo/ruido. (Responde: ESTADO: RELEVANTE o RUIDO).
2. Si es RELEVANTE, redacta una propuesta de respuesta imitando tu estilo exacto. (Si no es relevante, pon N/A).
3. Genera un nuevo resumen actualizado para la Mini-Agenda con esta persona (ej. qué tema quedó abierto, qué se respondió).

FORMATO EXACTO DE SALIDA (sin markdown envolvente extra, solo texto):
ESTADO: [RELEVANTE/RUIDO]
BORRADOR_SUGERIDO: 
[Tu texto aquí]
FIN_BORRADOR
NUEVA_AGENDA:
[Resumen histórico actualizado]
"""
    try:
        response = model.generate_content(prompt)
        texto = response.text
        
        es_relevante = "ESTADO: RELEVANTE" in texto.upper()
        
        borrador = ""
        nueva_agenda = ""
        
        if "BORRADOR_SUGERIDO:" in texto and "FIN_BORRADOR" in texto:
            borrador = texto.split("BORRADOR_SUGERIDO:")[1].split("FIN_BORRADOR")[0].strip()
            
        if "NUEVA_AGENDA:" in texto:
            nueva_agenda = texto.split("NUEVA_AGENDA:")[1].strip()
            
        return es_relevante, borrador, nueva_agenda
        
    except Exception as e:
        print(f"❌ Error con la API de Gemini: {e}")
        return False, "", ""

# -------------------------------------------------------------
# 3. ENVÍO DE CORREO A CORPORATIVO Y TELEGRAM
# -------------------------------------------------------------

def enviar_borrador_corporativo(remitente, asunto, cuerpo_original, borrador, agenda_resumen):
    if not CORREO_CORPORATIVO or not GMAIL_USER:
        print("❌ Faltan credenciales SMTP en el archivo .env")
        return False
        
    mensaje = MIMEMultipart()
    mensaje['From'] = GMAIL_USER
    mensaje['To'] = CORREO_CORPORATIVO
    mensaje['Subject'] = f"[Borrador Supervisor] Re: {asunto}"
    
    cuerpo = f"""
==== ASISTENTE DE SUPERVISIÓN ====
Remitente Original: {remitente}
Asunto: {asunto}

[CONTEXTO DE AGENDA]
{agenda_resumen}

---------------------------------------------------
🤖 BORRADOR PROPUESTO PARA ENVIAR (Copia y pega):
---------------------------------------------------
{borrador}

---------------------------------------------------
CORREO ORIGINAL RECIENTE:
{cuerpo_original[:1000]}...
"""
    mensaje.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(mensaje)
        server.quit()
        print(f"📧 Borrador reenviado a tu cuenta corporativa: {CORREO_CORPORATIVO}")
        return True
    except Exception as e:
        print(f"❌ Error SMTP: {e}")
        return False

def notificar_telegram(remitente, asunto):
    # Por ahora imprime para ser capturado por el orquestador principal
    print(f"📱 [ALERTA TELEGRAM] Nuevo correo prioritario procesado.")
    print(f"   -> Remitente: {remitente}")
    print(f"   -> Asunto: {asunto}")
    print(f"   -> El borrador ya fue enviado a tu cuenta de Outlook.\n")

# -------------------------------------------------------------
# 4. MOTOR SCRAPING (PLAYWRIGHT) EN OUTLOOK
# -------------------------------------------------------------

def ejecutar_scraping_outlook():
    print("🚀 Iniciando Motor de Extracción de Outlook Web...")
    
    # Ruta del perfil dedicada a automatización para evitar bloqueos
    user_data_dir = os.path.expanduser("~/.config/google-chrome-automation")
    url_bandeja = "https://outlook.cloud.microsoft/mail/0/inbox"
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path="/usr/bin/google-chrome",
                headless=True,  # Ejecutar en segundo plano sin molestar
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            print(f"❌ Error al abrir el perfil de Chrome (¿Está Chrome abierto ahora mismo?): {e}")
            return

        page = browser.new_page()
        print("🌐 Navegando a la bandeja de entrada corporativa...")
        
        try:
            page.goto(url_bandeja, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # Usar selectores tolerantes (ARIA) que resistan cambios en la interfaz
            # Outlook suele marcar los no leídos de varias formas, buscaremos atributos aria
            
            print("🔍 Buscando correos no leídos...")
            # Unread items in Outlook usually have an unread status or aria-label containing "Unread"
            # Esperamos un poco para que renderice el DOM SPA
            page.wait_for_timeout(5000)
            
            # Localizar correos no leídos en la lista de mensajes
            mensajes_no_leidos = page.locator("div[aria-label*='unread' i], div[aria-label*='no leíd' i], div[aria-label*='no leid' i]").all()
            
            if not mensajes_no_leidos:
                # Intento alternativo de selector por clase
                mensajes_no_leidos = page.locator(".U26fK").all() # Clase común, pero volátil
            
            if not mensajes_no_leidos:
                print("📭 No se detectaron correos nuevos/no leídos.")
                browser.close()
                return
                
            print(f"📥 Encontrados posibles correos no leídos: {len(mensajes_no_leidos)}")
            
            # Solo procesaremos los primeros 3 para no bloquear
            for idx, msg in enumerate(mensajes_no_leidos[:3]):
                try:
                    # Hacer clic en el mensaje en la lista para que se abra a la derecha
                    msg.click()
                    page.wait_for_timeout(3000) # Esperar a que cargue el panel de lectura
                    
                    # Extraer información del panel de lectura
                    # Outlook usa atributos aria generosos
                    # Intentar obtener remitente con selectores alternativos tolerantes
                    remitente = "Remitente Desconocido"
                    selectors_remitente = [
                        "div[aria-label*='De ' i]", 
                        "div[aria-label*='From' i]",
                        "span[class*='Persona' i]", 
                        "div[class*='Persona' i]",
                        "button[aria-label*='De ' i]",
                        "button[aria-label*='From' i]",
                        "span[title*='@']"
                    ]
                    for sel in selectors_remitente:
                        try:
                            loc = page.locator(sel)
                            if loc.count() > 0:
                                txt = loc.first.inner_text().strip()
                                if txt:
                                    remitente = txt.split('\n')[0] # Quedarse con la primera línea
                                    break
                        except Exception:
                            continue

                    # Intentar obtener asunto con selectores alternativos
                    asunto = "Asunto Desconocido"
                    selectors_asunto = [
                        "span.title", 
                        "div[role='heading']", 
                        "h1", 
                        "div[class*='subject' i]", 
                        "span[class*='subject' i]"
                    ]
                    for sel in selectors_asunto:
                        try:
                            loc = page.locator(sel)
                            if loc.count() > 0:
                                txt = loc.first.inner_text().strip()
                                if txt:
                                    asunto = txt
                                    break
                        except Exception:
                            continue
                    
                    # Cuerpo del correo (buscamos el div principal de lectura)
                    cuerpo_locator = page.locator("div.BodyFragment, div.x_WordSection1, div[aria-label='Cuerpo del mensaje']")
                    if cuerpo_locator.count() > 0:
                        cuerpo = cuerpo_locator.first.inner_text()
                    else:
                        cuerpo = page.locator("div.allowTextSelection").first.inner_text()
                        
                    print(f"--- CORREO DETECTADO ---")
                    print(f"De: {remitente}")
                    print(f"Asunto: {asunto}")
                    
                    # Pasa a la IA
                    es_relevante, borrador, nueva_agenda = procesar_con_ia(remitente, asunto, cuerpo)
                    
                    if es_relevante:
                        print("✅ IA: Correo RELEVANTE. Generando actualización de agenda y borrador.")
                        guardar_agenda_contacto(remitente, nueva_agenda)
                        enviar_borrador_corporativo(remitente, asunto, cuerpo, borrador, nueva_agenda)
                        notificar_telegram(remitente, asunto)
                    else:
                        print("💤 IA: Correo clasificado como ruido. Ignorando.")
                        
                    # Marcar como leído (opcional, para que no lo vuelva a leer en la próxima pasada)
                    # En Outlook, al hacer click ya suele marcarse como leído, pero si no, 
                    # podrías agregar un atajo de teclado: page.keyboard.press('Q') 
                    
                except Exception as e_msg:
                    print(f"⚠️ Error al leer un mensaje específico: {e_msg}")
                    continue

        except Exception as e:
            print(f"❌ Error durante el Scraping: {e}")
        finally:
            browser.close()
            print("🛑 Navegador cerrado. Ciclo terminado.")

if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY no encontrada en .env")
    else:
        ejecutar_scraping_outlook()
