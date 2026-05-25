# Metodología de Desarrollo GSD (Get Shit Done) - Protocolo de Orquestación

Este documento define la metodología conceptual **GSD (Get Shit Done)**, diseñada como una máquina de estados para guiar el desarrollo de software modular de forma aislada, previniendo la putrefacción de contexto y controlando los ciclos de corrección autónoma.

> [!IMPORTANT]
> **INSTRUCCIONES DE EJECUCIÓN PARA EL AGENTE ANTIGRAVITY:**
> Este archivo representa una especificación de comportamiento y gestión de estado. No debe ejecutarse de forma inmediata. Sirve como base para orquestar futuros desarrollos en fases controladas y con límites claros de recuperación autónoma (self-healing/auto-debugging).

---

## Estructura de Estado Persistente (`.gsd_state.json`)

Para asegurar la continuidad entre sesiones y ejecuciones, el estado se registra en la raíz del proyecto correspondiente bajo la siguiente estructura:

```json
{
  "proyecto": null,
  "fase": "IDLE",
  "framework_testing": null,
  "retry_count": 0,
  "max_retries": 5
}
```

---

## Protocolo de Interrupción y Alerta (Límite de Escape)

Si en cualquier punto del bucle de verificación de errores el valor de `retry_count` alcanza o supera **5**:
1. **Detener:** Interrumpir inmediatamente toda generación de código o intentos de corrección automática.
2. **Reportar:** Generar un reporte técnico detallado con el error de salida, los archivos modificados y el diagnóstico del estado actual.
3. **Notificar:** Invocar de forma autónoma el script `.gsd_core/alert_gateway` (o simular la llamada mediante notificaciones de sistema habilitadas como Telegram/Email).
4. **Congelar:** Entrar en estado de congelamiento (`FREEZE`) y solicitar la intervención explícita del usuario. No realizar más acciones hasta que el contador sea restablecido manualmente.

---

## Pipeline de Ejecución de Estados (Los 6 Comandos GSD)

### 1. `/gsd-new-project`
*   **Acciones:** Lee el espacio de trabajo. Pregunta explícitamente al usuario qué desarrollo quiere iniciar (ofreciendo opciones contextuales) y qué framework de pruebas utilizará (ej: PyTest, Jest, Bash automation).
*   **Destino:** Crea la carpeta del proyecto, inicializa `.gsd_state.json` y setea la fase a `"DISCUSSION"`.

### 2. `/gsd-discuss-phase`
*   **Acciones:** Abre un debate técnico controlado sobre ideas de arquitectura.
*   **Restricción:** No se escribe código de producción. Solo se refinan requerimientos lógicos. Al finalizar, cambia la fase a `"PLANNING"`.

### 3. `/gsd-plan-phase`
*   **Acciones:** Genera el diseño técnico, mapa de arquitectura, definición de módulos y especificaciones de archivos. Define la suite de testing.
*   **Destino:** Cambia la fase a `"EXECUTION"`.

### 4. `/gsd-execute-phase`
*   **Acciones:** Instancia un subcontexto fresco, escribe el código de forma modular y limpia, y guarda los archivos en su directorio.
*   **Destino:** Cambia la fase a `"VERIFICATION"`.

### 5. `/gsd-verify-work`
*   **Acciones:** Ejecuta las pruebas automáticas en el entorno.
*   **Lógica de Flujo:**
    *   **Si pasan:** Fase cambia a `"SHIP"`, limpia `retry_count` a 0 e informa del éxito.
    *   **Si fallan:** Incrementa `retry_count` en 1. Si alcanza 5, ejecuta el *Protocolo de Interrupción*. Si es menor a 5, analiza el error, modifica el archivo afectado autónomamente y re-ejecuta `/gsd-verify-work`.

### 6. `/gsd-ship`
*   **Acciones:** Despliega, empaqueta o entrega el código en el directorio final, genera un resumen de la arquitectura, limpia `.gsd_state.json` a `"IDLE"` y cierra la sesión.
