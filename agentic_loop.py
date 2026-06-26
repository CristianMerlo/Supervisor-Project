import os
import json
import sqlite3
import requests
import subprocess
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
        conn = sqlite3.connect("/home/cristian/PROYECTOS/Supervisor-Project/supervisor_local.db")
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
        conn = sqlite3.connect("/home/cristian/PROYECTOS/Supervisor-Project/supervisor_local.db")
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
    """Busca en los manuales técnicos (Obsidian/NotebookLM) soluciones a problemas técnicos de equipos."""
    try:
        from obsidian_bridge import ObsidianVault
        vault = ObsidianVault()
        hallazgos = vault.buscar_manual(sintoma_falla)
        if hallazgos:
            resp = "Información encontrada en manuales locales:\n"
            for h in hallazgos[:2]:
                resp += f"- {h['contexto']}\n"
            return resp
    except Exception as e:
        pass
    
    # Fallback to NotebookLM
    try:
        nlm_path = "/home/cristian/.local/bin/nlm"
        res_nlm = subprocess.run([nlm_path, "cross", "query", sintoma_falla, "--all"], capture_output=True, text=True)
        if res_nlm.returncode == 0 and res_nlm.stdout.strip():
            return f"Información encontrada en NotebookLM:\n{res_nlm.stdout.strip()[:1000]}"
    except:
        pass
    return f"No se encontró información en los manuales sobre: {sintoma_falla}"

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

def tool_consultar_antigravity(consulta_tecnica):
    """Usa esta herramienta cuando el usuario pregunte por algo de código, scripts, infraestructura o logs que tú no puedas responder."""
    return f"He notificado a AntiGravity sobre esto: '{consulta_tecnica}'. Él revisará los logs."

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
        elif tool_name == "tool_redactar_correo_borrador":
            return tool_redactar_correo_borrador(args.get("instrucciones_respuesta", ""))
        else:
            return f"Herramienta desconocida: {tool_name}"
    except Exception as e:
        return f"Error ejecutando herramienta {tool_name}: {e}"

def consultar_agentic_loop(mensaje_usuario, historial, system_prompt):
    """Ejecuta el bucle de razonamiento usando Groq con Tool Calling."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Inyección vital para evitar loops y alucinaciones
    system_prompt += """
REGLAS VITALES DE COMPORTAMIENTO PARA HERRAMIENTAS:
1. Utiliza estrictamente el esquema JSON provisto para invocar herramientas. NUNCA escribas etiquetas XML o pseudo-código como <function=...>. Si necesitas datos, invoca la herramienta por la API oficial.
2. Si buscas en un manual (o cualquier base de datos) y no encuentras la respuesta esperada, NO repitas la misma búsqueda con los mismos argumentos. Informa al usuario que no tienes ese dato específico.
3. NO alucines datos. Si no encuentras la información, admite que no la tienes y finaliza tu respuesta.
"""
    
    # Convertir el historial en texto para inyectarlo en el system_prompt y evitar errores de parseo de Tool Calling en Groq
    if historial:
        historial_texto = "Historial reciente de la conversación (para tu memoria):\n"
        for msg in historial[-5:]: # Limitar a los últimos 5 mensajes
            rol = "Usuario" if msg["role"] == "user" else "Hermes"
            # Limitar la longitud del contenido para no explotar la cuota de Groq
            contenido_seguro = str(msg['content'])[:1000] + ("..." if len(str(msg['content'])) > 1000 else "")
            historial_texto += f"{rol}: {contenido_seguro}\n"
        system_prompt += f"\n\n{historial_texto}"
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": mensaje_usuario})
    
    max_iterations = 4
    for _ in range(max_iterations):
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "tool_choice": "auto"
        }
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if res.status_code != 200:
                with open("groq_error.log", "a") as f:
                    f.write(f"Error de API: {res.status_code} - {res.text}\n")
                
                # Intentar auto-recuperar si Groq falló al parsear la herramienta (400 tool_use_failed)
                try:
                    error_data = res.json()
                    if error_data.get("error", {}).get("code") == "tool_use_failed":
                        failed_gen = error_data["error"].get("failed_generation", "")
                        import re
                        match = re.search(r'<function=(\w+)\((.*?)\)</function>', failed_gen)
                        if match:
                            tool_name = match.group(1)
                            args_str = match.group(2)
                            tool_result = execute_tool(tool_name, args_str)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": f"call_auto_{tool_name}",
                                "name": tool_name,
                                "content": str(tool_result)
                            })
                            continue # Reintentar el loop con el resultado
                except Exception:
                    pass
                
                return f"Ocurrió un error al contactar al modelo de razonamiento. {res.status_code}"
            
            data = res.json()
            response_message = data["choices"][0]["message"]
            
            # Si el modelo decidió llamar a una o más herramientas
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
                # Volver al inicio del loop con los resultados de la herramienta
                continue
            
            # Si no llamó herramientas, devolvemos el contenido de texto final
            return response_message.get("content", "Sin respuesta.")
            
        except Exception as e:
            return f"Error en el bucle agentic: {e}"
            
    return "Error: Se alcanzó el límite máximo de razonamiento sin llegar a una respuesta final."
