# Auditoría Retrospectiva y Plano de Arquitectura (PIT-V3)

## Proceso de Compilación de Historial

**Mapeo de la Evolución del Proyecto:**
El usuario inició explorando un sistema de productividad en 4 niveles para integrar las herramientas de IA de Google (NotebookLM, Gemini, Gems, Workspace). Rápidamente intentó transponer el proyecto "Hermes" (asociado a un equipo técnico de mantenimiento en calle) a este ecosistema. 
- Inicialmente se evaluó Google Chat con @Gemini invocable como centro de comunicación similar a Slack.
- Luego se barajó la opción de centralizar todo vía correo electrónico en Gmail usando un Gem como "Supervisor de Mantenimiento".
- Finalmente, se concluyó que saltar al mail era operativo y culturalmente inviable para técnicos acostumbrados a la inmediatez de la mensajería instantánea (WhatsApp). 
- **Se seleccionó Google Chat** como el eje central por su similitud funcional con WhatsApp y su capacidad nativa de integración con Google Drive y Google Sheets sin salir de la infraestructura de Google.

**Enfoques y Tecnologías Rechazados:**
- **Telegram / WhatsApp:** Descartados como centros operativos finales para evitar la fuga de información, la dispersión de archivos y la falta de control administrativo y de auditoría sobre los datos técnicos.
- **Flujo Exclusivo por Gmail (Correo Electrónico):** Rechazado debido a la fricción operativa y falta de agilidad en el trabajo de campo para los técnicos.
- **Uso de Servidores o Infraestructura Externa Dedicada:** Descartado explícitamente para capitalizar la cuenta Pro del usuario y delegar la resiliencia de la infraestructura en Google.

**Núcleo Inmutable del Proyecto:**
El objetivo técnico real es el despliegue de un Ecosistema de Supervisión Semi-Automatizado de Mantenimiento (en clave: Proyecto Hermes-Workspace). El sistema debe centralizar reportes técnicos de campo (ingresados mediante una PWA/Formularios existentes) en una base de datos plana (Google Sheets), permitiendo la auditoría, la asistencia técnica interactiva en un canal de chat (Google Chat) mediante un modelo de lenguaje con base de conocimiento (Gem), y la generación automatizada y no-interactiva de reportes de cierre diarios mediante secuencias de comandos programadas.

---

## ⚠️ POR QUÉ ESTO FALLARÁ
El diseño actual asume una interoperabilidad mágica que colisionará con las limitaciones API estrictas de Google Workspace:

1. **Limitaciones de Workspace:** Los Gems personalizados y las menciones directas a @Gemini en los Espacios de Google Chat están fuertemente limitados a licencias corporativas de Google Workspace (Enterprise/Business) o planes específicos de Google One AI Premium con Google Workspace Add-ons activados; si el ecosistema se despliega sobre cuentas @gmail.com personales/Pro estándar, las APIs de Chat bloquearán la inyección directa del Gem personalizado.
2. **Cuellos de botella por cuotas:** La sincronización entre la PWA externa y Google Sheets mediante Google Apps Script generará cuellos de botella por cuotas de ejecución diaria (Daily Quotas: 90 min/día en cuentas gratis/pro estándar) si los técnicos saturan la carga de archivos multimedia pesados (videos/audios) en horas pico.
3. **Fallos silenciosos en Apps Script:** El diseño de Apps Script propuesto como "ejecución en segundo plano" es propenso a fallar de forma silenciosa si los tokens de autenticación OAuth2 expiran o si los formatos de las celdas de la hoja de cálculo varían, provocando reportes truncados o duplicados al final del día sin que el supervisor reciba alertas críticas del fallo.

---

## EVIDENCE & UNCERTAINTY CALIBRATION
- **Módulo 1: Repositorio de Base de Conocimiento (Drive/Sheets)**
  - *Principio Base:* Arquitectura Basada en Datos Compartidos (Shared-Data Pattern).
  - *Certeza (Cs):* 1.0. Acordado explícitamente que los manuales se alojan en Drive y los reportes caen en Sheets.
- **Módulo 2: Interfaz de Comunicación de Campo (Google Chat + App Android)**
  - *Principio Base:* Comunicación Síncrona Orientada a Eventos / Tópicos.
  - *Certeza (Cs):* 0.95. Confirmado tras rechazar Gmail y priorizar la similitud con grupos de mensajería instantánea.
- **Módulo 3: Motor de Inferencia (Gem Customizado / "Supervisor Técnico")**
  - *Principio Base:* Generación Aumentada por Recuperación (RAG) integrada en cliente.
  - *Certeza (Cs):* 0.85. Definido el prompt y la base de conocimiento. Riesgo leve por viabilidad técnica exacta según el tipo de cuenta final.
