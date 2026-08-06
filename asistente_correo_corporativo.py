#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: asistente_correo_corporativo.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Asistente autónomo exclusivo para la cuenta cmerlo@mostazaweb.com.ar.
Utiliza Microsoft Graph API con autenticación OAuth2 (Device Code Flow).
Aplica las reglas de filtrado anti-spam de filtro_correos.json, procesa
los correos relevantes con Gemini 2.5 Flash y envía alertas ejecutivas a Telegram.
"""

import os
import sys
import json
import time
import sqlite3
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

import notificador_telegram
import llm_fallback

# Cargar .env
load_dotenv(str(BASE_DIR / ".env"))

CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46" # Microsoft CLI Public App ID
SCOPES = "https://graph.microsoft.com/Mail.ReadWrite offline_access"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

TOKEN_FILE = Path("/home/cristian/Documentos/Supervisor/ms_token.json")
FILTRO_FILE = BASE_DIR / "filtro_correos.json"
DB_PATH = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")

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

def iniciar_autenticacion_device_flow():
    """Inicia el flujo Device Code de Microsoft OAuth2."""
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
    data = {"client_id": CLIENT_ID, "scope": SCOPES}
    r = requests.post(url, data=data)
    if r.status_code != 200:
        print(f"Error iniciando Device Code: {r.text}")
        return None
        
    res = r.json()
    user_code = res.get("user_code")
    device_code = res.get("device_code")
    verification_uri = res.get("verification_uri", "https://login.microsoft.com/device")
    interval = res.get("interval", 5)
    expires_in = res.get("expires_in", 900)
    
    print("\n==================================================================")
    print("🔑 AUTENTICACIÓN REQUERIDA PARA TU CORREO CORPORATIVO")
    print(f"1. Abre en tu navegador (celular o PC): {verification_uri}")
    print(f"2. Ingresa el código de 9 letras:  >>> {user_code} <<<")
    print("3. Inicia sesión con cmerlo@mostazaweb.com.ar y aprueba el acceso.")
    print("==================================================================\n")
    
    # Notificar también por Telegram con el código
    msg_tg = (
        "🔐 *[Antigravity] Inicio de Sesión Correo Corporativo*\n\n"
        f"Por favor abre en tu navegador: {verification_uri}\n"
        f"E ingresa el código: `{user_code}`\n\n"
        "_Este proceso se realiza una sola vez para guardar la clave segura de Microsoft._"
    )
    notificador_telegram.enviar_alerta(msg_tg, agente="Antigravity")
    
    # Polling del token
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    start_time = time.time()
    
    while time.time() - start_time < expires_in:
        time.sleep(interval)
        token_data = {
            "client_id": CLIENT_ID,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code
        }
        res_t = requests.post(token_url, data=token_data)
        if res_t.status_code == 200:
            token_json = res_t.json()
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(token_json, f, indent=2)
            print("✅ Token de Microsoft Graph obtenido y guardado exitosamente!")
            return token_json
            
        err = res_t.json().get("error")
        if err == "authorization_pending":
            continue
        else:
            print(f"Error en polling de token: {err}")
            break
            
    return None

def obtener_access_token():
    """Obtiene un access token válido usando el refresh_token guardado."""
    if not TOKEN_FILE.exists():
        return None
        
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            tokens = json.load(f)
            
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            return None
            
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPES
        }
        r = requests.post(token_url, data=data)
        if r.status_code == 200:
            new_tokens = r.json()
            # Preservar el refresh token si no vino uno nuevo
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = refresh_token
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(new_tokens, f, indent=2)
            return new_tokens.get("access_token")
    except Exception as e:
        print(f"Error refrescando token de Microsoft: {e}")
        
    return None

def es_correo_relevante(remitente, asunto, cuerpo, filtros):
    remitente_lower = remitente.lower()
    asunto_lower = asunto.lower()
    
    # 1. Comprobar Blacklist de remitentes
    for bl_rem in filtros.get("blacklist_remitentes", []):
        if bl_rem.lower() in remitente_lower:
            return False, "Blacklist Remitente"
            
    # 2. Comprobar Blacklist de asuntos
    for bl_asu in filtros.get("blacklist_asuntos", []):
        if bl_asu.lower() in asunto_lower:
            return False, "Blacklist Asunto"
            
    # 3. Comprobar Whitelist de dominios
    es_whitelist = False
    for wl_dom in filtros.get("whitelist_dominios", []):
        if wl_dom.lower() in remitente_lower:
            es_whitelist = True
            break
            
    # 4. Comprobar Palabras Clave en Asunto/Cuerpo
    es_keyword = False
    for kw in filtros.get("keywords_asunto_prioritario", []):
        if kw.lower() in asunto_lower or kw.lower() in cuerpo.lower()[:300]:
            es_keyword = True
            break
            
    if es_whitelist or es_keyword:
        return True, "Aprobado por Filtro"
        
    # Por defecto, si viene de una persona directa sin estar en blacklist, procesar
    if "@" in remitente and not any(x in remitente_lower for x in ["no-reply", "noreply", "info@"]):
        return True, "Remitente Humano Directo"
        
    return False, "No coincide con criterios prioritarios"

def procesar_correos_corporativos():
    access_token = obtener_access_token()
    if not access_token:
        print("⚠️ No hay token de Microsoft activo. Se requiere iniciar sesión.")
        return
        
    filtros = cargar_filtros()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Obtener correos no leídos
    endpoint = f"{GRAPH_URL}/me/mailFolders/inbox/messages?$filter=isRead eq false&$top=10"
    r = requests.get(endpoint, headers=headers)
    
    if r.status_code != 200:
        print(f"Error consultando Microsoft Graph: {r.status_code} - {r.text}")
        return
        
    mensajes = r.json().get("value", [])
    if not mensajes:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Correo Corporativo: No hay mensajes nuevos no leídos.")
        return
        
    conn = obtener_conexion_db()
    c = conn.cursor()
    
    for msg in mensajes:
        msg_id = msg.get("id")
        asunto = msg.get("subject", "Sin Asunto")
        from_dict = msg.get("from", {}).get("emailAddress", {})
        remitente_nombre = from_dict.get("name", "")
        remitente_email = from_dict.get("address", "")
        remitente_str = f"{remitente_nombre} <{remitente_email}>".strip()
        fecha_str = msg.get("receivedDateTime", "")
        cuerpo = msg.get("bodyPreview", "") or msg.get("body", {}).get("content", "")
        
        # Verificar en DB si ya fue procesado
        c.execute("SELECT id FROM correos_corporativos WHERE id = ?", (msg_id,))
        if c.fetchone():
            continue
            
        relevante, razon = es_correo_relevante(remitente_str, asunto, cuerpo, filtros)
        if not relevante:
            print(f"[FILTRADO-DESCARTE] Mail de '{remitente_email}' | Asunto: '{asunto}' | Razón: {razon}")
            # Marcar como leído silenciosamente para no atascar la bandeja
            requests.patch(f"{GRAPH_URL}/me/messages/{msg_id}", headers=headers, json={"isRead": True})
            continue
            
        print(f"[PROCESANDO] Mail Corporativo Relevante: '{asunto}' de '{remitente_str}'")
        
        # Resumen por Gemini 2.5 Flash
        prompt = f"""Analiza el siguiente correo corporativo recibido por el Supervisor de Mantenimiento:
