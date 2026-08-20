#!/usr/bin/env python3
"""Headless smoke test for the interactive family map."""

from pathlib import Path

from playwright.sync_api import sync_playwright


MAP_URL = (Path(__file__).resolve().parents[1] / "www" / "map" / "index.html").as_uri()
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> None:
    errors = []
    with sync_playwright() as playwright:
        launch_options = {"executable_path": str(LOCAL_CHROME)} if LOCAL_CHROME.exists() else {}
        browser = playwright.chromium.launch(headless=True, **launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(MAP_URL, wait_until="networkidle", timeout=45_000)

        page.locator("#year-filter-status").wait_for(state="visible")
        assert page.locator("#year-filter-number").get_attribute("max") == "2001"
        assert page.locator("#location-list li").count() > 0
        assert page.locator(".marker-cluster").count() > 0
        for retained_profile in ("Glasgow-2712", "Garvin-1831", "Glasgow-3667"):
            page.locator("#location-search").fill(retained_profile)
            assert page.locator("#location-list li").count() > 0
        page.locator("#location-search").fill("")
        assert page.locator("#cluster-filters input").count() >= 10
        assert page.locator('#cluster-filters input[value="Associated person"]').count() == 0
        assert page.locator("summary", has_text="What is included?").count() == 1
        assert page.locator('.project-links a[href="../index.html"]').count() == 1
        assert page.locator('.project-links a[href="../timeline.html"]').count() == 1
        assert page.locator("#location-panel").is_visible()
        page.locator("#sidebar-close").click()
        assert "sidebar-collapsed" in page.locator("body").get_attribute("class")
        assert page.locator("#sidebar-open").is_visible()
        page.locator("#sidebar-open").click()
        assert "sidebar-collapsed" not in (page.locator("body").get_attribute("class") or "")

        ydna_toggle = page.locator("#show-ydna")
        assert not ydna_toggle.is_checked()
        ydna_toggle.check()
        assert "ydna=1" in page.url
        assert page.locator(".ydna-stage-marker").count() == 15
        assert page.locator("path.ydna-path").count() == 1
        page.locator(".ydna-stage-marker").first.click()
        assert "Shum Laka" in page.locator(".ydna-popup").inner_text()
        assert "ancestral birthplace unknown" in page.locator(".ydna-popup").inner_text()
        ydna_toggle.uncheck()
        assert page.locator(".ydna-stage-marker").count() == 0

        early_toggle = page.locator("#show-early-bearers")
        assert not early_toggle.is_checked()
        early_toggle.check()
        assert "earlyBearers=1" in page.url
        page.wait_for_timeout(500)
        assert page.locator(".early-bearer-marker").count() + page.locator(".early-bearer-cluster").count() > 0
        early_markers = page.locator(".early-bearer-marker")
        assert early_markers.count() > 0
        early_markers.first.click()
        bearer_popup = page.locator(".early-bearer-popup")
        assert bearer_popup.is_visible()
        bearer_link = bearer_popup.locator("a")
        assert "Space:Bearers_of_the_" in bearer_link.get_attribute("href")
        early_toggle.uncheck()
        assert page.locator(".early-bearer-marker").count() == 0
        assert page.locator(".early-bearer-cluster").count() == 0

        page.locator("#year-filter-1800s").click()
        assert "from=1800" in page.url
        assert "1800–1900" in page.locator("#year-filter-status").inner_text()
        page.locator("#year-filter-latest").click()

        from_box = page.locator("#year-filter-from")
        through_box = page.locator("#year-filter-number")
        from_box.fill("")
        from_box.type("1750")
        assert from_box.input_value() == "1750"
        assert page.locator("#year-filter-from-slider").input_value() == "1750"
        through_box.fill("")
        through_box.type("1825")
        assert through_box.input_value() == "1825"
        assert page.locator("#year-filter-slider").input_value() == "1825"
        assert "1750–1825" in page.locator("#year-filter-status").inner_text()
        page.locator("#year-filter-latest").click()

        page.locator("summary", has_text="Research tools").click()
        all_basis_locations = page.locator("#location-list li").count()
        page.locator("#record-kind").select_option("profiles")
        assert "basis=profiles" in page.url
        assert 0 < page.locator("#location-list li").count() < all_basis_locations
        page.locator("#record-kind").select_option("records")
        assert "basis=records" in page.url
        assert page.locator("#location-list li").count() > 0
        page.locator("#record-kind").select_option("both")

        page.locator("#movement-person").fill("Glasgow-3902")
        page.locator("#show-movement-paths").check()
        assert page.locator("path.movement-line").count() == 1
        assert "movement=Glasgow-3902" in page.url
        page.locator("#show-movement-paths").uncheck()
        page.locator("#movement-person").fill("")
        page.locator("#movement-root").select_option("Glasgow-3904")
        page.locator("#show-movement-paths").check()
        assert page.locator("path.movement-line").count() > 0
        assert "movementRoot=Glasgow-3904" in page.url
        page.locator("#show-movement-paths").uncheck()
        page.locator("#movement-root").select_option("")

        page.locator("#compare-root-a").select_option("Glasgow-3904")
        page.locator("#compare-root-b").select_option("Glasgow-822")
        comparison_text = page.locator("#comparison-result").inner_text()
        assert "Shared places:" in comparison_text
        assert "none within current filters" not in comparison_text

        page.locator("#display-table").click()
        assert "display=table" in page.url
        assert page.locator("#research-table-panel").is_visible()
        assert "table-mode" in (page.locator("body").get_attribute("class") or "")
        all_table_people = page.locator("#research-table .individual-table-row").count()
        assert all_table_people >= 1720
        assert page.locator(".cluster-group-row", has_text="Recent WikiTree profile additions").count() == 1
        tyrone_supplement = page.locator('tr[data-individual="Glasgow-3962"]')
        assert tyrone_supplement.count() == 1
        assert tyrone_supplement.locator(".table-birth").inner_text() == "c. 1725"
        assert tyrone_supplement.locator(".table-birth-location").inner_text() == "County Tyrone, Ireland"
        assert page.locator('tr[data-individual="Glasgow-3956"]').count() == 1
        william_james = page.locator('tr[data-individual="Glasgow-1421"]')
        assert william_james.count() == 1
        assert william_james.locator(".table-birth").inner_text() == "1870-05-09"
        assert "Ballymoney" in william_james.locator(".table-birth-location").inner_text()
        for retained_profile in ("Glasgow-2712", "Garvin-1831", "Glasgow-3667"):
            page.locator("#location-search").fill(retained_profile)
            assert page.locator("#research-table .individual-table-row").count() > 0
        page.locator("#location-search").fill("")
        assert page.locator("#research-table .cluster-group-row").count() > 0
        assert page.locator(".cluster-group-row", has_text="Associated person").count() == 0
        james_root_href = 'a.cluster-link[href="https://www.wikitree.com/wiki/Glasgow-1025"]'
        assert page.locator(".cluster-group-row " + james_root_href).count() == 1
        assert page.locator(".cluster-group-row", has_text="J1700").count() == 1
        assert page.locator('#research-table th[data-sort="cluster"]').inner_text() == "Cluster"
        assert page.locator('#research-table th[data-sort="spouse"]').inner_text() == "Spouse(s)"
        assert page.locator('#research-table th[data-sort="father"]').inner_text() == "Father"
        assert page.locator('#research-table th[data-sort="mother"]').inner_text() == "Mother"
        assert page.locator("#research-table .table-cluster " + james_root_href).count() > 0
        assert page.locator("#research-table .table-cluster").first.evaluate(
            "cell => getComputedStyle(cell).backgroundColor !== 'rgba(0, 0, 0, 0)'"
        )
        assert page.locator("#research-table th[data-sort=person]").count() == 1
        assert page.locator('#research-table th[data-sort="birth"]').inner_text() == "Birth"
        assert page.locator('#research-table th[data-sort="birth_location"]').inner_text() == "Birth location"
        assert page.locator('#research-table th[data-sort="death"]').inner_text() == "Death"
        assert page.locator('#research-table th[data-sort="death_location"]').inner_text() == "Death location"
        assert page.locator('#research-table th[data-sort="recorded_location"]').inner_text() == "Recorded in"
        assert page.locator('#research-table th[data-sort="suffix"]').inner_text() == "Suffix"
        assert "sort-active" in (page.locator('#research-table th[data-sort="person"]').get_attribute("class") or "")
        assert page.locator('#research-table th[data-column="person"]').evaluate("cell => getComputedStyle(cell).position") == "sticky"
        assert any(
            value != "—"
            for value in page.locator("#research-table .table-descendants").all_inner_texts()
        )
        page.locator("#table-missing-parents").check()
        assert 0 < page.locator("#research-table .individual-table-row").count() < all_table_people
        assert page.locator('tr[data-individual="Glasgow-3903"]').count() == 0
        page.locator("#table-missing-parents").uncheck()
        page.locator("#table-missing-vital-location").check()
        assert 0 < page.locator("#research-table .individual-table-row").count() < all_table_people
        page.locator("#table-missing-vital-location").uncheck()
        page.locator("#table-estimated-location").check()
        assert 0 < page.locator("#research-table .individual-table-row").count() < all_table_people
        page.locator("#table-estimated-location").uncheck()
        page.locator("#location-search").fill("Glasgow-3941")
        assert page.locator("#research-table .individual-table-row").count() == 1
        page.locator("#location-search").fill("")
        page.locator("#table-has-descendants").check()
        assert all(int(value.replace(",", "")) > 0 for value in page.locator("#research-table .table-descendants").all_inner_texts())
        page.locator("#table-has-descendants").uncheck()
        page.locator("#table-has-profile").check()
        assert page.locator("#research-table .individual-table-row").count() < all_table_people
        assert all(value != "—" for value in page.locator('#research-table td[data-column="profile_id"]').all_inner_texts())
        page.locator("#table-has-profile").uncheck()
        page.locator("#table-women-married-glasgow").check()
        wives_count = page.locator("#research-table .individual-table-row").count()
        assert wives_count > 0
        assert page.locator("#research-table tbody").evaluate(
            "tbody => { const variants=new Set(['glasgow','glasco','glassco','glascoe','glasgo','glasow','glascow','glasoe','glassgow','glassgo','glasko']); return [...tbody.querySelectorAll('.individual-table-row')].every(row => row.querySelector('.table-spouses').textContent.toLowerCase().split(/[^a-z]+/).some(word => variants.has(word))); }"
        )
        page.locator("#table-women-married-glasgow").uncheck()
        page.locator("#table-has-suffix").check()
        assert page.locator("#research-table .individual-table-row").count() > 0
        assert all(value != "—" for value in page.locator("#research-table .table-suffix").all_inner_texts())
        page.locator("#table-has-suffix").uncheck()
        page.locator("#table-column-picker > summary").click()
        father_column_toggle = page.locator('#table-column-picker input[value="father"]')
        father_column_toggle.uncheck()
        assert page.locator('#research-table th[data-column="father"]').is_hidden()
        assert "hideColumns=father" in page.url
        page.locator('#table-column-picker button[data-columns="all"]').click()
        assert page.locator('#research-table th[data-column="father"]').is_visible()
        page.locator("#table-column-picker > summary").click()
        assert not page.locator("#table-group-locations").is_checked()
        assert page.locator("#table-location-level").is_disabled()
        assert page.locator("#table-location-level").input_value() == "3"
        assert page.locator("#table-toggle-location-groups").is_disabled()
        page.locator("#table-group-locations").check()
        assert page.locator("#table-location-level").is_enabled()
        bulk_location_toggle = page.locator("#table-toggle-location-groups")
        assert bulk_location_toggle.is_enabled()
        assert bulk_location_toggle.inner_text() == "Collapse all"
        assert page.locator("#research-table .cluster-group-row").count() > 0
        assert page.locator("#research-table .country-group-row").count() > 0
        assert page.locator("#research-table .county-group-row").count() > 0
        assert page.locator("#research-table .location-group-row").count() > 0
        assert page.locator(".location-group-row", has_text="Inishrush").count() > 0
        assert "famil" in page.locator("#research-table .country-group-row").first.inner_text()
        assert "emigrant" in page.locator("#research-table .county-group-row").first.inner_text()
        expanded_location_people = page.locator("#research-table .individual-table-row").count()
        bulk_location_toggle.click()
        assert bulk_location_toggle.inner_text() == "Expand all"
        assert page.locator("#research-table .country-group-row").count() > 0
        assert page.locator("#research-table .county-group-row").count() == 0
        assert page.locator("#research-table .location-group-row").count() == 0
        assert page.locator("#research-table .individual-table-row").count() == 0
        bulk_location_toggle.click()
        assert bulk_location_toggle.inner_text() == "Collapse all"
        assert page.locator("#research-table .individual-table-row").count() == expanded_location_people
        assert "groupLocations=1" in page.url
        page.locator("#table-group-clusters").uncheck()
        assert page.locator("#research-table .cluster-group-row").count() == 0
        assert page.locator("#research-table .location-group-row").count() > 0
        assert page.locator("#research-table .area-group-row").count() > 0
        assert page.locator(".country-group-row", has_text="Ireland").count() == 1
        assert page.locator(".country-group-row", has_text="Scotland").count() == 1
        assert page.locator(".country-group-row", has_text="England").count() == 1
        assert page.locator(".area-group-row", has_text="Lanarkshire").count() == 1
        page.locator("#table-location-level").select_option("1")
        assert page.locator("#research-table .country-group-row").count() > 0
        assert page.locator("#research-table .county-group-row").count() == 0
        assert page.locator("#research-table .area-group-row").count() == 0
        assert page.locator("#research-table .location-group-row").count() == 0
        assert page.locator("#research-table .individual-table-row").count() > 0
        assert "locationLevel=1" in page.url
        assert "Level 1" in page.locator("#research-table-count").inner_text()
        page.locator("#table-location-level").select_option("2")
        assert page.locator("#research-table .country-group-row").count() > 0
        assert page.locator("#research-table .county-group-row").count() > 0
        assert page.locator("#research-table .area-group-row").count() > 0
        assert page.locator("#research-table .location-group-row").count() == 0
        assert "locationLevel=2" in page.url
        assert "Level 2" in page.locator("#research-table-count").inner_text()
        page.locator("#table-location-level").select_option("3")
        assert page.locator("#research-table .location-group-row").count() > 0
        assert "locationLevel=" not in page.url
        assert "Level 3" in page.locator("#research-table-count").inner_text()
        adam_rows = page.locator('#research-table .individual-table-row:not([data-group-county=""])').filter(
            has=page.locator('td:last-child a[href="https://www.wikitree.com/wiki/Glasgow-3902"]')
        )
        assert page.locator('#research-table .individual-table-row[data-group-county="County Londonderry"]').filter(
            has=page.locator('td:last-child a[href="https://www.wikitree.com/wiki/Glasgow-3902"]')
        ).count() == 1
        cross_county_rows = page.locator('#research-table .individual-table-row:not([data-group-county=""])').filter(
            has=page.locator('td:last-child a[href="https://www.wikitree.com/wiki/Glasgow-1101"]')
        )
        assert cross_county_rows.count() == 2
        assert cross_county_rows.locator(".multi-location-badge").count() == 2
        assert adam_rows.locator(".multi-location-badge").count() == 0
        hierarchy = page.locator("#research-table tbody tr").evaluate_all(
            "rows => rows.map(row => ({className: row.className, text: row.innerText}))"
        )
        country_index = next(i for i, row in enumerate(hierarchy) if "country-group-row" in row["className"] and "Ireland" in row["text"])
        county_index = next(i for i, row in enumerate(hierarchy) if "county-group-row" in row["className"] and "County Londonderry" in row["text"])
        inishrush_index = next(i for i, row in enumerate(hierarchy) if "location-group-row" in row["className"] and "Inishrush" in row["text"])
        assert country_index < county_index < inishrush_index
        county_counts_match = page.locator("#research-table tbody").evaluate(
            "tbody => { const rows=[...tbody.rows]; return rows.every((row,i) => { if(!row.classList.contains('county-group-row')) return true; const stated=Number((row.innerText.match(/· (\\d+) individual/)||[])[1]); const people=new Set(); for(let j=i+1;j<rows.length;j++){ if(rows[j].classList.contains('country-group-row')||rows[j].classList.contains('county-group-row')||rows[j].classList.contains('area-group-row')) break; if(rows[j].classList.contains('individual-table-row')) people.add(rows[j].dataset.individual); } return stated===people.size; }); }"
        )
        assert county_counts_match
        country_counts_match = page.locator("#research-table tbody").evaluate(
            "tbody => { const rows=[...tbody.rows]; return rows.every((row,i) => { if(!row.classList.contains('country-group-row')) return true; const stated=Number((row.innerText.match(/· (\\d+) individual/)||[])[1]); const people=new Set(); for(let j=i+1;j<rows.length;j++){ if(rows[j].classList.contains('country-group-row')||rows[j].classList.contains('cluster-group-row')) break; if(rows[j].classList.contains('individual-table-row')) people.add(rows[j].dataset.individual); } return stated===people.size; }); }"
        )
        assert country_counts_match
        ireland_country_toggle = page.locator(".country-group-row .country-group-toggle", has_text="Ireland")
        assert ireland_country_toggle.count() == 1
        expanded_country_rows = page.locator("#research-table .individual-table-row").count()
        ireland_country_toggle.click()
        assert ireland_country_toggle.get_attribute("aria-expanded") == "false"
        assert page.locator(".county-group-row", has_text="County Londonderry").count() == 0
        assert page.locator("#research-table .individual-table-row").count() < expanded_country_rows
        ireland_country_toggle.click()
        assert ireland_country_toggle.get_attribute("aria-expanded") == "true"
        londonderry_toggle = page.locator(".county-group-row .regional-group-toggle", has_text="County Londonderry")
        assert londonderry_toggle.count() == 1
        expanded_rows = page.locator("#research-table .individual-table-row").count()
        londonderry_toggle.click()
        assert londonderry_toggle.get_attribute("aria-expanded") == "false"
        assert page.locator("#research-table .individual-table-row").count() < expanded_rows
        londonderry_toggle.click()
        assert londonderry_toggle.get_attribute("aria-expanded") == "true"
        page.locator("#table-group-locations").uncheck()
        page.locator("#table-group-clusters").check()
        assert adam_rows.count() == 0
        assert cross_county_rows.count() == 0
        page.locator("#location-search").fill("Glasgow-3903")
        expandable_row = page.locator('tr[data-individual="Glasgow-3903"]')
        assert expandable_row.count() == 1
        expandable_row.locator(".table-person-toggle").click()
        detail_row = page.locator("#research-table .individual-detail-row")
        assert detail_row.count() == 1
        assert "all mapped records" in detail_row.inner_text().lower()
        assert "Inishrush" in detail_row.inner_text()
        assert expandable_row.get_attribute("aria-expanded") == "true"
        expandable_row.locator(".table-person-toggle").click()
        assert page.locator("#research-table .individual-detail-row").count() == 0
        page.locator("#location-search").fill("")
        page.locator("#table-location-search").fill("Ireland")
        assert page.locator("#research-table .table-recorded-location", has_text="Larne").count() > 0
        page.locator("#table-location-search").fill("County Antrim")
        assert page.locator("#research-table .table-recorded-location", has_text="Larne").count() > 0
        page.locator("#table-location-search").fill("County Londonderry")
        assert page.locator("#research-table .table-recorded-location", has_text="Inishrush").count() > 0
        page.locator("#table-location-search").fill("")
        page.locator("#table-first-name").fill("Adam")
        page.locator("#table-last-name").fill("Glasgow")
        page.locator("#table-date-from").fill("1758")
        page.locator("#table-date-to").fill("1758")
        page.locator("#table-spouse-name").fill("Rose")
        page.locator("#table-location-search").fill("Inishrush")
        assert page.locator("#research-table .individual-table-row").count() == 1
        assert page.locator('.individual-table-row a[href="https://www.wikitree.com/wiki/Glasgow-3902"]').count() > 0
        assert "Inishrush" in page.locator("#research-table .table-recorded-location").inner_text()
        assert "firstName=Adam" in page.url and "tableLocation=Inishrush" in page.url
        page.locator("#table-search-clear").click()
        page.locator("#table-father-name").fill("Adam Glasgow")
        page.locator("#table-mother-name").fill("Rose Unknown")
        assert page.locator("#research-table .individual-table-row").count() > 1
        james_row = page.locator(".individual-table-row").filter(
            has=page.locator('a[href="https://www.wikitree.com/wiki/Glasgow-3903"]')
        )
        assert james_row.locator('.table-fathers a[href="https://www.wikitree.com/wiki/Glasgow-3902"]').inner_text() == "Adam Glasgow"
        assert james_row.locator('.table-mothers a[href="https://www.wikitree.com/wiki/Unknown-760890"]').inner_text() == "Rose (Unknown) Glasgow"
        assert "father=Adam+Glasgow" in page.url and "mother=Rose+Unknown" in page.url
        page.locator("#table-search-clear").click()
        assert page.locator("#research-table .individual-table-row").count() == all_table_people
        page.locator("#location-search").fill("Glasgow-3902")
        assert 0 < page.locator("#research-table .individual-table-row").count() < all_table_people
        assert "1758" in page.locator("#research-table .table-birth").all_inner_texts()
        assert "1844-06-30" in page.locator("#research-table .table-death").all_inner_texts()
        assert any(
            "Tamlaght O'Crilly" in value
            for value in page.locator("#research-table .table-death-location").all_inner_texts()
        )
        assert page.locator('.table-spouses a[href="https://www.wikitree.com/wiki/Unknown-760890"]').inner_text() == "Rose (Unknown) Glasgow"
        page.locator("#location-search").fill("Glasgow-3941")
        assert page.locator("#research-table .table-birth").inner_text() == "before 1776"
        assert page.locator("#research-table .table-birth-location").inner_text() == "Ireland"
        page.locator("#location-search").fill("Glasgow-3931")
        assert page.locator("#research-table .table-birth").inner_text() == "before 1722"
        page.locator("#location-search").fill("Henry Ellis")
        assert page.locator("#research-table .individual-table-row").count() == 0
        page.locator("#location-search").fill("")
        page.locator("#table-death-exclude").fill("USA")
        usa_excluded_count = page.locator("#research-table .individual-table-row").count()
        assert 0 < usa_excluded_count < all_table_people
        assert all(
            "united states" not in value.lower()
            for value in page.locator("#research-table .table-death-location").all_inner_texts()
        )
        assert "excludeDeath=USA" in page.url
        page.locator("#table-group-clusters").uncheck()
        assert page.locator("#research-table .cluster-group-row").count() == 0
        assert page.locator("#research-table .table-cluster").count() == usa_excluded_count
        assert "groupClusters=0" in page.url
        names_before_sort = page.locator("#research-table .individual-table-row td:first-child").all_inner_texts()
        page.locator('#research-table th[data-sort="death_location"]').click()
        names_after_sort = page.locator("#research-table .individual-table-row td:first-child").all_inner_texts()
        assert names_after_sort != names_before_sort
        page.locator("#table-death-exclude").fill("")
        page.locator("#table-spouse-name").fill("Mary")
        page.locator('#research-table th[data-sort="spouse"]').click()
        assert page.locator("#research-table .individual-table-row").count() > 5
        assert page.locator("#research-table tbody").evaluate(
            "tbody => { const names=[...tbody.querySelectorAll('.individual-table-row .table-spouses a:first-child')].map(a=>a.textContent.trim()); const surname=name=>{ const match=name.match(/\\(([^)]+)\\)/); const source=match?match[1]:name; return source.trim().split(/\\s+/).pop(); }; const surnames=names.map(surname); const expected=[...surnames].sort((a,b)=>a.localeCompare(b)); return JSON.stringify(surnames)===JSON.stringify(expected); }"
        )
        page.locator("#table-spouse-name").fill("")
        page.locator("#location-search").fill("Unknown-760890")
        assert page.locator("#research-table .individual-table-row").count() == 1
        page.locator("#location-search").fill("")
        page.locator("#table-males-only").check()
        assert 0 < page.locator("#research-table .individual-table-row").count() < usa_excluded_count
        assert "males=1" in page.url
        page.locator("#location-search").fill("entry 1272")
        assert page.locator("#research-table .individual-table-row").count() == 1
        page.locator("#location-search").fill("Unknown-760890")
        assert page.locator("#research-table .individual-table-row").count() == 0
        page.locator("#location-search").fill("")
        with page.expect_download() as download_info:
            page.locator("#table-export").click()
        assert download_info.value.suggested_filename == "glasgow-map-visible-individuals.csv"
        page.locator("#table-close").click()
        assert page.locator("#research-table-panel").is_hidden()
        assert page.locator("#display-map").get_attribute("aria-pressed") == "true"
        page.locator("summary", has_text="Research tools").click()
        ireland_toggle = page.locator("#show-ireland")
        scotland_toggle = page.locator("#show-scotland")
        britain_toggle = page.locator("#show-great-britain")
        assert ireland_toggle.is_checked()
        assert scotland_toggle.is_checked()
        assert britain_toggle.is_checked()
        all_region_locations = page.locator("#location-list li").count()
        scotland_toggle.set_checked(False, force=True)
        britain_toggle.set_checked(False, force=True)
        ireland_only_locations = page.locator("#location-list li").count()
        assert 0 < ireland_only_locations < all_region_locations
        britain_toggle.set_checked(True, force=True)
        assert "regions=ireland%7Ebritain" in page.url
        assert page.locator("#location-list li").count() > ireland_only_locations
        page.locator("#location-search").fill("Glasgow-3110")
        assert page.locator("#location-list li").count() > 0
        page.locator("#location-search").fill("")
        britain_toggle.set_checked(False, force=True)
        ireland_toggle.set_checked(False, force=True)
        scotland_toggle.set_checked(True, force=True)
        assert "regions=scotland" in page.url
        assert page.locator("#location-list li").count() > 0
        page.locator("#location-search").fill("Glasgow-1095")
        assert page.locator("#location-list li").count() == 1
        page.locator("#view-individuals").click()
        assert page.locator("#location-list li").count() == 1
        page.evaluate("map_b6066c8e00159c81bc5341da9da20086.setZoom(12)")
        page.locator("body.individual-name-zoom").wait_for()
        assert page.locator(".individual-name-label:visible").count() > 0
        assert page.evaluate("""
            () => {
              const labels = [...document.querySelectorAll('.individual-name-label')]
                .filter(label => getComputedStyle(label).visibility !== 'hidden' && label.getClientRects().length);
              return labels.every((label, index) => {
                const a = label.getBoundingClientRect();
                return labels.slice(index + 1).every(other => {
                  const b = other.getBoundingClientRect();
                  return a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom;
                });
              });
            }
        """)
        page.locator("#view-locations").click()
        page.locator("#location-search").fill("Glasgow-1140")
        assert page.locator("#location-list li").count() == 1
        page.locator("#location-search").fill("")
        page.locator("#regions-all").click()
        assert ireland_toggle.is_checked() and scotland_toggle.is_checked() and britain_toggle.is_checked()
        assert "regions=" not in page.url

        page.locator("#view-individuals").click()
        individual_locations = page.locator("#location-list > li").count()
        assert page.locator(".individual-list").count() == individual_locations
        assert page.locator(".individual-row").count() > individual_locations
        assert page.locator("#root-generations").is_disabled()
        page.locator("#show-major-roots-only").check()
        assert page.locator("#root-generations").is_enabled()
        page.locator("#root-generations").fill("0")
        page.locator("#location-search").fill("Glasgow-1078")
        assert page.locator("#location-list li").count() == 1
        assert "Robert" in page.locator("#location-list li").inner_text()
        assert page.locator(".patriarch-descendants").inner_text() == "136 descendants"
        page.locator("#location-search").fill("")
        page.locator("#view-locations").click()

        page.locator("#view-individuals").click()
        page.locator("#show-major-roots-only").check()
        page.locator("#root-generations").fill("2")
        page.locator("#show-relationship-lines").check()
        assert "view=individuals" in page.url
        assert "majorRoots=1" in page.url
        assert page.locator("path.relationship-line").count() > 0

        assert page.locator("#location-list li").count() > 0
        page.locator("#location-list li a").nth(0).evaluate("element => element.click()")
        assert page.locator("#details-panel").is_visible()
        assert page.locator("#details-content .family-section").count() > 0
        assert page.locator("#details-content summary", has_text="Profile audit").count() > 0
        page.locator("#details-close").click()

        page.locator("#view-locations").click()
        page.locator("#location-search").fill("Alexander Glasgow Esq")
        assert "q=Alexander+Glasgow+Esq" in page.url
        assert page.locator("#location-list li").count() > 0

        page.locator("summary", has_text="Research tools").click()
        page.locator("#unresolved-only").check()
        assert "unresolved=1" in page.url
        page.reload(wait_until="networkidle")
        assert page.locator("#location-search").input_value() == "Alexander Glasgow Esq"
        assert page.locator("#unresolved-only").is_checked()

        page.locator("#location-search").fill("")
        page.locator("summary", has_text="Research tools").click()
        page.locator("#unresolved-only").uncheck()
        initial_markers = page.locator(".leaflet-marker-icon").count()
        page.locator('#evidence-filters input[value="profile"]').uncheck()
        assert "evidence=" in page.url
        assert page.locator(".leaflet-marker-icon").count() < initial_markers

        page.locator("summary", has_text="Family clusters").click()
        page.locator("#clusters-none").click()
        assert page.locator(".leaflet-marker-icon").count() == 0
        page.locator("#clusters-all").click()
        assert page.locator(".leaflet-marker-icon").count() > 0

        browser.close()
    if errors:
        raise AssertionError("Browser errors: " + " | ".join(errors))
    print("Family-map browser smoke test passed")


if __name__ == "__main__":
    main()
