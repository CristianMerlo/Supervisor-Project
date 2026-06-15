import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Interceptar todas las peticiones para ver si hay API calls de login
        api_requests = []
        page.on("request", lambda request: api_requests.append(request.url) if "api" in request.url.lower() or "login" in request.url.lower() else None)
        
        print("[*] Navigating to https://appmostaza.linkuperp.com/")
        await page.goto("https://appmostaza.linkuperp.com/", wait_until="networkidle")
        
        print("[*] Checking form fields")
        try:
            # Imprimir campos input encontrados
            inputs = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('input')).map(i => ({id: i.id, name: i.name, type: i.type, placeholder: i.placeholder}));
            }''')
            print("Inputs en la página:", inputs)
            
            # Completar form
            # Buscamos inputs de email/usuario
            user_selector = 'input[type="text"], input[type="email"], input[name="usuario"], input[id="usuario"], input[name="username"]'
            await page.wait_for_selector(user_selector, timeout=5000)
            await page.fill(user_selector, "cmerlo@mostazaweb.com.ar")
            
            pass_selector = 'input[type="password"]'
            await page.fill(pass_selector, "cmer654321")
            
            # Click login
            btn_selector = 'button[type="submit"], input[type="submit"], button:has-text("Ingresar"), button:has-text("Login")'
            print("[*] Clicking login button")
            
            async with page.expect_navigation(wait_until="networkidle", timeout=15000):
                await page.click(btn_selector)
                
            print("[+] Login successful!")
            
            # Buscar botones o links relacionados a 'tickets' o 'descargar'
            html = await page.content()
            if "ticket" in html.lower():
                print("[+] Se encontró la palabra 'ticket' en el dashboard.")
            
        except Exception as e:
            print("[-] Error durante login:", e)
            
        print("[*] URLs de API/Login interceptadas:")
        for url in set(api_requests):
            print("   -", url)
            
        await browser.close()

asyncio.run(main())
