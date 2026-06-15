import os
import glob
import re
from datetime import datetime

class ObsidianVault:
    def __init__(self, base_path="/home/cristian/PROYECTOS/Supervisor-Project/brain"):
        self.base_path = base_path
        self.dir_bitacoras = os.path.join(base_path, "00_Bitacoras")
        self.dir_manuales = os.path.join(base_path, "01_Manuales_Tecnicos")
        self.dir_equipos = os.path.join(base_path, "02_Equipos_Local")
        self.dir_wiki = os.path.join(base_path, "03_Wiki_Hermes")

    def buscar_manual(self, palabra_clave: str):
        """
        Busca palabras clave en los títulos y el contenido de los manuales técnicos.
        """
        resultados = []
        archivos_md = glob.glob(os.path.join(self.dir_manuales, "*.md"))
        
        # Extraer keywords (palabras > 3 letras)
        palabras = [p.lower() for p in palabra_clave.split() if len(p) > 3]
        if not palabras:
            palabras = [palabra_clave.lower()]
            
        for archivo in archivos_md:
            nombre_nota = os.path.splitext(os.path.basename(archivo))[0]
            
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
            contenido_lower = contenido.lower()
            nombre_lower = nombre_nota.lower()
            
            # Ver cuántas palabras clave están presentes
            matches = sum(1 for p in palabras if p in contenido_lower or p in nombre_lower)
            
            # Consideramos coincidencia si al menos 1 palabra pesada está (o la mayoría si son varias)
            umbral = max(1, len(palabras) // 2)
            if matches >= umbral:
                contexto = "Coincidencia en el documento."
                # Proveer un bloque inmenso de contexto para la IA (hasta 15000 caracteres)
                for p in palabras:
                    if p in contenido_lower:
                        idx = contenido_lower.find(p)
                        inicio = max(0, idx - 3000)
                        fin = min(len(contenido), idx + 12000)
                        contexto = "..." + contenido[inicio:fin] + "..."
                        break
                        
                resultados.append({
                    "nota": nombre_nota,
                    "contexto": contexto,
                    "link": f"[[{nombre_nota}]]"
                })
                
        return resultados

    def crear_nota_wiki(self, titulo: str, contenido: str, enlaces: list = None):
        """
        Crea una nueva nota en la Wiki de Hermes.
        Los enlaces deben ser una lista de nombres de notas (ej: ['Manual_Cimbali']).
        """
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        texto_enlaces = ""
        if enlaces:
            texto_enlaces = "\n**Relacionado:** " + ", ".join([f"[[{link}]]" for link in enlaces]) + "\n"
            
        contenido_completo = f"---\nfecha: {fecha_str}\ntags: [falla, resolucion]\n---\n\n# {titulo}\n\n{contenido}\n{texto_enlaces}"
        
        # Sanitizar título para nombre de archivo
        nombre_archivo = re.sub(r'[^\w\s-]', '', titulo).strip().replace(' ', '_') + ".md"
        ruta_archivo = os.path.join(self.dir_wiki, nombre_archivo)
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido_completo)
            
        return f"[[{nombre_archivo.replace('.md', '')}]]"

if __name__ == "__main__":
    # Prueba rápida
    vault = ObsidianVault()
    print("Bóveda inicializada:", vault.base_path)
