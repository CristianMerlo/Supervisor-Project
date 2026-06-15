import os
import sys
import re
import io
import shutil
import gspread
from datetime import datetime
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configurar path para poder importar módulos locales
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

import motor_supervisor
import archivador_drive
import notificador_telegram

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Lista de correos de técnicos autorizados (se puede ampliar)
CORREOS_TECNICOS_AUTORIZADOS = [
    "guerreroana.mtz@gmail.com",
    "tomasvera.mtz@gmail.com",
    "frametta.mtz@gmail.com",
    "fernandosoria.mtz@gmail.com"
]

def obtener_cliente_sheets():
    ruta_credenciales = BASE_DIR / "credentials.json"
    if not ruta_credenciales.exists():
        raise FileNotFoundError(f"Falta credentials.json en: {ruta_credenciales}")
    creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
    return gspread.authorize(creds)

def obtener_servicio_drive():
    ruta_credenciales = BASE_DIR / "credentials.json"
    if not ruta_credenciales.exists():
        raise FileNotFoundError(f"Falta credentials.json en: {ruta_credenciales}")
    creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def descargar_archivo_drive(service, file_id, dest_path):
    print(f"[DRIVE-DOWNLOAD] Descargando archivo ID: {file_id} en {dest_path}")
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.close()
    print("[✓] Descarga completa.")

def extraer_id_archivo_drive(url):
    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def extraer_sigla_de_opcion(opcion):
    match = re.search(r'\((.*?)\)', opcion)
    if match:
        return match.group(1).strip().upper()
    return opcion.strip().upper()

def extraer_estado_cafetera(texto):
    texto_lower = texto.lower()
    if "fuera de servicio" in texto_lower or "no operativo" in texto_lower:
        return "Fuera de Servicio"
    elif "con observaciones" in texto_lower or "operativo con observaciones" in texto_lower:
        return "Con Observaciones"
    elif "operativo" in texto_lower or "queda operativo" in texto_lower:
        return "Operativa"
    return "Desconocido"

def cargar_env():
    ruta_env = BASE_DIR / ".env"
    if ruta_env.exists():
        with open(ruta_env, "r") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                os.environ[k.strip()] = v.strip()

def buscar_worksheet_respuestas(sabana):
    nombres_comunes = ["respuestas de formulario 1", "respuestas_formulario", "informes_formulario", "respuestas", "informes"]
    for sheet in sabana.worksheets():
        title_lower = sheet.title.lower()
        if any(nc in title_lower for nc in nombres_comunes):
            print(f"[FORM] Detectada hoja de respuestas: '{sheet.title}'")
            return sheet
    # Fallback
    sheet = sabana.worksheets()[0]
    print(f"[FORM] No se encontró hoja de respuestas típica. Usando la primera: '{sheet.title}'")
    return sheet

