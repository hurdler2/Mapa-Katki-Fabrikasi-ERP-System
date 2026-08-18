"""Grafikli muhasebe panosu + banka havale paneli dogrulama."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/v3"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    login(page, "acc.manager", "Demo123!")

    # Grafikli muhasebe panosu
    page.goto(f"{BASE}/portal/muhasebe/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)  # chart animation
    page.screenshot(path=str(OUT / "01_accounting_dashboard_charts.png"), full_page=True)
    print("01: muhasebe pano (grafikli)")

    # Banka havale paneli
    page.goto(f"{BASE}/accounting/payments/new/")
    page.wait_for_load_state("networkidle")
    page.select_option('select[name="method"]', "BANK_TRANSFER")
    page.wait_for_timeout(200)
    page.screenshot(path=str(OUT / "02_payment_bank_transfer.png"), full_page=True)
    print("02: banka havale paneli")

    # Cek paneli (karsilastirma)
    page.select_option('select[name="method"]', "CHECK")
    page.wait_for_timeout(200)
    page.screenshot(path=str(OUT / "03_payment_check.png"), full_page=True)
    print("03: cek paneli")

    ctx.close()
    browser.close()
