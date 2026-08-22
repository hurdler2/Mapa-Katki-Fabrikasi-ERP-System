"""Sprint 6 dogrulama: aging + valorisation + yields + BL-invoice + ajustement + statement."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint6"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
    page = ctx.new_page()

    login(page, "acc.manager", "Demo123!")

    page.goto(f"{BASE}/portal/rapor/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_hub_updated.png"), full_page=True)
    print("01: rapor hub yeni tile'lar")

    page.goto(f"{BASE}/portal/rapor/echeancier-clients/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "02_aging.png"), full_page=True)
    print("02: aging")

    page.goto(f"{BASE}/portal/rapor/valorisation-stocks/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "03_valuation.png"), full_page=True)
    print("03: valuation")

    page.goto(f"{BASE}/portal/rapor/rendements-production/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "04_yields.png"), full_page=True)
    print("04: yields")

    page.goto(f"{BASE}/portal/rapor/bl-fatura/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "05_bl_invoice.png"), full_page=True)
    print("05: bl-invoice")

    # Customer statement — ilk musteri
    page.goto(f"{BASE}/portal/muhasebe/cari/1/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "06_customer_statement.png"), full_page=True)
    print("06: cari hesap")

    # Ajustement formu
    login(page, "warehouse.chief", "Demo123!")
    page.goto(f"{BASE}/portal/stok/ajustement/yeni/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "07_ajustement.png"), full_page=True)
    print("07: ajustement form")

    ctx.close()
    browser.close()
    print("Done.")
