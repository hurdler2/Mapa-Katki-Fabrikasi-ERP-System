"""Show sidebar filtering for 4 org roles."""
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


TESTS = [
    ("gm.director",     "Demo123!", "org_01_gm"),
    ("acc.manager",     "Demo123!", "org_02_muhasebe"),
    ("shift.supervisor","Demo123!", "org_03_supervizor"),
    ("lab.tech",        "Demo123!", "org_04_lab"),
    ("warehouse.chief", "Demo123!", "org_05_depo"),
    ("it.admin",        "Demo123!", "org_06_bt"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    for user, pw, name in TESTS:
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        login(page, user, pw)
        print(f"{user:22s} -> {page.url}")
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
        ctx.close()
    browser.close()
print("Done.")
