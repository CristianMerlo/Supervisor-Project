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

def extraer_errores(texto, maquina):
    """Le pide a Gemini que extraiga posibles errores de todo el manual."""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""Extrae todos los códigos de error y soluciones del siguiente texto del manual de la máquina '{maquina}'.
Si no hay códigos de error ni soluciones en el manual, devuelve una lista vacía [].
Devuelve ÚNICAMENTE los errores encontrados en el JSON estructurado.

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
        print(f"[Gemini Exception]: {e}")
        return None

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
            
    print("--- Extracción finalizada ---")

if __name__ == "__main__":
    main()
