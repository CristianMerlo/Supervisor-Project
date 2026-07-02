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
    *   `informe_estatus_proyecto.md`: (Este archivo) Reporte de situación actual y mapa de tareas del proyecto.
*   **Núcleo de Procesamiento y Reglas de Negocio:**
    *   `motor_supervisor.py`: Contiene el parser híbrido por expresiones regulares (Fase 1) y el motor de evaluación de reglas de negocio para dureza de agua y mantenimiento predictivo (Fase 2).
*   **Integración con Hojas de Cálculo (Google Sheets):**
    *   `actualizar_locales.py`: Script para cargar y sobrescribir la base de datos maestra de locales (151 sucursales mapeadas en detalle) en la hoja de cálculo.
    *   `fase3_sheets.py`: Módulo de integración que vuelca reportes de campo en `Historial_Mantenimiento` e inyecta incidentes en `Alertas_Activas`.
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
    *   `restore_telegram.sh`: Script Bash que levanta en caliente la API, el bridge, un túnel de Cloudflare, y actualiza ## 3. Estatus de Funciones Aplicadas (Listas y Operativas)

### A. Estructura de Datos e Infraestructura Cloud (Bloque 1)
*   **Base de datos relacional en Google Sheets:** La base de datos está completamente modelada. El script `app_script_inicializar.js` crea correctamente todas las pestañas necesarias (`Locales`, `Tecnicos`, `Historial_Reportes`, `Alertas_Preventivas`, `Control_Auditoria`, `Conciliacion_Viaticos`, `Config_Umbrales`) y precarga los 115 locales originales y la nómina de técnicos autorizados.
*   **Jerarquía de Carpetas de Google Drive:** Automatizada a través de `supervisor_drive_generator.js`, generando carpetas siguiendo el patrón `[SIGLA SISTEMA] - NOMBRE LOCAL` de forma óptima para evitar timeouts.

