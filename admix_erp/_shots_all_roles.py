"""Her rol icin ekran turu — landing page + gorunur menu."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/roles"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/")
    page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


# 16 rol + superuser = 17 kullanici
USERS = [
    ("admin",             "Secret123!",  "00_admin_superuser"),
    ("gm.director",       "Demo123!",    "01_general_manager"),
    ("tm.director",       "Demo123!",    "02_technical_manager"),
    ("op.manager",        "Demo123!",    "03_operations_manager"),
    ("qa.manager",        "Demo123!",    "04_ims_qa_manager"),
    ("acc.manager",       "Demo123!",    "05_accounting_manager"),
    ("lab.tech",          "Demo123!",    "06_lab_qc"),
    ("shift.supervisor",  "Demo123!",    "07_operations_supervisor"),
    ("warehouse.chief",   "Demo123!",    "08_warehouse"),
    ("purchase.officer",  "Demo123!",    "09_purchasing"),
    # 6 yeni MCOS rolu
    ("rdt.eng",           "Demo123!",    "10_rdt_engineer"),
    ("mlts.analyst",      "Demo123!",    "11_mlts_analyst"),
    ("hse.officer",       "Demo123!",    "12_hse_officer"),
    ("audit.internal",    "Demo123!",    "13_internal_auditor"),
    ("maint.tech",        "Demo123!",    "14_maintenance_tech"),
    ("comm.eng",          "Demo123!",    "15_commercial_eng"),
    ("it.admin",          "Demo123!",    "16_it_admin"),
]


with sync_playwright() as p:
    browser = p.chromium.launch()
    for user, pw, tag in USERS:
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            login(page, user, pw)
            landing = page.url
            page.goto(f"{BASE}/portal/")
            page.wait_for_load_state("networkidle")
            out = OUT / f"{tag}_home.png"
            page.screenshot(path=str(out), full_page=True)

            # Menu labels'i extract et (sadece link'lere sahip menu item'lar)
            labels = page.eval_on_selector_all(
                "aside a", "els => els.map(e => e.textContent.trim())"
            )
            menu_items = [l for l in labels if l and len(l) > 1]
            print(f"[{tag}] {user}  landing={landing.replace(BASE, '')}  menu_items={len(menu_items)}")
            for lbl in menu_items:
                print(f"    - {lbl}")
        except Exception as e:  # noqa: BLE001
            print(f"[{tag}] {user}  HATA: {e}")
        finally:
            ctx.close()
    browser.close()
print("\nTUM ROLLER SCREENSHOT'LANDI.")
