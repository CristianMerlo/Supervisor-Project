import pandas as pd
import numpy as np

class DataAuditor:
    def __init__(self):
        pass

    def audit_dataframe(self, df: pd.DataFrame, source_name: str) -> dict:
        """
        Escanea un DataFrame en busca de anomalías.
        Retorna un diccionario con los hallazgos y un booleano indicando si es seguro continuar.
        """
        report = {
            "source": source_name,
            "total_rows": len(df),
            "is_clean": True,
            "issues": []
        }

        if df.empty:
            report["is_clean"] = False
            report["issues"].append("El dataframe está vacío.")
            return report

        # Buscar duplicados
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            report["is_clean"] = False
            report["issues"].append(f"Se encontraron {duplicates} filas duplicadas.")

        # Buscar valores nulos
        nulls = df.isnull().sum()
        total_nulls = nulls.sum()
        if total_nulls > 0:
            report["is_clean"] = False
            report["issues"].append(f"Se encontraron {total_nulls} valores nulos repartidos en las columnas.")
            for col, count in nulls.items():
                if count > 0:
                    report["issues"].append(f"  - Columna '{col}': {count} nulos")

        return report

if __name__ == "__main__":
    # Test rápido
    print("Iniciando Data Auditor Test...")
    auditor = DataAuditor()
    df_test = pd.DataFrame({
        "ID": [1, 2, 2, 4],
        "Local": ["FVDP", "CABA", "CABA", None]
    })
    resultado = auditor.audit_dataframe(df_test, "Test DF")
    print(resultado)
