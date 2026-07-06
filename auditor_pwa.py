import os
import sys
import argparse
import re
import json
import gspread
from google.oauth2.service_account import Credentials
import subprocess
import requests

# -- CONFIGURACIÓN --
PROYECTOS_DIR = "/home/cristian/PROYECTOS"
CREDS_JSON = os.path.join(PROYECTOS_DIR, "Supervisor-Project", "credentials.json")
SHEET_URL = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing"

REPO_BUSCADOR = os.path.join(PROYECTOS_DIR, "localizador-de-locales")
FILE_BUSCADOR = os.path.join(REPO_BUSCADOR, "assets", "js", "data.js")

REPO_GENERADOR = os.path.join(PROYECTOS_DIR, "Generador_de_Informes_online")
FILE_GENERADOR = os.path.join(REPO_GENERADOR, "index.html")

ENV_FILE = os.path.join("/home/cristian/Documentos/Supervisor/telegram_bridge/.env")

def get_telegram_config():
    token = None
    chat_id = None
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_TOKEN="):
                    token = line.strip().split("=", 1)[1]
                elif line.startswith("ALLOWED_CHAT_IDS="):
                    chat_id = line.strip().split("=", 1)[1].split(",")[0]
    return token, chat_id


def send_telegram_message(msg):
    try:
        import requests
        url = "http://127.0.0.1:8088/notify"
        requests.post(url, json={"message": msg}, timeout=5)
        print(f"Mensaje enviado a Telegram via Userbot: {msg}")
    except Exception as e:
        print(f"Error enviando mensaje a Userbot local: {e}")


def get_sabana_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDS_JSON, scopes=scopes)
    cliente = gspread.authorize(creds)
    sabana = cliente.open_by_url(SHEET_URL)
    ws = sabana.worksheet("La Sábana - Matriz de Locales V2")
    records = ws.get_all_records()
    return records

def format_data_for_buscador(records):
    locales = []
    for r in records:
        if not r.get('LOCAL') or r.get('LOCAL').strip() == '-': continue
        
        # Mapping spreadsheet columns to localesData JSON
        locales.append({
            "sigla_sistema": str(r.get('SIGLA SISTEMA', '-')),
            "sigla_tickets": str(r.get('SIGLA TICKETS', '-')),
            "regional": str(r.get('REGIONAL', '-')),
            "supervisor": str(r.get('SUPERVISOR', '-')),
            "local": str(r.get('LOCAL', '-')),
            "email": str(r.get('MAIL', '-')),
            "direccion": str(r.get('DIRECCION', '-')),
            "ciudad": str(r.get('LOCALIDAD', '-')),
            "provincia": str(r.get('PROVINCIA', '-')),
            "tipo_local": str(r.get('TIPO DE LOCAL', '-')),
            "razon_social": str(r.get('RAZON SOCIAL', '-')),
            "tecnico": str(r.get('TECNICO ASIGNADO', '-')),
            "email_regional": str(r.get('MAIL REGIONAL', '-')),
            "email_supervisor": str(r.get('MAIL SUPERVISOR', '-'))
        })
    return locales

def format_data_for_generador(records):
    db_locales = []
    # Usar ID_Generador si existe, sino crear consecutivo
    next_id = 1
    for r in records:
        n = str(r.get('LOCAL', '-')).strip()
        if not n or n == '-': continue
        s = str(r.get('SIGLA SISTEMA', '-')).strip()
        t = str(r.get('SIGLA TICKETS', '-')).strip()
        
        id_gen = r.get('ID_Generador', '')
        if id_gen:
            try:
                id_val = int(id_gen)
                next_id = max(next_id, id_val + 1)
            except:
                id_val = next_id
                next_id += 1
        else:
            id_val = next_id
            next_id += 1
            
        db_locales.append({"n": n, "s": s, "t": t, "id": id_val})
    return db_locales

