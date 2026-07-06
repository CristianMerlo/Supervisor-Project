import asyncio
import os
import shutil
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv("/home/cristian/PROYECTOS/Supervisor-Project/.env")
user = os.getenv("MOSTAZA_USER", "cmerlo@mostazaweb.com.ar")
password = os.getenv("MOSTAZA_PASS", "Mante2026")

DOWNLOAD_DIR = "/home/cristian/Documentos/Supervisor/base_tickets"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
TARGET_FILE = os.path.join(DOWNLOAD_DIR, "Historial_Tickets.xlsx")

async def run():
    async with async_playwright() as p:
        print("[*] Conectando a Chrome (CDP)...")
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print("[-] Error conectando a CDP:", e)
            return

        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        try:
            print("[*] Navegando a login...")
            await page.goto("https://opgroup.linkuperp.com/login", wait_until="networkidle")
            
            # Login if not logged in
            if await page.locator("input[name='email']").count() > 0:
                print("[*] Ingresando credenciales...")
                await page.fill("input[name='email']", user)
                await page.fill("input[name='password']", password)
                await page.click("button[type='submit']")
                await page.wait_for_timeout(3000)
            
            print("[*] Navegando a la sección de métricas de franquicias...")
            await page.goto("https://opgroup.linkuperp.com/admin/ticket/2/metrics")
            await page.wait_for_timeout(3000)
            
            # Click export and wait for download
            print("[*] Descargando Excel histórico...")
            async with page.expect_download(timeout=60000) as download_info:
                await page.click('#export-excel')
            
            download = await download_info.value
            
            if os.path.exists(TARGET_FILE):
                os.remove(TARGET_FILE)
                
            await download.save_as(TARGET_FILE)
            print(f"[+] Archivo descargado exitosamente en: {TARGET_FILE}")
            
        except Exception as e:
            print(f"[-] Error durante la navegación/descarga: {e}")
        finally:
            await page.close()
            await context.close()
            # NOT closing browser as it's the shared CDP instance for WhatsApp!

if __name__ == "__main__":
    asyncio.run(run())

