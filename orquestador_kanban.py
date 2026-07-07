import os
import sqlite3
import glob
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import notificador_telegram
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
SHEET_URL = os.environ.get("GOOGLE_SHEET_URL")

# Alcances para Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def cargar_mapa_categorias():
    cat_map = {}
    
    # 1. Cargar de Historial_Tickets.xlsx
    web_path = "/home/cristian/Documentos/Supervisor/base_tickets/Historial_Tickets.xlsx"
    if os.path.exists(web_path):
        try:
            df_web = pd.read_excel(web_path)
            for _, r in df_web.iterrows():
                tid = str(r.get("Código", "")).strip()
                cat = str(r.get("Categoría", "")).strip()
                if tid:
                    cat_map[tid] = cat
        except Exception as e:
            print(f"Error cargando Historial_Tickets.xlsx: {e}")
            
    # 2. Cargar de Base_Tickets_Mostaza_*.xlsx
    api_files = glob.glob("/home/cristian/PROYECTOS/Supervisor-Project/Base_Tickets_Mostaza_*.xlsx")
    if api_files:
        try:
            latest_api = max(api_files, key=os.path.getmtime)
            xls = pd.ExcelFile(latest_api)
            for sh in xls.sheet_names:
                df_api = pd.read_excel(xls, sheet_name=sh)
                for _, r in df_api.iterrows():
                    tid = str(r.get("id", "")).strip()
                    cat = str(r.get("category", "")).strip()
                    if tid:
                        cat_map[tid] = cat
        except Exception as e:
            print(f"Error cargando Base_Tickets_Mostaza: {e}")
            
    return cat_map

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
            cat_map = cargar_mapa_categorias()
            
            for r in registros_historial:
                if str(r.get("ESTADO", "")).strip().lower() == "pendiente":
                    # Evitar tickets de "Lista de Mantenimiento" mapeando ID
                    ticket_id = str(r.get("TICKET", "")).strip()
                    categoria = cat_map.get(ticket_id, "").upper()
                    if "LISTA DE MANTENIMIENTO" in categoria:
                        continue
                    try:
                        fecha_str = str(r.get("FECHA_REPORTE", ""))
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        if fecha_obj < limite_48hs:
                            tecnico = str(r.get("TECNICO", "Desconocido"))
                            local = str(r.get("SIGLA", "N/A"))
                            ticket = str(r.get("TICKET", "N/A"))
                            mensajes_alerta.append(f"🛠️ *Local:* {local} | *Ticket:* {ticket}\n⏰ Lleva PENDIENTE desde el {fecha_str}.\n🧑‍🔧 *Técnico asignado:* {tecnico}\n👉 *Requiere actualización urgente en el grupo.*")
                    except Exception:
                        pass
        except gspread.exceptions.WorksheetNotFound:
            pass

        # 2. Analizar Alertas Activas
        try:
            hoja_alertas = sabana.worksheet("Alertas_Activas")
            registros_alertas = hoja_alertas.get_all_records()
            for a in registros_alertas:
                if str(a.get("ESTADO", "")).strip().upper() == "ABIERTA":
                    # Evitar alertas de "Lista de Mantenimiento"
                    categoria = str(a.get("CATEGORIA", a.get("CATEGORÍA", a.get("Categoria", a.get("Categoría", a.get("TIPO_ALERTA", "")))))).strip().upper()
                    if "LISTA DE MANTENIMIENTO" in categoria:
                        continue
                    try:
                        fecha_str = str(a.get("FECHA", ""))
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        if fecha_obj < limite_48hs:
                            local = str(a.get("SIGLA", "N/A"))
                            tipo = str(a.get("TIPO_ALERTA", "N/A"))
                            nivel = str(a.get("NIVEL", "N/A"))
                            mensajes_alerta.append(f"⚠️ *ALERTA ABIERTA (>48hs)*\n🏢 *Local:* {local}\n🚨 *Nivel:* {nivel} | *Tipo:* {tipo}\n📅 Creada: {fecha_str}\n👉 *Requiere intervención o cierre de la alerta.*")
                    except Exception:
                        pass
        except gspread.exceptions.WorksheetNotFound:
            pass
            
        # Si hay alertas, enviarlas
        if mensajes_alerta:
            if len(mensajes_alerta) > 5:
                report_path = "/home/cristian/Documentos/Supervisor/brain/tareas_demoradas.txt"
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("=== REPORTE DETALLADO DE TAREAS Y TICKETS DEMORADOS (>48HS) ===\n")
                    f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("============================================================\n\n")
                    for idx, msg in enumerate(mensajes_alerta, 1):
                        clean_msg = msg.replace("**", "").replace("*", "").replace("👉 ", "")
                        f.write(f"[{idx}] {clean_msg}\n")
                        f.write("-" * 60 + "\n")
                
                resumen_locales = {}
                for msg in mensajes_alerta:
                    import re
                    local_match = re.search(r'Local:\*?\s*(\w+)', msg)
                    if not local_match:
                        local_match = re.search(r'🏢 \*Local:\*?\s*(\w+)', msg)
                    if local_match:
                        loc = local_match.group(1)
                        resumen_locales[loc] = resumen_locales.get(loc, 0) + 1
                
                resumen_texto = "\n".join([f"• *{loc}:* {cnt} tareas" for loc, cnt in sorted(resumen_locales.items())])
                
                titulo = (
                    "🔔 *[ORQUESTADOR KANBAN] Tareas Demoradas (>48hs)* 🔔\n\n"
                    f"El sistema detectó **{len(mensajes_alerta)}** tickets y alertas colgados sin resolución.\n\n"
                    "📊 *Resumen por Local:*\n"
                    f"{resumen_texto}\n\n"
                    "📄 _Se adjunta el reporte detallado con cada ticket en un archivo de texto para no saturar el chat._"
                )
                
                notificador_telegram.enviar_alerta(titulo, agente="Hermes Analytics")
                notificador_telegram.enviar_archivo(report_path, caption="Detalle de tareas demoradas")
            else:
                titulo = "🔔 *[ORQUESTADOR KANBAN] Tareas Demoradas (>48hs)* 🔔\n\nEl sistema detectó los siguientes tickets colgados sin resolución:\n\n"
                cuerpo = "\n---\n".join(mensajes_alerta)
                mensaje_final = titulo + cuerpo
                notificador_telegram.enviar_alerta(mensaje_final, agente="Hermes Analytics")
        else:
            print("[KANBAN] No hay tickets o alertas demorados.")

    except Exception as e:
        notificador_telegram.enviar_alerta(f"❌ [KANBAN ERROR] Falló el orquestador: {e}", agente="Sistema")

if __name__ == "__main__":
    orquestar_kanban()
