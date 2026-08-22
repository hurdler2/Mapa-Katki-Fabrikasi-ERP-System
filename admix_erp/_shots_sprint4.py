"""Sprint 4 dogrulama: stok detay (alert), reporting hub."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint4"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    login(page, "warehouse.chief", "Demo123!")

    # 1. HD - alert seviyesi
    page.goto(f"{BASE}/portal/stok/hammadde/4/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_hammadde_hd_alert.png"), full_page=True)
    print("01: HD hammadde ALERT")

    # 2. W - ok seviyesi
    page.goto(f"{BASE}/portal/stok/hammadde/1/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "02_hammadde_w_ok.png"), full_page=True)
    print("02: W hammadde OK")

    # Login as acc for reporting
    login(page, "acc.manager", "Demo123!")
    page.goto(f"{BASE}/portal/rapor/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "03_reporting_hub.png"), full_page=True)
    print("03: reporting hub")

    ctx.close()
    browser.close()
    print("Done.")
