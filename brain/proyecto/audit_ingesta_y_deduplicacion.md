# Informe de Auditoría Integral: Ingesta, Almacenamiento y Deduplicación de Reportes

Este informe presenta el análisis técnico de punta a punta del **Proyecto Supervisor (Hermes)**, enfocándose en la trazabilidad de los informes técnicos, los mecanismos para evitar duplicados y el mapa de almacenamiento multicapa.

---

## 1. Almacenamiento de Informes por Email y Canales

### ¿Los informes por Email se guardan en Google Drive?
**SÍ.** El flujo automatizado para los correos que ingresan por Gmail funciona de la siguiente manera:
1. **Descarga:** El módulo `ingestor_automatico.py` lee Gmail por IMAP (`UNSEEN`), filtra adjuntos `.pdf` que inician con `MTZ_` y los guarda en la carpeta `/entrantes/`.
2. **Procesamiento y Extracción:** `motor_supervisor.py` parsea el texto del PDF, identifica la sucursal (sigla), técnico, ticket, PPM de agua y contador de shots.
3. **Google Sheets:** `fase3_sheets.py` inyecta los datos en la planilla gerencial "La Sábana".
4. **Google Drive:** `archivador_drive.py` mapea la sigla del ticket a la carpeta oficial del local en Drive y sube el PDF original a la subcarpeta `Reportes`.
5. **Copia Física Local:** Una vez confirmado el éxito en Drive, el PDF local se mueve para resguardo físico permanente a `/home/cristian/PROYECTOS/Supervisor-Project/brain/locales/PDFs_Originales/`.

---

## 2. Mecanismo de Control y Prevención de Duplicados

Actualmente el sistema cuenta con **tres capas independientes de control de duplicación**:

| Capa | Módulo | Criterio de Control | Comportamiento |
| :--- | :--- | :--- | :--- |
| **1. Google Sheets** | `fase3_sheets.py` | Compara `TICKET` + `SIGLA` | Si el ticket ya existe en "La Sábana", omite la inserción de la fila. |
| **2. Ficha Local Markdown** | `gestion_locales.py` | Compara presencia de `Ticket #[NRO]` | Si la intervención ya está registrada en el `.md` del local, omite agregarla al historial. |
| **3. Auditoría en Drive** | `auditar_y_limpiar_duplicados_drive.py` | Escaneo semántico + patrones de archivo | Corre en crontab los domingos a las 3:00 AM. Identifica archivos repetidos en Drive y elimina duplicados redundantes. |

### ⚠️ Vulnerabilidades / Ineficiencias Detectadas en la Deduplicación:
* **Falta de Hash Criptográfico en Ingesta:** Si un reporte ingresa **sin número de ticket** (ej. medición hídrica de rutina o ticket no detectado por OCR), el control por ticket se saltea.
* **Procesamiento Cruzado:** Si el mismo PDF exacto se envía por Email y luego por Telegram, el sistema procesa el archivo completo en ambas vías antes de que la hoja de Sheets descarte la fila.

### 💡 Propuesta de Mejora (Deduplicación Absoluta):
Implementar una tabla liviana de hashes SHA-256 (`hash_reportes.db`). Al recibir un PDF (por Email, Telegram o Formulario), se calcula la firma SHA-256 de su contenido binario. Si el hash ya fue procesado en el pasado, **se frena el archivo inmediatamente en el paso 0**, bloqueando duplicados antes de tocar Sheets, Drive o Telegram.

---

## 3. Mapa de Almacenamiento Multicapa

Cada informe o intervención procesada se almacena en 5 ubicaciones sincronizadas:

```
                          [ INGESTA DE PDF ]
                     (Gmail / Telegram / Form)
                                 │
                                 ▼
                     [ Parser: motor_supervisor ]
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
 [ 1. Google Sheets ]    [ 2. Google Drive ]     [ 3. Resguardo Físico ]
 Matrix "La Sábana"      Subcarpeta Reportes     brain/locales/PDFs_Originales
                         del Local en la Nube
                                                         │
                                                         ▼
                                               [ 4. Ficha Markdown ]
                                               brain/locales/[SIGLA].md
                                               (Bóveda Obsidian)
                                                         │
                                                         ▼
                                               [ 5. NotebookLM Pro ]
                                               Sincronización vía CLI 'nlm'
```

1. **Google Sheets ("La Sábana"):** Matriz de control tabular para seguimiento gerencial.
2. **Google Drive (Nube):** Carpeta organizada por local (`[SIGLA - Nombre]/Reportes/`) para consulta de adjuntos originales.
3. **Resguardo Físico Local:** Almacenamiento interno en la Mini PC Ubuntu (`brain/locales/PDFs_Originales/`).
4. **Ficha Markdown (Obsidian / Cerebro RAG):** Documento consolidado por local (`brain/locales/[SIGLA].md`) que guarda el historial de intervenciones y parámetros técnicos (PPM, shots, equipo, serie).
5. **Google NotebookLM Pro:** Cuadernos independientes por sucursal en la nube de Google para análisis de inteligencia de alta fidelidad (sincronizados automáticamente vía CLI `nlm`).

---

## 4. Estado Actual del Proyecto: Punta a Punta

### ✅ Lo que trabaja de forma EFICIENTE y ESTABLE:
- **Ingesta de PDFs:** Procesamiento rápido por Gmail y Telegram.
- **Confirmación Reactiva por Telegram:** Mensajes inmediatos de recepción de reportes para técnicos.
- **Monitoreo de Tickets ERP:** Chequeo cada 10 minutos de tickets de Mostaza Linkup (incluyendo Caseros `FMMCB`).
- **Reportes de Salud y Calidad:** Monitoreo de recursos del servidor, auditoría semanal de manuales QA y balance semanal de errores.

### 🗑️ Lo que fue DEPURADO Y DESCONTINUADO (Limpieza realizada):
- **WhatsApp Web:** Módulo Selenium y reinicio de Chrome desactivados (0% impacto en RAM).
- **Procesamiento de Fotos y Videos:** Eliminado para evitar gastar cuotas de IA y prevenir *timeouts*.
- **Orquestador Kanban (+48hs):** Reporte masivo desactivado de `crontab`.
- **Recordatorios Personales:** Desactivados del bot para centralizar seguimiento en Gemini.
- **Alertas de Errores Técnicos:** Redirigidas silenciosamente a logs locales en lugar de spamear a Cristian.

---

## 5. Recomendación de Próximos Pasos
1. **Activar Deduplicador Criptográfico SHA-256:** Crear la base de hashes binarios de PDFs para garantizar 0% duplicados sin importar la vía de entrada o la falta de número de ticket.
2. **Mantener el flujo actual de Telegram:** Ingesta de PDFs, notificaciones de tickets y consultas privadas con Hermes.
