# Paquete de Despliegue: Actualización de Hermes a v0.14

Este documento contiene las instrucciones precisas para que **Antigravity (en la instancia de Ubuntu)** actualice el motor de Hermes Agent a la versión 0.14, migrando desde la arquitectura antigua (repositorio completo clonado) a la nueva arquitectura modular basada en Python.

---

## 📋 Instrucciones para Antigravity (Ubuntu)

Eres el agente de ejecución en el servidor local. Tu tarea es actualizar Hermes Agent a su última versión (0.14) sin romper las configuraciones actuales del proyecto Supervisor. Ejecuta los siguientes pasos de forma secuencial:

### Paso 1: Respaldo de Configuración
Antes de tocar nada, asegúrate de respaldar el archivo `.env` o la carpeta oculta de configuración de Hermes (suele estar en `~/.hermes/` o dentro de la carpeta `hermes-cli` que clonaste originalmente).
```bash
mkdir -p ~/respaldo_hermes
cp -r ~/.hermes ~/respaldo_hermes/ 2>/dev/null || echo "No existe ~/.hermes, saltando..."
cp -r ~/hermes-cli/.env ~/respaldo_hermes/ 2>/dev/null || echo "No existe .env en hermes-cli, saltando..."
```

### Paso 2: Limpieza de la Versión Antigua (Monolítica)
En la instalación original (Fase C), descargaste el repositorio completo con `git clone`. Como la v0.14 ya no requiere clonar repositorios pesados, vamos a eliminar la carpeta vieja para evitar conflictos (tus credenciales ya están respaldadas o en el proyecto de Supervisor).
```bash
sudo rm -rf ~/hermes-cli
```

### Paso 3: Instalación Modular (Nueva Arquitectura Python)
Siguiendo las notas de la versión 0.14, instala la base ligera y nativa a través del gestor de paquetes de Python (pip). Asegúrate de hacerlo a nivel global o en el entorno del usuario según corresponda:
```bash
pip install --upgrade hermes-agent
```
*(Nota para el agente: Si el nombre del paquete exacto en PyPI difiere según la documentación oficial de Hermes a la que tengas acceso en tiempo real, ajusta el comando `pip install` al nombre correcto).*

### Paso 4: Inicialización y Comprobación de Seguridad
Una vez instalado el núcleo base, comprueba que la herramienta funcione correctamente en su versión 0.14 ejecutando:
```bash
hermes --version
```
Luego, inicializa la configuración base y vuelve a vincular el modelo que Cristian utiliza (ej. Groq o Nose Portal) si es que el respaldo no lo cargó automáticamente:
```bash
hermes model
```

### Paso 5: Levantamiento del Proxy Local (Opcional pero Recomendado)
La versión 0.14 incluye un "Proxy Local". Inícialo de fondo en un puerto seguro para que nuestros otros scripts (`motor_supervisor.py` o `motor_whatsapp_web.py`) puedan conectarse a él en el futuro simulando la API de OpenAI:
```bash
nohup hermes proxy --port 8080 > hermes_proxy.log 2>&1 &
```

### Paso 6: Reporte al Usuario
Infórmale a Cristian que la migración ha sido exitosa. Confírmale:
1. Qué versión exacta responde `hermes --version`.
2. Que el Proxy Local quedó corriendo en el puerto 8080.
3. Que las barreras de seguridad contra `sudo` ya están activas nativamente.
