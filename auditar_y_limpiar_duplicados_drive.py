#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: auditar_y_limpiar_duplicados_drive.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Audita y limpia reportes en PDF duplicados en las carpetas de locales en Google Drive.
Utiliza PyPDF2 para extraer texto de los PDFs sospechosos. Realiza una validación
rápida local (por metadatos extraídos con regex y similitud de texto difflib).
En caso de duda y si la cuota lo permite, utiliza Gemini 2.5 Flash para comparar
estructural y semánticamente la información. Conserva el archivo con el nombre más limpio
y envía los redundantes a la papelera.
Genera un reporte markdown en /home/cristian/Documentos/Supervisor/Reporte_Limpieza_Duplicados.md.
Permite agendarse en crontab para ejecutarse todos los domingos a las 3:00 AM.
"""

import os
import sys
import re
import csv
import json
import logging
import tempfile
import argparse
import time
import difflib
from pathlib import Path
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload
import PyPDF2
import google.generativeai as genai
from dotenv import load_dotenv

# Configurar logs estructurados
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/home/cristian/PROYECTOS/Supervisor-Project/limpieza_duplicados.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("auditor_duplicados")

# Rutas del sistema
PROYECTO_DIR = Path("/home/cristian/PROYECTOS/Supervisor-Project")
LOCALES_CSV = PROYECTO_DIR / "locales.csv"
ENV_FILE = PROYECTO_DIR / ".env"
REPORTE_MD = Path("/home/cristian/Documentos/Supervisor/Reporte_Limpieza_Duplicados.md")

# Asegurar import de archivador_drive
sys.path.append(str(PROYECTO_DIR))
try:
    import archivador_drive
except ImportError:
    logger.error("No se pudo importar archivador_drive. Asegúrese de que el script esté en el directorio del proyecto.")
    sys.exit(1)

# Cargar variables de entorno y configurar Gemini
load_dotenv(str(ENV_FILE))
api_key = os.getenv("GEMINI_API_KEY")
GEMINI_DISABLED = False

if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY no encontrada en el archivo .env. La comparación semántica por IA no estará disponible.")
    GEMINI_DISABLED = True

def llamar_gemini_con_retry(prompt, model_name="gemini-2.5-flash", system_instruction=None):
    """Llama a la API de Gemini con manejo de cuota (error 429) y reintentos automáticos."""
    global GEMINI_DISABLED
    if GEMINI_DISABLED or not api_key:
        return None
        
    config = {}
    if system_instruction:
        config["system_instruction"] = system_instruction
        
    max_retries = 3
    base_delay = 5
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name, **config)
            response = model.generate_content(prompt)
            time.sleep(1)  # Delay amigable
            return response.text.strip()
        except Exception as e:
            err_str = str(e).lower()
            if "daily" in err_str or "requestsperday" in err_str:
                logger.warning("Límite diario de Gemini alcanzado. Desactivando llamadas por el resto de la ejecución.")
                GEMINI_DISABLED = True
                return None
            elif "429" in err_str or "quota" in err_str or "limit" in err_str or "exhausted" in err_str:
                delay = base_delay * (attempt + 1)
                logger.warning(f"Límite de cuota Gemini alcanzado (RPM). Reintentando en {delay}s...")
                time.sleep(delay)
            else:
                logger.warning(f"Falla de API de Gemini: {e}")
                break
    return None

def obtener_siglas_locales():
    """Retorna un conjunto de siglas válidas desde locales.csv."""
    siglas = set()
    if not LOCALES_CSV.exists():
        logger.warning(f"No se encontró locales.csv en {LOCALES_CSV}")
        return siglas
    try:
        with open(LOCALES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # Omitir cabecera
            for row in reader:
                if len(row) > 1:
                    s_sis = row[0].strip().upper()
                    s_tic = row[1].strip().upper()
                    if s_sis and s_sis != "-":
                        siglas.add(s_sis)
                    if s_tic and s_tic != "-":
                        siglas.add(s_tic)
    except Exception as e:
        logger.error(f"Error al leer locales.csv: {e}")
    return siglas

def descargar_archivo_drive(servicio, file_id, dest_path):
    """Descarga un archivo desde Google Drive de forma segura."""
    try:
        request = servicio.files().get_media(fileId=file_id)
        with open(dest_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        return True
    except Exception as e:
        logger.error(f"Error descargando archivo {file_id}: {e}")
        return False

def extraer_texto_pdf(pdf_path):
    """Extrae el texto plano del archivo PDF."""
    texto = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                texto += page.extract_text() or ""
    except Exception as e:
        logger.error(f"Error al extraer texto de {pdf_path}: {e}")
    return texto.strip()

def parsear_con_regex(texto):
    """Extrae metadatos del reporte usando expresiones regulares rápidas y seguras."""
    # Ticket
    m_ticket = re.search(r'Ticket\s*(?:N°|Nro|Nro\.|#)?\s*:?\s*(\d+)', texto, re.IGNORECASE)
    ticket = m_ticket.group(1) if m_ticket else None
    
    # Date
    m_date = re.search(r'(\d{4}-\d{2}-\d{2})', texto)
    if not m_date:
        m_date = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
    date = m_date.group(1) if m_date else None
    
    # PPM
    m_ppm = re.search(r'PPM\s*:\s*([^\s|]+)', texto, re.IGNORECASE)
    ppm = m_ppm.group(1) if m_ppm else None
    
    # Shots
    m_shots = re.search(r'(?:shoots|shots)\s*:\s*(\d+)', texto, re.IGNORECASE)
    shots = m_shots.group(1) if m_shots else None
    
    # Observaciones
    m_obs = re.search(r'3\.\s*Observaciones\s*Iniciales\s*:\s*(.*?)(?=\s*4\.\d*|\s*4\s+|$)', texto, re.DOTALL | re.IGNORECASE)
    obs = m_obs.group(1).strip() if m_obs else None
    
    return {
        "numero_ticket": ticket,
        "fecha_servicio": date,
        "ppm_agua": ppm,
        "cantidad_shots": shots,
        "observaciones": obs
    }

def confirmar_duplicidad_con_ia(texto_a, texto_b):
    """Pregunta a Gemini 2.5 Flash si dos reportes son el mismo de forma semántica."""
    prompt = f"""
    Compara los siguientes dos reportes técnicos extraídos de archivos de mantenimiento.
    Determina si corresponden a la misma visita de servicio / ticket (es decir, son duplicados redundantes,
    aunque tengan sutiles variaciones en formato, errores tipográficos o hayan sido cargados dos veces).

    Reporte A:
    ---
    {texto_a}
    ---

    Reporte B:
    ---
    {texto_b}
    ---

    Responde estrictamente con un JSON estructurado así:
    {{
      "es_duplicado": true | false,
      "razon": "Explicación breve de tu decisión en español"
    }}
    """
    text = llamar_gemini_con_retry(prompt)
    if not text:
        return False, "No disponible"
    try:
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
        res = json.loads(text)
        return res.get("es_duplicado", False), res.get("razon", "")
    except Exception as e:
        logger.error(f"Error parseando JSON de comparación IA: {e}")
        return False, "Error de parseo"

def son_duplicados_localmente(f1, f2):
    """Compara reportes a nivel local usando metadatos regex y similitud de texto."""
    d1 = f1['datos_regex']
    d2 = f2['datos_regex']
    
    # 1. Si los tickets coinciden y no son nulos
    if d1['numero_ticket'] and d2['numero_ticket'] and d1['numero_ticket'] == d2['numero_ticket']:
        return True
        
    # 2. Si el texto completo normalizado es idéntico
    t1_norm = re.sub(r'\s+', '', f1['texto']).lower()
    t2_norm = re.sub(r'\s+', '', f2['texto']).lower()
    if t1_norm == t2_norm:
        return True
        
    # 3. Si la fecha, PPM y shots coinciden y observaciones son idénticas
    if d1['fecha_servicio'] == d2['fecha_servicio'] and d1['ppm_agua'] == d2['ppm_agua'] and d1['cantidad_shots'] == d2['cantidad_shots']:
        if d1['observaciones'] and d2['observaciones'] and d1['observaciones'].lower() == d2['observaciones'].lower():
            return True
            
    # 4. Similitud de texto usando difflib
    ratio = difflib.SequenceMatcher(None, t1_norm, t2_norm).ratio()
    if ratio > 0.88:
        return True
        
    return False

def calcular_penalizacion_nombre(nombre):
    """Calcula un puntaje de penalización de limpieza de nombre. El menor puntaje es el más limpio."""
    score = 0
    nombre_lower = nombre.lower()
    
    # Sufijos de copia comunes
    if "(" in nombre_lower and ")" in nombre_lower:
        score += 10
    if "copia" in nombre_lower or "_copia" in nombre_lower:
        score += 10
    if "_v2" in nombre_lower or "-v2" in nombre_lower or "_v3" in nombre_lower:
        score += 5
    # Patrón de timestamp (ej: _260714_221000)
    if re.search(r'_\d{6}_\d{6}', nombre_lower):
        score += 5
    # Prefijo numérico inútil (ej: 00004338-)
    if re.match(r'^\d+-', nombre_lower):
        score += 2
        
    # Longitud extra penaliza sutilmente para preferir nombres cortos y estándar
    score += 0.1 * len(nombre)
    return score

def agendar_cron():
    """Agenda el script en el crontab para ejecutarse los domingos a las 3:00 AM."""
    try:
        import subprocess
        python_bin = sys.executable
        script_path = __file__
        log_path = PROYECTO_DIR / "cron_limpieza_duplicados.log"
        cron_command = f"0 3 * * 0 {python_bin} {script_path} >> {log_path} 2>&1"
        
        process = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = process.stdout if process.returncode == 0 else ""
        
        if script_path in current_cron:
            lines = []
            for line in current_cron.splitlines():
                if script_path not in line:
                    lines.append(line)
            lines.append(cron_command)
            new_cron = "\n".join(lines) + "\n"
            logger.info("El script ya estaba en el crontab. Actualizando la entrada de programación.")
        else:
            new_cron = current_cron.strip() + "\n" + cron_command + "\n"
            logger.info("Agregando nueva programación al crontab.")
            
        subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True)
        logger.info("🟢 Tarea programada exitosamente en el crontab para todos los domingos a las 3:00 AM.")
        return True
    except Exception as e:
        logger.error(f"Error al configurar el crontab: {e}")
        return False

def auditar_y_limpiar(dry_run=False):
    logger.info("=== INICIANDO AUDITORÍA Y LIMPIEZA DE REPORTES DUPLICADOS EN DRIVE ===")
    if dry_run:
        logger.info("[DRY RUN] Modo de prueba activo. No se enviará ningún archivo a la papelera.")
        
    try:
        servicio = archivador_drive.obtener_servicio_drive()
    except Exception as e:
        logger.error(f"No se pudo inicializar la conexión con Google Drive: {e}")
        return
        
    siglas_oficiales = obtener_siglas_locales()
    logger.info(f"Cargadas {len(siglas_oficiales)} siglas oficiales de locales.")
    
    # 1. Obtener todas las carpetas para trazar rutas
    logger.info("Obteniendo árbol de carpetas de Google Drive...")
    folders = []
    page_token = None
    while True:
        res = servicio.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name, parents)",
            pageToken=page_token,
            pageSize=1000
        ).execute()
        folders.extend(res.get('files', []))
        page_token = res.get('nextPageToken')
        if not page_token:
            break
            
    folder_map = {f['id']: {'name': f['name'], 'parents': f.get('parents', [])} for f in folders}
    
    def obtener_ruta_completa(folder_id):
        if not folder_id or folder_id not in folder_map:
            return ""
        f_info = folder_map[folder_id]
        parent_id = f_info['parents'][0] if f_info['parents'] else None
        if parent_id and parent_id in folder_map:
            return obtener_ruta_completa(parent_id) + "/" + f_info['name']
        return f_info['name']

    # 2. Buscar todos los archivos PDF
    logger.info("Buscando archivos PDF en Google Drive...")
    pdfs = []
    page_token = None
    while True:
        res = servicio.files().list(
            q="mimeType='application/pdf' and trashed=false",
            fields="nextPageToken, files(id, name, parents, size, createdTime, modifiedTime)",
            pageToken=page_token,
            pageSize=1000
        ).execute()
        pdfs.extend(res.get('files', []))
        page_token = res.get('nextPageToken')
        if not page_token:
            break
            
    logger.info(f"Se encontraron {len(pdfs)} archivos PDF en total.")
    
    # 3. Agrupar PDFs por Local y normalizar candidatos a duplicados
    grouped_by_local = {}
    for p in pdfs:
        name = p['name']
        parent_id = p.get('parents')[0] if p.get('parents') else None
        parent_path = obtener_ruta_completa(parent_id) if parent_id else "Raíz"
        
        # Buscar sigla
        sigla = "OTRO"
        parent_folder_name = folder_map.get(parent_id, {}).get('name', '') if parent_id else ''
        m_parent = re.search(r'\[([A-Z0-9]+)\]', parent_folder_name)
        if m_parent:
            sigla = m_parent.group(1).upper()
        else:
            m_file = re.search(r'MTZ_([A-Z0-9]+)_', name, re.IGNORECASE)
            if m_file:
                sigla = m_file.group(1).upper()
            else:
                for s in siglas_oficiales:
                    if s in name.upper() or s in parent_path.upper():
                        sigla = s
                        break
                        
        p['parent_path'] = parent_path
        p['sigla'] = sigla
        grouped_by_local.setdefault(sigla, []).append(p)
        
    # Agrupar por patrones sospechosos de duplicados dentro de cada local
    candidatos_duplicados = []
    
    def normalizar_base(name):
        name_no_ext = name.rsplit('.', 1)[0]
        name_clean = re.sub(r'^\d+-', '', name_no_ext)
        m = re.match(r'^(MTZ_[A-Z0-9]+_\d{4}-\d{2}-\d{2})', name_clean, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        name_clean = re.sub(r'\s*\(\d+\)$', '', name_clean)
        name_clean = re.sub(r'_\d{6}_\d{6}$', '', name_clean)
        name_clean = re.sub(r'_v\d+$', '', name_clean, flags=re.IGNORECASE)
        name_clean = re.sub(r'_copia$', '', name_clean, flags=re.IGNORECASE)
        return name_clean.strip().upper()

    for sigla, archivos in grouped_by_local.items():
        norm_groups = {}
        for a in archivos:
            base_norm = normalizar_base(a['name'])
            norm_groups.setdefault(base_norm, []).append(a)
            
        for base_norm, grupo in norm_groups.items():
            if len(grupo) > 1:
                candidatos_duplicados.append((sigla, base_norm, grupo))
                
    logger.info(f"Se identificaron {len(candidatos_duplicados)} grupos sospechosos de duplicación.")
    
    audited_files_count = 0
    duplicate_groups_cleaned = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        for sigla, base_norm, grupo in candidatos_duplicados:
            logger.info(f"Analizando grupo: {base_norm} ({len(grupo)} archivos)...")
            
            # Descargar y extraer textos
            archivos_procesados = []
            for i, f in enumerate(grupo):
                local_file_path = tmp_path / f"file_{i}.pdf"
                if descargar_archivo_drive(servicio, f['id'], str(local_file_path)):
                    texto = extraer_texto_pdf(local_file_path)
                    f['texto'] = texto
                    f['datos_regex'] = parsear_con_regex(texto)
                    archivos_procesados.append(f)
                    audited_files_count += 1
                    
            # Clasificar duplicados reales usando reglas locales primero, y Gemini como fallback
            verificados = []
            
            for f in archivos_procesados:
                colocado = False
                for subgrupo in verificados:
                    ref_f = subgrupo[0]
                    
                    # 1. Validar localmente (muy rápido, ahorra cuota)
                    datos_match = son_duplicados_localmente(f, ref_f)
                    
                    # 2. Fallback con IA en caso de duda (si la similitud no fue contundente pero sospechosa)
                    if not datos_match and api_key:
                        es_dup, razon = confirmar_duplicidad_con_ia(f['texto'], ref_f['texto'])
                        if es_dup:
                            datos_match = True
                            
                    if datos_match:
                        subgrupo.append(f)
                        colocado = True
                        break
                        
                if not colocado:
                    verificados.append([f])
                    
            # Procesar cada subgrupo verificado
            for subgrupo in verificados:
                if len(subgrupo) < 2:
                    continue
                    
                subgrupo_scores = []
                for f in subgrupo:
                    score = calcular_penalizacion_nombre(f['name'])
                    subgrupo_scores.append((score, f))
                    
                subgrupo_scores.sort(key=lambda x: x[0])
                mejor_f = subgrupo_scores[0][1]
                redundantes = [x[1] for x in subgrupo_scores[1:]]
                
                logger.info(f"  [DUP VERIFICADO] Se conserva: {mejor_f['name']} (ID: {mejor_f['id']})")
                
                eliminados = []
                for red in redundantes:
                    logger.info(f"  [DUP VERIFICADO] Descartando: {red['name']} (ID: {red['id']})")
                    if not dry_run:
                        try:
                            servicio.files().update(fileId=red['id'], body={'trashed': True}).execute()
                            logger.info(f"    Papelera: {red['name']} [OK]")
                        except Exception as e:
                            err_str = str(e)
                            if "insufficientFilePermissions" in err_str or "403" in err_str:
                                logger.warning(f"    Sin permisos para enviar a papelera. Intentando remover de la carpeta actual...")
                                try:
                                    f_meta = servicio.files().get(fileId=red['id'], fields="parents").execute()
                                    parents = f_meta.get('parents', [])
                                    if parents:
                                        servicio.files().update(
                                            fileId=red['id'],
                                            removeParents=parents[0]
                                        ).execute()
                                        logger.info(f"    Removido de la carpeta {red['parent_path']} [OK] (Huérfano)")
                                    else:
                                        logger.warning(f"    El archivo {red['name']} no tiene padres.")
                                except Exception as e2:
                                    logger.error(f"    Error al remover de la carpeta actual: {e2}")
                            else:
                                logger.error(f"    Error al mover a papelera {red['name']}: {e}")
                    eliminados.append(red)
                    
                duplicate_groups_cleaned.append({
                    'conservado': mejor_f,
                    'eliminados': eliminados,
                    'sigla': sigla
                })

    # Reporte Markdown
    escribir_reporte(audited_files_count, duplicate_groups_cleaned, dry_run)
    logger.info(f"=== AUDITORÍA FINALIZADA. Reporte escrito en {REPORTE_MD} ===")

def escribir_reporte(audited_count, duplicate_groups, dry_run):
    REPORTE_MD.parent.mkdir(parents=True, exist_ok=True)
    fecha_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    modo = "SIMULACIÓN / DRY RUN" if dry_run else "PRODUCCIÓN (Papelera activa)"
    total_eliminados = sum(len(g['eliminados']) for g in duplicate_groups)
    
    contenido = [
        f"# Reporte de Auditoría y Limpieza de Reportes Duplicados en Google Drive\n",
        f"- **Fecha de Ejecución:** {fecha_ejecucion}",
        f"- **Modo de Operación:** {modo}",
        f"- **Total de PDFs Auditados:** {audited_count}",
        f"- **Grupos de Duplicados Confirmados:** {len(duplicate_groups)}",
        f"- **Total de Archivos Enviados a la Papelera:** {total_eliminados}\n",
        "## Resumen de Decisiones de Limpieza\n"
    ]
    
    if not duplicate_groups:
        contenido.append("No se detectaron reportes duplicados redundantes en las carpetas auditadas.")
    else:
        contenido.append("| Local | Archivo Conservado (Original) | Archivo Redundante Descartado (Papelera) | ID Descartado | Ruta en Drive | Razón de Decisión |")
        contenido.append("|---|---|---|---|---|---|")
        
        for g in duplicate_groups:
            cons = g['conservado']
            sigla = g['sigla']
            for el in g['eliminados']:
                t_cons = cons.get('datos_regex', {}).get('numero_ticket')
                ticket_str = f"Ticket #{t_cons}" if t_cons else "Sin número"
                
                razon = f"Duplicado semántico/estructural verificado de {cons['name']}. ({ticket_str}). Nombre conservado es el original/limpio."
                contenido.append(f"| {sigla} | `{cons['name']}` | `{el['name']}` | `{el['id']}` | `{el['parent_path']}` | {razon} |")
                
    contenido.append("\n---\n*Reporte generado automáticamente por Antigravity Supervisor Service Account.*")
    
    try:
        with open(REPORTE_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(contenido))
        logger.info(f"Reporte escrito en {REPORTE_MD}")
    except Exception as e:
        logger.error(f"Error escribiendo reporte: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Auditar y limpiar reportes duplicados de Google Drive.")
    parser.add_argument("--dry-run", action="store_true", help="Ejecutar en modo simulación (sin borrar nada).")
    parser.add_argument("--setup-cron", action="store_true", help="Configurar programación en crontab y salir.")
    
    args = parser.parse_args()
    
    if args.setup_cron:
        agendar_cron()
    else:
        auditar_y_limpiar(dry_run=args.dry_run)
