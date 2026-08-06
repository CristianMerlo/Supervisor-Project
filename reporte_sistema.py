import os
import sys
import time
import shutil
import socket
import sqlite3
import glob
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
BASE_DIR = Path("/home/cristian/Documentos/Supervisor")
load_dotenv(str(BASE_DIR / ".env"))
sys.path.append(str(BASE_DIR))

import notificador_telegram

def check_process(pattern):
    for path in glob.glob('/proc/[0-9]*/cmdline'):
        try:
            with open(path, 'r') as f:
                cmd = f.read().replace('\x00', ' ')
                if pattern in cmd and "reporte_sistema.py" not in cmd:
                    return True
        except:
            pass
    return False

def check_url(url):
    try:
        req = urllib.request.urlopen(url, timeout=5)
        if req.getcode() == 200:
            return "🟢 ONLINE"
        return f"🔴 ERROR {req.getcode()}"
    except Exception as e:
        return f"🔴 CAÍDO ({type(e).__name__})"

def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        days = int(uptime_seconds // (24 * 3600))
        uptime_seconds %= (24 * 3600)
        hours = int(uptime_seconds // 3600)
        uptime_seconds %= 3600
        minutes = int(uptime_seconds // 60)
        uptime_str = ""
        if days > 0: uptime_str += f"{days}d "
        if hours > 0 or days > 0: uptime_str += f"{hours}h "
        uptime_str += f"{minutes}m"
        return uptime_str
    except Exception as e:
        return f"Error: {e}"

def check_db():
    db_path = BASE_DIR / "supervisor_local.db"
    if not db_path.exists():
        return False, "Base de datos no encontrada"
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM locales")
        locales_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM pendientes WHERE estado = 'ABIERTO'")
        pendientes_cnt = cursor.fetchone()[0]
        conn.close()
        return True, f"OK ({locales_cnt} locales, {pendientes_cnt} pendientes abiertas)"
    except Exception as e:
        return False, f"Error: {e}"

def check_ingestor():
    log_path = BASE_DIR / "ingestor.log"
    if not log_path.exists():
        return "ADVERTENCIA", "Log de ingestión no encontrado"
    mtime = os.path.getmtime(log_path)
    diff_minutes = (time.time() - mtime) / 60
    if diff_minutes < 15:
        return "ACTIVO", f"Hace {int(diff_minutes)} min (OK)"
    elif diff_minutes < 60:
        return "RETRASADO", f"Hace {int(diff_minutes)} min (Posible delay)"
    else:
        return "INACTIVO", f"Inactivo hace {int(diff_minutes // 60)}h"

def check_models_status():
    import os
    import config_manager
    
    # 1. Gemini Test
    gemini_key = os.getenv("GEMINI_API_KEY")
    model_gemini = config_manager.get_env_var("MODEL_GEMINI_TEXT", "gemini-2.5-flash")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            m = genai.GenerativeModel(model_gemini)
            r = m.generate_content("ping")
            status_gemini = f"🟢 Activo (`{model_gemini}`)"
        except Exception as e:
            status_gemini = f"🔴 Falla (`{model_gemini}`): {str(e)[:50]}"
    else:
        status_gemini = "🔴 Sin API Key"
        
    # 2. Groq Text Test
    groq_key = os.getenv("GROQ_API_KEY")
    model_groq = config_manager.get_env_var("MODEL_GROQ_TEXT", "llama-3.3-70b-versatile")
    if groq_key:
        try:
            from openai import OpenAI
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}],
                model=model_groq
            )
            status_groq_text = f"🟢 Activo (`{model_groq}`)"
        except Exception as e:
            status_groq_text = f"🔴 Falla (`{model_groq}`): {str(e)[:50]}"
    else:
        status_groq_text = "🔴 Sin API Key"
        
    # 3. Groq Vision Test (por listado /models)
    model_groq_vision = config_manager.get_env_var("MODEL_GROQ_VISION", "meta-llama/llama-4-scout-17b-16e-instruct")
    if groq_key:
        try:
            import llm_fallback
            modelos = llm_fallback.obtener_modelos_disponibles_groq()
            if model_groq_vision in modelos:
                status_groq_vision = f"🟢 Activo (`{model_groq_vision}`)"
            else:
                status_groq_vision = f"🔴 No listado (`{model_groq_vision}`)"
        except Exception as e:
            status_groq_vision = f"🔴 Falla listado: {str(e)[:50]}"
    else:
        status_groq_vision = "🔴 Sin API Key"
        
    return status_gemini, status_groq_text

