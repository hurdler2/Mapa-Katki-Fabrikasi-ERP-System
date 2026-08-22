"""Sprint 1 dogrulama: uretim emri detay + bilan massique + besoins theoriques."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sprint1"); OUT.mkdir(parents=True, exist_ok=True)


def login(page, user, pw):
    page.goto(f"{BASE}/logout/"); page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    login(page, "op.manager", "Demo123!")

    # 1. Baz scale (order.target_qty ile)
    page.goto(f"{BASE}/portal/uretim/emir/5/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "01_base_scale.png"), full_page=True)
    print("01: base scale (target_qty original)")

    # 2. Scale 2.0 preview
    page.goto(f"{BASE}/portal/uretim/emir/5/?scale=2.0")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "02_scale_2x.png"), full_page=True)
    print("02: scale 2.0 preview")

    # 3. Scale 0.5 preview (bilan massique kucuk hedef)
    page.goto(f"{BASE}/portal/uretim/emir/5/?scale=0.5")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "03_scale_05x.png"), full_page=True)
    print("03: scale 0.5 preview")

    ctx.close()
    browser.close()
    print("Done.")
