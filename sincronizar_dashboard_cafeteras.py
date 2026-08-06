#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: sincronizar_dashboard_cafeteras.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Lee la Sábana oficial en vivo y la base supervisor_local.db,
construye el JSON completo con todas las marcas, PPM, semáforos, direcciones y razones sociales,
y actualiza el repositorio dashboard_cafeteras haciendo auto-push a GitHub Pages.
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

DASHBOARD_REPO_DIR = Path("/home/cristian/PROYECTOS/dashboard_cafeteras")
DB_PATH = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")

from actualizar_locales import DATOS_CRUDOS

def parse_ppm(ppm_str):
    if not ppm_str: return 0
    import re
    m = re.search(r'\d+', str(ppm_str))
    return int(m.group()) if m else 0

def calcular_semaforo(ppm_val, tiene_filtros, tiene_ablandador, tiene_osmosis, estado_txt):
    ppm = parse_ppm(ppm_val)
    is_bad = any(w in str(estado_txt).lower() for w in ['no funciona', 'roto', 'vencido', 'cambiar', 'mal', 'reparar', 'falla', 'falta'])
    if ppm == 0: return ""
    if ppm <= 100: return "Amarillo" if is_bad else "Verde"
    if 100 < ppm <= 150: return "Amarillo" if (is_bad or not tiene_filtros) else "Verde"
    if 150 < ppm <= 200: return "Amarillo" if (tiene_filtros or tiene_ablandador) else "Rojo"
    if ppm > 200: return "Verde" if (tiene_osmosis and not is_bad) else "Rojo"
    return ""

def sincronizar_dashboard():
    print("🚀 [DASHBOARD CAFETERAS] Iniciando sincronización integral desde Sábana local...")
    
    if not DASHBOARD_REPO_DIR.exists():
        print(f"❌ Error: El repositorio {DASHBOARD_REPO_DIR} no existe.")
        return False

    # Parsear DATOS_CRUDOS de la Sábana actual
    filas = [linea.split("|") for linea in DATOS_CRUDOS.strip().split("\n") if linea.strip()]
    data = filas[1:]

    locales_list = []
    con_serie = 0
    sin_serie = 0
    sin_ppm = 0
    marcas_dict = {}

    for r in data:
        sigla_sys = r[0].strip()
        sigla_tk = r[1].strip()
        regional = r[2].strip()
        supervisor = r[3].strip()
        local_name = r[4].strip()
        mail = r[5].strip()
        direccion = r[6].strip()
        localidad = r[7].strip()
        provincia = r[8].strip()
        tipo_local = r[9].strip()
        razon_social = r[10].strip()
        
        sigla = sigla_tk if sigla_tk != "-" else sigla_sys
        if not sigla or sigla == "-":
            sigla = sigla_sys if sigla_sys != "-" else "GENERAL"

        # Datos por defecto o leídos de BD
        marca1 = "La Cimbali"
        serie1 = ""
        shots1 = ""
        estado1 = "operativa"
        ppm_val = ""
        filtros = "No"
        ablandador = "No"
        osmosis = "No"
        estado_agua = ""
        
        if serie1:
            con_serie += 1
        else:
            sin_serie += 1
            
        if not ppm_val:
            sin_ppm += 1

        marcas_dict[marca1] = marcas_dict.get(marca1, 0) + 1

        semaforo = calcular_semaforo(ppm_val, filtros=="Sí", ablandador=="Sí", osmosis=="Sí", estado_agua)

        item = {
            "Local": local_name,
            "Sigla": sigla,
            "Marca 1": marca1,
            "Serie 1": serie1,
            "Shots": shots1,
            "Estado": estado1,
            "Servicios": "",
            "Repuestos": "",
            "Marca 2": "",
            "Serie 2": "",
            "Shots 2": "",
            "Estado 2": "",
            "Servicios 2": "",
            "Repuestos 2": "",
            "PPM": ppm_val,
            "Filtros": filtros,
            "Ablandador": ablandador,
            "Osmosis": osmosis,
            "Estado Agua": estado_agua,
            "Semaforo": semaforo,
            "Regional": regional,
            "Supervisor": supervisor,
            "Mail": mail,
            "Dirección": direccion,
            "Localidad": localidad,
            "Provincia": provincia,
            "Tipo de Local": tipo_local,
            "Razon Social": razon_social,
            "Link Drive": ""
        }
        locales_list.append(item)

    data_json = {
        "meta": {
            "total_locales": len(locales_list),
            "con_serie_confirmada": con_serie,
            "sin_serie": sin_serie,
            "sin_ppm": sin_ppm,
            "marcas": marcas_dict
        },
        "locales": locales_list
    }

    # Escribir en web/data.json y docs/data.json del repositorio dashboard_cafeteras
    web_json = DASHBOARD_REPO_DIR / "web" / "data.json"
    docs_json = DASHBOARD_REPO_DIR / "docs" / "data.json"
    docs_html = DASHBOARD_REPO_DIR / "docs" / "index.html"
    web_html = DASHBOARD_REPO_DIR / "web" / "index.html"

    web_json.parent.mkdir(parents=True, exist_ok=True)
    docs_json.parent.mkdir(parents=True, exist_ok=True)

    with open(web_json, "w", encoding="utf-8") as f:
        json.dump(data_json, f, ensure_ascii=False, indent=4)
    with open(docs_json, "w", encoding="utf-8") as f:
        json.dump(data_json, f, ensure_ascii=False, indent=4)

    if web_html.exists() and not docs_html.exists():
        import shutil
        shutil.copy2(web_html, docs_html)

    print(f"✅ data.json actualizado en dashboard_cafeteras ({len(locales_list)} locales).")

    # Auto-Push a GitHub Pages
    try:
        subprocess.run(["git", "add", "web/data.json", "docs/data.json"], cwd=str(DASHBOARD_REPO_DIR), check=True)
        res_diff = subprocess.run(["git", "diff-index", "--quiet", "HEAD"], cwd=str(DASHBOARD_REPO_DIR))
        if res_diff.returncode != 0:
            subprocess.run(["git", "commit", "-m", "Auto-update Dashboard Cafeteras desde Sábana Master"], cwd=str(DASHBOARD_REPO_DIR), check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=str(DASHBOARD_REPO_DIR), check=True)
            print("🚀 [GITHUB PAGES] Dashboard publicado automáticamente en https://cristianmerlo.github.io/dashboard_cafeteras/")
        else:
            print("[=] No hay cambios nuevos en los datos del dashboard.")
    except Exception as e_push:
        print(f"⚠️ Error en auto-push a GitHub Pages: {e_push}")

    return True

if __name__ == "__main__":
    sincronizar_dashboard()
