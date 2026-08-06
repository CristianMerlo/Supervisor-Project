#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: generar_tablero_web.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Lee la base SQLite pedidos_repuestos.db y genera la página HTML interactiva
web_repuestos_tablero.html con los datos reales en tiempo real.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = Path("/home/cristian/Documentos/Supervisor/pedidos_repuestos.db")
HTML_OUT = Path("/home/cristian/Documentos/Supervisor/web_repuestos_tablero.html")
HTML_LOCAL = BASE_DIR / "web_repuestos_tablero.html"

def resolver_nombre_local(sigla_raw):
    """Obtiene el nombre completo del local desde la BD supervisor_local.db."""
    if not sigla_raw or sigla_raw.upper() in ["GENERAL", "DESCONOCIDO"]:
        return "General (GENERAL)"
    try:
        conn = sqlite3.connect("/home/cristian/Documentos/Supervisor/supervisor_local.db")
        c = conn.cursor()
        s_clean = sigla_raw.upper().strip()
        c.execute("SELECT nombre, sigla FROM locales WHERE sigla = ?", (s_clean,))
        row = c.fetchone()
        if not row:
            c.execute("SELECT nombre, sigla FROM locales WHERE sigla LIKE ? OR nombre LIKE ?", (f"%{s_clean}%", f"%{s_clean}%"))
            row = c.fetchone()
        conn.close()
        if row:
            return f"{row[0].title()} ({row[1]})"
    except Exception:
        pass
    return sigla_raw.upper()

