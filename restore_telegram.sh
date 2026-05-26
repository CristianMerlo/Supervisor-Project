#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DE RESTAURACIÓN AUTOMÁTICA DEL BOT DE TELEGRAM (PROYECTO HERMES)
# ==============================================================================
# Autor: Antigravity
# Ubicación: /home/cristian/Documentos/Supervisor/restore_telegram.sh
#
# Este script levanta toda la pila de servicios en orden, captura la nueva URL
# de Cloudflare, la inyecta en el archivo .env, y actualiza el webhook del bot.
# ==============================================================================

# Configuración de Rutas
SUPERVISOR_DIR="/home/cristian/Documentos/Supervisor"
API_DIR="${SUPERVISOR_DIR}/antigravity_api"
BRIDGE_DIR="${SUPERVISOR_DIR}/telegram_bridge"

API_LOG="/tmp/antigravity_api.log"
BRIDGE_LOG="/tmp/telegram_bridge.log"
CLOUDFLARED_LOG="/tmp/cloudflared.log"

echo "=== 🧹 PASO 1: Limpieza de Procesos Anteriores ==="
pkill -f "server.py" 2>/dev/null
pkill -f "app.py" 2>/dev/null
pkill -f "cloudflared" 2>/dev/null
sleep 2
echo "✅ Puertos liberados."

echo "=== 🚀 PASO 2: Iniciando Antigravity API (Puerto 8000) ==="
cd "$API_DIR" || exit 1
nohup python3 server.py > "$API_LOG" 2>&1 &
API_PID=$!
echo "PID API: $API_PID"

# Esperar a que la API responda
echo "⏳ Esperando que la API esté lista..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health | grep -q '"status":"ok"' || grep -q "Uvicorn running" "$API_LOG"; then
        echo "🟢 API lista y escuchando en el puerto 8000."
        break
    fi
    sleep 1.5
done

echo "=== 🚀 PASO 3: Iniciando Telegram Bridge (Puerto 5000) ==="
cd "$BRIDGE_DIR" || exit 1
# Cargar variables de entorno del archivo .env local
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ ERROR: No se encontró el archivo .env en $BRIDGE_DIR"
    exit 1
fi

nohup python3 -u app.py > "$BRIDGE_LOG" 2>&1 &
BRIDGE_PID=$!
echo "PID Bridge: $BRIDGE_PID"
sleep 2

echo "=== 🌐 PASO 4: Iniciando Túnel de Cloudflared ==="
nohup cloudflared tunnel --url http://localhost:5000 > "$CLOUDFLARED_LOG" 2>&1 &
CLOUDFLARED_PID=$!
echo "PID Cloudflared: $CLOUDFLARED_PID"

echo "⏳ Esperando URL dinámica de Cloudflared..."
CLOUDFLARE_URL=""
for i in {1..15}; do
    CLOUDFLARE_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" "$CLOUDFLARED_LOG" | head -n 1)
    if [ -n "$CLOUDFLARE_URL" ]; then
        echo "🟢 URL del túnel obtenida: $CLOUDFLARE_URL"
        break
    fi
    sleep 1.5
done

if [ -z "$CLOUDFLARE_URL" ]; then
    echo "❌ ERROR: No se pudo obtener la URL de Cloudflare en 20 segundos."
    echo "Revisá el log en: cat $CLOUDFLARED_LOG"
    exit 1
fi

echo "⏳ Esperando 30 segundos para permitir la propagación DNS global antes de registrar en Telegram..."
sleep 30

echo "=== ⚙️ PASO 5: Reconfigurando Webhook de Telegram ==="
# 1. Actualizar el archivo .env del bridge para consistencia
sed -i "s|^WEBHOOK_URL=.*|WEBHOOK_URL=${CLOUDFLARE_URL}/webhook|" "${BRIDGE_DIR}/.env"
echo "✅ Archivo .env actualizado con la nueva URL."

# 2. Registrar el nuevo Webhook en Telegram API
TELEGRAM_TOKEN=$(grep -oP '^TELEGRAM_TOKEN=\K.*' "${BRIDGE_DIR}/.env")
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ ERROR: No se encontró TELEGRAM_TOKEN en el .env"
    exit 1
fi

echo "⏳ Esperando propagación de DNS de Cloudflare..."
sleep 5

for i in {1..5}; do
    echo "🔄 Registrando webhook (Intento $i/5)..."
    WEBHOOK_RES=$(curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${CLOUDFLARE_URL}/webhook")
    if echo "$WEBHOOK_RES" | grep -q '"ok":true'; then
        echo "🟢 Webhook de Telegram registrado con éxito en la API oficial."
        break
    else
        echo "⚠️ Intento $i falló: $WEBHOOK_RES"
        if [ $i -lt 5 ]; then
            sleep 3
        else
            echo "❌ ERROR definitivo al registrar Webhook en Telegram."
            exit 1
        fi
    fi
done

echo "=== 📊 PASO 6: Diagnóstico y Verificación Final ==="
echo "🔍 Verificando puertos:"
ss -tlnp | grep -E ":5000|:8000"

echo "🔍 Verificando Webhook en vivo:"
WEBHOOK_STATUS=$(curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getWebhookInfo")
echo "Respuesta de Telegram: $WEBHOOK_STATUS"

echo "=================================================="
echo "🎉 ¡SERVICIOS RESTAURADOS DE FORMA CORRECTA Y EN LÍNEA!"
echo "=================================================="
