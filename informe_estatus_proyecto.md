# Informe de Estatus: Proyecto Supervisor Hermes

Este documento detalla el estado actual del **Proyecto Hermes (Supervisor)**, basado en la revisión del repositorio y los archivos de configuración localizados en el directorio del proyecto `/home/cristian/Documentos/Supervisor`.

---

## 1. Resumen General del Proyecto
El **Proyecto Hermes** está diseñado bajo un paradigma de **infraestructura híbrida** para optimizar los flujos de trabajo del Supervisor de Mantenimiento de sucursales gastronómicas (especialmente enfocado en locales de *Mostaza*):
1. **Capa Orquestadora Local (Ubuntu + Antigravity):** Servidor local físico que ejecuta servicios en segundo plano para procesar la comunicación y automatizar interacciones de bajo costo (scripts de automatización, APIs locales, túneles seguros y bots de Telegram).
2. **Capa Cloud (Google Workspace):** Utiliza Google Sheets como motor de base de datos relacional y Google Drive como almacenamiento jerárquico de documentos e imágenes. NotebookLM Pro funciona como el motor RAG de conocimiento aislado por sucursal.

---

## 2. Mapa de Archivos del Proyecto
El ecosistema actual del proyecto se compone de los siguientes archivos:

*   **Documentación de Diseño y Operaciones:**
    *   `manual_operativo_supervisor.md`: Detalla la lógica de locales, sucursales y la estructura de sincronización con Drive y NotebookLM.
    *   `hermes_architecture_breakdown.md`: Desglose de arquitectura por bloques (del 1 al 8) y diseño técnico general.
*   **Scripts de Inicialización de Base de Datos y Drive (Google Apps Script):**
    *   `app_script_inicializar.js`: Estructura las pestañas de Google Sheets y precarga la información de sucursales, técnicos y umbrales.
    *   `supervisor_drive_generator.js`: Crea carpetas de forma jerárquica e idempotente en Google Drive.
*   **Automatización de NotebookLM Pro (Python + Playwright):**
    *   `notebooklm_bulk_creator.py`: Crea de forma masiva y automatizada los cuadernos en NotebookLM utilizando una sesión de Chrome.
    *   `delete_untitled.py`: Limpia los cuadernos huérfanos o sin título ("Untitled notebook").
    *   `diagnose_notebook.py`: Herramienta interna para analizar el DOM y los selectores del sitio de NotebookLM.
*   **API y Puente con Telegram (Python + Flask/FastAPI):**
    *   `server.py` (en `antigravity_api/`): Servidor FastAPI que simula la API de OpenAI y redirige las peticiones a Gemini, implementando una **identidad dual** (Asistente de Cristian vs. Supervisor de Técnicos).
    *   `app.py` (en `telegram_bridge/`): Bridge de Telegram en Flask. Recibe mensajes y notas de voz, los procesa y delega de manera asíncrona a la API.
*   **Orquestador de Despliegue Local:**
    *   `restore_telegram.sh`: Script Bash que levanta en caliente la API, el bridge, un túnel de Cloudflare, y actualiza el webhook del bot de Telegram.

---

## 3. Estatus de Funciones Aplicadas (Listas y Operativas)

### A. Estructura de Datos e Infraestructura Cloud (Bloque 1)
*   **Base de datos relacional en Google Sheets:** La base de datos está completamente modelada. El script `app_script_inicializar.js` crea correctamente todas las pestañas necesarias (`Locales`, `Tecnicos`, `Historial_Reportes`, `Alertas_Preventivas`, `Control_Auditoria`, `Conciliacion_Viaticos`, `Config_Umbrales`) y precarga los 115 locales originales y la nómina de técnicos autorizados.
*   **Jerarquía de Carpetas de Google Drive:** Automatizada a través de `supervisor_drive_generator.js`, generando carpetas siguiendo el patrón `[SIGLA SISTEMA] - NOMBRE LOCAL` de forma óptima para evitar timeouts.

### B. Automatización de Inteligencia (NotebookLM) (Bloque 7 - Parcial)
*   **Creación masiva de cuadernos:** Mediante `notebooklm_bulk_creator.py`, el sistema lee las sucursales y crea de forma automática sus cuadernos individuales en Google NotebookLM Pro, asociando la carpeta de Drive como fuente.
*   **Script de Mantenimiento:** `delete_untitled.py` automatiza la remoción de pruebas fallidas u hojas sin título generadas en el dashboard.

