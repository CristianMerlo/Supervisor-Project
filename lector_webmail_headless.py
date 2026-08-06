#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: lector_webmail_headless.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Monitorea la bandeja de entrada de Outlook Web (outlook.office365.com) utilizando
un perfil de usuario persistente de Google Chrome sin requerir APIs ni desencadenar
alertas de consentimiento de administradores de Azure AD.
Aplica reglas anti-spam de filtro_correos.json y envía alertas por Telegram.
"""

import os
import sys
import json
import time
import sqlite3
import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

import notificador_telegram
import llm_fallback

# Cargar variables de entorno
load_dotenv(str(BASE_DIR / ".env"))

PROFILE_DIR = Path("/home/cristian/.config/chrome_mostaza_profile")
FILTRO_FILE = BASE_DIR / "filtro_correos.json"
DB_PATH = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")
OUTLOOK_URL = "https://outlook.office365.com/mail/inbox"

def obtener_conexion_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS correos_corporativos (
            id TEXT PRIMARY KEY,
            remitente TEXT,
            asunto TEXT,
            fecha TEXT,
            cuerpo TEXT,
            sigla_local TEXT,
            resumen TEXT
        );
    """)
    conn.commit()
    return conn

def cargar_filtros():
    if FILTRO_FILE.exists():
        try:
            with open(FILTRO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "whitelist_dominios": ["mostazaweb.com.ar"],
        "keywords_asunto_prioritario": ["mantenimiento", "presupuesto", "service", "urgente", "factura"],
        "blacklist_remitentes": ["noreply", "no-reply", "notifications"],
        "blacklist_asuntos": ["automatic reply", "fuera de la oficina"]
    }

def modo_login():
    """Abre la ventana interactiva de Chrome para que Cristian inicie sesión 1 sola vez."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print("\n==================================================================")
    print("🌐 INICIANDO NAVEGADOR PARA INICIO DE SESIÓN DE OUTLOOK WEB")
    print("1. Se abrirá la ventana oficial de Google Chrome.")
    print("2. Inicia sesión con tu cuenta cmerlo@mostazaweb.com.ar y aprueba tu MFA.")
    print("3. Cuando veas la bandeja de entrada, regresa aquí y presiona Enter.")
    print("==================================================================\n")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = context.new_page()
        page.goto(OUTLOOK_URL)
        
        input(">>> Presiona Enter una vez que hayas iniciado sesión y veas la bandeja de entrada... ")
        print("✅ Sesión guardada en el perfil local exitosamente.")
        context.close()

def es_correo_relevante(remitente, asunto, cuerpo, filtros):
    remitente_lower = remitente.lower()
    asunto_lower = asunto.lower()
    
    for bl_rem in filtros.get("blacklist_remitentes", []):
        if bl_rem.lower() in remitente_lower:
            return False, "Blacklist Remitente"
            
    for bl_asu in filtros.get("blacklist_asuntos", []):
        if bl_asu.lower() in asunto_lower:
            return False, "Blacklist Asunto"
            
    es_whitelist = any(wl.lower() in remitente_lower for wl in filtros.get("whitelist_dominios", []))
    es_keyword = any(kw.lower() in asunto_lower or kw.lower() in cuerpo.lower()[:300] for kw in filtros.get("keywords_asunto_prioritario", []))
    
    if es_whitelist or es_keyword:
        return True, "Aprobado por Criterio"
        
    if "@" in remitente and not any(x in remitente_lower for x in ["no-reply", "noreply", "info@"]):
        return True, "Remitente Humano Directo"
        
    return False, "Secundario / Sin coincidencia"

def procesar_webmail_headless():
    """Ejecución periódica invisible en segundo plano."""
    if not PROFILE_DIR.exists():
        print("⚠️ El perfil de Chrome no existe. Ejecuta primero: python3 lector_webmail_headless.py --login")
        return
        
    filtros = cargar_filtros()
    conn = obtener_conexion_db()
    c = conn.cursor()
    
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Escaneando Outlook Webmail (Headless)...")
    
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="chrome",
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = context.new_page()
            page.goto(OUTLOOK_URL, wait_until="networkidle", timeout=30000)
            time.sleep(4)
            
            # Extraer textos de la bandeja de entrada
            # Buscar elementos de lista de correo en Outlook Web
            mail_items = page.query_selector_all("div[role='option'], div[data-convid], div[aria-label*='no leído'], div[aria-label*='Unread']")
            
            if not mail_items:
                # Intento secundario selector genérico de filas de lista de Outlook
                mail_items = page.query_selector_all("div[aria-label*='de:']") or page.query_selector_all("div[aria-label*='From:']")
                
            print(f"Items detectados en pantalla: {len(mail_items)}")
            
            procesados_count = 0
            for item in mail_items[:10]:
                aria_label = item.get_attribute("aria-label") or ""
                item_text = item.inner_text() or ""
                
                # Generar ID sintético de conversación/mail a partir del texto e ID de Outlook
                import hashlib
                raw_id = (aria_label + item_text[:100]).strip()
                if not raw_id:
                    continue
                msg_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()
                
                # Verificar en DB si ya fue notificado
                c.execute("SELECT id FROM correos_corporativos WHERE id = ?", (msg_id,))
                if c.fetchone():
                    continue
                    
                lines = [l.strip() for l in item_text.split("\n") if l.strip()]
                remitente = lines[0] if lines else "Remitente Desconocido"
                asunto = lines[1] if len(lines) > 1 else "Sin Asunto"
                cuerpo_preview = " ".join(lines[2:]) if len(lines) > 2 else item_text[:300]
                
                relevante, razon = es_correo_relevante(remitente, asunto, cuerpo_preview, filtros)
                if not relevante:
                    print(f"  [OMITIDO-FILTRO] De: {remitente[:20]} | Asunto: {asunto[:30]} | Razón: {razon}")
                    # Registrar descarte para no reevaluar
                    c.execute("INSERT OR IGNORE INTO correos_corporativos (id, remitente, asunto, fecha, cuerpo, sigla_local, resumen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (msg_id, remitente, asunto, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cuerpo_preview[:300], "DESCONOCIDO", "DESCARTE_FILTRO"))
                    conn.commit()
                    continue
                    
                print(f"  [NUEVO RELEVANTE] De: {remitente} | Asunto: {asunto}")
                
                # Gemini 2.5 Flash Resumen
                prompt = f"""Analiza el siguiente correo corporativo recibido:
