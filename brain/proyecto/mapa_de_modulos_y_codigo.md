# Mapa de Módulos y Arquitectura del Sistema Supervisor (Hermes)

Este documento describe la arquitectura de software actualizada del **Proyecto Supervisor (Hermes)**, detallando la función de cada módulo de código Python en producción.

---

## 1. Agente e Interfaz de Telegram: `userbot_supervisor.py`
Es la interfaz principal de interacción y control ejecutada como servicio systemd (`supervisor-userbot.service`).
- **Ingesta de PDFs:** Intercepta la subida de informes técnicos PDF en grupos y privado, ejecutando el procesamiento en segundo plano e interviniendo con una respuesta reactiva de recepción exitosa: `✅ Reporte procesado exitosamente...`.
- **Clasificación Interactiva:** Si un archivo es ambiguo, consulta en privado a Cristian mediante comandos `/local_...` para clasificarlo manualmente.
- **Chat Privado Inteligente:** Atiende las consultas de Cristian conectándose al motor de razonamiento `agentic_loop.py`.
- **Optimización de Recursos:** No procesa ni descarga fotos ni archivos de video, enfocando su cómputo en estabilidad y velocidad.

---

## 2. Motor de Razonamiento Intuitivo: `agentic_loop.py`
El cerebro inteligente de Hermes que orquesta el análisis utilizando Gemini (`gemini-2.5-flash`) y Groq (`llama-3.3-70b-versatile`) como fallback.
- **`tool_buscar_local`:** Consulta datos maestros y direcciones de las sucursales.
- **`tool_buscar_pendientes`:** Revisa incidencias pendientes por local.
- **`tool_buscar_manuales` / `tool_consultar_error`:** Busca soluciones técnicas en la base estructurada de manuales de equipos (Cimbali, Nieco, Melitta, Frymaster, etc.).
- **Perfiles y Few-Shot:** Aplica directrices de tono, estilo y correcciones semánticas guardadas dinámicamente.

---

## 3. Ingesta y Extracción de Datos
- **`ingestor_automatico.py`:** Revisa periódicamente correos entrantes de Gmail con PDFs de intervenciones técnicas (`MTZ_...`).
- **`motor_supervisor.py`:** Extrae texto crudo del PDF y aplica expresiones regulares y análisis heurístico para identificar la Sigla del local, técnico, tickets, shots del molino, ppm de agua, etc.
- **`ingestor_formulario.py`:** Se conecta a Google Forms para incorporar reportes ingresados por formulario web.

---

## 4. Alertas de Tickets y Salidas de Datos (Data Sinks)
- **`motor_tickets_mostaza.py`:** Consulta la API de tickets ERP de Mostaza cada 10 minutos y envía notificaciones de tickets nuevos al grupo de Telegram.
- **`fase3_sheets.py`:** Conecta con Google Sheets API y escribe una nueva fila en "La Sábana" cada vez que un reporte es procesado con éxito.
- **`archivador_drive.py`:** Respalda el PDF original en la carpeta específica del local en Google Drive.
- **`notificador_telegram.py`:** Módulo central de envío unificado de alertas y avisos por Telegram.

---

## 5. Reportes Automáticos de Salud y Calidad (Cron Jobs)
- **`reporte_sistema.py`:** Envía una ficha técnica diaria (8:15 AM) a Cristian sobre el estado del servidor (Uptime, CPU, RAM, espacio libre en disco).
- **`agente_qa_wiki.py`:** Audita semanalmente (Viernes 9:00 AM) la calidad de los manuales y soluciones almacenados.
- **`reporte_errores_semanal.py`:** Envía un informe semanal (Lunes 9:00 AM) con el balance de errores de procesamiento.

---

## 6. Base de Conocimiento y Resguardo Local
- **`gestion_locales.py`:** Mantiene los archivos Markdown de memoria de cada sucursal en `brain/locales/`.
- **`base_errores.json`:** Base de conocimientos JSON estructurada con manuales técnicos, procedimientos de seguridad y códigos de error limpios.
