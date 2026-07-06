import os
import sqlite3
import json
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
DB_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/brain/correcciones.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS correcciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pregunta TEXT,
            respuesta_incorrecta TEXT,
            correccion TEXT,
            vector TEXT,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

def guardar_correccion(pregunta, respuesta_incorrecta, correccion):
    init_db()
    embedding_str = None
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=pregunta
            )
            embedding_str = json.dumps(res['embedding'])
    except Exception as e:
        print(f"Error generando embedding para corrección: {e}")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO correcciones (pregunta, respuesta_incorrecta, correccion, vector, fecha) VALUES (?, ?, ?, ?, ?)",
        (pregunta, respuesta_incorrecta, correccion, embedding_str, fecha)
    )
    conn.commit()
    conn.close()
    print("Corrección guardada con éxito.")

def obtener_correcciones_relevantes(pregunta, limit=2):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT pregunta, respuesta_incorrecta, correccion, vector FROM correcciones")
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return []
        
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=pregunta
            )
            query_vector = np.array(res['embedding'])
            
            scored_rows = []
            for q, r_inc, corr, vec_str in rows:
                if vec_str:
                    vec = np.array(json.loads(vec_str))
                    dot = np.dot(query_vector, vec)
                    norm_q = np.linalg.norm(query_vector)
                    norm_v = np.linalg.norm(vec)
                    score = dot / (norm_q * norm_v) if (norm_q * norm_v) > 0 else 0
                    scored_rows.append((score, q, r_inc, corr))
                else:
                    scored_rows.append((0, q, r_inc, corr))
                    
            scored_rows.sort(key=lambda x: x[0], reverse=True)
            conn.close()
            return [(q, r_inc, corr) for score, q, r_inc, corr in scored_rows[:limit] if score > 0.4]
    except Exception as e:
        print(f"Error en búsqueda semántica de correcciones: {e}")
        
    cursor.execute("SELECT pregunta, respuesta_incorrecta, correccion FROM correcciones ORDER BY id DESC LIMIT ?", (limit,))
    latest = cursor.fetchall()
    conn.close()
    return latest
