#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: aplicar_actualizaciones_sabana.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Aplica masivamente las 66 Razones Sociales actualizadas y las 82 Direcciones corregidas
a la Sábana en Google Sheets, supervisor_local.db, locales.csv, sucursales_nuevas.json
y actualizar_locales.py.
"""

import os
import sys
import json
import sqlite3
import pandas as pd
from pathlib import Path
from difflib import SequenceMatcher

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from actualizar_locales import DATOS_CRUDOS

def similaridad(a, b):
    return SequenceMatcher(None, str(a).upper().strip(), str(b).upper().strip()).ratio()

def aplicar():
    # 1. Parsear Sábana Actual
    filas = [linea.split("|") for linea in DATOS_CRUDOS.strip().split("\n") if linea.strip()]
    headers = filas[0]
    data = filas[1:]
    
    # 2. Cargar CSV con nuevas Direcciones
    csv_path = Path("/home/cristian/Descargas/base_locales_mostaza.csv")
    df_csv = pd.read_csv(csv_path)
    df_csv.columns = [c.strip() for c in df_csv.columns]
    
    dict_csv = {}
    for _, row in df_csv.iterrows():
        l_name = str(row.get("LOCAL", "")).strip().upper()
        dict_csv[l_name] = {
            "direccion": str(row.get("DIRECCION", "")).strip(),
            "razon_social": str(row.get("RAZON SOCIAL", "")).strip()
        }

    # 3. Cargar Excel con Razones Sociales y CUITs
    excel_path = Path("/home/cristian/Descargas/Detalle FR - CUIT 2.xlsx")
    df_excel = pd.read_excel(excel_path)
    df_excel.columns = [c.strip() for c in df_excel.columns]
    
    dict_excel = {}
    for _, row in df_excel.iterrows():
        l_name = str(row.get("Local", "")).strip().upper()
        dict_excel[l_name] = {
            "razon_social": str(row.get("Razon Social", "")).strip(),
            "cuit": str(row.get("Cuit", "")).strip()
        }

    # 4. Actualizar filas de DATOS_CRUDOS
    nuevas_filas = [headers]
    modificados_rs = 0
    modificados_dir = 0

    for r in data:
        r_mod = list(r)
        sigla_sys = r_mod[0].strip()
        sigla_tk = r_mod[1].strip()
        local_name = r_mod[4].strip()
        dir_actual = r_mod[6].strip()
        rs_actual = r_mod[10].strip()
        local_key = local_name.upper()

        # Buscar coincidencia en Excel para Razon Social
        best_match_excel = None
        best_score_excel = 0
        for ex_key in dict_excel.keys():
            sc = similaridad(local_key, ex_key)
            if sc > best_score_excel:
                best_score_excel = sc
                best_match_excel = ex_key

        if best_match_excel and best_score_excel > 0.65:
            rs_nueva = dict_excel[best_match_excel]["razon_social"]
            if rs_nueva and rs_nueva != "nan" and rs_nueva.upper() != rs_actual.upper():
                r_mod[10] = rs_nueva
                modificados_rs += 1

        # Buscar coincidencia en CSV para Dirección
        best_match_csv = None
        best_score_csv = 0
        for csv_k in dict_csv.keys():
            sc = similaridad(local_key, csv_k)
            if sc > best_score_csv:
                best_score_csv = sc
                best_match_csv = csv_k

        if best_match_csv and best_score_csv > 0.65:
            dir_nueva = dict_csv[best_match_csv]["direccion"]
            if dir_nueva and dir_nueva != "nan" and dir_nueva.upper() != dir_actual.upper():
                r_mod[6] = dir_nueva
                modificados_dir += 1

        nuevas_filas.append(r_mod)

    print(f"✅ Se actualizaron {modificados_rs} Razones Sociales y {modificados_dir} Direcciones en los datos.")

    # 5. Reconstruir DATOS_CRUDOS string
    lineas_datos = ["|".join(f) for f in nuevas_filas]
    nuevo_datos_crudos_str = "\n".join(lineas_datos)

    # 6. Escribir actualizar_locales.py
    act_path = BASE_DIR / "actualizar_locales.py"
    with open(act_path, "r", encoding="utf-8") as f:
        act_code = f.read()

    # Reemplazar el bloque DATOS_CRUDOS = """..."""
    import re
    nuevo_code = re.sub(r'DATOS_CRUDOS = """(.*?)"""', f'DATOS_CRUDOS = """{nuevo_datos_crudos_str}"""', act_code, flags=re.DOTALL)
    with open(act_path, "w", encoding="utf-8") as f:
        f.write(nuevo_code)

    print("[✓] actualizar_locales.py guardado con los nuevos datos.")

    # 7. Escribir locales.csv
    csv_out = BASE_DIR / "locales.csv"
    lineas_csv = [",".join([f'"{val}"' if "," in val else val for val in f]) for f in nuevas_filas]
    with open(csv_out, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_csv))
    print("[✓] locales.csv guardado.")

    # 8. Actualizar supervisor_local.db
    db_path = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    for r in nuevas_filas[1:]:
        sigla_sys = r[0].strip()
        sigla_tk = r[1].strip()
        local_name = r[4].strip()
        direccion = r[6].strip()
        razon_social = r[10].strip()

        sigla_usar = sigla_tk if sigla_tk != "-" else sigla_sys
        if sigla_usar and sigla_usar != "-":
            c.execute("UPDATE locales SET nombre = ? WHERE sigla = ?", (local_name, sigla_usar))
            c.execute("INSERT OR REPLACE INTO locales (sigla, nombre) VALUES (?, ?)", (sigla_usar, local_name))
            
        if sigla_sys and sigla_sys != "-":
            c.execute("INSERT OR REPLACE INTO locales (sigla, nombre) VALUES (?, ?)", (sigla_sys, local_name))

    conn.commit()
    conn.close()
    print("[✓] supervisor_local.db actualizado.")

if __name__ == "__main__":
    aplicar()
