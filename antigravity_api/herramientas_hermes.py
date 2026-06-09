import os
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno del directorio padre (.env principal)
base_dir = Path(__file__).parent
parent_env = base_dir.parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env)
else:
    load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing"
SHEET_URL = os.getenv("SHEETS_SABANA_URL", DEFAULT_SHEET_URL)

def _obtener_sabana():
    # Ruta absoluta para credentials.json para garantizar que funcione bajo systemd
    ruta_credenciales = base_dir.parent / "credentials.json"
    if not ruta_credenciales.exists():
        ruta_credenciales = base_dir / "credentials.json"
    
    if not ruta_credenciales.exists():
        raise FileNotFoundError(f"No se encontró credentials.json en: {base_dir.parent} ni en {base_dir}")
        
    creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
    cliente = gspread.authorize(creds)
    return cliente.open_by_url(SHEET_URL)

def consultar_datos_maestros_local(sigla_o_nombre: str) -> str:
    """Consulta la información estática de un local (supervisor, dirección, regional, mail, etc) basado en su sigla (ej: FVDP, FBER) o su nombre comercial (ej: Berazategui, Rotonda)."""
    print(f"[TOOL-CALL] consultar_datos_maestros_local con argumento: '{sigla_o_nombre}'", flush=True)
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Locales_Maestro")
        registros = hoja.get_all_records()
        busqueda = sigla_o_nombre.upper().strip()
        
        # 1. Buscar por coincidencia exacta de siglas
        for fila in registros:
            if str(fila.get('SIGLA SISTEMA', '')).upper() == busqueda or str(fila.get('SIGLA TICKETS', '')).upper() == busqueda:
                print(f"[TOOL-RESULT] Local encontrado por sigla: {fila.get('LOCAL')}", flush=True)
                return str(fila)
                
        # 2. Buscar si el nombre del local contiene el término de búsqueda
        for fila in registros:
            if busqueda in str(fila.get('LOCAL', '')).upper():
                print(f"[TOOL-RESULT] Local encontrado por nombre: {fila.get('LOCAL')}", flush=True)
                return str(fila)
                
        print(f"[TOOL-RESULT] No se encontró ningún local para: '{sigla_o_nombre}'", flush=True)
        return f"No se encontró ningún local con sigla o nombre '{sigla_o_nombre}' en la base de datos."
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_datos_maestros_local: {e}", flush=True)
        return f"Error consultando la base: {str(e)}"

def consultar_ultimo_mantenimiento(sigla_o_nombre: str) -> str:
    """Devuelve el último reporte de mantenimiento para un local basado en su sigla (ej: FVDP) o nombre comercial (ej: Berazategui, Rotonda)."""
    print(f"[TOOL-CALL] consultar_ultimo_mantenimiento con argumento: '{sigla_o_nombre}'", flush=True)
    try:
        sabana = _obtener_sabana()
        busqueda = sigla_o_nombre.upper().strip()
        
        # Primero, intentar encontrar la sigla en la pestaña maestra de locales
        hoja_maestro = sabana.worksheet("Locales_Maestro")
        registros_maestro = hoja_maestro.get_all_records()
        
        sigla_encontrada = None
        for fila in registros_maestro:
            if busqueda in [str(fila.get('SIGLA SISTEMA', '')).upper(), str(fila.get('SIGLA TICKETS', '')).upper()]:
                sigla_encontrada = str(fila.get('SIGLA SISTEMA', '')).upper()
                break
            if busqueda in str(fila.get('LOCAL', '')).upper():
                sigla_encontrada = str(fila.get('SIGLA SISTEMA', '')).upper()
                break
                
        if not sigla_encontrada:
            # Fallback: Usar el término de búsqueda directamente si no se encontró en el maestro
            sigla_encontrada = busqueda
            
        hoja = sabana.worksheet("Historial_Mantenimiento")
        registros = hoja.get_all_records()
        
        # Filtrar por la sigla resuelta
        reportes_local = [r for r in registros if str(r.get('SIGLA', '')).upper() == sigla_encontrada]
        
        if not reportes_local:
            print(f"[TOOL-RESULT] No hay mantenimientos para: '{sigla_o_nombre}' (sigla: {sigla_encontrada})", flush=True)
            return f"No hay reportes de mantenimiento registrados para el local '{sigla_o_nombre}' (sigla: {sigla_encontrada})."
            
        ultimo = reportes_local[-1] # El más reciente
        print(f"[TOOL-RESULT] Mantenimiento encontrado para: '{sigla_o_nombre}' (sigla: {sigla_encontrada})", flush=True)
        return f"Último Mantenimiento para '{sigla_o_nombre}' (sigla: {sigla_encontrada}): Fecha {ultimo.get('FECHA_REPORTE')}, Técnico {ultimo.get('TECNICO')}, Ticket {ultimo.get('TICKET')}, PPM {ultimo.get('PPM_AGUA')}, Shots {ultimo.get('SHOTS')}, Estado {ultimo.get('ESTADO')}."
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_ultimo_mantenimiento: {e}", flush=True)
        return f"Error consultando el historial: {str(e)}"

