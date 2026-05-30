#!/bin/bash
# Script para activar el Inicio de Sesión Automático en Ubuntu (GDM3)

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Este script debe ejecutarse con privilegios de administrador."
  echo "Por favor, ejecútalo como: sudo ./configurar_autologin.sh"
  exit 1
fi

CONF_FILE="/etc/gdm3/custom.conf"

if [ -f "$CONF_FILE" ]; then
  echo "Configurando login automático en $CONF_FILE..."
  
  # Remover líneas previas comentadas o activas de AutomaticLogin para evitar duplicados
  sed -i '/AutomaticLoginEnable/d' "$CONF_FILE"
  sed -i '/AutomaticLogin/d' "$CONF_FILE"
  
  # Insertar la configuración activa justo debajo de [daemon]
  sed -i '/\[daemon\]/a AutomaticLoginEnable = true\nAutomaticLogin = cristian' "$CONF_FILE"
  
  echo "✅ ¡Listo! Login automático configurado exitosamente para el usuario 'cristian'."
  echo "En el próximo reinicio, el sistema entrará al escritorio sin pedir contraseña."
else
  echo "❌ Error: No se encontró el archivo de configuración en $CONF_FILE."
  echo "Verifica qué gestor de login estás utilizando."
fi
