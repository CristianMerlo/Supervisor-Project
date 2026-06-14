import csv
import os
from datetime import datetime

# Rutas de archivos
CSV_FILE = "/home/cristian/PROYECTOS/Supervisor-Project/locales.csv"
OUTPUT_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/locales"

def generate_reports():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        created_count = 0
        
        for row in reader:
            # Obtener sigla para el nombre del archivo
            sigla = row.get("SIGLA SISTEMA", "").strip()
            if not sigla or sigla == "-":
                sigla = row.get("SIGLA TICKETS", "").strip()
            
            if not sigla or sigla == "-":
                # Fallback al nombre del local limpio
                sigla = row.get("LOCAL", "UNKNOWN").replace(" ", "_").upper()
            
            # Limpiar caracteres inválidos
            sigla = "".join([c for c in sigla if c.isalnum() or c == "_"])
            
            filepath = os.path.join(OUTPUT_DIR, f"{sigla}.md")
            
            # Si el archivo ya existe (como FMPCH.md), no lo sobrescribimos completo si ya tiene datos
            # Pero para esta etapa inicial, vamos a asegurar que todos existan y tengan la info base actualizada
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            markdown_content = f"""# Estado del Local: {row.get("LOCAL", "N/A")} ({sigla})

## Información General
- **Regional:** {row.get("REGIONAL", "N/A")}
- **Supervisor (Gte Zona):** {row.get("SUPERVISOR (GTE ZONA)", "N/A")}
- **Mail:** {row.get("MAIL", "N/A")}
- **Dirección:** {row.get("DIRECCION", "N/A")}
- **Localidad/Provincia:** {row.get("LOCALIDAD", "N/A")}, {row.get("PROVINCIA", "N/A")}
- **Tipo de Local:** {row.get("TIPO DE LOCAL", "N/A")}
- **Razón Social:** {row.get("RAZON SOCIAL", "N/A")}

## Resumen de Estado Actual
- **Última Actualización:** {current_date}
- **Estado de la Cafetera:** Operativa (Dato por Defecto)
- **Dureza del Agua (PPM):** Pendiente
- **Contador de Shots:** Pendiente
- **Modelo de Cafetera:** Pendiente

## Historial de Intervenciones Recientes
- *No hay intervenciones registradas recientemente.*
"""
            
            # Escribir el archivo solo si no existe o si queremos forzar actualización.
            # Aquí forzamos actualización pero no tocamos FMPCH si ya tenía datos valiosos.
            # Para simplificar, si es FMPCH.md no lo pisamos, el resto sí.
            if sigla == "FMPCH" and os.path.exists(filepath):
                continue
                
            with open(filepath, "w", encoding="utf-8") as out_f:
                out_f.write(markdown_content)
                
            created_count += 1
            
    print(f"✅ Generación completada. Se generaron/actualizaron {created_count} reportes locales en {OUTPUT_DIR}")

if __name__ == "__main__":
    generate_reports()
