import os
import sqlite3
from datetime import datetime

DB_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/brain/recordatorios.db"

def obtener_conexion():
    """Retorna una conexión activa a la base de datos de recordatorios y crea la estructura si no existe."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarea TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha_creacion TEXT NOT NULL,
            fecha_completado TEXT
        )
    """)
    conn.commit()
    return conn

def crear_recordatorio(tarea):
    """Crea un nuevo recordatorio o tarea pendiente."""
    if not tarea or not str(tarea).strip():
        return "Error: El texto de la tarea no puede estar vacío."
        
    conn = obtener_conexion()
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute(
            "INSERT INTO recordatorios (tarea, estado, fecha_creacion) VALUES (?, 'pendiente', ?)",
            (tarea.strip(), fecha_actual)
        )
        conn.commit()
        last_id = cursor.lastrowid
        return f"Éxito: Recordatorio #{last_id} guardado correctamente: '{tarea}'."
    except Exception as e:
        return f"Error al guardar recordatorio: {e}"
    finally:
        conn.close()

def listar_recordatorios(estado="todos"):
    """Lista los recordatorios filtrados por su estado ('pendiente', 'completado', 'todos')."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    estado = str(estado).strip().lower()
    
    try:
        if estado == "pendiente":
            cursor.execute("SELECT id, tarea, estado, fecha_creacion FROM recordatorios WHERE estado = 'pendiente' ORDER BY id ASC")
        elif estado == "completado":
            cursor.execute("SELECT id, tarea, estado, fecha_creacion, fecha_completado FROM recordatorios WHERE estado = 'completado' ORDER BY id ASC")
        else:
            cursor.execute("SELECT id, tarea, estado, fecha_creacion, fecha_completado FROM recordatorios ORDER BY id ASC")
            
        rows = cursor.fetchall()
        if not rows:
            return "No se encontraron recordatorios."
            
        resultado = []
        for r in rows:
            icon = "📌" if r["estado"] == "pendiente" else "✅"
            info = f"#{r['id']} {icon} {r['tarea']} (Creado: {r['fecha_creacion']})"
            if r["estado"] == "completado" and r["fecha_completado"]:
                info += f" - Completado: {r['fecha_completado']}"
            resultado.append(info)
            
        return "\n".join(resultado)
    except Exception as e:
        return f"Error al listar recordatorios: {e}"
    finally:
        conn.close()

def marcar_completado(id_recordatorio):
    """Marca un recordatorio pendiente como completado."""
    try:
        id_rec = int(id_recordatorio)
    except ValueError:
        return "Error: El ID del recordatorio debe ser un número entero."

    conn = obtener_conexion()
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Verificar si existe y está pendiente
        cursor.execute("SELECT estado, tarea FROM recordatorios WHERE id = ?", (id_rec,))
        row = cursor.fetchone()
        if not row:
            return f"Error: No existe el recordatorio con ID #{id_rec}."
        if row["estado"] == "completado":
            return f"Info: El recordatorio #{id_rec} ('{row['tarea']}') ya estaba marcado como completado."
            
        cursor.execute(
            "UPDATE recordatorios SET estado = 'completado', fecha_completado = ? WHERE id = ?",
            (fecha_actual, id_rec)
        )
        conn.commit()
        return f"Éxito: Tarea #{id_rec} ('{row['tarea']}') marcada como completada."
    except Exception as e:
        return f"Error al actualizar recordatorio: {e}"
    finally:
        conn.close()

def eliminar_recordatorio(id_recordatorio):
    """Elimina definitivamente un recordatorio por su ID."""
    try:
        id_rec = int(id_recordatorio)
    except ValueError:
        return "Error: El ID del recordatorio debe ser un número entero."

    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT tarea FROM recordatorios WHERE id = ?", (id_rec,))
        row = cursor.fetchone()
        if not row:
            return f"Error: No existe el recordatorio con ID #{id_rec}."
            
        cursor.execute("DELETE FROM recordatorios WHERE id = ?", (id_rec,))
        conn.commit()
        return f"Éxito: Recordatorio #{id_rec} ('{row['tarea']}') eliminado físicamente."
    except Exception as e:
        return f"Error al eliminar recordatorio: {e}"
    finally:
        conn.close()