def listar_alertas_activas() -> str:
    """Devuelve una lista resumen de todos los locales que actualmente tienen alertas rojas o mantenimientos pendientes."""
    print("[TOOL-CALL] listar_alertas_activas sin argumentos", flush=True)
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Alertas_Activas")
        registros = hoja.get_all_records()
        
        alertas_abiertas = [r for r in registros if str(r.get('ESTADO', '')).upper() == 'ABIERTA']
        
        if not alertas_abiertas:
            print("[TOOL-RESULT] No hay alertas abiertas", flush=True)
            return "No hay ninguna alerta activa en la Sábana en este momento. ¡Todo en orden!"
            
        resumen = "Alertas Activas:\n"
        for a in alertas_abiertas:
            resumen += f"- [{a.get('SIGLA')}] {a.get('TIPO_ALERTA')} Nivel {a.get('NIVEL')}: {a.get('MENSAJE')}\n"
        print(f"[TOOL-RESULT] Se encontraron {len(alertas_abiertas)} alertas abiertas", flush=True)
        return resumen
    except Exception as e:
        print(f"[TOOL-ERROR] Error en listar_alertas_activas: {e}", flush=True)
        return f"Error consultando las alertas: {str(e)}"

def ejecutar_consulta_db_local(query: str) -> str:
    """Ejecuta una consulta SQL SELECT en la base de datos SQLite local del supervisor para obtener registros de locales o pendientes."""
    print(f"[TOOL-CALL] ejecutar_consulta_db_local con query: '{query}'", flush=True)
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Solo se permiten consultas de tipo SELECT por seguridad."
    
    import sqlite3
    db_path = base_dir.parent / "supervisor_local.db"
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(query)
        columnas = [description[0] for description in cursor.description]
        filas = cursor.fetchall()
        conn.close()
        
        if not filas:
            return "Consulta ejecutada con éxito. No se encontraron resultados."
            
        resultados = []
        for fila in filas:
            resultados.append(dict(zip(columnas, fila)))
        return str(resultados[:100])
    except Exception as e:
        print(f"[TOOL-ERROR] Error en ejecutar_consulta_db_local: {e}", flush=True)
        return f"Error al ejecutar la consulta SQL: {str(e)}"

def leer_datos_pestana(nombre_pestana: str) -> str:
    """Devuelve el contenido completo (filas) de una pestaña específica de Google Sheets de la Sábana."""
    print(f"[TOOL-CALL] leer_datos_pestana con pestaña: '{nombre_pestana}'", flush=True)
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet(nombre_pestana)
        registros = hoja.get_all_records()
        if not registros:
            return f"La pestaña '{nombre_pestana}' está vacía."
        return str(registros[:200])
    except Exception as e:
        print(f"[TOOL-ERROR] Error en leer_datos_pestana: {e}", flush=True)
        return f"Error al leer la pestaña '{nombre_pestana}': {str(e)}"

