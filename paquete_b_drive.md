# Paquete de Despliegue: Paso B.1 (Archivo Automático en Google Drive)

**Instrucciones para el Antigravity de la máquina destino:**
Hola de nuevo. Siguiendo las directivas de arquitectura, vamos a pausar la creación del bot interactivo y enfocarnos 100% en dejar las rutinas del **Supervisor (Antigravity)** perfectamente automatizadas. 

El objetivo de este módulo es que los PDFs de los reportes, una vez extraídos e inyectados en Sheets, no queden ocupando espacio en disco local, sino que se suban dinámicamente a la jerarquía de Google Drive que creaste con Apps Script, directamente a la carpeta del local correspondiente.

Sigue estos pasos.

---

## 1. Instalar la librería oficial de Google API
Ejecuta en la terminal de tu entorno (Ubuntu) la instalación de la librería cliente de Google:
`pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

---

## 2. Crear el Módulo `archivador_drive.py`
Crea este archivo en tu directorio de trabajo. Reutiliza el `credentials.json` que la Service Account ya generó para la Sábana de Sheets. La Service Account debe tener permisos de **Editor** en la carpeta raíz de "Locales" en Google Drive (el usuario ya lo concedió previamente).

```python
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path

# Usamos los mismos scopes que en Sheets, pero enfocados a Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

def obtener_servicio_drive():
    ruta_credenciales = "credentials.json"
    if not os.path.exists(ruta_credenciales):
        raise FileNotFoundError("No se encontró credentials.json. Es necesario para conectar con Drive.")
    
    creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
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

def archivar_reporte_en_drive(pdf_path, sigla_local):
    """
    Toma un archivo local, busca la carpeta del local en Drive (por la sigla),
    y lo sube allí, borrando el archivo local al terminar.
    """
    servicio = obtener_servicio_drive()
    nombre_archivo = Path(pdf_path).name
    
    print(f"[DRIVE] Buscando carpeta para la sigla: {sigla_local}")
    
    # 1. Buscar la carpeta raíz del local (El nombre suele ser "SIGLA - Nombre")
    id_carpeta_local = buscar_carpeta_por_nombre(servicio, sigla_local)
    
    if not id_carpeta_local:
        print(f"[ERROR DRIVE] No se encontró la carpeta raíz para la sigla {sigla_local}.")
        return False
        
    print(f"[DRIVE] Carpeta del local encontrada (ID: {id_carpeta_local}). Buscando subcarpeta 'Reportes'...")
    
    # 2. (Opcional) Buscar subcarpeta "Reportes" dentro del local. 
    # Si la estructura no tiene subcarpeta "Reportes", subimos a la raíz del local.
    id_carpeta_destino = buscar_carpeta_por_nombre(servicio, "Reportes", parent_id=id_carpeta_local)
    
    if not id_carpeta_destino:
        print("[DRIVE] No se encontró subcarpeta 'Reportes', subiendo a la raíz del local.")
        id_carpeta_destino = id_carpeta_local

    # 3. Subir el archivo
    print(f"[DRIVE] Subiendo {nombre_archivo} a Google Drive...")
    file_metadata = {
        'name': nombre_archivo,
        'parents': [id_carpeta_destino]
    }
    media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
    
    archivo_subido = servicio.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id'
    ).execute()
    
    print(f"[✓] Archivo subido exitosamente a Drive con ID: {archivo_subido.get('id')}")
    
    # 4. Limpieza local
    try:
        os.remove(pdf_path)
        print(f"[LIMP] Archivo local eliminado: {pdf_path}")
    except OSError as e:
        print(f"[WARN] No se pudo eliminar el archivo local: {e}")
        
    return True
```

---

## 3. Integrarlo en el Orquestador (`ingestor_automatico.py`)

Para conectar esta pieza, simplemente ve al script que diseñamos en el **Paso A** (`ingestor_automatico.py`), y modifica la función `procesar_carpeta_entrantes()` para que, en lugar de usar `shutil.move()` hacia la carpeta `procesados/`, invoque al nuevo `archivador_drive`.

**Reemplaza las líneas del final del ciclo:**
```python
            # ... código existente (inyectar en sabana) ...
            
            # 3. Mover a procesados
            # shutil.move(str(pdf_path), str(DIR_PROCESADOS / pdf_path.name))
            # print(f"[✓] Archivo movido a procesados.")
```

**Por esto:**
```python
            # 3. Archivar en Google Drive
            import archivador_drive
            sigla = datos_extraidos.get("sigla", "")
            if sigla:
                exito = archivador_drive.archivar_reporte_en_drive(str(pdf_path), sigla)
                if not exito:
                    # Fallback si falla Drive
                    shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))
            else:
                shutil.move(str(pdf_path), str(DIR_ERRORES / pdf_path.name))
```

Con esto, el archivo se escanea, los datos se van a Sheets, el PDF original se sube ordenado a la carpeta Drive de su respectivo local, y luego el PDF se autodestruye del disco local de Ubuntu para mantener el servidor limpio. ¡Aplica los cambios!
