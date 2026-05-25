# Bloque 1: Inicialización Hermes

Este bloque contiene la última versión (la más reciente) de la estrategia técnica para que Antigravity pueda interpretar, estructurar y aplicar todo el proyecto en una máquina Ubuntu de forma automática.

Se utiliza un **Script de Inicialización Auto-Ejecutable en Python** (`setup_hermes.py`).

## ¿Qué va a pasar cuando se ejecute?

1. Creará un directorio principal llamado `hermes-headless-supervisor/`.
2. Generará la subcarpeta `.antigravity/` con la configuración de tareas cronometradas (`automation_config.json`), mapeando el monitor de correo cada dos horas y el de Telegram cada una hora.
3. Configurará el archivo `app_config.json` con la lista explícita de los técnicos a monitorear (Fernando Soria, Tomás Vera, Anabella Guerrero y Francisco Rameta) para que los scripts sepan exactamente a quiénes filtrar.
4. Escribirá el conector directo por API de Google Sheets (`sheets_connector.py`) aislando la autenticación por token JSON local para asegurar que la sincronización con Looker Studio no sufra interrupciones ni requiera interfaces gráficas.
