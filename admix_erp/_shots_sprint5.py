"""Sprint 5 dogrulama: musteri avans listesi + tahsis formu."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint5"); OUT.mkdir(parents=True, exist_ok=True)


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
    login(page, "acc.manager", "Demo123!")

    page.goto(f"{BASE}/portal/muhasebe/avans/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_advances_list.png"), full_page=True)
    print("01: advances list")

    # Tahsis formu ile ilk avansi ac
    link = page.query_selector("a.btn-primary[href*='/tahsis/']")
    if link:
        href = link.get_attribute("href")
        page.goto(f"{BASE}{href}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(OUT / "02_advance_allocate.png"), full_page=True)
        print("02: advance allocate form")
    else:
        print("Tahsis butonu bulunamadi")

    ctx.close()
    browser.close()
    print("Done.")
