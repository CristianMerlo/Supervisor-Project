#!/bin/bash

# Recibir el mensaje como argumentos del comando
MESSAGE="$*"

# Si no hay argumentos, leer de stdin
if [ -z "$MESSAGE" ]; then
    read -r MESSAGE
fi

# Si aún está vacío, definir un mensaje genérico
if [ -z "$MESSAGE" ]; then
    MESSAGE="Alerta del sistema UPS (evento desconocido)"
fi

# Registrar localmente en los logs de Supervisor para depuración
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UPS TRIGGER] $MESSAGE" >> /home/cristian/Documentos/Supervisor/userbot.log

# Enviar el POST al servidor local del userbot
curl -s -X POST -H "Content-Type: text/plain" -d "$MESSAGE" http://127.0.0.1:8088/notify > /dev/null 2>&1
