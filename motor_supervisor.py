import os
import json
import re
import PyPDF2
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Configuración
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and genai:
    genai.configure(api_key=GEMINI_API_KEY)

try:
    if genai:
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        model = None
except Exception:
    model = None

# --- CONSTANTES DE NEGOCIO (Umbrales del sistema) ---
UMBRAL_PPM_CRITICO = 200
UMBRAL_SHOTS_PREVENTIVO = 150000

def extraer_texto_pdf(pdf_path):
    texto_completo = ""
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        for page in reader.pages:
            texto_completo += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error leyendo PDF: {e}")
    return texto_completo

def parser_hibrido(pdf_path):
    """Fase 1: Extrae los datos del PDF usando Expresiones Regulares ultrarrápidas."""
    texto = extraer_texto_pdf(pdf_path)
    
    datos = {
        "fecha": "",
        "local": "",
        "sigla": "",
        "tecnico": "",
        "ticket": "",
        "viatico": 0.0,
        "ppm": 0,
        "maquina": "",
        "shots": 0,
        "repuestos": ""
    }
    
    m_local = re.search(r"Local:\s*(.+?)\s*\((.*?)\)", texto)
    if m_local:
        datos["local"] = m_local.group(1).strip()
        datos["sigla"] = m_local.group(2).strip()
        
    # Fallback lookup in local SQLite database if sigla is missing
    if not datos["sigla"] and datos["local"]:
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supervisor_local.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                local_name_clean = datos["local"].lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").strip()
                cursor.execute("SELECT sigla, nombre FROM locales")
                for db_sigla, db_nombre in cursor.fetchall():
                    db_nombre_clean = db_nombre.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").strip()
                    if local_name_clean == db_nombre_clean or local_name_clean in db_nombre_clean or db_nombre_clean in local_name_clean:
                        datos["sigla"] = db_sigla
                        datos["local"] = db_nombre
                        print(f"   [Fallback DB] Resolved sigla '{db_sigla}' for local name '{datos['local']}'")
                        break
                conn.close()
        except Exception as e_db:
            print(f"   [!] Error performing fallback DB lookup: {e_db}")
        
    m_tecnico = re.search(r"Técnico:\s*(.+?)Ticket", texto)
    if m_tecnico:
        datos["tecnico"] = m_tecnico.group(1).strip()
        
    m_ticket = re.search(r"Ticket N°:\s*(\d+)", texto)
    if m_ticket:
        datos["ticket"] = m_ticket.group(1).strip()
        
    m_ppm = re.search(r"PPM:\s*(\d+)", texto)
    if m_ppm:
        datos["ppm"] = int(m_ppm.group(1))
        
    m_viatico = re.search(r"VIÁTICO:\s*\$(\d+\.?\d*)", texto)
    if m_viatico:
        datos["viatico"] = float(m_viatico.group(1))

    m_shots = re.search(r"SHOOTS:\s*(\d+)", texto)
    if m_shots:
        datos["shots"] = int(m_shots.group(1))
    
    return datos

def evaluar_reglas_negocio(datos):
    """
    Fase 2: Motor de Reglas.
    Aplica la Jerarquía Hídrica y de Mantenimiento Predictivo.
    """
    alertas = []
    estado_general = "VERDE_NORMAL"
    
    # 1. Regla Suprema: Jerarquía Hídrica
    ppm = datos.get("ppm", 0)
    if ppm > UMBRAL_PPM_CRITICO:
        estado_general = "ROJO_CRITICO"
        alertas.append({
            "tipo": "JERARQUIA_HIDRICA",
            "nivel": "CRITICO",
            "mensaje": f"Peligro: Agua Dura detectada ({ppm} PPM). Supera el límite de {UMBRAL_PPM_CRITICO} PPM. Riesgo inminente de calcificación en caldera de {datos.get('local')}."
        })
    elif ppm >= 150: 
        if estado_general == "VERDE_NORMAL":
            estado_general = "AMARILLO_ADVERTENCIA"
        alertas.append({
            "tipo": "JERARQUIA_HIDRICA",
            "nivel": "ADVERTENCIA",
            "mensaje": f"Precaución: PPM elevado ({ppm}). Agendar posible cambio de resina."
        })

    # 2. Mantenimiento Predictivo: Shots de la Cafetera
    shots = datos.get("shots", 0)
    if shots > UMBRAL_SHOTS_PREVENTIVO:
        if estado_general == "VERDE_NORMAL":
            estado_general = "AMARILLO_ADVERTENCIA"
        alertas.append({
            "tipo": "MANTENIMIENTO_PREDICTIVO",
            "nivel": "ADVERTENCIA",
            "mensaje": f"Preventivo requerido. La máquina alcanzó los {shots} ciclos (Umbral: {UMBRAL_SHOTS_PREVENTIVO})."
        })
        
    return {
        "estado_general": estado_general,
        "alertas_activas": alertas
    }

def procesar_reporte(pdf_path):
    print(f"--- PROCESANDO: {Path(pdf_path).name} ---")
    
    datos_extraidos = parser_hibrido(pdf_path)
    resultado_auditoria = evaluar_reglas_negocio(datos_extraidos)
    
    return datos_extraidos, resultado_auditoria
