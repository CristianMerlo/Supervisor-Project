import os
import json
import time
import shutil
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright
import notificador_telegram

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

    # Obtener el último ID/texto procesado de este grupo
    ultimo_procesado = estado_actual.get(grupo, "")
    
    # Extraer mensajes entrantes (message-in)
    mensajes_in = page.locator("div.message-in")
    cantidad = mensajes_in.count()
    
    print(f"   📥 Mensajes entrantes detectados en pantalla: {cantidad}")
    
    # Evaluamos hasta los últimos 50 mensajes para no perder información si hay mucho texto
    limite = min(50, cantidad)
    
    # Primero, escaneamos de adelante hacia atrás para identificar cuáles son realmente nuevos
    mensajes_a_procesar = []
    
    for i in range(cantidad - limite, cantidad):
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
            meta = msg.inner_text().split("\n")[-1] 
        except:
            meta = "Hora desconocida"
            
        identificador_msg = f"{texto[:50]}_{meta}"
        mensajes_a_procesar.append((i, identificador_msg, texto))

    # Filtrar solo los mensajes que ocurrieron DESPUÉS del ultimo_procesado
    nuevos_mensajes = []
    encontrado_ultimo = False
    
    if ultimo_procesado:
        # Buscamos de atrás hacia adelante el último procesado para saber desde dónde partir
        for idx, (original_idx, ident, texto) in enumerate(reversed(mensajes_a_procesar)):
            if ident == ultimo_procesado:
                # El último procesado está en la lista.
                # Los nuevos son todos los que están después de este índice
                start_from = len(mensajes_a_procesar) - idx
                nuevos_mensajes = mensajes_a_procesar[start_from:]
                encontrado_ultimo = True
                break
                
    if not encontrado_ultimo:
        # Si no había historial o el último mensaje ya se salió de la pantalla (más de 50 mensajes nuevos),
        # procesamos solo los últimos 10 de forma segura para no duplicar demasiado o perder el hilo.
        nuevos_mensajes = mensajes_a_procesar[-10:]

    # Registrar el momento exacto antes de descargar
    tiempo_inicio_descargas = time.time()
    nuevo_ultimo_procesado = ultimo_procesado
    
    if nuevos_mensajes:
        print(f"   🆕 Se detectaron {len(nuevos_mensajes)} mensajes nuevos desde la última revisión.")
        for original_idx, ident, texto in nuevos_mensajes:
            msg = mensajes_in.nth(original_idx)
            
            # Descarga de archivos adjuntos
            btn_descarga = msg.locator("span[data-icon='download']")
            if btn_descarga.count() > 0:
                print(f"   [Descarga] Archivo detectado en mensaje: '{texto[:20]}...'")
                btn_descarga.first.click()
                page.wait_for_timeout(3000) # Esperar a que descargue
                
            nuevo_ultimo_procesado = ident
            
        estado_actual[grupo] = nuevo_ultimo_procesado
        print(f"   ✅ Se procesaron {len(nuevos_mensajes)} mensajes nuevos en '{grupo}'")
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
                msg_err = "❌ ERROR CRÍTICO [WhatsApp Bot]: La sesión de WhatsApp no está iniciada (Pide código QR). Escanea el código en la pantalla del servidor."
                print(msg_err)
                notificador_telegram.enviar_alerta(msg_err)
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
            msg_err = f"❌ ERROR [WhatsApp Bot]: Error al conectar con Chrome (¿Está abierto en puerto 9222?): {e}"
            print(msg_err)
            notificador_telegram.enviar_alerta(msg_err)

if __name__ == "__main__":
    ejecutar_motor()
