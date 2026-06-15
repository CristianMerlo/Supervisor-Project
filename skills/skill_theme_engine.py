import pandas as pd
import xlsxwriter

class ThemeEngine:
    def __init__(self):
        pass

    def export_to_excel(self, df: pd.DataFrame, pivot_df: pd.DataFrame, output_path: str):
        """
        Exporta los dataframes a un archivo Excel aplicando estilos corporativos básicos.
        """
        try:
            # Creamos el escritor de Excel usando xlsxwriter
            writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
            
            # Escribir la data cruda
            df.to_excel(writer, sheet_name='Datos_Crudos', index=False)
            
            # Escribir la tabla dinámica
            if not pivot_df.empty:
                pivot_df.to_excel(writer, sheet_name='Resumen_Dinamico')
            
            workbook = writer.book
            
            # Definir algunos formatos
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Aplicar estilos a la hoja de Datos_Crudos
            worksheet_datos = writer.sheets['Datos_Crudos']
            for col_num, value in enumerate(df.columns.values):
                worksheet_datos.write(0, col_num, value, header_format)
                # Auto-ajustar ancho de columnas (básico)
                worksheet_datos.set_column(col_num, col_num, 15)

            # Aplicar estilos a la hoja de Resumen_Dinamico si existe
            if not pivot_df.empty:
                worksheet_resumen = writer.sheets['Resumen_Dinamico']
                # Ajustar columnas de la tabla dinámica
                worksheet_resumen.set_column(0, len(pivot_df.columns), 18)
            
            writer.close()
            print(f"[THEME ENGINE] Reporte generado exitosamente en: {output_path}")
            return True
        except Exception as e:
            print(f"[THEME ENGINE ERROR] Error al generar Excel: {e}")
            return False
