import os
import re
from datetime import datetime, timedelta
import google.generativeai as genai
import notificador_telegram
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("❌ Falta GEMINI_API_KEY en .env")
    exit(1)

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
import llm_fallback

LOG_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/grupo_aprendizaje.log"
PROCESADAS_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/preguntas_procesadas.txt"

def cargar_procesadas():
    if os.path.exists(PROCESADAS_PATH):
        with open(PROCESADAS_PATH, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def guardar_procesada(pregunta):
    with open(PROCESADAS_PATH, "a", encoding="utf-8") as f:
        f.write(pregunta + "\n")

def buscar_respuesta_gemini(pregunta):
    import autodiagnostico
    instrucciones = (
        "Eres Hermes, el asistente y supervisor de IA para el equipo de mantenimiento de franquicias de Mostaza, "
        "corriendo sobre la infraestructura de 'AntiGravity'. Tienes componentes de software como 'Ingestor Antigravity', "
        "'bot de WhatsApp' y 'Userbot de Telegram'.\n"
        "Analiza la duda recibida:\n"
        "1. Si la duda es una pregunta real sobre mantenimiento de equipamiento gastronómico o industrial (cafeteras Cimbali, broilers, freidoras, etc.), "
        "usa tu base de conocimientos para responder de forma técnica, paso a paso, precisa y profesional en no más de 3 párrafos cortos.\n"
        "2. Si la duda es sobre el funcionamiento del bot o el sistema (ej. 'error con el ingestor', 'bot de whatsapp', 'antigravity', etc.), "
        "explica su estado actual basándote en el contexto del sistema provisto y sugiere acciones correspondientes.\n"
        "3. Si la duda es sobre políticas administrativas de la empresa (ej. presentismo, horarios, presentismo en la app), "
        "explica de forma clara cómo el sistema asiste a la verificación (fichadas, geolocalización, etc.) según las políticas vigentes.\n"
        "4. IMPORTANTE: Si la duda NO es una consulta útil (es decir, es una conversación casual, comentarios del supervisor, quejas, "
        "charlas entre técnicos que no requieren soporte, o no tiene sentido responderla), responde ÚNICAMENTE con la palabra: IGNORE_QUERY\n\n"
        "--- EJEMPLOS DE DIAGNÓSTICO (FEW-SHOT) ---\n"
        "**Ejemplo 1 (Falla de Vapor en Cimbali):**\n"
        "Pregunta: 'La cafetera Cimbali M26 no tira vapor por la lanza derecha'\n"
        "Respuesta: 'Hola colega. Para solucionar la falta de vapor en la lanza derecha de una Cimbali M26, sigue estos pasos de descarte técnico:\n"
        "1. Verifica si la boquilla de la lanza está obstruida con residuos de leche seca. Desenrosca la punta y límpiala con un clip o aguja fina.\n"
        "2. Si el problema persiste, realiza una purga de vapor y comprueba si hay paso físico de aire o si la válvula rotativa de control de vapor gira en vacío (posible desgaste del vástago de la maneta).\n"
        "3. Si no sale nada de aire/vapor en absoluto pero la lanza izquierda funciona, la electroválvula de vapor derecha o el grifo manual correspondiente están bloqueados internamente por sarro, requiriendo desmontaje y descalcificación con ácido cítrico.'\n\n"
        "**Ejemplo 2 (Falla de Broiler Nieco - Apagado de Llama):**\n"
        "Pregunta: 'El broiler de Morón se apaga a los 5 minutos de encenderlo'\n"
        "Respuesta: 'Buen día técnico. Cuando un broiler Nieco o similar se apaga tras unos minutos de marcha, la causa principal suele ser la acumulación de calor o falla de detección de llama:\n"
        "1. Revisa el sensor de llama (fotocélula o termocupla). Si está sucio de grasa u hollín, limpiarlo suavemente con un paño seco.\n"
        "2. Comprueba el extractor de aire/campana. Si la extracción no tiene suficiente caudal o hay contrapresión, el switch de seguridad de aire cortará el suministro de gas a los pocos minutos.\n"
        "3. Verifica que la presión dinámica de gas en la línea del local sea estable (debe rondar los 18-20 mbar en GN o 28-30 mbar en GLP) y no caiga cuando otros equipos de la línea encienden.'"
    )
    
    info_sistema = ""
    pregunta_lower = pregunta.lower()
    if any(term in pregunta_lower for term in ["ingestor", "bot", "whatsapp", "antigravity", "supervisor", "sistema"]):
        try:
            info_sistema = f"\n\n[CONTEXTO DE INFRAESTRUCTURA ACTUAL EN VIVO]:\n{autodiagnostico.obtener_estado_sistema()}"
        except Exception:
            pass

    try:
        response = llm_fallback.generar_texto(pregunta + info_sistema, system_instruction=instrucciones)
        return response.strip() if response else None
    except Exception as e:
        print(f"Error con LLM Fallback: {e}")
        return None

def ejecutar_busqueda():
    if not os.path.exists(LOG_PATH):
        print("No hay log de aprendizaje.")
        return

    procesadas = cargar_procesadas()
    hoy = datetime.now()
    limite = hoy - timedelta(hours=24)
    preguntas_candidatas = []

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    # Regex para parsear el log: [2026-06-15 18:40:02] [Privado] ID: 215173956 (...) -> mensaje
    pattern = re.compile(r"\[(.*?)\] \[(.*?)\] ID: .*? -> (.*)")
    
    for linea in lineas:
        match = pattern.match(linea)
        if match:
            fecha_str, tipo, mensaje = match.groups()
            try:
                fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                if fecha_obj >= limite:
                    mensaje_lower = mensaje.lower()
                    # Filtro rudimentario para dudas técnicas
                    if "?" in mensaje_lower or "error" in mensaje_lower or "falla" in mensaje_lower:
                        # Limpiamos tags
                        pregunta_limpia = mensaje.strip()
                        if pregunta_limpia not in procesadas and len(pregunta_limpia) > 10:
                            preguntas_candidatas.append(pregunta_limpia)
            except Exception:
                pass

    if not preguntas_candidatas:
        print("No hay nuevas preguntas candidatas.")
        return

    # Limitar a procesar máximo 3 por ejecución para no saturar al supervisor
    for pregunta in preguntas_candidatas[:3]:
        print(f"Analizando: {pregunta}")
        respuesta = buscar_respuesta_gemini(pregunta)
        if respuesta:
            if "IGNORE_QUERY" in respuesta:
                print(f"Pregunta ignorada por ser ajena al contexto técnico: {pregunta}")
                guardar_procesada(pregunta)
                continue
                
            alerta = (
                f"🔍 *[BÚSQUEDA AUTÓNOMA]*\n"
                f"Detecté esta duda técnica reciente:\n_{pregunta}_\n\n"
                f"💡 *Respuesta encontrada por Gemini:*\n{respuesta}\n\n"
                f"👉 _Si la información es útil, puedes reenviarla al grupo de técnicos._"
            )
            exito = notificador_telegram.enviar_alerta(alerta, agente="Hermes Research")
            if exito:
                guardar_procesada(pregunta)

if __name__ == "__main__":
    ejecutar_busqueda()
