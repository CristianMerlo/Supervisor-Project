import os
import sys
import time
import json
import requests
import datetime
from pathlib import Path

BASE_DIR = Path("/home/cristian/PROYECTOS/Supervisor-Project")
sys.path.append(str(BASE_DIR))
import notificador_telegram

# URLs extraidas autónomamente
URL_LOGIN = "https://opgroup.linkuperp.com/apiv2/Oauth/token"
URL_TICKETS_FRANQUICIAS = "https://opgroup.linkuperp.com/apiv2/tickets/channel/2"

# Credenciales de API extraidas del código fuente js/app.js
API_CLIENT_ID = "4"
API_CLIENT_SECRET = "lXsUsNd9NXldzNENiUTNC2uLSQMhc3kI4CjhimJn"

USERNAME = os.getenv("MOSTAZA_USER", "cmerlo@mostazaweb.com.ar")
PASSWORD = os.getenv("MOSTAZA_PASS", "Mante2026")

STATE_FILE = BASE_DIR / "brain" / "tickets_vistos.json"
DB_PATH = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")

def cargar_vistos():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def guardar_vistos(vistos):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(vistos, f)
    except Exception as e:
        print(f"Error guardando estado de tickets: {e}")

def obtener_locales_conocidos():
    """Lee el CSV de locales y retorna un set con las siglas (ej: 'FSAL4') de los locales conocidos."""
    conocidos = set()
    CSV_PATH = BASE_DIR / "locales.csv"
    if not CSV_PATH.exists():
        print(f"[!] CSV no encontrado en {CSV_PATH}")
        return conocidos
        
    try:
        import csv
        with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                sigla = row.get("SIGLA TICKETS", "").strip().upper()
                if sigla:
                    conocidos.add(sigla)
    except Exception as e:
        print(f"Error leyendo CSV de locales: {e}")
    return conocidos

def obtener_nombre_local_por_sigla(sigla):
    """Resuelve la sigla del local a su nombre comercial completo usando locales.csv"""
    CSV_PATH = Path("/home/cristian/PROYECTOS/Supervisor-Project/locales.csv")
    if not CSV_PATH.exists():
        return ""
    try:
        import csv
        with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                sigla_tickets = row.get("SIGLA TICKETS", "").strip().upper()
                sigla_sistema = row.get("SIGLA SISTEMA", "").strip().upper()
                if sigla.upper() in [sigla_tickets, sigla_sistema]:
                    return row.get("LOCAL", "").strip()
    except Exception as e:
        print(f"Error resolviendo nombre de local: {e}")
    return ""

def autenticar():
    """Realiza el login contra la API de Mostaza y retorna el token JWT"""
    payload = {
        "grant_type": "password",
        "client_id": API_CLIENT_ID,
        "client_secret": API_CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "device_os": "android",
        "app_version": "7.0.5"
    }
    
    print("[*] Autenticando en Linkup ERP (Mostaza)...")
    try:
        res = requests.post(URL_LOGIN, json=payload, timeout=15)
        res.raise_for_status()
        return res.json().get("access_token")
    except Exception as e:
        print(f"[-] Error en autenticación: {e}")
        return None

