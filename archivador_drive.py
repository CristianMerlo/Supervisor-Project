import os
import base64
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path

# Usamos los mismos scopes que en Sheets, pero enfocados a Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

def obtener_servicio_drive():
    # Obtener la ruta absoluta del archivo credentials.json respecto al script
    base_dir = Path(__file__).parent
    ruta_credenciales = base_dir / "credentials.json"
    
    if not ruta_credenciales.exists():
        raise FileNotFoundError(f"No se encontró credentials.json en: {ruta_credenciales}. Es necesario para conectar con Drive.")
    
    creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def buscar_carpeta_por_nombre(servicio, nombre_carpeta, parent_id=None):
    """Busca una carpeta en Drive por su nombre exacto o parte de él."""
    query = f"mimeType='application/vnd.google-apps.folder' and name contains '{nombre_carpeta}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    resultados = servicio.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    archivos = resultados.get('files', [])
    
    if not archivos:
        return None
    return archivos[0].get('id')

def obtener_sigla_sistema(sigla_ticket):
    """Mapea una SIGLA TICKETS a su correspondiente SIGLA SISTEMA usando locales.csv."""
    try:
        import csv
        ruta_csv = Path(__file__).parent / "locales.csv"
        if not ruta_csv.exists():
            return sigla_ticket
            
        with open(ruta_csv, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # Omitir cabecera
            for row in reader:
                if len(row) > 1:
                    sigla_sis = row[0].strip()
                    sigla_tic = row[1].strip()
                    if sigla_tic.upper() == sigla_ticket.upper():
                        if sigla_sis and sigla_sis != "-":
                            return sigla_sis
    except Exception as e:
        print(f"[WARN] Error mapeando sigla: {e}")
    return sigla_ticket

def archivar_reporte_en_drive(pdf_path, sigla_local):
    """
    Toma un archivo local, busca la carpeta del local en Drive (por la sigla),
    y lo sube allí, borrando el archivo local al terminar.
    Soporta subida por Web App (cuotas seguras) o cuenta de servicio directamente (fallback).
    """
    # Mapear la sigla de ticket (ej: FLINR) a la sigla de sistema (ej: FLIN) para encontrar la carpeta en Drive
    sigla_mapeada = obtener_sigla_sistema(sigla_local)
    if sigla_mapeada != sigla_local:
        print(f"[DRIVE-MAP] Mapeando sigla de ticket '{sigla_local}' a sigla de sistema '{sigla_mapeada}' para Google Drive")
        sigla_local = sigla_mapeada

    webapp_url = os.getenv("DRIVE_WEBAPP_URL")
    
    if webapp_url:
        print(f"[DRIVE-WEBAPP] Iniciando subida para la sigla {sigla_local} vía Web App...")
        try:
            nombre_archivo = Path(pdf_path).name
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            base64_data = base64.b64encode(pdf_bytes).decode("utf-8")
            
            payload = {
                "sigla": sigla_local,
                "fileName": nombre_archivo,
                "fileBase64": base64_data
            }
            
            response = requests.post(webapp_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("status") == "success":
                    print(f"[✓] Archivo subido exitosamente a Drive vía Web App. ID: {res_data.get('fileId')}")
                    # Guardar archivo local en lugar de eliminarlo
                    import shutil
                    dir_destino = Path("/home/cristian/PROYECTOS/Supervisor-Project/brain/locales/PDFs_Originales")
                    dir_destino.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(pdf_path, str(dir_destino / nombre_archivo))
                        print(f"[REPALDO] Archivo local movido a: {dir_destino}")
                    except OSError as e:
                        print(f"[WARN] No se pudo mover el archivo local: {e}")
                    return True
                else:
                    print(f"[ERROR DRIVE-WEBAPP] Error retornado por la Web App: {res_data.get('message')}")
                    return False
            else:
                print(f"[ERROR DRIVE-WEBAPP] Error HTTP {response.status_code} al llamar a la Web App.")
                return False
        except Exception as e:
            print(f"[ERROR DRIVE-WEBAPP] Falló la subida vía Web App: {e}")
            return False

    # --- FALLBACK: Método de Cuenta de Servicio ---
    try:
        servicio = obtener_servicio_drive()
    except Exception as e:
        print(f"[ERROR DRIVE] No se pudo inicializar el servicio de Drive: {e}")
        return False
        
    nombre_archivo = Path(pdf_path).name
    
    print(f"[DRIVE] Buscando carpeta para la sigla: {sigla_local}")
    
    # 1. Buscar la carpeta raíz del local (El nombre suele ser "SIGLA - Nombre")
    try:
        id_carpeta_local = buscar_carpeta_por_nombre(servicio, sigla_local)
    except Exception as e:
        print(f"[ERROR DRIVE] Falla en la búsqueda de carpeta para la sigla {sigla_local}: {e}")
        return False
    
    if not id_carpeta_local:
        print(f"[ERROR DRIVE] No se encontró la carpeta raíz para la sigla {sigla_local}.")
        return False
        
    print(f"[DRIVE] Carpeta del local encontrada (ID: {id_carpeta_local}). Buscando subcarpeta 'Reportes'...")
    
    # 2. Buscar subcarpeta "Reportes" dentro de la carpeta del local.
    try:
        id_carpeta_destino = buscar_carpeta_por_nombre(servicio, "Reportes", parent_id=id_carpeta_local)
    except Exception as e:
        print(f"[WARN DRIVE] Falla al buscar la subcarpeta 'Reportes': {e}. Se subirá a la carpeta raíz del local.")
        id_carpeta_destino = None
    
    if not id_carpeta_destino:
        print("[DRIVE] No se encontró subcarpeta 'Reportes', subiendo a la raíz del local.")
        id_carpeta_destino = id_carpeta_local

    # 3. Subir el archivo
    print(f"[DRIVE] Subiendo {nombre_archivo} a Google Drive...")
    file_metadata = {
        'name': nombre_archivo,
        'parents': [id_carpeta_destino]
    }
    
    try:
        media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
        archivo_subido = servicio.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        print(f"[✓] Archivo subido exitosamente a Drive con ID: {archivo_subido.get('id')}")
    except Exception as e:
        print(f"[ERROR DRIVE] Falla al subir el archivo {nombre_archivo} a Drive: {e}")
        return False
    
    # 4. Guardar archivo local en lugar de eliminarlo
    import shutil
    dir_destino = Path("/home/cristian/PROYECTOS/Supervisor-Project/brain/locales/PDFs_Originales")
    dir_destino.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(pdf_path, str(dir_destino / nombre_archivo))
        print(f"[RESPALDO] Archivo local movido a: {dir_destino}")
    except OSError as e:
        print(f"[WARN] No se pudo mover el archivo local: {e}")
        
    return True
