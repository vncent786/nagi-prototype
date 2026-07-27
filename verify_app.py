import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.getenv("NAGI_APP_URL", "http://127.0.0.1:8771/app.html")
OUT = Path(r"D:\OpenClaw\.openclaw\workspace\real-estate\tmp\nagi-onboarding")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=1)
    errors = []
    page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
    response = page.goto(URL, wait_until="networkidle")
    assert response and response.status == 200

    assert page.locator("#todayView.active").count() == 1
    assert page.get_by_text("Sample month", exact=True).count() == 1
    assert page.locator("#reviewCount").inner_text() == "2"
    assert page.locator("#reviewPulse").evaluate("el => getComputedStyle(el).animationName") == "pulse"
    page.screenshot(path=str(OUT / "daily-01-today.png"), full_page=True)

    # Transaction rows show category only, not "/ Automatic".
    tx_text = page.locator("#transactionList").inner_text()
    assert "/ Automatic" not in tx_text, "Recent rows should not say / Automatic"
    assert "/ Manual" not in tx_text, "Recent rows should not say / Manual"

    # Clicking a recent transaction opens the detail sheet.
    page.locator("#transactionList .tx-row").first.click()
    assert page.locator("#detailSheet.open").count() == 1
    assert page.locator("#detailMerchant").inner_text() != ""
    assert page.locator("#detailDate").inner_text() != ""
    assert page.locator("#detailMethod").inner_text() != ""
    assert page.locator("#detailSource").inner_text() != ""
    page.get_by_role("button", name="Close", exact=True).click()
    assert page.locator("#detailSheet.open").count() == 0

    # Clicking a category in "Where it went" opens the category breakdown.
    page.locator(".cat-btn[data-cat='Food']").click()
    assert page.locator("#catSheet.open").count() == 1
    assert page.locator("#catTitle").inner_text() == "Food"
    assert page.locator("#catTotal").inner_text() == "$842"
    assert page.locator("#catTxList .cat-tx").count() >= 1
    page.get_by_role("button", name="Close", exact=True).click()
    assert page.locator("#catSheet.open").count() == 0

    # Manual-entry validation and successful add.
    page.get_by_role("button", name="Add expense", exact=True).click()
    assert page.locator("#manualSheet.open").count() == 1
    page.locator("#manualMerchant").fill("Kopitiam")
    page.locator("#manualAmount").fill("12.34")
    page.locator("#manualCategory").select_option(label="Food")
    old_total = page.locator("#monthTotal").inner_text()
    page.get_by_role("button", name="Add to Today", exact=True).click()
    assert page.locator("#manualSheet.open").count() == 0
    assert page.get_by_text("Kopitiam", exact=True).count() == 1
    assert page.locator("#monthTotal").inner_text() != old_total
    new_tx_text = page.locator("#transactionList").inner_text()
    assert "/ Manual" not in new_tx_text, "Manual entry should not show / Manual in meta"
    page.wait_for_timeout(2300)

    # Review first capture, edit it, and keep it.
    page.get_by_role("button", name="Two captures need a glance", exact=False).click()
    assert page.locator("#reviewView.active").count() == 1
    assert page.locator("#reviewPosition").inner_text() == "Capture 1 of 2"
    assert "sample content" in page.locator("#sourceCopy").text_content()
    page.wait_for_timeout(850)
    assert page.locator("#doneView").evaluate("el => getComputedStyle(el).display") == "none"
    assert page.locator(".notification").evaluate("el => Number(getComputedStyle(el).opacity)") > 0.99
    page.screenshot(path=str(OUT / "daily-02-review.png"), full_page=True)
    page.locator("#merchant").fill("VivoCity")
    page.get_by_role("button", name="Dining", exact=True).click()
    assert page.get_by_role("button", name="Dining", exact=True).get_attribute("aria-pressed") == "true"
    page.get_by_role("button", name="Keep expense", exact=True).click()
    page.wait_for_timeout(820)
    assert page.locator("#reviewPosition").inner_text() == "Capture 2 of 2"
    assert page.locator("#progressOne").get_attribute("class") == "done"
    assert page.locator("#progressTwo").get_attribute("class") == "current"

    # Reject second capture and finish.
    page.get_by_role("button", name="This is not an expense", exact=True).click()
    page.wait_for_timeout(260)
    assert page.locator("#doneView").evaluate("el => getComputedStyle(el).display") == "flex"
    assert page.get_by_role("heading", name="All caught up.", exact=True).count() == 1
    assert page.locator(".still-square").evaluate("el => getComputedStyle(el).animationName") == "comeToRest"
    page.screenshot(path=str(OUT / "daily-03-done.png"), full_page=True)

    page.get_by_role("button", name="Return to Today", exact=True).click()
    assert page.locator("#todayView.active").count() == 1
    assert page.locator("#reviewCount").inner_text() == "0"
    assert page.get_by_text("VivoCity", exact=True).count() == 1
    assert "/ Reviewed" not in page.locator("#transactionList").inner_text(), "Reviewed tx should not show / Reviewed"
    assert page.get_by_role("button", name="Replay the sample review", exact=True).is_visible()

    # Replay and leave without mutating the queue.
    page.get_by_role("button", name="Replay the sample review", exact=True).click()
    assert page.locator("#reviewPosition").inner_text() == "Capture 1 of 2"
    page.get_by_role("button", name="Back", exact=True).click()
    assert page.locator("#todayView.active").count() == 1

    # Trends is connected as a real app destination.
    page.get_by_role("button", name="Trends", exact=True).click()
    page.wait_for_url("**/trends.html")
    assert page.get_by_role("heading", name="Trends", exact=True).count() == 1

    dimensions = page.evaluate("({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
    assert dimensions["scroll"] == dimensions["client"], dimensions
    assert not errors, errors

    reduced = browser.new_page(viewport={"width": 430, "height": 932}, reduced_motion="reduce")
    reduced.goto(URL, wait_until="networkidle")
    assert reduced.locator("#reviewPulse").evaluate("el => getComputedStyle(el).animationName") == "none"
    reduced.close()

    print("PASS: Today dashboard, simplified meta, transaction detail sheet, category breakdown, manual add, capture edit/category/keep, discard, completion, return, replay, nav messaging, reduced motion, responsiveness, and console")
    browser.close()
