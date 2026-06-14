# Mapa de Módulos y Código del Sistema Supervisor

Este documento describe la arquitectura de software del **Proyecto Supervisor (Hermes)**, detallando la función de cada módulo principal de código Python.

## 1. El Orquestador Central: `ingestor_automatico.py`
Es el corazón del sistema. Se ejecuta automáticamente cada 5 minutos mediante un Cron Job en el servidor.
**Responsabilidades:**
- **Descarga IMAP:** Se conecta a Gmail y descarga cualquier correo no leído que contenga archivos adjuntos que empiecen con `MTZ_` y sean `.pdf`.
- **Invocación de Ingesta:** Llama a los motores de procesamiento para que analicen los PDFs descargados en la carpeta `entrantes/`.
- **Invocación de WhatsApp:** Cada 20 minutos (minutos 0, 20, 40), ejecuta `motor_whatsapp_web.py` para procesar mensajes de WhatsApp no leídos.
- **Invocación de Formularios:** Llama a `ingestor_formulario.py` para verificar si hay nuevas respuestas en el Google Form de Mantenimiento.
- **Ruteo Post-Procesamiento:** Luego de procesar un PDF:
  - Manda los datos a Google Sheets (`fase3_sheets.py`).
  - Respalda el PDF original en la nube (`archivador_drive.py`).
  - Actualiza el modelo Markdown local del local (`gestion_locales.py`).
  - **Tiempo Real:** Lanza `actualizar_notebook_local.py` para impactar la actualización en NotebookLM instantáneamente.

## 2. Los Motores de Extracción de Datos
- **`motor_supervisor.py`:** El cerebro analítico. Extrae texto crudo del PDF y aplica expresiones regulares y análisis heurístico para identificar la Sigla del local, técnico, tickets, shots del molino, ppm de agua, etc. También evalúa el estado general de las alarmas del sistema y lanza alertas a Telegram si hay problemas críticos.
- **`ingestor_formulario.py`:** Se conecta a la API de Google Forms para traer reportes ingresados manualmente vía web, parseándolos e inyectándolos en el mismo flujo de datos que los PDFs.

## 3. Puentes de Comunicación
- **`userbot_supervisor.py`:** Es la cuenta automatizada de Telegram (Userbot) que permite la ingesta interactiva de reportes que no cumplen con los formatos estandarizados. Si el usuario manda una foto, el bot le hace preguntas interactivas para clasificarla (¿Es manual? ¿Es informe? ¿De qué local?) y la enruta a `entrantes/`. También maneja el envío de alertas operativas al jefe.
- **`motor_whatsapp_web.py`:** Utiliza automatización de navegador (Selenium/Playwright) para barrer conversaciones fijadas o específicas en WhatsApp Web, detectando y descargando documentos para que el ingestor los procese.

## 4. Gestión de Base de Conocimiento (RAG y NotebookLM)
- **`gestion_locales.py`:** Crea y actualiza los archivos `.md` de cada local dentro de la carpeta `brain/locales/`. Estos archivos `.md` son el cerebro local de la Inteligencia Artificial Hermes, actuando como Memoria a Largo Plazo.
- **`actualizar_notebook_local.py`:** Script ultra rápido que sincroniza un único archivo Markdown a la cuenta Pro de NotebookLM usando el CLI `nlm`. Se encarga de agregar la fecha al título (ej: `FVDP_20260614.md`) para crear un historial apilado de cada visita sin borrar los registros anteriores.
- **`sincronizar_notebooklm.py` / `completar_notebooks_faltantes.py`:** Scripts de mantenimiento masivo para asegurar que todos los locales existan como cuadernos independientes en la nube de Google.

## 5. Salidas de Datos (Data Sinks)
- **`fase3_sheets.py`:** Conecta con Google Sheets API y escribe una nueva fila en "La Sábana" cada vez que un reporte es procesado con éxito, garantizando visibilidad tabular para la gerencia.
- **`archivador_drive.py`:** Se asegura de que el PDF original, una vez procesado, no se pierda. Lo sube a la carpeta específica del local en Google Drive y lo mueve a `brain/locales/PDFs_Originales/` de manera local para un doble respaldo físico y en la nube.
