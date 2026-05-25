# Paquete de Despliegue: Cliente de Telegram (Userbot) con Número Propio

Este módulo documenta cómo implementar la integración de Telegram actuando como un **Cliente Real (Userbot)** utilizando la librería **Telethon** en Python, en lugar de usar un Bot API estándar. Esto nos permite asociar el sistema directamente al número telefónico asignado (`+54 11 2163 3815`) para el perfil "Supervisor Mantenimiento".

> [!IMPORTANT]
> **VENTAJAS DEL ENFOQUE USERBOT:**
> - **Sin Webhooks ni Dominios:** Se conecta directamente mediante el protocolo MTProto de Telegram. No requiere abrir puertos, configurar Cloudflare Tunnels ni usar HTTPS.
> - **Identidad Humana Real:** El bot chatea y responde desde una cuenta de usuario normal, permitiéndole iniciar conversaciones de forma proactiva con los técnicos.
> - **Estabilidad Extrema:** Ideal para correr en segundo plano dentro de un servicio `systemd` y una sesión de `tmux`.

---

## 🛠️ Requisitos de Configuración Inicial

Para conectar el script a la cuenta `+54 11 2163 3815`, necesitamos credenciales de desarrollador de Telegram:

1. Ingresar a [my.telegram.org](https://my.telegram.org/) desde un navegador.
2. Colocar el número de teléfono `+54 11 2163 3815` y confirmar el código enviado a la aplicación de Telegram.
3. Ir a **API development tools** y crear una aplicación (puedes poner nombres simples como "SupervisorHermes").
4. Copiar los valores de:
   - `api_id` (número entero)
   - `api_hash` (cadena de caracteres)

Estos datos se guardarán en el archivo local de variables de entorno `.env` en la máquina Ubuntu:
```env
TELEGRAM_PHONE=+541121633815
TELEGRAM_API_ID=TU_API_ID
TELEGRAM_API_HASH=TU_API_HASH
```

---

## 🐍 Implementación del Script base: `userbot_supervisor.py`

Este script se encarga de escuchar los chats, procesar mensajes de texto, descargar audios y delegar al motor local de base de datos.

```python
import os
import sys
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

# Crear el cliente de Telegram. Genera el archivo 'supervisor.session' para persistencia
client = TelegramClient('supervisor', API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def manejador_mensajes(event):
    # Evitar auto-respuestas
    if event.is_private or event.is_group:
        remitente = await event.get_sender()
        nombre_usuario = remitente.username or remitente.first_name
        mensaje = event.text
        
        print(f"[NUEVO MENSAJE] De: {nombre_usuario} (ID: {event.sender_id}) -> {mensaje}")
        
        # Filtro de Técnicos Autorizados (cruzando con SQLite)
        # TODO: Cargar nómina de técnicos
        
        # Nivel 1: Consultas Estáticas (Direcciones)
        if "direccion" in mensaje.lower():
            # TODO: Buscar local en sqlite local
            await event.respond("La dirección de Urquiza es Av. Triunvirato 4500.")
            return
            
        # Nivel 2: Consultas Dinámicas (Pendientes / Chacabuco)
        elif "pendientes" in mensaje.lower() or "chacabuco" in mensaje.lower():
            # TODO: Buscar alertas de Chacabuco en sqlite
            await event.respond("En Chacabuco tenemos pendiente: Reparación de ablandador de agua.")
            return

        # Nivel 3: Consulta Compleja / Manuales (Uso de IA asíncrono)
        elif "error" in mensaje.lower() or "falla" in mensaje.lower():
            # Avisar que se está procesando para no bloquear la interacción
            mensaje_espera = await event.respond("Buscando el error en el manual técnico...")
            
            # TODO: Llamar al pipeline RAG local y API Free (Groq/DeepSeek)
            respuesta_ia = "El error indica problemas de presión de caldera. Por favor, verificar válvula de entrada."
            
            # Responder editando el mensaje de espera
            await mensaje_espera.edit(respuesta_ia)
            return

async def main():
    print("Iniciando conexión con Telegram MTProto...")
    await client.start(phone=PHONE)
    print("--- [CONECTADO] El Supervisor está escuchando chats de forma activa ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
```

---

## 🔑 Flujo de Autenticación por Única Vez

Cuando el script se ejecute por primera vez en la máquina Ubuntu final:

1. **Lanzamiento:** Ejecutaremos `python3 userbot_supervisor.py`.
2. **Entrada de Código:** La terminal se detendrá y te pedirá ingresar el código de verificación que Telegram te envía a tu celular/app Desktop.
3. **Código de Dos Pasos:** Si la cuenta tiene verificación de dos pasos (contraseña adicional), la solicitará en la terminal de forma segura.
4. **Archivo de Sesión:** Tras ingresar los datos con éxito, se creará el archivo `supervisor.session` en la raíz del proyecto. **No se volverá a solicitar el código** a menos que elimines este archivo.

---

## ⚙️ Registro en el Plan de Tareas
*   **Fase 0 (Tema Crítico):** Se integrará la ejecución de `userbot_supervisor.py` en el arranque de `systemd` y la consola persistente en `tmux`.
*   **Paso C:** La estrategia alternativa de Telegram ahora utilizará **Telethon (Userbot)** en lugar de la API de Bot tradicional, lo que elimina la necesidad de HTTPS / Webhooks.
