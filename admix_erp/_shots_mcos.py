"""Faz D/E/G/H MCOS sayfalarinin ekran goruntuleri."""
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


TOUR = [
    # (yol, dosya_adi, ne_gorunmeli)
    ("/portal/",                                  "mcos_00_home.png",           "Portal ana ekran (yeni MCOS menusu solda)"),
    ("/portal/registry/",                          "mcos_01_registry_list.png",  "Faz C: Kontrollu Kod Register (271 kimlik)"),
    ("/portal/cases/",                             "mcos_02_case_list.png",       "Faz D: Case listesi"),
    ("/portal/cases/INCIDENT-DEMO-001/",           "mcos_03_case_detail.png",     "Faz D: Case detay (T-faz timeline + records/evidence/decisions)"),
    ("/portal/records/NCR-DEMO-001/",              "mcos_04_record_detail.png",   "Faz D: RecordInstance detay (SoD roller)"),
    ("/portal/decisions/DEC-DEMO-001/",            "mcos_05_decision_detail.png", "Faz D: Decision detay (NAV-002 §4)"),
    ("/portal/gates/",                             "mcos_06_gate_list.png",       "Faz E: 8-Part Gate listesi"),
    ("/portal/gates/GATE-DEMO-001/",               "mcos_07_gate_detail.png",     "Faz E: 8 renkli kart detay"),
    ("/portal/master/integrated/",                 "mcos_08_master_integrated.png","Faz G: Integrated Register (KPI + HOLD kirmizi)"),
    ("/portal/master/integrated/INCIDENT-DEMO-001/","mcos_09_master_detail.png",   "Faz G: Integrated detay (snapshot chain)"),
    ("/portal/master/security/",                   "mcos_10_master_security.png", "Faz G: Security Event Register (SEV1 ESCALATED)"),
    ("/portal/kurallar/",                          "mcos_11_rule_violations.png", "Faz H: Kural ihlal listesi"),
    ("/portal/kurallar/katalog/",                  "mcos_12_rule_catalog.png",    "Faz H: 12 kural katalog"),
    ("/api/v1/retrieve/?ref=INCIDENT-DEMO-001",    "mcos_13_retrieve_api.png",    "Faz F: Retrieval endpoint JSON"),
]


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    login(page, "admin", "Secret123!")
    print(f"Login OK -> {page.url}")
    for path, fname, note in TOUR:
        page.goto(f"{BASE}{path}")
        page.wait_for_load_state("networkidle")
        out = OUT / fname
        page.screenshot(path=str(out), full_page=True)
        print(f"  {path:55s} -> {fname}  ({note})")
    ctx.close()
    browser.close()
print("\nTUM SCREENSHOT'LAR TAMAM.")
