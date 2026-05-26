import sqlite3

def init_db():
    conn = sqlite3.connect("supervisor_local.db")
    cursor = conn.cursor()
    
    # Tabla de locales (Nivel 1 - Estático)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locales (
        sigla TEXT PRIMARY KEY,
        nombre TEXT,
        direccion TEXT,
        telefono TEXT,
        supervisor TEXT
    )
    """)
    
    # Tabla de pendientes/alertas (Nivel 2 - Dinámico)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pendientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sigla TEXT,
        detalle TEXT,
        fecha TEXT,
        estado TEXT DEFAULT 'ABIERTO',
        FOREIGN KEY(sigla) REFERENCES locales(sigla)
    )
    """)
    
    # Datos de muestra iniciales (Urquiza y Chacabuco)
    cursor.executemany("INSERT OR IGNORE INTO locales VALUES (?, ?, ?, ?, ?)", [
        ("URQ", "Urquiza", "Av. Triunvirato 4500, CABA", "+54 11 9999-8888", "Cristian Merlo"),
        ("CHA", "Chacabuco", "Calle Mitre 123, Chacabuco", "+54 2352 99-9999", "Cristian Merlo")
    ])
    
    cursor.executemany("INSERT OR IGNORE INTO pendientes (sigla, detalle, fecha) VALUES (?, ?, ?)", [
        ("CHA", "Reparación crítica del ablandador de agua (PPM > 200)", "2026-05-25"),
        ("CHA", "Fuga en cafetera Cimbali Horno 1", "2026-05-24")
    ])
    
    conn.commit()
    conn.close()
    print("[SQLite] Base de datos local inicializada exitosamente.")

if __name__ == "__main__":
    init_db()
