import os
import json
import time
import shutil
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright
import notificador_telegram
import re
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(PROJECT_ROOT, "whatsapp_last_read.json")
ENTRANTES_DIR = os.path.join(PROJECT_ROOT, "entrantes")

# Mapeo de nombres de técnicos de WhatsApp a estándar
MAP_TECNICOS = {
    "ana guerrero": "Anabela Guerrero",
    "anabela guerrero": "Anabela Guerrero",
    "tomas vera": "Tomas Vera",
    "tomás vera": "Tomas Vera",
    "francisco rametta": "Francisco Rametta",
    "francisco mto rosario mostaza": "Francisco Rametta",
    "fernando soria": "Fernando Soria",
    "fernando soria mantenimiento": "Fernando Soria",
    "fer soria": "Fernando Soria"
}

def analizar_mensaje_actividad(texto):
    texto_lower = texto.lower()
    
    # Siglas de locales (F seguida de 3 letras o números, o FMCB, etc)
    siglas = re.findall(r'\b(F[A-Z0-9]{3,4})\b', texto.upper())
    sigla = siglas[0] if siglas else ""
    
    evento = "COMENTARIO"
    if any(kw in texto_lower for kw in ["llegando", "ingreso", "entrando", "entrado", "llegue", "llegué", "adentro", "en local"]):
        evento = "CHECK-IN"
    elif any(kw in texto_lower for kw in ["saliendo", "egreso", "sali", "salí", "retirando", "retiro", "terminado", "fin", "completo", "me voy"]):
        evento = "CHECK-OUT"
        
    return evento, sigla

def registrar_actividad_sheet(timestamp_msg, tecnico, local, evento, mensaje):
    try:
        ruta_credenciales = Path(PROJECT_ROOT) / "credentials.json"
        if not ruta_credenciales.exists():
            return
            
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=scopes)
        cliente = gspread.authorize(creds)
        
        # Obtener URL de Sábana de .env
        sheet_url = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing"
        ruta_env = Path(PROJECT_ROOT) / ".env"
        if ruta_env.exists():
            with open(ruta_env, "r") as f:
                for linea in f:
                    if linea.strip().startswith("SHEETS_SABANA_URL="):
                        sheet_url = linea.strip().split("=", 1)[1].strip()
                        break
                        
        sabana = cliente.open_by_url(sheet_url)
        try:
            worksheet = sabana.worksheet("Actividad_Tecnicos")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sabana.add_worksheet(title="Actividad_Tecnicos", rows="1000", cols="6")
            worksheet.append_row(["FECHA_HORA", "TECNICO", "LOCAL", "EVENTO", "MENSAJE_ORIGINAL", "TIMESTAMP_REGISTRO"])
            
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([timestamp_msg, tecnico, local, evento, mensaje, fecha_actual])
        print(f"[SHEETS-ACT] Registrada actividad de {tecnico} en local {local}.")
    except Exception as e:
        print(f"[SHEETS-ACT-ERROR] Falló registro en Sheets: {e}")

def registrar_actividad_local_md(tecnico, local, evento, mensaje, timestamp):
    name_map = {
        "Anabela Guerrero": "anabela_guerrero.md",
        "Tomas Vera": "tomas_vera.md",
        "Francisco Rametta": "francisco_rametta.md",
        "Fernando Soria": "fernando_soria.md"
    }
    file_name = name_map.get(tecnico)
    if not file_name:
        return
        
    file_path = Path(PROJECT_ROOT) / "brain" / "tecnicos" / file_name
    if not file_path.exists():
        return
        
    try:
        log_entry = f"- **[{timestamp}]** {evento} en local **{local if local else 'Desconocido'}**: \"{mensaje}\"\n"
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        idx_history = -1
        for idx, line in enumerate(lines):
            if "Historial de Actividad" in line:
                idx_history = idx
                break
                
        if idx_history != -1:
            lines.insert(idx_history + 2, log_entry)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"[MD-ACT] Registrada actividad en ficha local de {tecnico}.")
    except Exception as e:
        print(f"[MD-ACT-ERROR] Falló escritura en ficha de técnico: {e}")


# Asegurar carpeta del ingestor
os.makedirs(ENTRANTES_DIR, exist_ok=True)

