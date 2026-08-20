#!/usr/bin/env python3
"""Search PRONI's public eCatalogue without a browser."""

from __future__ import annotations

import argparse
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SEARCH_URL = "https://apps.proni.gov.uk/eCatNI_IE/SearchPage.aspx"


def form_defaults(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for node in soup.select("input[name]"):
        kind = node.get("type", "text")
        if kind in {"submit", "image", "button"}:
            continue
        if kind in {"checkbox", "radio"} and not node.has_attr("checked"):
            continue
        values[node["name"]] = node.get("value", "")
    for node in soup.select("select[name]"):
        selected = node.select_one("option[selected]") or node.select_one("option")
        values[node["name"]] = selected.get("value", "") if selected else ""
    return values


def clean(text: str) -> str:
    return " ".join(text.split())


def browser_details(reference: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        page = browser.new_page()
        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        page.locator("#ContentPlaceHolder1_txtPRONIRef").fill(reference)
        page.locator("#ContentPlaceHolder1_SearchArchiveBtn").click()
        page.wait_for_url("**/SearchResults.aspx", timeout=60_000)
        page.wait_for_load_state("networkidle")
        more = page.locator('input[value="More"]')
        if more.count() != 1:
            print(clean(page.locator("#contain").inner_text()))
            browser.close()
            return
        more.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)
        print(f"{page.title()} | {page.url}")
        for link in page.locator("a[href]").all():
            label = clean(link.inner_text())
            href = link.get_attribute("href") or ""
            if label or any(word in href.lower() for word in ("digital", "view", "browse")):
                print(f"LINK {label!r}: {href}")
        for control in page.locator("input, button").all():
            label = control.get_attribute("value") or clean(control.inner_text())
            name = control.get_attribute("name") or ""
            if "view" in label.lower() or "digital" in name.lower():
                print(f"CONTROL {name!r}: {label!r}")
        print(clean(page.locator("body").inner_text()))
        browser.close()


def search(query: str, reference: str, debug: bool = False, details: bool = False) -> None:
    session = requests.Session()
    response = session.get(SEARCH_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    data = form_defaults(soup)
    data.update(
        {
            "ctl00$ContentPlaceHolder1$txtWords": query,
            "ctl00$ContentPlaceHolder1$txtPRONIRef": reference,
            "ctl00$ContentPlaceHolder1$radWordSearchFields": "BOTH",
            "ctl00$ContentPlaceHolder1$radWordMatch": "EXP",
            "ctl00$ContentPlaceHolder1$ddPageSize": "50",
            "ctl00$ContentPlaceHolder1$ddSortBy": "REF",
            "ctl00$ContentPlaceHolder1$SearchArchiveBtn": "Search",
        }
    )
    response = session.post(SEARCH_URL, data=data, timeout=60)
    response.raise_for_status()
    refresh = response.headers.get("Refresh", "")
    if "URL=" in refresh:
        target = refresh.split("URL=", 1)[1].split(",", 1)[0].strip()
        response = session.get(urljoin(response.url, target), timeout=60)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    if debug:
        print(f"URL: {response.url}")
        print("History:", [(item.status_code, item.url, item.headers.get("location")) for item in response.history])
        print("Headers:", {key: response.headers.get(key) for key in ("Refresh", "Location", "Set-Cookie")})
        print(f"Title: {clean(soup.title.get_text(' ')) if soup.title else '(none)'}")
        print("Links:")
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if "Search" in href or "Detail" in href or "Result" in href:
                print(clean(link.get_text(" ")), href)
        print("Forms:")
        for form in soup.select("form"):
            print(dict(form.attrs))
            print([(node.get("name"), node.get("value")) for node in form.select("input[name]")])
        print("Meta refresh:", [node.get("content") for node in soup.select('meta[http-equiv="refresh"]')])
        print("Scripts:", clean(" ".join(node.get_text(" ") for node in soup.select("script")))[:2000])
        print(clean(soup.get_text(" "))[:1500])

    result_rows = [
        row
        for row in soup.select("tr")
        if row.select_one('input[name*="hdnItemId"], input[name*="btnItemView"]')
    ]
    if result_rows:
        item_rows = [row for row in result_rows if row.get("class") and "maintGVRow" in row.get("class", [])]
        if details and len(item_rows) == 1:
            button = item_rows[0].select_one('input[name*="btnItemView"]')
            detail_data = form_defaults(soup)
            if button:
                detail_data[button["name"]] = button.get("value", "More")
                detail_response = session.post(response.url, data=detail_data, timeout=60)
                detail_response.raise_for_status()
                detail_soup = BeautifulSoup(detail_response.text, "html.parser")
                main = detail_soup.select_one("#contain, #divMain, main") or detail_soup
                print(clean(main.get_text(" | ")))
                return
        if debug:
            print(str(result_rows[-1])[:5000])
        for row in result_rows:
            print(clean(row.get_text(" | ")))
        return

    result_links = soup.select('a[href*="DetailsPage.aspx"]')
    if not result_links:
        message = soup.select_one(".ValSummary, .validation-summary-errors")
        print(clean(message.get_text(" ")) if message else "No catalogue results")
        return

    seen: set[str] = set()
    for link in result_links:
        url = urljoin(response.url, link.get("href", ""))
        if url in seen:
            continue
        seen.add(url)
        row = link.find_parent("tr")
        print(f"{clean(row.get_text(' | ')) if row else clean(link.get_text(' '))}\n{url}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="")
    parser.add_argument("--reference", default="")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--browser-details", action="store_true")
    args = parser.parse_args()
    if not args.query and not args.reference:
        parser.error("provide --query or --reference")
    if args.browser_details:
        if not args.reference:
            parser.error("--browser-details requires --reference")
        browser_details(args.reference)
        return
    search(args.query, args.reference, args.debug, args.details)


if __name__ == "__main__":
    main()
