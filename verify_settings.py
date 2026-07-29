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

    # Capture health is passive and transparent. There is no source-selection chore.
    assert page.get_by_text("Capture health", exact=True).count() == 1
    assert page.locator(".setting-label").filter(has_text="Notification access").count() == 1
    assert page.locator(".setting-label").filter(has_text="Last capture").count() == 1
    assert page.get_by_text("Notifications received", exact=True).count() == 1
    assert page.get_by_text("47", exact=True).count() >= 1
    assert page.get_by_text("Unresolved", exact=True).count() == 1
    assert page.get_by_text("0", exact=True).count() >= 1
    assert page.get_by_text("Nagi can only count payment notifications it receives", exact=False).count() == 1
    assert page.locator("#regionSelect").count() == 0
    assert page.locator("#captureSources .toggle").count() == 0

    # Capture history exposes source and outcome without cluttering Today.
    page.get_by_role("button", name="View capture history", exact=True).click()
    assert page.locator("#captureSheet.open").count() == 1
    assert page.locator("#captureHistory .capture-event").count() == 3
    assert page.get_by_text("Google Wallet", exact=True).count() >= 1
    assert page.get_by_text("Recorded", exact=True).count() >= 1
    page.locator("#closeCapture").click()
    assert page.locator("#captureSheet.open").count() == 0

    # Categories - functional management
    assert page.locator(".cat-row").count() == 6
    assert page.get_by_text("3 merchant rules", exact=False).count() >= 1
    assert page.get_by_text("Dining, Groceries", exact=False).count() == 0

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

    # Add a flat custom category without creating a subcategory hierarchy.
    page.get_by_role("button", name="Add category", exact=True).click()
    assert page.locator("#catSheet.open").count() == 1
    assert page.locator("#catEditName").input_value() == "New category"
    page.locator("#catEditName").fill("Healthcare")
    page.get_by_role("button", name="Save changes", exact=True).click()
    assert page.get_by_text("Healthcare", exact=True).count() == 1
    assert page.locator(".cat-row").count() == 7

    # Recurring section
    assert page.get_by_text("Recurring expenses", exact=True).count() == 1
    assert page.locator("#recurringList .recurring-row").count() == 5
    assert page.get_by_text("Netflix", exact=False).count() >= 1
    assert page.get_by_text("$372.96", exact=False).count() == 0  # no total shown, just individual
    assert page.get_by_text("Add recurring expense", exact=True).count() == 1

    # Sharing is deferred to a later phase.
    assert page.get_by_text("Couple Sync", exact=False).count() == 0
    assert page.get_by_text("Kelly", exact=False).count() == 0
    assert page.get_by_text("Total household", exact=False).count() == 0

    # Paid app includes complete export and restore, not CSV-only portability.
    assert page.get_by_text("Data", exact=True).count() == 1
    assert page.get_by_text("Records, rules, recurring expenses and settings", exact=False).count() == 1
    page.get_by_role("button", name="Export", exact=True).click()
    assert page.locator("#toast").inner_text() == "Nagi backup ready to export"
    page.get_by_role("button", name="Restore", exact=True).click()
    assert page.locator("#toast").inner_text() == "Choose a Nagi backup in the full app"
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "settings-01-full.png"), full_page=True)

    # Privacy
    assert page.get_by_text("Bank integration", exact=False).count() == 0
    assert page.get_by_text("Nagi never connects to your bank", exact=False).count() == 0

    # Nav to Today
    page.get_by_role("button", name="Today", exact=True).click()
    page.wait_for_url("**/app.html")
    assert page.locator("#todayView.active").count() == 1

    dimensions = page.evaluate("({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
    assert dimensions["scroll"] == dimensions["client"], dimensions
    assert not errors, errors

    reduced = browser.new_page(viewport={"width": 430, "height": 932}, reduced_motion="reduce")
    reduced.goto(URL, wait_until="networkidle")
    assert reduced.locator(".content").evaluate("el => getComputedStyle(el).animationName") == "none"
    reduced.close()

    print("PASS: passive capture health/history, no sharing phase, category management, recurring expenses, complete data portability, privacy, navigation, reduced motion, responsiveness, and console")
    browser.close()