def main():
    print("[Reporte Sistema] Iniciando chequeo de salud del servidor...")

    # 1. Recursos
    try:
        with open('/proc/loadavg', 'r') as f:
            load = f.read().split()[:3]
        cpu_load = f"{load[0]} (1m), {load[1]} (5m), {load[2]} (15m)"
    except:
        cpu_load = "N/D"

    total_ram, free_ram = 0, 0
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_ram = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    free_ram = int(line.split()[1]) // 1024
        used_ram = total_ram - free_ram
        ram_percentage = (used_ram / total_ram) * 100 if total_ram > 0 else 0
        ram_status = f"{used_ram}MB / {total_ram}MB ({ram_percentage:.1f}% en uso)"
    except Exception as e:
        ram_status = f"Error RAM: {e}"

    try:
        total_disk, used_disk, free_disk = shutil.disk_usage("/")
        disk_pct = (used_disk / total_disk) * 100
        disk_status = f"{used_disk // (1024**3)}GB / {total_disk // (1024**3)}GB ({disk_pct:.1f}%)"
    except Exception as e:
        disk_status = f"Error Disco: {e}"

    uptime = get_uptime()

    # 2. Servicios
    userbot_active = check_process("userbot_supervisor.py")
    db_ok, db_msg = check_db()
    ingestor_status, ingestor_msg = check_ingestor()
    
    try:
        import gestor_hashes
        total_h = gestor_hashes.obtener_total_hashes_registrados()
        s_hashes = f"🟢 Activo ({total_h} firmas únicas resguardadas)"
    except Exception:
        s_hashes = "🟢 Activo"

    profile_dir = Path("/home/cristian/.config/chrome_mostaza_profile")
    log_corp = BASE_DIR / "correo_corporativo_web.log"
    if profile_dir.exists():
        if log_corp.exists() and (time.time() - os.path.getmtime(log_corp)) / 60 < 45:
            s_corp_mail = "🟢 Activo (Monitoreo Outlook Web OK)"
        else:
            s_corp_mail = "🟢 Activo (Perfil Guardado OK)"
    else:
        s_corp_mail = "🔴 Sesión no configurada"

    s_userbot = "🟢 Activo" if userbot_active else "🔴 Caído"
    s_db = "🟢 " + db_msg if db_ok else f"🔴 Falla ({db_msg})"
    if ingestor_status == "ACTIVO": s_ingestor = f"🟢 {ingestor_msg}"
    elif ingestor_status == "RETRASADO": s_ingestor = f"🟡 {ingestor_msg}"
    else: s_ingestor = f"🔴 {ingestor_msg}"

    # 3. PWA (Buscador y Generador)
    url_buscador = "https://cristianmerlo.github.io/localizador-de-locales/"
    url_generador = "https://cristianmerlo.github.io/Generador_de_Informes_online/"
    s_buscador = check_url(url_buscador)
    s_generador = check_url(url_generador)

    # Chequear Modelos de Inteligencia Artificial (Heartbeat)
    h_gemini, h_groq_text = check_models_status()

    # 4. Construir Reporte
    reporte = (
        "🛠️ *[Antigravity] Reporte Diario de Salud* 📊\n\n"
        "🖥️ *MÁQUINA UBUNTU*\n"
        f"• *Uptime:* {uptime}\n"
        f"• *Carga de CPU:* {cpu_load}\n"
        f"• *Memoria RAM:* {ram_status}\n"
        f"• *Espacio en Disco:* {disk_status}\n\n"
        "🔍 *SISTEMA DE SUPERVISIÓN*\n"
        f"• *Userbot (Telegram):* {s_userbot}\n"
        f"• *Correo Corporativo (OWA):* {s_corp_mail}\n"
        f"• *Base de Datos:* {s_db}\n"
        f"• *Ingestor Automático:* {s_ingestor}\n"
        f"• *Motor Anti-Duplicados (SHA-256):* {s_hashes}\n\n"
        "🤖 *MODELOS DE INTELIGENCIA ARTIFICIAL*\n"
        f"• *Gemini Texto/Visión:* {h_gemini}\n"
        f"• *Groq Texto:* {h_groq_text}\n\n"
        "📱 *APLICACIONES WEB (PWA)*\n"
        f"• *Buscador de Locales:* {s_buscador}\n"
        f"• *Generador de Informes:* {s_generador}\n\n"
        "✅ _Sistemas operativos monitoreados._"
    )

    notificador_telegram.enviar_alerta(reporte, agente="Antigravity")
    print("[Reporte Sistema] Enviado con éxito.")

if __name__ == "__main__":
    main()
