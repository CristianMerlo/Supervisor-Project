import os
import sys
from pathlib import Path
import datetime

# Agregar directorio del proyecto para importar módulos locales
base_dir = Path(__file__).parent
sys.path.append(str(base_dir))

import notificador_telegram

def generar_reporte():
    # En producción la carpeta de trabajo del cron suele ser /home/cristian/Documentos/Supervisor
    # Usamos una ruta absoluta para errores para evitar discrepancias
    errores_dir = Path("/home/cristian/Documentos/Supervisor/errores")
    if not errores_dir.exists():
        errores_dir.mkdir(parents=True, exist_ok=True)
        
    pdfs = list(errores_dir.glob("*.pdf"))
    
    if not pdfs:
        mensaje = "📊 **[Antigravity] Reporte Semanal de Pendientes**\n\n✅ ¡Excelente noticias! La carpeta de revisión manual y errores está completamente limpia. No hay reportes pendientes de clasificar."
        notificador_telegram.enviar_alerta(mensaje)
        print("Carpeta limpia. Mensaje enviado.")
        return
        
    mensaje = f"📊 **[Antigravity] Reporte Semanal de Pendientes**\n\n⚠️ Actualmente hay **{len(pdfs)}** archivos en la carpeta de errores que no pudieron ser clasificados o asignados automáticamente.\n\n**Detalle de archivos pendientes:**\n"
    
    for pdf in pdfs:
        mtime = datetime.datetime.fromtimestamp(pdf.stat().st_mtime)
        fecha_str = mtime.strftime("%d/%m/%Y %H:%M")
        size_kb = pdf.stat().st_size / 1024
        mensaje += f"• `{pdf.name}` ({size_kb:.1f} KB) - Modificado: {fecha_str}\n"
        
    mensaje += "\n💡 Recuerda que puedes procesar estos archivos manualmente o clasificarlos para cargarlos en Sheets y Drive."
    
    notificador_telegram.enviar_alerta(mensaje)
    print(f"Reporte enviado con {len(pdfs)} pendientes.")

if __name__ == "__main__":
    generar_reporte()
