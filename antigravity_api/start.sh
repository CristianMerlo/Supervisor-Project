#!/bin/bash
cd "$(dirname "$0")"

# Verificar si existe venv
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 Instalando dependencias..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🚀 Iniciando servidor FastAPI en el puerto 8000..."
python server.py
