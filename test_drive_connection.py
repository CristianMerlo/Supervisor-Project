import sys
from pathlib import Path

# Agregar el directorio actual para asegurar que se pueda importar el módulo
sys.path.append(str(Path(__file__).parent))

import archivador_drive

def test():
    print("=== PROBANDO CONEXIÓN A GOOGLE DRIVE (LISTAR TODO) ===")
    try:
        servicio = archivador_drive.obtener_servicio_drive()
        print("🟢 Servicio de Drive inicializado con éxito.")
        
        # Intentar listar cualquier archivo accesible para verificar permisos
        print("🔍 Buscando TODO TIPO DE ARCHIVO/CARPETA accesible...")
        resultados = servicio.files().list(
            q="trashed = false",
            pageSize=30,
            fields='files(id, name, mimeType)'
        ).execute()
        
        items = resultados.get('files', [])
        if not items:
            print("⚠️ No se encontró absolutamente ningún archivo accesible para esta cuenta de servicio.")
            print("Correo de la cuenta de servicio: supervisor-service-account@supervisor-tecnico.iam.gserviceaccount.com")
            print("Por favor, asegúrate de compartir la carpeta en Google Drive con este correo.")
        else:
            print(f"🟢 Se encontraron {len(items)} ítems:")
            for item in items:
                print(f" - {item['name']} (ID: {item['id']}, Tipo: {item['mimeType']})")
                
    except Exception as e:
        print(f"❌ ERROR DURANTE LA PRUEBA: {e}")

if __name__ == "__main__":
    test()
