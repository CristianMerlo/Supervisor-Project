#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: gestor_pedidos_repuestos.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Motor de seguimiento del ciclo de vida de pedidos de repuestos en 5 etapas:
1. SOLICITADO
2. PRESUPUESTADO
3. APROBADO
4. LISTO EN DEPÓSITO (Alerta prioritaria a Cristian por Telegram)
5. INSTALADO / CONCLUIDO

Administra la base SQLite pedidos_repuestos.db.
"""

import os
import sys
import re
import json
import sqlite3
import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

import notificador_telegram
import llm_fallback

DB_PATH = Path("/home/cristian/Documentos/Supervisor/pedidos_repuestos.db")

ETAPAS = {
    1: "🟡 SOLICITADO",
    2: "🟠 PRESUPUESTADO",
    3: "🔵 APROBADO",
    4: "🟢 LISTO EN DEPÓSITO",
    5: "✅ INSTALADO"
}

def obtener_conexion():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos_repuestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sigla_local TEXT,
            equipo_repuesto TEXT,
            hilo_asunto TEXT,
            etapa_actual INTEGER,
            fecha_solicitud TEXT,
            fecha_presupuesto TEXT,
            fecha_aprobacion TEXT,
            fecha_deposito TEXT,
            fecha_instalado TEXT,
            ultimo_remitente TEXT,
            detalles JSON
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_trazabilidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER,
            fecha TEXT,
            remitente TEXT,
            asunto TEXT,
            etapa_detectada INTEGER,
            resumen_ia TEXT,
            FOREIGN KEY (id_pedido) REFERENCES pedidos_repuestos (id)
        );
    """)
    conn.commit()
    return conn

def extraer_sigla(texto):
    """Extrae siglas de locales (ej: [FURQ], FURQ, Urquiza)."""
    m = re.search(r'\[?([A-Z]{3,5})\]?', texto.upper())
    if m:
        sigla = m.group(1)
        if len(sigla) in [3, 4, 5]:
            return sigla
    return "GENERAL"

def detectar_etapa_con_ia(asunto, cuerpo, remitente):
    """Analiza con Gemini 2.5 Flash qué etapa del circuito alcanzó el correo."""
    prompt = f"""Analiza la siguiente comunicación sobre un pedido de repuestos de mantenimiento:
Remitente: {remitente}
Asunto: {asunto}
Mensaje:
{cuerpo[:1500]}

Determina a qué ETAPA del circuito de repuestos corresponde este correo:
Etapa 1: SOLICITADO (Técnico o local pide un repuesto o cotización).
Etapa 2: PRESUPUESTADO (Se envía el presupuesto, monto o cotización PDF).
Etapa 3: APROBADO (Se aprueba la compra u orden por parte de operaciones/regional).
Etapa 4: LISTO_EN_DEPOSITO (Depósito confirma que el repuesto ya se puede pasar a retirar).
Etapa 5: INSTALADO (Se confirma que el repuesto fue colocado/instalado).
Etapa 0: NO_APLICA (No es una novedad de repuestos).

Responde EXACTAMENTE en una sola línea con este formato JSON:
{{"etapa": 1|2|3|4|5|0, "repuesto": "Nombre breve del equipo/repuesto", "sigla": "SIGLA_LOCAL o GENERAL"}}"""

    res_text = llm_fallback.generar_texto(prompt)
    try:
        if "```" in res_text:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", res_text, re.DOTALL)
            if m:
                res_text = m.group(1)
        res = json.loads(res_text.strip())
        return res.get("etapa", 0), res.get("repuesto", "Repuesto General"), res.get("sigla", "GENERAL")
    except Exception:
        return 0, "Repuesto General", "GENERAL"

