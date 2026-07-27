import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.getenv("NAGI_URL", "http://127.0.0.1:8771/")
OUT = Path(r"D:\OpenClaw\.openclaw\workspace\real-estate\tmp\nagi-onboarding")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=1)
    errors = []
    page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
    response = page.goto(URL, wait_until="networkidle")
    assert response and response.status == 200

    # Inter Tight font
    assert page.locator("link[href*='fonts.googleapis']").count() >= 1
    assert "Inter Tight" in page.evaluate("getComputedStyle(document.body).fontFamily")

    # Maroon accent
    accent = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()")
    assert accent == "#814543", f"accent was {accent}"

    # No kicker class anywhere
    assert page.locator(".kicker").count() == 0

    # Screen 0: Welcome
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "0"
    assert page.get_by_text("when wind stops", exact=False).count() >= 1

    # Screen 1: History
    page.get_by_role("button", name="Try a sample", exact=True).click()
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "1"
    page.get_by_role("button", name="I tried an app and stopped", exact=True).click()
    page.get_by_role("button", name="Continue", exact=True).click()

    # Screen 2: Pain (multi-select)
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "2"
    assert page.get_by_text("It's too complex", exact=False).count() >= 1
    assert page.get_by_text("share with people I care about", exact=False).count() >= 1
    page.get_by_role("button", name="It's too complex", exact=False).click()
    page.get_by_role("button", name="Entering every purchase gets old", exact=True).click()
    page.get_by_text("Choose all that apply", exact=True)
    page.get_by_role("button", name="Continue", exact=True).click()

    # Screen 3: Reason
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "3"
    reason_text = page.locator("#reasonList").inner_text()
    assert "Logging every purchase" in reason_text
    assert "Too many moving parts" in reason_text
    page.get_by_role("button", name="Let me try it", exact=True).click()

    # Screen 4: Intro (NEW)
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "4"
    assert page.get_by_text("A quiet record of your spending", exact=False).count() >= 1
    # Wait for staggered animation to reveal content
    page.wait_for_timeout(3000)
    assert page.get_by_text("You pay as usual", exact=False).count() >= 1
    assert page.get_by_text("Everything stays on your phone", exact=False).count() >= 1
    page.screenshot(path=str(OUT / "v6-04-intro.png"), full_page=True)
    # Wait for button to appear (delay 4400ms)
    page.wait_for_timeout(2500)
    page.get_by_role("button", name="See it work", exact=True).click()

    # Screen 5: Capture
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "5"
    page.get_by_role("button", name="Keep this expense", exact=True).click()
    page.wait_for_timeout(1500)

    # Screen 6: Permission (category screen removed)
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "6"
    page.get_by_role("button", name="I understand", exact=True).click()

    # Screen 7: Paywall
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "7"
    assert page.get_by_text("$79.99", exact=False).count() >= 1
    page.get_by_role("button", name="Start my 7-day trial", exact=True).click()

    # Screen 8: Setup
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "8"
    page.get_by_role("button", name="Skip for now", exact=True).click()

    # Screen 9: Done
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "9"
    assert page.get_by_text("You're set", exact=False).count() >= 1

    # Enter app
    page.get_by_role("button", name="Enter Nagi", exact=True).click()
    page.wait_for_url("**/app.html")
    assert page.locator("#todayView.active").count() == 1

    # Back button from capture screen re-enables button
    page.go_back()
    page.wait_for_url("**/")
    page.get_by_role("button", name="Try a sample", exact=True).click()
    page.wait_for_timeout(400)
    page.get_by_role("button", name="I tried an app and stopped", exact=True).click()
    page.wait_for_timeout(200)
    page.get_by_role("button", name="Continue", exact=True).click()
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Entering every purchase gets old", exact=True).click()
    page.wait_for_timeout(200)
    page.get_by_role("button", name="Continue", exact=True).click()
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Let me try it", exact=True).click()
    page.wait_for_timeout(400)
    # Skip intro animation
    page.wait_for_timeout(5000)
    page.get_by_role("button", name="See it work", exact=True).click()
    page.wait_for_timeout(400)
    # Screen 5: capture
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "5"
    page.get_by_role("button", name="Keep this expense", exact=True).click()
    page.wait_for_timeout(1500)
    # Screen 6: permission, press back
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "6"
    page.get_by_role("button", name="Back", exact=True).click()
    page.wait_for_timeout(300)
    # Back at screen 5, button should be re-enabled
    assert page.locator(".screen.is-active").get_attribute("data-screen") == "5"
    btn = page.get_by_role("button", name="Keep this expense", exact=True)
    assert btn.is_enabled(), "Capture button was not re-enabled after back"

    dimensions = page.evaluate("({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
    assert dimensions["scroll"] == dimensions["client"], dimensions
    assert not errors, errors

    print("PASS: Inter Tight font, maroon accent, no kickers, multi-select pain, tailored reasons, intro screen with staggered animation, capture with back-recovery, category screen removed, paywall with lifetime, done screen, app entry")
    browser.close()
