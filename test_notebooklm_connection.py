import asyncio
from playwright.async_api import async_playwright

CHROME_SESSION = "/home/cristian/Documentos/Supervisor/.chrome_session"
CHROME_BIN = "/usr/bin/google-chrome"
NOTEBOOKLM_URL = "https://notebooklm.google.com/"

async def test_connection():
    print("Iniciando prueba de conexión con la cuenta del Supervisor...")
    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=CHROME_SESSION,
                headless=True,  # Modo invisible para que no moleste en pantalla
                executable_path=CHROME_BIN,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = await context.new_page()
            print(f"Navegando a {NOTEBOOKLM_URL}...")
            await page.goto(NOTEBOOKLM_URL, timeout=30000)
            
            # Esperamos a ver si carga el botón de crear cuaderno, lo que confirmaría que estamos logueados
            try:
                await page.wait_for_selector("button[aria-label='Crear cuaderno']", timeout=15000)
                print("✅ ¡Conexión exitosa! La sesión del Supervisor está activa y NotebookLM cargó correctamente.")
            except Exception:
                print("❌ No se encontró el botón de 'Crear cuaderno'. Es posible que la sesión haya expirado o necesite login manual.")
            
            await context.close()
        except Exception as e:
            print(f"Error al intentar abrir el navegador: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