def generar_tablero():
    if not DB_PATH.exists():
        pedidos_data = []
    else:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, sigla_local as sigla, equipo_repuesto as equipo, etapa_actual as etapa, fecha_solicitud as fecha FROM pedidos_repuestos ORDER BY etapa_actual DESC, id DESC")
        rows = c.fetchall()
        conn.close()
        
        pedidos_data = []
        for r in rows:
            etapa = r["etapa"]
            avance = etapa * 20
            sigla_val = r["sigla"]
            nombre_display = resolver_nombre_local(sigla_val)
            
            accion = "Sin acción requerida"
            if etapa == 1: accion = "Pendiente cotización Mantenimiento"
            elif etapa == 2: accion = "Pendiente aprobación Operaciones/Regional"
            elif etapa == 3: accion = "Esperando disponibilidad Depósito"
            elif etapa == 4: accion = "Notificar a franquiciado para retirar por depósito"
            elif etapa == 5: accion = "Instalado / Concluido"
            
            pedidos_data.append({
                "id": r["id"],
                "sigla": nombre_display,
                "equipo": r["equipo"],
                "etapa": etapa,
                "fecha": r["fecha"],
                "avance": avance,
                "accion": accion
            })

    json_data = json.dumps(pedidos_data, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tablero de Seguimiento de Pedidos de Repuestos - Mostaza</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-card: #1e293b;
            --accent: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --stage-1: #eab308;
            --stage-2: #f97316;
            --stage-3: #3b82f6;
            --stage-4: #22c55e;
            --stage-5: #64748b;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-main);
            padding: 24px;
            min-height: 100vh;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }}

        .title-group h1 {{
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .title-group p {{ font-size: 0.875rem; color: var(--text-muted); margin-top: 4px; }}

        .controls {{ display: flex; gap: 12px; }}

        input, select {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: 8px;
            outline: none;
            font-size: 0.875rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
        }}

        .stat-card .val {{ font-size: 1.8rem; font-weight: 700; margin-top: 6px; }}
        .stat-card.stage-4 .val {{ color: var(--stage-4); }}
        .stat-card.stage-3 .val {{ color: var(--stage-3); }}
        .stat-card.stage-2 .val {{ color: var(--stage-2); }}
        .stat-card.stage-1 .val {{ color: var(--stage-1); }}

        .table-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}

        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem; }}
        th {{ background: #111827; padding: 14px 16px; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--border); }}
        td {{ padding: 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}

        .badge-sigla {{
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.8rem;
        }}

        .progress-bar-bg {{
            background: #334155;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            width: 100%;
            margin-top: 6px;
        }}

        .progress-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s ease; }}

        .pill-status {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .s1 {{ background: rgba(234, 179, 8, 0.15); color: #fde047; }}
        .s2 {{ background: rgba(249, 115, 22, 0.15); color: #fdba74; }}
        .s3 {{ background: rgba(59, 130, 246, 0.15); color: #93c5fd; }}
        .s4 {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }}
        .s5 {{ background: rgba(100, 116, 139, 0.15); color: #cbd5e1; }}

        /* Adaptación Responsiva para Celulares y Tablets */
        @media (max-width: 768px) {{
            body {{ padding: 12px; }}
            header {{ flex-direction: column; align-items: flex-start; gap: 14px; }}
            .controls {{ width: 100%; flex-direction: column; gap: 8px; }}
            input, select {{ width: 100%; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); gap: 10px; }}
            .table-container {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
            table {{ min-width: 650px; }}
        }}
    </style>
</head>
<body>

    <header>
        <div class="title-group">
            <h1>📦 Tablero de Control de Repuestos</h1>
            <p>Seguimiento en tiempo real del circuito de 5 etapas por sucursal</p>
        </div>
        <div class="controls">
            <input type="text" id="searchInput" placeholder="Buscar por local o repuesto..." onkeyup="filterTable()">
            <select id="stageFilter" onchange="filterTable()">
                <option value="ALL">Todas las Etapas</option>
                <option value="1">1. Solicitado</option>
                <option value="2">2. Presupuestado</option>
                <option value="3">3. Aprobado</option>
                <option value="4">4. Listo en Depósito</option>
                <option value="5">5. Instalado</option>
            </select>
        </div>
    </header>

    <div class="stats-grid">
        <div class="stat-card stage-4">
            <span>🟢 Listo en Depósito (Aviso a Franquicia)</span>
            <span class="val" id="cntStage4">0</span>
        </div>
        <div class="stat-card stage-3">
            <span>🔵 Aprobados (Esperando Depósito)</span>
            <span class="val" id="cntStage3">0</span>
        </div>
        <div class="stat-card stage-2">
            <span>🟠 Presupuestados (Pend. Aprobación)</span>
            <span class="val" id="cntStage2">0</span>
        </div>
        <div class="stat-card stage-1">
            <span>🟡 Solicitados (Pend. Cotizar)</span>
            <span class="val" id="cntStage1">0</span>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Local</th>
                    <th>Equipo / Repuesto</th>
                    <th>Avance del Circuito</th>
                    <th>Etapa Actual</th>
                    <th>Última Actualización</th>
                    <th>Acción Siguiente</th>
                </tr>
            </thead>
            <tbody id="tableBody">
            </tbody>
        </table>
    </div>

    <script>
        const pedidos = {json_data};

        function renderTable(items) {{
            const tbody = document.getElementById("tableBody");
            tbody.innerHTML = "";

            let c1=0, c2=0, c3=0, c4=0;

            if (items.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">No hay pedidos registrados en esta vista.</td></tr>`;
                return;
            }}

            items.forEach(p => {{
                if (p.etapa === 1) c1++;
                if (p.etapa === 2) c2++;
                if (p.etapa === 3) c3++;
                if (p.etapa === 4) c4++;

                const row = document.createElement("tr");

                let stageClass = `s${{p.etapa}}`;
                let stageName = "";
                let barColor = "#eab308";
                if(p.etapa === 1) {{ stageName = "🟡 1. Solicitado"; barColor = "#eab308"; }}
                if(p.etapa === 2) {{ stageName = "🟠 2. Presupuestado"; barColor = "#f97316"; }}
                if(p.etapa === 3) {{ stageName = "🔵 3. Aprobado"; barColor = "#3b82f6"; }}
                if(p.etapa === 4) {{ stageName = "🟢 4. Listo en Depósito"; barColor = "#22c55e"; }}
                if(p.etapa === 5) {{ stageName = "✅ 5. Instalado"; barColor = "#64748b"; }}

                row.innerHTML = `
                    <td>#${{p.id}}</td>
                    <td><span class="badge-sigla">${{p.sigla}}</span></td>
                    <td><strong>${{p.equipo}}</strong></td>
                    <td style="width: 200px;">
                        <span style="font-size: 0.75rem; color: var(--text-muted);">${{p.avance}}%</span>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width: ${{p.avance}}%; background: ${{barColor}};"></div>
                        </div>
                    </td>
                    <td><span class="pill-status ${{stageClass}}">${{stageName}}</span></td>
                    <td style="color: var(--text-muted); font-size: 0.8rem;">${{p.fecha}}</td>
                    <td style="color: var(--text-main); font-size: 0.8rem;">${{p.accion}}</td>
                `;
                tbody.appendChild(row);
            }});

            document.getElementById("cntStage1").innerText = c1;
            document.getElementById("cntStage2").innerText = c2;
            document.getElementById("cntStage3").innerText = c3;
            document.getElementById("cntStage4").innerText = c4;
        }}

        function filterTable() {{
            const query = document.getElementById("searchInput").value.toLowerCase();
            const stage = document.getElementById("stageFilter").value;

            const filtered = pedidos.filter(p => {{
                const matchQuery = p.sigla.toLowerCase().includes(query) || p.equipo.toLowerCase().includes(query);
                const matchStage = stage === "ALL" || p.etapa.toString() === stage;
                return matchQuery && matchStage;
            }});

            renderTable(filtered);
        }}

        renderTable(pedidos);
    </script>
</body>
</html>
"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(HTML_LOCAL, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # Actualizar repositorio GitHub online
    repo_online = Path("/home/cristian/PROYECTOS/Tablero-de-Control-de-Repuestos")
    if repo_online.exists():
        try:
            dst_online = repo_online / "index.html"
            with open(dst_online, "w", encoding="utf-8") as f:
                f.write(html_content)
            import subprocess
            subprocess.Popen(["git", "add", "index.html"], cwd=str(repo_online))
            subprocess.Popen(["git", "commit", "-m", "Auto-update online dashboard"], cwd=str(repo_online))
            subprocess.Popen(["git", "push", "origin", "main"], cwd=str(repo_online))
            print("🚀 [GITHUB ONLINE] Tablero sincronizado y enviado a GitHub Pages.")
        except Exception as e_gh:
            print(f"Error sincronizando GitHub Pages: {e_gh}")
        
    print(f"✅ Tablero visual generado exitosamente en: {HTML_OUT}")

if __name__ == "__main__":
    generar_tablero()
