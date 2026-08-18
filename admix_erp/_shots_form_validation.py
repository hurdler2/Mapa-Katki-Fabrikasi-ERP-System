"""Form validation testleri — eksik/hatali veri gonderme."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/tour"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def check_required_fields_marked(page, path, tag):
    """HTML form icinde `required` attribute'u olan alanlari listele."""
    page.goto(f"{BASE}{path}")
    page.wait_for_load_state("networkidle")
    required = page.eval_on_selector_all(
        "form input[required], form select[required], form textarea[required]",
        "els => els.map(e => e.name || e.id || 'unnamed')"
    )
    all_fields = page.eval_on_selector_all(
        "form input:not([type='hidden']), form select, form textarea",
        "els => els.map(e => ({name: e.name || e.id, required: e.required}))"
    )
    print(f"[{tag}] {path}")
    print(f"  Toplam form alan: {len(all_fields)}")
    print(f"  Required marked  : {len(required)}")
    if required:
        print(f"  Required: {', '.join(required[:8])}")


VALIDATE_TESTS = [
    ("/portal/muhasebe/faturalar/yeni/", "Yeni fatura"),
    ("/accounting/payments/new/",       "Yeni odeme"),
    ("/portal/uretim/parti-baslat/",    "Yeni parti"),
    ("/portal/stok/mal-kabul/",         "Mal kabul"),
    ("/portal/ehs/olay-bildir/",        "Olay bildir"),
]


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    login(page, "admin", "Secret123!")

    print("=" * 60)
    print("FORM VALIDATION KONTROL (required attribute'lari)")
    print("=" * 60)
    for path, tag in VALIDATE_TESTS:
        try:
            check_required_fields_marked(page, path, tag)
        except Exception as e:  # noqa: BLE001
            print(f"[{tag}] HATA: {e}")
        print()

    # Fatura eksik veri ile submit dene
    print("=" * 60)
    print("EKSIK VERI SUBMIT TESTLERI")
    print("=" * 60)

    page.goto(f"{BASE}/portal/muhasebe/faturalar/yeni/")
    page.wait_for_load_state("networkidle")
    print("Test 1: Bos submit (fatura no yok)")
    # Submit direct
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)
    if "faturalar/yeni" in page.url:
        print(f"  Form kabul etmedi (URL: {page.url}) - OK, browser required calisti")
    else:
        print(f"  Form kabul etti (URL degisti) - EKSIK VALIDASYON")

    # Cek odemesi eksik alan ile
    page.goto(f"{BASE}/accounting/payments/new/")
    page.wait_for_load_state("networkidle")
    page.select_option('select[name="method"]', "CHECK")
    page.fill('input[name="amount"]', "50000")
    print("Test 2: Cek secildi ama cek alanlari bos - submit")
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)
    if "payments/new" in page.url:
        print(f"  Form kabul etmedi (URL: {page.url}) - OK")
    else:
        print(f"  Form kabul etti - EKSIK VALIDASYON")

    ctx.close()
    browser.close()

print("\nValidation tour tamam.")
