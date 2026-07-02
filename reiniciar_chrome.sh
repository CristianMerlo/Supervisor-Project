#!/bin/bash
# Script para reiniciar Google Chrome con el puerto de depuración 9222 habilitado.
# Esto previene cuelgues del navegador por consumo excesivo de memoria (OOM).

# Exportar variables gráficas para asegurar ejecución bajo cron
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"

echo "=== REINICIANDO GOOGLE CHROME (CDP 9222) ==="
date

# 1. Matar procesos existentes de Chrome
echo "[1/2] Cerrando instancias previas de Chrome..."
killall -9 chrome || true
sleep 3

# Eliminar archivos de bloqueo antiguos si existen
rm -f /home/cristian/.config/chrome-whatsapp/Singleton*

# 2. Iniciar Chrome en background con el puerto CDP abierto
echo "[2/2] Lanzando Chrome con remote debugging..."
setsid google-chrome --remote-debugging-port=9222 --user-data-dir="/home/cristian/.config/chrome-whatsapp" --no-first-run --no-default-browser-check < /dev/null > /dev/null 2>&1 &

sleep 2
echo "✓ Proceso completado exitosamente."
