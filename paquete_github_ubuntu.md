# Paquete de Despliegue: Sincronización de GitHub en Ubuntu

Este documento contiene las instrucciones operativas para que Antigravity (en la instancia de Ubuntu) configure el entorno de Git y conecte el repositorio del proyecto con la menor intervención humana posible.

---

## 📋 Instrucciones para Antigravity (Ubuntu)

Eres el agente encargado de replicar el entorno de desarrollo en este equipo Ubuntu. Debes seguir estos pasos de forma secuencial. No te saltes ninguno.

### Paso 1: Configuración de Identidad Git
Configura la identidad global de Git para que coincida con el equipo principal de Cristian. Ejecuta en tu terminal:
```bash
git config --global user.name "Cristian Merlo"
git config --global user.email "cristian.merlo@outlook.com"
```

### Paso 2: Instalación de GitHub CLI (`gh`)
Verifica si GitHub CLI está instalado (`gh --version`). Si no lo está, instálalo ejecutando:
```bash
(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
&& sudo mkdir -p -m 755 /etc/apt/keyrings \
&& wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
&& sudo apt update \
&& sudo apt install gh -y
```

### Paso 3: Autenticación Desatendida (Intervención Mínima)
Dado que los comandos interactivos en terminal te pueden bloquear, debes pedirle a Cristian la mínima intervención posible.
Dile a Cristian exactamente esto:
> "Para sincronizar tu cuenta de GitHub, por favor ve a https://github.com/settings/tokens y genera un Token de Acceso Personal (Classic) con permisos de `repo`. Pégalo aquí en el chat para que yo me encargue de la autenticación por ti."

Una vez que Cristian te pase el token, ejecuta de forma silenciosa:
```bash
echo "EL_TOKEN_QUE_TE_PASO_CRISTIAN" | gh auth login --with-token
```
*(Si Cristian prefiere hacerlo él mismo por seguridad, dile que simplemente ejecute `gh auth login -w` en su terminal de Ubuntu y te avise cuando termine).*

### Paso 4: Clonar el Repositorio Maestro
Una vez autenticado exitosamente, procede a clonar el proyecto del Supervisor para que podamos empezar a trabajar en él:
```bash
mkdir -p ~/PROYECTOS
cd ~/PROYECTOS
gh repo clone CristianMerlo/Supervisor-Project
```

### Paso 5: Confirmación
Informa a Cristian que la sincronización fue exitosa, haz un `ls -la` en la carpeta clonada y muéstrale los archivos que has recibido. A partir de aquí, el entorno de Ubuntu estará listo para seguir construyendo sobre la misma base de código.
