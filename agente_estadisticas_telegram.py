import os
import sys
import json
import datetime
from collections import Counter
from pathlib import Path

BASE_DIR = Path("/home/cristian/PROYECTOS/Supervisor-Project")
sys.path.append(str(BASE_DIR))
import notificador_telegram

TICKETS_FILE = BASE_DIR / "brain" / "tickets_activos.json"

def enviar_reporte_diario():
    if not TICKETS_FILE.exists():
        print("[-] El archivo de tickets activos no existe. Ejecuta el motor primero.")
        return

    with open(TICKETS_FILE, "r") as f:
        tickets = json.load(f)

    if not tickets:
        notificador_telegram.enviar_alerta("📊 *Reporte de Tickets*\n\n¡Excelentes noticias! Actualmente no hay tickets abiertos para nuestros locales.", agente="Analista")
        return

    # Cálculos Estadísticos Básicos
    total_abiertos = len(tickets)
    
    # Prioridades
    urgentes = sum(1 for t in tickets if t.get("priority", "").upper() in ["ALTA", "URGENTE", "EMERGENCIA"])
    
    # Locales con más tickets
    locales_counter = Counter(t.get("store", "Desconocido") for t in tickets)
    top_locales = locales_counter.most_common(3)
    
    # Categorías más comunes
    cat_counter = Counter(t.get("category", "Otra") for t in tickets)
    top_cat = cat_counter.most_common(2)

    # Formateo del mensaje
    mensaje = (
        f"📊 *REPORTE DIARIO DE TICKETS (Looker Studio)*\n\n"
        f"📈 *Total de Tickets Abiertos:* {total_abiertos}\n"
        f"🔴 *Tickets Urgentes/Alta:* {urgentes}\n\n"
        f"🏆 *Top Locales Críticos:*\n"
    )
    
    for loc, count in top_locales:
        mensaje += f"   • {loc}: {count} tickets\n"
        
    mensaje += f"\n📂 *Categorías más recurrentes:*\n"
    for cat, count in top_cat:
        mensaje += f"   • {cat}: {count} tickets\n"
        
    mensaje += f"\n🔗 Consulta los gráficos en tiempo real en tu panel de Google Looker Studio."

    print("[*] Enviando reporte estadístico por Telegram...")
    notificador_telegram.enviar_alerta(mensaje, agente="Analista")
    print("[+] Enviado con éxito.")

if __name__ == "__main__":
    enviar_reporte_diario()
