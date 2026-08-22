"""Sprint 2 dogrulama: quality catalog + specs list + spec detail + sampling plans."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint2"); OUT.mkdir(parents=True, exist_ok=True)


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
    login(page, "qa.manager", "Demo123!")

    page.goto(f"{BASE}/portal/kalite/katalog/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_catalog.png"), full_page=True)
    print("01: catalog")

    page.goto(f"{BASE}/portal/kalite/sartname/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "02_specs_list.png"), full_page=True)
    print("02: specs list")

    from urllib.parse import urlparse
    link = page.query_selector("table a[href*='/kalite/sartname/']")
    if link:
        href = link.get_attribute("href")
        page.goto(f"{BASE}{href}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(OUT / "03_spec_detail.png"), full_page=True)
        print("03: spec detail")

    page.goto(f"{BASE}/portal/kalite/orneklem-plani/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "04_sampling_plans.png"), full_page=True)
    print("04: sampling plans")

    ctx.close()
    browser.close()
    print("Done.")
