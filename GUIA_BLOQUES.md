# Guía de Implementación: Hermes Headless Supervisor

Este documento funciona como un índice y guía descriptiva de todos los bloques que componen el proyecto "Supervisor". A medida que se agreguen nuevos bloques, esta guía se irá actualizando para documentar las acciones y responsabilidades de cada parte del sistema.

---

## 📁 Bloque 01: Inicialización de Arquitectura
**Ruta:** `bloque_01_inicializacion/`

Este es el bloque fundacional del proyecto. Contiene un script en Python (`setup_hermes.py`) diseñado para ser ejecutado de forma autónoma en el entorno destino (Ubuntu). 

**Acciones que implementa:**
- **Creación de la estructura del proyecto:** Genera automáticamente la carpeta raíz `hermes-headless-supervisor/` junto con sus subdirectorios críticos (`.antigravity/`, `config/`, `src/`, `logs/`).
- **Automatización Nativa:** Genera `automation_config.json`, donde se definen las tareas cronometradas para que el Agente Antigravity las ejecute de forma nativa (por ejemplo, escanear correos cada 2 horas y revisar Telegram cada hora).
- **Configuración Dinámica:** Establece un archivo `app_config.json` pre-poblado con los datos del equipo a supervisar y las variables de configuración del proyecto.
- **Preparación de Scripts Core:** Escribe las plantillas iniciales de los conectores críticos sin necesidad de escribirlos a mano en el destino:
  - `sheets_connector.py`: Conector Headless para interactuar con la API de Google Sheets y volcar datos.
  - `mail_monitor.py`: Monitor automatizado de Outlook Exchange.
  - `telegram_monitor.py`: Auditor automatizado de Telegram.
- **Seguridad:** Crea placeholders y plantillas para las variables de entorno (`secrets.env`) y credenciales de Google (`google_credentials.json`), asegurando que las llaves privadas se manejen de forma local y segura.

---

## 📁 Bloque 02: Análisis de Viabilidad e Historial
**Ruta:** `bloque_02_analisis_viabilidad/`

Este bloque es un documento conceptual y de auditoría de arquitectura (`analisis_riesgos_y_viabilidad.md`). Almacena la historia de las decisiones técnicas y actúa como salvaguarda antes de escribir código pesado.

**Acciones que implementa (o previene):**
- **Registro del "Núcleo Inmutable":** Establece que el orquestador será en Python (Docker/Ubuntu), asincrónico, conmutando APIs externas y usando Telegram como única interfaz.
- **Auditoría de Riesgos (Anti-Patrones):** Documenta las 3 razones principales por las que el sistema colapsaría si se implementa mal (bloqueo de hilos asincrónicos, desborde de logs en SSD de 240GB y pérdida de contexto en failovers).
- **Control de Decisiones Descartadas:** Registra por qué no se usa procesamiento LLM Local (Ollama) ni interfaces nativas en el servidor, evitando repetición de errores futuros.
- **RFI (Request for Information):** Deja planteadas las 4 preguntas críticas de contingencia (Prioridad de APIs, Persistencia de contexto en SQLite, Destino de la data de mantenimiento, y el estado actual del bot) necesarias para generar la lógica de conmutación.

## 📁 Bloque 03: Auditoría y Plano Workspace (PIT-V3)
**Ruta:** `bloque_03_auditoria_y_plano_workspace/`

Este bloque contiene el análisis y la documentación de una variante del proyecto pensada íntegramente dentro del ecosistema de Google Workspace (utilizando Apps Script, Google Chat, Drive y Google Sheets).

**Acciones que implementa (o previene):**
- **Registro de Evolución (Por qué Google Chat):** Documenta las razones operativas por las cuales, en ese enfoque, se eligió Google Chat frente a Telegram o Gmail.
- **Prevención de Limitaciones (Quotas):** Actúa como salvaguarda al exponer las restricciones reales de Google Workspace (límites de 90 min de ejecución diaria en Apps Script y las restricciones de las cuentas gratuitas para invocar Gems en chats).
- **Blueprint de Arquitectura en Apps Script:** Proporciona un árbol de directorios de referencia (`hermes-workspace-core`) estructurado profesionalmente para Google Apps Script (`Code.js`, `automation.js`, `webhookHandler.js`).
- **Mecanismos de Resiliencia:** Incluye el código base JavaScript (`installHermesTriggers`) para la creación y limpieza segura de Triggers temporales, previniendo tareas duplicadas y manejando reintentos (Exponential Backoff) con logs en Sheets.

## 📁 Bloque 04: Auditoría VPS y Arquitectura Docker (NEXUS)
**Ruta:** `bloque_04_auditoria_vps_docker/`

Este bloque plantea la variante del proyecto (OP_HERMES_NEXUS) diseñada específicamente para un servidor VPS local en Argentina con recursos limitados (4GB de RAM), apoyándose en Docker, Celery y Redis para orquestar la carga.

**Acciones que implementa (o previene):**
- **Prevención de Out Of Memory (OOM):** Documenta por qué correr múltiples procesos asincrónicos simultáneos ahogará un VPS chico, prescribiendo el uso de Redis Queue y límites de memoria estrictos en `docker-compose.yml`.
- **Mitigación de Race Conditions en Git:** Propone un script (`github_dashboard_updater.py`) que previene y elimina bloqueos de archivo (`.git/index.lock`) al momento de hacer un Git Push automático hacia el dashboard.
- **Evolución Tecnológica y Soberanía:** Explica el descarte de soluciones internacionales y locales pesadas (Ollama, Hostinger, Termux Android) en favor de un VPS liviano delegando la inferencia de IA en APIs rápidas de terceros (Groq / OpenRouter).

