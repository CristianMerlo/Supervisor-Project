import os
import sys
import gspread
from datetime import datetime
from pathlib import Path
from google.oauth2.service_account import Credentials

# Configurar path para poder importar módulos locales
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

import notificador_telegram

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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

def main():
    print("Generando resumen de jornada diario...")
    env = cargar_env()
    sheet_url = env.get("SHEETS_SABANA_URL", "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing")

    try:
        ruta_credenciales = BASE_DIR / "credentials.json"
        if not ruta_credenciales.exists():
            print("[ERROR] Falta credentials.json")
            return
            
        creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
        cliente = gspread.authorize(creds)
        sabana = cliente.open_by_url(sheet_url)
        
        try:
            worksheet = sabana.worksheet("Actividad_Tecnicos")
        except gspread.exceptions.WorksheetNotFound:
            print("[INFO] No se encontró la pestaña 'Actividad_Tecnicos'. No hay actividades registradas.")
            notificador_telegram.enviar_alerta("🤖 *Resumen de Jornada*\n\nNo se ha registrado actividad de técnicos aún.")
            return

        registros = worksheet.get_all_records()
    except Exception as e:
        print(f"[ERROR] Falló lectura de Sheets: {e}")
        return

    # Filtrar por la fecha de hoy en TIMESTAMP_REGISTRO o TIMESTAMP de la fecha
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    registros_hoy = []
    
    for r in registros:
        ts_registro = r.get("TIMESTAMP_REGISTRO", "")
        if ts_registro.startswith(hoy_str):
            registros_hoy.append(r)

    # Agrupar por técnico
    actividad_por_tecnico = {}
    for r in registros_hoy:
        tecnico = r.get("TECNICO", "Desconocido")
        if tecnico not in actividad_por_tecnico:
            actividad_por_tecnico[tecnico] = []
        actividad_por_tecnico[tecnico].append(r)

    # Formatear el mensaje del resumen
    fecha_bonita = datetime.now().strftime("%d/%m/%Y")
    mensaje = f"🤖 *Resumen de Jornada de Técnicos* ({fecha_bonita})\n\n"

    if not registros_hoy:
        mensaje += "No se registró actividad en los grupos de WhatsApp el día de hoy."
    else:
        for tecnico, eventos in actividad_por_tecnico.items():
            mensaje += f"👤 *{tecnico}*:\n"
            for ev in eventos:
                hora = ev.get("FECHA_HORA", "--:--")
                evento = ev.get("EVENTO", "COMENTARIO")
                local = ev.get("LOCAL", "")
                msg_orig = ev.get("MENSAJE_ORIGINAL", "").replace("\n", " ").strip()
                
                # Truncar mensaje original si es muy largo
                if len(msg_orig) > 50:
                    msg_orig = msg_orig[:47] + "..."
                
                local_info = f" en *{local}*" if local else ""
                mensaje += f" • `{hora}` - {evento}{local_info}: _{msg_orig}_\n"
            mensaje += "\n"

    # Enviar alerta por Telegram
    print(f"Enviando mensaje a Telegram: {mensaje[:200]}...")
    notificador_telegram.enviar_alerta(mensaje)
    print("Resumen de jornada enviado exitosamente.")

if __name__ == "__main__":
    main()
