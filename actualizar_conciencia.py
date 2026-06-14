import os
import sys
import subprocess
import glob

NLM_CMD = "/home/cristian/.local/bin/nlm"
PROYECTO_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/proyecto"
NB_ID = "1b458b5b-af6f-4681-bf33-7b19bd028488"

def main():
    print("==================================================")
    print("🧠 ACTUALIZANDO CONCIENCIA DEL PROYECTO EN NOTEBOOKLM")
    print("==================================================\n")
    
    if not os.path.exists(PROYECTO_DIR):
        print(f"Error: No existe el directorio {PROYECTO_DIR}")
        sys.exit(1)
        
    md_files = glob.glob(os.path.join(PROYECTO_DIR, "*.md"))
    if not md_files:
        print("No se encontraron archivos .md en el directorio del proyecto.")
        sys.exit(0)
        
    print(f"Archivos a subir: {len(md_files)}\n")
    
    # 1. Obtener lista de fuentes actuales
    print("Consultando fuentes actuales en el cuaderno...")
    res_list = subprocess.run([NLM_CMD, "source", "list", NB_ID, "--json"], capture_output=True, text=True)
    import json
    sources = []
    if res_list.returncode == 0:
        try:
            sources = json.loads(res_list.stdout)
        except json.JSONDecodeError:
            pass
            
    # Borrar todas las fuentes actuales para hacer una subida limpia
    if sources:
        print(f"Eliminando {len(sources)} fuentes antiguas para refrescar memoria...")
        for src in sources:
            src_id = src.get("id")
            title = src.get("title", "")
            subprocess.run([NLM_CMD, "source", "delete", NB_ID, src_id, "--force"], capture_output=True)
            print(f" - Eliminado: {title}")
            
    print("\nIniciando subida de la nueva arquitectura...")
    # 2. Subir todos los archivos
    exitosos = 0
    for file_path in md_files:
        filename = os.path.basename(file_path)
        print(f"Subiendo: {filename}...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        res_add = subprocess.run(
            [NLM_CMD, "add", "text", NB_ID, content, "--title", filename],
            capture_output=True, text=True
        )
        if res_add.returncode == 0:
            exitosos += 1
        else:
            print(f"  ❌ Error al subir {filename}: {res_add.stderr}")
            
    print(f"\n✅ Conciencia actualizada. Se subieron {exitosos} de {len(md_files)} documentos de arquitectura.")
    print("Ya puedes hacerle preguntas a NotebookLM sobre su propio código.")

if __name__ == "__main__":
    main()
