import urllib.request
import csv
import sqlite3
import os

URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTs9ktsmxlfoL6C0aD-bJvjkM_WTKRh0EHaYoGPxwmzRhwHtGfaLT75GJinUA9lougJOh07bGffz_go/pub?gid=923285048&single=true&output=csv"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supervisor_local.db")

def sync_locales():
    print("[Sync] Descargando CSV desde Google Sheets...")
    req = urllib.request.Request(URL)
    with urllib.request.urlopen(req) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
    
    reader = csv.reader(lines)
    header = next(reader)
    
    # Índices basados en la estructura:
    # 0: SIGLA SISTEMA, 1: SIGLA TICKETS, 2: REGIONAL, 3: SUPERVISOR (GTE ZONA)
    # 4: LOCAL, 5: MAIL, 6: DIRECCION, 7: LOCALIDAD, 8: PROVINCIA
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    upsertados = 0
    
    for row in reader:
        if len(row) < 7: continue
        
        sigla = row[0].strip()
        if not sigla or sigla == "-": 
            sigla = row[1].strip() # Fallback a SIGLA TICKETS
            if not sigla or sigla == "-":
                continue
                
        nombre = row[4].strip()
        direccion = f"{row[6].strip()}, {row[7].strip()}, {row[8].strip()}"
        supervisor = row[3].strip()
        telefono = "N/A" # No está en la planilla
        
        # Upsert: Inserta o actualiza
        cursor.execute("""
            INSERT INTO locales (sigla, nombre, direccion, telefono, supervisor)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(sigla) DO UPDATE SET
                nombre=excluded.nombre,
                direccion=excluded.direccion,
                supervisor=excluded.supervisor
        """, (sigla, nombre, direccion, telefono, supervisor))
        upsertados += 1
        
    conn.commit()
    conn.close()
    print(f"[Sync] Se han sincronizado {upsertados} locales exitosamente.")

if __name__ == "__main__":
    sync_locales()
