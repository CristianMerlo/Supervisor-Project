#!/bin/bash
echo "Configurando /etc/nut/upsmon.conf..."
sudo bash -c 'cat >> /etc/nut/upsmon.conf' << 'EOF'

# --- Configuración de Notificaciones por Telegram ---
NOTIFYCMD "/home/cristian/Documentos/Supervisor/notify_telegram.sh"
NOTIFYMSG ONBATT "⚠️ El servidor entró en modo batería (corte de luz eléctrica)!"
NOTIFYMSG ONLINE "✔️ Se restableció la energía de red. Retornando a modo normal."
NOTIFYFLAG ONBATT SYSLOG+WALL+EXEC
NOTIFYFLAG ONLINE SYSLOG+WALL+EXEC
EOF
echo "Reiniciando servicio nut-monitor..."
sudo systemctl restart nut-monitor
echo "¡Configuración de NUT completada con éxito!"