Remitente: {remitente}
Asunto: {asunto}
Previsualización del mensaje:
{cuerpo_preview}

Escribe un resumen breve y ejecutivo de 2 oraciones en español indicando el tema principal y si requiere alguna acción."""
                
                resumen = llm_fallback.generar_texto(prompt) or "Resumen no disponible."
                
                # Guardar en SQLite
                fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT OR IGNORE INTO correos_corporativos (id, remitente, asunto, fecha, cuerpo, sigla_local, resumen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (msg_id, remitente, asunto, fecha_actual, cuerpo_preview, "CORPORATIVO", resumen))
                conn.commit()
                
                # Descargar adjuntos PDF hacia la carpeta /entrantes para la ingesta automática
                try:
                    dir_entrantes = Path("/home/cristian/Documentos/Supervisor/entrantes")
                    dir_entrantes.mkdir(parents=True, exist_ok=True)
                    
                    # Si el correo indica adjuntos PDF o la palabra PDF / informe
                    if "pdf" in item_text.lower() or "adjunto" in item_text.lower() or "informe" in item_text.lower():
                        item.click()
                        time.sleep(2)
                        
                        # Buscar botones o links de descarga de archivos PDF en el panel de lectura
                        pdf_links = page.query_selector_all("a[href*='.pdf'], button[aria-label*='.pdf'], div[aria-label*='.pdf']")
                        for pdf_btn in pdf_links:
                            with page.expect_download(timeout=5000) as download_info:
                                pdf_btn.click()
                            download = download_info.value
                            dest_path = dir_entrantes / download.suggested_filename
                            download.save_as(str(dest_path))
                            print(f"📥 [PDF DEPOSITADO EN ENTRANTES] {download.suggested_filename} desde Correo Corporativo.")
                except Exception as e_pdf:
                    # Ignorar si no había descarga directa o falló el click
                    pass
                
                # Evaluar si corresponde al circuito de Seguimiento de Repuestos
                try:
                    import gestor_pedidos_repuestos
                    gestor_pedidos_repuestos.procesar_correo_repuesto(remitente, asunto, cuerpo_preview, fecha_actual)
                except Exception as e_rep:
                    print(f"Error evaluando repuestos: {e_rep}")
                
                # Notificar Telegram
                msg_tg = (
                    "📧 *[Correo Corporativo] NUEVO MAIL RECIBIDO*\n"
                    f"👤 *De:* {remitente}\n"
                    f"📌 *Asunto:* {asunto}\n\n"
                    f"🤖 *Resumen Gemini:* _{resumen.strip()}_"
                )
                notificador_telegram.enviar_alerta(msg_tg, agente="Antigravity", destinatario_id=215173956)
                procesados_count += 1
                
            print(f"Finalizado chequeo webmail. Procesados y notificados: {procesados_count}")
            context.close()
        except Exception as e:
            print(f"Error procesando webmail headless: {e}")
            
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--login":
        modo_login()
    else:
        procesar_webmail_headless()
