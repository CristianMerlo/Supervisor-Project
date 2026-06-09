# Skills de Gestión y Supervisión (Rol de Supervisor)

Este documento detalla las habilidades conceptuales y lógicas de gestión que el Agente Hermes aplicará para supervisar activamente al equipo de técnicos de mantenimiento.

---

## 🕒 1. Auditoría de Tiempos y Desempeño (SLA Tracking)
*   **Función:** Hermes calculará el tiempo transcurrido entre el `CHECK-IN` y el `CHECK-OUT` en cada local para medir la duración real de cada servicio.
*   **Valor para el Negocio:**
    *   Mapear la duración promedio de reparación por tipo de falla o local.
    *   Detectar desvíos: Si un técnico lleva más de 4 horas en estado de `CHECK-IN` sin registrar salida, Hermes enviará un mensaje recordatorio o una alerta preventiva para verificar si surgió algún obstáculo en el local.

---

## 📊 2. Conciliación Horaria de Jornada (Doble Registro)
*   **Función:** Cruzar la duración real de los registros de WhatsApp con las horas de labor declaradas en los PDFs y el Formulario.
*   **Valor para el Negocio:** 
    *   Identificar discrepancias: Si el técnico estuvo físicamente 2 horas en el local según WhatsApp, pero declaró 8 horas en el reporte formal, Hermes registrará una alerta de auditoría por "Inconsistencia de Horas".

---

## 🗣️ 3. Análisis de Claridad y Tono (NLP)
*   **Función:** Evaluar la calidad de las descripciones del trabajo técnico enviadas en el chat y en los reportes.
*   **Valor para el Negocio:**
    *   Hermes verificará que las explicaciones de los diagnósticos sean claras y profesionales (evitando textos demasiado cortos o incomprensibles).
    *   Si detecta frustración, urgencia extrema o falta de datos críticos en el texto, puede pedirle sutilmente al técnico más detalles antes de cerrar la jornada.

---

## 🚨 4. Lógica de Escalado de Incidentes Críticos
*   **Función:** Detección de palabras clave críticas de bloqueo en las conversaciones (ej. *"máquina rota"*, *"sin repuesto"*, *"no se puede reparar"*).
*   **Valor para el Negocio:**
    *   En lugar de esperar a que leas el reporte al final del día, Hermes abrirá de inmediato una alerta en `Alertas_Activas` y te la notificará por Telegram para que puedas gestionar el repuesto o la asistencia de inmediato.
