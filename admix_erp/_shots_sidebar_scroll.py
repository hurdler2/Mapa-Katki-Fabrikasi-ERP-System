"""Sidebar scroll koruma testi.

Adimlar:
1. Admin ile giris (menu uzun oldugu icin)
2. /portal/kalite/ sayfasina git
3. Sidebar'i asagi scroll et (200px)
4. Sidebar'in altindaki bir link'e tikla (Kural Ihlalleri)
5. Yeni sayfada sidebar scrollTop kontrol et — 200 civari olmali
6. Screenshot al
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path("_screenshots/sidebar"); OUT.mkdir(parents=True, exist_ok=True)


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 700})
    page = ctx.new_page()

    # Login
    page.goto(f"{BASE}/login/")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "Secret123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # Kalite sayfasi
    page.goto(f"{BASE}/portal/kalite/")
    page.wait_for_load_state("networkidle")

    # Sidebar'i asagi scroll et
    page.evaluate("document.querySelector('aside').scrollTop = 400")
    scroll_before = page.evaluate("document.querySelector('aside').scrollTop")
    print(f"Scroll BEFORE navigation: {scroll_before}px")
    page.screenshot(path=str(OUT / "01_before_click_scrolled.png"), full_page=False)

    # Sidebar'daki alt menu link'ine tikla (Kural Ihlalleri gorunmeli)
    # Once linkin var oldugundan emin ol, sonra tikla
    page.click('aside a:has-text("Kural İhlalleri")')
    page.wait_for_load_state("networkidle")

    scroll_after = page.evaluate("document.querySelector('aside').scrollTop")
    print(f"Scroll AFTER  navigation: {scroll_after}px")
    print(f"Fark: {abs(scroll_before - scroll_after)}px (0 olmali)")
    page.screenshot(path=str(OUT / "02_after_click.png"), full_page=False)

    # Baska bir uzun link'e daha tikla — Case'ler
    page.click('aside a:has-text("Case\'ler / Vakalar")')
    page.wait_for_load_state("networkidle")
    scroll_3 = page.evaluate("document.querySelector('aside').scrollTop")
    print(f"Scroll after 2nd navigation: {scroll_3}px (koruma calisiyor mu)")
    page.screenshot(path=str(OUT / "03_second_nav.png"), full_page=False)

    ctx.close()
    browser.close()
