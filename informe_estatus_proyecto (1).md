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
    *   `restore_telegram.sh`: Script Bash que levanta en caliente la API, el bridge, un túnel de Cloudflare, y actualiza el webhook del bot de Telegram.

---

## 3. Estatus de Funciones Aplicadas (Listas y Operativas)

### A. Estructura de Datos e Infraestructura Cloud (Bloque 1)
*   **Base de datos relacional en Google Sheets:** La base de datos está completamente modelada. El script `app_script_inicializar.js` crea correctamente todas las pestañas necesarias (`Locales`, `Tecnicos`, `Historial_Reportes`, `Alertas_Preventivas`, `Control_Auditoria`, `Conciliacion_Viaticos`, `Config_Umbrales`) y precarga los 115 locales originales y la nómina de técnicos autorizados.
*   **Jerarquía de Carpetas de Google Drive:** Automatizada a través de `supervisor_drive_generator.js`, generando carpetas siguiendo el patrón `[SIGLA SISTEMA] - NOMBRE LOCAL` de forma óptima para evitar timeouts.

### B. Motor Supervisor: Parser y Reglas de Negocio (Fases 1 y 2 - Núcleo Listo)
*   **Parser Híbrido (Fase 1):** Implementado en `motor_supervisor.py`. Extrae eficientemente datos estructurados del PDF (Local, Sigla, Técnico, Ticket, PPM, Viático, Shots) utilizando expresiones regulares optimizadas y PyPDF2.
*   **Motor de Reglas y Prioridad Hídrica (Fase 2):** Implementado en `motor_supervisor.py`. Evalúa las PPM en base a la jerarquía de dureza del agua (verde/amarillo/rojo crítico) y calcula alertas de mantenimiento predictivo basad### C. Integración de Hojas de Cálculo (Fase 3 - Completado)
*   **Credenciales y acceso configurados:** Se cargó [credentials.json](file:///home/cristian/Documentos/Supervisor/credentials.json) en el proyecto y se otorgaron permisos de Editor en Google Drive a la Cuenta de Servicio.
*   **Base de datos poblada:** Se ejecutó [actualizar_locales.py](file:///home/cristian/Documentos/Supervisor/actualizar_locales.py) poblando exitosamente la pestaña `Locales_Maestro` con la nómina de locales.
*   **Pipeline de Inyección Automático:** Se conectó [motor_supervisor.py](file:///home/cristian/Documentos/Supervisor/motor_supervisor.py) con [fase3_sheets.py](file:///home/cristian/Documentos/Supervisor/fase3_sheets.py). Al procesar cualquier PDF con `procesar_reporte()`, se extraen los datos y se inyectan tanto los registros del historial de mantenimiento como las alertas automáticas de PPM y Shots en las pestañas `Historial_Mantenimiento` y `Alertas_Activas` respectivamente de manera 100% funcional.

### D. Automatización de Inteligencia (NotebookLM) (Bloque 7 - Parcial)
*   **Creación masiva de cuadernos:** Mediante `notebooklm_bulk_creator.py`, el sistema lee las sucursales y crea de forma automática sus cuadernos individuales en Google NotebookLM Pro, asociando la carpeta de Drive como fuente.
*   **Script de Mantenimiento:** `delete_untitled.py` automatiza la remoción de pruebas fallidas u hojas sin título generadas en el dashboard.

### E. Canal de Comunicación y API de Identidad Dual (Bloque 8 - Parcial)
*   **Detección de Audio y Texto en Telegram:** El script `app.py` recibe los mensajes de Telegram, descarga las notas de voz de los técnicos, las convierte a Base64 y las envía a la API local de forma asíncrona.
*   **Identidad Dual basada en Chat ID:** Implementada en `server.py`. Si el remitente es Cristian (`215173956`), la IA actúa como su colega Ingeniero de Software / Asistente Senior (Antigravity). Si es un técnico de la lista blanca, actúa como el "Agente Supervisor" resolutivo de fallas mecánicas.
*   **Levantamiento Automático de Infraestructura Local:** `restore_telegram.sh` limpia procesos viejos, levanta puertos locales (`8000` y `5000`), establece el túnel de Cloudflare y actualiza la URL dinámica del webhook en la API oficial de Telegram de manera automática.

---

## 4. Estatus de Funciones Pendientes (Planificadas en Arquitectura)

Analizando los códigos de producción frente al diseño de `hermes_architecture_breakdown.md`, las siguientes lógicas y módulos están **pendientes de desarrollo**:

### 🚫 Integración de Ingesta y Validación de PDFs de la PWA (Bloque 1)
*   Falta el script/trigger para recibir los PDFs generados por la PWA (con prefijo `MTZ_`), guardarlos en la carpeta específica de Drive del local y validar la identidad del emisor cruzándola con la pestaña `Tecnicos`. El motor para procesar estos archivos y volcar los datos ya está integrado y funcional.

### 🚫 Auditoría de Campo y Visión Computacional (Bloque 4)
*   Falta el desarrollo de análisis de fotos ("antes y después" del filtro / verificación de marcas y legibilidad de imágenes) para auditar automáticamente las intervenciones de campo.

### 🚫 Conciliación Financiera de Viáticos (Bloque 5)
*   Falta la lógica que lee los recibos de Uber/Cabify desde el correo y los compara automáticamente con lo declarado en Sheets bajo el concepto de viáticos.

### 🚫 Orquestación Predictiva de Mantenimiento por Shots (Bloque 6 - Integración con Calendario)
*   Falta la automatización para proyectar matemáticamente la fecha de desgaste y agendar órdenes preventivas (OTs) en el calendario 5 días antes de alcanzar los 150.000 shots.

### 🚫 Function Calling y Lectura Programática en la API (Bloque 7 - Extensión)
*   Actualmente, el bot de Telegram responde usando conocimiento general y el prompt de sistema. Está pendiente implementar *Function Calling* en la API (`server.py`) para que el bot pueda leer carpetas de Drive, consultar la planilla de Sheets o buscar información histórica de locales de manera dinámica (`tools=[leer_drive, consultar_correo, buscar_sucursal]`).

### 🚫 Escalado y Notificaciones Asíncronas Automáticas (Bloque 8 - Alertas Activas)
*   Faltan los demonios locales en Ubuntu para auditar las demoras de los técnicos y enviar notificaciones activas de Nivel 1, 2 y 3 (avisos directos a técnicos y supervisor por retrasos o tickets críticos sin resolver).

---

## 5. Resumen de Próximos Pasos Recomendados
1.  **Prioridad 1: Pipeline de Ingesta Completo (PWA):** Conectar la carga de PDFs de la PWA con la llamada automática de `procesar_reporte` en [motor_supervisor.py](file:///home/cristian/Documentos/Supervisor/motor_supervisor.py) para que funcione en tiempo real sin intervención manual.
2.  **Prioridad 2: Function Calling en la API:** Vincular las herramientas de lectura de Sheets y Drive en la API local (`server.py`) para dar acceso en tiempo real a los datos al bot de Telegram.
3.  **Prioridad 3: Auditoría y Viáticos:** Continuar con los bloques de visión computacional y conciliación financiera de recibos de transporte.