def procesar_correo_repuesto(remitente, asunto, cuerpo, fecha_str=None):
    """Procesa un mail entrante y actualiza la trazabilidad del pedido en la BD."""
    etapa, repuesto, sigla = detectar_etapa_con_ia(asunto, cuerpo, remitente)
    if etapa == 0:
        return False, "No corresponde a circuito de repuestos."
        
    fecha_now = fecha_str or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = obtener_conexion()
    c = conn.cursor()
    
    # Buscar si ya existe un pedido en curso para este local y repuesto/asunto
    hilo_clean = re.sub(r'^(RE|FWD|RV|FW):\s*', '', asunto, flags=re.IGNORECASE).strip()
    
    c.execute("""
        SELECT id, etapa_actual, detalles FROM pedidos_repuestos 
        WHERE (sigla_local = ? OR sigla_local = 'GENERAL') 
          AND (hilo_asunto LIKE ? OR equipo_repuesto LIKE ?)
          AND etapa_actual < 5
        ORDER BY id DESC LIMIT 1
    """, (sigla, f"%{hilo_clean[:20]}%", f"%{repuesto[:15]}%"))
    
    row = c.fetchone()
    
    if row:
        pedido_id = row["id"]
        etapa_anterior = row["etapa_actual"]
        nueva_etapa = max(etapa_anterior, etapa)
        
        # Actualizar fecha correspondiente según la etapa alcanzada
        col_fecha = ""
        if etapa == 2: col_fecha = "fecha_presupuesto = ?"
        elif etapa == 3: col_fecha = "fecha_aprobacion = ?"
        elif etapa == 4: col_fecha = "fecha_deposito = ?"
        elif etapa == 5: col_fecha = "fecha_instalado = ?"
        
        if col_fecha:
            c.execute(f"UPDATE pedidos_repuestos SET etapa_actual = ?, ultimo_remitente = ?, {col_fecha} WHERE id = ?", (nueva_etapa, remitente, fecha_now, pedido_id))
        else:
            c.execute("UPDATE pedidos_repuestos SET etapa_actual = ?, ultimo_remitente = ? WHERE id = ?", (nueva_etapa, remitente, pedido_id))
            
    else:
        # Crear nuevo pedido
        pedido_id = c.execute("""
            INSERT INTO pedidos_repuestos (sigla_local, equipo_repuesto, hilo_asunto, etapa_actual, fecha_solicitud, ultimo_remitente)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sigla, repuesto, hilo_clean, etapa, fecha_now, remitente)).lastrowid
        etapa_anterior = 0
        nueva_etapa = etapa
        
    # Registrar evento en historial
    resumen_log = f"Mail de {remitente}: {asunto[:50]} -> Alcanza {ETAPAS.get(nueva_etapa, 'Etapa ' + str(nueva_etapa))}"
    c.execute("""
        INSERT INTO historial_trazabilidad (id_pedido, fecha, remitente, asunto, etapa_detectada, resumen_ia)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pedido_id, fecha_now, remitente, asunto, nueva_etapa, resumen_log))
    
    conn.commit()
    conn.close()
    
    print(f"📦 [SEGUIMIENTO REPUESTOS] Pedido #{pedido_id} | Local: {sigla} | Repuesto: {repuesto} | Etapa: {ETAPAS.get(nueva_etapa)}")
    
    # 🚨 SI ALCANZA ETAPA 4 (LISTO EN DEPÓSITO), NOTIFICAR A CRISTIAN CON ALERTA ACCIONABLE
    if nueva_etapa == 4 and etapa_anterior < 4:
        msg_alerta = (
            "📦 *[REPUESTO LISTO EN DEPÓSITO]* 🚀\n\n"
            f"📍 *Local:* {sigla}\n"
            f"🛠️ *Repuesto / Equipo:* {repuesto}\n"
            f"👤 *Aviso de Depósito:* {remitente}\n"
            f"📌 *Asunto:* {asunto}\n\n"
            "🟢 *Estado:* _Confirmado por Depósito. Ya se puede pasar a retirar._\n"
            "📲 *Acción:* Listo para coordinar técnico e instalación."
        )
        notificador_telegram.enviar_alerta(msg_alerta, agente="Antigravity", destinatario_id=215173956)
        
    return True, f"Pedido #{pedido_id} actualizado a {ETAPAS.get(nueva_etapa)}"

def obtener_resumen_pedidos_telegram(sigla_filtro=None):
    """Genera un reporte formateado para Telegram de los pedidos en curso."""
    conn = obtener_conexion()
    c = conn.cursor()
    
    query = "SELECT id, sigla_local, equipo_repuesto, etapa_actual, fecha_solicitud, ultimo_remitente FROM pedidos_repuestos WHERE etapa_actual < 5"
    params = []
    if sigla_filtro:
        query += " AND sigla_local = ?"
        params.append(sigla_filtro.upper())
        
    query += " ORDER BY etapa_actual DESC, id DESC"
    c.execute(query, params)
    pedidos = c.fetchall()
    conn.close()
    
    if not pedidos:
        tag = f" de {sigla_filtro}" if sigla_filtro else ""
        return f"ℹ️ No hay pedidos de repuestos pendientes{tag} en este momento."
        
    res = f"📦 *TABLERO DE PEDIDOS DE REPUESTOS EN CURSO* ({len(pedidos)})\n\n"
    for p in pedidos:
        etapa_str = ETAPAS.get(p["etapa_actual"], "DESCONOCIDO")
        res += f"📍 *[{p['sigla_local']}]* #{p['id']} - *{p['equipo_repuesto']}*\n"
        res += f"  • *Etapa:* {etapa_str}\n"
        res += f"  • *Solicitado:* {p['fecha_solicitud'][:10]}\n\n"
        
    return res.strip()

if __name__ == "__main__":
    print("Inicializando base de datos de repuestos...")
    conn = obtener_conexion()
    conn.close()
    print("✅ pedidos_repuestos.db inicializada.")
