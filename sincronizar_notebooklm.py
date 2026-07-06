import os
import json
import subprocess
import glob

NLM_CMD = "/home/cristian/.local/bin/nlm"
LOCALES_DIR = "/home/cristian/PROYECTOS/Supervisor-Project/brain/locales"

def get_notebooks():
    result = subprocess.run([NLM_CMD, "list", "notebooks", "--json"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error al listar notebooks:", result.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error decodificando la respuesta JSON de nlm.")
        return []

def sincronizar_local_especifico(sigla):
    """Sincroniza una ficha local específica con su cuaderno en NotebookLM."""
    sigla = sigla.upper().strip()
    notebooks = get_notebooks()
    notebook_map = {}
    for nb in notebooks:
        title = nb.get("title", "")
        if "[" in title and "]" in title:
            nb_sigla = title.split("[")[1].split("]")[0].strip().upper()
            notebook_map[nb_sigla] = nb["id"]

    nb_id = notebook_map.get(sigla)
    if not nb_id:
        for nb_sigla, nid in notebook_map.items():
            if sigla in nb_sigla or nb_sigla in sigla:
                nb_id = nid
                break
                
    if not nb_id:
        print(f"⚠️ No se encontró cuaderno en NotebookLM para la sigla '{sigla}'")
        return False
        
    file_path = os.path.join(LOCALES_DIR, f"{sigla}.md")
    if not os.path.exists(file_path):
        print(f"❌ Archivo local {file_path} no existe.")
        return False
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    filename = f"{sigla}.md"
    print(f"Subiendo '{filename}' a cuaderno '{sigla}' ({nb_id})...")
    
    try:
        res = subprocess.run(
            [NLM_CMD, "add", "text", nb_id, content, "--title", filename],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            print(f"  ✅ '{filename}' subido exitosamente a NotebookLM.")
            return True
        else:
            print(f"  ❌ Error subiendo '{filename}': {res.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Excepción al subir '{filename}' a NotebookLM: {e}")
        return False

def main():
    notebooks = get_notebooks()
    notebook_map = {}
    for nb in notebooks:
        title = nb.get("title", "")
        if "[" in title and "]" in title:
            sigla = title.split("[")[1].split("]")[0].strip()
            notebook_map[sigla] = nb["id"]

    files = glob.glob(os.path.join(LOCALES_DIR, "*.md"))
    uploaded = 0
    errors = 0

    print(f"Se encontraron {len(files)} archivos para sincronizar.")

    for file in files:
        filename = os.path.basename(file)
        sigla_file = os.path.splitext(filename)[0]
        
        nb_id = notebook_map.get(sigla_file)
        if not nb_id:
            for nb_sigla, nid in notebook_map.items():
                if sigla_file in nb_sigla or nb_sigla in sigla_file:
                    nb_id = nid
                    break
                    
        if nb_id:
            print(f"Subiendo '{filename}' a cuaderno '{sigla_file}' ({nb_id})...")
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            
            try:
                res = subprocess.run(
                    [NLM_CMD, "add", "text", nb_id, content, "--title", filename],
                    capture_output=True, text=True
                )
                if res.returncode == 0:
                    print(f"  ✅ '{filename}' subido exitosamente.")
                    uploaded += 1
                else:
                    print(f"  ❌ Error subiendo '{filename}': {res.stderr}")
                    errors += 1
            except Exception as e:
                print(f"  ❌ Excepción al subir '{filename}': {e}")
                errors += 1
        else:
            print(f"  ⚠️ No se encontró cuaderno en NotebookLM para la sigla '{sigla_file}'")
            
    print(f"\nSincronización Finalizada.")
    print(f"✅ Subidos exitosamente: {uploaded}")
    print(f"❌ Errores: {errors}")
    print(f"⚠️ No encontrados: {len(files) - uploaded - errors}")

if __name__ == "__main__":
    main()