def analyze_buscador(expected_data):
    try:
        with open(FILE_BUSCADOR, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const localesData = (\[.*?\]);', content, re.DOTALL)
        if match:
            actual_data = json.loads(match.group(1))
            return len(actual_data) == len(expected_data)
        return False
    except Exception as e:
        print(f"Error analizando buscador: {e}")
        return False

def analyze_generador(expected_data):
    try:
        with open(FILE_GENERADOR, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const DB_LOCALES\s*=\s*\[(.*?)\];', content, re.DOTALL)
        if not match: return False
        
        locales_text = match.group(1)
        pattern = r'{\s*n:\s*"([^"]+)",\s*s:\s*"([^"]+)",\s*t:\s*"([^"]+)",\s*id:\s*(\d+)\s*}'
        actual_data = []
        for m in re.finditer(pattern, locales_text):
            n, s, t, id_val = m.groups()
            actual_data.append({"n": n, "s": s, "t": t, "id": int(id_val)})
            
        return len(actual_data) == len(expected_data)
    except Exception as e:
        print(f"Error analizando generador: {e}")
        return False

def apply_buscador(expected_data):
    with open(FILE_BUSCADOR, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_json = json.dumps(expected_data, indent=4, ensure_ascii=False)
    new_content = re.sub(r'const localesData = \[.*?\];', f'const localesData = {new_json};', content, flags=re.DOTALL)
    
    with open(FILE_BUSCADOR, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Buscador actualizado localmente.")
    commit_and_push(REPO_BUSCADOR)

def apply_generador(expected_data):
    with open(FILE_GENERADOR, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Formatear el array de JS
    js_array_inner = ", ".join([f'{{ n: "{d["n"]}", s: "{d["s"]}", t: "{d["t"]}", id: {d["id"]} }}' for d in expected_data])
    new_block = f'const DB_LOCALES = [\n        {js_array_inner}\n    ];'
    
    new_content = re.sub(r'const DB_LOCALES\s*=\s*\[.*?\];', new_block, content, flags=re.DOTALL)
    
    with open(FILE_GENERADOR, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Generador actualizado localmente.")
    commit_and_push(REPO_GENERADOR)

def commit_and_push(repo_path):
    try:
        # Check if there are changes
        status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo_path).decode('utf-8').strip()
        if not status:
            print(f"No hay cambios para subir en {repo_path}")
            return
            
        subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Sincronización automática de locales desde La Sábana'], cwd=repo_path, check=True)
        subprocess.run(['git', 'push', 'origin', 'HEAD'], cwd=repo_path, check=True)
        print(f"Cambios subidos a GitHub para {repo_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error en Git para {repo_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Auditor y Sincronizador de PWA")
    parser.add_argument('--check', action='store_true', help='Verifica sincronización y reporta')
    parser.add_argument('--apply', action='store_true', help='Aplica cambios y sube a GitHub')
    args = parser.parse_args()

    if not args.check and not args.apply:
        print("Uso: python3 auditor_pwa.py --check | --apply")
        sys.exit(1)

    print("Obteniendo datos de La Sábana...")
    records = get_sabana_data()
    
    data_buscador = format_data_for_buscador(records)
    data_generador = format_data_for_generador(records)

    if args.check:
        b_sync = analyze_buscador(data_buscador)
        g_sync = analyze_generador(data_generador)
        
        if b_sync and g_sync:
            msg = "✅ <b>Auditoría Semanal</b>\n\nTodas las plataformas PWA (Buscador y Generador) se encuentran sincronizadas con <i>La Sábana</i>."
        else:
            msg = f"⚠️ <b>Alerta de Sincronización</b>\n\nSe encontraron discrepancias de locales/personal entre La Sábana y las plataformas PWA.\nBuscador: {'Sincronizado' if b_sync else 'Desactualizado'}\nGenerador: {'Sincronizado' if g_sync else 'Desactualizado'}\n\nAvisá a Antigravity para aplicar los cambios a producción."
        
        send_telegram_message(msg)

    elif args.apply:
        print("Aplicando cambios al Buscador...")
        apply_buscador(data_buscador)
        
        print("Aplicando cambios al Generador...")
        apply_generador(data_generador)
        
        send_telegram_message("🚀 <b>Despliegue Exitoso</b>\n\nSe aplicaron los cambios de La Sábana y se subieron a GitHub para el Buscador y Generador.")

if __name__ == "__main__":
    main()
