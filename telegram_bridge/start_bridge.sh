#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DE INICIO DE TELEGRAM BRIDGE BAJO SYSTEMD
# ==============================================================================
# Este script espera la URL de Cloudflare, actualiza el .env y ejecuta el bridge.
# ==============================================================================

BRIDGE_DIR="/home/cristian/Documentos/Supervisor/telegram_bridge"
CLOUDFLARED_LOG="/home/cristian/Documentos/Supervisor/cloudflared.log"

echo "⏳ Esperando URL dinámica de Cloudflared en el archivo de log..."
CLOUDFLARE_URL=""

# Esperar hasta 60 segundos por la URL en el log
for i in {1..30}; do
    if [ -f "$CLOUDFLARED_LOG" ]; then
        # Obtener la URL más reciente de trycloudflare del log
        CLOUDFLARE_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" "$CLOUDFLARED_LOG" | tail -n 1)
        if [ -n "$CLOUDFLARE_URL" ]; then
            echo "🟢 URL de túnel obtenida: $CLOUDFLARE_URL"
            break
        fi
    fi
    sleep 2
done

if [ -z "$CLOUDFLARE_URL" ]; then
    echo "❌ ERROR: No se pudo obtener la URL del túnel de Cloudflared en el log."
    exit 1
fi

# Actualizar el archivo .env
sed -i "s|^WEBHOOK_URL=.*|WEBHOOK_URL=${CLOUDFLARE_URL}/webhook|" "${BRIDGE_DIR}/.env"
echo "✅ Archivo .env actualizado con la URL: ${CLOUDFLARE_URL}/webhook"

# Cargar variables de entorno del archivo .env local
export $(grep -v '^#' "${BRIDGE_DIR}/.env" | xargs)

# Esperar propagación inicial de DNS para que Telegram no guarde un cache NXDOMAIN negativo
echo "⏳ Esperando 30 segundos para permitir la propagación DNS inicial del nuevo túnel..."
sleep 30

# 1. Eliminar cualquier Webhook previo y limpiar actualizaciones pendientes
echo "🧹 Eliminando webhook anterior de Telegram..."
DELETE_RES=$(curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/deleteWebhook?drop_pending_updates=true")
echo "Resultado deleteWebhook: $DELETE_RES"

# 2. Registrar webhook en Telegram con reintentos
echo "🔄 Registrando nuevo webhook en Telegram API..."
WEBHOOK_SUCCESS=false
for i in {1..10}; do
    WEBHOOK_RES=$(curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${CLOUDFLARE_URL}/webhook")
    echo "Intento $i/10: $WEBHOOK_RES"
    if echo "$WEBHOOK_RES" | grep -q '"ok":true'; then
        echo "🟢 Webhook de Telegram registrado con éxito."
        WEBHOOK_SUCCESS=true
        break
    fi
    echo "⏳ Esperando 10 segundos para permitir propagación DNS..."
    sleep 10
done

if [ "$WEBHOOK_SUCCESS" = false ]; then
    echo "❌ ERROR: No se pudo registrar el webhook en Telegram tras varios reintentos."
    exit 1
fi

# Ejecutar el puente de Telegram reemplazando el proceso actual de bash (exec)
echo "🚀 Iniciando Telegram Bridge..."
exec python3 -u app.py
