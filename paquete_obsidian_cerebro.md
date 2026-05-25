# Paquete de Integración: Obsidian como Segundo Cerebro del Supervisor

Este módulo detalla cómo integrar **Obsidian** en la máquina local Ubuntu como la base de conocimiento estructurada (Bóveda / Vault) para el Supervisor. Los scripts de Antigravity y el bot de Hermes interactuarán de forma directa leyendo y escribiendo archivos Markdown y configurando Canvas visuales interactivos.

> [!IMPORTANT]
> **REGLAS DE DISEÑO DE LA BÓVEDA (VAULT):**
> Toda la información de locales, incidentes y manuales se mantendrá en texto plano (Markdown), permitiendo que la IA local y el bot busquen información de forma ultra-rápida utilizando archivos locales y con consumo cero de red o tokens externos.

---

## Pilares de la Integración con Obsidian

### 1. Estructura Jerárquica del Vault (Método de Carpeta Única)
Se creará una bóveda local en la máquina Ubuntu (ej: `~/SupervisorVault/`) con la siguiente jerarquía estructurada:
*   `📁 01_Locales/`: Una nota por sucursal (ej. `FVDP - Devoto Plaza.md`). Contiene dirección, contactos, supervisor a cargo y links a reportes recientes.
*   `📁 02_Reportes_Historicos/`: Subcarpetas por sigla del local. Guarda los resúmenes de reportes inyectados en Sheets en formato Markdown limpio.
*   `📁 03_Manuales_Soporte/`: Manuales técnicos en Markdown (Cimbali, Melitta, hornos) desglosados con etiquetas de códigos de error (ej: `#error-58`).
*   `📁 04_Alertas/`: Notas de incidentes activos. Al cerrarse el incidente, se archiva.

### 2. Organización Automática de Diálogos (Filtro de Ingesta)
Cuando **Hermes** finaliza una interacción por Telegram con un técnico o procesa una nota de voz:
1. Genera un archivo Markdown con el resumen de la conversación, la fecha y el nombre del técnico.
2. Lo deposita en la carpeta `📁 02_Reportes_Historicos/[SIGLA]/` del Vault de Obsidian.
3. Esto alimenta automáticamente el gráfico de relaciones y el historial local RAG del local sin intervención manual.

### 3. Dashboard Visual Interactivo (`.canvas`)
Obsidian utiliza un formato JSON abierto para sus lienzos o mapas mentales (`.canvas`). Desarrollaremos un script en Python que:
*   Genere y actualice un lienzo visual (`Resumen_Supervisor.canvas`).
*   Muestre tarjetas de colores para cada local (Rojo/Amarillo/Verde) según el estado de PPM o shots.
*   Conecte visualmente los locales con alertas críticas activas a sus notas de reporte correspondientes.

### 4. Consultas y RAG Local 100% Privado
Para las preguntas de Nivel 3 de los técnicos (ej: "Error 58 de Cimbali"):
*   Hermes ejecutará un script en segundo plano que realiza una búsqueda local en la carpeta `📁 03_Manuales_Soporte/` buscando el archivo del modelo de la máquina y la etiqueta `#error-58`.
*   Esto garantiza memoria ilimitada y velocidad instantánea, sirviendo el contexto correcto al LLM sin necesidad de cargar documentos enteros.

---

## Registro de Estado y Tareas Futuras
*   **Fecha de Registro:** 2026-05-25
*   **Estatus:** Planificado bajo el Roadmap Estratégico (NotebookLM & Obsidian Vault).
