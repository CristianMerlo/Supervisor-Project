import pandas as pd

class PivotBuilder:
    def __init__(self):
        pass

    def create_pivot_table(self, df: pd.DataFrame, index: list, values: list, aggfunc='sum') -> pd.DataFrame:
        """
        Crea una tabla dinámica a partir de un DataFrame.
        """
        try:
            pivot = pd.pivot_table(df, index=index, values=values, aggfunc=aggfunc, fill_value=0)
            return pivot
        except Exception as e:
            print(f"[PIVOT ERROR] Error al crear la tabla dinámica: {e}")
            return pd.DataFrame()

    def merge_data(self, df_main: pd.DataFrame, df_secondary: pd.DataFrame, on_key: str, how='left') -> pd.DataFrame:
        """
        Cruza dos DataFrames emulando un BUSCARV.
        """
        try:
            merged = pd.merge(df_main, df_secondary, on=on_key, how=how)
            return merged
        except Exception as e:
            print(f"[JOIN ERROR] Error al cruzar los datos: {e}")
            return df_main
