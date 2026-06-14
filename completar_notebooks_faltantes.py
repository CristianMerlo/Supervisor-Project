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
        return []

def extract_name_from_md(filepath):
    # La primera línea tiene el formato: # Estado del Local: NOMBRE_LOCAL (SIGLA)
    with open(filepath, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if first_line.startswith("# Estado del Local:"):
            # Remover el prefijo
            parts = first_line.replace("# Estado del Local:", "").strip()
            # Remover la sigla al final, que está entre paréntesis "(SIGLA)"
            if "(" in parts and parts.endswith(")"):
                name = parts[:parts.rfind("(")].strip()
                return name
    return "DESCONOCIDO"

def main():
    print("Obteniendo lista de cuadernos actuales en NotebookLM...")
    notebooks = get_notebooks()
    notebook_map = {}
    for nb in notebooks:
        title = nb.get("title", "")
        if "[" in title and "]" in title:
            sigla = title.split("[")[1].split("]")[0].strip()
            notebook_map[sigla] = nb["id"]

    files = glob.glob(os.path.join(LOCALES_DIR, "*.md"))
    creados = 0
    errores = 0

    print(f"Verificando {len(files)} archivos locales...")

    for file in files:
        filename = os.path.basename(file)
        sigla_file = os.path.splitext(filename)[0]
        
        # Búsqueda exacta
        nb_id = notebook_map.get(sigla_file)
        
        # Búsqueda difusa si no es exacta
        if not nb_id:
            for nb_sigla, nid in notebook_map.items():
                if sigla_file in nb_sigla or nb_sigla in sigla_file:
                    nb_id = nid
                    break
        
        # Si sigue sin haber nb_id, significa que falta crearlo
        if not nb_id:
            local_name = extract_name_from_md(file)
            new_title = f"[{sigla_file}] - {local_name}"
            print(f"⚠️ Faltante detectado: {sigla_file}. Creando cuaderno '{new_title}'...")
            
            # Crear el cuaderno
            res_create = subprocess.run(
                [NLM_CMD, "create", "notebook", new_title],
                capture_output=True, text=True
            )
            
            if res_create.returncode == 0:
                try:
                    data = json.loads(res_create.stdout)
                    new_id = data.get("notebook_id")
                    if new_id:
                        print(f"  ✅ Cuaderno creado con ID: {new_id}. Subiendo reporte...")
                        with open(file, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        # Subir archivo al nuevo cuaderno
                        res_add = subprocess.run(
                            [NLM_CMD, "add", "text", new_id, content, "--title", filename],
                            capture_output=True, text=True
                        )
                        if res_add.returncode == 0:
                            print(f"  ✅ Reporte '{filename}' subido exitosamente.")
                            creados += 1
                        else:
                            print(f"  ❌ Error subiendo reporte: {res_add.stderr}")
                            errores += 1
                    else:
                        print("  ❌ No se pudo extraer el ID del cuaderno creado.")
                        errores += 1
                except Exception as e:
                    print(f"  ❌ Error parseando JSON de creación: {e}")
                    errores += 1
            else:
                print(f"  ❌ Error creando cuaderno: {res_create.stderr}")
                errores += 1

    print(f"\nFinalizado: {creados} nuevos cuadernos creados y sincronizados, {errores} errores.")

if __name__ == "__main__":
    main()
