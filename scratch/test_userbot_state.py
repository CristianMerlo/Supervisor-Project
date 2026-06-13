import os
import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Configurar path
sys.path.append(str(Path(__file__).parent.parent))

from userbot_supervisor import on_new_message, STATE_FILE

# Limpiar estado anterior
if os.path.exists(STATE_FILE):
    os.remove(STATE_FILE)

# Mock de evento de Telethon
class MockEvent:
    def __init__(self, sender_id, text="", media=None, is_group=False, voice=False, photo=None):
        self.sender_id = sender_id
        self.text = text
        self.is_group = is_group
        self.is_channel = False
        
        # Estructura de mensaje
        self.message = MagicMock()
        self.message.media = media
        self.message.voice = voice
        self.message.photo = photo
        
        # Async Mocks
        self.respond = AsyncMock()
        self.message.download_media = MagicMock()
        self.message.download_media.side_effect = AsyncMock()

# Ejecución asíncrona de pruebas
async def run_async_tests():
    # 1. Simular envío de documento 1
    mock_attr1 = MagicMock()
    mock_attr1.file_name = "Manual1.pdf"
    mock_media1 = MagicMock()
    mock_media1.document.attributes = [mock_attr1]
    
    event_doc1 = MockEvent(sender_id=215173956, media=mock_media1, voice=False)
    
    async def mock_download_impl1(*args, **kwargs):
        dest = kwargs.get("file", "/tmp/tg_manuals_temp/Manual1.pdf")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            f.write("DUMMY PDF MANUAL 1")
        return dest
        
    event_doc1.message.download_media.side_effect = mock_download_impl1

    print("--- PRUEBA BATCH 1: Envío del primer manual ---")
    await on_new_message(event_doc1)
    
    # 2. Simular envío de documento 2 (debe acumularse en el lote)
    mock_attr2 = MagicMock()
    mock_attr2.file_name = "Manual2.pdf"
    mock_media2 = MagicMock()
    mock_media2.document.attributes = [mock_attr2]
    
    event_doc2 = MockEvent(sender_id=215173956, media=mock_media2, voice=False)
    
    async def mock_download_impl2(*args, **kwargs):
        dest = kwargs.get("file", "/tmp/tg_manuals_temp/Manual2.pdf")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            f.write("DUMMY PDF MANUAL 2")
        return dest
        
    event_doc2.message.download_media.side_effect = mock_download_impl2

    print("\n--- PRUEBA BATCH 2: Envío de segundo manual (Acumulación) ---")
    await on_new_message(event_doc2)
    
    # Verificar que el estado se guardó con ambos archivos
    with open(STATE_FILE, "r") as f:
        estado = json.load(f)
        print(f"Estado en userbot: {estado}")
        
    assert estado["status"] == "waiting_manual_confirm"
    assert len(estado["files"]) == 2
    assert estado["files"][0]["file_name"] == "Manual1.pdf"
    assert estado["files"][1]["file_name"] == "Manual2.pdf"
    
    # 3. Simular confirmación
    print("\n--- PRUEBA BATCH 3: Confirmación positiva ---")
    event_confirm = MockEvent(sender_id=215173956, text="Sí")
    await on_new_message(event_confirm)
    
    with open(STATE_FILE, "r") as f:
        estado = json.load(f)
        print(f"Estado en userbot después de confirmar: {estado}")
        
    assert estado["status"] == "waiting_equipment_name"

    # 4. Simular nombre de máquina
    print("\n--- PRUEBA BATCH 4: Clasificación final del lote ---")
    event_equipo = MockEvent(sender_id=215173956, text="Molino Compak")
    await on_new_message(event_equipo)
    
    # El archivo de estado debe haberse limpiado
    assert not os.path.exists(STATE_FILE)
    
    # Los archivos deben estar en brain/manuales
    final_path1 = Path("/home/cristian/Documentos/Supervisor/brain/manuales/Molino Compak - Manual1.pdf")
    final_path2 = Path("/home/cristian/Documentos/Supervisor/brain/manuales/Molino Compak - Manual2.pdf")
    print(f"¿Existe manual 1 clasificado? {final_path1.exists()}")
    print(f"¿Existe manual 2 clasificado? {final_path2.exists()}")
    assert final_path1.exists()
    assert final_path2.exists()
    
    # Limpiar
    if final_path1.exists():
        final_path1.unlink()
    if final_path2.exists():
        final_path2.unlink()
        
    print("\n✅ TODAS LAS PRUEBAS DE BATCH EN EL USERBOT PASARON EXITOSAMENTE")

async def run_photo_tests():
    print("\n--- PRUEBA FOTO: Envío de una foto comprimida ---")
    # Limpiar estado anterior
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        
    mock_photo = MagicMock()
    # Para Telethon, el photo attribute no debe ser None
    event_photo = MockEvent(sender_id=215173956, voice=False, photo=mock_photo)
    event_photo.message.id = 999
    
    async def mock_download_impl(*args, **kwargs):
        dest = kwargs.get("file", "/tmp/tg_manuals_temp/foto_999.jpg")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            f.write("FAKE IMAGE BYTES")
        return dest
        
    event_photo.message.download_media.side_effect = mock_download_impl
    
    await on_new_message(event_photo)
    
    # Verificar que el estado se guardó con el archivo de foto
    with open(STATE_FILE, "r") as f:
        estado = json.load(f)
        print(f"Estado en userbot para foto: {estado}")
        
    assert estado["status"] == "waiting_manual_confirm"
    assert len(estado["files"]) == 1
    assert estado["files"][0]["file_name"] == "foto_999.jpg"
    
    # Simular confirmación
    print("--- Confirmando foto ---")
    event_confirm = MockEvent(sender_id=215173956, text="Sí")
    await on_new_message(event_confirm)
    
    # Simular nombre de máquina
    print("--- Clasificando foto ---")
    event_equipo = MockEvent(sender_id=215173956, text="Cafetera Iberital")
    
    # Mockear requests.post para simular el endpoint de transcripción
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"markdown": "# Transcripción de la foto de la Cafetera Iberital"}
    
    with patch('requests.post', return_value=mock_response):
        await on_new_message(event_equipo)
        
    # Esperar un momento corto para que el hilo de transcripción termine
    await asyncio.sleep(0.5)
    
    # Verificar que el archivo de imagen y el .md existen en brain/manuales/
    img_path = Path("/home/cristian/Documentos/Supervisor/brain/manuales/Cafetera Iberital - foto_999.jpg")
    md_path = Path("/home/cristian/Documentos/Supervisor/brain/manuales/Cafetera Iberital - foto_999.md")
    
    print(f"¿Existe imagen final? {img_path.exists()}")
    print(f"¿Existe markdown final? {md_path.exists()}")
    
    assert img_path.exists()
    assert md_path.exists()
    
    # Leer contenido del markdown
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"Contenido del markdown generado: {content}")
    assert "Transcripción" in content
    
    # Limpiar
    if img_path.exists():
        img_path.unlink()
    if md_path.exists():
        md_path.unlink()
        
    print("\n✅ PRUEBA DE FOTOS PASÓ EXITOSAMENTE")

if __name__ == "__main__":
    async def run_all():
        await run_async_tests()
        await run_photo_tests()
    asyncio.run(run_all())
