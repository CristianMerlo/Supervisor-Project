# Pendientes Menores y Manuales Técnicos - Brain de Hermes

Este documento detalla las tareas menores del sistema y actúa como checklist/inventario de los manuales de servicio y guías técnicas que deben ser recolectados e integrados en la carpeta `brain/manuales/` para alimentar la base de conocimiento de la IA.

---

## 📋 Tareas y Pendientes Menores

- [ ] **Limpieza de historial local de Fichas**: Limitar el log de intervenciones local en `brain/locales/*.md` a las últimas 15-20 entradas.
- [ ] **Filtro de logs de depuración**: Silenciar o rotar logs de WhatsApp Web si superan los 50MB en la PC.
- [ ] **Monitoreo de UPS**: Programar el aviso por corte de energía vía Telegram usando `upsmon` cuando la UPS cambie a modo batería.

---

## 📚 Checklist de Manuales para la Base de Conocimiento
> [!NOTE]
> Colocar los archivos PDF, de texto o Markdown de estas guías en la ruta local: [brain/manuales/](file:///home/cristian/Documentos/Supervisor/brain/manuales/). Hermes podrá escanearlos y utilizarlos para dar soporte preciso en el diagnóstico de fallas a los técnicos en campo.

### ☕ Cafeteras Comerciales
- [ ] **La Cimbali M26 / M39**: Manual técnico, códigos de error y procedimientos de calibración de bombas/presión.
- [ ] **Expobar Megacrem / Markus**: Despiece de caldera, esquemas eléctricos y manual de usuario/servicio.
- [ ] **Wega Pegaso / Polaris**: Guía de mantenimiento de grupos y parámetros de temperatura.

### 🧪 Filtrado e Hidráulica (Tratamiento de Agua)
- [ ] **Ablandadores de Agua Manuales/Automáticos**: Guía de regeneración de resina con sal y mantenimiento de válvulas.
- [ ] **Sistemas de Ósmosis Inversa**: Manuales de filtros, recambio de membranas y rangos óptimos de PPM/presión.
- [ ] **Filtros de Sedimentos y Carbón Activado**: Frecuencias de recambio y lavado a contracorriente.

### ⚙️ Molinos y Periféricos
- [ ] **Molinos Mazzer (Super Jolly / Kony)**: Manual de calibración de molienda y cambio de fresas.
- [ ] **Molinos Fiorenzato**: Guía de mantenimiento rápido y limpieza de conductos de salida de café.

---

## 🛠️ Cómo agregar un nuevo manual al cerebro
1. Obtener el archivo en formato **PDF**, **Texto** o **Markdown**.
2. Guardarlo en la carpeta `/home/cristian/Documentos/Supervisor/brain/manuales/`.
3. Informarle a Hermes: *"Hermes, leé los nuevos manuales del cerebro"* para que actualice su índice de conocimiento.
