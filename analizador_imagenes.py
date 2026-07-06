import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
# También cargar el del supervisor para contingencias de ruta
load_dotenv("/home/cristian/Documentos/Supervisor/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analizar_foto(ruta_imagen, texto_mensaje="", locales_db=[], contexto_cronograma=""):
    import llm_fallback
    import json
    import re
    
    try:
        locales_str = ", ".join(locales_db)
        prompt = (
            "Eres un supervisor experto en mantenimiento de locales gastronómicos.\n"
            "Analiza detalladamente esta imagen (que puede ser una foto de campo o una captura de pantalla) enviada por el supervisor o por un técnico.\n\n"
            f"Mensaje de texto adjunto: '{texto_mensaje}'\n"
            f"Cronograma del técnico para hoy: '{contexto_cronograma}'\n"
            f"Locales oficiales disponibles (siglas y nombres): {locales_str}\n\n"
            "Debes clasificar la imagen en uno de los siguientes tipos ('tipo_imagen'):\n"
            "1. 'EVIDENCIA_TECNICA': Fotografía de una máquina, reparación, repuestos, tablero de control, pantalla con error o tareas de mantenimiento.\n"
            "2. 'PLANIFICACION': Captura de pantalla, planilla, tabla o listado del cronograma semanal de ruteo/servicios de los técnicos (indica qué técnico va a qué local cada día de la semana).\n"
            "3. 'MANUAL_TECNICO': Un diagrama, despiece, guía de troubleshooting, plano eléctrico o página de manual de servicio.\n"
            "4. 'OTRO': Fotos casuales, comprobantes de pago de peajes/comida, capturas de pantalla que no son cronogramas, selfies, etc.\n\n"
            "Responde estrictamente en formato JSON con la siguiente estructura:\n"
            "{\n"
            '  "tipo_imagen": "EVIDENCIA_TECNICA" | "PLANIFICACION" | "MANUAL_TECNICO" | "OTRO",\n'
            '  "local_detectado": "SIGLA" (solo aplicable para EVIDENCIA_TECNICA; debe ser la sigla exacta en mayúsculas que precede a los dos puntos en la lista, ej: "FMMVP", "FLIN", o null si no se puede determinar),\n'
            '  "descripcion_tecnica": "descripción sintética y técnica de lo que muestra la imagen",\n'
            '  "cronograma_datos": { ... } (solo aplicable para PLANIFICACION. Extrae el cronograma completo de la imagen. Claves: Nombre del Técnico (ej: "Fernando Soria", "Tomas Vera", "Anabella Guerrero", "Francisco Rametta"). Valores: un diccionario con los días de la semana en español en minúscula (lunes, martes, miercoles, jueves, viernes, sabado, domingo) y una lista de los nombres/siglas de locales que tiene asignados ese día, o ["OFF"] si tiene franco. Si la imagen no contiene la planificación de algún técnico mencionado en las claves, inicialízalo con listas vacías en todos sus días)\n'
            "}\n"
        )
        
        response_text = llm_fallback.analizar_imagen(ruta_imagen, prompt)
        
        # Limpieza por si retorna markdown json blocks
        if "```" in response_text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                response_text = match.group(1)
                
        resultado = json.loads(response_text.strip())
        return resultado
    except Exception as e:
        return {
            "tipo_imagen": "OTRO",
            "local_detectado": None,
            "descripcion_tecnica": f"Error analizando imagen: {e}",
            "cronograma_datos": None
        }
