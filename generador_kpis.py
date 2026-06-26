import os
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

def generar_kpis():
    if not SHEET_URL:
        notificador_telegram.enviar_alerta("❌ [KPI] Falta GOOGLE_SHEET_URL en .env", agente="Sistema")
        return

    ruta_credenciales = "/home/cristian/Documentos/Supervisor/credentials.json"
    if not os.path.exists(ruta_credenciales):
        notificador_telegram.enviar_alerta("❌ [KPI] Falta credentials.json", agente="Sistema")
        return
        
    try:
        creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
        cliente = gspread.authorize(creds)
        sabana = cliente.open_by_url(SHEET_URL)
        
        # Analizar Historial de Mantenimiento
        hoja_historial = sabana.worksheet("Historial_Mantenimiento")
        registros = hoja_historial.get_all_records()
        
        # Calcular KPIs
        hoy = datetime.now()
        hace_7_dias = hoy - timedelta(days=7)
        
        tickets_pendientes = 0
        fallas_recientes = 0
        maquinas_mas_fallidas = {}
        
        for r in registros:
            # Parsear fecha
            try:
                fecha_str = str(r.get("FECHA_REPORTE", "")).split(" ")[0]
                fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
            except:
                continue
                
            if fecha_obj >= hace_7_dias:
                fallas_recientes += 1
                sigla = str(r.get("SIGLA", "Desconocida"))
                maquinas_mas_fallidas[sigla] = maquinas_mas_fallidas.get(sigla, 0) + 1
                
            if str(r.get("ESTADO", "")).strip().lower() == "pendiente":
                tickets_pendientes += 1
                
        # Analizar Alertas Activas
        hoja_alertas = sabana.worksheet("Alertas_Activas")
        alertas = hoja_alertas.get_all_records()
        alertas_abiertas = sum(1 for a in alertas if str(a.get("ESTADO", "")).strip().upper() == "ABIERTA")
        alertas_criticas = sum(1 for a in alertas if str(a.get("ESTADO", "")).strip().upper() == "ABIERTA" and str(a.get("NIVEL", "")).strip().upper() == "CRÍTICO")

        # Armar reporte
        top_maquinas = sorted(maquinas_mas_fallidas.items(), key=lambda x: x[1], reverse=True)[:3]
        str_maquinas = "\n".join([f"  - {m[0]}: {m[1]} averías" for m in top_maquinas]) if top_maquinas else "  - Ninguna esta semana"
        
        mensaje = f"📊 *Reporte Semanal de KPIs (Mantenimiento)* 📊\n\n"
        mensaje += f"Resumen de los últimos 7 días:\n\n"
        mensaje += f"🛠 *Tickets Activos:* {tickets_pendientes} pendientes de resolución.\n"
        mensaje += f"📈 *Nuevas Averías:* {fallas_recientes} registradas esta semana.\n\n"
        mensaje += f"⚠️ *Alertas Preventivas:*\n"
        mensaje += f"  - Activas Totales: {alertas_abiertas}\n"
        mensaje += f"  - Nivel CRÍTICO: {alertas_criticas}\n\n"
        mensaje += f"🏆 *Top Locales con más Fallas:*\n{str_maquinas}\n\n"
        mensaje += f"👉 *Recomendación:* Ingresa al panel de Sheets para revisar los tickets demorados."
        
        notificador_telegram.enviar_alerta(mensaje, agente="Hermes Analytics")
        
    except Exception as e:
        notificador_telegram.enviar_alerta(f"❌ [KPI ERROR] Falló la generación de KPIs: {e}", agente="Sistema")

if __name__ == "__main__":
    generar_kpis()
