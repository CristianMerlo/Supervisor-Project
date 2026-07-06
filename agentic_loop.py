import os
import json
import sqlite3
import requests

import glob
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def tool_buscar_local(nombre_o_sigla):
    """Busca en la base de datos la dirección, sigla oficial y datos maestros de un local."""
    conn = sqlite3.connect("/home/cristian/Documentos/Supervisor/supervisor_local.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sigla, nombre, direccion FROM locales WHERE sigla = ? OR nombre LIKE ?", (nombre_o_sigla.upper(), f"%{nombre_o_sigla}%"))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return f"Local encontrado: Sigla oficial: {resultado[0]}, Nombre: {resultado[1]}, Dirección: {resultado[2]}"
    return f"No se encontró ningún local con la sigla o nombre '{nombre_o_sigla}' en la base de datos."

def tool_buscar_pendientes(sigla):
    """Busca las tareas o incidencias pendientes para un local específico."""
    conn = sqlite3.connect("/home/cristian/Documentos/Supervisor/supervisor_local.db")
    cursor = conn.cursor()
    cursor.execute("SELECT detalle, fecha FROM pendientes WHERE sigla = ?", (sigla.upper(),))
    resultados = cursor.fetchall()
    conn.close()
    if resultados:
        resp = f"Pendientes para {sigla}:\n"
        for r in resultados:
            resp += f"- {r[0]} (Registrado: {r[1]})\n"
        return resp
    return f"No hay tareas pendientes registradas para el local {sigla}."

def tool_consultar_error(equipo, codigo_error):
    """Consulta la base de datos estructurada de errores para una máquina."""
    base_errores_path = "/home/cristian/PROYECTOS/Supervisor-Project/brain/base_errores.json"
    if not os.path.exists(base_errores_path):
        return "La base de datos de errores estructurada aún no ha sido generada o está vacía."
    
    try:
        with open(base_errores_path, "r", encoding="utf-8") as f:
            base_errores = json.load(f)
            
        equipo_lower = equipo.lower()
        codigo_lower = str(codigo_error).lower()
        
        # Buscar equipo similar
        equipo_key = None
        for k in base_errores.keys():
            if equipo_lower in k.lower():
                equipo_key = k
                break
                
        if not equipo_key:
            return f"No encontré manuales indexados para el equipo: {equipo}"
            
        # Buscar error
        errores_equipo = base_errores[equipo_key]
        for error in errores_equipo:
            if codigo_lower in str(error.get("codigo", "")).lower() or codigo_lower in str(error.get("falla", "")).lower():
                resp = f"Error encontrado en {equipo_key}:\n"
                resp += f"Código: {error.get('codigo', 'N/A')}\n"
                resp += f"Falla: {error.get('falla', 'N/A')}\n"
                resp += f"Solución: {error.get('solucion', 'N/A')}\n"
                return resp
                
        return f"No se encontró el código de error '{codigo_error}' en la base estructurada de {equipo_key}."
    except Exception as e:
        return f"Error leyendo base de errores: {e}"

def tool_proponer_solucion(maquina, falla, solucion):
    """Propone una solución al Supervisor para que la apruebe antes de registrarla en la Wiki. Úsala cuando deduzcas una solución final en el grupo."""
    try:
        import datetime
        conn = sqlite3.connect("/home/cristian/Documentos/Supervisor/supervisor_local.db")
        c = conn.cursor()
        c.execute("INSERT INTO soluciones_pendientes (maquina, falla, solucion, estado, fecha) VALUES (?, ?, ?, 'PENDIENTE', ?)",
                  (maquina, falla, solucion, datetime.datetime.now().isoformat()))
        sol_id = c.lastrowid
        conn.commit()
        conn.close()
        
        import notificador_telegram
        # Enviar alerta interactiva al supervisor
        msg = f"🔔 *NUEVA SOLUCIÓN DETECTADA EN EL CHAT*\n\n"
        msg += f"🛠 *Máquina:* {maquina}\n"
        msg += f"⚠️ *Falla:* {falla}\n"
        msg += f"💡 *Solución Propuesta:* {solucion}\n\n"
        msg += f"¿Apruebas registrar esto en la Wiki? Responde a este mensaje con:\n`/aprobar {sol_id}` o `/rechazar {sol_id}`"
        
        notificador_telegram.enviar_alerta(msg, agente="Hermes")
        return "He enviado la solución al Supervisor por privado para su aprobación. No la agregaré hasta que él la valide."
    except Exception as e:
        return f"Error proponiendo solución: {e}"