def leer_archivo_codigo_servidor(ruta_relativa: str) -> str:
    """Lee el contenido de un archivo de código o documentación en el servidor del Supervisor (ruta relativa al directorio del proyecto)."""
    print(f"[TOOL-CALL] leer_archivo_codigo_servidor con ruta: '{ruta_relativa}'", flush=True)
    ruta_limpia = os.path.normpath(ruta_relativa).lstrip("/")
    if ruta_limpia.startswith("..") or ruta_limpia.startswith("/"):
        return "Error: Acceso no autorizado fuera de la carpeta del proyecto."
        
    ruta_completa = base_dir.parent / ruta_limpia
    if not ruta_completa.exists() or not ruta_completa.is_file():
        return f"Error: El archivo '{ruta_relativa}' no existe en el servidor."
        
    try:
        with open(ruta_completa, "r", encoding="utf-8") as f:
            contenido = f.read()
        return contenido[:8000]
    except Exception as e:
        print(f"[TOOL-ERROR] Error en leer_archivo_codigo_servidor: {e}", flush=True)
        return f"Error leyendo el archivo: {str(e)}"

def listar_archivos_servidor(directorio_relativo: str = "") -> str:
    """Lista todos los archivos y carpetas del servidor en el directorio del proyecto del Supervisor (ruta relativa)."""
    print(f"[TOOL-CALL] listar_archivos_servidor en: '{directorio_relativo}'", flush=True)
    ruta_limpia = os.path.normpath(directorio_relativo).lstrip("/")
    if ruta_limpia.startswith("..") or ruta_limpia.startswith("/"):
        return "Error: Acceso no autorizado fuera de la carpeta del proyecto."
        
    ruta_completa = base_dir.parent / (ruta_limpia if directorio_relativo else "")
    if not ruta_completa.exists() or not ruta_completa.is_dir():
        return f"Error: El directorio '{directorio_relativo}' no existe o no es una carpeta."
        
    try:
        elementos = os.listdir(ruta_completa)
        resumen = []
        for elem in elementos:
            ruta_elem = ruta_completa / elem
            tipo = "📁 Carpeta" if ruta_elem.is_dir() else "📄 Archivo"
            resumen.append(f"{tipo}: {elem}")
        return "\n".join(resumen)
    except Exception as e:
        print(f"[TOOL-ERROR] Error en listar_archivos_servidor: {e}", flush=True)
        return f"Error listando directorios: {str(e)}"

def obtener_estado_servicios(servicio: str = None) -> str:
    """Verifica el estado de los servicios systemd del usuario en la Mini PC de Ubuntu (ej: telegram-bridge, antigravity-api, cloudflared-tunnel, supervisor-userbot)."""
    print(f"[TOOL-CALL] obtener_estado_servicios para: '{servicio}'", flush=True)
    import subprocess
    servicios_validos = ["telegram-bridge.service", "antigravity-api.service", "cloudflared-tunnel.service", "supervisor-userbot.service"]
    
    if servicio:
        serv_name = servicio if servicio.endswith(".service") else f"{servicio}.service"
        if serv_name not in servicios_validos:
            return f"Error: El servicio '{servicio}' no está en la lista de monitoreo autorizada."
        cmd = ["systemctl", "--user", "status", serv_name]
    else:
        res = "Estado de los servicios de Hermes:\n"
        for s in servicios_validos:
            try:
                proc = subprocess.run(["systemctl", "--user", "is-active", s], capture_output=True, text=True)
                estado = proc.stdout.strip()
                res += f"- {s}: {estado}\n"
            except Exception as e:
                res += f"- {s}: Error al obtener estado ({str(e)})\n"
        return res

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        status_output = proc.stdout or proc.stderr
        
        log_proc = subprocess.run(["journalctl", "--user", "-u", serv_name, "-n", "15", "--no-pager"], capture_output=True, text=True, timeout=10)
        logs_output = log_proc.stdout
        
        return f"--- STATUS ---\n{status_output}\n\n--- ULTIMOS LOGS ---\n{logs_output}"
    except Exception as e:
        print(f"[TOOL-ERROR] Error en obtener_estado_servicios: {e}", flush=True)
        return f"Error consultando los servicios de Linux: {str(e)}"

