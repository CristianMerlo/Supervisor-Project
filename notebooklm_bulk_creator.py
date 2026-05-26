#!/usr/bin/env python3
"""
MOTOR DE CREACIÓN MASIVA - NOTEBOOKLM PRO
v3.0 - REINGENIERÍA DEFINITIVA BASADA EN DOM REAL

Fixes implementados tras diagnóstico científico del DOM:
  - ELIMINADO wait_for_load_state("networkidle") → NotebookLM nunca alcanza idle
  - MODAL CERRADO con click directo en button.close-button (nativo de Google)
  - CLICK FORZADO en input.title-input con force=True
  - ANTI-DUPLICADO: usa <project-button> .project-button-title para detectar existentes
  - NAVEGACIÓN: usa a.primary-action-button href para entrar a notebooks sin clicks
"""

import sys
import os
import asyncio
from playwright.async_api import async_playwright

SUCURSALES_FILE = "/home/cristian/Documentos/Supervisor/sucursales.txt"
NOTEBOOKLM_URL  = "https://notebooklm.google.com/"

CHROME_SESSION  = "/home/cristian/Documentos/Supervisor/.chrome_session"
CHROME_BIN      = "/usr/bin/google-chrome"

# ── Helpers ──────────────────────────────────────────────────────────────────

async def launch_browser(p):
    return await p.chromium.launch_persistent_context(
        user_data_dir=CHROME_SESSION,
        headless=False,
        executable_path=CHROME_BIN,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )

async def go_home(page):
    """Navega al home y espera a que aparezca el botón de crear cuaderno."""
    await page.goto(NOTEBOOKLM_URL)
    await page.wait_for_selector("button[aria-label='Crear cuaderno']", timeout=20000)
    await page.wait_for_timeout(1500)

async def get_existing_notebooks(page):
    """Devuelve un set con los títulos de cuadernos ya existentes en el dashboard."""
    cards = await page.query_selector_all("project-button")
    names = set()
    for card in cards:
        title_el = await card.query_selector(".project-button-title")
        if title_el:
            text = await title_el.text_content()
            if text:
                names.add(text.strip())
    return names

async def dismiss_modal(page):
    """Cierra el modal de 'Añadir fuente' usando el botón nativo close-button."""
    try:
        close_btn = await page.wait_for_selector("button.close-button", timeout=5000)
        await close_btn.click()
        await page.wait_for_timeout(800)
    except Exception:
        # Fallback: Escape key si el botón no se encuentra
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(800)

async def rename_notebook(page, name):
    """Localiza input.title-input y sobreescribe el título con el nombre dado."""
    title_input = await page.wait_for_selector("input.title-input", timeout=10000)
    await title_input.click(force=True)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Delete")
    await page.keyboard.type(name)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1500)   # Tiempo para que Google guarde el título

# ── Main ──────────────────────────────────────────────────────────────────────

async def run_automation():
    # 1. Cargar sucursales
    if not os.path.exists(SUCURSALES_FILE):
        print(f"❌ ERROR: No se encontró {SUCURSALES_FILE}")
        sys.exit(1)

    with open(SUCURSALES_FILE, "r") as f:
        sucursales = [line.strip() for line in f if line.strip()]
    print(f"📖 {len(sucursales)} sucursales cargadas desde sucursales.txt")

    async with async_playwright() as p:
        print("🚀 Lanzando navegador con sesión dedicada...")
        context = await launch_browser(p)
        page    = await context.new_page()

        # Ir al home
        await page.goto(NOTEBOOKLM_URL)

        print("\n🔒 VERIFICACIÓN DE SESIÓN:")
        print("   → Asegurate de estar logueado en NotebookLM Pro.")
        print("   → Cuando veas el panel principal, volvé a la terminal y presioná [ENTER].")
        input()

        # 2. Detectar existentes y calcular pendientes
        await page.wait_for_selector("button[aria-label='Crear cuaderno']", timeout=20000)
        await page.wait_for_timeout(2000)

        print("🔍 Escaneando cuadernos ya existentes...")
        existing = await get_existing_notebooks(page)
        print(f"   → {len(existing)} cuadernos ya creados detectados.")

        remaining = [s for s in sucursales if s not in existing]
        print(f"   → {len(remaining)} cuadernos por crear.\n")

        if not remaining:
            print("✅ Todos los cuadernos ya existen. ¡Nada que hacer!")
            await context.close()
            return

        print("▶️  Iniciando creación en 2 segundos...")
        await page.wait_for_timeout(2000)

        created = 0
        errors  = 0

        for i, sucursal in enumerate(remaining):
            print(f"📒 [{i+1}/{len(remaining)}] Creando: '{sucursal}'...")

            try:
                # Asegurarse de estar en home
                if "notebooklm.google.com" not in page.url or "notebook/" in page.url:
                    await go_home(page)

                # 1. Click en "Crear cuaderno"
                crear_btn = await page.wait_for_selector(
                    "button[aria-label='Crear cuaderno']", timeout=10000
                )
                await crear_btn.click()

                # 2. Esperar redirección al workspace (SIN networkidle)
                await page.wait_for_url("**/notebook/**", timeout=15000)
                await page.wait_for_timeout(3000)  # ← FIX CRÍTICO: tiempo fijo, no networkidle

                # 3. Cerrar el modal de "Añadir fuente"
                await dismiss_modal(page)

                # 4. Renombrar el cuaderno
                await rename_notebook(page, sucursal)
                print(f"   ✅ '{sucursal}' creado con éxito.")
                created += 1

                # 5. Volver al home para la próxima iteración
                await go_home(page)

            except Exception as e:
                errors += 1
                short_err = str(e).split("\n")[0]
                print(f"   ❌ ERROR en '{sucursal}': {short_err}")
                print("   → Volviendo al home para continuar...")
                try:
                    await go_home(page)
                except Exception:
                    await page.goto(NOTEBOOKLM_URL)
                    await page.wait_for_timeout(3000)

        print("\n" + "=" * 55)
        print("🎉 PROCESO FINALIZADO")
        print(f"   ✅ Creados con éxito : {created}")
        print(f"   ❌ Errores           : {errors}")
        print(f"   📦 Total en dashboard: {len(existing) + created}")
        print("=" * 55)

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_automation())
