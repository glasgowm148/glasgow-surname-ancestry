#!/usr/bin/env python3
"""Rendered regression test for the catalogue search toolbar and filter panels.

Run against a local static server of ``www/`` (``python -m http.server 8765 -d www``):

    CATALOGUE_TEST_BASE=http://127.0.0.1:8765 .venv/bin/python tests/test_catalogue_toolbar_ui.py
"""

import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CATALOGUE_TEST_BASE", "http://127.0.0.1:8765")
ROOT = Path(__file__).resolve().parents[1]
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PANELS = ("name", "relatives", "dates", "places", "evidence", "filters", "wikitree")
HEADERS = ["Individual", "Birth", "Birth location", "Death", "Death location", "Spouse(s)", "Father", "Mother"]

ROWS_JS = """() => [...document.querySelectorAll('#catalogue-results .catalogue-results-table tbody tr td:first-child > a')]
  .map(link => new URL(link.href).pathname.split('/').pop())"""


def settle(page):
    page.wait_for_timeout(220)  # search input debounce is 160 ms
    page.wait_for_function("() => document.querySelector('#catalogue-results-count').dataset.state !== 'busy'")


def rows(page):
    return page.evaluate(ROWS_JS)


def result_total(page):
    """Result total from the toolbar (rows are paginated)."""
    text = page.locator(".catalogue-result-toolbar > strong").inner_text() if page.locator(".catalogue-result-toolbar > strong").count() else "0"
    return int(re.sub(r"[^0-9]", "", text) or 0)


def chips(page):
    return page.locator("#catalogue-applied-list .catalogue-chip-text").all_inner_texts()


def params(page):
    return page.evaluate("() => Object.fromEntries(new URLSearchParams(location.search))")


def load(page, query="", path="/catalogue.html"):
    page.goto(f"{BASE}{path}{('?' + query) if query else ''}", wait_until="networkidle")
    settle(page)


def open_panels(page):
    return [key for key in PANELS if page.locator(f"#catalogue-filter-panel-{key}").is_visible()]


