import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Asegurar import de config_manager
sys.path.append(str(Path(__file__).parent))
import config_manager

# Cargar variables de entorno
load_dotenv("/home/cristian/Documentos/Supervisor/.env")

logger = logging.getLogger("llm_fallback")
logging.basicConfig(level=logging.INFO)

def notificar_error_modelo(provider, model_name, error_msg):
    """
    Registra de forma silenciosa las fallas de modelo en un archivo de log local,
    evitando molestar a Cristian por Telegram con mensajes de depuración técnica.
    """
    log_path = "/home/cristian/Documentos/Supervisor/fallas_modelos.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now().isoformat()}] [{provider.upper()}] Modelo: {model_name} | Error: {error_msg}\n")
        logger.error(f"[LOGGED] Falló modelo {model_name} ({provider}). Registrado en fallas_modelos.log")
    except Exception as e_log:
        logger.error(f"No se pudo escribir en log de fallas de modelos: {e_log}")

def obtener_modelos_disponibles_groq():
    """Consulta la API de Groq para obtener el listado de todos los modelos activos."""
    try:
        import requests
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return []
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            return [m["id"] for m in data.get("data", []) if m.get("active", True)]
    except Exception as e:
        logger.error(f"Error listando modelos de Groq: {e}")
    return []

def generar_texto(prompt, system_instruction=None):
    """
    Genera texto a partir de un prompt con fallback automático.
    Prioridad: 1. Gemini (Directo) | 2. Groq (Llama-3)
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    model_gemini = config_manager.get_env_var("MODEL_GEMINI_TEXT", "gemini-2.5-flash")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction
            model = genai.GenerativeModel(model_gemini, **config)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e_gemini:
            logger.warning(f"   [!] Gemini falló ({model_gemini}): {e_gemini}. Activando fallback a Groq...")
            if "not found" in str(e_gemini).lower() or "deprecated" in str(e_gemini).lower() or "invalid" in str(e_gemini).lower():
                notificar_error_modelo("gemini", model_gemini, str(e_gemini))
            
    groq_key = os.getenv("GROQ_API_KEY")
    model_groq = config_manager.get_env_var("MODEL_GROQ_TEXT", "llama-3.3-70b-versatile")
    if groq_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model_groq
            )
            res = chat_completion.choices[0].message.content
            if res:
                logger.info(f"   [Fallback] Completada solicitud de texto con éxito usando Groq ({model_groq}).")
                return res.strip()
        except Exception as e_groq:
            logger.error(f"   [!] Fallback a Groq falló ({model_groq}): {e_groq}")
            if "model" in str(e_groq).lower() or "decommissioned" in str(e_groq).lower() or "400" in str(e_groq).lower():
                notificar_error_modelo("groq", model_groq, str(e_groq))
            
    raise RuntimeError("Todos los proveedores de LLM fallaron o no están configurados.")

def analizar_imagen(image_path, prompt):
    """
    Analiza una imagen a partir de un path y prompt con fallback automático.
    Prioridad: 1. Gemini (Directo) | 2. Groq Vision
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    model_gemini = config_manager.get_env_var("MODEL_GEMINI_TEXT", "gemini-2.5-flash")
    if gemini_key:
        try:
            import google.generativeai as genai
            from PIL import Image
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(model_gemini)
            img = Image.open(image_path)
            response = model.generate_content([prompt, img])
            if response and response.text:
                return response.text.strip()
        except Exception as e_gemini:
            logger.warning(f"   [!] Gemini Vision falló ({model_gemini}): {e_gemini}. Activando fallback a Groq Vision...")
            if "not found" in str(e_gemini).lower() or "deprecated" in str(e_gemini).lower() or "invalid" in str(e_gemini).lower():
                notificar_error_modelo("gemini", model_gemini, str(e_gemini))
            
    groq_key = os.getenv("GROQ_API_KEY")
    model_groq_vision = config_manager.get_env_var("MODEL_GROQ_VISION", "meta-llama/llama-4-scout-17b-16e-instruct")
    if groq_key:
        try:
            from openai import OpenAI
            import base64
            
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )
            
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                             },
                        ],
                    }
                ],
                model=model_groq_vision,
            )
            res = chat_completion.choices[0].message.content
            if res:
                logger.info(f"   [Fallback] Analizada imagen con éxito usando Groq Vision ({model_groq_vision}).")
                return res.strip()
        except Exception as e_groq:
            logger.error(f"   [!] Fallback a Groq Vision falló ({model_groq_vision}): {e_groq}")
            if "model" in str(e_groq).lower() or "decommissioned" in str(e_groq).lower() or "400" in str(e_groq).lower():
                notificar_error_modelo("groq", model_groq_vision, str(e_groq))
            
    raise RuntimeError("Todos los proveedores de LLM de Visión fallaron o no están configurados.")
