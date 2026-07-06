import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from dotenv import load_dotenv
load_dotenv("/home/cristian/Documentos/Supervisor/.env")

CREDENTIALS_FILE = '/home/cristian/Documentos/Supervisor/credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
EVIDENCIAS_FOLDER_NAME = "Evidencias_Telegram"
MOSTAZA_LOCALES_FOLDER_ID = "1iOGWgu04vtGRv2QBpmxhT5b5NROkJHR8" # Carpeta principal de la empresa

def get_drive_service():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def buscar_o_crear_carpeta(service, name, parent_id):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed = false and '{parent_id}' in parents"
    res = service.files().list(q=query, fields='files(id, name)').execute()
    files = res.get('files', [])
    if files:
        return files[0]['id']
    else:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def subir_evidencia(ruta_archivo, nombre_archivo=None, sigla="FMCYM"):
    if not os.path.exists(ruta_archivo):
        return None
        
    webapp_url = os.getenv("DRIVE_WEBAPP_URL")
    if webapp_url:
        try:
            import base64
            import requests
            
            if not nombre_archivo:
                nombre_archivo = os.path.basename(ruta_archivo)
                
            with open(ruta_archivo, "rb") as f:
                file_bytes = f.read()
            base64_data = base64.b64encode(file_bytes).decode("utf-8")
            
            payload = {
                "sigla": sigla if sigla else "FMCYM",
                "fileName": nombre_archivo,
                "fileBase64": base64_data,
                "mode": "reporte"
            }
            
            res = requests.post(webapp_url, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    file_id = data.get("fileId")
                    return f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
                else:
                    print(f"Error WebApp al subir evidencia: {data.get('message')}")
        except Exception as e:
            print(f"Error de conexión WebApp al subir evidencia: {e}")
            
    try:
        service = get_drive_service()
        folder_id = buscar_o_crear_carpeta(service, EVIDENCIAS_FOLDER_NAME, MOSTAZA_LOCALES_FOLDER_ID)
        
        if not nombre_archivo:
            nombre_archivo = os.path.basename(ruta_archivo)
            
        file_metadata = {
            'name': nombre_archivo,
            'parents': [folder_id]
        }
        
        mime = 'image/jpeg'
        if nombre_archivo.lower().endswith('.png'): mime = 'image/png'
        
        media = MediaFileUpload(ruta_archivo, mimetype=mime, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        file_id = file.get('id')
        
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        print(f"Error subiendo evidencia a Drive (Directo): {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        link = subir_evidencia(sys.argv[1])
        print(link)
