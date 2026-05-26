import os
import uvicorn
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import base64
from typing import List, Optional, Union, Dict, Any
from dotenv import load_dotenv

# Cargar variables de entorno del directorio padre (.env principal)
from pathlib import Path
base_dir = Path(__file__).parent
parent_env = base_dir.parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env)
else:
    load_dotenv()

# Configurar API de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "ACA_VA_TU_CLAVE":
    print("⚠️ ADVERTENCIA: GEMINI_API_KEY no configurada correctamente en .env")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Importar las herramientas para Function Calling
from herramientas_hermes import consultar_datos_maestros_local, consultar_ultimo_mantenimiento, listar_alertas_activas
herramientas = [
    consultar_datos_maestros_local,
    consultar_ultimo_mantenimiento,
    listar_alertas_activas
]

app = FastAPI(title="Antigravity Supervisor API")

# Modelos Pydantic para validar el formato compatible con OpenAI
class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    user: Optional[str] = None

def get_supervisor_prompt(chat_id: str = None):
    """Contexto maestro: Identidad Dual basada en el usuario"""
    
    # Identidad 1: Asistente / Ingeniero (Para Cristian)
    if chat_id == "215173956":
        return (
            "Eres Antigravity, un Ingeniero de Software Senior y Asistente de IA personal de Cristian. "
            "Tu objetivo es ayudarlo a administrar, desarrollar y optimizar el sistema 'Supervisor' y toda la "
            "infraestructura relacionada. Tienes un profundo conocimiento técnico. Responde de forma analítica, "
            "extensa, y asume el rol de un colega experto. Usa Markdown para estructurar tus respuestas."
        )
    
    # Identidad 2: Supervisor de Mantenimiento (Para los Técnicos)
    return (
        "Eres el Agente Supervisor, una IA diseñada para asistir a técnicos de mantenimiento "
        "en campo de cafeteras comerciales e infraestructura. Responde de manera profesional, concisa "
        "y resolutiva. NO digas que eres un bot genérico. Usa Markdown para estructurar tus respuestas (negritas, viñetas)."
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ACA_VA_TU_CLAVE":
        raise HTTPException(status_code=500, detail="Gemini API Key no configurada en el servidor.")
        
    try:
        # Extraer el mensaje del usuario
        mensaje_usuario = ""
        for msg in reversed(req.messages):
            if msg.role == "user":
                if isinstance(msg.content, str):
                    mensaje_usuario = msg.content
                else:
                    parts = []
                    for part in msg.content:
                        if part.get("type") == "text":
                            parts.append(part.get("text"))
                        elif part.get("type") == "input_audio":
                            audio_b64 = part["input_audio"]["data"]
                            audio_format = part["input_audio"].get("format", "ogg")
                            audio_bytes = base64.b64decode(audio_b64)
                            parts.append({
                                "mime_type": f"audio/{audio_format}",
                                "data": audio_bytes
                            })
                    mensaje_usuario = parts
                break
                
        if not mensaje_usuario:
            raise HTTPException(status_code=400, detail="No se encontró mensaje del usuario.")

        print(f"📩 Consulta entrante (ID: {req.user})")

        # --- ARQUITECTURA FUTURA: ENRUTADOR (ROUTER) ---
        # Aquí determinaremos qué modelo usar. 
        # Ejemplo futuro: if req.model == "groq" or (es_solo_texto and quiere_velocidad):
        #   return enviar_a_groq(...)
        # -----------------------------------------------

        # Generar respuesta con reintentos y fallback a gemini-1.5-flash para alta disponibilidad
        texto_respuesta = ""
        model_used = 'gemini-2.0-flash'
        try:
            model = genai.GenerativeModel(
                model_name=model_used, 
                system_instruction=get_supervisor_prompt(req.user),
                tools=herramientas
            )
            chat = model.start_chat(enable_automatic_function_calling=True)
            response = chat.send_message(mensaje_usuario)
            texto_respuesta = response.text
        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ Error con gemini-2.0-flash: {err_msg}")
            
            # Si es un error de cuota (429) o de red, esperamos un momento y reintentamos o hacemos fallback
            if "429" in err_msg or "quota" in err_msg.lower():
                import time
                print("⏳ Límite de cuota detectado. Esperando 3 segundos para reintentar con gemini-2.5-flash...")
                time.sleep(3)
            
            # Fallback a gemini-2.5-flash
            try:
                model_used = 'gemini-2.5-flash'
                print(f"🔄 Intentando fallback con {model_used}...")
                model = genai.GenerativeModel(
                    model_name=model_used, 
                    system_instruction=get_supervisor_prompt(req.user),
                    tools=herramientas
                )
                chat = model.start_chat(enable_automatic_function_calling=True)
                response = chat.send_message(mensaje_usuario)
                texto_respuesta = response.text
            except Exception as e_fallback:
                print(f"❌ Error también en fallback {model_used}: {str(e_fallback)}")
                raise HTTPException(status_code=500, detail=f"Error en Gemini principal y fallback: {str(e_fallback)}")
        
        print(f"🤖 Respuesta generada ({model_used}): {texto_respuesta[:100]}...")
        
        # Formatear la salida imitando la API de OpenAI
        return {
            "id": "chatcmpl-antigravity",
            "object": "chat.completion",
            "created": 1234567890,
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": texto_respuesta,
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
    except Exception as e:
        print(f"❌ Error en Gemini: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Levantando Antigravity Supervisor API en el puerto 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
