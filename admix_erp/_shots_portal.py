"""Test portal for 3 roles: muhasebeci, üretim planlayıcı, depo."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots"); OUT.mkdir(exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # 1) Muhasebeci
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    login(page, "ahmet.kaya", "Demo123!")
    print(f"Muhasebeci landing: {page.url}")
    page.screenshot(path=str(OUT / "portal_01_muhasebeci_home.png"), full_page=True)

    page.goto(f"{BASE}/portal/muhasebe/faturalar/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "portal_02_muhasebeci_invoices.png"), full_page=True)

    page.goto(f"{BASE}/portal/muhasebe/faturalar/yeni/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "portal_03_muhasebeci_new_invoice.png"), full_page=True)
    ctx.close()

    # 2) Üretim planlayıcı
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    login(page, "okan.yilmaz", "Demo123!")
    print(f"Uretim landing: {page.url}")
    page.screenshot(path=str(OUT / "portal_04_uretim_home.png"), full_page=True)
    ctx.close()

    # 3) Depo
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    login(page, "fatma.sahin", "Demo123!")
    print(f"Depo landing: {page.url}")
    page.screenshot(path=str(OUT / "portal_05_depo_home.png"), full_page=True)

    page.goto(f"{BASE}/portal/stok/mal-kabul/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "portal_06_depo_receipt.png"), full_page=True)
    ctx.close()

    # 4) Yönetim
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    login(page, "sibel.can", "Demo123!")
    print(f"Yonetim landing: {page.url}")
    page.screenshot(path=str(OUT / "portal_07_yonetim_home.png"), full_page=True)
    ctx.close()

    browser.close()
print("Done.")
