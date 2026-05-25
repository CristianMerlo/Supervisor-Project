# Bloque 02: Análisis de Viabilidad, Historial y RFI

## Evolución del Proyecto
El proyecto nace de la necesidad de Cristian Merlo de desplegar un asistente de IA de tiempo completo (Proyecto Hermes) enfocado en la supervisión y gestión de mantenimiento de infraestructura comercial (maquinaria de café, refrigeración, etc.), operando de forma continua (24/7). 

Inicialmente, existía la duda sobre la viabilidad de su convivencia con Antigravity IDE (entorno de desarrollo y ejecución de tareas a demanda) dentro del hardware disponible (Lenovo ThinkCentre M700 Tiny, i3, 8GB RAM). 

Tras analizar las especificaciones del servidor local, se acordó:
- **Desacoplar el procesamiento pesado** delegándolo a APIs externas (Google, Groq, OpenRouter, Mistral).
- **Mutar el bot de Telegram preexistente** en Antigravity para que actúe como la interfaz de usuario final de Hermes.
- **Consolidar a Antigravity** estrictamente como el entorno de desarrollo, control y monitoreo de logs.

## Enfoques Rechazados/Descartados
1. **Procesamiento LLM Local:** Se descartó la ejecución de modelos de lenguaje locales (vía Ollama/Docker) en segundo plano de forma continua. *Motivo:* Saturación crítica de los 8 GB de RAM y degradación del procesador i3 ante picos de demanda.
2. **Interfaz de Usuario Nativa en Antigravity para Operación:** Se descartó el uso de Open WebUI o chats internos de Antigravity para la comunicación diaria con el asistente. *El canal operativo exclusivo será Telegram.*

## Núcleo Inmutable
Desarrollar un servicio orquestador asincrónico y no interactivo en Python, que corra 24/7 en segundo plano dentro de un contenedor Docker en Ubuntu, utilizando un bot de Telegram como interfaz de E/S y conmutando dinámicamente entre múltiples APIs externas para el procesamiento de lenguaje natural.

---

## ⚠️ POR QUÉ ESTO FALLARÁ (Vectores Críticos)
El sistema colapsará bajo tres vectores específicos si no se establecen las reglas claras:

1. **Bloqueo de Hilos por E/S Asincrónica Deficiente:** Si la escucha de Telegram (Pooling) o la consulta a las APIs externas se implementa con librerías síncronas bloqueantes, un retraso en una API congelará el demonio de Hermes. Esto provocará la acumulación de mensajes y disparará el consumo de CPU.
2. **Inundación y Desborde de Logs en Almacenamiento:** Un agente 24/7 genera escrituras masivas en el SSD de 240 GB. Si no se implementa rotación de logs, el llenado del disco detendrá tanto a Hermes como a los contenedores de Antigravity.
3. **Falta de Manejo de Estado en Caídas de Conexión:** Al alternar entre APIs, la falta de un sistema de persistencia liviano (SQLite/Redis) para el estado del contexto de la conversación provocará que Hermes pierda el hilo ante un failover (cambio de API por error).

---

## Calibración de Evidencias e Incertidumbres (GAP ANALYSIS)
**Certezas (1.0):**
- Infraestructura de hardware clara (i3, 8GB RAM, SSD 240GB).
- Carga computacional puramente en APIs externas.
- Canal operativo es Telegram.

**Riesgos Altos / Incertidumbres:**
- **Motor de Conmutación (Failover) [Certeza 0.4]:** No se han definido tiempos de timeout ni orden de prioridad en la contingencia de APIs.
- **Persistencia de Datos [Certeza 0.2]:** Falta definir el destino donde Hermes guarda los reportes de mantenimiento que extrae de los chats.

## 📝 Request For Information (RFI)
Para que este bloque sea accionable y generar los scripts sin fallos de ejecución, es necesario responder a:
1. **Prioridad de APIs y Fallback:** ¿Cuál es el orden exacto de preferencia? (Ej. 1. Google Gemini, 2. Groq...). ¿Cuántos reintentos fallidos antes de saltar a la siguiente?
2. **Persistencia del Contexto:** ¿Se necesita recordar el historial de conversación por usuario? Si es así, ¿se utilizará SQLite local?
3. **Destino de los Datos:** ¿Dónde se guardan los reportes ("Se cayó la presión en Mar del Plata")? ¿JSON local, Outlook o Base de datos?
4. **Mecanismo Actual del Bot:** ¿El bot actual de Telegram corre mediante script en Python o vía Open WebUI?
