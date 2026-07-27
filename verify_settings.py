import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.getenv("NAGI_SETTINGS_URL", "http://127.0.0.1:8771/settings.html")
OUT = Path(r"D:\OpenClaw\.openclaw\workspace\real-estate\tmp\nagi-onboarding")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=1)
    errors = []
    page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
    response = page.goto(URL, wait_until="networkidle")
    assert response and response.status == 200

    assert page.get_by_role("heading", name="Quiet by default", exact=True).count() == 1

    # Region selector exists and defaults to Singapore
    region = page.locator("#regionSelect")
    assert region.get_attribute("value") == "sg" or region.evaluate("el => el.selectedIndex") == 0
    assert page.get_by_text("DBS PayLah!", exact=False).count() >= 1
    # Grab and Shopee must NOT exist
    assert page.get_by_text("Grab", exact=False).count() == 0
    assert page.get_by_text("Shopee", exact=False).count() == 0
    assert page.locator("#captureSources .toggle").count() == 3

    # Change region to Australia
    region.select_option("au")
    page.wait_for_timeout(300)
    assert page.get_by_text("CommBank", exact=False).count() >= 1
    assert page.get_by_text("DBS PayLah!", exact=False).count() == 0
    assert page.locator("#captureSources .toggle").count() == 3

    # Change back to Singapore
    region.select_option("sg")
    page.wait_for_timeout(300)
    assert page.get_by_text("DBS PayLah!", exact=False).count() >= 1

    # Toggle interaction
    toggle = page.locator("#captureSources .toggle").first
    initial = toggle.get_attribute("aria-checked")
    toggle.click()
    assert toggle.get_attribute("aria-checked") != initial

    # Categories - functional management
    assert page.locator(".cat-row").count() == 5
    assert page.get_by_text("3 rules", exact=False).count() >= 1  # Food has 3 rules

    # Open category edit sheet
    page.get_by_role("button", name="Food", exact=False).first.click()
    page.wait_for_timeout(300)
    assert page.locator("#catSheet.open").count() == 1
    assert page.locator("#catEditName").input_value() == "Food"
    assert page.locator(".rule-row").count() == 3  # FairPrice, Cold Storage, GrabFood

    # Add a merchant rule
    page.locator("#newRuleInput").fill("Kopitiam")
    page.get_by_role("button", name="Add rule", exact=True).click()
    page.wait_for_timeout(200)
    assert page.locator(".rule-row").count() == 4
    assert "Kopitiam" in page.locator("#ruleList").inner_text()

    # Remove a rule
    page.locator(".rule-remove").first.click()
    page.wait_for_timeout(200)
    assert page.locator(".rule-row").count() == 3

    # Rename category
    page.locator("#catEditName").fill("Food & Drink")
    page.get_by_role("button", name="Save changes", exact=True).click()
    page.wait_for_timeout(300)
    assert page.locator("#catSheet.open").count() == 0
    assert page.get_by_text("Food & Drink", exact=False).count() >= 1

    # Recurring section
    assert page.get_by_text("Recurring expenses", exact=True).count() == 1
    assert page.locator("#recurringList .recurring-row").count() == 5
    assert page.get_by_text("Netflix", exact=False).count() >= 1
    assert page.get_by_text("$372.96", exact=False).count() == 0  # no total shown, just individual
    assert page.get_by_text("Add recurring expense", exact=True).count() == 1

    # Couple Sync
    assert page.get_by_text("Total household", exact=False).count() >= 1
    assert "$7,317" in page.locator(".combined-preview").inner_text()

    # Disconnect
    page.get_by_role("button", name="Disconnect", exact=True).click()
    assert page.locator("#toast").inner_text() == "Disconnected from Kelly"
    page.wait_for_timeout(300)
    assert page.locator("#disconnectedState").evaluate("el => getComputedStyle(el).display") != "none"
    assert page.get_by_text("nagi.app/join", exact=False).count() >= 1
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "settings-01-full.png"), full_page=True)

    # Privacy
    assert page.get_by_text("Bank integration", exact=False).count() >= 1
    assert page.get_by_text("Never", exact=False).count() >= 1

    # Nav to Today
    page.get_by_role("button", name="Today", exact=True).click()
    page.wait_for_url("**/app.html")
    assert page.locator("#todayView.active").count() == 1

    dimensions = page.evaluate("({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
    assert dimensions["scroll"] == dimensions["client"], dimensions
    assert not errors, errors

    reduced = browser.new_page(viewport={"width": 430, "height": 932}, reduced_motion="reduce")
    reduced.goto(URL, wait_until="networkidle")
    assert reduced.locator(".rest-track span").evaluate("el => getComputedStyle(el).animationName") == "none"
    reduced.close()

    print("PASS: region selector + dynamic capture sources, category management (rename/rules/add/remove), recurring section, Couple Sync, privacy, navigation, reduced motion, responsiveness, and console")
    browser.close()
