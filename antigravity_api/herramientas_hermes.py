import os
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno del directorio padre (.env principal)
base_dir = Path(__file__).parent
parent_env = base_dir.parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env)
else:
    load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing"
SHEET_URL = os.getenv("SHEETS_SABANA_URL", DEFAULT_SHEET_URL)

def _obtener_sabana():
    # Ruta absoluta para credentials.json para garantizar que funcione bajo systemd
    ruta_credenciales = base_dir.parent / "credentials.json"
    if not ruta_credenciales.exists():
        ruta_credenciales = base_dir / "credentials.json"
    
    if not ruta_credenciales.exists():
        raise FileNotFoundError(f"No se encontró credentials.json en: {base_dir.parent} ni en {base_dir}")
        
    creds = Credentials.from_service_account_file(str(ruta_credenciales), scopes=SCOPES)
    cliente = gspread.authorize(creds)
    return cliente.open_by_url(SHEET_URL)

def consultar_datos_maestros_local(sigla_o_nombre: str) -> str:
    """Consulta la información estática de un local (supervisor, dirección, regional, mail, etc) basado en su sigla (ej: FVDP, FBER) o su nombre comercial (ej: Berazategui, Rotonda)."""
    print(f"[TOOL-CALL] consultar_datos_maestros_local con argumento: '{sigla_o_nombre}'", flush=True)
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Locales_Maestro")
        registros = hoja.get_all_records()
        busqueda = sigla_o_nombre.upper().strip()
        
        # 1. Buscar por coincidencia exacta de siglas
        for fila in registros:
            if str(fila.get('SIGLA SISTEMA', '')).upper() == busqueda or str(fila.get('SIGLA TICKETS', '')).upper() == busqueda:
                print(f"[TOOL-RESULT] Local encontrado por sigla: {fila.get('LOCAL')}", flush=True)
                return str(fila)
                
        # 2. Buscar si el nombre del local contiene el término de búsqueda
        for fila in registros:
            if busqueda in str(fila.get('LOCAL', '')).upper():
                print(f"[TOOL-RESULT] Local encontrado por nombre: {fila.get('LOCAL')}", flush=True)
                return str(fila)
                
        print(f"[TOOL-RESULT] No se encontró ningún local para: '{sigla_o_nombre}'", flush=True)
        return f"No se encontró ningún local con sigla o nombre '{sigla_o_nombre}' en la base de datos."
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_datos_maestros_local: {e}", flush=True)
        return f"Error consultando la base: {str(e)}"

def consultar_ultimo_mantenimiento(sigla_o_nombre: str) -> str:
    """Devuelve el último reporte de mantenimiento para un local basado en su sigla (ej: FVDP) o nombre comercial (ej: Berazategui, Rotonda)."""
    print(f"[TOOL-CALL] consultar_ultimo_mantenimiento con argumento: '{sigla_o_nombre}'", flush=True)
    try:
        sabana = _obtener_sabana()
        busqueda = sigla_o_nombre.upper().strip()
        
        # Primero, intentar encontrar la sigla en la pestaña maestra de locales
        hoja_maestro = sabana.worksheet("Locales_Maestro")
        registros_maestro = hoja_maestro.get_all_records()
        
        sigla_encontrada = None
        for fila in registros_maestro:
            if busqueda in [str(fila.get('SIGLA SISTEMA', '')).upper(), str(fila.get('SIGLA TICKETS', '')).upper()]:
                sigla_encontrada = str(fila.get('SIGLA SISTEMA', '')).upper()
                break
            if busqueda in str(fila.get('LOCAL', '')).upper():
                sigla_encontrada = str(fila.get('SIGLA SISTEMA', '')).upper()
                break
                
        if not sigla_encontrada:
            # Fallback: Usar el término de búsqueda directamente si no se encontró en el maestro
            sigla_encontrada = busqueda
            
        hoja = sabana.worksheet("Historial_Mantenimiento")
        registros = hoja.get_all_records()
        
        # Filtrar por la sigla resuelta
        reportes_local = [r for r in registros if str(r.get('SIGLA', '')).upper() == sigla_encontrada]
        
        if not reportes_local:
            print(f"[TOOL-RESULT] No hay mantenimientos para: '{sigla_o_nombre}' (sigla: {sigla_encontrada})", flush=True)
            return f"No hay reportes de mantenimiento registrados para el local '{sigla_o_nombre}' (sigla: {sigla_encontrada})."
            
        ultimo = reportes_local[-1] # El más reciente
        print(f"[TOOL-RESULT] Mantenimiento encontrado para: '{sigla_o_nombre}' (sigla: {sigla_encontrada})", flush=True)
        return f"Último Mantenimiento para '{sigla_o_nombre}' (sigla: {sigla_encontrada}): Fecha {ultimo.get('FECHA_REPORTE')}, Técnico {ultimo.get('TECNICO')}, Ticket {ultimo.get('TICKET')}, PPM {ultimo.get('PPM_AGUA')}, Shots {ultimo.get('SHOTS')}, Estado {ultimo.get('ESTADO')}."
    except Exception as e:
        print(f"[TOOL-ERROR] Error en consultar_ultimo_mantenimiento: {e}", flush=True)
        return f"Error consultando el historial: {str(e)}"

def listar_alertas_activas() -> str:
    """Devuelve una lista resumen de todos los locales que actualmente tienen alertas rojas o mantenimientos pendientes."""
    print("[TOOL-CALL] listar_alertas_activas sin argumentos", flush=True)
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Alertas_Activas")
        registros = hoja.get_all_records()
        
        alertas_abiertas = [r for r in registros if str(r.get('ESTADO', '')).upper() == 'ABIERTA']
        
        if not alertas_abiertas:
            print("[TOOL-RESULT] No hay alertas abiertas", flush=True)
            return "No hay ninguna alerta activa en la Sábana en este momento. ¡Todo en orden!"
            
        resumen = "Alertas Activas:\n"
        for a in alertas_abiertas:
            resumen += f"- [{a.get('SIGLA')}] {a.get('TIPO_ALERTA')} Nivel {a.get('NIVEL')}: {a.get('MENSAJE')}\n"
        print(f"[TOOL-RESULT] Se encontraron {len(alertas_abiertas)} alertas abiertas", flush=True)
        return resumen
    except Exception as e:
        print(f"[TOOL-ERROR] Error en listar_alertas_activas: {e}", flush=True)
        return f"Error consultando las alertas: {str(e)}"
