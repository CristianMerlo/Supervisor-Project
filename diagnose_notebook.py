#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

TEST_NOTEBOOK_URL = "https://notebooklm.google.com/notebook/4589abc5-2706-4e08-8eff-787670964c1d"

async def diagnose_workspace():
    chrome_user_data = "/home/cristian/Documentos/Supervisor/.chrome_session"
    
    async with async_playwright() as p:
        print("🔍 Navigating directly to workspace (no networkidle wait)...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_user_data,
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )

        page = await context.new_page()
        await page.goto(TEST_NOTEBOOK_URL)
        await page.wait_for_timeout(5000) # Wait exactly 5 seconds for UI to load
        
        # 1. Print all inputs
        print("\n--- ALL INPUTS ON WORKSPACE PAGE ---")
        inputs = await page.query_selector_all("input")
        for idx, el in enumerate(inputs):
            html = await el.evaluate("el => el.outerHTML")
            val = await el.evaluate("el => el.value")
            print(f"Input [{idx}]: Value='{val}' | HTML:\n{html}")
            
        # 2. Print all buttons (to find close button for modal)
        print("\n--- ALL BUTTONS ON WORKSPACE PAGE ---")
        buttons = await page.query_selector_all("button")
        for idx, el in enumerate(buttons):
            text = await el.text_content()
            html = await el.evaluate("el => el.outerHTML")
            if text and len(text.strip()) > 0:
                print(f"Button [{idx}]: Text='{text.strip()}' | HTML:\n{html[:300]}")
            else:
                aria = await el.evaluate("el => el.getAttribute('aria-label')")
                print(f"Button [{idx}]: Aria='{aria}' | HTML:\n{html[:300]}")

        # 3. Print the outerHTML of the top header area
        print("\n--- TOP HEADER REGION ---")
        header = await page.query_selector("header, div.header, div.top-bar")
        if header:
            html = await header.evaluate("el => el.outerHTML")
            print(f"Header HTML:\n{html[:2000]}")
        else:
            # Fallback: grab top-left region containing the text
            top_left = await page.query_selector("div:has-text('PRUEBA')")
            if top_left:
                html = await top_left.evaluate("el => el.outerHTML")
                print(f"Top-Left HTML:\n{html[:2000]}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(diagnose_workspace())
