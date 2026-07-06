import os
import sys
import glob
import time
import shutil
import sqlite3
from pathlib import Path

BASE_DIR = Path("/home/cristian/Documentos/Supervisor")
DB_PATH = BASE_DIR / "supervisor_local.db"
LOG_PATH = BASE_DIR / "ingestor.log"

def check_process(pattern):
    for path in glob.glob('/proc/[0-9]*/cmdline'):
        try:
            with open(path, 'r') as f:
                cmd = f.read().replace('\x00', ' ')
                if pattern in cmd and "autodiagnostico" not in cmd:
                    return True
        except:
            pass
    return False

def obtener_estado_sistema():
    userbot_ok = check_process("userbot_supervisor.py")
    whatsapp_ok = check_process("motor_whatsapp_web.py") or os.path.exists("/home/cristian/Documentos/Supervisor/whatsapp_last_read.json")
    
    db_status = "Inaccesible"
    locales_cnt = 0
    pendientes_cnt = 0
    soluciones_cnt = 0
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT count(*) FROM locales")
            locales_cnt = c.fetchone()[0]
            try:
                c.execute("SELECT count(*) FROM pendientes")
                pendientes_cnt = c.fetchone()[0]
            except:
                pass
            try:
                c.execute("SELECT count(*) FROM soluciones_pendientes")
                soluciones_cnt = c.fetchone()[0]
            except:
                pass
            conn.close()
            db_status = "OK"
        except Exception as e:
            db_status = f"Error: {e}"
            
    ingestor_ok = "Inactivo"
    if LOG_PATH.exists():
        try:
            mtime = os.path.getmtime(LOG_PATH)
            diff_min = (time.time() - mtime) / 60
            if diff_min < 20:
                ingestor_ok = "Activo (OK)"
            else:
                ingestor_ok = f"Inactivo hace {int(diff_min)} min"
        except Exception:
            pass
            
    whatsapp_state = "Sin registros recientes"
    state_file = Path("/home/cristian/Documentos/Supervisor/whatsapp_last_read.json")
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                import json
                data = json.load(f)
                whatsapp_state = f"Último mensaje en Mto. Franquicias: {data.get('Equipo Mto. Franquicias')}"
        except:
            pass

    report = (
        "=== DIAGNÓSTICO DE INFRAESTRUCTURA Y SISTEMAS ===\n"
        f"• Userbot (Telegram): {'🟢 ACTIVO' if userbot_ok else '🔴 CAÍDO'}\n"
        f"• Ingestor de WhatsApp: {'🟢 OPERATIVO' if whatsapp_ok else '🔴 CAÍDO/INACTIVO'}\n"
        f"• Base de Datos Master: {db_status} ({locales_cnt} locales, {pendientes_cnt} tickets registrados, {soluciones_cnt} soluciones wiki)\n"
        f"• Ingestor Automático (PDFs): {ingestor_ok}\n"
        f"• Estado del Puente WhatsApp: {whatsapp_state}\n"
        "==============================================="
    )
    return report

if __name__ == "__main__":
    print(obtener_estado_sistema())