- **Módulo 4: Engine de Automatización de Cierre (Apps Script / Webhooks)**
  - *Principio Base:* Automatización No-Interactiva Basada en Tiempo (Cron-job pattern).
  - *Certeza (Cs):* 0.70. Se propuso como alternativa proactiva. Riesgo: No se ha definido la estructura exacta de datos de la PWA que inyecta datos a Sheets.

---

## 📝 GAP ANALYSIS & RFI (REQUEST FOR INFORMATION)
Los datos del historial no permiten que Antigravity autogestione la implementación al 100% de manera segura. Se detiene el desarrollo detallado de código hasta obtener respuesta a los siguientes puntos críticos:
1. **Tipo de Cuenta de Google Exacta:** ¿La cuenta "Pro" mencionada es una suscripción Google One AI Premium sobre un correo @gmail.com personal o es una cuenta de Google Workspace Business/Enterprise con dominio propio (@tudominio.com)?
2. **Mapeo de la PWA Existente:** ¿Cómo inyecta la PWA actual los datos en Google Sheets? ¿Utiliza la API de Google Sheets mediante una Service Account o requiere un endpoint HTTP (Webhook/Apps Script Web App URL) expuesto?
3. **Esquema de Datos de Asignación Diaria:** ¿Dónde se registran o se asignan originalmente esas tareas matutinas a los técnicos (Google Calendar, una pestaña en Sheets, o dentro de la propia PWA)?

---

## 🏗️ BLUEPRINT DE ENTREGABLE PARA ANTIGRAVITY
*(Estructura preliminar de arquitectura preparada para su inicialización en el entorno una vez resuelto el RFI)*

### 1. ARQUITECTURA GENERAL & DIRECTORIOS (TREE)
**Nombre Técnico del Proyecto:** `hermes-workspace-core`
**Stack y Dependencias:** Google Apps Script (V8 Engine), Google Sheets API v4, Google Chat API (Cards v2 / Chat Webhooks), Advanced Drive Service.

```text
hermes-workspace-core/
├── config/
│   ├── env.json                 # IDs de Carpetas de Drive, Hojas de Cálculo y Webhooks
│   └── prompt_supervisor.txt    # System Prompt oficial para el comportamiento del Gem
├── src/
│   ├── Code.js                  # Punto de entrada principal de Google Apps Script
│   ├── automation.js            # Lógica del Trigger de cierre diario (Generación de Reportes)
│   ├── webhookHandler.js        # Receptor de payloads provenientes de la PWA técnica
│   └── chatNotifier.js          # Formateador y despachador de tarjetas a Google Chat
├── test/
│   └── mockPayloads.js          # Datos de prueba para simular reportes de campo
└── README.md                    # Documentación operativa para el entorno Antigravity
```

### 2. PROTOCOLO DE FLUJO DE DATOS & ESTADO
- **Gatillos (Triggers):**
  - *Trigger por Evento (HTTP POST):* La PWA envía un payload JSON al finalizar un mantenimiento.
  - *Trigger Temporal (Time-Driven Cron):* Ejecución diaria automática a las 18:00 h.
- **Lógica de Procesamiento:**
  - Validación y parseo asíncrono del payload de la PWA en `webhookHandler.js`.
  - Añadido de datos estructurados a Google Sheets.
  - Archivos binarios se almacenan en Drive; URL anexada a la celda correspondiente.
  - A las 18:00 h, `automation.js` despierta y consolida las filas del día.
- **Salidas (Outputs):**
  - Registro persistente en Sheets.
  - Envío automatizado de Card v2 al Espacio de Google Chat del Supervisor.

### 3. CONFIGURACIÓN DE AUTOMATIZACIÓN Y SCRIPTS (CRÍTICO)
Para garantizar ejecución autónoma y no-interactiva:

```javascript
function installHermesTriggers() {
  // Borrar triggers previos para mitigar ejecuciones duplicadas redundantes
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  // Configurar trigger de cierre automatizado diario a las 18:00
  ScriptApp.newTrigger('executeDailyClosureReport')
           .timeBased()
           .everyDays(1)
           .atHour(18)
           .nearMinute(0)
           .create();
}
```

**Manejo de Errores e Idempotencia:**
Si la llamada a la API falla o la cuota se agota, el script realiza hasta 3 reintentos con pausa exponencial (Exponential Backoff). Si el error persiste, salta la interfaz de chat y escribe un log estructurado en una pestaña aislada (`/logs`) en Sheets, previniendo loops infinitos.