### B. Motor Supervisor: Parser y Reglas de Negocio (Fases 1 y 2 - Núcleo Listo)
*   **Parser Híbrido (Fase 1):** Implementado en [motor_supervisor.py](file:///home/cristian/Documentos/Supervisor/motor_supervisor.py). Extrae eficientemente datos estructurados del PDF (Local, Sigla, Técnico, Ticket, PPM, Viático, Shots) utilizando expresiones regulares optimizadas y PyPDF2.
*   **Motor de Reglas y Prioridad Hídrica (Fase 2):** Implementado en [motor_supervisor.py](file:///home/cristian/Documentos/Supervisor/motor_supervisor.py). Evalúa las PPM en base a la jerarquía de dureza del agua (verde/amarillo/rojo crítico) y calcula alertas de mantenimiento predictivo basadas en umbrales de negocio (como caldera o desgaste por shots).

### C. Integración de Hojas de Cálculo (Fase 3 - Completado)
*   **Credenciales y acceso configurados:** Se cargó [credentials.json](file:///home/cristian/Documentos/Supervisor/credentials.json) en el proyecto y se otorgaron permisos de Editor en Google Drive a la Cuenta de Servicio.
*   **Base de datos poblada:** Se ejecutó [actualizar_locales.py](file:///home/cristian/Documentos/Supervisor/actualizar_locales.py) poblando exitosamente la pestaña `Locales_Maestro` con la nómina de locales.
*   **Pipeline de Inyección:** Se implementó [fase3_sheets.py](file:///home/cristian/Documentos/Supervisor/fase3_sheets.py) para inyectar los datos en las pestañas `Historial_Mantenimiento` y `Alertas_Activas`.

### D. Pipeline de Ingesta Automática (Paso A - Completado)
*   **Ingestión por Gmail (IMAP)**: [ingestor_automatico.py](file:///home/cristian/Documentos/Supervisor/ingestor_automatico.py) conecta de forma segura a Gmail (usando la contraseña de aplicación de 16 caracteres en `.env`), descarga archivos adjuntos `MTZ_*.pdf` de correos no leídos y los coloca en `entrantes/`.
*   **Ingestión por Telegram Webhook**: El bot [app.py](file:///home/cristian/Documentos/Supervisor/telegram_bridge/app.py) detecta archivos PDF de reportes enviados por técnicos autorizados y los deposita directamente en la cola `entrantes/`.
*   **Ejecución Programada (Cron)**: Se configuró un cron job en el sistema local que corre cada 5 minutos para ejecutar [ingestor_automatico.py](file:///home/cristian/Documentos/Supervisor/ingestor_automatico.py). El script evalúa los reportes, los inyecta de forma única (con la inyección redundante de [motor_supervisor.py](file:///home/cristian/Documentos/Supervisor/motor_supervisor.py) removida) en Sheets y los archiva en `procesados/` o `errores/`.
*   **Aislamiento y Seguridad**: Todo se maneja de forma configurable mediante variables locales en el archivo [.env](file:///home/cristian/Documentos/Supervisor/.env).

### E. Automatización de Inteligencia (NotebookLM) (Bloque 7 - Parcial)
*   **Creación masiva de cuadernos:** Mediante `notebooklm_bulk_creator.py`, el sistema lee las sucursales y crea de forma automática sus cuadernos individuales en Google NotebookLM Pro, asociando la carpeta de Drive como fuente.
*   **Script de Mantenimiento:** `delete_untitled.py` automatiza la remoción de pruebas fallidas u hojas sin título generadas en el dashboard.

### F. Canal de Comunicación y API de Identidad Dual (Bloque 8 - Parcial)
*   **Detección de Audio y Texto en Telegram:** El script [app.py](file:///home/cristian/Documentos/Supervisor/telegram_bridge/app.py) recibe los mensajes de Telegram, descarga las notas de voz de los técnicos, las convierte a Base64 y las envía a la API local de forma asíncrona.
*   **Identidad Dual basada en Chat ID:** Implementada en `server.py` de la API. Si el remitente es Cristian (`215173956`), la IA actúa como su colega/asistente de software (Antigravity). Si es un técnico autorizado, actúa como el "Agente Supervisor" resolutivo de fallas.
*   **Levantamiento Automático y Robustez**: [restore_telegram.sh](file:///home/cristian/Documentos/Supervisor/restore_telegram.sh) limpia procesos anteriores, levanta el puerto de la API (`8000`), el puerto del bridge (`5000`), inicializa el túnel seguro de Cloudflare, espera 30 segundos para la propagación DNS y re-registra dinámicamente el webhook en la API oficial de Telegram.

### G. Archivo Automático y Autolimpieza en Google Drive (Paso B.1 - Completado)
*   **Archivo Inteligente por Sigla:** Implementado en [archivador_drive.py](file:///home/cristian/Documentos/Supervisor/archivador_drive.py). El sistema analiza la sigla de la sucursal (ej. `FVDP`), localiza su carpeta en Google Drive y deposita el PDF directamente en su subcarpeta `Reportes`.
*   **Bypass de Límite de Cuota (Web App)**: Se solucionó el problema de la cuota de almacenamiento de 0 bytes de las Cuentas de Servicio en Drives personales. Desarrollamos y desplegamos una Web App de Google Apps Script (`supervisor_uploader_webapp.js` / Versión 2 de la implementación) que corre bajo el espacio de Cristian y recibe cargas directas vía HTTPS POST desde Python.
*   **Autolimpieza e Integración**: El orquestador [ingestor_automatico.py](file:///home/cristian/Documentos/Supervisor/ingestor_automatico.py) ejecuta la carga en Drive tras la inyección exitosa en Sheets y elimina inmediatamente el archivo local para preservar el disco del servidor. Si hay algún error, el archivo se resguarda en `errores/`.

### H. Function Calling y Lectura Programática en la API (Bloque 7 - Completado)
*   **Conexión Dinámica con Sheets (Gemini Tools)**: Se integró el soporte nativo de Function Calling en la API local (`server.py`). Al consultar sobre el estado de una sucursal, mantenimientos o alertas, la IA ejecuta automáticamente búsquedas y lecturas dinámicas sobre la base de datos de Sheets (`Locales_Maestro`, `Historial_Mantenimiento`, `Alertas_Activas`).
*   **Ejecución Transparente y Asíncrona**: Habilitado el modo `enable_automatic_function_calling=True` en las sesiones de chat de la API. El bot resuelve la petición por detrás de escena y responde con los datos duros reales formateados.

### I. Motor de Conocimiento RAG y Bóveda de Obsidian (Completado)
*   **Integración Local-First:** Se implementó `obsidian_bridge.py`, que actúa como buscador semántico sobre la bóveda local de Obsidian (`brain/`).
*   **Conversión de PDFs y OCR Automático:** Se desarrolló `convertir_pdfs_a_md.py` para transformar manuales técnicos PDF a formato Markdown. Además, el bot transcribe fotos (ej. diagramas de error) enviadas por Telegram a texto utilizando la API local.
*   **Contexto Extendido:** El motor RAG fue configurado para extraer hasta 15,000 caracteres preservando el formato de tablas y enviarlo a Gemini 2.5 Flash, logrando cero alucinaciones en diagnósticos complejos como los errores de La Cimbali.
*   **Automatización de Mantenimiento de la Bóveda:** Tarea programada en cron que corre diariamente a las 02:00 AM para ingestar y convertir nuevos PDFs a la base de conocimientos, así como conversión en tiempo real al subir documentos por Telegram.

### J. Optimización de Infraestructura Local (Completado)
*   **Perfil de Bajo Consumo para Chrome:** Se configuró el daemon de WhatsApp Web (`reiniciar_chrome.sh`) con banderas estrictas (`--disable-gpu`, `--disable-extensions`, `--mute-audio`, `--disable-sync`) para reducir radicalmente el consumo de RAM en Ubuntu.

---

## 4. Estatus de Funciones Pendientes (Planificadas en Arquitectura)

Analizando los códigos de producción frente al diseño de `hermes_architecture_breakdown.md`, las siguientes lógicas y módulos están **pendientes de desarrollo**:

### 🚫 Validación de Emisores (Bloque 1)
*   Falta validar el remitente del correo o el Chat ID del técnico emisor cruzándolo con la nómina de la pestaña `Tecnicos` antes de autorizar la ingesta del reporte.

### 🚫 Auditoría de Campo y Visión Computacional (Bloque 4)
*   Falta el desarrollo de análisis de fotos ("antes y después" del filtro / verificación de marcas y legibilidad de imágenes) para auditar automáticamente las intervenciones de campo.

### 🚫 Conciliación Financiera de Viáticos (Bloque 5)
*   Falta la lógica que lee los recibos de Uber/Cabify desde el correo y los compara automáticamente con lo declarado en Sheets bajo el concepto de viáticos.

### 🚫 Orquestación Predictiva de Mantenimiento por Shots (Bloque 6 - Integración con Calendario)
*   Falta la automatización para proyectar matemáticamente la fecha de desgaste y agendar órdenes preventivas (OTs) en el calendario 5 días antes de alcanzar los 150.000 shots.

### 🚫 Escalado y Notificaciones Asíncronas Automáticas (Bloque 8 - Alertas Activas)
*   Faltan los demonios locales en Ubuntu para auditar las demoras de los técnicos y enviar notificaciones activas de Nivel 1, 2 y 3 (avisos directos a técnicos y supervisor por retrasos o tickets críticos sin resolver).

---

## 5. Resumen de Próximos Pasos Recomendados
1.  **Prioridad 1: Validación de Emisores:** Implementar la validación de Chat ID y correo electrónico contra la lista oficial de técnicos habilitados.
2.  **Prioridad 2: Auditoría y Viáticos:** Desarrollar los bloques de visión computacional y conciliación de viáticos.
3.  **Prioridad 3: Orquestación Predictiva:** Programar la proyección por shots y la integración de agendamiento en calendario.

---

## 6. Últimas Actualizaciones de Arquitectura (Integradas)
*   **Módulo Asistente de Correos**: Desarrollado `asistente_correos.py` con integración IMAP y procesamiento de IA (Gemini Flash) para leer, resumir y almacenar correos informativos en `supervisor_local.db` y Google Drive. Se sumaron las capacidades `tool_consultar_correos` y `tool_redactar_correo_borrador` a Hermes.
*   **Enrutamiento Inteligente en Telegram**: Se modificó la infraestructura de notificaciones y el userbot para rutear alertas directamente al chat privado del supervisor (evitando fugas de privacidad en el grupo general).
*   **Motor de Extracción (Self-Healing)**: El `motor_extraccion_errores.py` se actualizó para utilizar el agente local Qwen 2.5 (0.5b), reduciendo drásticamente el consumo de recursos de Ubuntu. Se agregó lógica de recuperación automática (auto-reinicio de Ollama si crashea) y control de estado para evitar reprocesar manuales.
*   **Estabilización del Cerebro Agentic Loop**: Se implementó un "limitador de contexto" en `agentic_loop.py` para prevenir excesos de cuota en Groq (Error 413 por historiales inmensos). Además, se programó un recuperador de alucinaciones (Error 400) que intercepta errores de sintaxis XML al buscar locales y fuerza la ejecución de las herramientas.
*   **Unificación de Base de Datos Maestro (Julio 2026)**: Unificadas de forma absoluta todas las conexiones de base de datos relacional de la aplicación hacia el archivo maestro consolidado en `/home/cristian/Documentos/Supervisor/supervisor_local.db`. Se fusionaron las tablas del repositorio de desarrollo y producción y se migraron con éxito los datos de memoria, correos e historial de soluciones.
*   **Silenciador Anti-Spam y Control de Colisiones (WhatsApp)**: 
    - Implementamos una lógica de archivo lock (`/tmp/whatsapp_alert.lock`) en `motor_whatsapp_web.py` que silencia alertas repetitivas de conexión por 4 horas tras enviar el primer aviso.
    - Se resolvió un conflicto de colisión de puertos (`9222` de Chrome) desactivando la ejecución del motor de WhatsApp de la tarea periódica (cron) de `ingestor_automatico.py` y delegando esta responsabilidad exclusivamente al daemon continuo de sistema `whatsapp-bridge.service`.
    - Ajustamos la frecuencia de revisión del servicio a un periodo más relajado de 2 minutos (`RestartSec=120`) para reducir la carga de CPU en el servidor de producción.
*   **Estabilización del Levantamiento de Chrome (Wayland/setsid)**: Rediseñamos `reiniciar_chrome.sh` para cerrar de forma agresiva instancias antiguas (`killall -9 chrome`), eliminar bloqueos huérfanos (`SingletonLock`), exportar variables de pantalla (`WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`) compatibles con cron y usar `setsid` con redirección de entrada `< /dev/null` para evitar cierres prematuros del navegador.
*   **Procesamiento Silencioso de Videos en Grupos**: Modificamos el manejador de video en `userbot_supervisor.py` para anular las respuestas e interactividad públicas de descarga y diagnóstico dentro del grupo de mantenimiento técnico. Los análisis se realizan de forma invisible y sus reportes/errores técnicos se enrutan de manera estrictamente privada al chat de Cristian para su aprobación.
*   **Búsqueda Inteligente de Locales y Sugerencias (Criterio Amplio)**: 
    - Desarrollamos un cargador del archivo de sucursales `/home/cristian/Documentos/Supervisor/locales.csv` que mapea de forma dual la **Sigla Sistema (ej: `FSJU`)** y la **Sigla Tickets (ej: `FCSJ3`)** hacia el local oficial.
    - Corregimos un error estructural en la detección de palabras clave en el userbot (`any(p in locales_conocidos)`) para permitir el matching correcto de siglas en el chat.
    - Agregamos un motor de tolerancia a errores tipográficos que sugiere nombres e interactúa con el técnico en caso de que escriba un nombre de local similar o incompleto.
*   **Watchdog de Inactividad en Flujos Interactivos**: Implementamos un supervisor de estados temporales (`esperar_respuesta_timeout`) que vigila los flujos de confirmación de local en Telegram. Si un técnico sube un archivo y no responde a la pregunta de confirmación en 10 minutos, se cancela la sesión interactiva y se notifica de forma privada a Cristian con los metadatos recopilados para su posterior revisión.
