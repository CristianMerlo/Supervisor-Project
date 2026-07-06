import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
sys.path.append("/home/cristian/PROYECTOS/Supervisor-Project")

import google.generativeai as genai
from agentic_loop import consultar_agentic_loop

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("Falta GEMINI_API_KEY en .env")
    exit(1)
genai.configure(api_key=GEMINI_KEY)

TEST_CASES = [
    {
        "query": "Cómo limpio el espumador de leche de la cafetera Melitta CT8?",
        "expected_criteria": "Debe indicar el uso del limpiador Melitta Milk Test, realizar enjuagues del sistema de leche y limpiar piezas desmontables."
    },
    {
        "query": "Cuál es el contacto del local Liniers (FLIN)?",
        "expected_criteria": "Debe consultar la información del local FLIN (Liniers) y proveer datos como teléfono o encargado."
    },
    {
        "query": "Qué hago si el broiler Nieco JF94 no enciende?",
        "expected_criteria": "Debe mencionar revisar válvulas de gas, verificar energía/fusibles, chispa de encendido y referenciar el manual de Nieco."
    }
]

def evaluar():
    model_judge = genai.GenerativeModel("gemini-2.5-flash")
    resultados = []
    print("Iniciando evaluación de Hermes (LLM-as-a-Judge)...")
    
    for idx, case in enumerate(TEST_CASES, 1):
        query = case["query"]
        criteria = case["expected_criteria"]
        
        print(f"Evaluando Caso {idx}: '{query}'...")
        
        try:
            # Mandamos un historial vacío para testear respuesta directa
            response = consultar_agentic_loop(query, historial=[], system_prompt="Eres Hermes, asistente experto de mantenimiento.")
        except Exception as e:
            response = f"ERROR: {e}"
            
        prompt_juez = (
            "Eres un Ingeniero de QA y Juez de Inteligencia Artificial para el sistema de mantenimiento gastronómico de Mostaza.\n"
            "Tu tarea es evaluar la respuesta dada por el bot (Hermes) a la consulta de un técnico, basándote en un criterio de éxito.\n\n"
            f"Consulta del Técnico: \"{query}\"\n"
            f"Criterio de Éxito Requerido: \"{criteria}\"\n"
            f"Respuesta generada por Hermes: \"{response}\"\n\n"
            "Por favor, responde estructurado en JSON con los siguientes campos:\n"
            "- puntaje: entero del 1 al 10 (donde 10 es excelente y cubre todo el criterio, y 1 es totalmente erróneo)\n"
            "- veredicto: breve explicación del puntaje otorgado y qué faltó o se destacó\n"
            "- aprobado: booleano (True si el puntaje es mayor o igual a 7, False si es menor)"
        )
        
        try:
            judge_res = model_judge.generate_content(prompt_juez, generation_config={"response_mime_type": "application/json"})
            eval_data = json.loads(judge_res.text)
        except Exception as e_judge:
            eval_data = {
                "puntaje": 0,
                "veredicto": f"Fallo al evaluar por el juez: {e_judge}",
                "aprobado": False
            }
            
        resultados.append({
            "caso": idx,
            "pregunta": query,
            "respuesta_bot": response,
            "criterio": criteria,
            "evaluacion": eval_data
        })
        
    report_path = "/home/cristian/PROYECTOS/Supervisor-Project/brain/reporte_evaluacion_supervisor.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Reporte de Evaluación de Hermes (LLM-as-a-Judge)\n\n")
        f.write(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("==================================================\n\n")
        
        aprobados = sum(1 for r in resultados if r["evaluacion"]["aprobado"])
        total = len(resultados)
        f.write(f"### Estatus General: {'🟢 APROBADO' if aprobados == total else '⚠️ REQUIERE REVISIÓN'} ({aprobados}/{total} aprobados)\n\n")
        
        for r in resultados:
            f.write(f"## Caso {r['caso']}: {r['pregunta']}\n")
            f.write(f"- **Criterio de Éxito:** {r['criterio']}\n")
            f.write(f"- **Respuesta del Bot:**\n```\n{r['respuesta_bot']}\n```\n")
            f.write(f"- **Puntaje del Juez:** `{r['evaluacion']['puntaje']}/10`\n")
            f.write(f"- **Aprobado:** {'✅ SÍ' if r['evaluacion']['aprobado'] else '❌ NO'}\n")
            f.write(f"- **Comentarios del Juez:** {r['evaluacion']['veredicto']}\n\n")
            f.write("---\n\n")
            
    print(f"Evaluación completada. Reporte guardado en {report_path}")

if __name__ == "__main__":
    evaluar()