def tool_generar_excel_kpi():
    """Genera un archivo Excel con un balance de KPIs de mantenimiento y viáticos y lo envía al usuario."""
    try:
        import pandas as pd
        import gspread
        from google.oauth2.service_account import Credentials
        from datetime import datetime
        import os
        
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        ruta_credenciales = "/home/cristian/Documentos/Supervisor/credentials.json"
        SHEET_URL = os.environ.get("GOOGLE_SHEET_URL")
        
        creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
        cliente = gspread.authorize(creds)
        sabana = cliente.open_by_url(SHEET_URL)
        
        # Obtener Historial
        hoja_historial = sabana.worksheet("Historial_Mantenimiento")
        registros = hoja_historial.get_all_records()
        df = pd.DataFrame(registros)
        
        # Limpiar datos para el excel
        if not df.empty:
            df["FECHA_REPORTE"] = pd.to_datetime(df["FECHA_REPORTE"], errors="coerce")
            df = df.sort_values(by="FECHA_REPORTE", ascending=False)
            
        ruta_excel = f"/home/cristian/Documentos/Supervisor/Reporte_Mantenimiento_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(ruta_excel, index=False, engine="openpyxl")
        
        return f"¡He generado el archivo Excel con éxito! Aquí tienes el reporte analítico.\n\n[ARCHIVO_ADJUNTO] {ruta_excel}"
    except Exception as e:
        return f"Error generando el Excel: {str(e)}"

def tool_consultar_correos(asunto_o_contenido):
    """Busca en la base de datos de correos recibidos por asunto, contenido o remitente."""
    try:
        conn = sqlite3.connect("/home/cristian/Documentos/Supervisor/supervisor_local.db")
        c = conn.cursor()
        
        palabras = asunto_o_contenido.split()
        if not palabras:
            return "El término de búsqueda está vacío."
            
        condiciones = []
        parametros = []
        for palabra in palabras:
            termino = f"%{palabra}%"
            condiciones.append("(asunto LIKE ? OR cuerpo LIKE ? OR remitente LIKE ?)")
            parametros.extend([termino, termino, termino])
            
        query = f'''SELECT remitente, asunto, fecha, sigla_local, resumen, cuerpo 
                     FROM correos 
                     WHERE {" AND ".join(condiciones)} 
                     ORDER BY fecha DESC LIMIT 5'''
                     
        c.execute(query, parametros)
        resultados = c.fetchall()
        conn.close()
        
        if not resultados:
            return f"No encontré ningún correo relacionado a '{asunto_o_contenido}' en la base de datos."
            
        resp = f"Encontré {len(resultados)} correos relacionados:\n\n"
        for idx, (rem, asu, fec, sig, res, cue) in enumerate(resultados):
            resp += f"--- CORREO {idx+1} ---\n"
            resp += f"De: {rem}\nAsunto: {asu}\nFecha: {fec}\nLocal: {sig}\n"
            resp += f"Resumen IA: {res}\n"
            snippet = cue[:200].replace('\n', ' ') + "..." if len(cue) > 200 else cue.replace('\n', ' ')
            resp += f"Fragmento: {snippet}\n\n"
        return resp
    except Exception as e:
        return f"Error consultando correos: {e}"