Remitente: {remitente_str}
Asunto: {asunto}
Cuerpo:
{cuerpo[:2000]}

Genera un resumen profesional y conciso de 2 oraciones en español destacando las acciones, presupuestos o requerimientos planteados."""
        
        resumen = llm_fallback.generar_texto(prompt) or "Sin resumen disponible."
        
        # Guardar en SQLite
        c.execute("""
            INSERT OR IGNORE INTO correos_corporativos (id, remitente, asunto, fecha, cuerpo, sigla_local, resumen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, remitente_str, asunto, fecha_str, cuerpo[:1000], "CORPORATIVO", resumen))
        conn.commit()
        
        # Enviar Alerta por Telegram
        mensaje_tg = (
            "📧 *[Correo Corporativo] NUEVO MAIL RECIBIDO*\n"
            f"👤 *De:* {remitente_str}\n"
            f"📌 *Asunto:* {asunto}\n\n"
            f"🤖 *Resumen Gemini:* _{resumen.strip()}_"
        )
        notificador_telegram.enviar_alerta(mensaje_tg, agente="Antigravity", destinatario_id=215173956)
        
        # Marcar como leído en Microsoft 365
        requests.patch(f"{GRAPH_URL}/me/messages/{msg_id}", headers=headers, json={"isRead": True})
        
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        iniciar_autenticacion_device_flow()
    else:
        procesar_correos_corporativos()
