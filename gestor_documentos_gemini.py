import os
import glob
import json
from dotenv import load_dotenv
import google.generativeai as genai

MANUALES_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/01_Manuales_Tecnicos/"
DB_FILES = "/home/cristian/PROYECTOS/Supervisor-Project/brain/gemini_files.json"

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY no encontrada")
    exit(1)

genai.configure(api_key=api_key)

def sync_manuales():
    print("Sincronizando manuales con Gemini File API...")
    if os.path.exists(DB_FILES):
        with open(DB_FILES, "r") as f:
            gemini_files = json.load(f)
    else:
        gemini_files = {}

    archivos = glob.glob(os.path.join(MANUALES_DIR, "*.md"))
    archivos_actuales = []
    
    for archivo in archivos:
        nombre = os.path.basename(archivo)
        archivos_actuales.append(nombre)
        if nombre not in gemini_files:
            print(f"Subiendo nuevo manual: {nombre}")
            try:
                g_file = genai.upload_file(archivo, display_name=nombre)
                gemini_files[nombre] = {
                    "name": g_file.name,
                    "uri": g_file.uri
                }
            except Exception as e:
                print(f"Error subiendo {nombre}: {e}")
                
    # Limpiar los que ya no existen
    a_borrar = [n for n in gemini_files.keys() if n not in archivos_actuales]
    for n in a_borrar:
        print(f"Eliminando manual obsoleto de Gemini: {n}")
        try:
            genai.delete_file(gemini_files[n]["name"])
        except:
            pass
        del gemini_files[n]

    with open(DB_FILES, "w") as f:
        json.dump(gemini_files, f, indent=4)
        
    print(f"Sincronización completa. {len(gemini_files)} manuales en Gemini.")

if __name__ == "__main__":
    sync_manuales()