# Grupos a monitorear (exactamente como están en WhatsApp)
GRUPOS = [
    # "Fichada ingreso - egreso",  # Suspendido temporalmente a pedido de Cristian
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
    
    grupo_encontrado = False
    intentos = 3
    
    for intento in range(1, intentos + 1):
        try:
            # En la lista lateral (sin buscar), ¿está ya visible?
            chat_locator = page.locator(f"#pane-side span[title='{grupo}']")
            if chat_locator.count() > 0:
                chat_locator.first.click()
                page.wait_for_timeout(2500) # Esperar a que cargue el chat
                grupo_encontrado = True
                break
                
            print(f"   [!] Intento {intento}/{intentos}: El grupo '{grupo}' no está visible. Usando buscador...")
            
            # Buscar el input de búsqueda
            search_box_locator = page.locator("input[data-tab='3'], div[contenteditable='true'][data-tab='3']")
            if search_box_locator.count() > 0:
                search_box = search_box_locator.first
                search_box.click()
                page.wait_for_timeout(500)
                search_box.fill("")
                page.wait_for_timeout(500)
                search_box.press_sequentially(grupo, delay=120)
                page.wait_for_timeout(4000) # Más tiempo para que react renderice resultados
                
                # Clic en el primer resultado que coincida
                result_locator = page.locator(f"span[title='{grupo}']")
                if result_locator.count() > 0:
                    result_locator.first.click()
                    page.wait_for_timeout(2500)
                    print(f"   [+] Grupo '{grupo}' seleccionado con éxito.")
                    grupo_encontrado = True
                    
                    # Limpiar buscador
                    search_box_locator.first.click()
                    search_box_locator.first.fill("")
                    page.wait_for_timeout(1000)
                    break
            
            # Si falló y no es el último intento, recargamos la página
            if intento < intentos:
                print(f"   [⚠️] No se pudo encontrar el grupo '{grupo}' en el intento {intento}. Forzando reload de WhatsApp Web...")
                page.reload()
                page.wait_for_timeout(12000) # Esperar a que cargue la interfaz completa
                
        except Exception as e_intento:
            print(f"   [❌] Error en intento {intento} para grupo {grupo}: {e_intento}")
            if intento < intentos:
                page.reload()
                page.wait_for_timeout(12000)

    if not grupo_encontrado:
        msg_alerta = f"⚠️ *[Antigravity]* Alerta de WhatsApp: No se pudo localizar ni abrir el grupo *'{grupo}'* tras {intentos} intentos. Los informes de este canal no están siendo capturados automáticamente."
        print(f"[ALERTA CRÍTICA] {msg_alerta}")
        
        # Guardar en estado que falló para el reporte de restauración posterior
        estado_actual[f"FALLO_{grupo}"] = True
        
        # Enviar alerta por Telegram
        try:
            notificador_telegram.enviar_alerta(msg_alerta)
        except Exception as e_tg:
            print(f"   [!] Error enviando alerta TG: {e_tg}")
            
        # Enviar alerta por Mail
        try:
            import notificador_mail
            asunto = f"⚠️ [Hermes] Alerta: Grupo de WhatsApp no localizado: {grupo}"
            notificador_mail.enviar_correo(asunto, msg_alerta.replace("*", ""))
        except Exception as e_mail:
            print(f"   [!] Error enviando alerta Mail: {e_mail}")
            
        return estado_actual

    # Si se encontró con éxito, ver si venía de un fallo previo para notificar la restauración
    if estado_actual.get(f"FALLO_{grupo}"):
        msg_recuperado = f"✅ *[Antigravity]* Servicio Restablecido: El grupo *'{grupo}'* de WhatsApp Web fue localizado con éxito y vuelve a estar operativo."
        print(f"[RECONEXIÓN EXITOSA] {msg_recuperado}")
        try:
            notificador_telegram.enviar_alerta(msg_recuperado)
        except Exception as e_tg:
            print(f"   [!] Error enviando alerta de recuperación TG: {e_tg}")
        # Remover flag de fallo
        estado_actual.pop(f"FALLO_{grupo}", None)

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
            
            # --- NUEVA LÓGICA: Monitoreo de actividad de técnicos ---
            try:
                raw_text = msg.inner_text()
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                if len(lines) >= 3:
                    sender = lines[0]
                    msg_text = "\n".join(lines[1:-1])
                    msg_time = lines[-1]
                else:
                    sender = "Desconocido"
                    msg_text = texto
                    msg_time = datetime.now().strftime("%H:%M")
                    
                sender_key = sender.lower().strip()
                tecnico_std = MAP_TECNICOS.get(sender_key)
                
                # Si el emisor es un técnico mapeado
                if tecnico_std:
                    evento, local_detectado = analizar_mensaje_actividad(msg_text)
                    # Registrar en Google Sheets y en ficha local
                    registrar_actividad_sheet(msg_time, tecnico_std, local_detectado, evento, msg_text)
                    registrar_actividad_local_md(tecnico_std, local_detectado, evento, msg_text, msg_time)
                    
                    # --- NUEVA LÓGICA: Auditoría activa del Supervisor ---
                    try:
                        import gestion_supervisor
                        # 1. Bloqueos críticos
                        gestion_supervisor.evaluar_bloqueos_criticos(tecnico_std, local_detectado, msg_text)
                        # 2. Claridad
                        gestion_supervisor.analizar_claridad_reporte(tecnico_std, msg_text, evento)
                        # 3. Duración / SLA
                        if evento == "CHECK-OUT":
                            duracion = gestion_supervisor.calcular_duración_visita(tecnico_std, local_detectado, msg_time)
                            if duracion != "N/A":
                                registrar_actividad_local_md(tecnico_std, local_detectado, f"DURACIÓN: {duracion}", "Cálculo de SLA por Supervisor", msg_time)
                    except Exception as e_super:
                        print(f"   [!] Error en auditoría de supervisor: {e_super}")
            except Exception as e_act:
                print(f"   [!] Error de parseo de actividad: {e_act}")
            # --------------------------------------------------------
            
            # Descarga de archivos adjuntos
            btn_descarga = msg.locator("span[data-icon='download']")
            btn_doc = msg.locator("div[data-testid='document-thumb']")
            
            if btn_descarga.count() > 0:
                print(f"   [Descarga] Archivo detectado en mensaje: '{texto[:20]}...'")
                btn_descarga.first.click()
                page.wait_for_timeout(3000) # Esperar a que descargue
            elif btn_doc.count() > 0:
                print(f"   [Descarga] Documento PDF detectado. Abriendo visor de medios...")
                btn_doc.first.click()
                page.wait_for_timeout(3000) # Esperar a que abra el visor
                
                # Descargar desde el visor
                btn_down_viewer = page.locator("span[data-testid='ic-download']")
                if btn_down_viewer.count() > 0:
                    print("   [Descarga] Clic en botón de descarga del visor...")
                    btn_down_viewer.first.click()
                    page.wait_for_timeout(5000) # Esperar descarga
                else:
                    print("   [!] Botón de descarga no encontrado en el visor.")
                
                # Cerrar visor
                btn_close_viewer = page.locator("span[data-testid='ic-close']")
                if btn_close_viewer.count() > 0:
                    btn_close_viewer.first.click()
                    page.wait_for_timeout(1000)
                
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
            
            # Configurar comportamiento de descarga para guardar en ~/Descargas
            try:
                cdp_session = whatsapp_page.context.new_cdp_session(whatsapp_page)
                descargas_dir = os.path.expanduser("~/Descargas")
                cdp_session.send("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": descargas_dir
                })
                print("   [+] Comportamiento de descarga CDP configurado exitosamente.")
            except Exception as e_cdp:
                print(f"   [!] Advertencia al configurar descargas vía CDP: {e_cdp}")
            
            # Resiliencia: si el visor de medios quedó abierto por error, cerrarlo
            close_btn = whatsapp_page.locator("span[data-testid='ic-close']")
            if close_btn.count() > 0:
                print("   [+] Visor de medios previo detectado abierto. Cerrando...")
                close_btn.first.click()
                whatsapp_page.wait_for_timeout(1000)
                
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
            try:
                import notificador_mail
                asunto = "⚠️ [Hermes] Alerta: Falla de Conexión en WhatsApp Web"
                notificador_mail.enviar_correo(asunto, msg_err)
            except Exception as e_mail:
                print(f"   [!] Error enviando email de contingencia: {e_mail}")

if __name__ == "__main__":
    ejecutar_motor()
