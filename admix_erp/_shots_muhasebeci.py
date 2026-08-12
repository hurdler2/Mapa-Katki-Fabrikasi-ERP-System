"""Login as muhasebeci → screenshot admin index (only allowed apps visible)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots"); OUT.mkdir(exist_ok=True)

PAGES = [
    ("mh_01_home",       "/",                                       ),
    ("mh_02_admin",      "/admin/",                                 ),
    ("mh_03_invoice",    "/admin/accounting/invoice/",              ),
    ("mh_04_journal",    "/admin/accounting/journalentry/",         ),
    ("mh_05_accounts",   "/admin/accounting/account/",              ),
    ("mh_06_tva",        "/admin/accounting/tvadeclaration/",       ),
    ("mh_07_fixedasset", "/admin/accounting/fixedasset/",           ),
    ("mh_08_balance",    "/accounting/balance/",                    ),
    ("mh_09_purchase",   "/admin/purchasing/purchaseorder/",        ),
    ("mh_10_invoice_add","/admin/accounting/invoice/add/",          ),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    page.goto(f"{BASE}/admin/login/?next=/")
    page.fill('input[name="username"]', "muhasebeci")
    page.fill('input[name="password"]', "Test123!")
    page.click('input[type="submit"]')
    page.wait_for_load_state("networkidle")
    print(f"After login URL: {page.url}")

    for name, path in PAGES:
        page.goto(f"{BASE}{path}")
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        out = OUT / f"{name}.png"
        page.screenshot(path=str(out), full_page=True)
        print(f"  {name:22s} {path:45s} -> {out}  (title: {page.title()!r})")

    browser.close()
print("Done.")
