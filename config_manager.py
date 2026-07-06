import os
from pathlib import Path

ENV_PATHS = [
    Path("/home/cristian/Documentos/Supervisor/.env"),
    Path("/home/cristian/PROYECTOS/Supervisor-Project/.env")
]

def get_env_var(key, default=None):
    for path in ENV_PATHS:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith(f"{key}="):
                            return line.strip().split("=", 1)[1].strip()
            except Exception:
                pass
    return os.getenv(key, default)

def set_env_var(key, value):
    for path in ENV_PATHS:
        if not path.exists():
            continue
        try:
            lines = []
            key_found = False
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    key_found = True
                    break
                    
            if not key_found:
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                lines.append(f"{key}={value}\n")
                
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass
            
    os.environ[key] = str(value)