def procesar_tickets():
    locales_conocidos = obtener_locales_conocidos()
    if not locales_conocidos:
        print("[!] Advertencia: No se cargaron locales conocidos de la base de datos. Se alertará sobre todos los de la sábana encontrada.")
        
    token = autenticar()
    if not token:
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    
    print("[*] Obteniendo listado de tickets de Franquicias...")
    try:
        res = requests.get(URL_TICKETS_FRANQUICIAS, headers=headers, timeout=20)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"[-] Error obteniendo tickets: {e}")
        return
        
    tickets = data.get("data", {}).get("tickets", [])
    print(f"[+] Se obtuvieron {len(tickets)} tickets activos del servidor.")
    
    vistos = cargar_vistos()
    nuevos_vistos = list(vistos)
    alertas_enviadas = 0
    
    for ticket in tickets:
        t_id = ticket.get("id")
        t_store = ticket.get("store", "").strip().upper()
        
        # Filtro: ¿Es un local que nos importa?
        if t_store not in locales_conocidos:
            # Si no está en locales_conocidos, lo ignoramos para no generar ruido
            continue
            
        # Filtro: Descartar "Lista de mantenimiento"
        if ticket.get("category", "").strip().upper() == "LISTA DE MANTENIMIENTO" or "LISTA DE MANTENIMIENTO" in ticket.get("incidence_breadcrumb", "").upper():
            continue
            
        if t_id not in vistos:
            # Ticket Nuevo de un local nuestro!
            t_title = ticket.get("title") or "Sin título"
            t_desc = ticket.get("description") or "Sin descripción"
            t_priority = ticket.get("priority") or "Normal"
            t_incidence = ticket.get("incidence") or "General"
            
            t_date = ticket.get("date")
            t_time = ticket.get("time") or "--:--"
            if t_date:
                try:
                    fecha_str = datetime.datetime.fromtimestamp(t_date).strftime('%d/%m/%Y')
                except Exception:
                    fecha_str = "Desconocida"
            else:
                fecha_str = "Desconocida"
            
            # Formatear el mensaje
            prioridad_icon = "🔴 EMERGENCIA" if t_priority.lower() in ["alta", "urgente", "emergencia"] else "🟡"
            
            nombre_local = obtener_nombre_local_por_sigla(t_store)
            store_display = f"{t_store} - {nombre_local}" if nombre_local else t_store
            
            mensaje = (
                f"🎫 *NUEVO TICKET DETECTADO (# {t_id})*\n"
                f"🏪 *Local:* {store_display}\n"
                f"🕒 *Fecha/Hora:* {fecha_str} a las {t_time}\n"
                f"⚠️ *Prioridad:* {prioridad_icon} ({t_priority})\n"
                f"🛠 *Incidencia:* {t_incidence}\n"
                f"📌 *Detalle:* {t_title}\n\n"
                f"_{t_desc[:150]}..._"
            )
            
            print(f"[+] Alertando sobre ticket {t_id} del local {t_store}")
            # ID del Grupo Mantenimiento Franquicias
            grupo_id = -5223900821
            exito = notificador_telegram.enviar_alerta(mensaje, agente="Hermes", destinatario_id=grupo_id)
            
            if exito:
                nuevos_vistos.append(t_id)
                alertas_enviadas += 1
                time.sleep(1) # Pequeña pausa para no saturar Telegram
                
    # Guardar estado de alertas
    if alertas_enviadas > 0:
        # Mantener solo los últimos 5000 tickets en el historial para evitar archivo gigante
        guardar_vistos(nuevos_vistos[-5000:])
        print(f"[+] Ciclo finalizado. Se enviaron {alertas_enviadas} alertas.")
    else:
        print("[*] Ciclo finalizado. No hay tickets nuevos para nuestros locales.")
        
    # [NUEVO] Guardar la foto en tiempo real de todos los tickets filtrados para el Dashboard
    tickets_activos = [t for t in tickets if t.get("store", "").strip().upper() in locales_conocidos and not (t.get("category", "").strip().upper() == "LISTA DE MANTENIMIENTO" or "LISTA DE MANTENIMIENTO" in t.get("incidence_breadcrumb", "").upper())]
    try:
        ruta_activos = BASE_DIR / "brain" / "tickets_activos.json"
        with open(ruta_activos, "w") as f:
            json.dump(tickets_activos, f, indent=2)
        print(f"[+] Snapshot de {len(tickets_activos)} tickets guardado en {ruta_activos} para el Dashboard.")
    except Exception as e:
        print(f"[-] Error guardando snapshot: {e}")

if __name__ == "__main__":
    print(f"=== Iniciando Motor de Tickets Mostaza ({datetime.datetime.now()}) ===")
    
    # Si se ejecuta con flag --daemon, corre en bucle infinito
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        print("[*] Modo Demonio activado. Consultando cada 5 minutos.")
        while True:
            procesar_tickets()
            time.sleep(300)
    else:
        procesar_tickets()
