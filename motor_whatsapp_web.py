import os
import json
import time
import shutil
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(PROJECT_ROOT, "whatsapp_last_read.json")
ENTRANTES_DIR = os.path.join(PROJECT_ROOT, "entrantes")

# Asegurar carpeta del ingestor
os.makedirs(ENTRANTES_DIR, exist_ok=True)

# Grupos a monitorear (exactamente como están en WhatsApp)
GRUPOS = [
    "Fichada ingreso - egreso",
    "Equipo Mto. Franquicias",
    "Informes técnicos Diarios"
]

def cargar_estado():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_estado(estado):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4)

def obtener_archivos_recientes_descargas(tiempo_inicio):
    """Busca archivos en la carpeta Downloads de Ubuntu descargados DESPUÉS de tiempo_inicio"""
    descargas_dir = os.path.expanduser("~/Downloads")
    if not os.path.exists(descargas_dir):
        # Fallback para español u otras configs
        descargas_dir = os.path.expanduser("~/Descargas")
        if not os.path.exists(descargas_dir):
            return []

    archivos_nuevos = []
    # Buscar todos los archivos en Descargas
    for archivo in glob.glob(os.path.join(descargas_dir, "*")):
        # Evitar archivos temporales de descarga de Chrome (.crdownload)
        if archivo.endswith(".crdownload") or archivo.endswith(".tmp"):
            continue
            
        mtime = os.path.getmtime(archivo)
        if mtime > tiempo_inicio:
            archivos_nuevos.append(archivo)
            
    return archivos_nuevos

def mover_al_ingestor(rutas_archivos):
    movidos = 0
    for ruta in rutas_archivos:
        nombre = os.path.basename(ruta)
        destino = os.path.join(ENTRANTES_DIR, nombre)
        try:
            shutil.move(ruta, destino)
            print(f"   [+] Archivo movido al ingestor: {nombre}")
            movidos += 1
        except Exception as e:
            print(f"   [!] Error moviendo archivo {nombre}: {e}")
    return movidos

def procesar_mensajes_grupo(page, grupo, estado_actual):
    print(f"\n🔍 Revisando grupo: {grupo}")
    
    # Intentar hacer click en el grupo en el panel izquierdo
    try:
        # En la lista lateral (sin buscar), ¿está ya visible?
        # Aseguramos que es de la lista lateral excluyendo el encabezado del chat activo
        chat_locator = page.locator(f"#pane-side span[title='{grupo}']")
        if chat_locator.count() > 0:
            chat_locator.first.click()
            page.wait_for_timeout(2000) # Esperar a que cargue el chat
        else:
            print(f"   [!] El grupo '{grupo}' no está visible en la lista lateral. Usando buscador...")
            
            # Buscar el input de búsqueda
            search_box_locator = page.locator("input[data-tab='3'], div[contenteditable='true'][data-tab='3']")
            if search_box_locator.count() == 0:
                print("   [❌] No se pudo encontrar el buscador de chats.")
                return estado_actual
                
            search_box = search_box_locator.first
            search_box.click()
            page.wait_for_timeout(500)
            
            # Limpiar buscador
            search_box.fill("")
            page.wait_for_timeout(500)
            
            # Escribir el grupo secuencialmente para disparar React
            search_box.press_sequentially(grupo, delay=100)
            page.wait_for_timeout(3000) # Esperar que carguen los resultados
            
            # Clic en el primer resultado que coincida
            result_locator = page.locator(f"span[title='{grupo}']")
            if result_locator.count() > 0:
                result_locator.first.click()
                page.wait_for_timeout(2000)
                print(f"   [+] Grupo '{grupo}' seleccionado con éxito.")
            else:
                print(f"   [⚠️] El grupo '{grupo}' no se encontró en los resultados de búsqueda.")
                # Limpiar buscador y salir
                search_box.click()
                search_box.fill("")
                page.wait_for_timeout(1000)
                return estado_actual
                
            # Limpiar buscador para restaurar la lista normal
            search_box_locator.first.click()
            search_box_locator.first.fill("")
            page.wait_for_timeout(1000)
            
    except Exception as e:
        print(f"   [❌] Error navegando al grupo {grupo}: {e}")
        return estado_actual

    # Estamos dentro del chat.
    # Obtener el último ID/texto procesado de este grupo
    ultimo_procesado = estado_actual.get(grupo, "")
    nuevo_ultimo_procesado = ultimo_procesado
    
    # Extraer mensajes entrantes (message-in)
    mensajes_in = page.locator("div.message-in")
    cantidad = mensajes_in.count()
    
    print(f"   📥 Mensajes entrantes detectados en pantalla: {cantidad}")
    
    mensajes_nuevos_encontrados = []
    
    # Registrar el momento exacto antes de descargar para poder detectar qué archivo cayó
    tiempo_inicio_descargas = time.time()
    
    # Recorremos desde el final (los más recientes) hacia atrás
    # Para simplificar, leemos los últimos 10
    rango = min(10, cantidad)
    
    for i in range(cantidad - rango, cantidad):
        msg = mensajes_in.nth(i)
        
        # Extraer texto del mensaje
        try:
            text_locator = msg.locator("span.selectable-text")
            if text_locator.count() > 0:
                texto = text_locator.first.inner_text()
            else:
                texto = "[Multimedia o Archivo sin texto]"
        except:
            texto = "[Error leyendo texto]"
            
        # Extraer hora (metadata)
        try:
            # WhatsApp guarda la hora en un atributo
            meta = msg.inner_text().split("\n")[-1] 
        except:
            meta = "Hora desconocida"
            
        # Crear un "hash" simple del mensaje para identificarlo
        identificador_msg = f"{texto[:50]}_{meta}"
        
        # Si encontramos el mensaje que leímos la última vez, sabemos que de ahí en adelante son nuevos.
        # Pero como leemos en orden cronológico, los evaluamos y si no es igual al último, lo agregamos.
        # Una forma más simple es mantener una lista circular o si superamos el último, procesamos.
        mensajes_nuevos_encontrados.append(identificador_msg)
        
        # Descarga de archivos adjuntos
        # Si hay un botón de descarga (ícono de flecha hacia abajo)
        btn_descarga = msg.locator("span[data-icon='download']")
        if btn_descarga.count() > 0:
            print(f"   [Descarga] Archivo detectado en mensaje: '{texto[:20]}...'")
            btn_descarga.first.click()
            page.wait_for_timeout(3000) # Esperar a que descargue
            
        nuevo_ultimo_procesado = identificador_msg

    # Evaluar qué mensajes son realmente nuevos comparando con el estado
    # (Lógica simplificada: si el id cambió, hay nuevos)
    if nuevo_ultimo_procesado != ultimo_procesado:
        print(f"   ✅ Se encontraron mensajes nuevos en '{grupo}'")
        # Aquí podrías inyectar Gemini para resumir los textos extraídos.
        estado_actual[grupo] = nuevo_ultimo_procesado
    else:
        print(f"   💤 No hay mensajes nuevos en '{grupo}'")
        
    # Verificar si cayeron archivos en Descargas
    archivos_bajados = obtener_archivos_recientes_descargas(tiempo_inicio_descargas)
    if archivos_bajados:
        print(f"   📦 Se descargaron {len(archivos_bajados)} archivos. Moviendo al Ingestor...")
        mover_al_ingestor(archivos_bajados)

    return estado_actual


