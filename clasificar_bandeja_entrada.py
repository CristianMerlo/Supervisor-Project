import os
import re
import sys
import sqlite3
import subprocess
from pathlib import Path
import PyPDF2

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai

BASE_DIR = Path(__file__).parent
SCOPES = ['https://www.googleapis.com/auth/drive']
MOSTAZA_LOCALES_FOLDER_ID = "1iOGWgu04vtGRv2QBpmxhT5b5NROkJHR8"
BANDEJA_ENTRADA_NAME = "001_Bandeja_de_Entrada"

def cargar_env():
    ruta_env = BASE_DIR / ".env"
    if ruta_env.exists():
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                os.environ[k.strip()] = v.strip()

def obtener_servicio_drive():
    ruta_credenciales = BASE_DIR / "credentials.json"
    if not ruta_credenciales.exists():
        raise FileNotFoundError(f"No se encontró credentials.json en: {ruta_credenciales}")
    creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def obtener_locales_db():
    db_path = Path("/home/cristian/Documentos/Supervisor/supervisor_local.db")
    locales = []
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT sigla, nombre FROM locales")
            for row in cursor.fetchall():
                sigla = row[0].strip().upper()
                nombre = row[1].strip()
                locales.append({'sigla': sigla, 'nombre': nombre})
            conn.close()
        except Exception as e:
            print(f"[DB-ERROR] No se pudo leer SQLite: {e}")
    return locales

