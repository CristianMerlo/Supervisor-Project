import os
import json
import logging
import urllib.request
import urllib.error
import ssl

# Configuración del Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de Obsidian
OBSIDIAN_PORT = os.getenv("OBSIDIAN_PORT", "27124")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY", "")
BASE_URL = f"https://127.0.0.1:{OBSIDIAN_PORT}"

# Ignorar verificación SSL para certificados locales
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def _hacer_peticion(endpoint, method="GET", data=None):
    """Función base para hacer peticiones seguras a la API de Obsidian."""
    if not OBSIDIAN_API_KEY:
        logger.warning("No se ha configurado OBSIDIAN_API_KEY en el entorno.")
        return None

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {OBSIDIAN_API_KEY}",
        "Accept": "application/json"
    }

    req_data = None
    if data is not None:
        if isinstance(data, dict):
            req_data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            req_data = data.encode("utf-8")
            headers["Content-Type"] = "text/markdown"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
            content_type = response.info().get("Content-Type", "")
            respuesta = response.read()
            if "application/json" in content_type:
                return json.loads(respuesta)
            return respuesta.decode("utf-8")
    except urllib.error.HTTPError as e:
        logger.error(f"Error HTTP {e.code} en Obsidian API: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.error(f"Error de conexión con Obsidian: {e}")
    
    return None

def buscar_notas(query):
    """Busca un término exacto en la bóveda de Obsidian."""
    logger.info(f"Buscando en Obsidian: '{query}'")
    # El endpoint de búsqueda simple en el plugin Local REST API
    # query param debe ser encodeado
    import urllib.parse
    q_encoded = urllib.parse.quote(query)
    resultados = _hacer_peticion(f"/search/simple?query={q_encoded}")
    return resultados

def leer_nota(filepath):
    """Lee el contenido Markdown de una nota específica."""
    logger.info(f"Leyendo nota de Obsidian: {filepath}")
    import urllib.parse
    # El path debe estar url-encoded (ej: "Manuales/Maquina.md")
    path_encoded = urllib.parse.quote(filepath)
    return _hacer_peticion(f"/vault/{path_encoded}", method="GET")

if __name__ == "__main__":
    # Test rápido
    if not OBSIDIAN_API_KEY:
        print("⚠️ Configura OBSIDIAN_API_KEY para probar el cliente.")
    else:
        print("Iniciando prueba de conexión con Obsidian...")
        res = _hacer_peticion("/")
        if res is not None:
            print("✅ Conexión exitosa. Archivos en raíz:", len(res.get("files", [])))
