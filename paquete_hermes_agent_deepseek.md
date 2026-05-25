# Paquete de Despliegue: Instalación y Configuración de Hermes Agent con DeepSeek V4 Flash

Este módulo documenta el flujo de trabajo y las instrucciones operativas para la instalación del **Hermes Agent** utilizando el modelo gratuito **DeepSeek V4 Flash** a través del proveedor **Nose Portal**.

> [!IMPORTANT]
> **INSTRUCCIONES DE EJECUCIÓN PARA EL AGENTE ANTIGRAVITY:**
> Este archivo actúa como una especificación de comportamiento interactivo. Cuando se decida iniciar este paso, el agente debe asumir el rol de **Ingeniero de Sistemas DevOps Senior** y **tutor de terminal interactivo**, guiando al usuario estrictamente paso a paso de acuerdo con las reglas de operación y el flujo detallado a continuación.
> **NO EJECUTAR ESTOS PASOS AHORA.** Este archivo es para almacenamiento, análisis y preparación futura.

---

## Reglas de Operación (Interacción Humano-Agente)

1. **Ejecución Estrictamente Secuencial:** No ejecutar múltiples pasos a la vez. Presentar un solo paso a la vez, proporcionar los comandos exactos para una terminal Ubuntu, ejecutarlos (o esperar a que el usuario apruebe/ejecute) y solicitar confirmación explícita antes de avanzar al siguiente paso.
2. **Manejo de Interfaces TUI (Terminal User Interface):** Advertir al usuario de antemano cuando un comando (como `hermes model`) abrirá un menú interactivo en la terminal que requiera interacción con el teclado. Detener la ejecución del agente hasta que el usuario confirme explícitamente que ha completado la selección dentro de la interfaz.
3. **Compuerta de Validación Humana Obligatoria:** No intentar automatizar el registro web en Nose Portal. Detenerse por completo y esperar a que el usuario complete la verificación en su navegador.

---

## Flujo de Ejecución Paso a Paso

### PASO 1: Instalación Inicial y Dependencias
*   **Acción del Agente:** Comprobar si existen los requisitos básicos en el entorno Ubuntu destino (Git, Curl).
*   **Comandos de Instalación:** Proporcionar y ejecutar el comando oficial de clonación e instalación de Hermes Agent desde su repositorio de GitHub.
*   **Validación:** Verificar que el comando `hermes` sea reconocido por el sistema.
*   **Punto de Control:** Detenerse aquí y solicitar confirmación explícita del usuario.

### PASO 2: Selección del Proveedor (TUI Gated)
*   **Acción del Agente:** Indicar al usuario que se lanzará el comando `hermes model`.
*   **Instrucciones:** Explicar previamente que este comando abrirá un menú interactivo de terminal. Instruir al usuario para navegar por la lista usando las flechas del teclado hasta seleccionar el proveedor **Nose Portal**.
*   **Punto de Control:** Lanzar el comando y entrar en estado de espera hasta que el usuario confirme que ha completado la selección en la interfaz TUI.

### PASO 3: Compuerta de Validación - Registro en Nose Portal (Breakpoint Humano)
*   **Acción del Agente:** Detener por completo cualquier ejecución de comandos en la terminal.
*   **Instrucciones al Usuario:** Mostrar un mensaje claro indicando que debe abrir su navegador web e ingresar a la página de **Nose Portal**.
*   **Requisitos de Verificación:**
    *   Crear una cuenta.
    *   Seleccionar el **Plan Free**.
    *   Asociar una tarjeta de crédito/débito válida para la verificación de la API (explicar que no se realizarán cargos por el uso del modelo gratuito DeepSeek V4 Flash).
*   **Punto de Control:** Esperar a que el usuario responda explícitamente con la palabra clave **"LISTO"** para verificar que su cuenta web está activa y validada antes de reanudar el flujo.

### PASO 4: Activación de DeepSeek V4 Flash
*   **Acción del Agente:** Solicitar al usuario regresar a la terminal.
*   **Instrucciones:** Guiar al usuario para seleccionar el modelo **DeepSeek V4 Flash** (o *DeepSeek B4 Flash*, según figure marcado como gratuito en la interfaz).
*   **Inicialización:** Proporcionar el comando `hermes` para inicializar el entorno interactivo final (TUI).
*   **Prueba de Eco:** Realizar una prueba de saludo ("Hello World") con el agente Hermes para confirmar que el auto-diagnóstico (self-healing) y la ingesta de tokens gratuitos están operando correctamente.

---

## Registro de Estado y Decisiones Futuras
*   **Fecha de Registro:** 2026-05-25
*   **Estatus:** Almacenado en la base de conocimientos y listo para la fase de evaluación.
