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

def main():
    notebooks = get_notebooks()
    notebook_map = {}
    for nb in notebooks:
        title = nb.get("title", "")
        # Extraer la sigla que está entre corchetes, ej: "[FVDP] - VILLA DEL PARQUE"
        if "[" in title and "]" in title:
            sigla = title.split("[")[1].split("]")[0].strip()
            notebook_map[sigla] = nb["id"]

    files = glob.glob(os.path.join(LOCALES_DIR, "*.*"))
    uploaded = 0
    errors = 0

    print(f"Se encontraron {len(files)} archivos para sincronizar.")

    for file in files:
        filename = os.path.basename(file)
        sigla_file = os.path.splitext(filename)[0]
        
        nb_id = notebook_map.get(sigla_file)
        
        if not nb_id:
            # Búsqueda difusa para casos especiales (ej: "MERCADO_PARAGUAY_X_15")
            for nb_sigla, nid in notebook_map.items():
                if sigla_file in nb_sigla or nb_sigla in sigla_file:
                    nb_id = nid
                    break
                    
        if nb_id:
            print(f"Subiendo '{filename}' a cuaderno '{sigla_file}' ({nb_id})...")
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            
            try:
                # Deshabilitamos output capture por si nlm necesita mostrar progreso, 
                # aunque add text por API es rápido.
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
