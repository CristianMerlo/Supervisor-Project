# Paquete de Despliegue: Fase 1 y Fase 2 (Supervisor Antigravity)

**Instrucciones para el Antigravity de la máquina destino:**
Hola Antigravity. Este archivo contiene el código de producción de las **Fase 1 (Ingesta y Parser de PDF)** y **Fase 2 (Motor de Reglas de Negocio)**. 
Por favor, lee el código a continuación, guárdalo en tu entorno local como `motor_supervisor.py` y asegúrate de tener instalada la dependencia `PyPDF2`.

---

## Código Fuente (`motor_supervisor.py`)

```python
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
```
