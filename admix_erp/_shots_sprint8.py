"""Sprint 8 dogrulama: multi-line adj + expense list/new/detail."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint8"); OUT.mkdir(parents=True, exist_ok=True)


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

    login(page, "acc.manager", "Demo123!")

    page.goto(f"{BASE}/portal/muhasebe/gider/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_expense_list.png"), full_page=True)
    print("01: expense list")

    link = page.query_selector("table a[href*='/muhasebe/gider/']")
    if link:
        href = link.get_attribute("href")
        page.goto(f"{BASE}{href}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(OUT / "02_expense_detail.png"), full_page=True)
        print("02: expense detail")

    page.goto(f"{BASE}/portal/muhasebe/gider/yeni/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "03_expense_new.png"), full_page=True)
    print("03: expense new")

    login(page, "warehouse.chief", "Demo123!")
    page.goto(f"{BASE}/portal/stok/ajustement/multi/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "04_multi_line_adj.png"), full_page=True)
    print("04: multi-line adjustment")

    ctx.close()
    browser.close()
    print("Done.")
