# Misión: Monitoreo de Actividad de Técnicos vía WhatsApp

Esta función complementa el ingreso formal de reportes (Google Forms) mediante el análisis continuo del grupo de WhatsApp "Fichada ingreso - egreso" y "Equipo Mto. Franquicias".

## Objetivo
Mapear la jornada laboral diaria de cada técnico en tiempo real, registrando:
1. **Fichadas de Entrada (Check-In):** Detección de mensajes como *"Llegando a [LOCAL]"*, *"Entrando a [SIGLA]"*.
2. **Fichadas de Salida (Check-Out):** Detección de mensajes como *"Saliendo de [LOCAL]"*, *"Trabajo terminado en [SIGLA]"*.
3. **Historial de Mensajes:** Registrar interacciones y comentarios operativos en el grupo.

## Estructura de Registro
Los eventos se registrarán en una nueva pestaña llamada `Actividad_Tecnicos` con las columnas:
- `FECHA_HORA` (Timestamp del mensaje)
- `TECNICO` (Nombre detectado)
- `LOCAL` (Sigla del local detectado)
- `EVENTO` (CHECK-IN / CHECK-OUT / COMENTARIO)
- `MENSAJE_ORIGINAL` (Texto completo)

## Frecuencia de Ejecución
Se sugiere que el motor de WhatsApp corra cada **15 o 30 minutos** para evitar saturar el navegador Chrome de la Mini PC, manteniendo un consumo de recursos balanceado.
