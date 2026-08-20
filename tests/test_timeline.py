#!/usr/bin/env python3
"""Responsive smoke test for the Y-DNA timeline."""

from pathlib import Path

from playwright.sync_api import sync_playwright


TIMELINE_URL = (Path(__file__).resolve().parents[1] / "www" / "timeline.html").as_uri()


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(TIMELINE_URL, wait_until="networkidle")

        rows = page.locator(".timeline-row")
        assert rows.count() == 15
        assert page.locator(".mobile-tabs-ready").count() == 15
        assert page.locator(".mobile-header").count() == 15
        assert page.locator(".mobile-tabs").count() == 15
        assert page.locator('.nav-bar a[href="index.html"]').count() == 1
        assert page.locator('.nav-bar a[href="map/index.html"]').count() == 1

        row = page.locator("#R-Z17")
        assert row.locator(".col-left").is_visible()
        assert not row.locator(".col-right").is_visible()
        row.locator(".tab-btn", has_text="Narrative").click()
        assert not row.locator(".col-left").is_visible()
        assert row.locator(".col-right").is_visible()
        assert not errors, errors
        browser.close()

    print("Timeline responsive browser smoke test passed")


if __name__ == "__main__":
    main()
