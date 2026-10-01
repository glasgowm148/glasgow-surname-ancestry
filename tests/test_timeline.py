#!/usr/bin/env python3
"""Responsive smoke test for the Y-DNA timeline."""

from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
TIMELINE_URL = (ROOT / "www" / "timeline" / "index.html").as_uri()


def test_timeline_disclosures_are_idempotent_and_anchor_safe() -> None:
    from tools.repair_timeline_navigation import collapse_large_timeline_sections

    page = (ROOT / "www" / "timeline" / "index.html").read_text(encoding="utf-8")
    before = BeautifulSoup(page, "html.parser")
    repaired = collapse_large_timeline_sections(page)
    after = BeautifulSoup(repaired, "html.parser")

    assert len(after.select("details.timeline-disclosure")) == 6
    assert len(after.select("details.timeline-disclosure")) == len(
        BeautifulSoup(collapse_large_timeline_sections(repaired), "html.parser").select(
            "details.timeline-disclosure"
        )
    )
    assert {node.get("id") for node in before.select("[id]")} == {
        node.get("id") for node in after.select("[id]")
    }
    assert after.select_one("#branch-map").find_parent("details").get(
        "data-timeline-disclosure"
    )
    assert after.select_one("#R-FTE32242").find_parent("details").get(
        "data-timeline-disclosure"
    )
    assert not after.select("details.timeline-disclosure[open]")


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(TIMELINE_URL, wait_until="networkidle")

        rows = page.locator(".timeline-row")
        assert rows.count() == 25
        assert page.locator(".mobile-tabs-ready").count() == 25
        assert page.locator(".mobile-header").count() == 25
        assert page.locator(".mobile-tabs").count() == 25
        assert page.locator('.g-nav-link[href="/"]').count() == 1
        assert page.locator('.g-nav-link[href="/onetree/"]').count() == 1

        row = page.locator("#R-Z17")
        assert row.locator(".col-left").is_visible()
        assert not row.locator(".col-right").is_visible()
        row.locator(".tab-btn", has_text="Narrative").click()
        assert not row.locator(".col-left").is_visible()
        assert row.locator(".col-right").is_visible()
        branch = page.locator("#R-FT20271")
        branch.locator(".timeline-card-disclosure > summary").click()
        assert branch.locator("#branch-map").is_hidden()
        branch.locator(".timeline-branch-disclosure > summary").click()
        assert branch.locator("#branch-map").is_visible()
        assert not errors, errors
        browser.close()

    print("Timeline responsive browser smoke test passed")


if __name__ == "__main__":
    main()
