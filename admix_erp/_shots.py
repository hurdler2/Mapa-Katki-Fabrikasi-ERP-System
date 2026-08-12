"""Login + take screenshots of all key ERP pages."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
OUT = Path("_screenshots")
OUT.mkdir(exist_ok=True)

PAGES = [
    ("01_home",         "/",                          "ADMIX-ERP"),
    ("02_reporting",    "/reporting/dashboard/",      "Dashboard"),
    ("03_bi",           "/analytics/bi/",             "BI"),
    ("04_iso_audit",    "/analytics/iso-audit/",      "ISO"),
    ("05_accounting",   "/accounting/balance/",       "Mizan"),
    ("06_notifications","/notifications/",            "Bildirim"),
    ("07_admin",        "/admin/",                    "administration"),
    ("08_admin_batch",  "/admin/production/productionbatch/",  "batch"),
    ("09_admin_lot",    "/admin/inventory/rawmateriallot/",    "lot"),
    ("10_admin_ncr",    "/admin/qms/nonconformance/",          "NCR"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    # Login via Django admin form (session cookie will apply everywhere)
    page.goto(f"{BASE}/admin/login/?next=/")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "Secret123!")
    page.click('input[type="submit"]')
    page.wait_for_load_state("networkidle")
    print(f"After login URL: {page.url}")

    for name, path, hint in PAGES:
        target = f"{BASE}{path}"
        page.goto(target)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        out = OUT / f"{name}.png"
        page.screenshot(path=str(out), full_page=True)
        # Console errors?
        title = page.title()
        print(f"  {name:20s} {path:45s} -> {out}  (title: {title!r})")

    browser.close()
print("Done.")
