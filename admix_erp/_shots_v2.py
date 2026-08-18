"""Yeni beyaz tema + fatura eki + cek odeme UI dogrulamasi."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/v2"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


PAGES = [
    # (kullanici, sifre, yol, tag)
    ("qa.manager",   "Demo123!",   "/portal/kalite/",          "01_qa_home_light"),
    ("qa.manager",   "Demo123!",   "/portal/registry/",        "02_registry_light"),
    ("qa.manager",   "Demo123!",   "/portal/cases/",           "03_cases_light"),
    ("acc.manager",  "Demo123!",   "/portal/muhasebe/",        "04_accounting_home_light"),
    ("acc.manager",  "Demo123!",   "/portal/muhasebe/faturalar/yeni/", "05_invoice_new_with_attachment"),
    ("acc.manager",  "Demo123!",   "/accounting/payments/new/",       "06_payment_new_default"),
    ("admin",        "Secret123!", "/notifications/",          "07_notifications_light"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    last_user = None
    ctx = None
    for user, pw, path, tag in PAGES:
        if user != last_user:
            if ctx: ctx.close()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            login(page, user, pw)
            last_user = user
        page.goto(f"{BASE}{path}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(OUT / f"{tag}.png"), full_page=True)
        print(f"  {tag:45s} -> {path}")

    # Ekstra: check odeme formunda method=CHECK sec, cek panelini goster
    page.goto(f"{BASE}/accounting/payments/new/")
    page.wait_for_load_state("networkidle")
    page.select_option('select[name="method"]', "CHECK")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "08_payment_new_check_selected.png"), full_page=True)
    print(f"  08_payment_new_check_selected             -> check panel visible")

    ctx.close()
    browser.close()
