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

def normalizar_tecnico(nombre):
    if not nombre:
        return "Desconocido"
    nombre_lower = str(nombre).lower().strip()
    
    # Mapeo de nombres y correos de técnicos a estándar
    MAP_TECNICOS = {
        "anabela guerrero": "Anabela Guerrero",
        "ana guerrero": "Anabela Guerrero",
        "guerreroana.mtz@gmail.com": "Anabela Guerrero",
        "tomas vera": "Tomas Vera",
        "tomás vera": "Tomas Vera",
        "tomasvera.mtz@gmail.com": "Tomas Vera",
        "francisco rametta": "Francisco Rametta",
        "frametta.mtz@gmail.com": "Francisco Rametta",
        "francisco mto rosario mostaza": "Francisco Rametta",
        "fernando soria": "Fernando Soria",
        "fernandosoria.mtz@gmail.com": "Fernando Soria",
        "fer soria": "Fernando Soria",
        "fernando soria mantenimiento": "Fernando Soria"
    }
    
    return MAP_TECNICOS.get(nombre_lower, nombre.strip())

def main():
    print("Generando resumen de jornada diario consolidado...")
    env = cargar_env()
    sheet_url = env.get("SHEETS_SABANA_URL", "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing")

    # Inicializar estructuras para agrupar por técnico
    actividad_por_tecnico = {}

    def asegurar_tecnico_dict(tecnico):
        tecnico_std = normalizar_tecnico(tecnico)
        if tecnico_std not in actividad_por_tecnico:
            actividad_por_tecnico[tecnico_std] = {
                'fichadas': [],
                'reportes': []
            }
        return tecnico_std

    try:
        ruta_credenciales = BASE_DIR / "credentials.json"
        if not ruta_credenciales.exists():
            print("[ERROR] Falta credentials.json")
            return
            
        creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
        cliente = gspread.authorize(creds)
        sabana = cliente.open_by_url(sheet_url)
    except Exception as e:
        print(f"[ERROR] Falló conexión con Google Sheets: {e}")
        return

    hoy_str = datetime.now().strftime("%Y-%m-%d")
    ticket_ids_procesados = set()  # Para evitar reportes duplicados de un mismo ticket

    # 1. LEER FICHADAS DE WHATSAPP (Actividad_Tecnicos)
    try:
        worksheet_act = sabana.worksheet("Actividad_Tecnicos")
        registros_act = worksheet_act.get_all_records()
        for r in registros_act:
            ts_registro = r.get("TIMESTAMP_REGISTRO", "")
            if ts_registro.startswith(hoy_str):
                tecnico = r.get("TECNICO", "Desconocido")
                tecnico_std = asegurar_tecnico_dict(tecnico)
                
                actividad_por_tecnico[tecnico_std]['fichadas'].append({
                    'hora': r.get("FECHA_HORA", "--:--"),
                    'evento': r.get("EVENTO", "COMENTARIO"),
                    'local': r.get("LOCAL", ""),
                    'mensaje': r.get("MENSAJE_ORIGINAL", "").replace("\n", " ").strip()
                })
    except gspread.exceptions.WorksheetNotFound:
        print("[INFO] Pestaña 'Actividad_Tecnicos' no encontrada.")
    except Exception as e:
        print(f"[WARN] Error procesando Actividad_Tecnicos: {e}")

    # 2. LEER REPORTES PROCESADOS (Historial_Mantenimiento)
    try:
        worksheet_hist = sabana.worksheet("Historial_Mantenimiento")
        registros_hist = worksheet_hist.get_all_records()
        for r in registros_hist:
            fecha_rep = r.get("FECHA_REPORTE", "")
            if fecha_rep.startswith(hoy_str):
                tecnico = r.get("TECNICO", "Desconocido")
                tecnico_std = asegurar_tecnico_dict(tecnico)
                ticket = str(r.get("TICKET", "")).strip()
                sigla = r.get("SIGLA", "")
                
                # Registrar el ticket para deduplicar con respuestas de formulario
                if ticket:
                    ticket_ids_procesados.add(f"{tecnico_std}_{sigla}_{ticket}")
                
                actividad_por_tecnico[tecnico_std]['reportes'].append({
                    'origen': 'WhatsApp/Local',
                    'local': sigla,
                    'ticket': ticket,
                    'ppm': r.get("PPM_AGUA", "-"),
                    'shots': r.get("SHOTS", "-"),
                    'estado': r.get("ESTADO", "Desconocido")
                })
    except gspread.exceptions.WorksheetNotFound:
        print("[INFO] Pestaña 'Historial_Mantenimiento' no encontrada.")
    except Exception as e:
        print(f"[WARN] Error procesando Historial_Mantenimiento: {e}")

    # 3. LEER NUEVAS RESPUESAS DE GOOGLE FORM (Respuestas_Formulario)
    try:
        worksheet_form = sabana.worksheet("Respuestas_Formulario")
        registros_form = worksheet_form.get_all_records()
        for r in registros_form:
            marca_temporal = r.get("Marca temporal", "")
            if marca_temporal.startswith(hoy_str):
                # Obtener técnico por campo 'Técnico' o correo
                tecnico = r.get("Técnico", "")
                if not tecnico:
                    tecnico = r.get("Dirección de correo", "Desconocido")
                
                tecnico_std = asegurar_tecnico_dict(tecnico)
                
                # Extraer sigla del local (ej: "PUMA CHILE (FMPCH)" -> "FMPCH")
                local_raw = r.get("Local", "")
                match = re.search(r'\((.*?)\)', local_raw)
                sigla = match.group(1).strip().upper() if match else local_raw.strip().upper()
                
                ticket = str(r.get("Número de Ticket", "")).strip()
                
                # Deduplicar si ya lo procesó e ingresó al Historial
                dup_key = f"{tecnico_std}_{sigla}_{ticket}"
                if ticket and dup_key in ticket_ids_procesados:
                    continue  # Ya está listado en el Historial de Mantenimiento
                
                actividad_por_tecnico[tecnico_std]['reportes'].append({
                    'origen': 'Google Form',
                    'local': sigla,
                    'ticket': ticket,
                    'ppm': r.get("PPM_Agua", "-"),
                    'shots': r.get("Shots_Cafetera", "-"),
                    'estado': 'Recibido (Pendiente Proceso)'
                })
    except gspread.exceptions.WorksheetNotFound:
        print("[INFO] Pestaña 'Respuestas_Formulario' no encontrada.")
    except Exception as e:
        print(f"[WARN] Error procesando Respuestas_Formulario: {e}")

    # Formatear mensaje final para Telegram
    fecha_bonita = datetime.now().strftime("%d/%m/%Y")
    mensaje = f"🧠 *[Hermes] Resumen de Jornada de Técnicos* ({fecha_bonita})\n\n"

    # Verificar si hubo alguna actividad registrada
    tiene_actividad = False
    for tec, data in actividad_por_tecnico.items():
        if data['fichadas'] or data['reportes']:
            tiene_actividad = True
            break

    if not tiene_actividad:
        mensaje += "No se registró actividad de técnicos (fichadas ni reportes de mantenimiento) el día de hoy."
    else:
        for tecnico, data in sorted(actividad_por_tecnico.items()):
            # Omitir si no tiene nada registrado hoy
            if not data['fichadas'] and not data['reportes']:
                continue
                
            mensaje += f"👤 *{tecnico}*:\n"
            
            # Listar fichadas (Ingreso/Egreso)
            if data['fichadas']:
                mensaje += "  📍 *Fichadas / Movimientos:*\n"
                for f in sorted(data['fichadas'], key=lambda x: x['hora']):
                    local_str = f" en *{f['local']}*" if f['local'] else ""
                    msg_orig = f['mensaje']
                    if len(msg_orig) > 50:
                        msg_orig = msg_orig[:47] + "..."
                    mensaje += f"   • `{f['hora']}` - *{f['evento']}*{local_str}: _{msg_orig}_\n"
            
            # Listar reportes técnicos enviados
            if data['reportes']:
                mensaje += "  📋 *Informes de Visitas / PDFs:*\n"
                for r in data['reportes']:
                    ticket_str = f" (Ticket #{r['ticket']})" if r['ticket'] else ""
                    mensaje += f"   • Local *{r['local']}*{ticket_str} - PPM: `{r['ppm']}`, Shots: `{r['shots']}` | _{r['estado']}_ ({r['origen']})\n"
                    
            mensaje += "\n"

    # Enviar reporte con identidad unificada de Hermes
    import re
    print(f"Enviando mensaje consolidado de Hermes a Telegram...")
    notificador_telegram.enviar_alerta(mensaje, agente="Hermes")
    print("Resumen de jornada enviado exitosamente.")

if __name__ == "__main__":
    import re # Asegurar import de re para la función de match
    main()
