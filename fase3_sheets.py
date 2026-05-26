import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def obtener_cliente_sheets():
    ruta_credenciales = "credentials.json"
    if not os.path.exists(ruta_credenciales):
        raise FileNotFoundError("Falta credentials.json")
    creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
    return gspread.authorize(creds)

def inyectar_en_sabana(datos_extraidos, alertas_negocio, sheet_url):
    cliente = obtener_cliente_sheets()
    sabana = cliente.open_by_url(sheet_url)
    
    # --- 1. HISTORIAL MANTENIMIENTO ---
    try:
        hoja_historial = sabana.worksheet("Historial_Mantenimiento")
    except gspread.exceptions.WorksheetNotFound:
        hoja_historial = sabana.add_worksheet(title="Historial_Mantenimiento", rows="1000", cols="8")
        # Escribir Headers
        hoja_historial.append_row(["FECHA_REPORTE", "TICKET", "SIGLA", "TECNICO", "PPM_AGUA", "SHOTS", "ESTADO", "REPUESTOS"])
        
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fila_historial = [
        fecha_actual,
        datos_extraidos.get("ticket", ""),
        datos_extraidos.get("sigla", ""),
        datos_extraidos.get("tecnico", ""),
        datos_extraidos.get("ppm", 0),
        datos_extraidos.get("shots", 0),
        "Pendiente",
        datos_extraidos.get("repuestos", "")
    ]
    hoja_historial.append_row(fila_historial)
    print(f"[✓] Registro inyectado en Historial_Mantenimiento: Local {datos_extraidos.get('sigla')}")
    
    # --- 2. ALERTAS ACTIVAS ---
    if alertas_negocio.get('alertas_activas'):
        try:
            hoja_alertas = sabana.worksheet("Alertas_Activas")
        except gspread.exceptions.WorksheetNotFound:
            hoja_alertas = sabana.add_worksheet(title="Alertas_Activas", rows="1000", cols="6")
            hoja_alertas.append_row(["FECHA", "SIGLA", "TIPO_ALERTA", "NIVEL", "MENSAJE", "ESTADO"])
            
        for alerta in alertas_negocio['alertas_activas']:
            fila_alerta = [
                fecha_actual,
                datos_extraidos.get("sigla", ""),
                alerta.get("tipo", ""),
                alerta.get("nivel", ""),
                alerta.get("mensaje", ""),
                "ABIERTA"
            ]
            hoja_alertas.append_row(fila_alerta)
            print(f"[✓] Alerta inyectada en Alertas_Activas: {alerta.get('nivel')}")
