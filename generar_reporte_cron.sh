#!/bin/bash
# Script para ejecutar el generador de reportes semanales (Cron Job)
# Uso recomendado en crontab: 0 8 * * 1 /home/cristian/PROYECTOS/Supervisor-Project/generar_reporte_cron.sh >> /home/cristian/PROYECTOS/Supervisor-Project/cron_reportes.log 2>&1

cd /home/cristian/PROYECTOS/Supervisor-Project
source venv/bin/activate 2>/dev/null || true # Si hay un entorno virtual
python3 motor_reportes_supervisor.py
