"""Fatura yeni + iskonto + PDF print sayfasi dogrulama."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/pdf"); OUT.mkdir(parents=True, exist_ok=True)


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

    # 1. Yeni fatura formu - iskonto alani gorunuyor mu
    page.goto(f"{BASE}/portal/muhasebe/faturalar/yeni/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_invoice_new_empty.png"), full_page=True)
    print("01: yeni fatura form")

    # 2. Musteri sec - iskonto otomatik gelmeli
    # Once ilk musteriyi bulup sec
    options = page.eval_on_selector_all("#customerSelect option", "els => els.map(e => ({v:e.value, d:e.dataset.discount}))")
    print(f"  Musteri secenek sayisi: {len(options)}")
    # C-2026-002 %15 iskontolu musteriyi bul
    target = next((o for o in options if o.get("d") and float(o["d"]) >= 10), None)
    if target:
        page.select_option("#customerSelect", target["v"])
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "02_customer_selected_discount.png"), full_page=True)
        print(f"02: musteri secildi - iskonto otomatik gelmeli (disc={target['d']})")
        disc_value = page.eval_on_selector("#discountPct", "el => el.value")
        print(f"  Discount alani degeri: {disc_value}")

    # 3. Bir faturayi print sayfasi olarak ac (var olan fatura)
    page.goto(f"{BASE}/portal/muhasebe/faturalar/")
    page.wait_for_load_state("networkidle")
    # Ilk fatura link'ini bul
    first_link = page.query_selector("table a[href*='/muhasebe/faturalar/']")
    if first_link:
        href = first_link.get_attribute("href")
        # href /portal/muhasebe/faturalar/N/ formatinda
        pk = href.rstrip("/").split("/")[-1]
        print(f"  Fatura pk: {pk}")

        page.goto(f"{BASE}/accounting/invoices/{pk}/print/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "03_invoice_print.png"), full_page=True)
        print(f"03: fatura print sayfasi (pk={pk})")

        # Fatura detay - iskonto gorunuyor mu
        page.goto(f"{BASE}/portal/muhasebe/faturalar/{pk}/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(OUT / "04_invoice_detail_with_discount.png"), full_page=True)
        print(f"04: fatura detay")

    ctx.close()
    browser.close()
