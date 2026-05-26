#!/usr/bin/env python3
"""
MOTOR DE LIMPIEZA - NOTEBOOKLM PRO
v2.0 - REINGENIERÍA DEFINITIVA BASADA EN DOM REAL

Fixes implementados tras diagnóstico científico del DOM:
  - Usa <project-button> (etiqueta Angular nativa) para detectar tarjetas
  - Lee títulos desde span.project-button-title (selector exacto de Google)
  - Usa el único <button> dentro de project-button para el menú de 3 puntos
  - Playwright regex bilingüe text=/Eliminar|Delete/i para compatibilidad ES/EN
"""

import sys
import os
import asyncio
from playwright.async_api import async_playwright

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
CHROME_SESSION  = "/home/cristian/Documentos/Supervisor/.chrome_session"
CHROME_BIN      = "/usr/bin/google-chrome"

async def run_cleanup():
    if not os.path.exists(CHROME_SESSION):
        print("❌ ERROR: No se encontró la sesión activa.")
        print("   Por favor, ejecutá notebooklm_bulk_creator.py primero para crear la sesión.")
        sys.exit(1)

    async with async_playwright() as p:
        print("🚀 Lanzando navegador para la limpieza...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=CHROME_SESSION,
            headless=False,
            executable_path=CHROME_BIN,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = await context.new_page()
        await page.goto(NOTEBOOKLM_URL)

        print("\n🔒 VERIFICACIÓN:")
        print("   → Cuando veas el panel de NotebookLM con los cuadernos 'Untitled notebook',")
        print("     volvé a la terminal y presioná [ENTER] para iniciar la limpieza automática.")
        input()

        print("🧹 Iniciando eliminación de cuadernos sin título...")
        total_deleted = 0

        while True:
            # Esperar a que el panel cargue
            await page.wait_for_selector("project-button", timeout=20000)
            await page.wait_for_timeout(2000)

            # Buscar cards sin título ("Untitled notebook" o "Cuaderno sin título")
            cards = await page.query_selector_all("project-button")
            target_card = None

            for card in cards:
                title_el = await card.query_selector(".project-button-title")
                if not title_el:
                    continue
                title_text = await title_el.text_content()
                if not title_text:
                    continue
                title_clean = title_text.strip()
                if title_clean in ("Untitled notebook", "Cuaderno sin título"):
                    target_card = card
                    break

            if not target_card:
                print(f"\n✅ ¡Limpieza completada! Se eliminaron {total_deleted} cuadernos sin título.")
                break

            try:
                # Hover sobre la tarjeta para que aparezca el botón de menú
                await target_card.hover()
                await page.wait_for_timeout(500)

                # El botón de 3 puntos es el ÚNICO <button> dentro de project-button
                menu_btn = await target_card.query_selector("button")
                if not menu_btn:
                    print("   ⚠️ No se encontró el botón de menú en esta tarjeta. Saltando...")
                    break

                await menu_btn.click()
                await page.wait_for_timeout(1000)

                # Click en "Eliminar" (ES) o "Delete" (EN) usando regex bilingüe
                delete_option = await page.wait_for_selector(
                    "text=/^Eliminar$|^Delete$/i", timeout=5000
                )
                await delete_option.click()
                await page.wait_for_timeout(800)

                # Confirmar en el modal de diálogo
                confirm_btn = await page.wait_for_selector(
                    "button:has-text('Eliminar'), button:has-text('Delete')",
                    timeout=5000
                )
                await confirm_btn.click()
                await page.wait_for_timeout(2000)

                total_deleted += 1
                print(f"   🗑️  [{total_deleted}] 'Untitled notebook' eliminado.")

            except Exception as e:
                short_err = str(e).split("\n")[0]
                print(f"   ❌ ERROR al eliminar tarjeta: {short_err}")
                # Refrescar la página y reintentar
                await page.reload()
                await page.wait_for_timeout(3000)

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_cleanup())
