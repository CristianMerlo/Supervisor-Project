import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Definir los alcances necesarios (scopes)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def obtener_cliente_sheets():
    """Autentica a Antigravity usando el archivo credentials.json"""
    # Ruta donde dejaremos el archivo descargado de Google Cloud
    ruta_credenciales = "credentials.json"
    
    if not os.path.exists(ruta_credenciales):
        raise FileNotFoundError(f"No se encontró el archivo de credenciales en: {ruta_credenciales}. Sigue el instructivo para descargarlo.")
        
    creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    return cliente

def inyectar_en_sabana(datos_extraidos, alertas_negocio, sheet_url_o_id):
    """
    Toma los datos de la Fase 1 y 2, y los escribe en Google Sheets.
    """
    cliente = obtener_cliente_sheets()
    sabana = cliente.open_by_url(sheet_url_o_id)
    
    # --- 1. HISTORIAL MANTENIMIENTO ---
    hoja_historial = sabana.worksheet("Historial_Mantenimiento")
    
    # Preparar la fila con la estructura que definimos (Pestaña 2)
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fila_historial = [
        fecha_actual,                                   # FECHA_REPORTE
        datos_extraidos.get("ticket", ""),              # TICKET
        datos_extraidos.get("sigla", ""),               # SIGLA
        datos_extraidos.get("tecnico", ""),             # TECNICO
        datos_extraidos.get("ppm", 0),                  # PPM_AGUA
        datos_extraidos.get("shots", 0),                # SHOTS_ACTUALES
        "Pendiente (Ver IA)",                           # FILTRO_ESTADO
        datos_extraidos.get("repuestos", "")            # REPUESTOS_PEDIDOS
    ]
    # Insertar al final
    hoja_historial.append_row(fila_historial)
    print(f"[✓] Registro inyectado en Historial_Mantenimiento para el local {datos_extraidos.get('sigla')}")
    
    # --- 2. ALERTAS ACTIVAS ---
    if alertas_negocio.get('alertas_activas'):
        hoja_alertas = sabana.worksheet("Alertas_Activas")
        for alerta in alertas_negocio['alertas_activas']:
            fila_alerta = [
                fecha_actual,                           # FECHA
                datos_extraidos.get("sigla", ""),       # SIGLA
                alerta.get("tipo", ""),                 # TIPO_ALERTA
                alerta.get("nivel", ""),                # NIVEL
                alerta.get("mensaje", ""),              # MENSAJE
                "ABIERTA"                               # ESTADO
            ]
            hoja_alertas.append_row(fila_alerta)
            print(f"[✓] Alerta inyectada en Alertas_Activas: {alerta.get('nivel')}")

if __name__ == "__main__":
    print("Módulo de integración con Sheets listo. Esperando ser invocado por el Motor Supervisor.")
