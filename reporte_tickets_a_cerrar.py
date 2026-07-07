#!/usr/bin/env python3
import os
import sys
import glob
import asyncio
import pandas as pd
from datetime import datetime

# Agregar la ruta del proyecto al path de Python
PROJECT_ROOT = "/home/cristian/PROYECTOS/Supervisor-Project"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import descargar_bases_tickets
import descargar_historico_tickets
import motor_supervisor
import notificador_telegram

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando relevamiento de tickets a cerrar...")
    
    # 1. Descargar base de la API (Locales Propios - Canal 1 & Franquicias - Canal 2)
    try:
        print("[*] Descargando bases de tickets vía API...")
        descargar_bases_tickets.main()
    except Exception as e:
        print(f"Error descargando tickets de la API: {e}")

    # 2. Descargar base de la Web (Historial de Tickets / Métricas - Canal 2)
    try:
        print("[*] Descargando historial de tickets vía Web Scraping...")
        asyncio.run(descargar_historico_tickets.run())
    except Exception as e:
        print(f"Error descargando historial de tickets vía Web Scraping: {e}")

    fecha_hoy_str = datetime.now().strftime("%Y%m%d")
    fecha_hoy_guiones = datetime.now().strftime("%Y-%m-%d")
    
    # Rutas de los archivos
    excel_api_path = os.path.join(PROJECT_ROOT, f"Base_Tickets_Mostaza_{fecha_hoy_str}.xlsx")
    excel_web_path = "/home/cristian/Documentos/Supervisor/base_tickets/Historial_Tickets.xlsx"

    # 3. Cargar y Unificar Bases de Tickets
    open_tickets = {} # Diccionario unificado: { ticket_id: {datos} }

    # Cargar base API
    if os.path.exists(excel_api_path):
        try:
            xls_api = pd.ExcelFile(excel_api_path)
            for sheet in xls_api.sheet_names:
                df = pd.read_excel(xls_api, sheet_name=sheet)
                print(f"[API] Cargados {len(df)} tickets desde la pestaña '{sheet}'.")
                
                # Filtrar lista de mantenimiento
                if 'category' in df.columns:
                    df = df[df['category'].astype(str).str.upper() != 'LISTA DE MANTENIMIENTO']
                if 'incidence_breadcrumb' in df.columns:
                    df = df[~df['incidence_breadcrumb'].astype(str).str.upper().str.contains('LISTA DE MANTENIMIENTO', na=False)]
                
                for _, row in df.iterrows():
                    t_id = str(row.get('id', '')).strip()
                    if t_id and t_id != 'nan':
                        open_tickets[t_id] = {
                            'ticket_id': t_id,
                            'titulo': row.get('title', 'Sin título'),
                            'local': row.get('store', 'Desconocido'),
                            'prioridad': row.get('priority', 'Normal'),
                            'origen': f"{sheet} (API)"
                        }
        except Exception as e:
            print(f"Error procesando base de tickets API: {e}")
    else:
        print(f"[!] No se encontró el archivo de la API en {excel_api_path}")

    # Cargar base Web (Historial)
    if os.path.exists(excel_web_path):
        try:
            df_web = pd.read_excel(excel_web_path)
            print(f"[WEB] Cargados {len(df_web)} tickets desde el historial web.")
            
            # Filtrar activos (que no estén Resueltos o Cerrados)
            if 'Estado' in df_web.columns:
                df_web = df_web[~df_web['Estado'].astype(str).str.upper().isin(['RESUELTO', 'CERRADO'])]
                
            # Filtrar lista de mantenimiento
            if 'Categoría' in df_web.columns:
                df_web = df_web[df_web['Categoría'].astype(str).str.upper() != 'LISTA DE MANTENIMIENTO']
                
            print(f"[WEB] Quedan {len(df_web)} tickets activos después de filtrar.")
            
            for _, row in df_web.iterrows():
                t_id = str(row.get('Código', '')).strip()
                if t_id and t_id != 'nan':
                    # Si ya existe en la API, respetamos el de la API o combinamos, si no, agregamos
                    if t_id not in open_tickets:
                        open_tickets[t_id] = {
                            'ticket_id': t_id,
                            'titulo': row.get('Título', 'Sin título'),
                            'local': row.get('Sucursal', 'Desconocido'),
                            'prioridad': row.get('Prioridad', 'Normal'),
                            'origen': "Historial Franquicias (Web)"
                        }
        except Exception as e:
            print(f"Error procesando base de tickets Web (Historial): {e}")
    else:
        print(f"[!] No se encontró el archivo de historial web en {excel_web_path}")

    print(f"[+] Total de tickets activos consolidados en memoria: {len(open_tickets)}")

    # 4. Buscar PDFs recibidos hoy en la carpeta original
    pdf_dir = os.path.join(PROJECT_ROOT, "brain", "locales", "PDFs_Originales")
    pattern = os.path.join(pdf_dir, f"*{fecha_hoy_guiones}*.pdf")
    today_pdfs = glob.glob(pattern)
    
    # Buscar por fecha de modificación como fallback
    if not today_pdfs:
        print("Buscando PDFs por fecha de modificación de hoy...")
        for f in glob.glob(os.path.join(pdf_dir, "*.pdf")):
            mtime = os.path.getmtime(f)
            mdate = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            if mdate == fecha_hoy_guiones:
                today_pdfs.append(f)
                
    if not today_pdfs:
        mensaje_no_tickets = (
            f"🧹 *RELEVAMIENTO DE TICKETS DIARIOS*\n\n"
            f"Hoy ({datetime.now().strftime('%d/%m/%Y')}) no se registraron reportes técnicos en formato PDF procesados en el sistema. "
            f"No hay tickets para cerrar."
        )
        notificador_telegram.enviar_alerta(mensaje_no_tickets, agente="Antigravity")
        print("No se encontraron reportes PDF hoy.")
        return

    # 5. Procesar PDFs de hoy
    reports_data = []
    for pdf_path in today_pdfs:
        try:
            datos, resultado, _ = motor_supervisor.procesar_reporte(pdf_path)
            datos['filename'] = os.path.basename(pdf_path)
            reports_data.append(datos)
        except Exception as e:
            print(f"Error procesando {pdf_path}: {e}")

    # 6. Cruzar reportes de hoy con la base unificada de tickets activos
    matches = []
    for rep in reports_data:
        ticket_rep = str(rep.get('ticket')).strip()
        if not ticket_rep or ticket_rep == '0' or ticket_rep == 'None':
            continue
            
        # Buscar en el diccionario consolidado de tickets activos
        if ticket_rep in open_tickets:
            t_data = open_tickets[ticket_rep]
            matches.append({
                'local': rep.get('local', t_data['local']),
                'sigla': rep.get('sigla', 'Desconocido'),
                'tecnico': rep.get('tecnico', 'Desconocido'),
                'ticket': ticket_rep,
                'titulo': t_data['titulo'],
                'origen': t_data['origen']
            })

    # 7. Enviar reporte por Telegram
    if not matches:
        mensaje_cruce_vacio = (
            f"🧹 *RELEVAMIENTO DE TICKETS DIARIOS*\n\n"
            f"Se detectaron {len(today_pdfs)} informes técnicos procesados hoy ({datetime.now().strftime('%d/%m/%Y')}), "
            f"pero ninguno corresponde a un ticket abierto registrado actualmente en la mesa de ayuda (cruzando las 3 bases de la API y Web)."
        )
        notificador_telegram.enviar_alerta(mensaje_cruce_vacio, agente="Antigravity")
        print("No se encontraron tickets abiertos cruzados hoy.")
        return

    # Construir mensaje final con las coincidencias encontradas
    mensaje_telegram = (
        f"🧹 *RELEVAMIENTO DE TICKETS DIARIOS*\n"
        f"Relevé los reportes recibidos hoy ({datetime.now().strftime('%d/%m/%Y')}) y los crucé con las 3 bases de tickets activas (API Locales Propios, API Franquicias e Historial Web).\n\n"
        f"Aquí tienes la lista de los *{len(matches)} tickets activos* en la mesa de ayuda que ya cuentan con su correspondiente informe técnico procesado hoy y que, por lo tanto, *ya se pueden cerrar*:\n\n"
    )
    
    for m in matches:
        mensaje_telegram += (
            f"• *Ticket #{m['ticket']}* (encontrado en {m['origen']})\n"
            f"  *Local:* {m['local']} ({m['sigla']})\n"
            f"  *Técnico:* {m['tecnico']}\n"
            f"  *Detalle:* {m['titulo']}\n\n"
        )
        
    exito = notificador_telegram.enviar_alerta(mensaje_telegram, agente="Antigravity")
    if exito:
        print("Mensaje de reporte enviado con éxito a Telegram.")
    else:
        print("Error al enviar el reporte a Telegram.")

if __name__ == "__main__":
    main()
