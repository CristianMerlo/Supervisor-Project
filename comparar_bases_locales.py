#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: comparar_bases_locales.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Compara las Direcciones y Razones Sociales entre la Sábana actual (actualizar_locales.py)
y las tres fuentes de información proporcionadas:
- base_locales_mostaza.txt
- base_locales_mostaza.csv
- Detalle FR - CUIT 2.xlsx
"""

import sys
import pandas as pd
import openpyxl
from pathlib import Path
from difflib import SequenceMatcher

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from actualizar_locales import DATOS_CRUDOS

def similaridad(a, b):
    return SequenceMatcher(None, str(a).upper().strip(), str(b).upper().strip()).ratio()

def analizar_discrepancias():
    # 1. Parsear Sábana Actual
    filas = [linea.split("|") for linea in DATOS_CRUDOS.strip().split("\n") if linea.strip()]
    headers = filas[0]
    data = filas[1:]
    
    dict_actual = {}
    for r in data:
        sigla_sys = r[0].strip()
        sigla_tk = r[1].strip()
        local_name = r[4].strip()
        direccion = r[6].strip()
        razon_social = r[10].strip()
        
        dict_actual[local_name.upper()] = {
            "sigla_sys": sigla_sys,
            "sigla_tk": sigla_tk,
            "local_original": local_name,
            "direccion_actual": direccion,
            "razon_social_actual": razon_social
        }

    # 2. Cargar CSV con nuevas Direcciones
    csv_path = Path("/home/cristian/Descargas/base_locales_mostaza.csv")
    df_csv = pd.read_csv(csv_path)
    df_csv.columns = [c.strip() for c in df_csv.columns]
    
    dict_csv = {}
    for _, row in df_csv.iterrows():
        l_name = str(row.get("LOCAL", "")).strip().upper()
        dir_val = str(row.get("DIRECCION", "")).strip()
        rs_val = str(row.get("RAZON SOCIAL", "")).strip()
        dict_csv[l_name] = {
            "direccion_csv": dir_val,
            "razon_social_csv": rs_val
        }

    # 3. Cargar Excel con Razones Sociales y CUITs
    excel_path = Path("/home/cristian/Descargas/Detalle FR - CUIT 2.xlsx")
    df_excel = pd.read_excel(excel_path)
    df_excel.columns = [c.strip() for c in df_excel.columns]
    
    dict_excel = {}
    for _, row in df_excel.iterrows():
        l_name = str(row.get("Local", "")).strip().upper()
        rs_val = str(row.get("Razon Social", "")).strip()
        cuit_val = str(row.get("Cuit", "")).strip()
        dict_excel[l_name] = {
            "razon_social_excel": rs_val,
            "cuit_excel": cuit_val
        }

    # 4. Cruzar y buscar discrepancias
    discrepancias_razon_social = []
    discrepancias_direccion = []

    for local_key, info_actual in dict_actual.items():
        # Buscar mejor coincidencia en Excel para Razon Social
        best_match_excel = None
        best_score_excel = 0
        for ex_key in dict_excel.keys():
            sc = similaridad(local_key, ex_key)
            if sc > best_score_excel:
                best_score_excel = sc
                best_match_excel = ex_key
                
        rs_nueva = None
        cuit_nuevo = None
        if best_match_excel and best_score_excel > 0.65:
            rs_nueva = dict_excel[best_match_excel]["razon_social_excel"]
            cuit_nuevo = dict_excel[best_match_excel]["cuit_excel"]

        # Buscar mejor coincidencia en CSV para Dirección
        best_match_csv = None
        best_score_csv = 0
        for csv_k in dict_csv.keys():
            sc = similaridad(local_key, csv_k)
            if sc > best_score_csv:
                best_score_csv = sc
                best_match_csv = csv_k
                
        dir_nueva = None
        if best_match_csv and best_score_csv > 0.65:
            dir_nueva = dict_csv[best_match_csv]["direccion_csv"]

        # Evaluar discrepancia en Razón Social
        if rs_nueva and rs_nueva.strip().upper() != info_actual["razon_social_actual"].strip().upper():
            if not (info_actual["razon_social_actual"] == "-" and rs_nueva == "nan"):
                discrepancias_razon_social.append({
                    "local": info_actual["local_original"],
                    "sigla": info_actual["sigla_tk"] if info_actual["sigla_tk"] != "-" else info_actual["sigla_sys"],
                    "actual": info_actual["razon_social_actual"],
                    "nueva": rs_nueva,
                    "cuit": cuit_nuevo
                })

        # Evaluar discrepancia en Dirección
        if dir_nueva and dir_nueva.strip().upper() != info_actual["direccion_actual"].strip().upper():
            if not (info_actual["direccion_actual"] == "-" and dir_nueva == "nan"):
                discrepancias_direccion.append({
                    "local": info_actual["local_original"],
                    "sigla": info_actual["sigla_tk"] if info_actual["sigla_tk"] != "-" else info_actual["sigla_sys"],
                    "actual": info_actual["direccion_actual"],
                    "nueva": dir_nueva
                })

    return discrepancias_razon_social, discrepancias_direccion

if __name__ == "__main__":
    rs_diffs, dir_diffs = analizar_discrepancias()
    print(f"Discrepancias en Razón Social encontradas: {len(rs_diffs)}")
    print(f"Discrepancias en Dirección encontradas: {len(dir_diffs)}")
