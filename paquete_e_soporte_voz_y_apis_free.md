# Paquete de Despliegue: Paso E (Soporte de Notas de Voz e Inferencia de Costo Cero)

Este módulo documenta cómo habilitar la ingesta y transcripción de notas de voz en el **Cliente de Telegram (Userbot)** utilizando la API gratuita de **Groq (Whisper)** y las llamadas a **Nose Portal (DeepSeek V4 Flash)**. Esta arquitectura está diseñada específicamente para optimizar costos, evitando que las llamadas de audio (que consumen muchos tokens) consuman los límites de tu plan Pro de Antigravity (Gemini Pro).

> [!IMPORTANT]
> **FLUJO MULTIMODAL DE INGESTA DE AUDIO:**
> 1. El técnico envía un audio por Telegram al número `+54 11 2163 3815`.
> 2. El Userbot descarga el archivo `.ogg` a la carpeta `temp_audios/`.
> 3. Se envía el archivo de audio a la API de **Groq Whisper (whisper-large-v3)** de forma gratuita para obtener el texto.
> 4. El texto se procesa a través del enrutador de niveles: SQLite local (Niveles 1 y 2) o **Nose Portal (DeepSeek)** para manuales técnicos (Nivel 3).
> 5. Si Cristian (Jefe) envía un mensaje de texto libre, se utiliza **Gemini Pro (Antigravity Pro)** para responderle (Nivel 4).

---

## ⚙️ 1. Configuración de Variables de Entorno (`.env`)

Asegúrate de agregar las siguientes API Keys al archivo `.env` en tu servidor Ubuntu:
```env
# API Key de Groq para la Transcripción Gratuita (Whisper)
GROQ_API_KEY=tu_groq_api_key

# API Key de Nose Portal para el Soporte Técnico Gratuito (DeepSeek V4 Flash)
NOSE_PORTAL_API_KEY=tu_nose_portal_api_key

# API Key de Antigravity (Gemini Pro) para tu Asistente Personal
GEMINI_API_KEY=tu_gemini_api_key
```

---

## 🛠️ 2. Código de Producción Incorporado

El archivo principal [userbot_supervisor.py](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/userbot_supervisor.py) ha sido completamente actualizado con esta ingeniería. 

### Características del Motor de Voz:
*   **Descarga Automática:** Detecta eventos de tipo `voice` y `audio` de forma nativa en Telethon.
*   **Limpieza de Disco:** Elimina inmediatamente la nota de voz descargada después de transcribirla para mantener libre el almacenamiento del servidor.
*   **Ahorro de Tokens:**
    *   La nota de voz se transcribe gratis en Groq.
    *   Si es sobre direcciones o tareas de locales (Urquiza/Chacabuco), se responde en milisegundos consultando la base de datos SQLite local, consumiendo **0 tokens** de inteligencia artificial.
    *   Si es una falla técnica, se le sirve el contexto local del manual a DeepSeek V4 Flash en Nose Portal (gratuito).
    *   Gemini Pro solo se invoca cuando Cristian le escribe directamente al bot.

---

## 🚀 3. Instrucciones de Implementación en Ubuntu

Para activar este soporte de audio en tu servidor:

1. **Reemplazar el script:** Reemplaza el contenido de `userbot_supervisor.py` en tu servidor con el código provisto en [userbot_supervisor.py](file:///Users/CR1S714N/Documents/Repositorios%20GitHub/PROYECTOS/SUPERVISOR%20AGENTE/userbot_supervisor.py).
2. **Reiniciar el Servicio:** Recarga y reinicia el servicio systemd:
   ```bash
   sudo systemctl restart supervisor-userbot
   ```
3. **Monitorear Logs:** Verifica que la ingesta de audios y la comunicación con Groq funcionen correctamente:
   ```bash
   sudo journalctl -u supervisor-userbot -f
   ```
