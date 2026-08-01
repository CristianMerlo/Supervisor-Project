#!/usr/bin/env python3
import os
import json
import glob
from dotenv import load_dotenv
import google.generativeai as genai
import typing_extensions as typing
import time

PROJECT_ROOT = "/home/cristian/PROYECTOS/Supervisor-Project"
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

MANUALES_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/01_Manuales_Tecnicos/"
OUTPUT_JSON = "/home/cristian/PROYECTOS/Supervisor-Project/brain/base_errores.json"

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY no encontrada.")
    exit(1)

genai.configure(api_key=api_key)

class Falla(typing.TypedDict):
    codigo: str
    falla: str
    solucion: str

def extraer_errores_gemini_15(texto, maquina):
    """Extrae usando gemini-flash-latest."""
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        
        prompt = f"""Analiza el manual de la máquina '{maquina}' y extrae un listado estructurado de fallas y soluciones siguiendo estrictamente estas reglas:

1. FILTRADO DE FALLAS REALES: Extrae únicamente fallas mecánicas, eléctricas, de erogación o códigos de error específicos que requieran un procedimiento de reparación.
2. EXCLUSIÓN DE NORMAS DE SEGURIDAD: NO extraigas advertencias de seguridad generales (ej. 'no tocar superficies calientes', 'riesgo de electrocución').
3. EXCLUSIÓN DE ESTADOS NORMALES O CONFIGURACIONES: NO extraigas descripciones que digan que el equipo o una parte funciona bien o que simplemente describan cómo configurar un parámetro regular.
4. EXCLUSIÓN DE METADATA O PLACEHOLDERS: NO guardes respuestas vacías, placeholders o metadata del proceso. Si no hay errores válidos, retorna una lista vacía [].
5. TRADUCCIÓN AL ESPAÑOL: Todo el contenido extraído (código, falla y solución) debe estar estrictamente redactado en ESPAÑOL. Si en el manual original está en inglés u otro idioma, tradúcelo fielmente.
6. COHERENCIA LÓGICA Y ESPECIFICIDAD: La solución descrita debe ser una acción técnica ejecutable y directamente relacionada con la resolución de la falla.

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
            request_options={"timeout": 60}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  [!] Falló Gemini 1.5 Flash para {maquina}: {e}")
        return []

def main():
    print("=== Completando extracción de errores con Gemini 1.5 Flash ===")
    if not os.path.exists(OUTPUT_JSON):
        print("No existe base_errores.json")
        return

    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        base_errores = json.load(f)

    # Identificar locales/manuales que tienen 0 errores o que fallaron
    a_procesar = []
    for maquina, fallas in base_errores.items():
        if len(fallas) == 0:
            a_procesar.append(maquina)

    print(f"Manuales pendientes de completar: {a_procesar}")

    for maquina in a_procesar:
        archivo_path = os.path.join(MANUALES_DIR, f"{maquina}.md")
        if not os.path.exists(archivo_path):
            continue

        print(f"Procesando {maquina} con Gemini 1.5 Flash...")
        with open(archivo_path, "r", encoding="utf-8") as f_in:
            contenido = f_in.read()

        print(f"  Analizando {len(contenido)} caracteres...")
        datos = extraer_errores_gemini_15(contenido, maquina)

        if datos is not None:
            base_errores[maquina] = datos
            print(f"  [✓] Completados {len(datos)} errores.")
            # Guardar progresivamente
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f_out:
                json.dump(base_errores, f_out, indent=4, ensure_ascii=False)
        else:
            print(f"  [!] Falló la extracción para {maquina}")

        # Dormir un poco
        time.sleep(10)

    print("=== Proceso de completitud finalizado ===")

if __name__ == "__main__":
    main()
