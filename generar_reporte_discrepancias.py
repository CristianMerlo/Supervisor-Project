#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from comparar_bases_locales import analizar_discrepancias

rs_diffs, dir_diffs = analizar_discrepancias()

print(f"=== DISCREPANCIAS EN RAZÓN SOCIAL ({len(rs_diffs)}) ===")
for d in rs_diffs[:10]:
    print(f"- {d['local']} [{d['sigla']}]: Actual='{d['actual']}' ➔ Nueva='{d['nueva']}' (CUIT: {d['cuit']})")

print(f"\n=== DISCREPANCIAS EN DIRECCIÓN ({len(dir_diffs)}) ===")
for d in dir_diffs[:10]:
    print(f"- {d['local']} [{d['sigla']}]: Actual='{d['actual']}' ➔ Nueva='{d['nueva']}'")