def buscar_carpeta_por_nombre(service, name, parent_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name contains '{name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    try:
        res = service.files().list(q=query, fields='files(id, name)').execute()
        files = res.get('files', [])
        if files:
            return files[0]['id']
    except Exception as e:
        print(f"[DRIVE-ERROR] Buscando carpeta '{name}': {e}")
    return None

def obtener_id_bandeja(service):
    # Buscar la bandeja en el directorio raíz
    bandeja_id = buscar_carpeta_por_nombre(service, BANDEJA_ENTRADA_NAME, MOSTAZA_LOCALES_FOLDER_ID)
    if not bandeja_id:
        # Si no existe, crearla
        print(f"[DRIVE] No se encontró la bandeja de entrada. Creándola...")
        file_metadata = {
            'name': BANDEJA_ENTRADA_NAME,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [MOSTAZA_LOCALES_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        bandeja_id = folder.get('id')
    return bandeja_id

def extraer_texto_pdf(pdf_path):
    texto = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                texto += page.extract_text() or ""
    except Exception as e:
        print(f"[PDF-ERROR] Leyendo {pdf_path}: {e}")
    return texto.strip()

def clasificar_con_gemini(texto_pdf, locales_db):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[GEMINI] Advertencia: No hay GEMINI_API_KEY configurada para validación por IA.")
        return None
        
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Armar lista de referencia
        lista_ref = "\n".join([f"- {l['sigla']}: {l['nombre']}" for l in locales_db])
        
        prompt = (
            "Analiza el siguiente texto extraído de un informe de mantenimiento/visita de local de Mostaza.\n"
            "Tu tarea es determinar a qué local corresponde. Devuelve ÚNICAMENTE la sigla correspondiente "
            "(ejemplo: FLIN, FCAB, FBOE) o 'DESCONOCIDO' si no es posible determinarlo con total seguridad.\n"
            "NO devuelvas ninguna otra palabra, comentario, negrita ni formato markdown.\n\n"
            "LISTA DE LOCALES VÁLIDOS:\n"
            f"{lista_ref}\n\n"
            "TEXTO DEL INFORME:\n"
            f"{texto_pdf[:4000]}"
        )
        
        response = model.generate_content(prompt)
        res_text = response.text.strip().upper()
        
        # Limpiar posibles respuestas que contengan markdown u otros textos
        match = re.search(r'\b[A-Z0-9]{3,6}\b', res_text)
        if match:
            sigla_detectada = match.group(0)
            # Validar que esté en la DB
            if any(l['sigla'] == sigla_detectada for l in locales_db):
                return sigla_detectada
    except Exception as e:
        print(f"[GEMINI-ERROR] Error consultando IA: {e}")
    return None

def determinar_sigla_local(filename, texto_pdf, locales_db):
    # Paso 1: Intentar buscar sigla exacta en el nombre del archivo
    for local in locales_db:
        sigla = local['sigla']
        # Buscar sigla como palabra aislada en el nombre del archivo
        if re.search(r'\b' + re.escape(sigla) + r'\b', filename.upper()):
            print(f"[MATCH] Sigla {sigla} encontrada en el nombre del archivo: {filename}")
            return sigla

    # Paso 2: Buscar sigla o nombre en el contenido del PDF (Opción B)
    candidatos = []
    texto_upper = texto_pdf.upper()
    for local in locales_db:
        sigla = local['sigla']
        nombre = local['nombre'].upper()
        
        # Buscar sigla en el texto
        if re.search(r'\b' + re.escape(sigla) + r'\b', texto_upper):
            candidatos.append(sigla)
        # Buscar fragmentos específicos del nombre (ej: "CABILDO")
        elif len(nombre) > 4 and nombre in texto_upper:
            candidatos.append(sigla)
            
    # Eliminar duplicados de candidatos
    candidatos = list(set(candidatos))
    
    if len(candidatos) == 1:
        print(f"[MATCH] Sigla única detectada en texto: {candidatos[0]}")
        return candidatos[0]
        
    # Paso 3: Si no hay candidatos o hay ambigüedad, usar Gemini (Opción C)
    print(f"[INFO] Ambigüedad o sin candidatos directos ({candidatos}). Consultando a Gemini...")
    sigla_ia = clasificar_con_gemini(texto_pdf, locales_db)
    if sigla_ia:
        print(f"[IA-MATCH] Gemini identificó la sucursal: {sigla_ia}")
        return sigla_ia
        
    return None

def enviar_telegram(mensaje):
    try:
        subprocess.run(
            ["/home/cristian/Documentos/Supervisor/notify_telegram.sh", mensaje],
            check=True
        )
    except Exception as e:
        print(f"[TG-ERROR] Falló notificación Telegram: {e}")

def main():
    print("=== INICIANDO CLASIFICACIÓN DE BANDEJA DE ENTRADA EN DRIVE ===")
    cargar_env()
    
    try:
        service = obtener_servicio_drive()
    except Exception as e:
        print(f"[CRITICAL] Error conectando a Drive: {e}")
        return
        
    locales_db = obtener_locales_db()
    bandeja_id = obtener_id_bandeja(service)
    
    # Listar archivos en la bandeja de entrada
    query_files = f"'{bandeja_id}' in parents and trashed = false"
    try:
        res = service.files().list(q=query_files, fields='files(id, name, mimeType)').execute()
        archivos = res.get('files', [])
    except Exception as e:
        print(f"[CRITICAL] Error listando archivos de bandeja: {e}")
        return
        
    if not archivos:
        print("[INFO] La bandeja de entrada está vacía. Terminando proceso.")
        return
        
    print(f"Detectados {len(archivos)} archivos en la bandeja de entrada.")
    
    trasladados = []
    fallidos = []
    
    for idx, f in enumerate(archivos):
        file_id = f['id']
        filename = f['name']
        mime_type = f['mimeType']
        
        print(f"\n[{idx+1}/{len(archivos)}] Procesando: {filename}")
        
        if 'pdf' not in mime_type.lower():
            print(f"[SKIP] El archivo no es un PDF. Saltando clasificación automática.")
            fallidos.append((filename, "No es un archivo PDF"))
            continue
            
        # Descarga temporal
        temp_path = Path(f"/tmp/temp_inbox_{file_id}.pdf")
        try:
            req = service.files().get_media(fileId=file_id)
            with open(temp_path, "wb") as out:
                out.write(req.execute())
        except Exception as e:
            print(f"[ERROR] No se pudo descargar el archivo: {e}")
            fallidos.append((filename, f"Error de descarga: {e}"))
            continue
            
        # Extraer texto del PDF
        texto_pdf = extraer_texto_pdf(temp_path)
        
        # Eliminar archivo temporal local de inmediato
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass
                
        # Clasificar
        sigla_local = determinar_sigla_local(filename, texto_pdf, locales_db)
        
        if not sigla_local:
            print(f"[FAIL] No se pudo clasificar el local para el archivo: {filename}")
            fallidos.append((filename, "Local no identificado"))
            continue
            
        # Buscar la carpeta raíz de ese local
        # Primero mapear la sigla si corresponde (como en el archivador)
        from archivador_drive import obtener_sigla_sistema
        sigla_mapeada = obtener_sigla_sistema(sigla_local)
        
        id_carpeta_local = buscar_carpeta_por_nombre(service, sigla_mapeada, MOSTAZA_LOCALES_FOLDER_ID)
        if not id_carpeta_local:
            print(f"[FAIL] No se encontró la carpeta raíz en Drive para el local: {sigla_mapeada}")
            fallidos.append((filename, f"Carpeta raíz no encontrada para [{sigla_mapeada}]"))
            continue
            
        # Buscar la subcarpeta "Reportes"
        id_carpeta_destino = buscar_carpeta_por_nombre(service, "Reportes", id_carpeta_local)
        if not id_carpeta_destino:
            print(f"[WARN] No se encontró subcarpeta 'Reportes'. Se archivará en la raíz del local.")
            id_carpeta_destino = id_carpeta_local
            
        # Mover archivo en Google Drive (Actualización de metadatos de padres)
        try:
            # Obtener padres actuales para removerlos
            f_metadata = service.files().get(fileId=file_id, fields='parents').execute()
            parents_actuales = ",".join(f_metadata.get('parents', []))
            
            service.files().update(
                fileId=file_id,
                addParents=id_carpeta_destino,
                removeParents=parents_actuales,
                fields='id, parents'
            ).execute()
            
            print(f"[✓] Archivo trasladado exitosamente a la carpeta del local [{sigla_mapeada}].")
            trasladados.append((filename, sigla_mapeada))
        except Exception as e:
            print(f"[ERROR] Error al mover el archivo en Google Drive: {e}")
            fallidos.append((filename, f"Error al mover en Drive: {e}"))
            
    # Notificar por Telegram
    reporte_str = "🪿 *[Goose] Clasificación de Bandeja de Entrada*\n\n"
    enviar_alerta = False
    
    if trasladados:
        enviar_alerta = True
        reporte_str += "✅ *Archivos clasificados y trasladados:*\n"
        for fn, sigla in trasladados:
            reporte_str += f"• `{fn}` ➡️ *[{sigla}]*\n"
        reporte_str += "\n"
        
    if fallidos:
        enviar_alerta = True
        reporte_str += "⚠️ *Archivos pendientes / fallidos (requieren revisión):*\n"
        for fn, razon in fallidos:
            reporte_str += f"• `{fn}`: _{razon}_\n"
            
    if enviar_alerta:
        enviar_telegram(reporte_str)
        print("\n[TELEGRAM] Resumen de clasificación enviado.")
    else:
        print("\n[INFO] Ejecución completada sin cambios requeridos en Telegram.")

if __name__ == "__main__":
    main()
