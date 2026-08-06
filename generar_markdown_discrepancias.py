#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from comparar_bases_locales import analizar_discrepancias

rs_diffs, dir_diffs = analizar_discrepancias()

out_md = Path("/home/cristian/.gemini/antigravity/brain/d89bc76c-0da5-4c85-9a8d-b550b2185c88/reporte_discrepancias_locales.md")

content = f"""# Reporte Comparativo de Discrepancias de Locales

Se realizó un análisis exhaustivo entre la **Sábana actual de datos (`DATOS_CRUDOS`)** y las tres nuevas fuentes de información:
- `base_locales_mostaza.txt`
- `base_locales_mostaza.csv`
- `Detalle FR - CUIT 2.xlsx`

> [!IMPORTANT]
> **Regla de Aprobar antes de Modificar:** No se ha realizado ninguna modificación en la Sábana. Este documento expone las diferencias exactas encontradas para tu revisión y aprobación punto por punto.

---

## Summary de Hallazgos
- **Discrepancias en Razones Sociales:** **{len(rs_diffs)}** locales.
- **Discrepancias en Direcciones:** **{len(dir_diffs)}** locales.

---

## 1. Discrepancias en Razones Sociales ({len(rs_diffs)})

| # | Local | Sigla | Razón Social Actual (Sábana) | Razón Social Nueva (Detalle FR - CUIT 2.xlsx) | CUIT Nuevo |
|---|---|---|---|---|---|
"""

for i, d in enumerate(rs_diffs, 1):
    content += f"| {i} | {d['local']} | `{d['sigla']}` | `{d['actual']}` | **`{d['nueva']}`** | `{d['cuit']}` |\n"

content += f"""

---

## 2. Discrepancias en Direcciones ({len(dir_diffs)})

| # | Local | Sigla | Dirección Actual (Sábana) | Dirección Nueva (base_locales_mostaza.csv / txt) |
|---|---|---|---|---|
"""

for i, d in enumerate(dir_diffs, 1):
    content += f"| {i} | {d['local']} | `{d['sigla']}` | `{d['actual']}` | **`{d['nueva']}`** |\n"

with open(out_md, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ Reporte generado exitosamente en: {out_md}")
