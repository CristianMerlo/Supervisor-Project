import os
import subprocess
import datetime
from duckduckgo_search import DDGS
import google.generativeai as genai
from dotenv import load_dotenv
import notificador_telegram

PROJECT_DIR = "/home/cristian/PROYECTOS/Supervisor-Project"
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

def run_vulture():
    """Ejecuta vulture para encontrar código muerto."""
    import sys
    try:
        result = subprocess.run([sys.executable, "-m", "vulture", PROJECT_DIR], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error ejecutando vulture: {e}"

def run_pylint():
    """Ejecuta pylint sobre los archivos principales para encontrar problemas estructurales."""
    import sys
    try:
        # Analizamos solo los principales para no saturar
        archivos = ["agentic_loop.py", "userbot_supervisor.py", "notificador_telegram.py", "motor_tickets_mostaza.py"]
        rutas = [os.path.join(PROJECT_DIR, f) for f in archivos if os.path.exists(os.path.join(PROJECT_DIR, f))]
        result = subprocess.run([sys.executable, "-m", "pylint", "--disable=all", "--enable=E,F,W0611", "-rn"] + rutas, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error ejecutando pylint: {e}"

def realizar_investigacion_web():
    """Usa DuckDuckGo para buscar novedades tecnológicas aplicables al proyecto."""
    try:
        query = "nuevas herramientas de inteligencia artificial para agentes y bots telegram python 2026"
        resultados = DDGS().text(query, max_results=3)
        if not resultados:
            return "No se encontraron resultados relevantes."
        
        texto = ""
        for res in resultados:
            texto += f"- {res['title']}: {res['body']} ({res['href']})\n"
        return texto
    except Exception as e:
        return f"Error en búsqueda web: {e}"

def generar_reporte(vulture_out, pylint_out, web_out):
    """Llama a Gemini 2.5 Flash para estructurar el reporte de auditoría."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: No hay GEMINI_API_KEY configurada."
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""Eres el Analista de Arquitectura (Auditor) del sistema Supervisor-Project.
Se te han proporcionado los siguientes datos crudos extraídos hoy:

1. REPORTE DE VULTURE (Código Muerto/No Usado):
{vulture_out[:2000]}

2. REPORTE DE PYLINT (Errores o Imports sin usar):
{pylint_out[:2000]}

3. NOVEDADES TECNOLÓGICAS (Búsqueda Web):
{web_out}

Tu tarea es redactar un "Reporte de Auditoría Semanal" en formato Markdown.
Debe incluir:
- **Resumen Ejecutivo**: Estado de salud general del proyecto.
- **Código Muerto u Obsoleto**: Análisis de lo encontrado por Vulture y recomendaciones de limpieza.
- **Problemas Estructurales**: Análisis de Pylint.
- **Oportunidades de Mejora y Nuevas Skills**: Basado en las novedades web y tu conocimiento.
- **Plan de Acción**: 3 pasos recomendados para el administrador (Cristian).

Sé directo, profesional y claro. Usa formato Markdown. No envuelvas todo en un bloque de código, escribe el markdown directamente.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error contactando a Gemini: {e}"

def ejecutar_auditoria():
    print("Iniciando auditoría...")
    vulture_out = run_vulture()
    pylint_out = run_pylint()
    web_out = realizar_investigacion_web()
    
    reporte_md = generar_reporte(vulture_out, pylint_out, web_out)
    
    fecha = datetime.datetime.now().strftime("%Y%m%d")
    nombre_archivo = f"Auditoria_Semanal_{fecha}.md"
    ruta_archivo = os.path.join(PROJECT_DIR, nombre_archivo)
    
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write(reporte_md)
        
    print(f"Reporte guardado en {ruta_archivo}")
    
    # Enviar alerta y luego enviar el archivo por Telegram
    resumen = "✨ [Analista de Arquitectura] La auditoría semanal ha finalizado. Adjunto el reporte con sugerencias de optimización, limpieza de código muerto y nuevas tendencias."
    notificador_telegram.enviar_alerta(resumen, agente="Sistema")
    notificador_telegram.enviar_archivo(ruta_archivo)

if __name__ == "__main__":
    ejecutar_auditoria()
