# Tareas Pendientes: Integración UPS y Telegram

## Alerta de Corte de Luz (Modo UPS) vía Telegram
**Estado**: 🕒 Pendiente (A desarrollar una vez que el bot de Telegram esté bien definido y estabilizado).

**Objetivo**:
Configurar el demonio de NUT (`upsmon`) para que dispare un aviso automático a través del bot de Telegram del proyecto de Supervisión en el momento exacto en que la UPS detecte un corte de energía (estado cambia a `OB` - On Battery).

**Por qué es importante**:
Esto nos permitirá recibir una notificación en el celular avisando que el sistema entró en "modo UPS". De esta manera, estaremos al tanto de que, si no se restablece el servicio eléctrico pronto, el servidor procederá a apagarse automáticamente de forma segura. Nos da una ventana de tiempo valiosa para estar informados o tomar medidas adicionales.

**Pasos previstos para la futura implementación**:
1. Crear un script notificador (ej: `/etc/nut/notify_telegram.sh`) que envíe un mensaje usando las credenciales y el chat ID del bot de Telegram.
2. Modificar el archivo de configuración `/etc/nut/upsmon.conf` y agregar la directiva `NOTIFYCMD /etc/nut/notify_telegram.sh`.
3. Ajustar los `NOTIFYFLAG` en `upsmon.conf` para que eventos clave como `ONBATT` (corte de luz) y `ONLINE` (regreso de la luz) ejecuten el script de notificación.
