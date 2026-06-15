import os
import glob
import PyPDF2
from pathlib import Path

def extraer_texto_pdf(pdf_path):
    texto = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                texto += page.extract_text() or ""
    except Exception as e:
        print(f"[ERROR] Falló extracción en {pdf_path}: {e}")
    return texto.strip()

def main():
    DIR_ORIGEN = "/home/cristian/Documentos/Supervisor/brain/manuales"
    DIR_DESTINO = "/home/cristian/PROYECTOS/Supervisor-Project/brain/01_Manuales_Tecnicos"
    
    os.makedirs(DIR_DESTINO, exist_ok=True)
    
    pdfs = glob.glob(os.path.join(DIR_ORIGEN, "*.pdf"))
    if not pdfs:
        print("No se encontraron PDFs en la carpeta de origen.")
        return
        
    for pdf_path in pdfs:
        nombre_base = Path(pdf_path).stem
        # Limpiar el nombre para markdown
        nombre_limpio = nombre_base.replace(" ", "_").replace("-", "_").replace("__", "_")
        md_path = os.path.join(DIR_DESTINO, f"{nombre_limpio}.md")
        
        print(f"Evaluando: {nombre_base}")
        
        if os.path.exists(md_path):
            # Ya existe, lo saltamos para no procesar de más
            continue
            
        print(f"Convirtiendo: {nombre_base} -> {nombre_limpio}.md")
        
        texto_pdf = extraer_texto_pdf(pdf_path)
        
        if texto_pdf:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Manual: {nombre_base}\n\n")
                f.write(texto_pdf)
            print(f"[OK] Archivo guardado: {md_path}")
        else:
            print(f"[WARN] Texto vacío extraído de: {pdf_path}")

if __name__ == "__main__":
    main()
