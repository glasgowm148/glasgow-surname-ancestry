#!/usr/bin/env python3
"""Rendered smoke test for the catalogue one-tree grouping."""

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
        local_url = (ROOT / "www" / "catalogue.html").as_uri() + "?q=Alexander&groupTree=1&treePaths=1"
        page.goto(local_url, wait_until="load")
        page.locator(".catalogue-one-tree").wait_for(state="visible")
        page.locator(".catalogue-one-tree-summary strong", has_text="Connecting paths").wait_for()
        assert page.url.startswith((ROOT / "www" / "catalogue.html").as_uri())
        page.goto(f"{BASE}/catalogue.html", wait_until="networkidle")
        page.locator("#catalogue-glasgow-at-birth").check()
        filtered_count = int(page.locator(".catalogue-result-toolbar > strong").inner_text().split()[0].replace(",", ""))
        assert 0 < filtered_count < 4450
        assert "glasgowBirth=1" in page.url
        page.goto(f"{BASE}/catalogue.html", wait_until="networkidle")
        page.locator("#statistics-detail > summary").click()
        marriage_panel = page.locator(".statistics-panel", has_text="Surnames joined by marriage to Glasgow")
        cunningham = marriage_panel.get_by_role("link", name="Cunningham", exact=True)
        assert cunningham.locator("xpath=ancestor::li/strong").inner_text() == "9"
        cunningham.click()
        assert "marriageSurname=Cunningham" in page.url
        assert page.locator("#catalogue-spouse-name").input_value() == "Cunningham"
        assert page.locator(".catalogue-results-table tbody tr").count() == 9
        assert page.locator(".catalogue-results-table tbody", has_text="Margaret (Knox) Glasgow").count() == 0
        page.goto(f"{BASE}/catalogue?marriageSurname=Cunningham", wait_until="networkidle")
        assert page.locator("#catalogue-spouse-name").input_value() == "Cunningham"
        assert page.locator(".catalogue-results-table tbody tr").count() == 9
        page.goto(f"{BASE}/catalogue.html?q=Alexander", wait_until="networkidle")
        page.locator("#catalogue-group-tree").check()
        tree = page.locator(".catalogue-one-tree")
        assert tree.is_visible()
        result_count = int(page.locator(".catalogue-result-toolbar > strong").inner_text().split()[0].replace(",", ""))
        folded_spouses = int(tree.get_attribute("data-folded-spouses"))
        assert folded_spouses > 0
        assert int(tree.get_attribute("data-tree-nodes")) + folded_spouses == result_count
        assert page.locator(".catalogue-tree-direct-match").count() > 0
        page.locator(".catalogue-tree-display-options > summary").click()
        assert page.locator("#catalogue-tree-ancestors").is_visible()
        assert page.locator("#catalogue-tree-descendants").is_visible()
        initial_people = int(tree.get_attribute("data-tree-people"))
        page.locator("#catalogue-tree-ancestors").select_option("2")
        assert int(tree.get_attribute("data-tree-people")) >= initial_people
        page.locator(".catalogue-tree-display-options > summary").click()
        page.locator("#catalogue-tree-evidence").select_option("supported")
        assert "treeEvidence=supported" in page.url
        page.locator('[data-tree-action="expand-all"]').click()
        assert page.locator(".catalogue-tree-couple-node").count() > 0
        assert page.locator(".catalogue-tree-spouse-inline").count() > 0
        assert page.locator('[role="treeitem"][aria-level]').count() > 0
        folded_spouse = page.locator(".catalogue-tree-folded-spouse").first
        assert folded_spouse.is_visible()
        folded_id = folded_spouse.get_attribute("data-folded-spouse")
        assert page.locator(f'[data-tree-person="{folded_id}"]').count() == 0
        assert page.locator(".catalogue-tree-person > ol .catalogue-tree-person").count() > 0
        assert page.locator(".catalogue-tree-minimap button").count() > 0
        page.locator(".catalogue-tree-display-options > summary").click()
        page.locator("#catalogue-tree-parent").select_option("mother")
        assert "treeParent=mother" in page.url
        page.locator(".catalogue-tree-display-options > summary").click()
        page.locator("#catalogue-tree-overlay").select_option("missing-parent")
        assert page.locator(".catalogue-tree-overlay-hit").count() > 0
        page.locator(".catalogue-tree-display-options > summary").click()
        page.locator("#catalogue-tree-timeline").check()
        assert "is-timeline" in tree.get_attribute("class")
        assert page.locator(".catalogue-tree-timeline-axis").is_visible()
        page.locator(".catalogue-tree-display-options > summary").click()
        page.locator("#catalogue-tree-paths").check()
        page.locator(".catalogue-one-tree-summary strong", has_text="Connecting paths").wait_for()
        page.locator(".catalogue-tree-display-options > summary").click()
        assert page.locator("#catalogue-tree-ancestors").is_disabled()
        page.locator("#catalogue-tree-paths").uncheck()
        page.locator(".catalogue-one-tree-summary strong", has_text="One tree").wait_for()
        page.locator(".catalogue-tree-branch-actions > summary").nth(0).click()
        page.locator(".catalogue-tree-branch-actions[open] button[data-tree-pin]").click()
        page.locator(".catalogue-tree-branch-actions > summary").nth(1).click()
        page.locator(".catalogue-tree-branch-actions[open] button[data-tree-pin]").click()
        page.locator(".catalogue-tree-navigation > summary").click()
        assert page.locator(".catalogue-tree-pins > button").count() == 2
        assert page.locator(".catalogue-tree-pins a", has_text="Compare pinned people").is_visible()
        assert not page.locator("#catalogue-group-locations").is_checked()
        assert not page.locator("#catalogue-group-families").is_checked()
        assert "groupTree=1" in page.url
        toggle = page.locator(".catalogue-tree-toggle").first
        assert toggle.get_attribute("aria-expanded") == "true"
        toggle.click()
        assert toggle.get_attribute("aria-expanded") == "false"
        page.locator('[data-tree-action="expand-all"]').click()
        focus_menu = page.locator(".catalogue-tree-branch-actions").first
        focus_menu.locator(":scope > summary").click()
        focus_menu.locator("button[data-tree-focus]").click()
        assert "treeFocus=" in page.url
        assert page.locator(".catalogue-tree-clear-focus").is_visible()
        page.locator(".catalogue-tree-line").first.click()
        assert "Select a person" not in page.locator(".catalogue-tree-breadcrumb").inner_text()
        page.locator(".catalogue-tree-more > summary").click()
        page.locator("#catalogue-tree-compact").check()
        assert "is-compact" in tree.get_attribute("class")
        page.locator(".catalogue-tree-navigation > summary").click()
        assert page.locator(".catalogue-tree-history").is_visible()
        page.locator(".catalogue-tree-more > summary").click()
        page.locator(".catalogue-tree-export > summary").click()
        assert page.locator('button[data-tree-export="gedcom"]').is_visible()
        page.locator('button[data-tree-export="share"]').click()
        page.wait_for_function("document.querySelector('#catalogue-tree-announcer').textContent.toLowerCase().includes('copied')")
        for export_format, filename in (("html", "glasgow-tree.html"), ("svg", "glasgow-tree.svg"), ("gedcom", "glasgow-tree.ged")):
            with page.expect_download() as download_info:
                page.locator(f'button[data-tree-export="{export_format}"]').evaluate("button => button.click()")
            download = download_info.value
            assert download.suggested_filename == filename
            assert download.path().stat().st_size > 0
            if export_format == "gedcom":
                gedcom = download.path().read_text(encoding="utf-8")
                assert "0 HEAD" in gedcom and "0 TRLR" in gedcom
        page.evaluate("window.__treePrinted=false;window.print=()=>{window.__treePrinted=true}")
        page.locator('button[data-tree-export="print"]').evaluate("button => button.click()")
        assert page.evaluate("window.__treePrinted")
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-one-tree-desktop.png"))

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.goto(
            f"{BASE}/catalogue.html?q=Alexander&groupTree=1&treeAncestors=1",
            wait_until="networkidle",
        )
        mobile.locator(".catalogue-one-tree").wait_for(state="visible")
        assert mobile.locator("#catalogue-tree-compact").is_checked()
        assert mobile.locator("#catalogue-tree-expand-depth").input_value() == "1"
        assert mobile.locator(".catalogue-tree-tools").is_visible()
        mobile.locator(".catalogue-tree-help > summary").click()
        assert mobile.locator(".catalogue-tree-legend").is_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        mobile.screenshot(path=str(ROOT / "artifacts" / "catalogue-one-tree-mobile.png"), full_page=True)

        large = browser.new_page(viewport={"width": 1200, "height": 800})
        large.on("pageerror", lambda error: errors.append(str(error)))
        large.goto(f"{BASE}/catalogue.html?q=Glasgow&groupTree=1&treeExpand=all", wait_until="networkidle")
        large.locator(".catalogue-tree-virtual-notice").wait_for(state="visible")
        before = large.locator(".catalogue-tree-person").count()
        assert before <= 600
        large.locator('[data-tree-action="load-more"]').click()
        assert large.locator(".catalogue-tree-person").count() > before
        assert not errors, errors
        browser.close()
    print("Catalogue one-tree browser smoke test passed")


if __name__ == "__main__":
    main()
