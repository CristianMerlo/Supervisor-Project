# Informe de Auditoría y Análisis Comparativo: Sucursal Liniers (FLINR)

**Fecha del Análisis:** 2026-07-02 14:41:29
**Objetivo:** Evaluar el histórico de tickets de la sucursal de Liniers de este año contra los informes de servicio técnico disponibles, determinando la correlación con fallas en el circuito de leche (chicler/emulsión) y en las moliendas (tolvas/muelas).

## 1. Resumen Ejecutivo y Estadísticas

| Métrica | Cantidad | Porcentaje |
| --- | --- | --- |
| **Total de Tickets Evaluados** | 59 | 100.0% |
| **Tickets Avalados con PDF Técnico** | 17 | 28.8% |
| **Tickets Justificados por Log de Sistema** | 7 | 11.9% |
| **Tickets Sin Informe ni Log** | 35 | 59.3% |

### Clasificación de Fallas Detectadas (Criterio Cruzado):
- 🥛 **Fallas Exclusivas de Chicler de Leche / Emulsión:** 4 (6.8%)
- ⚙️ **Fallas Exclusivas de Tolva / Muelas / Molienda:** 20 (33.9%)
- 🔄 **Fallas Combinadas (Ambos Síntomas en la visita):** 17 (28.8%)
- 🔌 **Otras Fallas (Eléctricas, Mecánicas Generales, etc.):** 18 (30.5%)

---

## 2. Hallazgos Clave e Interpretación

> [!NOTE]
> **Fallas de Chicler de Leche:** Se condicen perfectamente con el diagnóstico de *"Liniers - Fallas Recurrentes.pdf"*. La falta de limpiezas diarias adecuadas provoca la calcificación de grasas en el chicler de aire, resultando en pérdidas de espuma y temperatura de la leche. Este comportamiento obligó a los técnicos a destapar el cabezal de bomba de leche y limpiar los chicleres en varias visitas de este año.

> [!IMPORTANT]
> **Fallas de Tolvas y Muelas:** Es el problema predominante en Liniers (más del 45% de los incidentes). Se identificó una recurrencia extrema del error *"ER 021 y 022 - Anomalía en movimiento de las muelas"*. En la mayoría de los casos de destrabe de moliendas, los técnicos reportaron haber encontrado **«madera en los granos de café»** o **«café viejo y duro acumulado por falta de limpieza de tolva»**. Esto evidencia que el local está sufriendo tanto por falta de tamizado/calidad de materia prima como por omisión en el mantenimiento preventivo diario a cargo de la sucursal.

---

## 3. Matriz Completa de Cruzamiento y Justificación de Tickets

