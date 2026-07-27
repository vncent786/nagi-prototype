import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.getenv("NAGI_TRENDS_URL", "http://127.0.0.1:8771/trends.html")
OUT = Path(r"D:\OpenClaw\.openclaw\workspace\real-estate\tmp\nagi-onboarding")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=1)
    errors = []
    page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
    response = page.goto(URL, wait_until="networkidle")
    assert response and response.status == 200

    assert page.get_by_role("heading", name="Trends", exact=True).count() == 1
    assert page.get_by_text("Sample data", exact=True).count() == 1

    # 4 range tabs now
    assert page.locator('[data-range]').count() == 4

    # Month range
    assert page.locator("#total").inner_text() == "$3,247"
    assert page.locator(".bar-button").count() == 7
    assert "Shopping rose by $142" in page.locator("#insight").inner_text()
    # Category split bar + legend
    assert page.locator(".split-segment").count() == 5
    assert page.locator(".legend-row").count() == 5
    assert "31.0%" in page.locator("#splitLegend").inner_text()
    assert "pp" in page.locator("#splitLegend").inner_text()
    page.wait_for_timeout(750)
    page.screenshot(path=str(OUT / "trends-01-month.png"), full_page=True)

    # Chart point selection
    page.get_by_role("button", name="Feb $2,920", exact=True).click()
    assert page.locator("#chartReadout").inner_text() == "Feb / $2,920"

    # Three-month range
    page.get_by_role("tab", name="3 months", exact=True).click()
    assert page.locator("#total").inner_text() == "$9,359"
    assert page.locator(".bar-button").count() == 2
    assert page.locator(".split-segment").count() == 5
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "trends-02-three-months.png"), full_page=True)

    # Year range
    page.get_by_role("tab", name="Year", exact=True).click()
    assert page.locator("#total").inner_text() == "$21,155"
    assert page.locator(".split-segment").count() == 5
    # Year range has no share deltas (null) - should show em dash
    assert "\u2014" in page.locator("#splitLegend").inner_text()

    # All range (new)
    page.get_by_role("tab", name="All", exact=True).click()
    assert page.get_by_role("tab", name="All", exact=True).get_attribute("aria-selected") == "true"
    assert page.locator("#total").inner_text() == "$37,460"
    assert page.locator("#comparison").inner_text() == "On pace for $36,300 this year, about 3% less"
    assert page.locator(".bar-button").count() == 2
    assert "stable year over year" in page.locator("#insight").inner_text()
    assert page.locator(".split-segment").count() == 5
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "trends-04-all.png"), full_page=True)

    # Settings nav
    page.get_by_role("button", name="Settings", exact=True).click()
    page.wait_for_url("**/settings.html")
    assert page.get_by_role("heading", name="Quiet by default", exact=True).count() == 1

    dimensions = page.evaluate("({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
    assert dimensions["scroll"] == dimensions["client"], dimensions
    assert not errors, errors

    # Today nav
    page.get_by_role("button", name="Today", exact=True).click()
    page.wait_for_url("**/app.html")
    assert page.locator("#todayView.active").count() == 1

    reduced = browser.new_page(viewport={"width": 430, "height": 932}, reduced_motion="reduce")
    reduced.goto(URL, wait_until="networkidle")
    assert reduced.locator(".rest-track span").evaluate("el => getComputedStyle(el).animationName") == "none"
    reduced.close()

    print("PASS: month/3-month/year/all trends, category split bar, share deltas, chart selection, dynamic insight, Today navigation, reduced motion, responsiveness, and console")
    browser.close()
