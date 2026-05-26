# Manual Operativo del Supervisor

Este documento centraliza todas las funciones, estructuras, flujos y acciones del Supervisor y los Técnicos. Se organiza en bloques modulares que definen el ecosistema de trabajo y los procedimientos operativos.

---

## 🏢 Bloque 1: Estructura de Locales
*Detalle de la organización física, geográfica y digital de los locales bajo la supervisión.*

### 📊 Fuente de Verdad (Base de Datos)
*   **Planilla de Referencia (Spreadsheet V2)**: [Mostaza Locales Spreadsheet](https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing)
*   **Columnas Clave**:
    *   `LOCAL`: Nombre descriptivo de la sucursal (ej. `VILLA DEL PARQUE`, `SAN JUSTO`).
    *   `SIGLA SISTEMA`: Acrónimo de 3-5 caracteres único para integración automatizada con Mail y Telegram (ej. `FVDP`, `FSJU`).

### 📂 Estructura de Carpetas en Google Drive
Para garantizar consistencia visual y automatización de análisis de strings, la arquitectura en Google Drive se organiza bajo la siguiente directiva:
*   **Directorio Raíz**: `Mostaza Locales`
*   **Nomenclatura de Subcarpetas**: `[SIGLA SISTEMA] - NOMBRE LOCAL` (ej. `[FVDP] - VILLA DEL PARQUE`).
*   **Volumen Estimado**: ~110 directorios de sucursales creados de manera idempotente.

### ⚙️ Automatización del Despliegue
La creación y verificación de la estructura se gestiona a través del script de producción [supervisor_drive_generator.js](file:///home/cristian/Documentos/Supervisor/supervisor_drive_generator.js). Este script cuenta con:
1.  **Idempotencia Absoluta**: Evita duplicación de carpetas en ejecuciones repetidas.
2.  **Optimización O(1)**: Carga en memoria todas las subcarpetas existentes para evitar timeouts del límite de 6 minutos de Google Apps Script.
3.  **Aislamiento de Fallos**: Procesamiento de cada fila dentro de bloques individuales `try-catch`.

---

## 👥 Bloque 2: Técnicos (Pendiente)
*Próximo bloque a desarrollar: Registro de perfiles, especialidades y asignaciones.*

---

## 💬 Bloque 3: Flujo de Comunicación e Integración de Contexto (NotebookLM & Drive)
*Arquitectura de ingesta de información desde Emails y Telegram hacia la base de conocimiento del supervisor.*

### 📥 1. Canales de Entrada (Fuentes de Contexto)
El supervisor y los técnicos reportan novedades a través de:
*   **Correos Electrónicos (Email)**: Reportes semanales, presupuestos y auditorías formales.
*   **Canal/Grupo de Telegram**: Alertas rápidas, fotos de fallas y reportes de finalización de trabajos.

### ⚙️ 2. Motor de Ingesta Automatizado hacia Google Drive
Dado que las carpetas de Google Drive ya están creadas con la nomenclatura `[SIGLA SISTEMA] - NOMBRE LOCAL`, utilizaremos un script centralizado (Google Apps Script / Webhook de Telegram) para realizar el siguiente flujo:
1.  **Parseo de Strings**: El motor lee el asunto del correo o el texto del mensaje de Telegram buscando la `SIGLA SISTEMA` (ej. `[FVDP]`).
2.  **Identificación del Destino**: Localiza la carpeta correspondiente en Google Drive utilizando la caché de carpetas.
3.  **Registro Histórico**: Escribe un archivo Markdown o de Texto (ej. `bitacora.md` o `novedades_telegram.txt`) dentro de la carpeta del local con la fecha, canal de origen y contenido del mensaje.

### 🧠 3. Arquitectura en Google NotebookLM Pro (Análisis de Inteligencia de Alta Fidelidad)
Dado que posees una **cuenta Pro/Workspace de Google (con límite extendido de hasta 500 cuadernos)**, la estrategia de un cuaderno individual por local es **100% viable y recomendada** para mantener un aislamiento absoluto de la información de cada sucursal.

Como NotebookLM no cuenta con una API pública para que agentes externos escriban directamente en su interfaz, establecemos un **puente bidireccional basado en Google Drive**:

#### 🔄 El Puente de Sincronización Dinámica:
1.  **Capa de Ingesta (Antigravity & Integraciones)**: Nosotros (Antigravity) y los scripts de automatización procesamos los correos y mensajes de Telegram, guardando el contenido como archivos de texto o Markdown en la carpeta específica de Drive del local (ej. `Mostaza Locales/[FVDP] - VILLA DEL PARQUE/bitacora.md`).
2.  **Capa de Lectura y Sincronización (NotebookLM)**: Cada uno de los 109 cuadernos de NotebookLM se crea vinculando su carpeta de Google Drive correspondiente como **Fuente Principal (Source)**. NotebookLM sincroniza automáticamente cualquier archivo nuevo o modificado dentro de esa carpeta.
3.  **Capa de Consulta (Supervisor)**: Tú, como supervisor, puedes ingresar a NotebookLM y consultar de forma aislada e inteligente el cuaderno de cualquier local, con la certeza de que el contexto está actualizado en tiempo real.
4.  **Capa de Auditoría para Antigravity**: Dado que los documentos fuente viven en Google Drive, nosotros desde Antigravity podemos leer, modificar o auditar todo el historial de la sucursal leyendo directamente los archivos de Drive mediante el navegador o Apps Script, cerrando el círculo operativo.

---

## ⚡ Bloque 4: Acciones del Supervisor (Pendiente)
*Próximo bloque a desarrollar: Tareas diarias, auditorías, asignación de órdenes de trabajo.*

---

## 🔧 Bloque 5: Acciones de los Técnicos (Pendiente)
*Próximo bloque a desarrollar: Protocolos de resolución, reporte de horas y uso de repuestos.*
