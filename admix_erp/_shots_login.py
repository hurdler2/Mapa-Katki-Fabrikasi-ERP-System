"""New login page + logged-in home with user + logout in navbar."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots"); OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    # 1) Login sayfası
    page.goto(f"{BASE}/login/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "new_01_login.png"), full_page=True)
    print(f"login page: {page.title()!r}")

    # 2) Login form failed
    page.fill('input[name="username"]', "muhasebeci")
    page.fill('input[name="password"]', "yanlisparola")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "new_02_login_error.png"), full_page=True)
    print(f"login error: {page.title()!r}")

    # 3) Login form success
    page.fill('input[name="username"]', "muhasebeci")
    page.fill('input[name="password"]', "Test123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    print(f"after login URL: {page.url}")
    page.screenshot(path=str(OUT / "new_03_home_muhasebeci.png"), full_page=True)

    # 4) Ahmet (muhasebe müdürü) — navbar'da ismi + çıkış görünsün
    page.goto(f"{BASE}/reporting/dashboard/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "new_04_reporting_with_navbar.png"), full_page=True)

    browser.close()
print("Done.")