### C. Canal de Comunicación y API de Identidad Dual (Bloque 8 - Parcial)
*   **Detección de Audio y Texto en Telegram:** El script `app.py` recibe los mensajes de Telegram, descarga las notas de voz de los técnicos, las convierte a Base64 y las envía a la API local de forma asíncrona.
*   **Identidad Dual basada en Chat ID:** Implementada en `server.py`. Si el remitente es Cristian (`215173956`), la IA actúa como su colega Ingeniero de Software / Asistente Senior (Antigravity). Si es un técnico de la lista blanca, actúa como el "Agente Supervisor" resolutivo de fallas mecánicas.
*   **Levantamiento Automático de Infraestructura Local:** `restore_telegram.sh` limpia procesos viejos, levanta puertos locales (`8000` y `5000`), establece el túnel de Cloudflare y actualiza la URL dinámica del webhook en la API oficial de Telegram de manera automática.

---

## 4. Estatus de Funciones Pendientes (Planificadas en Arquitectura)

Analizando los códigos de producción frente al diseño de `hermes_architecture_breakdown.md`, las siguientes lógicas y módulos están **pendientes de desarrollo**:

### 🚫 Ingesta y Validación de PDFs de la PWA (Bloque 1)
*   Falta el script para recibir los PDFs generados por la PWA (con prefijo `MTZ_`), guardarlos en la carpeta específica de Drive del local y validar la identidad del emisor cruzándola con la pestaña `Tecnicos`.

### 🚫 Parser Automático de Reportes con IA (Bloque 2)
*   Falta programar el flujo de extracción que toma un archivo `MTZ_` recibido, corre *Gemini Vision API* para convertirlo a JSON e inserta los datos estructurados en la pestaña `Historial_Reportes` de Sheets.

### 🚫 Motor de Reglas y Prioridad Hídrica (Bloque 3)
*   Aunque los umbrales de PPM de agua y estado de filtros están cargados en `Config_Umbrales`, falta programar la lógica activa que evalúe si la dureza del agua excede los umbrales críticos para disparar alertas preventivas en la pestaña `Alertas_Preventivas` e ignorar temporalmente fallas menores de la cafetera.

### 🚫 Auditoría de Campo y Visión Computacional (Bloque 4)
*   Falta el desarrollo de análisis de fotos ("antes y después" del filtro / verificación de marcas y legibilidad de imágenes) para auditar automáticamente las intervenciones de campo.

### 🚫 Conciliación Financiera de Viáticos (Bloque 5)
*   Falta la lógica que lee los recibos de Uber/Cabify desde el correo y los compara automáticamente con lo declarado en Sheets bajo el concepto de viáticos.

### 🚫 Orquestación Predictiva de Mantenimiento (Bloque 6)
*   Falta la lógica matemática para proyectar el desgaste de piezas basado en la tasa de cambio del campo `Contador_Shots` y agendar órdenes preventivas automáticamente.

### 🚫 Function Calling y Lectura Programática en la API (Bloque 7 - Extensión)
*   Actualmente, el bot de Telegram responde usando conocimiento general y el prompt de sistema. Está pendiente implementar *Function Calling* en la API (`server.py`) para que el bot pueda leer carpetas de Drive, consultar la planilla de Sheets o buscar información histórica de locales de manera dinámica (`tools=[leer_drive, consultar_correo, buscar_sucursal]`).

### 🚫 Escalado y Notificaciones Asíncronas Automáticas (Bloque 8 - Alertas Activas)
*   Faltan los demonios locales en Ubuntu para auditar las demoras de los técnicos y enviar notificaciones activas de Nivel 1, 2 y 3 (avisos directos a técnicos y supervisor por retrasos o tickets críticos sin resolver).

---

## 5. Resumen de Próximos Pasos Recomendados
1.  **Prioridad 1: Extracción de PDFs (Parser de Reportes):** Codificar el parser de reportes PDF que extraiga los campos clave y los inserte en la planilla de Sheets. Esta es la base para poblar el historial de forma automática.
2.  **Prioridad 2: Function Calling (Lectura en vivo):** Dotar al agente local de herramientas para leer las filas de la sucursal directo desde Sheets para responder consultas específicas por chat.