def consultar_archivos_google_drive(nombre_carpeta_o_archivo: str = None) -> str:
    """Lista o busca archivos y carpetas en el Google Drive asociado al Supervisor."""
    print(f"[TOOL-CALL] consultar_archivos_google_drive con argumento: '{nombre_carpeta_o_archivo}'", flush=True)
    try:
        from googleapiclient.discovery import build
        
        ruta_credenciales = base_dir.parent / "credentials.json"
        if not ruta_credenciales.exists():
            ruta_credenciales = base_dir / "credentials.json"
        if not ruta_credenciales.exists():
            return "Error: No se encontró credentials.json para conectar con Drive."
            
        creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=['https://www.googleapis.com/auth/drive'])
        servicio = build('drive', 'v3', credentials=creds)
        
        if nombre_carpeta_o_archivo:
            query = f"name contains '{nombre_carpeta_o_archivo}' and trashed = false"
        else:
            query = "trashed = false"
            
        resultados = servicio.files().list(q=query, spaces='drive', fields='files(id, name, mimeType, parents)', pageSize=30).execute()
        archivos = resultados.get('files', [])
        
        if not archivos:
            return "No se encontraron archivos o carpetas con ese nombre en Drive."
            
        res = "Archivos encontrados en Google Drive:\n"
        for a in archivos:
            tipo = "📁 Carpeta" if a.get('mimeType') == 'application/vnd.google-apps.folder' else "📄 Archivo"
            res += f"- {tipo}: {a.get('name')} (ID: {a.get('id')})\n"
        return res
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_archivos_google_drive: {e}", flush=True)
        return f"Error consultando Google Drive: {str(e)}"

def obtener_resumen_carpetas_ingesta() -> str:
    """Devuelve un resumen con la cantidad de archivos (PDFs de reportes) en las carpetas de 'entrantes', 'procesados' y 'errores' del sistema."""
    print("[TOOL-CALL] obtener_resumen_carpetas_ingesta", flush=True)
    resumen = "Resumen de carpetas de ingesta:\n"
    for carpeta in ["entrantes", "procesados", "errores"]:
        ruta = base_dir.parent / carpeta
        if ruta.exists() and ruta.is_dir():
            try:
                archivos = [f for f in os.listdir(ruta) if (ruta / f).is_file()]
                resumen += f"- {carpeta}: {len(archivos)} archivos\n"
            except Exception as e:
                resumen += f"- {carpeta}: Error al leer ({str(e)})\n"
        else:
            resumen += f"- {carpeta}: La carpeta no existe\n"
    return resumen

def leer_ultimas_lineas_log(ruta_relativa: str, num_lineas: int = 50) -> str:
    """Lee las últimas N líneas de un archivo de log o texto en el servidor (ruta relativa al proyecto). Útil para ver logs recientes."""
    print(f"[TOOL-CALL] leer_ultimas_lineas_log con ruta: '{ruta_relativa}' y lineas: {num_lineas}", flush=True)
    ruta_limpia = os.path.normpath(ruta_relativa).lstrip("/")
    if ruta_limpia.startswith("..") or ruta_limpia.startswith("/"):
        return "Error: Acceso no autorizado fuera de la carpeta del proyecto."
        
    ruta_completa = base_dir.parent / ruta_limpia
    if not ruta_completa.exists() or not ruta_completa.is_file():
        return f"Error: El archivo '{ruta_relativa}' no existe."
        
    try:
        with open(ruta_completa, "rb") as f:
            f.seek(0, os.SEEK_END)
            tamanio = f.tell()
            bloque = 1024 * 32  # 32KB buffer to cover enough lines
            if tamanio < bloque:
                bloque = tamanio
            
            f.seek(tamanio - bloque)
            datos = f.read(bloque)
            lineas = datos.decode("utf-8", errors="ignore").splitlines()
            res = "\n".join(lineas[-num_lineas:])
            return res
    except Exception as e:
        print(f"[TOOL-ERROR] Error en leer_ultimas_lineas_log: {e}", flush=True)
        return f"Error leyendo las últimas líneas: {str(e)}"

