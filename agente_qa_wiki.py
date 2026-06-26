import os
import json
import random
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import notificador_telegram

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")

# Configuración de Gemini
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    notificador_telegram.enviar_alerta("❌ [QA ERROR] Falta GEMINI_API_KEY en .env", agente="QA_Agent")
    exit(1)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

BASE_JSON_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/brain/base_errores.json"
REPORTE_PATH = f"/home/cristian/Documentos/Supervisor/Reporte_QA_{datetime.now().strftime('%Y%m%d')}.md"

def realizar_qa():
    if not os.path.exists(BASE_JSON_PATH):
        notificador_telegram.enviar_alerta("❌ [QA ERROR] No se encontró base_errores.json.", agente="QA_Agent")
        return

    with open(BASE_JSON_PATH, "r", encoding="utf-8") as f:
        try:
            base_errores = json.load(f)
        except Exception as e:
            notificador_telegram.enviar_alerta(f"❌ [QA ERROR] JSON Corrupto: {e}", agente="QA_Agent")
            return

    # Extraer una muestra para analizar (max 20 fallas aleatorias)
    muestra = []
    for maquina, fallas in base_errores.items():
        if isinstance(fallas, list) and len(fallas) > 0:
            # Tomar hasta 2 errores al azar por máquina
            seleccionados = random.sample(fallas, min(len(fallas), 2))
            for falla in seleccionados:
                muestra.append({"maquina": maquina, "datos": falla})
    
    if len(muestra) > 20:
        muestra = random.sample(muestra, 20)

    if not muestra:
        notificador_telegram.enviar_alerta("⚠️ [QA] La base de errores está vacía, no hay nada que evaluar.", agente="QA_Agent")
        return

    prompt = f"""
Eres un Agente de Quality Assurance (QA) auditando una base de datos de soluciones técnicas para equipos gastronómicos (cafeteras, freidoras, broilers).
A continuación te presento una muestra aleatoria de códigos de error, fallas y soluciones extraídas automáticamente de los manuales.

MUESTRA A EVALUAR:
{json.dumps(muestra, indent=2, ensure_ascii=False)}

TUS TAREAS:
1. Evalúa si la información tiene sentido lógico y técnico.
2. Identifica si el bot extractor "alucinó" o guardó texto basura en lugar de una solución real.
3. Redacta un reporte en Markdown estructurado detallando la calidad general, errores encontrados y sugerencias.
4. Genera al final una frase resumen ("VEREDICTO:") indicando si la base está SANA o si requiere limpieza humana.
"""

    try:
        response = model.generate_content(prompt)
        reporte = response.text
        
        # Guardar archivo Markdown
        with open(REPORTE_PATH, "w", encoding="utf-8") as f:
            f.write(reporte)
        
        # Extraer el veredicto para enviarlo por Telegram
        veredicto = "No se encontró un veredicto claro."
        for linea in reporte.split('\n'):
            if "VEREDICTO:" in linea.upper():
                veredicto = linea.strip()
                break
                
        mensaje_tg = f"📊 *Reporte Semanal de Calidad (QA)*\n\nHe finalizado la revisión de la Base de Errores Extraída.\n\n*Conclusión:* {veredicto}\n\n📁 El reporte detallado se guardó en: `Documentos/Supervisor/Reporte_QA_{datetime.now().strftime('%Y%m%d')}.md`"
        notificador_telegram.enviar_alerta(mensaje_tg, agente="QA_Agent")
        
    except Exception as e:
        notificador_telegram.enviar_alerta(f"❌ [QA ERROR] Falló la evaluación con Gemini: {e}", agente="QA_Agent")

if __name__ == "__main__":
    realizar_qa()