def surname_count(scope_key, surname):
    index = json.loads((ROOT / "www/data/catalogue-search-index.json").read_text(encoding="utf-8"))
    return sum(1 for person in index if surname in " ".join(person.get(scope_key) or []).lower())


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        options = {"executable_path": str(LOCAL_CHROME)} if LOCAL_CHROME.exists() else {}
        browser = playwright.chromium.launch(headless=True, **options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))

        # Clean default view: header total from the loaded index, all panels closed, no chips.
        load(page)
        total = len(json.loads((ROOT / "www/data/catalogue-search-index.json").read_text(encoding="utf-8")))
        assert page.locator("#catalogue-total").inner_text() == f"{total:,}"
        assert f"Search {total:,} historical people" in page.locator(".catalogue-hero .lede").inner_text()
        labels = page.locator(".catalogue-filter-toggle > span:first-child").all_inner_texts()
        assert labels == ["Name", "Relatives", "Dates", "Places", "Evidence", "Filters", "WikiTree"], labels
        assert open_panels(page) == []
        assert chips(page) == [] and page.locator("#catalogue-search-clear").is_hidden()
        assert page.locator(".catalogue-filter-count:visible").count() == 0
        assert page.locator(".catalogue-advanced, .catalogue-search-footer").count() == 0
        # Every control is discoverable in its named panel.
        placement = {
            "name": ("catalogue-first-name", "catalogue-last-name", "catalogue-last-scope", "catalogue-name", "catalogue-exact-name"),
            "relatives": ("catalogue-spouse-name", "catalogue-father-name", "catalogue-mother-name", "catalogue-child-name", "catalogue-sibling-name"),
            "dates": ("catalogue-date-type", "catalogue-date-from", "catalogue-date-to"),
            "places": ("catalogue-location-type", "catalogue-location", "catalogue-region", "catalogue-death-exclude"),
            "evidence": ("catalogue-cluster", "catalogue-record-type", "catalogue-source-quality"),
            "filters": ("catalogue-glasgow-at-birth", "catalogue-women-married-glasgow", "catalogue-has-suffix",
                        "catalogue-missing-father", "catalogue-missing-mother", "catalogue-has-descendants"),
            "wikitree": ("catalogue-missing-profile", "catalogue-needs-wikitree-update"),
        }
        for key, ids in placement.items():
            for control_id in ids:
                assert page.locator(f"#catalogue-filter-panel-{key} #{control_id}").count() == 1, (key, control_id)
        assert page.locator("#catalogue-filter-panel-name input[name=catalogue-gender]").count() == 3
        assert page.locator("#catalogue-exact-name").count() == 1

        # Panels: one open at a time, Escape closes and returns focus, values survive closing.
        page.click("#catalogue-filter-toggle-name")
        assert open_panels(page) == ["name"]
        assert page.get_attribute("#catalogue-filter-toggle-name", "aria-expanded") == "true"
        assert page.evaluate("document.activeElement.id") == "catalogue-first-name"
        page.keyboard.type("James")
        page.keyboard.press("Escape")
        settle(page)
        assert open_panels(page) == [] and page.evaluate("document.activeElement.id") == "catalogue-filter-toggle-name"
        assert page.input_value("#catalogue-first-name") == "James"
        assert chips(page) == ["First name: James"] and params(page)["first"] == "James"
        page.keyboard.press("Enter")  # keyboard opens the focused toggle
        assert open_panels(page) == ["name"]
        page.click("#catalogue-filter-toggle-dates")
        assert open_panels(page) == ["dates"]
        page.click("#catalogue-results")  # outside click closes
        assert open_panels(page) == [] and page.input_value("#catalogue-first-name") == "James"

        # Split names are additive and match the legacy first/last URL search exactly.
        page.click("#catalogue-filter-toggle-name")
        page.fill("#catalogue-last-name", "Glasgow")
        page.get_by_role("radio", name="Male", exact=True).check()
        settle(page)
        split_rows = rows(page)
        assert params(page)["first"] == "James" and params(page)["last"] == "Glasgow" and params(page)["gender"] == "male"
        load(page, "first=james&last=glasgow&gender=male")
        assert rows(page) == split_rows and result_total(page) == 235 and len(split_rows) == 50
        assert page.input_value("#catalogue-first-name") == "james"
        assert page.is_checked('input[name=catalogue-gender][value=male]')

        # Surname scope: unset has no effect; birth/current follow structured surname data.
        load(page, "q=Alexander")
        alexander = rows(page)
        load(page, "q=Alexander&lastScope=birth")
        assert rows(page) == alexander and "lastScope" not in params(page)
        for scope, key in (("birth", "last_names_at_birth"), ("current", "last_names_current")):
            load(page, f"last=Smith&lastScope={scope}")
            expected = surname_count(key, "smith")
            assert result_total(page) == expected, (scope, result_total(page), expected)
            assert params(page)["lastScope"] == scope
        assert chips(page) == ["Current/last surname: Smith"]

        # Gender with Glasgow at birth and another recorded surname stay independent.
        load(page)
        page.click("#catalogue-filter-toggle-name")
        page.fill("#catalogue-last-name", "Smith")
        page.get_by_role("radio", name="Female", exact=True).check()
        page.click("#catalogue-filter-toggle-filters")
        page.check("#catalogue-glasgow-at-birth")
        settle(page)
        combined = rows(page)
        load(page, "gender=female&glasgowBirth=1&last=Smith")
        assert rows(page) == combined and len(combined) == 11 and result_total(page) == 11
        assert page.locator("#catalogue-filter-toggle-name .catalogue-filter-count").inner_text().startswith("2")
        assert page.locator("#catalogue-filter-toggle-filters .catalogue-filter-count").inner_text().startswith("1")
        assert set(chips(page)) == {"Last name: Smith", "Gender: Female", "Glasgow at birth"}
        load(page, "males=1")
        assert page.is_checked('input[name=catalogue-gender][value=male]') and chips(page) == ["Gender: Male"]

        # Relatives: repeatable rows over the existing single-value criteria.
        load(page)
        page.click("#catalogue-filter-toggle-relatives")
        assert page.locator(".catalogue-relative-row:not([hidden])").count() == 1
        assert page.input_value("#catalogue-relative-type-spouse") == "spouse"
        page.fill("#catalogue-spouse-name", "Smith")
        page.click("#catalogue-add-relative")
        page.fill("#catalogue-father-name", "John")
        settle(page)
        assert params(page)["spouse"] == "Smith" and params(page)["father"] == "John"
        assert result_total(page) == 4
        assert page.locator("#catalogue-relative-type-father option[value=spouse]").is_disabled()
        page.select_option("#catalogue-relative-type-father", "mother")
        settle(page)
        assert "father" not in params(page) and params(page)["mother"] == "John" and params(page)["spouse"] == "Smith"
        page.locator('.catalogue-relative-row[data-relation="spouse"] [data-relative-remove]').click()
        settle(page)
        assert "spouse" not in params(page) and params(page)["mother"] == "John"
        assert chips(page) == ["Mother: John"]
        for _ in range(4):
            page.click("#catalogue-add-relative")
        assert page.locator(".catalogue-relative-row:not([hidden])").count() == 5 and page.is_disabled("#catalogue-add-relative")
        load(page, "child=James&sibling=Mary")
        assert page.locator(".catalogue-relative-row:not([hidden])").count() == 2
        assert set(chips(page)) == {"Child: James", "Sibling: Mary"}

        # Chips: meaningful labels, reopen their panel, remove only one condition.
        load(page, "dateType=birth&from=1800&to=1830&location=Antrim&excludeDeath=USA")
        assert chips(page) == ["Birth: 1800–1830", "Location: Antrim", "Death location excludes: USA"], chips(page)
        assert len(rows(page)) > 0
        page.get_by_role("button", name="Remove filter: Location: Antrim").click()
        settle(page)
        after_remove = rows(page)
        assert "location" not in params(page) and params(page)["excludeDeath"] == "USA" and params(page)["from"] == "1800"
        assert page.evaluate("document.activeElement.textContent") == "×"
        load(page, "dateType=birth&from=1800&to=1830&excludeDeath=USA")
        assert rows(page) == after_remove
        page.get_by_role("button", name="Birth: 1800–1830", exact=True).click()
        assert open_panels(page) == ["dates"]
        load(page, "to=1650")
        assert chips(page) == ["Any date: 1650 or earlier"]

        # Marriage-surname links and exact birth surname are represented and removable.
        load(page, "marriageSurname=Smith")
        assert chips(page) == ["Glasgow-born, spouse’s surname: Smith"] and result_total(page) == 24
        page.get_by_role("button", name="Remove filter: Glasgow-born, spouse’s surname: Smith").click()
        settle(page)
        assert page.input_value("#catalogue-spouse-name") == "" and chips(page) == []
        # With no filters left the whole catalogue is browsable, A–Z.
        assert page.locator("#catalogue-results-count").inner_text().startswith("Browsing all") and len(rows(page)) == 50
        load(page, "birthSurname=Glasgow")
        assert chips(page) == ["Surname at birth (exact): Glasgow"] and page.locator(".catalogue-results-table").count() == 1

        # Legacy combined name, exact spelling, evidence and WikiTree filters.
        load(page, "name=John+Glasgow")
        assert page.input_value("#catalogue-name") == "John Glasgow" and chips(page) == ["Full name: John Glasgow"]
        assert result_total(page) == 303
        load(page, "q=Glasco&exact=1")
        assert chips(page) == ["Exact name spelling"] and result_total(page) == 191
        load(page, "q=Glasco")
        assert result_total(page) > 191  # variants expand to Glasgow
        load(page, "quality=original&recordType=Marriages&needsUpdate=1&missingProfile=1")
        assert set(chips(page)) == {"Source quality: Original record", "Record type: Marriages",
                                    "No confirmed WikiTree link", "Needs updated on WikiTree"}
        assert page.locator("#catalogue-filter-toggle-wikitree .catalogue-filter-count").inner_text().startswith("2")
        load(page, "missingFather=1&missingMother=1&region=Scotland")
        assert result_total(page) == 432 and set(chips(page)) == {"Missing father", "Missing mother", "Country or region: Scotland"}
        load(page, "descendants=1&suffix=1")
        assert set(chips(page)) == {"Has descendants", "Has suffix"}

        # Clear all restores defaults without touching grouping.
        load(page, "q=Alexander&region=Ireland&gender=female&groupLocation=1&locationLevel=2")
        assert page.locator(".catalogue-location-path-group").count() > 0
        page.click("#catalogue-search-clear")
        settle(page)
        assert chips(page) == [] and page.input_value("#catalogue-query") == ""
        assert params(page) == {"groupLocation": "1", "locationLevel": "2"}, params(page)
        assert page.is_checked('input[name=catalogue-gender][value=both]')

        # Table, sorting, grouping, refresh and history.
        load(page, "q=Alexander")
        headers = [text.rstrip("↕↑↓ \n") for text in page.locator(".catalogue-results-table th").all_inner_texts()]
        assert headers == HEADERS, headers
        assert page.locator("#catalogue-results img").count() == 0
        # WikiTree IDs and relatives open in a new tab and never replace the search.
        targets = page.evaluate("[...document.querySelectorAll('#catalogue-results a[href*=wikitree]')].map(a => a.target + ' ' + a.rel)")
        assert targets and set(targets) == {"_blank noopener noreferrer"}, set(targets)
        assert page.locator(".catalogue-result-table-wrap").is_visible() and page.locator(".catalogue-result-cards").is_hidden()
        page.click('button[data-sort="birth"]')
        settle(page)
        assert params(page)["sort"] == "birth:asc"
        page.check("#catalogue-group-families")
        assert page.locator(".catalogue-family-group").count() > 0 and params(page)["groupFamily"] == "1"
        page.reload(wait_until="networkidle")
        settle(page)
        assert page.is_checked("#catalogue-group-families") and page.input_value("#catalogue-query") == "Alexander"
        load(page, "q=Glasco&exact=1")
        page.go_back(wait_until="networkidle")
        settle(page)
        assert page.input_value("#catalogue-query") == "Alexander" and params(page)["groupFamily"] == "1"
        page.go_forward(wait_until="networkidle")
        settle(page)
        assert page.is_checked("#catalogue-exact-name")

        # Default browse view, pagination and page-reset rules, history.
        load(page)
        assert result_total(page) == len(json.loads((ROOT / "www/data/catalogue-search-index.json").read_text(encoding="utf-8")))
        assert len(rows(page)) == 50 and "sort" not in params(page)
        first_page = rows(page)
        page.click('.catalogue-pagination button[data-page="2"]')
        settle(page)
        assert params(page)["page"] == "2" and rows(page) != first_page and len(rows(page)) == 50
        page.go_back(wait_until="networkidle")
        settle(page)
        assert "page" not in params(page) and rows(page) == first_page
        page.go_forward(wait_until="networkidle")
        settle(page)
        assert params(page)["page"] == "2"
        page.select_option("#catalogue-per-page", "100")
        settle(page)
        assert params(page)["perPage"] == "100" and "page" not in params(page) and len(rows(page)) == 100
        load(page, "q=Glasgow&page=3")
        assert page.locator(".catalogue-page.is-current").inner_text() == "3"
        page.fill("#catalogue-query", "Glasgow James")
        settle(page)
        assert "page" not in params(page)  # filter changes return to page 1
        load(page, "region=Ireland")
        page.click("#catalogue-filter-toggle-filters")
        page.check("#catalogue-missing-father")
        settle(page)
        page.go_back(wait_until="networkidle")
        settle(page)
        assert not page.is_checked("#catalogue-missing-father") and chips(page) == ["Country or region: Ireland"]

        # Empty results and load failure.
        load(page, "q=Zzyzxnomatch")
        assert "No catalogue match" in page.locator("#catalogue-results .notice").inner_text()
        failing = browser.new_page(viewport={"width": 1440, "height": 1000})
        failing.route("**/catalogue-search-index.json", lambda route: route.fulfill(status=500, body="error"))
        failing.goto(f"{BASE}/catalogue/?q=Alexander", wait_until="networkidle")
        failing.locator("#catalogue-results .notice").wait_for()
        assert failing.locator("#catalogue-results-count").inner_text() == "Search unavailable"
        failing.close()

        # Unified /catalogue/ route uses the same interface.
        load(page, "q=Alexander&region=Ireland", path="/catalogue/")
        assert chips(page) == ["Country or region: Ireland"]
        page.click("#catalogue-filter-toggle-filters")
        page.screenshot(path=str(ROOT / "artifacts" / "catalogue-toolbar-filters-desktop.png"))
        box = page.locator("#catalogue-filter-panel-filters").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 1440

        # Narrow screens: the same panels become a sheet; the table scrolls horizontally.
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        load(mobile, "q=Alexander&region=Ireland", path="/catalogue/")
        assert mobile.locator(".catalogue-results-table th").count() == 8
        wrap = mobile.locator(".catalogue-result-table-wrap")
        assert wrap.is_visible() and mobile.locator(".catalogue-result-cards").is_hidden()
        assert wrap.evaluate("element => element.scrollWidth > element.clientWidth")
        assert mobile.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        mobile.click("#catalogue-filter-toggle-places")
        sheet = mobile.locator("#catalogue-filter-panel-places")
        assert sheet.get_attribute("role") == "dialog" and sheet.get_attribute("aria-modal") == "true"
        assert mobile.locator(".catalogue-filter-backdrop").is_visible()
        box = sheet.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390 and box["y"] + box["height"] <= 844 + 1
        mobile.screenshot(path=str(ROOT / "artifacts" / "catalogue-toolbar-sheet-mobile.png"))
        mobile.keyboard.press("Escape")
        assert sheet.is_hidden() and mobile.locator(".catalogue-filter-backdrop").is_hidden()
        assert mobile.input_value("#catalogue-region") == "Ireland"
        browser.close()
    assert not errors, errors
    print("Catalogue toolbar browser regression test passed")


if __name__ == "__main__":
    main()
