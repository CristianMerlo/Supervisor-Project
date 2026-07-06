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

html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background-color: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { background-color: #1a202c; color: #fff; padding: 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .header p { margin: 10px 0 0 0; color: #a0aec0; font-size: 14px; }
        .content { padding: 30px; }
        .section-title { font-size: 18px; color: #2d3748; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-top: 0; margin-bottom: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
        
        .card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .card-title { font-size: 16px; font-weight: 600; color: #1a202c; margin: 0; }
        .badge { background-color: #ebf8ff; color: #3182ce; padding: 4px 8px; border-radius: 9999px; font-size: 12px; font-weight: 600; }
        .badge-cron { background-color: #f0fff4; color: #38a169; }
        .badge-live { background-color: #fff5f5; color: #e53e3e; }
        
        .script-name { font-family: monospace; font-size: 13px; color: #718096; background: #edf2f7; padding: 2px 6px; border-radius: 4px; margin-top: 5px; display: inline-block; }
        .card-desc { font-size: 14px; color: #4a5568; margin: 10px 0 0 0; line-height: 1.5; }
        
        .footer { text-align: center; padding: 20px; font-size: 12px; color: #a0aec0; background-color: #f8fafc; border-top: 1px solid #e2e8f0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Mapa de Arquitectura y Funcionalidades</h1>
            <p>Antigravity / Supervisor System - Reporte de Estado Actual</p>
        </div>
        
        <div class="content">
            <!-- SECCION 1 -->
            <h2 class="section-title">🎫 Gestión de Tickets y Operaciones</h2>
            
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Motor de Alertas de Tickets</h3>
                    <span class="badge badge-cron">Cada 10 minutos</span>
                </div>
                <span class="script-name">motor_tickets_mostaza.py / exportar_tickets_gsheets.py</span>
                <p class="card-desc">Conecta directamente con la API de Mostaza (sin navegador) para buscar nuevos tickets. Notifica alertas a Telegram y respalda la data en Google Sheets.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Descarga Histórica y Cruce</h3>
                    <span class="badge badge-cron">Diario - 02:00 AM</span>
                </div>
                <span class="script-name">descargar_historico_tickets.py / cruzar_tickets_tecnicos.py</span>
                <p class="card-desc">Robot nocturno que descarga el Excel gigante con más de 1.500 tickets históricos usando Chrome en modo invisible. Filtra los descartados (ej. Mantenimiento) y los cruza con la matriz de tus técnicos para dejar la base 100% limpia.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Reporte Matutino de Técnicos</h3>
                    <span class="badge badge-cron">Diario - 07:30 AM</span>
                </div>
                <span class="script-name">reporte_diario_tecnicos.py</span>
                <p class="card-desc">Lee la base cruzada en la madrugada, empaqueta un Excel limpio con 2 pestañas (Abiertos / Cerrados en el mes) y te lo envía por Telegram justo antes de iniciar la jornada. A su vez, actualiza un dashboard resumen dentro de "La Sábana" en Google Sheets.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Orquestador Kanban</h3>
                    <span class="badge badge-cron">Diario - 10:00 AM</span>
                </div>
                <span class="script-name">orquestador_kanban.py</span>
                <p class="card-desc">Sincroniza y mueve tarjetas en el tablero de trabajo del equipo.</p>
            </div>

            <!-- SECCION 2 -->
            <h2 class="section-title">📲 Comunicaciones y Asistentes</h2>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Bot de WhatsApp (Escucha Activa)</h3>
                    <span class="badge badge-live">Servicio Continuo</span>
                </div>
                <span class="script-name">motor_whatsapp_web.py</span>
                <p class="card-desc">Mantiene la sesión de Chrome abierta en puerto 9222. Lee los mensajes de los grupos de franquicias y operarios. Cuenta con protección contra modales superpuestos para no trabarse.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Userbot de Telegram</h3>
                    <span class="badge badge-live">Servicio Continuo</span>
                </div>
                <span class="script-name">userbot_supervisor.py (Restore loop)</span>
                <p class="card-desc">El bot al que le hablas por privado. Permite el envío de manuales y PDFs interactivos, preguntando a qué equipo pertenecen para catalogarlos correctamente.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Asistente de Correos</h3>
                    <span class="badge badge-cron">Cada 15 minutos</span>
                </div>
                <span class="script-name">asistente_correos.py</span>
                <p class="card-desc">Monitorea la bandeja de entrada del correo, clasifica los emails entrantes y genera respuestas o alertas si se detectan urgencias operativas.</p>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Resumen de Jornada</h3>
                    <span class="badge badge-cron">Diario - 20:00 hrs</span>
                </div>
                <span class="script-name">resumen_jornada.py</span>
                <p class="card-desc">Realiza el cierre operativo del día consolidando los eventos más relevantes del trabajo de los técnicos.</p>
            </div>

            <!-- SECCION 3 -->
            <h2 class="section-title">🧠 Base de Conocimiento e I.A.</h2>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Ingestor Automático</h3>
                    <span class="badge badge-cron">Cada 5 minutos</span>
                </div>
                <span class="script-name">ingestor_automatico.py</span>
                <p class="card-desc">El motor principal de almacenamiento. Toma cualquier archivo, foto o PDF que descargas o mandas a los bots y lo clasifica automáticamente en la carpeta del local correspondiente (Caseros, Morón, Salta, etc.).</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Conversor Markdown para I.A.</h3>
                    <span class="badge badge-cron">Diario - 02:00 AM</span>
                </div>
                <span class="script-name">convertir_pdfs_a_md.py</span>
                <p class="card-desc">Toma los manuales (PDFs) subidos a la base y los transforma en texto estructurado (.md) para que Antigravity y NotebookLM puedan leerlos y entenderlos más rápido a futuro.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Auditor QA de Wiki y Arquitectura</h3>
                    <span class="badge badge-cron">Lunes y Viernes - 09:00 AM</span>
                </div>
                <span class="script-name">agente_qa_wiki.py / auditor_arquitectura.py</span>
                <p class="card-desc">Revisa la calidad de los reportes subidos, controla la limpieza de las carpetas de evidencia y previene que los archivos se acumulen fuera de lugar.</p>
            </div>

            <!-- SECCION 4 -->
            <h2 class="section-title">⚙️ Mantenimiento del Servidor</h2>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Reinicio Preventivo de Chrome</h3>
                    <span class="badge badge-cron">Diario - 04:00 AM</span>
                </div>
                <span class="script-name">reiniciar_chrome.sh</span>
                <p class="card-desc">Apaga y vuelve a encender Google Chrome por detrás (puerto 9222) asegurando que no consuma toda la memoria RAM del servidor y previniendo caídas del bot de WhatsApp.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Reporte del Sistema y Errores</h3>
                    <span class="badge badge-cron">Diario - 03:00 AM y 08:15 AM</span>
                </div>
                <span class="script-name">motor_extraccion_errores.py / reporte_sistema.py</span>
                <p class="card-desc">Analiza los logs de error durante la noche. A la mañana, envía un parte de salud sobre el estado de la CPU, la RAM y los scripts del equipo.</p>
            </div>

        </div>
        
        <div class="footer">
            Generado automáticamente por Antigravity A.I. • Dashboard de Funcionalidades Activas
        </div>
    </div>
</body>
</html>
"""

def main():
    env = cargar_env()
    gmail_user = env.get("GMAIL_USER")
    gmail_pass = env.get("GMAIL_APP_PASSWORD")
    destinatario = env.get("CORREO_CORPORATIVO", gmail_user)

    if not gmail_user or not gmail_pass:
        print("Faltan credenciales de Gmail.")
        return

    msg = MIMEMultipart("alternative")
    msg['From'] = gmail_user
    msg['To'] = destinatario
    msg['Subject'] = "[Antigravity] 🌐 Dashboard: Mapa de Funcionalidades y Automatizaciones"

    # Adjuntar HTML
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, destinatario, msg.as_string())
        server.quit()
        print("[+] Correo enviado con el Dashboard HTML.")
    except Exception as e:
        print(f"[-] Error al enviar el correo: {e}")

if __name__ == "__main__":
    main()

