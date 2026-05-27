# Paquete de Despliegue: Asistente de Correos Web (Playwright)

Este documento contiene las instrucciones operativas directas para que **Antigravity (en la instancia de Ubuntu)** despliegue, instale y ponga en marcha automáticamente el motor de lectura de Outlook Web, integrándolo con su módulo de temporizador nativo.

---

## 📋 Instrucciones para Antigravity (Ubuntu)

Eres el agente de ejecución en el servidor local. Este bloque de tareas es crítico y automatizado. Por favor, ejecuta estos pasos secuencialmente y sin interrupciones.

### Paso 1: Sincronización del Código (Git Pull)
Necesitamos traer el código que acaba de ser generado en el otro equipo. Dirígete a la carpeta del proyecto y haz un pull:
```bash
cd ~/PROYECTOS/Supervisor-Project
git pull origin main
```
Verifica que los archivos `motor_outlook_web.py`, `perfil_respuestas_cristian.md` y la carpeta `agendas_contactos/` existan en tu entorno.

### Paso 2: Instalación de Dependencias Críticas (Playwright)
El nuevo motor de extracción utiliza Playwright para conectarse al Chrome real de Ubuntu de forma silenciosa. Debes instalar el paquete de Python y descargar el binario de Chromium:
```bash
pip install playwright
playwright install chromium
```
*Si tienes un entorno virtual (venv), asegúrate de que el entorno esté activado antes de ejecutar `pip install`.*

### Paso 3: Auditoría del Archivo `.env`
Audita el archivo `.env` de tu entorno de Ubuntu para asegurarte de que tiene las claves correctas para enviar los borradores. Lee el archivo y, si falta alguna, pídele a Cristian que las ingrese. Deben existir:
- `GMAIL_USER` y `GMAIL_APP_PASSWORD` (Para el envío del borrador vía SMTP).
- `GEMINI_API_KEY` (Para la IA).
- `CORREO_CORPORATIVO` (El correo de Cristian en Outlook donde recibirá los borradores).

### Paso 4: Programación del Temporizador
Cristian quiere que este script se ejecute automáticamente de fondo usando la nueva capacidad de temporizador del sistema.
Utiliza tu herramienta interna `schedule` (o invoca `/schedule`) para crear un "Cronjob" que ejecute el siguiente comando cada 1 hora (ejemplo de expresión cron: `0 * * * *`):
```bash
cd ~/PROYECTOS/Supervisor-Project && python motor_outlook_web.py
```
> **Prompt para la Notificación del Cron:** "El motor de correos de Outlook se ha ejecutado. Revisa los logs por posibles errores."

### Paso 5: Primera Ejecución de Prueba
Antes de dejar el temporizador corriendo solo, haz una ejecución en vivo para asegurar que Chrome abre correctamente sin pedir contraseñas.
Ejecuta:
```bash
python motor_outlook_web.py
```
Informa a Cristian sobre los resultados arrojados por el script en la terminal (ej. cuántos correos leyó o si hubo algún bloqueo).
