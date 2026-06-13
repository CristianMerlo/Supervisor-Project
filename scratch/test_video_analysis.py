import os
import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Configurar path
sys.path.append(str(Path(__file__).parent.parent))

from userbot_supervisor import on_new_message

# Mock de evento de Telethon para video
class MockEvent:
    def __init__(self, sender_id, video=None, media=None):
        self.sender_id = sender_id
        self.text = ""
        self.is_group = False
        self.is_channel = False
        
        # Estructura de mensaje
        self.message = MagicMock()
        self.message.media = media
        self.message.voice = False
        self.message.photo = None
        self.message.video = video
        self.message.id = 777
        
        # Async Mocks
        self.respond = AsyncMock()

async def run_video_test():
    print("--- PRUEBA VIDEO: Envío de video de falla técnica ---")
    
    mock_video = MagicMock()
    mock_attr = MagicMock()
    mock_attr.file_name = "falla_cafetera.mp4"
    mock_media = MagicMock()
    mock_media.document.attributes = [mock_attr]
    mock_media.document.mime_type = "video/mp4"
    
    event_video = MockEvent(sender_id=215173956, video=mock_video, media=mock_media)
    
    # Mockear download_media
    async def mock_download_impl(*args, **kwargs):
        dest = kwargs.get("file", "/tmp/tg_videos_temp/falla_cafetera.mp4")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            f.write("DUMMY VIDEO DATA")
        return dest
        
    event_video.message.download_media = MagicMock()
    event_video.message.download_media.side_effect = mock_download_impl
    
    # Mockear requests.post para simular el endpoint /v1/analyze_video
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "diagnosis": "🧠 [Hermes] Se ha detectado un código de error E03 (presión baja de caldera) en la cafetera Cimbali. Por favor verifique el manómetro y la válvula de entrada."
    }
    
    # Mock para el mensaje de espera
    mock_msg_espera = AsyncMock()
    event_video.respond.return_value = mock_msg_espera
    
    patcher = patch('requests.post', return_value=mock_response)
    patcher.start()
    try:
        await on_new_message(event_video)
        # Esperar que termine el background task
        await asyncio.sleep(0.5)
    finally:
        patcher.stop()
    
    # Verificar que respond se llamó con el mensaje de espera y el diagnóstico
    print("Llamadas a respond:")
    for call in event_video.respond.call_args_list:
        print(f" - {call}")
        
    # Verificar que el diagnóstico fue enviado
    last_call_text = event_video.respond.call_args[0][0]
    print(f"Último mensaje enviado: '{last_call_text}'")
    assert "Hermes" in last_call_text
    assert "E03" in last_call_text
    
    # Verificar que el archivo temporal fue eliminado
    temp_file = Path("/tmp/tg_videos_temp/falla_cafetera.mp4")
    print(f"¿Existe archivo temporal? {temp_file.exists()}")
    assert not temp_file.exists()
    
    print("\n✅ PRUEBA DE ANÁLISIS DE VIDEO PASÓ EXITOSAMENTE")

if __name__ == "__main__":
    asyncio.run(run_video_test())
