import os
import json
import re
import PyPDF2
import sqlite3
import logging
from pathlib import Path
import hermes_obsidian_client

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE IA (GEMINI) ---
try:
    import google.generativeai as genai
except ImportError:
    genai = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model = None
if GEMINI_API_KEY and genai:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("Modelo Gemini 2.5 Flash inicializado correctamente.")
    except Exception as e:
        logger.error(f"Error inicializando Gemini: {e}")

# --- CONSTANTES DE NEGOCIO (Umbrales del sistema) ---
UMBRAL_PPM_BLANDO = 50
UMBRAL_PPM_ADVERTENCIA = 120
UMBRAL_PPM_CRITICO = 300
UMBRAL_SHOTS_PREVENTIVO = 150000

# --- PRE-COMPILACIÓN DE EXPRESIONES REGULARES ---
REGEX_LOCAL = re.compile(r"Local:\s*(.+?)\s*\((.*?)\)")
REGEX_TECNICO = re.compile(r"Técnico:\s*(.+?)Ticket")
REGEX_TICKET = re.compile(r"Ticket N°:\s*(\d+)")
REGEX_PPM = re.compile(r"PPM:\s*(\d+)")
REGEX_VIATICO = re.compile(r"VIÁTICO:\s*\$(\d+\.?\d*)")
REGEX_SHOTS = re.compile(r"SHOOTS:\s*(\d+)")

# Tabla de traducción para limpieza rápida
ACCENT_MAPPING = str.maketrans('áéíóúÁÉÍÓÚ', 'aeiouAEIOU')

def clean_string(text: str) -> str:
    """Remueve tildes y pasa a minúsculas de forma eficiente."""
    return text.translate(ACCENT_MAPPING).lower().strip()

def extraer_texto_pdf(pdf_path):
    texto_completo = ""
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        for page in reader.pages:
            texto_completo += page.extract_text() + "\n"
    except Exception as e:
        logger.error(f"Error leyendo PDF {pdf_path}: {e}")
    return texto_completo

def fallback_ia_gemini(texto: str, datos_parciales: dict) -> dict:
    """Utiliza Gemini (u otro LLM de resguardo) para completar datos que las Regex no pudieron encontrar."""
    import llm_fallback
    
    prompt = f"""
Extrae los siguientes datos de mantenimiento a partir del texto del PDF.
Responde ÚNICAMENTE con un JSON válido con estas claves exactas:
"local" (string), "sigla" (string), "tecnico" (string), "ticket" (string), "viatico" (float), "ppm" (int), "shots" (int),
"filtro_presente" (bool), "ablandador_presente" (bool), "osmosis_presente" (bool), "observaciones_hidricas" (string).
Para los booleanos, pon true si el texto menciona que ese elemento está instalado o presente en el local.
En "observaciones_hidricas" pon un breve resumen del estado del sistema de agua (ej: "Se cambió cartucho", "Resina saturada").
Si un dato no existe, pon 0 para números, false para booleanos, o "" para strings.

Texto del reporte:
{texto}
"""
    try:
        response_text = llm_fallback.generar_texto(prompt)
        
        # Limpieza por si retorna markdown json blocks
        if "```" in response_text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                response_text = match.group(1)
                
        nuevos_datos = json.loads(response_text)
        
        # Mergeando datos: dar prioridad a lo encontrado por IA si estaba vacío en regex
        for k, v in nuevos_datos.items():
            if k in datos_parciales:
                if not datos_parciales[k] and v:
                    datos_parciales[k] = v
                    logger.info(f"   [IA Fallback] Rescatado dato faltante '{k}': {v}")
                    
    except Exception as e:
        logger.error(f"[!] Error durante el fallback de IA: {e}")
        
    return datos_parciales

def resolver_sigla_desde_db(datos):
    db_path = "/home/cristian/Documentos/Supervisor/supervisor_local.db"
    if not os.path.exists(db_path):
        return datos
        
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sigla, nombre FROM locales")
            locales_db = cursor.fetchall()
            valid_siglas = {r[0] for r in locales_db}
            
            # Si no hay sigla o la sigla no es válida en la BD
            if not datos.get("sigla") or datos.get("sigla") not in valid_siglas:
                if datos.get("local"):
                    local_name_clean = clean_string(datos["local"])
                    for db_sigla, db_nombre in locales_db:
                        db_nombre_clean = clean_string(db_nombre)
                        if local_name_clean in db_nombre_clean or db_nombre_clean in local_name_clean:
                            datos["sigla"] = db_sigla
                            datos["local"] = db_nombre
                            logger.info(f"   [Fallback DB] Resuelta sigla '{db_sigla}' para '{datos['local']}'")
                            break
    except Exception as e_db:
        logger.error(f"   [!] Error DB lookup: {e_db}")
    return datos