def tool_analizar_adjuntos_correo(asunto_o_contenido):
    """Busca un correo en la bandeja de entrada, descarga TODOS sus archivos adjuntos y analiza sus contenidos."""
    import os
    import imaplib
    import email
    from email.header import decode_header
    import tempfile
    import google.generativeai as genai
    from pathlib import Path
    
    user = os.environ.get("GMAIL_USER")
    pas = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pas:
        return "Error: Credenciales de GMail (GMAIL_USER o GMAIL_APP_PASSWORD) no configuradas."
        
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=30)
        mail.login(user, pas)
        mail.select("inbox")
        
        status, mensajes = mail.search(None, 'ALL')
        if status != "OK" or not mensajes[0]:
            mail.logout()
            return "No se encontraron correos en la bandeja de entrada."
            
        target_msg = None
        msg_ids = mensajes[0].split()
        msg_ids.reverse()
        
        for num in msg_ids[:30]:
            status, data = mail.fetch(num, '(RFC822)')
            if status != "OK": continue
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            subject_header = msg.get("Subject")
            subject = ""
            if subject_header:
                decoded = decode_header(subject_header)
                for frag, enc in decoded:
                    if isinstance(frag, bytes):
                        subject += frag.decode(enc or 'utf-8', errors='ignore')
                    else:
                        subject += str(frag)
                        
            if asunto_o_contenido.lower() in subject.lower():
                target_msg = msg
                break
                
        if not target_msg:
            mail.logout()
            return f"No encontré ningún correo reciente con el asunto o término '{asunto_o_contenido}'."
            
        adjuntos_guardados = []
        temp_dir = tempfile.mkdtemp()
        
        for part in target_msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if filename:
                decoded = decode_header(filename)
                decoded_filename = ""
                for frag, enc in decoded:
                    if isinstance(frag, bytes):
                        decoded_filename += frag.decode(enc or 'utf-8', errors='ignore')
                    else:
                        decoded_filename += str(frag)
                
                if decoded_filename:
                    filepath = os.path.join(temp_dir, decoded_filename)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    adjuntos_guardados.append(filepath)
                    
        mail.logout()
        
        if not adjuntos_guardados:
            return f"El correo '{subject}' fue encontrado, pero no contiene ningún archivo adjunto."
            
        resumen_adjuntos = f"Encontré {len(adjuntos_guardados)} archivos adjuntos en el correo '{subject}':\n\n"
        
        # Configurar Gemini
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
        if GEMINI_KEY:
            genai.configure(api_key=GEMINI_KEY)
            
        for path in adjuntos_guardados:
            name = os.path.basename(path)
            resumen_adjuntos += f"📄 *Archivo:* {name}\n"
            
            if name.lower().endswith(".pdf"):
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(path)
                    text = ""
                    for page in reader.pages[:10]:
                        text += page.extract_text() or ""
                    
                    if len(text.strip()) > 50 and GEMINI_KEY:
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        prompt = (
                            "Analiza el siguiente texto extraído de un remito o reporte de trabajos técnicos de un proveedor de mantenimiento:\n\n"
                            f"{text[:8000]}\n\n"
                            "Determina detalladamente:\n"
                            "1. Qué locales (sucursales de Mostaza) son mencionados en los trabajos.\n"
                            "2. Qué tareas específicas (reparación de cafeteras, aires acondicionados, cloacas, etc.) se realizaron en cada local.\n"
                            "Responde de forma clara, técnica y estructurada."
                        )
                        response = model.generate_content(prompt)
                        resumen_adjuntos += f"{response.text}\n\n"
                    else:
                        resumen_adjuntos += f"El PDF no contiene texto extraíble suficiente. (Longitud del texto: {len(text)})\n\n"
                except Exception as e_pdf:
                    resumen_adjuntos += f"Error analizando el contenido del PDF: {e_pdf}\n\n"
            elif name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')) and GEMINI_KEY:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    with open(path, "rb") as img_f:
                        img_data = img_f.read()
                    
                    contents = [
                        {
                            "mime_type": "image/jpeg" if name.lower().endswith(('.jpg', '.jpeg')) else "image/png",
                            "data": img_data
                        },
                        "Analiza esta imagen de un remito o reporte de trabajos técnicos. Identifica el local de Mostaza y detalla los trabajos realizados y firmas correspondientes."
                    ]
                    response = model.generate_content(contents)
                    resumen_adjuntos += f"{response.text}\n\n"
                except Exception as e_img:
                    resumen_adjuntos += f"Error analizando la imagen con IA: {e_img}\n\n"
            else:
                resumen_adjuntos += f"Formato no soportado para análisis automatizado de contenido.\n\n"
                
        return resumen_adjuntos
    except Exception as e:
        return f"Error procesando correo y adjuntos: {e}"

def tool_redactar_correo_borrador(instrucciones_respuesta):
    """Redacta un borrador de correo profesional basado en instrucciones."""
    try:
        import google.generativeai as genai
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
        if not GEMINI_KEY:
            return "No se pudo redactar el borrador (Falta GEMINI_API_KEY en .env)."
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""Eres un asistente ejecutivo profesional. El supervisor de mantenimiento te pide que redactes un borrador de correo en base a las siguientes instrucciones.
El tono debe ser cordial, resolutivo y corporativo.
Instrucciones:
{instrucciones_respuesta}