def ejecutar_ingesta_formulario():
    print("\n=== INICIANDO INGESTA DESDE GOOGLE FORM ===")
    
    cargar_env()
    sheet_url = os.getenv("SHEETS_SABANA_URL", "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing")

    try:
        cliente = obtener_cliente_sheets()
        drive_service = obtener_servicio_drive()
        sabana = cliente.open_by_url(sheet_url)
        worksheet = buscar_worksheet_respuestas(sabana)
    except Exception as e:
        print(f"[ERROR INICIALIZACIÓN] No se pudo conectar a Sheets/Drive: {e}")
        return

    # 1. Asegurar la presencia de columnas de KPIs
    KPI_HEADERS = [
        "PPM_Agua", "Shots_Cafetera", "Prioridad", "Equipo", "Nro_Serie",
        "Estado_Cafetera", "Repuestos", "Estado_General", "Alertas_Detalle",
        "Discrepancia_Local", "Discrepancia_Ticket", "Correo_Autorizado",
        "Estado_Proceso", "Detalle_Proceso"
    ]
    
    try:
        header_row = worksheet.row_values(1)
    except Exception as e:
        print(f"[ERROR READ HEADERS] {e}")
        return

    headers_lower = [h.strip().lower() for h in header_row]
    headers_updated = list(header_row)

    for kh in KPI_HEADERS:
        if kh.lower() not in headers_lower:
            headers_updated.append(kh)

    if len(headers_updated) > len(header_row):
        print(f"[FORM] Añadiendo nuevas columnas de KPI a la hoja...")
        worksheet.update('A1', [headers_updated])
        header_row = headers_updated
        headers_lower = [h.strip().lower() for h in header_row]

    # Map indices of columns
    def find_col_idx(keywords, default):
        for kw in keywords:
            for i, h in enumerate(headers_lower):
                if kw in h:
                    return i + 1
        return default

    col_timestamp = find_col_idx(["timestamp", "marca temporal"], 1)
    col_email = find_col_idx(["correo", "email", "dirección"], -1)
    col_local = find_col_idx(["local"], 2)
    col_fecha = find_col_idx(["fecha"], 3)
    col_ticket = find_col_idx(["ticket"], 4)
    col_tecnico = find_col_idx(["tecnico", "técnico"], 5)
    col_pdf = find_col_idx(["informe", "pdf", "archivo", "adjunto"], 6)

    # Map KPI column indices
    kpi_col_indices = {kh: headers_lower.index(kh.lower()) + 1 for kh in KPI_HEADERS}

    # 2. Leer registros
    try:
        all_values = worksheet.get_all_values()
    except Exception as e:
        print(f"[ERROR READ VALUES] {e}")
        return

    if len(all_values) <= 1:
        print("[FORM] No hay respuestas en la hoja de cálculo.")
        return

    print(f"[FORM] Analizando {len(all_values)-1} registros...")

    # Carpeta temporal para descargar PDFs
    temp_dir = BASE_DIR / "temp_form_pdfs"
    temp_dir.mkdir(exist_ok=True)

    for idx, row in enumerate(all_values[1:], start=2):
        # Rellenar row si es más corta que los headers
        while len(row) < len(header_row):
            row.append("")

        # Comprobar Estado_Proceso
        estado_proceso_val = row[kpi_col_indices["Estado_Proceso"] - 1].strip().upper()
        if estado_proceso_val in ["PROCESADO", "COMPLETO"]:
            continue

        print(f"\n--- Procesando Fila {idx} ---")

        # Obtener valores
        email_val = row[col_email - 1].strip() if col_email > 0 else "N/A"
        local_val = row[col_local - 1].strip()
        fecha_val = row[col_fecha - 1].strip()
        ticket_val = row[col_ticket - 1].strip()
        tecnico_val = row[col_tecnico - 1].strip()
        pdf_url = row[col_pdf - 1].strip()

        if not pdf_url:
            print(f"[ROW-{idx}] Fila vacía o sin enlace PDF. Omitiendo.")
            continue

        file_id = extraer_id_archivo_drive(pdf_url)
        if not file_id:
            msg = f"No se pudo extraer el ID del archivo Drive de la URL: {pdf_url}"
            print(f"[ROW-{idx}] {msg}")
            worksheet.update_cell(idx, kpi_col_indices["Estado_Proceso"], "ERROR")
            worksheet.update_cell(idx, kpi_col_indices["Detalle_Proceso"], msg)
            continue

        temp_pdf_path = temp_dir / f"MTZ_FORM_R{idx}.pdf"

        try:
            # 1. Descargar el PDF
            descargar_archivo_drive(drive_service, file_id, temp_pdf_path)

            # 2. Parsear reporte y obtener texto
            datos_extraidos, resultado_auditoria, texto_pdf = motor_supervisor.procesar_reporte(str(temp_pdf_path))
            
            # 3. Extraer estado de la cafetera
            estado_cafetera = extraer_estado_cafetera(texto_pdf)
            
            # 4. Validaciones cruzadas
            # Mapear local del formulario a su sigla
            sigla_form = extraer_sigla_de_opcion(local_val)
            sigla_pdf = datos_extraidos.get("sigla", "").strip().upper()
            discrepancia_local = "NO" if sigla_form == sigla_pdf else "SÍ"

            # Validar Ticket
            ticket_pdf = str(datos_extraidos.get("ticket", "")).strip()
            discrepancia_ticket = "NO" if ticket_val == ticket_pdf else "SÍ"

            # Validar Correo de Técnico
            correo_autorizado = "NO"
            if col_email > 0 and email_val != "N/A":
                if email_val.lower() in [e.lower() for e in CORREOS_TECNICOS_AUTORIZADOS]:
                    correo_autorizado = "SÍ"
            else:
                # Si no se colecta email, asumimos que no aplica verificación estricta por mail
                correo_autorizado = "SÍ"

            # Alerta de Telegram si hay discrepancias
            if discrepancia_local == "SÍ" or discrepancia_ticket == "SÍ" or correo_autorizado == "NO":
                msg_alerta = f"⚠️ *Discrepancia en Formulario de Reportes*\n" \
                             f"• Fila: {idx}\n" \
                             f"• Técnico: {tecnico_val} ({email_val})\n" \
                             f"• Local Form: {local_val} | PDF: {sigla_pdf}\n" \
                             f"• Ticket Form: {ticket_val} | PDF: {ticket_pdf}\n" \
                             f"• Discrepancia Local: {discrepancia_local}\n" \
                             f"• Discrepancia Ticket: {discrepancia_ticket}\n" \
                             f"• Correo Autorizado: {correo_autorizado}"
                notificador_telegram.enviar_alerta(msg_alerta)

            # 5. Archivar en Google Drive en la carpeta por sigla
            sigla_archivo = sigla_pdf if sigla_pdf else sigla_form
            exito_archive = archivador_drive.archivar_reporte_en_drive(str(temp_pdf_path), sigla_archivo)

            # 6. Escribir resultados directamente en la fila
            alerts_text = "; ".join([a.get("mensaje", "") for a in resultado_auditoria.get("alertas_activas", [])])
            
            updates = [
                (kpi_col_indices["PPM_Agua"], datos_extraidos.get("ppm", 0)),
                (kpi_col_indices["Shots_Cafetera"], datos_extraidos.get("shots", 0)),
                (kpi_col_indices["Prioridad"], resultado_auditoria.get("estado_general", "VERDE_NORMAL")),
                (kpi_col_indices["Equipo"], datos_extraidos.get("maquina", "")),
                (kpi_col_indices["Nro_Serie"], re.search(r"SN:\s*(\w+)", texto_pdf).group(1) if re.search(r"SN:\s*(\w+)", texto_pdf) else ""),
                (kpi_col_indices["Estado_Cafetera"], estado_cafetera),
                (kpi_col_indices["Repuestos"], datos_extraidos.get("repuestos", "")),
                (kpi_col_indices["Estado_General"], resultado_auditoria.get("estado_general", "VERDE_NORMAL")),
                (kpi_col_indices["Alertas_Detalle"], alerts_text),
                (kpi_col_indices["Discrepancia_Local"], discrepancia_local),
                (kpi_col_indices["Discrepancia_Ticket"], discrepancia_ticket),
                (kpi_col_indices["Correo_Autorizado"], correo_autorizado),
                (kpi_col_indices["Estado_Proceso"], "PROCESADO"),
                (kpi_col_indices["Detalle_Proceso"], "Procesado exitosamente con archivado en Drive." if exito_archive else "Procesado, pero falló el archivado en Drive.")
            ]

            for col_num, val in updates:
                worksheet.update_cell(idx, col_num, val)

            print(f"[✓] Fila {idx} completada correctamente.")
            
            # Actualizar ficha local en el cerebro de Hermes
            try:
                import gestion_locales
                sn_match = re.search(r"SN:\s*(\w+)", texto_pdf)
                gestion_locales.actualizar_ficha_local(
                    sigla=sigla_archivo,
                    nombre_local=datos_extraidos.get("local", local_val),
                    tecnico=tecnico_val,
                    ticket=ticket_val,
                    ppm=datos_extraidos.get("ppm", 0),
                    shots=datos_extraidos.get("shots", 0),
                    maquina=datos_extraidos.get("maquina", ""),
                    sn=sn_match.group(1) if sn_match else "",
                    estado_cafetera=estado_cafetera,
                    estado_general=resultado_auditoria.get("estado_general", "VERDE_NORMAL"),
                    repuestos=datos_extraidos.get("repuestos", ""),
                    fecha_reporte=fecha_val
                )
            except Exception as e_ficha:
                print(f"[ROW-{idx}] Error al actualizar ficha local del local {sigla_archivo}: {e_ficha}")

        except Exception as ex:
            err_msg = f"Error: {ex}"
            print(f"[ROW-{idx}] Falló el procesamiento de la fila: {err_msg}")
            try:
                worksheet.update_cell(idx, kpi_col_indices["Estado_Proceso"], "ERROR")
                worksheet.update_cell(idx, kpi_col_indices["Detalle_Proceso"], err_msg)
            except Exception as e_sheet:
                print(f"[ROW-{idx}] No se pudo escribir estado de error: {e_sheet}")

        finally:
            if temp_pdf_path.exists():
                try:
                    os.remove(temp_pdf_path)
                except Exception:
                    pass

    # Eliminar directorio temporal si está vacío
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    print("=== INGESTA DESDE FORMULARIO FINALIZADA ===\n")

if __name__ == "__main__":
    ejecutar_ingesta_formulario()
