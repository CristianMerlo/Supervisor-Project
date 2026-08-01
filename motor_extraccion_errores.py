import os
import json
import glob
from dotenv import load_dotenv
import google.generativeai as genai
import typing_extensions as typing

MANUALES_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/01_Manuales_Tecnicos/"
OUTPUT_JSON = "/home/cristian/PROYECTOS/Supervisor-Project/brain/base_errores.json"

# Configurar Gemini
load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY no encontrada en .env")
    exit(1)

genai.configure(api_key=api_key)

class Falla(typing.TypedDict):
    codigo: str
    falla: str
    solucion: str

def extraer_errores_groq(texto, maquina):
    """Fallback usando la API de Groq si Gemini falla por cuota. Soporta fragmentación para archivos grandes."""
    import requests
    import time
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("  [!] Sin API Key de Groq para fallback.")
        return None

    # Fragmentar el texto si es muy largo para evitar Límite de Tokens (413/429)
    limite_chars = 15000
    fragmentos = []
    if len(texto) > limite_chars:
        # Dividir por caracteres intentando cortar por líneas
        pos = 0
        while pos < len(texto):
            fragmentos.append(texto[pos:pos+limite_chars])
            pos += limite_chars
        print(f"  [Groq] Archivo grande ({len(texto)} chars). Dividido en {len(fragmentos)} fragmentos para no saturar API.")
    else:
        fragmentos = [texto]

    todas_fallas = []
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    for idx, frag in enumerate(fragmentos):
        if idx > 0:
            print(f"  [Groq] Durmiendo 12s antes de procesar fragmento {idx+1}/{len(fragmentos)}...")
            time.sleep(12)  # Dormir para evitar rebasar TPM de Groq
            
        prompt = f"""Analiza el fragmento {idx+1}/{len(fragmentos)} del manual de la máquina '{maquina}' y extrae un listado estructurado de fallas y soluciones.
Debes responder ÚNICAMENTE con un JSON en formato de lista de objetos, donde cada objeto tenga exactamente las siguientes claves:
- "codigo": el código de error o identificador de la falla (por ejemplo, E01, Y51, etc.).
- "falla": descripción breve en español de la falla o síntoma del equipo.
- "solucion": procedimiento específico en español para reparar o corregir la falla.

Reglas estrictas:
1. Extrae únicamente fallas mecánicas, de erogación o códigos de error reales.
2. NO extraigas normas de seguridad ni descripciones de funcionamiento correcto.
3. Si no hay fallas, devuelve una lista vacía [].
4. Todo el contenido debe estar traducido y redactado en ESPAÑOL.

Texto a analizar:
{frag}
"""
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                raw_content = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(raw_content)
                lista = []
                if isinstance(parsed, list):
                    lista = parsed
                elif isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            lista = v
                            break
                todas_fallas.extend(lista)
                print(f"  [Groq] Procesado fragmento {idx+1}. Encontradas {len(lista)} fallas.")
            else:
                print(f"  [!] Groq Fallback fragmento {idx+1} retornó status {res.status_code}")
        except Exception as e:
            print(f"  [!] Falló fragmento {idx+1}: {e}")
            
    return todas_fallas

def extraer_errores(texto, maquina):
    """Le pide a Gemini que extraiga posibles errores de todo el manual, con fallback a Groq."""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""Analiza el manual de la máquina '{maquina}' y extrae un listado estructurado de fallas y soluciones siguiendo estrictamente estas reglas:

1. FILTRADO DE FALLAS REALES: Extrae únicamente fallas mecánicas, eléctricas, de erogación o códigos de error específicos que requieran un procedimiento de reparación.
2. EXCLUSIÓN DE NORMAS DE SEGURIDAD: NO extraigas advertencias de seguridad generales (ej. 'no tocar superficies calientes', 'riesgo de electrocución').
3. EXCLUSIÓN DE ESTADOS NORMALES O CONFIGURACIONES: NO extraigas descripciones que digan que el equipo o una parte funciona bien o que simplemente describan cómo configurar un parámetro regular.
4. EXCLUSIÓN DE METADATA O PLACEHOLDERS: NO guardes respuestas vacías, placeholders (como 'Solución propuesta') o metadata del proceso (como 'El manual no contiene errores'). Si no hay errores válidos, retorna una lista vacía [].
5. TRADUCCIÓN AL ESPAÑOL: Todo el contenido extraído (código, falla y solución) debe estar estrictamente redactado en ESPAÑOL. Si en el manual original está en inglés u otro idioma, tradúcelo fielmente.
6. COHERENCIA LÓGICA Y ESPECIFICIDAD: La solución descrita debe ser una acción técnica ejecutable y directamente relacionada con la resolución de la falla. Evita referencias genéricas vacías como 'Ver manual' si el texto de origen provee la solución.

Texto a analizar:
{texto}
"""
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=list[Falla],
                temperature=0.1
            ),
            request_options={"timeout": 600}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  [!] Gemini falló o superó cuota: {e}. Iniciando fallback con Groq...")
        return extraer_errores_groq(texto, maquina)

def main():
    print("--- Iniciando extracción de errores en segundo plano con Gemini 2.5 Flash ---")
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            base_errores = json.load(f)
    else:
        base_errores = {}

    archivos = glob.glob(os.path.join(MANUALES_DIR, "*.md"))
    for archivo in archivos:
        maquina = os.path.basename(archivo).replace(".md", "")
        print(f"Procesando manual: {maquina}...")
        
        if maquina in base_errores and len(base_errores[maquina]) > 0:
            print(f"  [>] {maquina} ya tiene errores extraídos. Omitiendo para no duplicar.")
            continue
            
        if maquina not in base_errores:
            base_errores[maquina] = []

        with open(archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
            
        print(f"  Analizando {len(contenido)} caracteres completos...")
        
        datos = extraer_errores(contenido, maquina)
        
        if datos is not None:
            if len(datos) > 0:
                base_errores[maquina] = datos
                print(f"  [+] Extraídos {len(datos)} errores.")
            else:
                print(f"  [-] No se encontraron errores.")
                
            # Guardar progresivamente
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f_out:
                json.dump(base_errores, f_out, indent=4, ensure_ascii=False)
        else:
            print("  [!] Falló la extracción para este manual.")
        
        # Dormir 10 segundos para no saturar APIs y respetar límites de tokens por minuto (TPM)
        import time
        print("  Dormir 10s antes del siguiente manual...")
        time.sleep(10)
            
    print("--- Extracción finalizada ---")

if __name__ == "__main__":
    main()