## 📁 Bloque 05: Orquestador Local y Gestión UPS (M700)
**Ruta:** `bloque_05_orquestador_local_ups/`

Este bloque contiene el análisis de la arquitectura final y más robusta del proyecto (`hermes-core-orchestrator`), diseñada para ejecutarse físicamente en una Mini PC local (Lenovo M700) para evadir las limitaciones de ejecución en la nube.

**Acciones que implementa (o previene):**
- **Arquitectura Local Resiliente:** Establece la base de un servidor físico en Ubuntu que utiliza bases de datos vectoriales (`pgvector`) para mantener la "memoria" del Agente aislada por cada uno de los 100 locales comerciales.
- **Protocolo de Energía (UPS):** Incorpora la lógica para un script crítico (`apcupsd_hook.sh`) que interactúa con la UPS por USB. Si hay corte de luz y la batería baja del 15%, apaga los contenedores Docker de forma segura y apaga la máquina (`shutdown -h now`) para no corromper la base de datos.
- **Jerarquía Hídrica:** Documenta la regla de negocio central: Si el agente detecta "PPM > 200" o un fallo en el ablandador de agua tras leer los PDFs de los técnicos, dispara una alerta crítica forzada (Estado ROJO).
- **Control de Concurrencia (Colas):** Previene la saturación del router doméstico y bloqueos en Google Sheets introduciendo una arquitectura de colas locales (SQLite/Redis) y técnicas de "Long-Polling".

## 📁 Bloque 06: Compilado de Cuadernos NotebookLM (001-004)
**Ruta:** `bloque_06_notebooks_compilado/`

Este bloque contiene la inteligencia técnica y evolutiva extraída automáticamente conectándome a tu cuenta de Google y consultando tus cuadernos en NotebookLM mediante inteligencia artificial (RAG).

**Acciones que implementa (o previene):**
- **Arquitectura PWA Offline-First (Cuaderno 001):** Documenta cómo se evitan cuelgues (OOM) en los celulares de los técnicos al procesar fotos en campo sin internet y generar PDFs de forma segura.
- **Enrutamiento de IA y RAG (Cuaderno 002):** Consolida la decisión de usar APIs externas especializadas (Groq, Gemini, Mistral) y de separar la "memoria" por sucursal para evitar que la IA alucine mezclando datos.
- **Análisis de Workspace vs Local (Cuaderno 003):** Documenta los límites reales de Google Apps Script (90 minutos diarios) y fundamenta por qué se eligió Google Chat corporativo en vez de WhatsApp.
- **Consolidación del Hardware Definitivo (Cuaderno 004):** Ratifica el uso de la Lenovo M700 con Ubuntu, la estrategia de apagado seguro con la UPS Lyonn, y el uso de Rclone para cuidar el disco sólido frente a subidas masivas de datos.

---

## 📁 Paquetes Adicionales de Despliegue

### 📄 [paquete_hermes_agent_deepseek.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/paquete_hermes_agent_deepseek.md)
Guía secuencial e interactiva paso a paso para la instalación oficial de la CLI de Hermes Agent. Incluye la integración de proveedores gratuitos mediante el uso de "Nose Portal" para cargar el modelo de "DeepSeek-V4".

### 📄 [metodologia_gsd.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/metodologia_gsd.md)
Metodología GSD (Get Shit Done) - Protocolo conceptual de orquestación y máquina de estados para el desarrollo ordenado y modular del proyecto mediante prompt commands.

### 📄 [paquete_github_ubuntu.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/paquete_github_ubuntu.md)
Guía automatizada para el agente de Ubuntu para configurar credenciales de Git, instalar la CLI de GitHub (gh) y clonar el repositorio de forma desatendida.

### 📄 [paquete_obsidian_cerebro.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/paquete_obsidian_cerebro.md)
Propuesta de integración para utilizar Obsidian como segundo cerebro local del Supervisor, organizando de forma automática diálogos de técnicos, resúmenes e incidentes en archivos Markdown y Canvas dinámicos.

### 📄 [paquete_telegram_userbot.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/paquete_telegram_userbot.md)
Guía técnica para la configuración del Cliente de Telegram (Userbot) usando la librería Telethon con el número de teléfono propio, eliminando el uso de Webhooks y dependencias de HTTPS externos.

### 📄 [paquete_c_userbot_y_hermes.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/paquete_c_userbot_y_hermes.md)
Paquete de despliegue unificado de ejecución para el Paso C, que incluye la instalación del Userbot con Telethon, la inicialización de la base de datos local SQLite y la configuración de persistencia en systemd.

### 📄 [paquete_e_soporte_voz_y_apis_free.md](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/paquete_e_soporte_voz_y_apis_free.md)
Documentación de despliegue y arquitectura de optimización para el procesamiento gratuito de notas de voz en el Userbot usando la API de Groq (Whisper) y la API de Nose Portal (DeepSeek).

*(Nuevos bloques y paquetes se irán agregando aquí a medida que se proporcionen)*




