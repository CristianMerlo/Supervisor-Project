import re
import os
import gspread
from datetime import datetime
from pathlib import Path
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).parent
import notificador_telegram

MAP_SENDER_NAME = {
    "Anabela Guerrero": "Ana",
    "Tomas Vera": "Tomás",
    "Francisco Rametta": "Francisco",
    "Fernando Soria": "Fernando"
}

def evaluar_bloqueos_criticos(tecnico, local, mensaje):
    """
    Analiza el mensaje en busca de palabras de bloqueo crítico 
    y envía una alerta urgente inmediata al supervisor Cristian.
    """
    palabras_criticas = [
        "roto", "defectuoso", "sin repuesto", "no se puede reparar", 
        "fuera de servicio", "inutilizable", "perdida de fuerza", 
        "perdida agua", "pérdida", "cortocircuito", "quemada"
    ]
    
    mensaje_lower = mensaje.lower()
    detectadas = [p for p in palabras_criticas if p in mensaje_lower]
    
    if detectadas:
        local_str = f" en local *{local}*" if local else ""
        alerta = (
            f"🚨 *[Supervisor] ALERTA DE BLOQUEO CRÍTICO*\n"
            f"• Técnico: {tecnico}\n"
            f"• Local: {local if local else 'No especificado'}\n"
            f"• Mensaje: \"{mensaje}\"\n"
            f"• Detalle detectado: {', '.join(detectadas)}\n"
            f"⚡ *Acción requerida:* Verificar estado o coordinar repuesto de inmediato."
        )
        notificador_telegram.enviar_alerta(alerta)
        print(f"[BLOQUEO-ALERTA] Alerta de bloqueo crítico enviada para {tecnico}{local_str}.")
        return True
    return False

def analizar_claridad_reporte(tecnico, mensaje, evento):
    """
    Evalúa la claridad y profesionalismo de las observaciones enviadas.
    Si el reporte es excesivamente corto o vacío, genera una advertencia.
    """
    # Solo auditar claridad en eventos relevantes (como check-outs o comentarios)
    if evento not in ["CHECK-OUT", "COMENTARIO"]:
        return "N/A"
        
    mensaje_clean = mensaje.strip()
    if len(mensaje_clean) < 10:
        alerta = (
            f"⚠️ *[Supervisor] AVISO DE CALIDAD DE REPORTE*\n"
            f"• Técnico: {tecnico}\n"
            f"• Detalle: Reporte muy corto o poco descriptivo (\"{mensaje_clean}\").\n"
            f"📝 *Sugerencia:* Solicitar al técnico ampliar el diagnóstico."
        )
        notificador_telegram.enviar_alerta(alerta)
        print(f"[CALIDAD-ALERTA] Reporte corto detectado para {tecnico}.")
        return "INSUFICIENTE"
        
    return "ACEPTABLE"

def calcular_duración_visita(tecnico, local, timestamp_out_str):
    """
    Busca el CHECK-IN correspondiente para calcular la duración del servicio en Sheets.
    """
    if not local:
        return "N/A"
        
    try:
        ruta_credenciales = BASE_DIR / "credentials.json"
        if not ruta_credenciales.exists():
            return "N/A"
            
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=scopes)
        cliente = gspread.authorize(creds)
        
        # Obtener URL
        sheet_url = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing"
        ruta_env = BASE_DIR / ".env"
        if ruta_env.exists():
            with open(ruta_env, "r") as f:
                for linea in f:
                    if linea.strip().startswith("SHEETS_SABANA_URL="):
                        sheet_url = linea.strip().split("=", 1)[1].strip()
                        break
                        
        sabana = cliente.open_by_url(sheet_url)
        worksheet = sabana.worksheet("Actividad_Tecnicos")
        registros = worksheet.get_all_records()
        
        # Buscar el CHECK-IN más reciente de hoy para este técnico y local
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        check_in_time = None
        
        # Recorrer en orden inverso para obtener el último
        for r in reversed(registros):
            if r.get("TECNICO") == tecnico and r.get("LOCAL") == local and r.get("EVENTO") == "CHECK-IN":
                ts_reg = r.get("TIMESTAMP_REGISTRO", "")
                if ts_reg.startswith(hoy_str):
                    # Encontrado el CHECK-IN
                    check_in_time = r.get("FECHA_HORA", "")
                    break
                    
        if not check_in_time:
            return "N/A"
            
        # Parsear horas (formato HH:MM o similar)
        # Asumiendo HH:MM
        t_in = datetime.strptime(check_in_time.strip(), "%H:%M")
        t_out = datetime.strptime(timestamp_out_str.strip(), "%H:%M")
        
        diferencia = t_out - t_in
        minutos_totales = int(diferencia.total_seconds() / 60)
        
        if minutos_totales < 0:
            # En caso de cruzar de día
            minutos_totales += 1440
            
        horas = minutos_totales // 60
        minutos = minutos_totales % 60
        
        duracion_str = f"{horas}h {minutos}m"
        print(f"[SLA-CALC] Duración calculada para {tecnico} en {local}: {duracion_str}")
        
        # Si es menor a 15 min o mayor a 6 horas, lanzar alertas
        if minutos_totales < 15:
            alerta = (
                f"⚠️ *[Supervisor] ALERTA DE TIEMPO SLA*\n"
                f"• Técnico: {tecnico}\n"
                f"• Local: {local}\n"
                f"• Detalle: Intervención sospechosamente corta ({duracion_str})."
            )
            notificador_telegram.enviar_alerta(alerta)
        elif minutos_totales > 360: # 6 horas
            alerta = (
                f"⚠️ *[Supervisor] ALERTA DE TIEMPO SLA*\n"
                f"• Técnico: {tecnico}\n"
                f"• Local: {local}\n"
                f"• Detalle: Intervención excedida ({duracion_str})."
            )
            notificador_telegram.enviar_alerta(alerta)
            
        return duracion_str
        
    except Exception as e:
        print(f"[SLA-ERROR] No se pudo calcular duración: {e}")
        return "N/A"
