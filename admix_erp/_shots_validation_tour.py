"""Portal validation tour — her menu link'ini gez, HTTP kod ve validation raporla."""
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


# admin ile en fazla menu itemi'na erisim var
PAGES_TO_TEST = [
    "/portal/",
    "/portal/uretim/",
    "/portal/uretim/parti-baslat/",
    "/portal/recete/",
    "/portal/kalite/",
    "/portal/kalite/test-sonuclari/",
    "/portal/kalite/coa/",
    "/portal/registry/",
    "/portal/cases/",
    "/portal/gates/",
    "/portal/master/integrated/",
    "/portal/master/security/",
    "/portal/kurallar/",
    "/portal/kurallar/katalog/",
    "/portal/ims/ncr/",
    "/portal/ims/capa/",
    "/portal/ims/dokumanlar/",
    "/portal/ims/ic-denetim/",
    "/portal/ims/yonetim-gozden-gecirme/",
    "/portal/stok/",
    "/portal/stok/mal-kabul/",
    "/portal/stok/lotlar/",
    "/portal/satin-alma/",
    "/portal/tedarikci/",
    "/portal/muhasebe/",
    "/portal/muhasebe/faturalar/",
    "/portal/muhasebe/faturalar/yeni/",
    "/portal/muhasebe/mizan/",
    "/accounting/payments/new/",
    "/portal/bakim/",
    "/portal/bakim/ekipmanlar/",
    "/portal/ehs/",
    "/portal/ehs/olay-bildir/",
    "/portal/yonetim/",
    "/portal/bt/",
    "/notifications/",
    "/portal/onaylar/",
    "/analytics/bi/",
    "/analytics/iso-audit/",
    "/reporting/dashboard/",
]


results = {"ok": [], "bad": [], "unknown": []}

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    login(page, "admin", "Secret123!")

    for path in PAGES_TO_TEST:
        try:
            resp = page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=15000)
            code = resp.status if resp else 0
            # Django hata sayfasi kontrol
            has_traceback = page.locator("body").filter(has_text="Traceback").count() > 0
            has_error = code >= 500 or has_traceback
            if has_error:
                results["bad"].append((path, code, "HATA - traceback var" if has_traceback else f"HTTP {code}"))
                print(f"  BAD [{code}]  {path}  {'traceback' if has_traceback else 'error'}")
            elif code == 200 or code == 302:
                results["ok"].append((path, code))
                print(f"  OK  [{code}]  {path}")
            else:
                results["unknown"].append((path, code))
                print(f"  ?   [{code}]  {path}")
        except Exception as e:  # noqa: BLE001
            results["bad"].append((path, 0, str(e)[:80]))
            print(f"  ERR       {path}  {e}")

    ctx.close()
    browser.close()

print()
print(f"OK   : {len(results['ok'])}")
print(f"BAD  : {len(results['bad'])}")
if results["bad"]:
    print()
    print("HATA ALAN SAYFALAR:")
    for p, c, m in results["bad"]:
        print(f"  {p:45s} [{c}] {m}")
