# Conciencia y Arquitectura del Proyecto (Versión 2.0)

Este documento centraliza el estado actual, las herramientas y la arquitectura del ecosistema del Supervisor de Mantenimiento, reemplazando las infraestructuras heredadas (ej. WhatsApp).

## 1. El Bot de Telegram (Hermes / Userbot)
La comunicación se realiza exclusivamente a través de **Telegram**, utilizando la librería `Telethon` configurada como un *Userbot* en la cuenta del usuario.
- **`userbot_supervisor.py`**: Es el cerebro de las telecomunicaciones. Escucha pasivamente los chats y grupos configurados en `.env` (ALLOWED_CHAT_IDS) en busca de problemas técnicos.
- Expone una **API HTTP local** en `127.0.0.1:8088/notify` que permite a cualquier script del sistema enviar notificaciones proactivas al usuario (cronjobs, alarmas, etc.).

## 2. Motor de Razonamiento (Agentic Loop)
Cuando un técnico reporta una falla, el mensaje es delegado a **`agentic_loop.py`**, un orquestador inteligente que emplea la API de **Groq** con modelos veloces y avanzados (ej. LLaMA 3.3).
- **Tool Calling:** El loop evalúa la consulta y decide qué herramientas (funciones en Python) llamar:
  - `tool_buscar_local`: Busca datos en la base `supervisor_local.db`.
  - `tool_consultar_error`: Busca en el índice estático `base_errores.json`.
  - `tool_generar_excel_kpi`: Accede a Google Sheets y genera reportes en Excel.
  - `tool_proponer_solucion`: Detecta cuando el técnico resolvió el problema y pide aprobación al Supervisor.

## 3. Inteligencia Documental (Gemini File API)
Se reemplazó el antiguo LLM local (Ollama/Qwen 0.5b) por la API nativa de **Gemini 2.5 Flash** para ganar precisión, velocidad y una ventana de contexto enorme.
- **Extracción de Errores (`motor_extraccion_errores.py`)**: Corre cada madrugada a las 04:00 AM. Ingiere los 16+ manuales completos y puebla el `base_errores.json`.
- **RAG Nativo / Fallback tipo NotebookLM (`gestor_documentos_gemini.py`)**: Sincroniza los manuales markdown a la nube de Gemini. Si `tool_consultar_error` no halla respuesta, se dispara `tool_consultar_manuales_profundo`, el cual interroga directamente al clúster de archivos de Gemini para lograr un razonamiento deductivo profundo (comportamiento idéntico a NotebookLM).

## 4. Ecosistema de PWA's y GitHub Pages
El sistema administra aplicaciones web externas (Buscador de Locales y Generador de Informes) alojadas en GitHub Pages.
- **La Sábana**: El maestro de datos es un Google Sheet actualizado periódicamente.
- **Auditor PWA (`auditor_pwa.py`)**: Un crontab se ejecuta todos los lunes a las 09:00 AM. 
  1. Descarga el JSON de *La Sábana*.
  2. Compara los datos con los repositorios locales (`localizador-de-locales` y `Generador_de_Informes_online`).
  3. Reemplaza las bases de datos de JavaScript en ambas aplicaciones si encuentra diferencias.
  4. Realiza `git commit` y `git push` para desplegar la información actualizada en vivo.
  5. Reporta discrepancias al Supervisor vía Telegram.

## Resumen de la "Esencia del Proyecto"
El ecosistema es ahora un ensamblaje modular, asíncrono y proactivo. Conecta una interfaz humana natural (Telegram) con un motor de razonamiento (Groq), respaldado por bases de datos robustas (SQLite, Google Sheets) e IA documental profunda (Gemini), siendo además capaz de operar repositorios web para uso generalizado de los técnicos en calle.