def ejecutar_motor():
    print("🚀 Iniciando Motor WhatsApp Web (Browser Attaching)...")
    
    # Conectarse al CDP (Puerto 9222)
    with sync_playwright() as p:
        try:
            print("🔗 Conectando al Chrome existente en localhost:9222...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            # Buscar la pestaña de WhatsApp entre las que ya están abiertas
            whatsapp_page = None
            for context in browser.contexts:
                for page in context.pages:
                    if "whatsapp" in page.url.lower():
                        whatsapp_page = page
                        break
                        
            if not whatsapp_page:
                print("⚠️ No se encontró una pestaña abierta con WhatsApp Web.")
                print("   Abriendo una nueva pestaña hacia web.whatsapp.com...")
                whatsapp_page = browser.contexts[0].new_page()
                whatsapp_page.goto("https://web.whatsapp.com/")
                
            whatsapp_page.bring_to_front()
            
            # Verificar si cargó correctamente o hay error
            whatsapp_page.wait_for_timeout(5000)
            
            # Si vemos el QR, la sesión no está iniciada
            if whatsapp_page.locator("canvas").count() > 0 and "QR" in whatsapp_page.locator("body").inner_text():
                print("❌ ERROR CRÍTICO: La sesión de WhatsApp no está iniciada (Pide QR).")
                print("   Por favor, escanea el código en el servidor y vuelve a correr el motor.")
                return

            # Resiliencia: Cartel de desconexión
            if "Computadora sin conexión" in whatsapp_page.locator("body").inner_text():
                print("⚠️ Detectado cartel de 'Sin conexión'. Recargando página...")
                whatsapp_page.reload()
                whatsapp_page.wait_for_timeout(10000)

            print("✅ WhatsApp Web detectado y activo.")
            
            estado_actual = cargar_estado()
            
            for grupo in GRUPOS:
                estado_actual = procesar_mensajes_grupo(whatsapp_page, grupo, estado_actual)
                
            guardar_estado(estado_actual)
            print("\n✅ Ciclo del Motor WhatsApp terminado.")

        except Exception as e:
            print(f"❌ Error al conectar con Chrome (¿Está abierto con --remote-debugging-port=9222?): {e}")

if __name__ == "__main__":
    ejecutar_motor()
