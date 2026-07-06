import pandas as pd
import os
from datetime import datetime

def encontrar_tecnico(store_id, df_tec):
    store_id = str(store_id).strip().upper()
    if store_id == 'NAN' or not store_id:
        return pd.Series(dtype='object')
        
    # 1. Exact match en sigla_tickets
    match = df_tec[df_tec['sigla_tickets'].astype(str).str.upper() == store_id]
    if not match.empty:
        return match.iloc[0]
        
    # 2. Exact match en sigla_sistema
    match = df_tec[df_tec['sigla_sistema'].astype(str).str.upper() == store_id]
    if not match.empty:
        return match.iloc[0]

    # 3. Substring match
    if len(store_id) >= 3:
        for idx, row in df_tec.iterrows():
            st = str(row['sigla_tickets']).upper()
            ss = str(row['sigla_sistema']).upper()
            if (st != 'NAN' and store_id in st) or (ss != 'NAN' and store_id in ss):
                return row
            
    # Si no hay match
    return pd.Series(dtype='object')

def cruzar_df(df, df_tec):
    if df.empty:
        return df
    
    res = []
    for idx, row in df.iterrows():
        store_val = row.get('Cód. de Sucursal', '')
        if pd.isna(store_val) or str(store_val).strip() == '':
            store_val = row.get('Sucursal', '')
            
        match_series = encontrar_tecnico(store_val, df_tec)
        
        # Filtrar locales que NO están a nuestro cargo
        if match_series.empty:
            continue
            
        # Combine
        combined = row.to_dict()
        combined['tecnico_asignado_matriz'] = match_series.get('tecnico_asignado', '')
        combined['regional'] = match_series.get('regional', '')
        combined['supervisor'] = match_series.get('supervisor', '')
        combined['local_maestro'] = match_series.get('local', '')
        combined['sigla_sistema_matriz'] = match_series.get('sigla_sistema', '')
        combined['sigla_tickets_matriz'] = match_series.get('sigla_tickets', '')
        
        res.append(combined)
    
    return pd.DataFrame(res)

def main():
    tickets_path = "/home/cristian/Documentos/Supervisor/base_tickets/Historial_Tickets.xlsx"
    tecnicos_path = "/home/cristian/Descargas/Telegram Desktop/Locales_Asignados.xlsx"
    salida_dir = "/home/cristian/Documentos/Supervisor/base_tickets"
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    salida_path = os.path.join(salida_dir, f"Tickets_Activos_Cruzados_{fecha_hoy}.xlsx")

    print(f"[*] Cargando archivo histórico descargado: {tickets_path}")
    if not os.path.exists(tickets_path):
        print(f"[-] El archivo {tickets_path} no existe. Saliendo.")
        return
        
    df_tickets = pd.read_excel(tickets_path)
    print(f"[+] Registros totales descargados: {len(df_tickets)}")
    
    # Filtrar categoría "Lista de Mantenimiento"
    df_tickets = df_tickets[df_tickets['Categoría'].astype(str).str.upper() != 'LISTA DE MANTENIMIENTO']
    
    print("[*] Filtrando tickets abiertos/excedidos...")
    # Filtrar todo lo que no sea 'Resuelto' ni 'Cerrado'
    df_activos = df_tickets[~df_tickets['Estado'].isin(['Resuelto', 'Cerrado'])]
    print(f"[+] Registros activos: {len(df_activos)}")
    
    print("[*] Cargando matriz de técnicos...")
    df_tecnicos = pd.read_excel(tecnicos_path)

    print("[*] Cruzando información y filtrando locales propios...")
    df_cruzado = cruzar_df(df_activos, df_tecnicos)
    print(f"[+] Registros cruzados resultantes: {len(df_cruzado)}")

    print(f"[*] Guardando archivo final en {salida_path}...")
    df_cruzado.to_excel(salida_path, index=False)
        
    print("[+] Proceso de cruce completado con éxito.")
    
    with open("/tmp/ultimo_excel_cruzado.txt", "w") as f:
        f.write(os.path.abspath(salida_path))

if __name__ == "__main__":
    main()
