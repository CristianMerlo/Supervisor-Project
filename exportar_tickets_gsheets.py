import os
import sys
import json
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

BASE_DIR = Path("/home/cristian/PROYECTOS/Supervisor-Project")
CREDENTIALS_FILE = Path("/home/cristian/Documentos/Supervisor/credentials.json")
TICKETS_FILE = BASE_DIR / "brain" / "tickets_activos.json"
SHEET_ID = "1B42-Ri71xiX-kXmNwGnCxDwg5lo5utKOJ9qPpqJCisY"

def exportar_a_google_sheets():
    if not TICKETS_FILE.exists():
        print("[-] El archivo de tickets activos no existe. Ejecuta el motor primero.")
        return
        
    try:
        with open(TICKETS_FILE, "r") as f:
            tickets = json.load(f)
    except Exception as e:
        print(f"[-] Error leyendo tickets_activos.json: {e}")
        return

    # Definir el scope para Google Drive y Google Sheets
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        print("[*] Autenticando con Google Cloud...")
        creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDENTIALS_FILE), scope)
        client = gspread.authorize(creds)
    except Exception as e:
        print(f"[-] Error autenticando con Google: {e}")
        return

    try:
        print(f"[*] Abriendo planilla {SHEET_ID}...")
        sheet = client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        print(f"[-] Error abriendo Google Sheets (¿compartiste la hoja con el bot?): {e}")
        return

    # Cargar datos de locales.csv para el enriquecimiento
    locales_data = {}
    CSV_PATH = BASE_DIR / "locales.csv"
    if CSV_PATH.exists():
        import csv
        try:
            with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    sigla = row.get("SIGLA TICKETS", "").strip().upper()
                    if sigla:
                        locales_data[sigla] = {
                            "regional": row.get("REGIONAL", "Desconocida"),
                            "supervisor": row.get("SUPERVISOR (GTE ZONA)", "Desconocido")
                        }
        except Exception as e:
            print(f"[-] Error leyendo locales.csv: {e}")

    # Preparar los datos
    encabezados = ["ID", "Local", "Regional", "Supervisor", "Prioridad", "Categoría", "Incidencia", "Detalle", "Fecha de Creación", "Hora", "Última Actualización"]
    filas = [encabezados]
    
    for t in tickets:
        t_date = t.get("date")
        if t_date:
            try:
                fecha_str = datetime.datetime.fromtimestamp(t_date).strftime('%Y-%m-%d')
            except Exception:
                fecha_str = "Desconocida"
        else:
            fecha_str = "Desconocida"
            
        store_sigla = t.get("store", "").strip().upper()
        regional = locales_data.get(store_sigla, {}).get("regional", "Desconocida")
        supervisor = locales_data.get(store_sigla, {}).get("supervisor", "Desconocido")
            
        filas.append([
            t.get("id", ""),
            store_sigla,
            regional,
            supervisor,
            t.get("priority", "Normal"),
            t.get("category", ""),
            t.get("incidence", ""),
            t.get("title", ""),
            fecha_str,
            t.get("time", ""),
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])

    try:
        print(f"[*] Subiendo {len(filas)-1} tickets a Google Sheets...")
        sheet.clear()
        sheet.update(filas)
        print("[+] ¡Exportación exitosa!")
    except Exception as e:
        print(f"[-] Error subiendo datos a Google Sheets: {e}")

if __name__ == "__main__":
    exportar_a_google_sheets()
