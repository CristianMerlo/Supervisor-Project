import sys
import os
import json
import subprocess
from pathlib import Path
from archivador_drive import obtener_sigla_sistema

NLM_CMD = "/home/cristian/.local/bin/nlm"
LOCALES_DIR = Path(__file__).parent / "brain" / "locales"

def get_notebooks():
    res = subprocess.run([NLM_CMD, "list", "notebooks", "--json"], capture_output=True, text=True)
    if res.returncode == 0:
        return json.loads(res.stdout)
    return []

def get_sources(nb_id):
    res = subprocess.run([NLM_CMD, "source", "list", nb_id, "--json"], capture_output=True, text=True)
    if res.returncode == 0:
        try:
            return json.loads(res.stdout)
        except json.JSONDecodeError:
            return []
    return []

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 actualizar_notebook_local.py <SIGLA>")
        sys.exit(1)
        
    sigla_ticket = sys.argv[1].upper()
    file_path = LOCALES_DIR / f"{sigla_ticket}.md"
    
    if not file_path.exists():
        print(f"Error: No existe el archivo local {file_path}")
        sys.exit(1)
        
    sigla_sistema = obtener_sigla_sistema(sigla_ticket)
    notebooks = get_notebooks()
    nb_id = None
    
    for nb in notebooks:
        title = nb.get("title", "")
        if f"[{sigla_sistema}]" in title:
            nb_id = nb["id"]
            break
            
    if not nb_id:
        print(f"No se encontró un cuaderno en NotebookLM para la sigla {sigla_sistema} (mapeada de {sigla_ticket})")
        sys.exit(1)
        
    print(f"Actualizando cuaderno de {sigla_ticket} (sistema: {sigla_sistema}) (ID: {nb_id})")
    
    # Listar fuentes actuales
    sources = get_sources(nb_id)
    filename = f"{sigla_ticket}.md"
    
    # (Borrado deshabilitado por instrucción del usuario para mantener historial de visitas)
    # for src in sources:
    #     if src.get("title") == filename:
    #         src_id = src.get("id")
    #         print(f"Eliminando fuente vieja {filename} (ID: {src_id})")
    #         subprocess.run([NLM_CMD, "source", "delete", nb_id, src_id, "--force"], capture_output=True)
            
    # Subir nueva fuente
    print(f"Subiendo fuente actualizada {filename}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    import datetime
    fecha_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    titulo_historial = f"{sigla_ticket}_{fecha_str}.md"
    
    res_add = subprocess.run(
        [NLM_CMD, "add", "text", nb_id, content, "--title", titulo_historial],
        capture_output=True, text=True
    )
    
    if res_add.returncode == 0:
        print(f"✅ Cuaderno de {sigla_ticket} (sistema: {sigla_sistema}) actualizado en NotebookLM exitosamente.")
    else:
        print(f"❌ Error actualizando NotebookLM: {res_add.stderr}")

if __name__ == "__main__":
    main()
