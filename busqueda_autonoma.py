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
    # System prompt instruyendo a ser sintético y directo
    instrucciones = (
        "Eres Hermes, un experto técnico en mantenimiento industrial y gastronómico (ej. cafeteras Cimbali, hornos, freidoras, etc.). "
        "Un técnico en campo tiene la siguiente duda o problema técnico. Usa tu base de conocimientos para darle una solución paso a paso, precisa y profesional. "
        "Si no sabes la respuesta exacta, indícalo. Responde en no más de 3 párrafos cortos."
    )
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"{instrucciones}\n\nDuda técnica: {pregunta}")
        return response.text.strip()
    except Exception as e:
        print(f"Error con Gemini: {e}")
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
