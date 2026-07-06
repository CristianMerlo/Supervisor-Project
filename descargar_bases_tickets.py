import os
import datetime
import requests
import pandas as pd

URL_LOGIN = "https://opgroup.linkuperp.com/apiv2/Oauth/token"
API_CLIENT_ID = "4"
API_CLIENT_SECRET = "lXsUsNd9NXldzNENiUTNC2uLSQMhc3kI4CjhimJn"
USERNAME = os.getenv("MOSTAZA_USER", "cmerlo@mostazaweb.com.ar")
PASSWORD = os.getenv("MOSTAZA_PASS", "Mante2026")

def autenticar():
    payload = {
        "grant_type": "password",
        "client_id": API_CLIENT_ID,
        "client_secret": API_CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "device_os": "android",
        "app_version": "7.0.5"
    }
    print("[*] Autenticando en Linkup ERP (Mostaza)...")
    try:
        res = requests.post(URL_LOGIN, json=payload, timeout=15)
        res.raise_for_status()
        return res.json().get("access_token")
    except Exception as e:
        print(f"[-] Error en autenticación: {e}")
        return None

def fetch_tickets(token, channel):
    url = f"https://opgroup.linkuperp.com/apiv2/tickets/channel/{channel}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.raise_for_status()
        data = res.json().get("data", {}).get("tickets", [])
        return data
    except Exception as e:
        print(f"[-] Error obteniendo canal {channel}: {e}")
        return []

def main():
    token = autenticar()
    if not token:
        print("No se pudo autenticar.")
        return

    print("[*] Descargando tickets de Locales Propios (Canal 1)...")
    tickets_propios = fetch_tickets(token, 1)
    
    print("[*] Descargando tickets de Franquicias (Canal 2)...")
    tickets_franquicias = fetch_tickets(token, 2)
    
    df_propios = pd.DataFrame(tickets_propios)
    df_franquicias = pd.DataFrame(tickets_franquicias)

    # Convertir timestamps a formato de fecha legible
    for df in [df_propios, df_franquicias]:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], unit='s', errors='coerce').dt.strftime('%d/%m/%Y')
    
    fecha_hoy = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"Base_Tickets_Mostaza_{fecha_hoy}.xlsx"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    
    print(f"[*] Guardando en {filepath}...")
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df_propios.to_excel(writer, sheet_name='Locales Propios', index=False)
        df_franquicias.to_excel(writer, sheet_name='Franquicias', index=False)
        
    print(f"[+] Archivo generado con éxito: {filepath}")
    
    # Escribir el nombre del archivo en un tmp file para usarlo en bash
    with open("/tmp/ultimo_excel_mostaza.txt", "w") as f:
        f.write(filepath)

if __name__ == "__main__":
    main()
