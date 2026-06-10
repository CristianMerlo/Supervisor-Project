import os
import glob
import subprocess
import sys

def main():
    # Rutas objetivo para limpiar
    brain_dir = "/home/cristian/.gemini/antigravity/brain/"
    system_screenshots_dir = "/home/cristian/Imágenes/Capturas de pantalla/"
    
    # Patrones de búsqueda
    patrones = [
        os.path.join(brain_dir, "**/media__*.png"),
        os.path.join(brain_dir, "**/.system_generated/click_feedback/*.png"),
        os.path.join(system_screenshots_dir, "**/*.png")
    ]
    
    deleted_count = 0
    deleted_bytes = 0
    
    for patron in patrones:
        for filepath in glob.glob(patron, recursive=True):
            try:
                # Obtener el tamaño del archivo antes de moverlo
                size = os.path.getsize(filepath)
                
                # Usar gio trash para mover el archivo a la papelera del sistema
                result = subprocess.run(
                    ["gio", "trash", filepath],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0:
                    deleted_count += 1
                    deleted_bytes += size
                else:
                    print(f"Error al mover a papelera {filepath}: {result.stderr.strip()}", file=sys.stderr)
            except Exception as e:
                print(f"Excepción con {filepath}: {e}", file=sys.stderr)
                
    # Convertir bytes a MB
    deleted_mb = deleted_bytes / (1024 * 1024)
    
    mensaje = (
        f"🪿 *[Goose] Limpieza semanal de capturas completada.*\n"
        f"Se enviaron {deleted_count} capturas de pantalla a la papelera del sistema.\n"
        f"Espacio total enviado a papelera: {deleted_mb:.2f} MB.\n"
        f"Nota: Los archivos permanecerán en la papelera por un mes antes de ser borrados definitivamente."
    )
    
    # Imprimir resultado en consola
    print(mensaje)
    
    # Enviar notificación de Telegram
    try:
        subprocess.run(
            ["/home/cristian/Documentos/Supervisor/notify_telegram.sh", mensaje],
            check=True
        )
        print("Notificación de Telegram enviada.")
    except Exception as e:
        print(f"Error al notificar por Telegram: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
