# Análisis Arquitectónico: Proyecto Supervisor Hermes

Este documento desglosa el diseño arquitectónico y las funciones operativas del **Proyecto Hermes**. Sirve como guía de ruta para implementar de manera modular cada bloque del sistema, permitiendo un desarrollo progresivo y escalable.

## 🏛️ Paradigma de Infraestructura Híbrida

El sistema evita la fragilidad y los costos de los servidores VPS convencionales y las API de pago mediante una arquitectura dividida en dos capas:

1. **Capa Orquestadora Local (Ubuntu + Antigravity):**
   *   Computadora-Servidor física funcionando 24/7.
   *   Ejecuta los scripts, automatizaciones y cronjobs.
   *   Aísla la carga de procesamiento localmente sin costo recurrente en dólares.
2. **Capa del Ecosistema Google (Nube del Supervisor):**
   *   **Google Sheets:** Actúa como motor de base de datos relacional (gratuito, persistente y auditable).
   *   **Google Drive (Unidades Compartidas):** Sistema de archivos para almacenamiento de PDFs y fotografías organizados jerárquicamente.
   *   **NotebookLM + Gemini/Gems:** Motor de inteligencia y RAG (Retrieval-Augmented Generation), que mantiene el contexto de los documentos sin alucinaciones.

---

## 🧩 Desglose de Implementación por Bloques

Para llevar este diseño a la realidad, el proyecto se divide en las siguientes fases o módulos independientes que pueden ser programados paso a paso:

### Bloque 1: Ingestión, Soberanía y Validación (El Puente Terreno-Nube)
Este bloque gestiona cómo llega la información desde la calle hasta la base de datos central.
*   **Origen:** PWA V12.5 (Offline-First) exporta un PDF estandarizado (prefijo `MTZ_`).
*   **Acción 1:** Recepción del PDF (vía email o subida directa).
*   **Acción 2:** Guardado automático en una estructura jerárquica dentro de Google Drive.
*   **Acción 3:** Validación de identidad: Cruce del ID del técnico emisor con la nómina oficial (Fernando Soria, Tomas Vera, etc.) para asegurar autenticidad.

### Bloque 2: Parser y Extracción Documental (El Cerebro Lector)
Automatiza la entrada de datos (Data Entry).
*   **Trigger:** Detección de un nuevo archivo `MTZ_` en la bandeja de entrada o Drive.
*   **Acción 1:** Uso de *Gemini Vision API* o *Google Document AI* para extraer datos clave en formato JSON (Técnico, Ticket, Local, Horas, Viáticos, Shots, PPM Agua, etc.).
*   **Acción 2:** Inserción de esta data estructurada como una nueva fila en Google Sheets (`Historial_Reportes`).
*   **Acción 3:** Renombrado y archivado del PDF original.

### Bloque 3: Motor de Reglas de Negocio (El Semáforo LED y Jerarquía Hídrica)
Aplica las políticas de la empresa sobre los datos extraídos.
*   **Trigger:** Inserción de nuevos datos en Sheets.
*   **Acción 1 (Prioridad Hídrica):** Evaluación del nivel de PPM y estado de filtros. Si los valores superan el umbral crítico, se ignora el estado mecánico de la cafetera.
*   **Acción 2:** Cambio del estado general a **ROJO (CRÍTICO)** y derivación automática del ticket a la pestaña de `Alertas_Preventivas`.

### Bloque 4: Auditoría de Campo y Visión Computacional
Validación antifraude y control de calidad de las intervenciones.
*   **Trigger:** Recepción de evidencias fotográficas adjuntas al ticket.
*   **Acción 1:** Análisis de imágenes mediante IA para verificar correspondencia de equipo (marca/modelo) e inteligibilidad de la foto.
*   **Acción 2:** Validación del "antes y después" (ej. filtro nuevo visible).
*   **Acción 3:** Si la confianza (Score) es baja, marcar en Sheets como "Pendiente de Auditoría" y notificar al técnico para que resuba la imagen.

### Bloque 5: Conciliación Financiera de Viáticos
Control automatizado de gastos.
*   **Trigger:** Barrido diario de la bandeja de entrada del Supervisor.
*   **Acción 1:** Búsqueda de facturas de transporte oficiales (Uber/Cabify).
*   **Acción 2:** Extracción del costo, hora y geolocalización.
*   **Acción 3:** Cruce de esta suma real contra lo declarado en el campo `Viáticos_ARS` de la PWA.
*   **Acción 4:** Generación de alerta de auditoría si la desviación supera el 10%.

### Bloque 6: Orquestación Predictiva de Mantenimiento
Paso de mantenimiento reactivo a proactivo.
*   **Trigger:** Actualización del campo `Contador_Shots`.
*   **Acción 1:** Cálculo diferencial entre el nuevo valor y el histórico para obtener el consumo promedio diario de esa sucursal.
*   **Acción 2:** Proyección matemática para predecir cuándo se alcanzará el límite de desgaste de piezas (ej. 10,000 shots).
*   **Acción 3:** Creación automática de una Orden de Trabajo (OT) preventiva en agenda 5 días antes del vencimiento proyectado.

### Bloque 7: RAG Local y Aislamiento de Memoria Histórica
Interacción natural para el Supervisor sin riesgo de mezclar datos entre las 120 sucursales.
*   **Trigger:** Consulta del Supervisor en lenguaje natural (ej. *"¿Cómo está el filtrado en San Justo?"*).
*   **Acción 1:** Traducción de la intención a un filtro de código estricto (`Sigla_Sistema` = `FSJU`).
*   **Acción 2:** Ejecución de RAG (recuperación de contexto) **exclusivamente** sobre los documentos y filas de esa sucursal en particular.
*   **Acción 3:** Generación de la respuesta precisa, citando intervenciones reales y recientes.

### Bloque 8: Comunicación Asíncrona y Escalado
Sistema de alertas automáticas para asegurar el cumplimiento.
*   **Trigger:** Scripts periódicos en Ubuntu evaluando tiempos de respuesta en Sheets.
*   **Nivel 1:** Bot envía mensaje directo por Google Chat (Spaces) al técnico si hay demora en el envío del informe post-jornada.
*   **Nivel 2:** Alerta secundaria preguntando si hay un obstáculo bloqueando el trabajo.
*   **Nivel 3:** Alerta privada al Supervisor resumiendo los tickets críticos que llevan más de 24 horas sin resolución por parte del técnico.
