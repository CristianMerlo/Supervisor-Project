import os
import uvicorn
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
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

# Estado global para fallback de clave de API (conmutación temporal por 10 minutos)
use_backup_until = 0.0


# Importar las herramientas para Function Calling
from herramientas_hermes import (
    consultar_datos_maestros_local,
    consultar_ultimo_mantenimiento,
    listar_alertas_activas,
    ejecutar_consulta_db_local,
    leer_datos_pestana,
    leer_archivo_codigo_servidor,
    listar_archivos_servidor,
    obtener_estado_servicios,
    consultar_archivos_google_drive,
    obtener_resumen_carpetas_ingesta,
    leer_ultimas_lineas_log,
    consultar_brain_hermes,
    consultar_ficha_local
)

# Herramientas de consulta básicas para técnicos (seguro)
herramientas_tecnico = [
    consultar_datos_maestros_local,
    consultar_ultimo_mantenimiento,
    listar_alertas_activas,
    consultar_ficha_local
]

# Herramientas de acceso completo al sistema para el desarrollador (Cristian)
herramientas_desarrollador = [
    consultar_datos_maestros_local,
    consultar_ultimo_mantenimiento,
    listar_alertas_activas,
    ejecutar_consulta_db_local,
    leer_datos_pestana,
    leer_archivo_codigo_servidor,
    listar_archivos_servidor,
    obtener_estado_servicios,
    consultar_archivos_google_drive,
    obtener_resumen_carpetas_ingesta,
    leer_ultimas_lineas_log,
    consultar_brain_hermes,
    consultar_ficha_local
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
    
    # Identidad 1: Enrutamiento Dinámico de Agentes (Para Cristian)
    if str(chat_id) == "215173956":
        return (
            "Eres un sistema multiagente que asiste a Cristian en la supervisión de locales y mantenimiento. "
            "Debes analizar la consulta de Cristian y adoptar OBLIGATORIAMENTE uno de los siguientes roles, "
            "comenzando tu respuesta siempre con su prefijo y emoji correspondiente en la primera línea:\n\n"
            "1. 🛠️ [Antigravity] (Desarrollo / DevOps / Infraestructura):\n"
            "   - Cuándo adoptar: Si Cristian pregunta sobre el código de los scripts, logs recientes, estado del hardware (RAM, disco, CPU), "
            "estado de los servicios de systemd o túneles de Porta/Cloudflare.\n"
            "   - Firma en la primera línea: 🛠️ [Antigravity]\n\n"
            "2. 🧠 [Hermes] (Operativo / Reportes / Sucursales):\n"
            "   - Cuándo adoptar: Si Cristian pregunta sobre locales (ej. PPM de agua de una sucursal, datos maestros), actividad de técnicos "
            "(check-ins, check-outs), reportes de mantenimiento guardados, viáticos o métricas de las sucursales.\n"
            "   - Firma en la primera línea: 🧠 [Hermes]\n\n"
            "3. 🪿 [Goose] (Mantenimiento de archivos / Limpieza):\n"
            "   - Cuándo adoptar: Si Cristian pregunta sobre limpieza del disco, papelera del sistema, clasificar la bandeja de entrada o "
            "el estado de las carpetas de ingesta (entrantes, procesados, errores).\n"
            "   - Firma en la primera línea: 🪿 [Goose]\n\n"
            "REGLAS DE TRANSPARENCIA:\n"
            "- Debes firmar siempre con la identidad correcta en la primera línea (ej. '🧠 [Hermes]' o '🛠️ [Antigravity]' o '🪿 [Goose]'). No uses otra.\n"
            "- Habla en primera persona como el agente seleccionado (ej: 'Como Hermes, he verificado que...' o 'Como Antigravity, el servidor...').\n"
            "- Tienes acceso a herramientas avanzadas para consultar datos. Úsalas según corresponda y responde con precisión en Markdown.\n"
            "- Eres un modelo multimodal y puedes entender notas de voz (archivos de audio). Si Cristian te habla por audio, clasifica su consulta igualmente y responde bajo el rol adecuado."
        )
    
    # Identidad 2: Supervisor de Mantenimiento (Para los Técnicos)
    return (
        "Eres el Agente Supervisor (con la identidad de 🧠 [Hermes]), una IA diseñada para asistir a técnicos de mantenimiento "
        "en campo de cafeteras comerciales e infraestructura. Responde de manera profesional, concisa y resolutiva.\n"
        "Comienza tu respuesta siempre con el prefijo: 🧠 [Hermes]\n\n"
        "IMPORTANTE: Eres un modelo multimodal y puedes recibir y entender notas de voz (archivos de audio). "
        "Responde de forma clara y directa en Markdown (negritas, viñetas)."
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    global use_backup_until
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ACA_VA_TU_CLAVE":
        raise HTTPException(status_code=500, detail="Gemini API Key no configurada en el servidor.")
        
    # Extraer la clave nativa (si la hay) de la cabecera Authorization
    native_key = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        parts = auth_header.split(" ")
        if len(parts) > 1:
            native_key = parts[1].strip()
            
    # La clave principal será la nativa (si viene en el header) o la de respaldo (si no hay nativa)
    primary_key = native_key if native_key else GEMINI_API_KEY
    
    import time
    current_time = time.time()
    is_fallback_active = current_time < use_backup_until
    
    # Determinar qué clave usar de entrada
    if is_fallback_active:
        print("🔄 [FALLBACK] Modo de conmutación temporal activo. Usando clave de respaldo de Google AI Studio (backup).")
        active_key = GEMINI_API_KEY
    else:
        active_key = primary_key
        
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
 
        # Determinar las herramientas permitidas según el usuario
        chat_id_str = str(req.user) if req.user else ""
        if chat_id_str == "215173956":
            herramientas_usuario = herramientas_desarrollador
            print("👨‍💻 Modo desarrollador habilitado para Cristian.")
        else:
            herramientas_usuario = herramientas_tecnico
            print("🛠️ Modo consulta estándar habilitado para técnico.")
 
        # Generar respuesta con reintentos y fallback
        texto_respuesta = ""
        model_used = 'gemini-2.0-flash'
        
        def run_generation(model_name, api_key_to_use):
            genai.configure(api_key=api_key_to_use)
            model = genai.GenerativeModel(
                model_name=model_name, 
                system_instruction=get_supervisor_prompt(req.user),
                tools=herramientas_usuario
            )
            chat = model.start_chat(enable_automatic_function_calling=True)
            response = chat.send_message(mensaje_usuario)
            return response.text

        try:
            texto_respuesta = run_generation(model_used, active_key)
        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ Error con {model_used} usando clave activa: {err_msg}")
            
            # Si el error es de cuota agotada en la clave primaria (nativa)
            # y NO estábamos usando ya la de respaldo:
            if not is_fallback_active and active_key == native_key and ("429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower()):
                use_backup_until = time.time() + 600  # 10 minutos
                print(f"⚠️ [FALLBACK] Límite de cuota detectado en clave nativa. Conmutando a clave de respaldo de Google AI Studio por 10 minutos.")
                # Reintentamos con la clave de respaldo
                try:
                    texto_respuesta = run_generation(model_used, GEMINI_API_KEY)
                except Exception as e_backup:
                    print(f"❌ Error también con clave de respaldo en {model_used}: {e_backup}")
                    # Si falla la de respaldo con gemini-2.0, intentamos con gemini-2.5-flash
                    try:
                        model_used = 'gemini-2.5-flash'
                        print(f"🔄 Intentando con clave de respaldo y modelo {model_used}...")
                        texto_respuesta = run_generation(model_used, GEMINI_API_KEY)
                    except Exception as e_fallback_all:
                        print(f"❌ Fallo absoluto en clave nativa, respaldo y modelos: {e_fallback_all}")
                        raise HTTPException(status_code=500, detail=f"Fallo absoluto en clave nativa y de respaldo: {str(e_fallback_all)}")
            else:
                # Si ya estábamos usando la clave de respaldo o no fue un error de cuota,
                # aplicamos el fallback normal del modelo (ej. probar con gemini-2.5-flash)
                try:
                    model_used = 'gemini-2.5-flash'
                    print(f"🔄 Intentando fallback de modelo con {model_used} usando clave activa...")
                    texto_respuesta = run_generation(model_used, active_key)
                except Exception as e_model_fallback:
                    print(f"❌ Error en fallback de modelo con clave activa: {e_model_fallback}")
                    # Si falla y la clave activa era la nativa, y el error es de cuota:
                    if not is_fallback_active and active_key == native_key and ("429" in str(e_model_fallback) or "quota" in str(e_model_fallback).lower() or "limit" in str(e_model_fallback).lower()):
                        use_backup_until = time.time() + 600
                        print(f"⚠️ [FALLBACK] Límite de cuota detectado en clave nativa durante fallback de modelo. Conmutando a clave de respaldo por 10 minutos.")
                        try:
                            texto_respuesta = run_generation('gemini-2.5-flash', GEMINI_API_KEY)
                        except Exception as e_backup_fallback:
                            print(f"❌ Error en clave de respaldo en fallback: {e_backup_fallback}")
                            raise HTTPException(status_code=500, detail=f"Error en clave nativa y de respaldo: {str(e_backup_fallback)}")
                    else:
                        raise HTTPException(status_code=500, detail=f"Error en modelo principal y fallback: {str(e_model_fallback)}")
        
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



@app.post("/v1/transcribe")
async def transcribe_image(file: UploadFile = File(...)):
    global use_backup_until
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ACA_VA_TU_CLAVE":
        raise HTTPException(status_code=500, detail="Gemini API Key no configurada en el servidor.")
        
    try:
        content = await file.read()
        mime_type = file.content_type or "image/jpeg"
        
        # Determinar si usar clave principal o fallback
        import time
        current_time = time.time()
        is_fallback_active = current_time < use_backup_until
        active_key = GEMINI_API_KEY
        
        genai.configure(api_key=active_key)
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        prompt = (
            "Eres un experto en digitalización de manuales técnicos de cafeteras y equipamiento comercial. "
            "Transcribe TODO el texto, tablas y estructura de esta imagen a un formato Markdown (.md) limpio, profesional y bien estructurado. "
            "Si la imagen contiene diagramas, describe el diagrama en texto de forma técnica. "
            "Devuelve ÚNICAMENTE el código Markdown resultante, sin bloques de código con triple comilla invertida (```markdown) "
            "ni comentarios introductorios o explicativos. Es muy importante que no agregues explicaciones externas, solo la transcripción."
        )
        
        image_part = {
            "mime_type": mime_type,
            "data": content
        }
        
        print(f"🔄 Transcribiendo imagen ({len(content)} bytes, {mime_type}) con Gemini-2.0-flash...")
        response = model.generate_content([image_part, prompt])
        print(f"✅ Transcripción completada ({len(response.text)} caracteres)")
        return {"markdown": response.text}
    except Exception as e:
        print(f"❌ Error en transcripción de imagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    global use_backup_until
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ACA_VA_TU_CLAVE":
        raise HTTPException(status_code=500, detail="Gemini API Key no configurada en el servidor.")
        
    import tempfile
    import json
    import time
    
    temp_path = None
    file_ref = None
    
    try:
        content = await file.read()
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        if not suffix:
            suffix = ".mp4"
            
        # 1. Guardar localmente de forma temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = tmp.name
            
        print(f"🔄 Video guardado temporalmente en: {temp_path} ({len(content)} bytes)")
        
        # 2. Configurar Gemini
        current_time = time.time()
        is_fallback_active = current_time < use_backup_until
        active_key = GEMINI_API_KEY
        
        genai.configure(api_key=active_key)
        
        # 3. Subir el archivo usando la API de archivos
        print(f"📤 Subiendo video {file.filename} a los servidores de Gemini...")
        file_ref = genai.upload_file(path=temp_path)
        
        # 4. Esperar el procesamiento del archivo
        print(f"⏳ Esperando procesamiento del archivo {file_ref.name}...")
        while file_ref.state.name == "PROCESSING":
            time.sleep(2)
            file_ref = genai.get_file(file_ref.name)
            
        if file_ref.state.name == "FAILED":
            raise Exception("El procesamiento del video en Gemini falló.")
            
        print("✅ Archivo procesado y listo en Gemini.")
        
        # 5. Generar análisis visual inicial
        model_name = "gemini-2.0-flash"
        analysis_prompt = (
            "Analiza este video de una máquina comercial (cafetera, molino, etc.) mostrando una falla o un código de error. "
            "Identifica el tipo de máquina, la marca/modelo si es posible, y describe el problema o código de error visualizado. "
            "Responde en un formato JSON estructurado con las siguientes claves y valores en español: "
            "\"tipo_equipo\": \"...\", \"marca\": \"...\", \"modelo\": \"...\", \"error_detectado\": \"...\", \"descripcion_falla\": \"...\""
        )
        
        try:
            print(f"🤖 Consultando análisis visual a {model_name}...")
            model = genai.GenerativeModel(model_name=model_name)
            response = model.generate_content([file_ref, analysis_prompt])
            analysis_text = response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "limit" in str(e).lower():
                model_name = "gemini-2.5-flash"
                print(f"🔄 [FALLBACK] Límite de cuota en gemini-2.0-flash. Reintentando análisis con {model_name}...")
                model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content([file_ref, analysis_prompt])
                analysis_text = response.text
            else:
                raise e
                
        print(f"Resultado análisis visual: {analysis_text[:200]}...")
        
        # Parsear JSON
        try:
            clean_text = analysis_text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0]
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0]
            data = json.loads(clean_text.strip())
        except Exception as json_err:
            print(f"⚠️ No se pudo parsear el resultado como JSON: {json_err}. Usando fallback.")
            data = {
                "tipo_equipo": "Equipamiento comercial",
                "marca": "",
                "modelo": "",
                "error_detectado": "Falla visual",
                "descripcion_falla": analysis_text
            }
            
        # 6. Consultar base de conocimiento (RAG)
        query_parts = [data.get("marca"), data.get("modelo"), data.get("error_detectado")]
        query_str = " ".join([p for p in query_parts if p])
        print(f"🔍 Buscando manuales para: '{query_str}'...")
        rag_response = consultar_brain_hermes(query=query_str.strip())
        
        # 7. Generar diagnóstico integrado
        prompt_final = (
            f"Como el Agente Supervisor (con la identidad de 🧠 [Hermes]), responde de manera profesional y resolutiva al técnico. "
            f"Combina el siguiente análisis visual del video:\n"
            f"- Tipo de equipo: {data.get('tipo_equipo')}\n"
            f"- Marca y modelo: {data.get('marca')} {data.get('modelo')}\n"
            f"- Error/Síntoma detectado: {data.get('error_detectado')}\n"
            f"- Descripción visual de la falla: {data.get('descripcion_falla')}\n\n"
            f"Con la información técnica extraída de nuestra base de conocimiento:\n"
            f"{rag_response}\n\n"
            f"Por favor, genera un diagnóstico integrado en español redactado en un tono técnico, estructurado en Markdown, "
            f"que empiece con el prefijo '🧠 [Hermes]' y enumere detalladamente los pasos de reparación recomendados."
        )
        
        try:
            print(f"🤖 Generando diagnóstico final integrado con {model_name}...")
            model = genai.GenerativeModel(model_name=model_name)
            response_final = model.generate_content(prompt_final)
        except Exception as e:
            if model_name == "gemini-2.0-flash" and ("429" in str(e) or "quota" in str(e).lower() or "limit" in str(e).lower()):
                model_name = "gemini-2.5-flash"
                print(f"🔄 [FALLBACK] Límite de cuota en diagnóstico. Reintentando con {model_name}...")
                model = genai.GenerativeModel(model_name=model_name)
                response_final = model.generate_content(prompt_final)
            else:
                raise e
                
        print("✅ Diagnóstico completado.")
        return {"diagnosis": response_final.text}
        
    except Exception as e:
        print(f"❌ Error en análisis de video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 8. Limpiar recursos
        if file_ref:
            try:
                print(f"🧹 Eliminando archivo temporal en Gemini: {file_ref.name}")
                genai.delete_file(file_ref.name)
            except Exception as e_del:
                print(f"Error eliminando archivo en Gemini: {e_del}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e_unl:
                print(f"Error eliminando archivo local temporal: {e_unl}")


if __name__ == "__main__":
    print("🚀 Levantando Antigravity Supervisor API en el puerto 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
