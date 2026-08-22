"""Sprint 7 dogrulama: zenginlesmis hareket + yeni formulation."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint7"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()

    login(page, "warehouse.chief", "Demo123!")
    page.goto(f"{BASE}/portal/stok/hammadde/1/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_rm_detail_enriched.png"), full_page=True)
    print("01: RM detay + accès rapides + zengin hareket tablosu")

    login(page, "op.manager", "Demo123!")
    page.goto(f"{BASE}/portal/recete/yeni/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "02_formulation_new.png"), full_page=True)
    print("02: Nouvelle formulation formu")

    ctx.close()
    browser.close()
    print("Done.")
