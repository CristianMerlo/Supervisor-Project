import pandas as pd
import os
import sys
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import notificador_telegram

PROJECT_ROOT = "/home/cristian/PROYECTOS/Supervisor-Project"
sys.path.append(PROJECT_ROOT)

def encontrar_tecnico(store_id, df_tec):
    store_id = str(store_id).strip().upper()
    if store_id == 'NAN' or not store_id:
        return pd.Series(dtype='object')
        
    match = df_tec[df_tec['sigla_tickets'].astype(str).str.upper() == store_id]
    if not match.empty:
        return match.iloc[0]
        
    match = df_tec[df_tec['sigla_sistema'].astype(str).str.upper() == store_id]
    if not match.empty:
        return match.iloc[0]

    if len(store_id) >= 3:
        for idx, row in df_tec.iterrows():
            st = str(row['sigla_tickets']).upper()
            ss = str(row['sigla_sistema']).upper()
            if (st != 'NAN' and store_id in st) or (ss != 'NAN' and store_id in ss):
                return row
            
    return pd.Series(dtype='object')

def procesar_datos():
    tickets_path = "/home/cristian/Documentos/Supervisor/base_tickets/Historial_Tickets.xlsx"
    tecnicos_path = "/home/cristian/Descargas/Telegram Desktop/Locales_Asignados.xlsx"
    
    if not os.path.exists(tickets_path):
        print(f"[-] Archivo {tickets_path} no encontrado.")
        return None, None
        
    df_tickets = pd.read_excel(tickets_path)
    df_tecnicos = pd.read_excel(tecnicos_path)
    
    # Filtrar categoría "Lista de Mantenimiento"
    df_tickets = df_tickets[df_tickets['Categoría'].astype(str).str.upper() != 'LISTA DE MANTENIMIENTO']
    
    # Cruzar y filtrar
    res = []
    for idx, row in df_tickets.iterrows():
        store_val = row.get('Cód. de Sucursal', '')
        if pd.isna(store_val) or str(store_val).strip() == '':
            store_val = row.get('Sucursal', '')
            
        match_series = encontrar_tecnico(store_val, df_tecnicos)
        
        if match_series.empty:
            continue
            
        combined = row.to_dict()
        combined['tecnico_asignado_matriz'] = match_series.get('tecnico_asignado', 'Desconocido')
        combined['supervisor'] = match_series.get('supervisor', '')
        res.append(combined)
        
    df_cruzado = pd.DataFrame(res)
    
    if df_cruzado.empty:
        return df_cruzado, df_cruzado
        
    # Filtrar abiertos
    df_abiertos = df_cruzado[~df_cruzado['Estado'].isin(['Resuelto', 'Cerrado'])].copy()
    
    # Filtrar cerrados en el mes
    mes_actual = datetime.now().strftime("%Y-%m")
    
    def es_mes_actual(val):
        if pd.isna(val):
            return False
        try:
            return str(val).startswith(mes_actual)
        except:
            return False

    df_cerrados = df_cruzado[df_cruzado['Estado'].isin(['Resuelto', 'Cerrado'])].copy()
    df_cerrados_mes = df_cerrados[df_cerrados['Fecha de Resolución'].apply(es_mes_actual)].copy()
    
    return df_abiertos, df_cerrados_mes

def actualizar_sheets(df_abiertos, df_cerrados_mes):
    try:
        ruta_credenciales = os.path.join(PROJECT_ROOT, "credentials.json")
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(ruta_credenciales, scopes=scopes)
        cliente = gspread.authorize(creds)
        
        sheet_url = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing"
        sabana = cliente.open_by_url(sheet_url)
        
        # Consolidado de métricas por técnico
        resumen = {}
        for tec in df_abiertos['tecnico_asignado_matriz'].unique():
            if pd.isna(tec): continue
            resumen[tec] = {"Abiertos": len(df_abiertos[df_abiertos['tecnico_asignado_matriz'] == tec]), "Cerrados": 0}
            
        for tec in df_cerrados_mes['tecnico_asignado_matriz'].unique():
            if pd.isna(tec): continue
            if tec not in resumen:
                resumen[tec] = {"Abiertos": 0, "Cerrados": 0}
            resumen[tec]["Cerrados"] = len(df_cerrados_mes[df_cerrados_mes['tecnico_asignado_matriz'] == tec])
            
        try:
            ws = sabana.worksheet("Resumen_Diario_Tecnicos")
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = sabana.add_worksheet(title="Resumen_Diario_Tecnicos", rows="100", cols="5")
            
        datos_sheets = [["Fecha Reporte", datetime.now().strftime("%Y-%m-%d %H:%M:%S")], [], ["Técnico", "Tickets Abiertos", "Tickets Cerrados (Mes)"]]
        for tec, counts in resumen.items():
            datos_sheets.append([tec, counts["Abiertos"], counts["Cerrados"]])
            
        ws.update("A1", datos_sheets)
        print("[+] Sheets actualizado correctamente.")
        return resumen
    except Exception as e:
        print(f"[-] Error actualizando Sheets: {e}")
        return {}

def main():
    print("[*] Generando reporte diario de técnicos...")
    df_abiertos, df_cerrados_mes = procesar_datos()
    
    if df_abiertos is None:
        return
        
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    salida_path = f"/home/cristian/Documentos/Supervisor/base_tickets/Reporte_Diario_{fecha_hoy}.xlsx"
    
    with pd.ExcelWriter(salida_path, engine='openpyxl') as writer:
        df_abiertos.to_excel(writer, sheet_name='Tickets Abiertos', index=False)
        df_cerrados_mes.to_excel(writer, sheet_name='Cerrados Mes Vigente', index=False)
        
    resumen = actualizar_sheets(df_abiertos, df_cerrados_mes)
    
    # Armar texto Telegram
    msg = "📊 *Reporte Diario de Tickets por Técnico*\n\n"
    for tec, counts in resumen.items():
        msg += f"👨‍🔧 *{tec}*\n  🔸 Abiertos: {counts['Abiertos']}\n  ✅ Cerrados (Mes): {counts['Cerrados']}\n\n"
        
    msg += "Se adjunta el Excel detallado con ambas pestañas. También actualicé la pestaña 'Resumen_Diario_Tecnicos' en La Sábana."
    
    try:
        notificador_telegram.enviar_archivo(
            ruta_archivo=salida_path,
            caption=msg
        )
        print("[+] Enviado por Telegram exitosamente.")
    except Exception as e:
        print(f"[-] Error enviando a Telegram: {e}")

if __name__ == "__main__":
    main()

