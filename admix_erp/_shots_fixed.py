"""Duzeltilen 7 template icin sidebar dogrulama."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/fixed"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


PAGES = [
    ("/notifications/",             "01_notifications"),
    ("/accounting/balance/",         "02_trial_balance"),
    ("/analytics/bi/",               "03_bi_dashboard"),
    ("/analytics/iso-audit/",        "04_iso_audit"),
    ("/reporting/dashboard/",        "05_production_report"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    login(page, "admin", "Secret123!")

    for path, tag in PAGES:
        page.goto(f"{BASE}{path}")
        page.wait_for_load_state("networkidle")
        has_aside = page.eval_on_selector("body", "b => !!b.querySelector('aside')")
        out = OUT / f"{tag}.png"
        page.screenshot(path=str(out), full_page=True)
        print(f"{path:35s} aside={has_aside}  -> {tag}.png")

    ctx.close()
    browser.close()
