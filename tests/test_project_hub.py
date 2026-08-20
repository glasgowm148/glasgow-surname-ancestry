#!/usr/bin/env python3
"""Smoke test for the Glasgow project landing page."""

from pathlib import Path

from playwright.sync_api import sync_playwright


HUB_URL = (Path(__file__).resolve().parents[1] / "www" / "index.html").as_uri()
SHARE_CARD = Path(__file__).resolve().parents[1] / "www" / "assets" / "share-card.png"
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        launch_options = {"executable_path": str(LOCAL_CHROME)} if LOCAL_CHROME.exists() else {}
        browser = playwright.chromium.launch(headless=True, **launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(HUB_URL, wait_until="networkidle")

        tiles = page.locator("nav.tiles a.tile")
        assert tiles.count() == 5
        hrefs = tiles.evaluate_all("nodes => nodes.map(node => node.href)")
        assert hrefs[0].endswith("/www/map/index.html")
        assert hrefs[1].endswith("/www/timeline.html")
        assert hrefs[2] == "https://www.wikitree.com/wiki/Space:Glasgow_Name_Study"
        assert hrefs[3] == "https://www.familytreedna.com/groups/glasgow/about"
        assert hrefs[4] == "https://groups.io/g/glasgowdnaproject/"
        assert tiles.evaluate_all("nodes => nodes.every(node => node.target === '_blank')")
        assert tiles.evaluate_all("nodes => nodes.every(node => node.rel.includes('noopener'))")
        assert page.locator(".featured-grid .tile").count() == 2
        assert page.locator(".participate-grid .tile").count() == 3
        assert page.locator('[data-stat="records"]').first.inner_text() == "1,913"
        assert page.locator('[data-stat="locations"]').inner_text() == "256"
        assert page.locator('meta[property="og:image"]').get_attribute("content").endswith("/assets/share-card.png")
        assert page.locator('link[rel="icon"]').count() == 1
        assert SHARE_CARD.exists() and SHARE_CARD.stat().st_size > 10_000

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        assert page.locator(".featured-grid .tile").evaluate_all(
            "nodes => nodes.every(node => getComputedStyle(node).display === 'flex')"
        )
        assert not errors, errors
        browser.close()

    print("Project-hub browser smoke test passed")


if __name__ == "__main__":
    main()
