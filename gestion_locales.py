import os
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent

def actualizar_ficha_local(sigla, nombre_local, tecnico, ticket, ppm, shots, maquina, sn, estado_cafetera, estado_general, repuestos, fecha_reporte=None):
    if not sigla:
        return
        
    sigla = sigla.upper().strip()
    brain_locales_dir = BASE_DIR / "brain" / "locales"
    brain_locales_dir.mkdir(exist_ok=True, parents=True)
    
    file_path = brain_locales_dir / f"{sigla}.md"
    
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_rep = fecha_reporte if fecha_reporte else datetime.now().strftime("%Y-%m-%d")
    
    # Formatear el registro de historial
    log_entry = f"- **[{fecha_rep}] Ticket #{ticket}** por *{tecnico}*: PPM: {ppm} | Shots: {shots} | Estado Cafetera: {estado_cafetera} | Repuestos: {repuestos if repuestos else 'Ninguno'}\n"
    
    historial_lineas = []
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            in_history = False
            for line in lines:
                if "## Historial de Intervenciones Recientes" in line:
                    in_history = True
                    continue
                if in_history:
                    # Evitar duplicados del mismo ticket en el historial local
                    if ticket and f"Ticket #{ticket}" in line:
                        print(f"[LOCAL-FICHA] El ticket {ticket} ya existe en el historial de {sigla}. Omitiendo duplicado.")
                        return
                    if line.strip():
                        historial_lineas.append(line)
        except Exception as e_read:
            print(f"[LOCAL-FICHA] Advertencia leyendo ficha existente de {sigla}: {e_read}")
            
    # Escribir la ficha consolidada con el último estado
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Estado del Local: {nombre_local} ({sigla})\n\n")
            f.write(f"## Resumen de Estado Actual\n")
            f.write(f"- **Última Actualización:** {fecha_actual}\n")
            f.write(f"- **Estado de la Cafetera:** {estado_cafetera}\n")
            f.write(f"- **Dureza del Agua (PPM):** {ppm} ({estado_general})\n")
            f.write(f"- **Contador de Shots:** {shots}\n")
            f.write(f"- **Modelo de Cafetera:** {maquina} {f'(SN: {sn})' if sn else ''}\n\n")
            f.write(f"## Historial de Intervenciones Recientes\n")
            
            # Escribir la nueva intervención al tope
            f.write(log_entry)
            
            # Escribir el resto del historial previo
            for h_line in historial_lineas:
                f.write(h_line)
                
        print(f"[LOCAL-FICHA] Ficha del local {sigla} actualizada exitosamente en: brain/locales/{sigla}.md")
    except Exception as e_write:
        print(f"[LOCAL-FICHA-ERROR] Falló escritura de ficha para {sigla}: {e_write}")