Redacta el cuerpo del correo listo para copiar y pegar:
"""
        response = model.generate_content(prompt)
        borrador = response.text.strip()
        
        import uuid
        borrador_id = str(uuid.uuid4())[:6]
        path = f"/home/cristian/Documentos/Supervisor/Borrador_{borrador_id}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(borrador)
            
        return f"📝 Borrador redactado exitosamente.\n\n{borrador}\n\n(Puedes copiar este texto para tu correo, o encontrarlo en {path})"
    except Exception as e:
        return f"Error redactando borrador: {e}"

def tool_buscar_manuales(sintoma_falla):
    """Busca en los manuales técnicos (Obsidian/NotebookLM) soluciones a problemas técnicos de equipos usando Búsqueda Semántica Vectorial (RAG)."""
    try:
        import sqlite3
        import json
        import numpy as np
        import google.generativeai as genai
        
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
        if not GEMINI_KEY:
            return "No se pudo realizar la búsqueda vectorial (Falta GEMINI_API_KEY)."
            
        genai.configure(api_key=GEMINI_KEY)
        
        # Generar embedding de la consulta
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=sintoma_falla
        )
        query_vector = np.array(response['embedding'])
        
        # Conectar a la base de datos de vectores
        DB_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/brain/manuales_vectores.db"
        if not os.path.exists(DB_PATH):
            return "La base de datos de vectores no existe aún."
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT archivo_nombre, texto_fragmento, vector FROM manuales_vectores")
        rows = cursor.fetchall()
        
        resultados = []
        for nombre, fragmento, vector_str in rows:
            vector = np.array(json.loads(vector_str))
            
            # Calcular similitud coseno
            dot = np.dot(query_vector, vector)
            norm_q = np.linalg.norm(query_vector)
            norm_v = np.linalg.norm(vector)
            score = dot / (norm_q * norm_v) if (norm_q * norm_v) > 0 else 0
            
            resultados.append({
                "archivo": nombre,
                "fragmento": fragmento,
                "score": score
            })
            
        conn.close()
        
        # Ordenar por similitud descendente
        resultados.sort(key=lambda x: x["score"], reverse=True)
        
        # Tomar los top 2 que superen un umbral razonable
        top_hallazgos = [r for r in resultados[:2] if r["score"] > 0.4]
        
        if top_hallazgos:
            resp = "💡 *Resultados Semánticos Encontrados en Manuales locales:*\n\n"
            for idx, h in enumerate(top_hallazgos, 1):
                resp += f"{idx}. *Documento:* {h['archivo']} (Similitud: {h['score']:.2f})\n"
                resp += f"   *Detalle:* {h['fragmento'][:800]}...\n\n"
            return resp
    except Exception as e:
        print(f"Error en búsqueda semántica local: {e}")
        
    return tool_consultar_manuales_profundo(sintoma_falla)

def tool_consultar_manuales_profundo(consulta):
    """Fallback tipo NotebookLM: Busca profundamente en todos los manuales técnicos subidos a Gemini."""
    try:
        import google.generativeai as genai
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
        if not GEMINI_KEY:
            return "No se pudo consultar NotebookLM/Gemini (Falta GEMINI_API_KEY)."
            
        genai.configure(api_key=GEMINI_KEY)
        
        DB_FILES = "/home/cristian/PROYECTOS/Supervisor-Project/brain/gemini_files.json"
        if not os.path.exists(DB_FILES):
            return "No hay manuales sincronizados en la nube todavía. Espera a que termine la sincronización."
            
        with open(DB_FILES, "r") as f:
            archivos_gemini = json.load(f)
            
        if not archivos_gemini:
            return "No hay manuales subidos al cerebro en la nube."
            
        # Pasar los nombres de los archivos a la API
        uploaded_files = []
        for nombre, datos in archivos_gemini.items():
            try:
                uploaded_files.append(genai.get_file(datos["name"]))
            except Exception:
                pass
                
        if not uploaded_files:
            return "Error recuperando los archivos del cerebro."
            
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"Eres un experto técnico analizando manuales de máquinas (comportándote como NotebookLM). El técnico pregunta: '{consulta}'. Revisa los documentos adjuntos y encuentra la respuesta más precisa. Cita la fuente o máquina."
        
        response = model.generate_content([prompt] + uploaded_files, request_options={"timeout": 60})
        return f"💡 [Respuesta Profunda de Manuales (NotebookLM)]: {response.text}"
        
    except Exception as e:
        return f"Error consultando los manuales profundos: {e}"

def tool_contar_reportes(sigla):
    """Escanea la carpeta de reportes analizados y la carpeta local de la sucursal para contar los informes."""
    archivos_encontrados = []
    
    # 1. Buscar en reportes analizados
    base_dir_analizados = "/home/cristian/Documentos/Supervisor/brain/reportes_analizados/"
    if os.path.exists(base_dir_analizados):
        archivos_encontrados.extend(glob.glob(os.path.join(base_dir_analizados, f"*{sigla}*")))
        
    # 2. Buscar en la carpeta cruda de Locales
    base_dir_locales = "/home/cristian/Documentos/Supervisor/Locales/"
    if os.path.exists(base_dir_locales):
        for carpeta in os.listdir(base_dir_locales):
            if carpeta.startswith(f"[{sigla}]"):
                ruta_carpeta = os.path.join(base_dir_locales, carpeta)
                if os.path.isdir(ruta_carpeta):
                    for f in os.listdir(ruta_carpeta):
                        if os.path.isfile(os.path.join(ruta_carpeta, f)):
                            archivos_encontrados.append(os.path.join(ruta_carpeta, f))
                            
    cantidad = len(archivos_encontrados)
    if cantidad == 0:
        return f"No se encontraron reportes procesados ni originales para la sigla {sigla}."
        
    nombres = [os.path.basename(a) for a in archivos_encontrados[:5]]
    resp = f"Se encontraron {cantidad} reportes para {sigla}."
    if cantidad > 0:
        resp += f" Algunos archivos recientes son: {', '.join(nombres)}"
    return resp

def tool_buscar_tickets(termino_busqueda):
    """Busca en el listado de tickets activos del Linkup ERP (de Mostaza) por sigla de local, nombre, ID de ticket, prioridad o descripción."""
    import json
    from pathlib import Path
    
    ruta_tickets = Path("/home/cristian/PROYECTOS/Supervisor-Project/brain/tickets_activos.json")
    if not ruta_tickets.exists():
        return "No hay datos de tickets activos disponibles en este momento."
        
    try:
        with open(ruta_tickets, "r", encoding="utf-8") as f:
            tickets = json.load(f)
            
        term = termino_busqueda.strip().lower()
        if not term:
            return f"Actualmente hay {len(tickets)} tickets activos en total."
            
        coincidencias = []
        for t in tickets:
            if (term in str(t.get("id", "")).lower() or
                term in t.get("store", "").lower() or
                term in t.get("title", "").lower() or
                term in t.get("description", "").lower() or
                term in t.get("category", "").lower() or
                term in t.get("incidence", "").lower()):
                coincidencias.append(t)
                
        if not coincidencias:
            siglas_candidatas = set()
            csv_path = "/home/cristian/Documentos/Supervisor/locales.csv"
            if not os.path.exists(csv_path):
                csv_path = "/home/cristian/PROYECTOS/Supervisor-Project/locales.csv"
            if os.path.exists(csv_path):
                import csv
                try:
                    with open(csv_path, newline='', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            nombre_local = row.get("LOCAL", "").strip().lower()
                            if term in nombre_local:
                                sigla_sis = row.get("SIGLA SISTEMA", "").strip().upper()
                                sigla_tic = row.get("SIGLA TICKETS", "").strip().upper()
                                if sigla_sis and sigla_sis != "-":
                                    siglas_candidatas.add(sigla_sis)
                                if sigla_tic and sigla_tic != "-":
                                    siglas_candidatas.add(sigla_tic)
                except Exception:
                    pass
            
            # Mapeo manual para Rosario
            if "rosario" in term:
                siglas_candidatas.update(["FPROS", "FMROS", "FRSM", "FORO", "FMPUM"])
                
            for t in tickets:
                if t.get("store", "").upper() in siglas_candidatas:
                    coincidencias.append(t)
                    
        if not coincidencias:
            return f"No encontré ningún ticket activo que coincida con el término '{termino_busqueda}'."
            
        resp = f"Encontré {len(coincidencias)} tickets activos relacionados:\n\n"
        for t in coincidencias[:10]:
            resp += f"--- TICKET {t.get('id')} ({t.get('statusName', 'open').upper()}) ---\n"
            resp += f"Local: {t.get('store')} | Prioridad: {t.get('priority')}\n"
            resp += f"Categoría/Incidencia: {t.get('category')} / {t.get('incidence')}\n"
            resp += f"Detalle: {t.get('title')}\n"
            desc = t.get('description', '')
            snippet = desc[:150].replace('\n', ' ') + "..." if len(desc) > 150 else desc.replace('\n', ' ')
            resp += f"Descripción: {snippet}\n\n"
            
        if len(coincidencias) > 10:
            resp += f"... y otros {len(coincidencias) - 10} tickets más."
            
        return resp
    except Exception as e:
        return f"Error consultando tickets activos: {e}"

def tool_guardar_memoria_diagnostico(sigla, resumen_falla, solucion=None, repuestos=None):
    """Guarda un registro de falla, diagnóstico, repuestos recomendados y resolución en la base de datos de memoria histórica del local."""
    import sqlite3
    import datetime
    db_path = "/home/cristian/Documentos/Supervisor/supervisor_local.db"
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO memoria_diagnostico (sigla, fecha, resumen_falla, solucion, repuestos) VALUES (?, ?, ?, ?, ?)",
            (sigla.upper().strip(), fecha, resumen_falla.strip(), solucion, repuestos)
        )
        conn.commit()
        conn.close()
        return f"Éxito: Se guardó el registro de memoria de diagnóstico histórico para el local {sigla}."
    except Exception as e:
        return f"Error guardando memoria de diagnóstico: {e}"

def tool_consultar_memoria_diagnostico(sigla):
    """Consulta todo el historial de diagnósticos y fallas pasadas registradas para un local en base a su sigla."""
    import sqlite3
    db_path = "/home/cristian/Documentos/Supervisor/supervisor_local.db"
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT fecha, resumen_falla, solucion, repuestos FROM memoria_diagnostico WHERE sigla = ? ORDER BY fecha DESC",
            (sigla.upper().strip(),)
        )
        rows = c.fetchall()
        conn.close()
        if not rows:
            return f"No hay registros de memoria diagnóstica histórica para el local {sigla}."
        
        resultado = f"Historial de Memoria Diagnóstica para {sigla}:\n"
        for i, row in enumerate(rows, 1):
            resultado += f"\n[{i}] Fecha: {row[0]}\n"
            resultado += f"• Falla: {row[1]}\n"
            if row[2]:
                resultado += f"• Solución: {row[2]}\n"
            if row[3]:
                resultado += f"• Repuestos sugeridos: {row[3]}\n"
        return resultado
    except Exception as e:
        return f"Error consultando memoria de diagnóstico: {e}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "tool_buscar_local",
            "description": "Busca la dirección y datos maestros de un local usando su nombre o sigla",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_o_sigla": {"type": "string", "description": "Nombre o sigla del local a buscar"}
                },
                "required": ["nombre_o_sigla"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_buscar_pendientes",
            "description": "Busca las tareas o incidencias pendientes críticas para un local",
            "parameters": {
                "type": "object",
                "properties": {
                    "sigla": {"type": "string", "description": "Sigla del local"}
                },
                "required": ["sigla"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_buscar_manuales",
            "description": "Busca en los manuales técnicos para resolver fallas de máquinas y equipos",
            "parameters": {
                "type": "object",
                "properties": {
                    "sintoma_falla": {"type": "string", "description": "Descripción del síntoma o código de error"}
                },
                "required": ["sintoma_falla"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_contar_reportes",
            "description": "Cuenta y lista los reportes de mantenimiento técnicos para un local",
            "parameters": {
                "type": "object",
                "properties": {
                    "sigla": {"type": "string", "description": "Sigla del local (ej: FSJU, FVDP)"}
                },
                "required": ["sigla"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_consultar_antigravity",
            "description": "Contacta al agente AntiGravity para problemas de código o infraestructura de servidores",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta_tecnica": {"type": "string", "description": "Detalle del problema"}
                },
                "required": ["consulta_tecnica"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_consultar_error",
            "description": "Consulta la base de datos estructurada para buscar el significado y solución de un código de error específico de una máquina.",
            "parameters": {
                "type": "object",
                "properties": {
                    "equipo": {"type": "string", "description": "Nombre de la máquina o equipo (ej: Cimbali, Taylor)"},
                    "codigo_error": {"type": "string", "description": "Código de error o síntoma principal (ej: E04, 53)"}
                },
                "required": ["equipo", "codigo_error"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_generar_excel_kpi",
            "description": "¡IMPORTANTE! Usa esta herramienta ÚNICAMENTE cuando el usuario pida armar o generar un Excel (.xlsx) con el reporte de mantenimiento o KPIs. Descarga los datos y se los envía como archivo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmar": {"type": "boolean", "description": "Pasa true para confirmar la generación."}
                },
                "required": ["confirmar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_proponer_solucion",
            "description": "Extrae de la conversación una falla y su solución definitiva confirmada y la envía al Supervisor para su revisión. NUNCA inventes soluciones. Úsala solo cuando un técnico valide que arregló el equipo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "maquina": {"type": "string", "description": "Nombre de la máquina (ej: 'Cimbali S30', 'Taylor C713')"},
                    "falla": {"type": "string", "description": "Descripción del problema o código de error reportado por el técnico."},
                    "solucion": {"type": "string", "description": "Paso a paso de cómo el técnico arregló el problema según sus mensajes."}
                },
                "required": ["maquina", "falla", "solucion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_consultar_correos",
            "description": "Busca y resume correos electrónicos recibidos en la bandeja de entrada del supervisor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asunto_o_contenido": {"type": "string", "description": "Término de búsqueda, nombre de local, remitente o tema del correo"}
                },
                "required": ["asunto_o_contenido"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_redactar_correo_borrador",
            "description": "Redacta un borrador de correo profesional para responder a una situación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instrucciones_respuesta": {"type": "string", "description": "Lo que debe decir el correo"}
                },
                "required": ["instrucciones_respuesta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_analizar_adjuntos_correo",
            "description": "Busca un correo electrónico por término en el asunto, descarga todos sus archivos adjuntos (PDFs, imágenes) y analiza su contenido técnico para reportar trabajos realizados por local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asunto_o_contenido": {"type": "string", "description": "Término de búsqueda del asunto del correo (ej: 'EVETEC')"}
                },
                "required": ["asunto_o_contenido"]
            }
        }
    ,
    {
        "type": "function",
        "function": {
            "name": "tool_buscar_tickets",
            "description": "Busca en el listado de tickets activos del Linkup ERP (Mostaza) por sigla de local, nombre del local, ID de ticket o descripción.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termino_busqueda": {"type": "string", "description": "Término a buscar (ej: 'rosario', 'FPROS', 'display', '128459')"}
                },
                "required": ["termino_busqueda"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_guardar_memoria_diagnostico",
            "description": "Guarda un registro de diagnóstico histórico de falla, solución y repuestos recomendados para un local específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sigla": {"type": "string", "description": "Sigla del local (ej: FLIN, FSJU)"},
                    "resumen_falla": {"type": "string", "description": "Descripción resumida de la falla y diagnóstico técnico"},
                    "solucion": {"type": "string", "description": "Detalle de la resolución o reparación ejecutada"},
                    "repuestos": {"type": "string", "description": "Repuestos e insumos recomendados o utilizados"}
                },
                "required": ["sigla", "resumen_falla"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_consultar_memoria_diagnostico",
            "description": "Consulta el historial de fallas y diagnósticos anteriores registrados para un local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sigla": {"type": "string", "description": "Sigla del local a consultar"}
                },
                "required": ["sigla"]
            }
        }
    }
]

def execute_tool(tool_name, arguments_str):
    try:
        args = json.loads(arguments_str)
        if tool_name == "tool_buscar_local":
            return tool_buscar_local(args.get("nombre_o_sigla", ""))
        elif tool_name == "tool_buscar_pendientes":
            return tool_buscar_pendientes(args.get("sigla", ""))
        elif tool_name == "tool_buscar_manuales":
            return tool_buscar_manuales(args.get("sintoma_falla", ""))
        elif tool_name == "tool_contar_reportes":
            return tool_contar_reportes(args.get("sigla", ""))
        elif tool_name == "tool_consultar_antigravity":
            return tool_consultar_antigravity(args.get("consulta_tecnica", ""))
        elif tool_name == "tool_consultar_error":
            return tool_consultar_error(args.get("equipo", ""), args.get("codigo_error", ""))
        elif tool_name == "tool_proponer_solucion":
            return tool_proponer_solucion(args.get("maquina", ""), args.get("falla", ""), args.get("solucion", ""))
        elif tool_name == "tool_generar_excel_kpi":
            return tool_generar_excel_kpi()
        elif tool_name == "tool_consultar_correos":
            return tool_consultar_correos(args.get("asunto_o_contenido", ""))
        elif tool_name == "tool_analizar_adjuntos_correo":
            return tool_analizar_adjuntos_correo(args.get("asunto_o_contenido", ""))
        elif tool_name == "tool_redactar_correo_borrador":
            return tool_redactar_correo_borrador(args.get("instrucciones_respuesta", ""))
        elif tool_name == "tool_consultar_manuales_profundo":
            return tool_consultar_manuales_profundo(args.get("consulta", ""))
        elif tool_name == "tool_buscar_tickets":
            return tool_buscar_tickets(args.get("termino_busqueda", ""))
        elif tool_name == "tool_guardar_memoria_diagnostico":
            return tool_guardar_memoria_diagnostico(
                args.get("sigla", ""), 
                args.get("resumen_falla", ""), 
                args.get("solucion", ""), 
                args.get("repuestos", "")
            )
        elif tool_name == "tool_consultar_memoria_diagnostico":
            return tool_consultar_memoria_diagnostico(args.get("sigla", ""))
        else:
            return f"Herramienta desconocida: {tool_name}"
    except Exception as e:
        return f"Error ejecutando herramienta {tool_name}: {e}"

def consultar_agentic_loop(mensaje_usuario, historial, system_prompt):
    """Ejecuta el bucle de razonamiento usando Gemini (vía API compatible con OpenAI) o Groq como resguardo."""
    import config_manager
    model_gemini = config_manager.get_env_var("MODEL_GEMINI_TEXT", "gemini-2.5-flash")
    model_groq = config_manager.get_env_var("MODEL_GROQ_TEXT", "llama-3.3-70b-versatile")
    
    api_provider = "gemini"
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        api_provider = "groq"
        
    # Cargar Perfil de Respuestas (Tono y Estilo de Cristian)
    perfil_path = "/home/cristian/Documentos/Supervisor/perfil_respuestas_cristian.md"
    if os.path.exists(perfil_path):
        try:
            with open(perfil_path, "r", encoding="utf-8") as f:
                perfil_texto = f.read()
            system_prompt += f"\n\nTONO Y ESTILO DE REDACCIÓN COMPROMETIDO (Sigue estrictamente estas directrices y ejemplos):\n{perfil_texto}\n"
        except Exception:
            pass
            
    # Cargar Correcciones Semánticas Few-Shot Dinámicas
    try:
        import sys
        ruta_dir = "/home/cristian/Documentos/Supervisor"
        if ruta_dir not in sys.path:
            sys.path.append(ruta_dir)
        import gestion_correcciones
        correcciones = gestion_correcciones.obtener_correcciones_relevantes(mensaje_usuario, limit=2)
        if correcciones:
            corr_prompt = "\n⚠️ CORRECCIONES DE HISTORIAL DE DECISIONES DEL SUPERVISOR (Úsalas como Few-Shot dinámico):\n"
            for q, r_inc, corr in correcciones:
                corr_prompt += f"- Ante la pregunta/situación: '{q}'\n  Evita responder como: '{r_inc}'\n  Respuesta correcta aprobada por el Supervisor: '{corr}'\n"
            system_prompt += corr_prompt
    except Exception as e_corr:
        print(f"Error cargando Few-Shot dinámico: {e_corr}")
    
    # Inyección vital para evitar loops y alucinaciones
    system_prompt += """