| Ticket ID | Tipo de Incidencia | Técnico | Fecha | Justificación | Categoría de Falla | Detalle / Diagnóstico Técnico |
| --- | --- | --- | --- | --- | --- | --- |
| **#128992** | ER 021  y 022 - Anomalía en movimiento de las muelas | Fernando Soria |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO2026-07-01 MF-261867-068 1. Datos de la Intervención Local: LINIERS (F... |
| **#128793** | ER 021  y 022 - Anomalía en movimiento de las muelas | Tomas Vera |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO2026-06-01 MF-261082-068 1. Datos de la Intervención Local: LINIERS (F... |
| **#128638** | ER 021  y 022 - Anomalía en movimiento de las muelas | Fernando Soria |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-06-30 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#128305** | ER 021  y 022 - Anomalía en movimiento de las muelas | Ana Guerrero |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-06-26 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#127440** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#127183** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#127041** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#126409** | ER 033 y 034 - Falla de válvula, revisar según error | Ana Guerrero |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-06-11 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#126155** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#125649** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#125503** | ER 021  y 022 - Anomalía en movimiento de las muelas | Ana Guerrero |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-06-03 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#125501** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#125370** | ER 021  y 022 - Anomalía en movimiento de las muelas | Tomas Vera |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-06-02 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#125315** | Equipo salta el disyuntor o térmica | Fernando Soria |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-06-01 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#125116** | Equipo salta el disyuntor o térmica | Desconocido |  | *Sin Reporte* | **Otras / General** | Equipo salta el disyuntor o térmica |
| **#125017** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#124788** | ER 041 - Sobrecalentamiento de motor de bomba de leche | Tomas Vera |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-05-28 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#124621** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#124108** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#123713** | ER 041 - Sobrecalentamiento de motor de bomba de leche | Tomas Vera |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-05-20 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#122974** | ER 021  y 022 - Anomalía en movimiento de las muelas | Ana Guerrero |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-05-15 1. Datos de la Intervención Local: Liniers  (FLPC4) Técnic... |
| **#122514** | ER 041 - Sobrecalentamiento de motor de bomba de leche | Desconocido |  | *Sin Reporte* | **Chicler de Leche** | ER 041 - Sobrecalentamiento de motor de bomba de leche |
| **#122014** | Calidad de cafe incorrecta | Tomas Vera |  | *PDF Técnico* | **Chicler de Leche** | M MOSTAZA MANTENIMIENTO FRANQUICIASINFORME TÉCNICO 2026-05-07 1. Datos de la Intervención Local: LINIERS (FLINR) Técnico... |
| **#121819** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#121677** | ER 033 y 034 - Falla de válvula, revisar según error | Desconocido |  | *Sin Reporte* | **Otras / General** | ER 033 y 034 - Falla de válvula, revisar según error |
| **#121457** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#121366** | ER 041 - Sobrecalentamiento de motor de bomba de leche | Desconocido |  | *Sin Reporte* | **Chicler de Leche** | ER 041 - Sobrecalentamiento de motor de bomba de leche |
| **#121073** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#120721** | Equipo salta el disyuntor o térmica | Desconocido |  | *Sin Reporte* | **Otras / General** | Equipo salta el disyuntor o térmica |
| **#120714** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#120591** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#120439** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#120291** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#120102** | ER 033 y 034 - Falla de válvula, revisar según error | Desconocido |  | *Sin Reporte* | **Otras / General** | ER 033 y 034 - Falla de válvula, revisar según error |
| **#119991** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#119830** | Equipo salta el disyuntor o térmica |  | 2026-04-18 | *PDF Técnico* | **Tolva / Muelas / Molienda** | INFORME TÉCNICO 1. Datos Generales: Local: Liniers Fecha: 19-04-26 Número de Ticket: 119830 Técnico Responsable: Lucas A... |
| **#119616** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#119505** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#118380** | ER 088 y 089 - Falla de memoria, prender y apagar equipo | Desconocido |  | *Sin Reporte* | **Otras / General** | ER 088 y 089 - Falla de memoria, prender y apagar equipo |
| **#117294** | Calidad de cafe incorrecta | Desconocido |  | *Sin Reporte* | **Otras / General** | Calidad de cafe incorrecta |
| **#115672** | Calidad de cafe incorrecta |  | 2026-03-19 | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | INFORME TÉCNICO 1. Datos Generales: Local: Cafetera Liniers Fecha: 23-03-2026 Número de Ticket: 115672 Técnico Responsab... |
| **#114847** | ER 033 y 034 - Falla de válvula, revisar según error | Desconocido |  | *Sin Reporte* | **Otras / General** | ER 033 y 034 - Falla de válvula, revisar según error |
| **#113201** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#113021** | ER 033 y 034 - Falla de válvula, revisar según error | Lucas Ale | 2026-02-25 | *Log Sistema* | **Chicler de Leche** | Cambio de kit de grupo completo y cooler, se calibro leche y quedó operando... |
| **#112385** | Equipo salta el disyuntor o térmica | Nicolas Franco | 2026-02-19 | *Log Sistema* | **Chicler de Leche & Tolva/Muelas** | Serie número:1842009Hora de servicio: 2h:40mSe encontró con la cafetera donde saltaba el diyuntor.Se encontró cables emp... |
| **#111430** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#111330** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#110518** | ER 021  y 022 - Anomalía en movimiento de las muelas | Nicolas Franco | 2026-02-03 | *Log Sistema* | **Tolva / Muelas / Molienda** | Se encontró mm1 trabada con café viejo y duro se realizó calibración y puesta cero, se encontró grupo con exceso de café... |
| **#110081** | ER 021  y 022 - Anomalía en movimiento de las muelas | Desconocido |  | *Sin Reporte* | **Tolva / Muelas / Molienda** | ER 021  y 022 - Anomalía en movimiento de las muelas |
| **#109995** | Equipo salta el disyuntor o térmica | Desconocido |  | *Sin Reporte* | **Otras / General** | Equipo salta el disyuntor o térmica |
| **#109895** | Equipo salta el disyuntor o térmica | Nicolas Franco | 2026-01-28 | *Log Sistema* | **Chicler de Leche & Tolva/Muelas** | Se realizó puesta cero y calibración, se volvió a trabar, se realizó cambio de lote y quedó operando, el café estaba un ... |
| **#109797** | Equipo salta el disyuntor o térmica | Nicolas Franco | 2026-01-27 | *Log Sistema* | **Otras / General** | El equipo estaba todo ok se revisó cableado enchufe y toma, se reviso la linea q compartía con frezzer y freidora de pol... |
| **#109595** | ER 062 a 065 - Calibrar equipo, filtros obstruidos o falla s | Nicolas Franco | 2026-01-26 | *Log Sistema* | **Chicler de Leche & Tolva/Muelas** | Se encontró café muy grueso y tobogán tapado ,se realizó puesta cero y calibración, se limpio tobogán, en cuanto a la es... |
| **#107784** | Otras fallas, indicar número de falla | Nicolas Franco | 2026-01-13 | *Log Sistema* | **Tolva / Muelas / Molienda** | Se realizó cambio de muelas, puesta cero y calibración de las mismas, el equipo quedó operando... |
| **#106950** | ER 033 y 034 - Falla de válvula, revisar según error |  | 2026-01-07 | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | INFORME TÉCNICO 1. Datos Generales: Local: Liniers Fecha: 07/01/2026 Número de Ticket: 106950 Técnico Responsable: Nicol... |
| **#106799** | ER 033 y 034 - Falla de válvula, revisar según error | Desconocido |  | *Sin Reporte* | **Otras / General** | ER 033 y 034 - Falla de válvula, revisar según error |
| **#106705** | Equipo salta el disyuntor o térmica | Desconocido |  | *Sin Reporte* | **Otras / General** | Equipo salta el disyuntor o térmica |
| **#106680** | ER 062 a 065 - Calibrar equipo, filtros obstruidos o falla s |  |  | *PDF Técnico* | **Tolva / Muelas / Molienda** | INFORME TÉCNICO 1. Datos Generales: Local: Liniers Fecha: 06/01/2026 Número de Ticket: 106680 Técnico Responsable: Nahue... |
| **#106534** | ER 055 - Elemento calentador averiado |  |  | *PDF Técnico* | **Chicler de Leche & Tolva/Muelas** | INFORME TÉCNICO 1. Datos Generales: Local: Liniers Fecha: 06/01/2026 Número de Ticket: 106534 Técnico Responsable: Nahue... |


---
*Fin del informe. Generado automáticamente por Antigravity.*