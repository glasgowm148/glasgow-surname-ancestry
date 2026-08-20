#!/usr/bin/env python3
"""Rendered smoke test for the public research catalogue."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE = os.environ.get("CATALOGUE_TEST_BASE", "http://127.0.0.1:8765")
ROOT = Path(__file__).resolve().parents[1]
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        options = {"executable_path": str(LOCAL_CHROME)} if LOCAL_CHROME.exists() else {}
        browser = playwright.chromium.launch(headless=True, **options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))

        page.goto(f"{BASE}/people/glasgow-951.html", wait_until="networkidle")
        assert page.locator(".person-hero h1").inner_text() == "Alexander Glasgow"
        identity = page.locator("#overview .identity-facts")
        assert identity.is_visible()
        for label in ("PARENTS", "SPOUSES", "CHILDREN"):
            assert label in identity.inner_text()
        assert page.locator(".timeline-card").count() >= 2
        assert not page.locator("#timeline").get_attribute("open")
        assert not page.locator("#timeline .timeline-card").first.is_visible()
        page.locator("#timeline > summary").click()
        assert page.locator("#timeline .timeline-card").first.is_visible()
        assert not page.locator("#questions .question-card").first.is_visible()
        assert not page.locator("#research-update .research-finding").first.is_visible()
        assert not page.locator("#research-findings .finding-table").is_visible()
        tabs = page.locator("#candidate-analysis [role=tab]")
        comparison_context = page.locator("#overview .identity-comparison-context")
        assert tabs.count() == 2
        assert tabs.nth(0).inner_text().startswith("Potential parents")
        assert tabs.nth(1).inner_text().startswith("Possible duplicates")
        assert tabs.nth(0).get_attribute("aria-selected") == "true"
        assert comparison_context.is_visible()
        assert page.locator("#candidate-analysis > .similar-subject-summary").count() == 0
        assert page.locator("#potential-parentage .parentage-clues").count() == 0
        assert page.locator("#potential-parentage .parentage-card").first.is_visible()
        assert page.locator("#potential-parentage .fit-track").first.is_visible()
        assert "FACTOR BREADTH" in page.locator("#potential-parentage .parentage-card").first.inner_text()
        assert not page.locator("#similar-people").is_visible()
        tabs.nth(1).click()
        assert tabs.nth(1).get_attribute("aria-selected") == "true"
        assert not page.locator("#potential-parentage").is_visible()
        assert page.locator("#similar-people .similar-people-cards").is_visible()
        assert "PARENT COMPARISON" in page.locator("#similar-people .candidate-card").first.inner_text()
        assert "#similar-people" in page.url
        assert comparison_context.is_visible()
        assert "PATERNAL GRANDFATHER POSITION" in comparison_context.inner_text()
        assert "UNCERTAIN" in page.locator("#overview").inner_text()
        external_profile_link = page.locator('a[href^="https://www.wikitree.com/wiki/"]').first
        assert external_profile_link.get_attribute("target") == "_blank"
        assert {"noopener", "noreferrer"} <= set(external_profile_link.get_attribute("rel").split())
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-person-desktop.png"), full_page=True)

        page.goto(f"{BASE}/catalogue.html?q=Alexander", wait_until="networkidle")
        page.locator(".catalogue-results-table").wait_for(state="visible")
        assert page.locator("#catalogue-date-type").input_value() == ""
        assert page.locator("#catalogue-location-type").input_value() == ""
        assert page.locator('#catalogue-date-type option[value=""]').inner_text() == "Any record"
        assert page.locator('#catalogue-location-type option[value=""]').inner_text() == "Any record"
        headers = page.locator(".catalogue-results-table th").all_inner_texts()
        assert len(headers) == 8
        assert "Recorded in" not in headers and "Cluster" not in headers and "WikiTree" not in headers
        wikitree_link = page.locator(".catalogue-results-table tbody tr").first.locator(".catalogue-wikitree-id a")
        assert wikitree_link.is_visible()
        assert "wikitree.com/wiki/" in wikitree_link.get_attribute("href")
        assert wikitree_link.get_attribute("target") == "_blank"
        assert {"noopener", "noreferrer"} <= set(wikitree_link.get_attribute("rel").split())
        page.locator("#catalogue-group-locations").check()
        assert page.locator("#catalogue-location-level").is_enabled()
        assert not page.locator("#catalogue-group-families").is_checked()
        page.locator("#catalogue-location-level").select_option("2")
        location_groups = page.locator(".catalogue-location-path-group", has_text="County Antrim")
        assert location_groups.count() > 0
        assert "Ireland" in location_groups.first.inner_text()
        assert page.locator(".catalogue-country-group, .catalogue-area-group").count() == 0
        assert "groupLocation=1" in page.url and "locationLevel=2" in page.url
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-table-desktop.png"), full_page=False)
        page.locator("#catalogue-group-families").check()
        assert not page.locator("#catalogue-group-locations").is_checked()
        assert page.locator("#catalogue-location-level").is_disabled()
        assert page.locator(".catalogue-family-group").count() > 0
        assert page.locator(".catalogue-family-root-vitals", has_text="Born").count() > 0
        ancestor_link = page.locator('.catalogue-family-group a[href^="https://www.wikitree.com/wiki/"]').first
        assert ancestor_link.is_visible()
        assert ancestor_link.get_attribute("target") == "_blank"
        assert {"noopener", "noreferrer"} <= set(ancestor_link.get_attribute("rel").split())
        assert page.locator(".catalogue-family-unconnected", has_text="not a family branch").count() > 0
        assert page.locator('#catalogue-result-sort option[value="family:asc"]').count() == 0
        assert "groupFamily=1" in page.url and "groupLocation" not in page.url
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-family-group-desktop.png"), full_page=False)
        page.locator("#statistics-detail > summary").click()
        assert page.locator(".statistics-panel").count() == 6
        page.locator("#statistics").screenshot(path=str(ROOT / "artifacts" / "catalogue-statistics-desktop.png"))

        page.goto(f"{BASE}/catalogue.html?q=Glasgow-951&from=1851&to=1851", wait_until="networkidle")
        page.locator(".catalogue-results-table").wait_for(state="visible")
        assert page.locator(".catalogue-results-table tbody tr").count() == 1
        page.locator("#catalogue-date-type").select_option("birth")
        page.locator(".catalogue-results > .notice").wait_for(state="visible")
        assert "dateType=birth" in page.url
        page.locator("#catalogue-date-type").select_option("")
        page.locator(".catalogue-results-table").wait_for(state="visible")
        page.locator("#catalogue-date-from").fill("")
        page.locator("#catalogue-date-to").fill("")
        page.locator("#catalogue-location").fill("Lisnagaver")
        page.locator(".catalogue-results-table").wait_for(state="visible")
        assert page.locator(".catalogue-results-table tbody tr").count() == 1
        page.locator("#catalogue-location-type").select_option("birth")
        page.locator(".catalogue-results > .notice").wait_for(state="visible")
        assert "locationType=birth" in page.url
        page.locator("#catalogue-location-type").select_option("death")
        page.locator("#catalogue-location").fill("Glasgow")
        page.locator(".catalogue-results-table").wait_for(state="visible")
        assert page.locator(".catalogue-results-table tbody tr").count() == 1

        page.goto(f"{BASE}/records/", wait_until="networkidle", timeout=60_000)
        page.locator("#record-query").fill("Alexander Glasgow")
        page.locator(".record-card").first.wait_for(state="visible")
        assert page.locator(".record-card").count() > 0
        assert "q=Alexander+Glasgow" in page.url

        page.goto(f"{BASE}/places/", wait_until="networkidle")
        page.locator("#place-query").fill("Lisnagaver")
        page.locator(".place-result-card").first.wait_for(state="visible")
        assert page.locator(".place-result-card").count() == 1

        page.goto(f"{BASE}/compare.html?a=Glasgow-951&b=Glasgow-3904", wait_until="networkidle")
        page.locator(".compare-card").first.wait_for(state="visible")
        assert page.locator(".compare-card").count() == 3
        assert "Shared places" in page.locator(".compare-shared").inner_text()

        page.goto(f"{BASE}/candidate-matches.html?maxYear=1750", wait_until="networkidle")
        assert page.locator("#candidate-max-year").input_value() == "1750"
        assert "1750 or earlier" in page.locator("#candidate-filter-status").inner_text()
        visible_match_rows = page.locator('tr[data-match-kind]:not([hidden])')
        assert visible_match_rows.count() > 0
        assert page.locator('tr[data-match-kind][hidden]').count() > 0
        for index in range(visible_match_rows.count()):
            row = visible_match_rows.nth(index)
            years = [row.get_attribute("data-subject-year"), row.get_attribute("data-candidate-year")]
            assert all(not year or int(year) <= 1750 for year in years)
        page.locator("#candidate-parent-role").select_option("father")
        assert "parentRole=father" in page.url
        assert "father-only parentage" in page.locator("#candidate-filter-status").inner_text()
        visible_parent_rows = page.locator('tr[data-match-kind="parent"]:not([hidden])')
        assert visible_parent_rows.count() > 0
        for index in range(visible_parent_rows.count()):
            assert visible_parent_rows.nth(index).get_attribute("data-parent-role") == "father"
        page.locator("#candidate-max-clear").click()
        assert "maxYear" not in page.url
        assert "parentRole" not in page.url
        assert page.locator('tr[data-match-kind][hidden]').count() == 0

        page.goto(f"{BASE}/feedback.html?person=Glasgow-951", wait_until="networkidle")
        assert "Glasgow-951" in page.locator("#feedback-template").input_value()

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{BASE}/catalogue.html?q=Alexander&groupLocation=1&locationLevel=2", wait_until="networkidle")
        page.locator(".catalogue-result-cards").wait_for(state="visible")
        assert page.locator(".catalogue-result-cards .catalogue-location-path-group").count() > 0
        page.locator(".catalogue-result-toolbar").scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-groups-mobile.png"), full_page=False)
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth"), page.evaluate(
            "[...document.querySelectorAll('*')].filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth+1).slice(0,8).map(e=>[e.tagName,e.className,e.getBoundingClientRect().right])"
        )

        page.goto(f"{BASE}/records/?q=Alexander+Glasgow", wait_until="networkidle", timeout=60_000)
        page.locator(".record-card").first.wait_for(state="visible")
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-records-mobile.png"), full_page=False)

        page.goto(f"{BASE}/people/glasgow-951.html#potential-parentage", wait_until="networkidle")
        assert page.locator("#potential-parentage").is_visible()
        assert page.locator("#potential-parentage .candidate-card-grid").first.is_visible()
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        page.locator("#candidate-analysis").screenshot(path=str(ROOT / "artifacts" / "catalogue-candidates-mobile.png"))
        assert not errors, errors
        browser.close()
    print("Public-catalogue browser smoke test passed")


if __name__ == "__main__":
    main()