def parser_hibrido(pdf_path):
    """Fase 1: Extrae los datos usando Regex. Fase 1B: Fallback IA si faltan datos críticos."""
    texto = extraer_texto_pdf(pdf_path)
    
    datos = {
        "fecha": "", "local": "", "sigla": "", "tecnico": "", "ticket": "",
        "viatico": 0.0, "ppm": 0, "maquina": "", "shots": 0, "repuestos": "",
        "filtro_presente": False, "ablandador_presente": False, "osmosis_presente": False,
        "observaciones_hidricas": ""
    }
    
    m_local = REGEX_LOCAL.search(texto)
    if m_local:
        datos["local"] = m_local.group(1).strip()
        datos["sigla"] = m_local.group(2).strip()
        
    # Fallback DB para la sigla si falta
    datos = resolver_sigla_desde_db(datos)
        
    m_tecnico = REGEX_TECNICO.search(texto)
    if m_tecnico: datos["tecnico"] = m_tecnico.group(1).strip()
        
    m_ticket = REGEX_TICKET.search(texto)
    if m_ticket: datos["ticket"] = m_ticket.group(1).strip()
        
    m_ppm = REGEX_PPM.search(texto)
    if m_ppm: datos["ppm"] = int(m_ppm.group(1))
        
    m_viatico = REGEX_VIATICO.search(texto)
    if m_viatico: datos["viatico"] = float(m_viatico.group(1))

    m_shots = REGEX_SHOTS.search(texto)
    if m_shots: datos["shots"] = int(m_shots.group(1))
    
    # ---------------------------------------------------------
    # FALLBACK IA: Si faltan datos críticos, consultar a Gemini
    # ---------------------------------------------------------
    # EXTRACCIÓN IA: Extraer campos booleanos hídricos y fallback
    # ---------------------------------------------------------
    if texto.strip():
        logger.info("   [IA] Activando Parser IA Gemini para datos hídricos...")
        datos = fallback_ia_gemini(texto, datos)
        # Re-intentar lookup de DB si la IA rescató el nombre del local pero no la sigla
        datos = resolver_sigla_desde_db(datos)
    return datos, texto

def evaluar_reglas_negocio(datos):
    """Fase 2: Motor de Reglas. Aplica la Jerarquía Hídrica y de Mantenimiento Predictivo."""
    alertas = []
    estado_general = "VERDE_NORMAL"
    
    ppm = datos.get("ppm", 0)
    if ppm > 0:
        if ppm < UMBRAL_PPM_BLANDO:
            estado_general = "ROJO_BLANDO"
            alertas.append({
                "tipo": "JERARQUIA_HIDRICA", "nivel": "CRITICO",
                "mensaje": f"Peligro: Agua Demasiado Blanda ({ppm} PPM). Riesgo Corrosivo. Requiere Filtro Remineralizador."
            })
        elif ppm > UMBRAL_PPM_CRITICO:
            estado_general = "ROJO_CRITICO"
            mensaje = f"Peligro: Agua Extremadamente Dura ({ppm} PPM). Supera {UMBRAL_PPM_CRITICO} PPM. Requiere Filtro Zen y Ablandador."
            
            # Enriquecimiento MCP (Obsidian)
            resultados = hermes_obsidian_client.buscar_notas("calcificación caldera")
            if resultados and "matches" in resultados and len(resultados["matches"]) > 0:
                mensaje += f"\n📚 Info en Obsidian: Se encontraron {len(resultados['matches'])} antecedentes/manuales sobre esto."
                
            alertas.append({
                "tipo": "JERARQUIA_HIDRICA", "nivel": "CRITICO",
                "mensaje": mensaje
            })
        elif ppm >= UMBRAL_PPM_ADVERTENCIA: 
            if estado_general == "VERDE_NORMAL": estado_general = "AMARILLO_ADVERTENCIA"
            alertas.append({
                "tipo": "JERARQUIA_HIDRICA", "nivel": "ADVERTENCIA",
                "mensaje": f"Precaución: Riesgo de Sarro ({ppm} PPM). Requiere Ablandador operativo."
            })
        else:
            # Entre 50 y 120
            pass # VERDE_NORMAL

    shots = datos.get("shots", 0)
    if shots > UMBRAL_SHOTS_PREVENTIVO:
        if estado_general == "VERDE_NORMAL": estado_general = "AMARILLO_ADVERTENCIA"
        
        # Enriquecimiento MCP (Obsidian)
        resultados_shots = hermes_obsidian_client.buscar_notas("mantenimiento preventivo maquina")
        mensaje_preventivo = f"Preventivo requerido. La máquina alcanzó {shots} ciclos (Umbral: {UMBRAL_SHOTS_PREVENTIVO})."
        if resultados_shots and "matches" in resultados_shots and len(resultados_shots["matches"]) > 0:
            mensaje_preventivo += "\n📚 Info en Obsidian: Hay manuales disponibles para este mantenimiento."
            
        alertas.append({
            "tipo": "MANTENIMIENTO_PREDICTIVO", "nivel": "ADVERTENCIA",
            "mensaje": mensaje_preventivo
        })
        
    return {"estado_general": estado_general, "alertas_activas": alertas}

def procesar_reporte(pdf_path):
    logger.info(f"--- PROCESANDO: {Path(pdf_path).name} ---")
    datos_extraidos, texto_pdf = parser_hibrido(pdf_path)
    resultado_auditoria = evaluar_reglas_negocio(datos_extraidos)
    return datos_extraidos, resultado_auditoria, texto_pdf
