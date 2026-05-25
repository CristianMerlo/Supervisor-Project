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

# --- CONSTANTES DE NEGOCIO (Idealmente vendrían de Google Sheets) ---
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
    """Fase 1: Extrae los datos del PDF."""
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
    
    m_local = re.search(r"Local:\s*(.+?)\s*\((\w+)\)", texto)
    if m_local:
        datos["local"] = m_local.group(1).strip()
        datos["sigla"] = m_local.group(2).strip()
        
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
    
    # Aquí iría el bloque de Gemini para Diagnóstico y Repuestos si hay Token disponible.
    return datos

def evaluar_reglas_negocio(datos):
    """
    Fase 2: Motor de Reglas.
    Evalúa los datos parseados y aplica la Jerarquía Hídrica y de Predictibilidad.
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
    
    # Fase 1: Parseo
    datos_extraidos = parser_hibrido(pdf_path)
    print("\n[✓] FASE 1: Datos Extraídos:")
    print(json.dumps(datos_extraidos, indent=4, ensure_ascii=False))
    
    # Fase 2: Auditoría y Reglas
    resultado_auditoria = evaluar_reglas_negocio(datos_extraidos)
    print(f"\n[✓] FASE 2: Auditoría Completada -> ESTADO: {resultado_auditoria['estado_general']}")
    for alerta in resultado_auditoria['alertas_activas']:
        print(f"  🚨 [{alerta['nivel']}] {alerta['mensaje']}")

if __name__ == "__main__":
    pdf_prueba = "/Users/CR1S714N/Downloads/Informes Tecnicos/MTZ_F3DF_2026-05-16.pdf"
    if os.path.exists(pdf_prueba):
        procesar_reporte(pdf_prueba)
    else:
        print("Archivo de prueba no encontrado.")
