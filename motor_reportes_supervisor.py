import os
import sys
import pandas as pd
from datetime import datetime
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from skills.skill_data_auditor import DataAuditor
from skills.skill_pivot_builder import PivotBuilder
from skills.skill_theme_engine import ThemeEngine
from notificador_telegram import enviar_alerta

SHEETS_SABANA_URL = os.getenv("SHEETS_SABANA_URL", "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing")

class ReportSupervisor:
    def __init__(self):
        self.auditor = DataAuditor()
        self.pivot_builder = PivotBuilder()
        self.theme_engine = ThemeEngine()

    def obtener_cliente_sheets(self):
        ruta_credenciales = os.path.join(os.path.dirname(__file__), "credentials.json")
        if not os.path.exists(ruta_credenciales):
            raise FileNotFoundError("Falta credentials.json")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(ruta_credenciales, scopes=scopes)
        return gspread.authorize(creds)

    def obtener_datos(self):
        enviar_alerta("Conectando a 'La Sábana' de Google Sheets...", tipo="INFO")
        try:
            cliente = self.obtener_cliente_sheets()
            sabana = cliente.open_by_url(SHEETS_SABANA_URL)
            hoja_historial = sabana.worksheet("Historial_Mantenimiento")
            registros = hoja_historial.get_all_records()
            df = pd.DataFrame(registros)
            enviar_alerta(f"Datos descargados exitosamente. {len(df)} filas encontradas.", tipo="INFO")
            return df
        except Exception as e:
            enviar_alerta(f"Error al descargar datos: {e}", tipo="ERROR")
            return pd.DataFrame()

    def interpretar_pedido_llm(self, prompt: str, columnas_disponibles: list):
        """
        Usa el modelo para decidir qué agrupar y cómo en base al prompt en texto libre.
        """
        enviar_alerta("🤖 LLM: Interpretando solicitud de reporte...", tipo="INFO")
        system_prompt = f"""
        Eres un experto en análisis de datos. 
        El usuario solicitó: '{prompt}'.
        Las columnas disponibles son: {columnas_disponibles}.
        Debes decidir cómo agrupar los datos en una tabla dinámica de Pandas (pivot_table).
        Responde ÚNICAMENTE con un JSON puro (sin marcas de markdown) con esta estructura:
        {{
            "index": ["columna_para_agrupar_filas"],
            "values": ["columna_a_sumar_o_contar"],
            "aggfunc": "sum" o "count" o "mean"
        }}
        Si el usuario no especifica, sugiere un index=["SIGLA"] y values=["TICKET"] con aggfunc="count".
        """
        try:
            url = "http://127.0.0.1:8000/v1/chat/completions"
            payload = {
                "model": "gemini-2.0-flash",
                "messages": [{"role": "system", "content": system_prompt}]
            }
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                respuesta_texto = res.json()["choices"][0]["message"]["content"].strip()
                # Limpiar backticks si los hay
                respuesta_texto = respuesta_texto.replace("```json", "").replace("```", "").strip()
                parametros = json.loads(respuesta_texto)
                return parametros
        except Exception as e:
            print(f"Error llamando al LLM: {e}")
        
        # Fallback por defecto si el LLM falla
        return {"index": ["SIGLA"], "values": ["TICKET"], "aggfunc": "count"}

    def generar_reporte_dinamico(self, instruccion_usuario: str = "Reporte general"):
        enviar_alerta(f"Iniciando reporte dinámico: '{instruccion_usuario}'", tipo="INFO")
        
        df_bruto = self.obtener_datos()
        if df_bruto.empty:
            return None

        # Auditoría
        audit_report = self.auditor.audit_dataframe(df_bruto, "Historial Mantenimiento")
        if not audit_report["is_clean"]:
            enviar_alerta("⚠️ Se encontraron errores leves en los datos. Procediendo de todos modos.", tipo="WARN")

        # Interpretar con LLM
        columnas = df_bruto.columns.tolist()
        params_pivot = self.interpretar_pedido_llm(instruccion_usuario, columnas)
        
        enviar_alerta(f"Configurando tabla dinámica con index={params_pivot.get('index')} y valores={params_pivot.get('values')}", tipo="INFO")
        
        df_resumen = self.pivot_builder.create_pivot_table(
            df_bruto, 
            index=params_pivot.get("index", ["SIGLA"]), 
            values=params_pivot.get("values", ["TICKET"]), 
            aggfunc=params_pivot.get("aggfunc", "count")
        )

        # Generar Excel
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = os.path.join(os.path.dirname(__file__), f"Reporte_Dinamico_{fecha_str}.xlsx")
        
        success = self.theme_engine.export_to_excel(df_bruto, df_resumen, output_path)

        if success:
            enviar_alerta(f"✅ Reporte dinámico generado exitosamente.", tipo="INFO")
            return output_path
        else:
            enviar_alerta("❌ Error al generar el Excel.", tipo="ERROR")
            return None

if __name__ == "__main__":
    # Test local
    supervisor = ReportSupervisor()
    supervisor.generar_reporte_dinamico("Quiero ver la cantidad de tickets por técnico")
