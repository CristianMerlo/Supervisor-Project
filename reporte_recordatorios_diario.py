#!/usr/bin/env python3
import os
import sys
import sqlite3
from datetime import datetime

PROJECT_ROOT = "/home/cristian/PROYECTOS/Supervisor-Project"
sys.path.insert(0, PROJECT_ROOT)

import notificador_telegram

DB_PATH = "/home/cristian/PROYECTOS/Supervisor-Project/brain/recordatorios.db"

def main():
    if not os.path.exists(DB_PATH):
        print("La base de datos de recordatorios no existe.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # 1. Obtener tareas completadas hoy
        cursor.execute(
            "SELECT id, tarea, fecha_creacion, fecha_completado FROM recordatorios WHERE estado = 'completado' AND fecha_completado LIKE ?",
            (f"{hoy_str}%",)
        )
        completadas_hoy = cursor.fetchall()
        
        # 2. Obtener todas las tareas pendientes
        cursor.execute(
            "SELECT id, tarea, fecha_creacion FROM recordatorios WHERE estado = 'pendiente' ORDER BY id ASC"
        )
        pendientes = cursor.fetchall()
        
        # Si no hay absolutamente nada pendiente ni completado hoy, salimos para no molestar
        if not completadas_hoy and not pendientes:
            print("No hay recordatorios pendientes ni completados hoy.")
            return

        mensaje = f"📋 *RESUMEN DIARIO DE RECORDATORIOS Y TAREAS*\n\n"
        
        if completadas_hoy:
            mensaje += "✅ *Completados hoy:*\n"
            for r in completadas_hoy:
                mensaje += f"- #{r['id']} {r['tarea']}\n"
            mensaje += "\n"
        else:
            mensaje += "✅ *Completados hoy:* Ninguno.\n\n"
            
        if pendientes:
            mensaje += "📌 *Pendientes para los siguientes días:*\n"
            for r in pendientes:
                mensaje += f"- #{r['id']} {r['tarea']} _(Anotado: {r['fecha_creacion'][:10]})_\n"
        else:
            mensaje += "📌 *Pendientes:* ¡No tienes tareas pendientes! Todo al día. 🎉\n"
            
        mensaje += "\n💬 _Puedes agregar más tareas o marcar estas como completadas hablándole directamente a Hermes._"
        
        # Enviar al chat privado de Cristian (ID: 215173956)
        destinatario_id = 215173956
        exito = notificador_telegram.enviar_alerta(mensaje, agente="Hermes Reminders", destinatario_id=destinatario_id)
        if exito:
            print("[+] Reporte de recordatorios diario enviado correctamente.")
        else:
            print("[-] Error enviando el reporte a Telegram.")
            
    except Exception as e:
        print(f"Error generando reporte diario: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