def consultar_brain_hermes(query: str = None) -> str:
    """Busca en el cerebro (Brain) de Hermes y lee la documentación del proyecto, manuales operativos o explicaciones arquitectónicas para responder dudas conceptuales del sistema."""
    print(f"[TOOL-CALL] consultar_brain_hermes con query: '{query}'", flush=True)
    brain_dir = base_dir.parent / "brain"
    if not brain_dir.exists():
        return "El cerebro (carpeta brain/) aún no contiene documentación."
        
    try:
        files = [f for f in os.listdir(brain_dir) if f.endswith(".md")]
        if not files:
            return "No se encontraron manuales ni archivos Markdown en el cerebro."
            
        if not query:
            return f"Archivos disponibles en el cerebro:\n" + "\n".join([f"- {f}" for f in files])
            
        # Buscar coincidencias en los títulos o contenido de los archivos
        matching_docs = []
        for file in files:
            file_path = brain_dir / file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if query.lower() in file.lower() or query.lower() in content.lower():
                matching_docs.append((file, content[:3000])) # Devolver los primeros 3000 chars
                
        if not matching_docs:
            # Si no hay match específico, listar qué archivos hay para guiar al bot
            return f"No se encontró match específico para '{query}'. Manuales disponibles en el cerebro:\n" + "\n".join([f"- {f}" for f in files])
            
        res = "Documentación encontrada en el Brain:\n"
        for doc_name, doc_content in matching_docs[:3]:
            res += f"\n--- Archivo: {doc_name} ---\n{doc_content}\n"
        return res
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_brain_hermes: {e}", flush=True)
        return f"Error leyendo el cerebro de Hermes: {str(e)}"

def consultar_ficha_local(sigla: str) -> str:
    """Consulta el estado operativo consolidado en tiempo real y el historial de un local de Mostaza por su sigla (ej: FMPCH, FVDP, FBER). Lee directamente de los resúmenes locales offline de alta velocidad."""
    print(f"[TOOL-CALL] consultar_ficha_local con sigla: '{sigla}'", flush=True)
    if not sigla:
        return "Error: Debes proporcionar la sigla del local."
        
    sigla_limpia = sigla.upper().strip()
    ruta_ficha = base_dir.parent / "brain" / "locales" / f"{sigla_limpia}.md"
    
    if not ruta_ficha.exists():
        # Intentar buscar si la sigla ingresada es en realidad una sigla de ticket
        try:
            import csv
            ruta_csv = base_dir.parent / "locales.csv"
            if ruta_csv.exists():
                with open(ruta_csv, mode="r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader)
                    for row in reader:
                        if len(row) > 1:
                            sigla_sis = row[0].strip().upper()
                            sigla_tic = row[1].strip().upper()
                            if sigla_tic == sigla_limpia and sigla_sis and sigla_sis != "-":
                                ruta_ficha = base_dir.parent / "brain" / "locales" / f"{sigla_sis}.md"
                                sigla_limpia = sigla_sis
                                break
        except Exception as e:
            print(f"[WARN] Error buscando sigla en CSV: {e}")
            
    if not ruta_ficha.exists():
        # Listar las fichas disponibles
        dir_locales = base_dir.parent / "brain" / "locales"
        disponibles = []
        if dir_locales.exists():
            disponibles = [f.stem for f in dir_locales.glob("*.md")]
        
        msg = f"No se encontró un resumen local para la sigla '{sigla}'."
        if disponibles:
            msg += f" Siglas disponibles localmente: {', '.join(disponibles)}."
        else:
            msg += " No hay resúmenes locales generados todavía en brain/locales/."
        return msg
        
    try:
        with open(ruta_ficha, "r", encoding="utf-8") as f:
            contenido = f.read()
        return contenido
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_ficha_local: {e}", flush=True)
        return f"Error leyendo el resumen del local '{sigla}': {str(e)}"

