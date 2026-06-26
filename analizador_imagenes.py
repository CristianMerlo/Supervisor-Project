import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analizar_foto(ruta_imagen):
    if not GEMINI_API_KEY:
        return "No hay API KEY de Gemini para analizar la imagen."
    
    try:
        # Importante: para enviar la imagen, necesitamos subirla con la API o pasarla directa.
        import PIL.Image
        img = PIL.Image.open(ruta_imagen)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = (
            "Eres un experto en mantenimiento de maquinaria gastronómica. "
            "Analiza detalladamente esta fotografía enviada por un técnico desde el local. "
            "Describe de forma muy sintética y técnica lo que ves. "
            "Si ves una pantalla con un código de error, indícalo expresamente. "
            "Si ves un tablero o repuesto dañado, descríbelo."
        )
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception as e:
        return f"Error analizando imagen: {e}"
