import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analizar_foto(ruta_imagen, texto_mensaje="", locales_db=[], contexto_cronograma=""):
    if not GEMINI_API_KEY:
        return {
            "es_evidencia_tecnica": False,
            "local_detectado": None,
            "descripcion_tecnica": "No hay API KEY de Gemini para analizar la imagen."
        }
    
    try:
        import PIL.Image
        import json
        img = PIL.Image.open(ruta_imagen)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        locales_str = ", ".join(locales_db)
        prompt = (
            "Eres un supervisor experto en mantenimiento de locales gastronómicos.\n"
            "Analiza detalladamente esta fotografía enviada por un técnico junto con el mensaje de texto adjunto.\n\n"
            f"Mensaje del técnico: '{texto_mensaje}'\n"
            f"Cronograma del técnico para hoy: '{contexto_cronograma}'\n"
            f"Locales oficiales disponibles (siglas y nombres): {locales_str}\n\n"
            "Debes responder estrictamente en formato JSON con la siguiente estructura:\n"
            "{\n"
            '  "es_evidencia_tecnica": true/false,\n'
            '  "local_detectado": "SIGLA" (debe ser la sigla exacta en mayúsculas que precede a los dos puntos en la lista, ej: "FMMVP", "FLIN", o null si no se puede determinar con certeza absoluta),\n'
            '  "descripcion_tecnica": "descripción sintética y técnica de lo que muestra la imagen"\n'
            "}\n\n"
            "Reglas de negocio:\n"
            "1. 'es_evidencia_tecnica' debe ser true SOLAMENTE si la imagen muestra una máquina, herramientas, repuestos, "
            "un tablero de control, pantallas de error, reparaciones en proceso, o tareas de mantenimiento. "
            "Debe ser false para fotos informales, selfies, remitos de entrega de mercadería, comprobantes de pago de materiales, "
            "o fotos casuales del chat.\n"
            "2. 'local_detectado' debe ser la sigla exacta (ej: FMMVP) asociada al local del cual se habla en el mensaje o se muestra en la foto. "
            "Determínalo inteligentemente analizando el texto del mensaje, el ticket o el contexto visual de la foto. "
            "Ignora diferencias de acentuación, abreviaturas informales o mayúsculas/minúsculas. "
            "Si no estás seguro o no hay información del local, pon null."
        )
        
        response = model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        
        resultado = json.loads(response.text.strip())
        return resultado
    except Exception as e:
        return {
            "es_evidencia_tecnica": False,
            "local_detectado": None,
            "descripcion_tecnica": f"Error analizando imagen: {e}"
        }

