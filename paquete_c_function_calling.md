# Paquete de Despliegue: Paso C (Function Calling para Hermes)

**Instrucciones para el Antigravity de la máquina destino:**
Hola de nuevo. Es momento de dotar a Hermes (el bot de Telegram) de visión sobre la base de datos para que deje de dar respuestas genéricas. Para esto, utilizaremos la capacidad de *Function Calling* nativa de la API de Gemini.

Sigue estos pasos para implementar las herramientas y conectarlas al servidor FastAPI (`server.py`).

---

## 1. Crear el Módulo `herramientas_hermes.py`
Crea este nuevo archivo en la misma carpeta donde tienes `server.py`. Este módulo utilizará `gspread` para consultar la Sábana.

```python
import os
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_URL = os.getenv("SHEETS_SABANA_URL", "PEGAR_URL_SABANA")

def _obtener_sabana():
    ruta_credenciales = "credentials.json"
    if not os.path.exists(ruta_credenciales):
        # Si estás en otra subcarpeta, ajusta la ruta
        ruta_credenciales = "../credentials.json" 
    creds = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    return cliente.open_by_url(SHEET_URL)

def consultar_datos_maestros_local(sigla: str) -> str:
    \"\"\"Consulta la información estática de un local (supervisor, dirección, etc) basado en su sigla (ej: FVDP).\"\"\"
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Locales_Maestro")
        registros = hoja.get_all_records()
        for fila in registros:
            if fila.get('SIGLA SISTEMA', '').upper() == sigla.upper() or fila.get('SIGLA TICKETS', '').upper() == sigla.upper():
                return str(fila)
        return f"No se encontró el local con sigla {sigla} en la base de datos."
    except Exception as e:
        return f"Error consultando la base: {str(e)}"

def consultar_ultimo_mantenimiento(sigla: str) -> str:
    \"\"\"Devuelve el último reporte de mantenimiento inyectado para un local específico, incluyendo PPM y shots.\"\"\"
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Historial_Mantenimiento")
        registros = hoja.get_all_records()
        
        # Filtrar por sigla y obtener el más reciente (asumiendo orden cronológico)
        reportes_local = [r for r in registros if r.get('SIGLA', '').upper() == sigla.upper()]
        
        if not reportes_local:
            return f"No hay reportes de mantenimiento registrados para el local {sigla}."
            
        ultimo = reportes_local[-1] # El último insertado
        return f"Último Mantenimiento {sigla}: Fecha {ultimo.get('FECHA_REPORTE')}, Técnico {ultimo.get('TECNICO')}, Ticket {ultimo.get('TICKET')}, PPM {ultimo.get('PPM_AGUA')}, Shots {ultimo.get('SHOTS')}, Estado {ultimo.get('ESTADO')}."
    except Exception as e:
        return f"Error consultando el historial: {str(e)}"

def listar_alertas_activas() -> str:
    \"\"\"Devuelve una lista resumen de todos los locales que actualmente tienen alertas rojas o mantenimientos pendientes.\"\"\"
    try:
        sabana = _obtener_sabana()
        hoja = sabana.worksheet("Alertas_Activas")
        registros = hoja.get_all_records()
        
        alertas_abiertas = [r for r in registros if r.get('ESTADO', '').upper() == 'ABIERTA']
        
        if not alertas_abiertas:
            return "No hay ninguna alerta activa en la Sábana en este momento. ¡Todo en orden!"
            
        resumen = "Alertas Activas:\\n"
        for a in alertas_abiertas:
            resumen += f"- [{a.get('SIGLA')}] {a.get('TIPO_ALERTA')} Nivel {a.get('NIVEL')}: {a.get('MENSAJE')}\\n"
        return resumen
    except Exception as e:
        return f"Error consultando las alertas: {str(e)}"
```

---

## 2. Integrar las Herramientas en `server.py`
Ahora ve al script `server.py` de tu API (donde configuras el modelo de Gemini) e inyéctale estas funciones para que el LLM sepa que existen y las pueda usar.

Busca donde inicializas el modelo de Gemini (algo como `genai.GenerativeModel(...)`) y modifícalo así:

```python
import google.generativeai as genai
from herramientas_hermes import consultar_datos_maestros_local, consultar_ultimo_mantenimiento, listar_alertas_activas

# Pasamos las funciones de Python directo al modelo (Requisito: Gemini 1.5 Flash o Pro)
herramientas = [
    consultar_datos_maestros_local,
    consultar_ultimo_mantenimiento,
    listar_alertas_activas
]

# Modifica la inicialización de tu modelo actual para incluir `tools`
modelo_supervisor = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="Eres Hermes, el bot Supervisor. Tienes acceso a herramientas para consultar la base de datos de Sheets. Úsalas siempre que el usuario pregunte por datos de un local, mantenimientos o alertas.",
    tools=herramientas
)
```

### 2.1 Habilitar la Invocación Automática (Auto-Call)
Cuando mandas el mensaje de chat (`chat.send_message`), asegúrate de tener `enable_automatic_function_calling` activado para que la librería de Python se encargue de ejecutar la función por detrás de escena y devolverle el resultado a Gemini:

```python
# Ejemplo de cómo debería quedar tu inicio de chat en server.py
chat = modelo_supervisor.start_chat(enable_automatic_function_calling=True)

# Cuando recibes el mensaje de Telegram
respuesta = chat.send_message(mensaje_usuario)
print(respuesta.text) # Gemini ya responderá con los datos reales que obtuvo de la herramienta
```

**Conclusión:**
Reemplaza el código de tu `server.py` para inyectarle estas 3 funciones. Reinicia el servidor (`systemctl restart tu_servicio_api` o `restore_telegram.sh`). A partir de este momento, si le escribes al bot de Telegram: *"Hermes, pásame el estado del local FVDP"*, el bot internamente ejecutará `consultar_ultimo_mantenimiento('FVDP')` y te responderá con la info exacta. ¡Haz la prueba!
