import os
import json
import glob
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_LOCAL = "qwen2.5:0.5b"

MANUALES_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/01_Manuales_Tecnicos/"
OUTPUT_JSON = "/home/cristian/PROYECTOS/Supervisor-Project/brain/base_errores.json"

import subprocess
import time

def consultar_ollama(prompt, retries=3):
    """Consulta al agente local Ollama, con autorecuperación si falla."""
    for intento in range(retries):
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": MODELO_LOCAL,
                "prompt": prompt,
                "stream": False
            }, timeout=120)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                print(f"[Ollama Error] Status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[Ollama Exception] Intento {intento+1}/{retries}: {e}")
            print("[SUPERVISOR] Intentando reiniciar el servicio de Ollama...")
            try:
                # Usar sudo no interactivo si es posible, o systemctl --user. 
                # Si esto falla, Ollama podría estar corriendo como proceso normal.
                subprocess.run(["systemctl", "restart", "ollama"], check=False)
                time.sleep(10) # Esperar a que levante
            except:
                pass
    
    # Si llega hasta aquí, fracasó las 3 veces
    import notificador_telegram
    notificador_telegram.enviar_alerta("❌ [CRÍTICO] Falló la extracción nocturna de manuales. Ollama está caído y no se pudo reiniciar.", agente="Sistema")
    return None

def extraer_errores(texto, archivo):
    """Le pide a Ollama que extraiga posibles errores de un fragmento de texto."""
    maquina = os.path.basename(archivo).replace(".md", "")
    prompt = f"""Extrae códigos de error y soluciones del siguiente texto del manual de la máquina '{maquina}'.
Si no hay códigos de error ni soluciones, responde únicamente con la palabra 'NADA'.
Si encuentras información de resolución de problemas (troubleshooting), devuelve el resultado EXCLUSIVAMENTE en el siguiente formato JSON estricto, sin ninguna otra palabra ni explicación adicional:
[
  {{"codigo": "E01", "falla": "Descripción de la falla", "solucion": "Solución propuesta"}}
]

Texto a analizar:
{texto}
"""
    return consultar_ollama(prompt)

def main():
    print(f"--- Iniciando extracción de errores en segundo plano con {MODELO_LOCAL} ---")
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
            
        # Fragmentar en bloques de 6000 caracteres para no asfixiar a Llama 3.2 1b
        CHUNK_SIZE = 6000
        for i in range(0, len(contenido), CHUNK_SIZE):
            chunk = contenido[i:i+CHUNK_SIZE]
            print(f"  Analizando fragmento {i//CHUNK_SIZE + 1} de {(len(contenido)//CHUNK_SIZE) + 1}...")
            
            respuesta = extraer_errores(chunk, archivo)
            if respuesta and "NADA" not in respuesta.upper():
                try:
                    # Limpiar posibles bloques de markdown en la respuesta de Ollama
                    json_str = respuesta.replace("```json", "").replace("```", "").strip()
                    datos = json.loads(json_str)
                    if isinstance(datos, list):
                        base_errores[maquina].extend(datos)
                        print(f"  [+] Extraídos {len(datos)} errores.")
                        
                        # Guardar progresivamente
                        with open(OUTPUT_JSON, "w", encoding="utf-8") as f_out:
                            json.dump(base_errores, f_out, indent=4, ensure_ascii=False)
                except json.JSONDecodeError:
                    print(f"  [!] Ollama devolvió algo que no es JSON válido: {respuesta[:100]}...")
            
    print("--- Extracción finalizada ---")

if __name__ == "__main__":
    main()
