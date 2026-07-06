import os
import glob
import json
import sqlite3
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: No se encontró GEMINI_API_KEY en .env")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

DB_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/brain/manuales_vectores.db"
MANUALS_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/01_Manuales_Tecnicos"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manuales_vectores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo_nombre TEXT,
            texto_fragmento TEXT,
            vector TEXT
        )
    """)
    conn.commit()
    conn.close()

def chunk_text(text, chunk_size=800, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def indexar():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Limpiar tabla anterior
    cursor.execute("DELETE FROM manuales_vectores")
    conn.commit()
    
    archivos_md = glob.glob(os.path.join(MANUALS_DIR, "*.md"))
    print(f"Encontrados {len(archivos_md)} manuales para indexación semántica...")
    
    for archivo in archivos_md:
        nombre = os.path.basename(archivo)
        print(f"Procesando {nombre}...")
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Limpiar markdown excesivo pero mantener la esencia
            chunks = chunk_text(content)
            print(f"  -> Dividido en {len(chunks)} fragmentos.")
            
            for idx, chunk in enumerate(chunks):
                if len(chunk.strip()) < 30:
                    continue
                
                import time
                intentos = 5
                for intento in range(intentos):
                    try:
                        response = genai.embed_content(
                            model="models/gemini-embedding-001",
                            content=chunk
                        )
                        embedding = response['embedding']
                        
                        cursor.execute(
                            "INSERT INTO manuales_vectores (archivo_nombre, texto_fragmento, vector) VALUES (?, ?, ?)",
                            (nombre, chunk, json.dumps(embedding))
                        )
                        time.sleep(0.7) # Evita pasar las 100 peticiones por minuto
                        break
                    except Exception as e:
                        if "429" in str(e) or "quota" in str(e).lower():
                            print(f"  [Rate Limit 429] Esperando 15s para reintentar ({intento+1}/{intentos})...")
                            time.sleep(15)
                        else:
                            print(f"  [Error Fragmento {idx}] {e}")
                            break
            conn.commit()
            print(f"  [✓] {nombre} indexado.")
        except Exception as e:
            print(f"  [Error] Falló indexación de {nombre}: {e}")
            
    conn.close()
    print("¡Indexación semántica completada con éxito!")

if __name__ == "__main__":
    indexar()
