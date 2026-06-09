# Skills del Agente Hermes

Este documento define la lista de "skills" (herramientas, APIs y librerías) recomendadas para expandir las capacidades del Agente Hermes en las tareas planificadas.

---

## 🔌 1. Integración UPS y Alertas de Energía (NUT)
Para monitorear cortes de luz y notificar a Telegram:
*   **Librerías recomendadas:** 
    *   `nut2` o `PyNUTClient` ( wrappers de Python para comunicarse con el demonio de NUT `upsd`).
    *   `requests` (para hacer POST directos a la API de bots de Telegram).
*   **Estrategia:** Configurar `upsmon.conf` para ejecutar un script Python disparado ante eventos `ONBATT` (Batería) u `ONLINE` (Red eléctrica).

---

## 👁️ 2. Auditoría Visual de Fotos de Campo (Antes y Después)
Para auditar que se hayan cambiado correctamente los filtros mediante fotos:
*   **Librerías recomendadas:**
    *   `google-genai` (SDK oficial más reciente de Google Gemini).
    *   `Pillow` (PIL) para tratamiento y redimensionamiento de las imágenes.
*   **Estrategia:** Pasar las dos imágenes (antes y después) como inputs multimodales directos a `gemini-2.5-flash` con un prompt estructurado de auditoría visual para identificar si el recambio se realizó con éxito.

---

## 📑 3. Ingesta de Mails y Lector de Recibos (Viáticos)
Para comparar facturas de Uber/Cabify con los viáticos declarados:
*   **Librerías recomendadas:**
    *   `google-api-python-client` (para acceso seguro a Gmail API vía OAuth2).
    *   `pdfplumber` (la mejor librería de Python para extraer texto estructurado y tablas de PDFs interactivos de facturas de transporte).
*   **Estrategia:** Escanear la casilla del Supervisor buscando correos con adjuntos de recibos de Uber/Cabify, extraer el monto por expresiones regulares y cruzarlo contra el Sheets.

---

## 📈 4. Proyección Predictiva y Google Calendar
Para agendar de forma predictiva órdenes de trabajo basadas en los shots de cafetera:
*   **Librerías recomendadas:**
    *   `scikit-learn` (para modelos de regresión lineal básicos) o `pandas` para promedios móviles.
    *   `gcsa` (Google Calendar Simple API - un wrapper sumamente amigable para Python).
*   **Estrategia:** Analizar el consumo promedio diario de shots de cada máquina, estimar el día en que llegará al límite y crear automáticamente una tarea en tu calendario de Google 5 días antes de la fecha proyectada.
