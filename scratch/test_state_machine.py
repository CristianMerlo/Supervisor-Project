import os
import sys
import shutil
import json
from pathlib import Path
from unittest.mock import patch

# Agregar el directorio al path
sys.path.append(str(Path(__file__).parent.parent / "telegram_bridge"))

from app import app, STATE_FILE

# Crear cliente de prueba de Flask
client = app.test_client()

# Limpiar cualquier estado anterior
if os.path.exists(STATE_FILE):
    os.remove(STATE_FILE)

# Mockear las funciones que hacen peticiones de red
@patch('app.descargar_documento_telegram')
@patch('app.responder_a_telegram')
def run_tests(mock_responder, mock_descargar):
    # Mockear descarga exitosa (crear archivo ficticio)
    def mock_descarga_impl(file_id, dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "w") as f:
            f.write("DUMMY PDF CONTENT")
        return True
    
    mock_descargar.side_effect = mock_descarga_impl
    
    # Mocks de respuestas de Telegram capturadas
    captured_messages = []
    def mock_responder_impl(chat_id, text):
        print(f"[TG-SEND] to {chat_id}: {text}")
        captured_messages.append(text)
        
    mock_responder.side_effect = mock_responder_impl

    print("\n--- PRUEBA 1: Envío de documento no estándar (Manual) ---")
    payload_doc = {
        "message": {
            "chat": {"id": 12345},
            "document": {
                "file_name": "Manual_Iberital_LExpression.pdf",
                "file_id": "file123"
            }
        }
    }
    
    # Forzar chat_id en ALLOWED_CHAT_IDS para la prueba
    with patch('app.ALLOWED_CHAT_IDS', ['12345']):
        res = client.post('/webhook', json=payload_doc)
        print(f"Status Code: {res.status_code}")
        print(f"Response JSON: {res.get_json()}")
        
        # Verificar estado
        with open(STATE_FILE, "r") as f:
            estado = json.load(f)
            print(f"Estado guardado: {estado}")
            
        assert estado["status"] == "waiting_manual_confirm"
        assert len(estado["files"]) == 1
        assert estado["files"][0]["file_name"] == "Manual_Iberital_LExpression.pdf"
        assert os.path.exists(estado["files"][0]["temp_path"])
        
        print("\n--- PRUEBA 2: Confirmación positiva ---")
        payload_confirm = {
            "message": {
                "chat": {"id": 12345},
                "text": "Sí, es un manual"
            }
        }
        res = client.post('/webhook', json=payload_confirm)
        print(f"Status Code: {res.status_code}")
        print(f"Response JSON: {res.get_json()}")
        
        # Verificar nuevo estado
        with open(STATE_FILE, "r") as f:
            estado = json.load(f)
            print(f"Estado guardado: {estado}")
        assert estado["status"] == "waiting_equipment_name"
        
        print("\n--- PRUEBA 3: Nombre del equipo ---")
        payload_equipo = {
            "message": {
                "chat": {"id": 12345},
                "text": "Cafetera Iberital"
            }
        }
        res = client.post('/webhook', json=payload_equipo)
        print(f"Status Code: {res.status_code}")
        print(f"Response JSON: {res.get_json()}")
        
        # El estado debe haberse limpiado
        assert not os.path.exists(STATE_FILE)
        
        # El archivo final debe existir en brain/manuales
        final_path = Path("/home/cristian/Documentos/Supervisor/brain/manuales/Cafetera Iberital - Manual_Iberital_LExpression.pdf")
        print(f"¿Existe archivo final? {final_path.exists()}")
        assert final_path.exists()
        
        # Limpieza
        if final_path.exists():
            final_path.unlink()
        
        print("\n✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")

if __name__ == "__main__":
    run_tests()
