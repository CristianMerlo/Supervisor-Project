# Paquete de Despliegue: Motor WhatsApp Web (Ubuntu)

Este documento instruye cómo arrancar el entorno gráfico en la Mini PC para que el script `motor_whatsapp_web.py` pueda engancharse (Browser Attaching) y procesar de forma automatizada los mensajes de los grupos.

---

## 🛠️ Paso 1: Arrancar Chrome con Depuración Remota

Para que este módulo funcione, el agente Antigravity **no** levantará el navegador por sí mismo. Debes tener una sesión de Google Chrome abierta permanentemente en la interfaz gráfica de tu Mini PC con Ubuntu.

Abre la terminal de Ubuntu (en tu escritorio) y ejecuta este comando para lanzar Chrome:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="/home/$USER/.config/chrome-whatsapp"
```

*Nota: Si prefieres aislar la sesión corporativa, el parámetro `--user-data-dir` crea un perfil completamente nuevo (limpio) llamado `chrome-whatsapp` exclusivo para este bot.*

## 📱 Paso 2: Inicio de Sesión Manual

1. En esa ventana de Chrome que se acaba de abrir, navega a `https://web.whatsapp.com/`.
2. Escanea el código QR con el celular corporativo.
3. Asegúrate de que los tres grupos (Fichada, Mto Franquicias, Informes) estén preferentemente fijados (Pin) arriba de todo para facilitar la carga.

A partir de este momento, **no cierres esa ventana de Chrome**. Puedes minimizarla, pero debe quedar corriendo de fondo.

## 🤖 Paso 3: Instrucciones para Antigravity (Ejecución Desatendida)

Una vez que Chrome está abierto y logueado, pásale este comando a tu agente Antigravity local:

> "Por favor, sincroniza los últimos cambios de Git (`git pull`) y luego programa una ejecución automática de `python motor_whatsapp_web.py` cada 30 minutos utilizando tu temporizador interno."

El script hará lo siguiente:
- Se conectará al puerto `9222`.
- Buscará y leerá los mensajes nuevos de los 3 grupos de técnicos.
- Si detecta un archivo adjunto (PDF, foto), hará clic en "Descargar".
- Automáticamente moverá el archivo desde la carpeta de Descargas de Ubuntu hacia la carpeta `entrantes/` de tu proyecto, para que el `ingestor_automatico.py` lo procese en su próximo ciclo.