REGLAS VITALES DE COMPORTAMIENTO PARA HERRAMIENTAS Y RAZONAMIENTO:
1. Utiliza estrictamente el esquema JSON provisto para invocar herramientas. NUNCA escribas etiquetas XML o pseudo-código como <function=...>. Si necesitas datos, invoca la herramienta por la API oficial.
2. Si buscas en un manual o base de datos y no encuentras la respuesta esperada, NO repitas la misma búsqueda con los mismos argumentos. Informa al usuario que no tienes ese dato específico.
3. NO alucines datos. Si no encuentras la información, admite que no la tienes y finaliza tu respuesta.
4. RAZONAMIENTO ESTRUCTURADO (Chain of Thought - CoT): De forma obligatoria, antes de llamar a cualquier herramienta o emitir tu respuesta final, debes escribir tu análisis técnico paso a paso encerrado entre etiquetas <razonamiento> y </razonamiento>. Analiza allí qué datos te faltan, qué herramientas invocarás y qué hipótesis técnicas manejas sobre la falla.
"""
    
    if historial:
        historial_texto = "Historial reciente de la conversación (para tu memoria):\n"
        for msg in historial[-5:]:
            rol = "Usuario" if msg["role"] == "user" else "Hermes"
            contenido_seguro = str(msg['content'])[:1000] + ("..." if len(str(msg['content'])) > 1000 else "")
            historial_texto += f"{rol}: {contenido_seguro}\n"
        system_prompt += f"\n\n{historial_texto}"
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": mensaje_usuario})
    
    max_iterations = 4
    for _ in range(max_iterations):
        if api_provider == "gemini":
            active_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            active_headers = {
                "Authorization": f"Bearer {gemini_key}",
                "Content-Type": "application/json"
            }
            active_model = model_gemini
        else:
            active_url = "https://api.groq.com/openai/v1/chat/completions"
            active_headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            active_model = model_groq

        payload = {
            "model": active_model,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "tool_choice": "auto"
        }
        
        try:
            res = requests.post(active_url, headers=active_headers, json=payload, timeout=60)
            
            # 1. Fallback: Si Gemini falla, rotar a Groq de inmediato
            if res.status_code != 200 and api_provider == "gemini":
                with open("groq_error.log", "a") as f:
                    f.write(f"Gemini API falló con {res.status_code}. Rotando a Groq...\n")
                api_provider = "groq"
                active_url = "https://api.groq.com/openai/v1/chat/completions"
                active_headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload["model"] = model_groq
                res = requests.post(active_url, headers=active_headers, json=payload, timeout=60)
                
            # 2. Fallback: Si Groq da 429 (Rate limit), rotar a llama-3.1-8b-instant
            if res.status_code == 429 and api_provider == "groq":
                with open("groq_error.log", "a") as f:
                    f.write(f"Groq API falló con 429. Rotando a llama-3.1-8b-instant...\n")
                payload["model"] = "llama-3.1-8b-instant"
                res = requests.post(active_url, headers=active_headers, json=payload, timeout=60)

            if res.status_code != 200:
                with open("groq_error.log", "a") as f:
                    f.write(f"Error de API final: {res.status_code} - {res.text}\n")
                
                try:
                    error_data = res.json()
                    if error_data.get("error", {}).get("code") == "tool_use_failed":
                        failed_gen = error_data["error"].get("failed_generation", "")
                        import re
                        name_match = re.search(r'<function=(\w+)', failed_gen)
                        if name_match:
                            tool_name = name_match.group(1)
                            json_match = re.search(r'(\{.*?\})', failed_gen, re.DOTALL)
                            if json_match:
                                args_str = json_match.group(1)
                            else:
                                args_match = re.search(r'<function=\w+\((.*?)\)', failed_gen)
                                args_str = args_match.group(1) if args_match else "{}"
                                
                            tool_result = execute_tool(tool_name, args_str)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": f"call_auto_{tool_name}",
                                "name": tool_name,
                                "content": str(tool_result)
                            })
                            continue
                except Exception as e_recovery:
                    with open("groq_error.log", "a") as f:
                        f.write(f"Auto-recovery falló: {e_recovery}\n")
                
                return f"Ocurrió un error al contactar al modelo de razonamiento. {res.status_code}"
            
            data = res.json()
            response_message = data["choices"][0]["message"]
            
            if response_message.get("tool_calls"):
                messages.append(response_message)
                for tool_call in response_message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    arguments = tool_call["function"]["arguments"]
                    
                    tool_result = execute_tool(tool_name, arguments)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_name,
                        "content": str(tool_result)
                    })
                continue
            
            content = response_message.get("content", "Sin respuesta.")
            
            # Extraer y limpiar razonamiento CoT
            if "<razonamiento>" in content and "</razonamiento>" in content:
                import re
                try:
                    razonamiento_match = re.search(r'<razonamiento>(.*?)</razonamiento>', content, re.DOTALL)
                    if razonamiento_match:
                        razonamiento = razonamiento_match.group(1).strip()
                        # Registrar razonamiento para auditoría
                        log_path = "/home/cristian/Documentos/Supervisor/brain/razonamientos.log"
                        os.makedirs(os.path.dirname(log_path), exist_ok=True)
                        from datetime import datetime
                        with open(log_path, "a", encoding="utf-8") as f_log:
                            f_log.write(f"=== RAZONAMIENTO [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
                            f_log.write(f"Pregunta: {mensaje_usuario}\n")
                            f_log.write(f"Análisis CoT:\n{razonamiento}\n")
                            f_log.write("=" * 60 + "\n\n")
                    
                    # Limpiar el contenido final
                    content = re.sub(r'<razonamiento>.*?</razonamiento>', '', content, flags=re.DOTALL).strip()
                except Exception as e_cot:
                    print(f"Error procesando CoT: {e_cot}")
                    
            return content
            
        except Exception as e:
            return f"Error en el bucle agentic: {e}"
            
    return "Error: Se alcanzó el límite máximo de razonamiento sin llegar a una respuesta final."
