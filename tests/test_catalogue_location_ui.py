#!/usr/bin/env python3
"""Exercise location scopes and compact parent status with isolated browser data."""
import copy
import json
import os
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("CATALOGUE_TEST_BASE", "http://127.0.0.1:8765")


def main():
    seed = json.loads((ROOT / "www/data/catalogue-search-index.json").read_text())[0]
    rows = []
    for index, scope in enumerate(("birth", "death", "marriage", "bio", "record", "other")):
        row = copy.deepcopy(seed)
        row.update(id=f"example-{scope}", name=f"Example {scope}", profile_ids=[],
                   birth_location="", death_location="", locations=[], location_aliases=[],
                   regions=[], recorded_in=[], spouses=[], father=[], mother=[],
                   marriage_locations=[], biography_text="", missing_profile=scope == "other",
                   needs_wikitree_update=scope == "bio", first_names=["Example"],
                   last_names_at_birth=[scope], last_names_current=[scope])
        if scope in ("birth", "death"):
            row[f"{scope}_location"] = "Seedstone"
            row["locations"] = ["Seedstone"]
        elif scope == "marriage":
            row["marriage_locations"] = ["Seedstone"]
        elif scope == "bio":
            row["biography_text"] = "She worked in Seedstone before moving overseas."
        elif scope == "record":
            row["locations"] = ["Seedstone"]
        row["father"] = [{"id": "Example-100", "name": "Parent Example",
                          "certainty": "confident" if index % 2 else "unmarked"}]
        rows.append(row)
    with sync_playwright() as playwright:
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        browser = playwright.chromium.launch(headless=True, **({"executable_path": str(chrome)} if chrome.exists() else {}))
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/catalogue-search-index.json", lambda route: route.fulfill(json=rows))

        def load(**filters):
            page.goto(f"{BASE}/catalogue/?{urlencode(filters)}", wait_until="networkidle")
            page.locator('#catalogue-results-count[data-state="ready"]').wait_for()

        def names():
            return page.locator('.catalogue-results-table tbody td:first-child > a').all_text_contents()

        for scope, expected in (("", 5), ("record", 3), ("birth", 1), ("death", 1), ("marriage", 1), ("bio", 1)):
            load(location="Seedstone", locationType=scope)
            assert len(names()) == expected, (scope, names())
            if expected == 1:
                assert names() == [f"Example {scope}"]
        # Exclusion follows the same scope, including when the selected field is empty.
        load(excludeLocation="Seedstone", locationType="marriage")
        assert len(names()) == 5 and "Example marriage" not in names()
        load(excludeLocation="Seedstone")
        assert names() == ["Example other"]
        load(excludeDeath="Seedstone")
        assert page.locator("#catalogue-location-type").input_value() == "death"
        assert len(names()) == 5 and "Example death" not in names()
        load()
        assert page.locator('.catalogue-parent-cell.confidence-unmarked').count() == 3
        assert page.locator('.catalogue-relation-status.confidence-confident').first.inner_text() == "✓"
        assert page.locator('.catalogue-relation-status.confidence-confident').first.get_attribute("aria-label") == "Tree-marked confident"
        assert "Unassessed tree link" not in page.locator("#catalogue-results").inner_text()
        for label, name in (("No WikiTree link", "Example other"), ("WikiTree updates", "Example bio")):
            link = page.locator('.g-section-subnav').get_by_role("link", name=label, exact=True)
            link.click()
            page.locator('#catalogue-results-count[data-state="ready"]').wait_for()
            assert names() == [name]
            active = page.locator('.g-section-subnav a[aria-current="location"]')
            assert active.inner_text() == label
            assert active.get_attribute("title")
            page.locator('.catalogue-sort[data-sort="name"]').click()
            page.wait_for_function("location.search.includes('sort=')")
            assert active.inner_text() == label
        assert not errors, errors
        browser.close()
    print("Location scopes, exclusions, sidebar queues and parent indicators passed.")


if __name__ == "__main__":
    main()
