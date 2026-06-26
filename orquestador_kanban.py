import os
import sqlite3
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import notificador_telegram
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
SHEET_URL = os.environ.get("GOOGLE_SHEET_URL")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def orquestar_kanban():
    if not SHEET_URL:
        notificador_telegram.enviar_alerta("❌ [Kanban] Falta GOOGLE_SHEET_URL en .env", agente="Sistema")
        return

    ruta_credenciales = "/home/cristian/Documentos/Supervisor/credentials.json"
    if not os.path.exists(ruta_credenciales):
        notificador_telegram.enviar_alerta("❌ [Kanban] Falta credentials.json", agente="Sistema")
        return
        
    try:
        creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
        cliente = gspread.authorize(creds)
        sabana = cliente.open_by_url(SHEET_URL)
        
        hoy = datetime.now()
        limite_48hs = hoy - timedelta(hours=48)
        
        mensajes_alerta = []

        # 1. Analizar Historial de Mantenimiento (Tickets colgados)
        try:
            hoja_historial = sabana.worksheet("Historial_Mantenimiento")
            registros_historial = hoja_historial.get_all_records()
            for r in registros_historial:
                if str(r.get("ESTADO", "")).strip().lower() == "pendiente":
                    try:
                        fecha_str = str(r.get("FECHA_REPORTE", ""))
                        # Intentar parsear formato "%Y-%m-%d %H:%M:%S"
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        if fecha_obj < limite_48hs:
                            tecnico = str(r.get("TECNICO", "Desconocido"))
                            local = str(r.get("SIGLA", "N/A"))
                            ticket = str(r.get("TICKET", "N/A"))
                            mensajes_alerta.append(f"🛠️ *Local:* {local} | *Ticket:* {ticket}\n⏰ Lleva PENDIENTE desde el {fecha_str}.\n🧑‍🔧 *Técnico asignado:* {tecnico}\n👉 *Requiere actualización urgente en el grupo.*")
                    except Exception as e:
                        pass
        except gspread.exceptions.WorksheetNotFound:
            pass

        # 2. Analizar Alertas Activas
        try:
            hoja_alertas = sabana.worksheet("Alertas_Activas")
            registros_alertas = hoja_alertas.get_all_records()
            for a in registros_alertas:
                if str(a.get("ESTADO", "")).strip().upper() == "ABIERTA":
                    try:
                        fecha_str = str(a.get("FECHA", ""))
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        if fecha_obj < limite_48hs:
                            local = str(a.get("SIGLA", "N/A"))
                            tipo = str(a.get("TIPO_ALERTA", "N/A"))
                            nivel = str(a.get("NIVEL", "N/A"))
                            mensajes_alerta.append(f"⚠️ *ALERTA ABIERTA (>48hs)*\n🏢 *Local:* {local}\n🚨 *Nivel:* {nivel} | *Tipo:* {tipo}\n📅 Creada: {fecha_str}\n👉 *Requiere intervención o cierre de la alerta.*")
                    except Exception as e:
                        pass
        except gspread.exceptions.WorksheetNotFound:
            pass
            
        # Si hay alertas, enviarlas
        if mensajes_alerta:
            titulo = "🔔 *[ORQUESTADOR KANBAN] Tareas Demoradas (>48hs)* 🔔\n\nEl sistema detectó los siguientes tickets colgados sin resolución:\n\n"
            cuerpo = "\n---\n".join(mensajes_alerta)
            mensaje_final = titulo + cuerpo
            # Enviar notificación privada al supervisor para que él coordine en el grupo
            notificador_telegram.enviar_alerta(mensaje_final, agente="Hermes Analytics")
        else:
            print("[KANBAN] No hay tickets o alertas demorados.")

    except Exception as e:
        notificador_telegram.enviar_alerta(f"❌ [KANBAN ERROR] Falló el orquestador: {e}", agente="Sistema")

if __name__ == "__main__":
    orquestar_kanban()
