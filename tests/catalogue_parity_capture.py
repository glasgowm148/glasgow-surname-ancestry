#!/usr/bin/env python3
"""Capture catalogue search results for a fixed set of URLs.

Used to prove behaviour parity across catalogue UI refactors:

    python tests/catalogue_parity_capture.py capture baseline.json
    python tests/catalogue_parity_capture.py compare baseline.json

Each capture records the normalised URL, the result count, the ordered result
IDs (person page links) and any group headings, so parity is checked on
ordering and membership, not counts alone.  Compare against the same data
build: the capture stores a hash of the search index it ran against.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CATALOGUE_TEST_BASE", "http://127.0.0.1:8765")
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "www" / "data" / "catalogue-search-index.json"
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

SEARCHES = [
    "q=Alexander",
    "q=Glasgow-1022",
    "q=Glasco",
    "q=Glasco&exact=1",
    "q=Glasgow",
    "q=James+Glasgow+1830",
    "name=John+Glasgow",
    "first=James",
    "last=Glasgow",
    "first=James&last=Glasgow&gender=male",
    "gender=female&glasgowBirth=1&last=Smith",
    "gender=female&glasgowBirth=1",
    "gender=male",
    "males=1",
    "spouse=Smith",
    "father=John",
    "father=John&mother=Mary",
    "child=James",
    "sibling=Mary",
    "spouse=Smith&father=John",
    "marriageSurname=Smith",
    "marriageSurname=Cunningham",
    "birthSurname=Glasgow",
    "dateType=birth&from=1800&to=1830",
    "from=1700",
    "to=1650",
    "dateType=death&from=1900",
    "location=Antrim&locationType=birth",
    "location=Glasgow&locationType=death",
    "location=Lisnagaver",
    "region=Ireland",
    "excludeDeath=USA",
    "dateType=birth&from=1800&to=1830&location=Antrim&excludeDeath=USA",
    "cluster=County+Antrim+Glasgow+network",
    "recordType=Marriages",
    "quality=original",
    "wives=1",
    "suffix=1",
    "missingFather=1",
    "missingMother=1",
    "missingFather=1&missingMother=1&region=Scotland",
    "descendants=1",
    "missingProfile=1",
    "needsUpdate=1",
    "q=Alexander&sort=name:asc",
    "q=Alexander&sort=birth:desc",
    "q=Alexander&sort=spouse:asc",
    "q=Alexander&groupLocation=1&locationLevel=2",
    "q=Alexander&groupFamily=1",
    "q=Alexander&groupFamily=1&familySort=count:desc",
    "q=Alexander&groupTree=1",
    "q=Zzyzxnomatch",
]

CAPTURE_JS = """() => {
  const out = document.querySelector('#catalogue-results');
  const tree = out.querySelector('.catalogue-one-tree');
  const rows = [...out.querySelectorAll('.catalogue-results-table tbody tr')].map(row => {
    const link = row.querySelector('td a');
    if (link) return 'P:' + new URL(link.href).pathname.split('/').pop();
    return 'H:' + row.innerText.replace(/\\s+/g, ' ').trim().slice(0, 120);
  });
  return {
    status: document.querySelector('#catalogue-results-count').textContent.trim(),
    total: (out.querySelector('.catalogue-result-toolbar > strong') || {}).textContent || '',
    notice: (out.querySelector(':scope > .notice') || {}).textContent || '',
    rows,
    tree: tree ? {
      nodes: tree.getAttribute('data-tree-nodes'),
      people: [...tree.querySelectorAll('[data-tree-person]')].map(item => item.dataset.treePerson),
    } : null,
    url: location.search,
  };
}"""


def index_hash() -> str:
    return hashlib.sha1(INDEX.read_bytes()).hexdigest()


def capture(path: str = "/catalogue.html") -> dict:
    results = {}
    with sync_playwright() as playwright:
        options = {"executable_path": str(LOCAL_CHROME)} if LOCAL_CHROME.exists() else {}
        browser = playwright.chromium.launch(headless=True, **options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for search in SEARCHES:
            page.goto(f"{BASE}{path}?{search}", wait_until="networkidle")
            page.wait_for_function(
                "() => { const s = document.querySelector('#catalogue-results-count');"
                " return s && s.dataset.state !== 'busy'; }"
            )
            results[search] = page.evaluate(CAPTURE_JS)
        browser.close()
    if errors:
        raise AssertionError(errors)
    return {"index_sha1": index_hash(), "path": path, "results": results}


def compare(baseline: dict, current: dict) -> list[str]:
    problems = []
    if baseline["index_sha1"] != current["index_sha1"]:
        problems.append("search index changed between captures; parity comparison is not valid")
    for search, expected in baseline["results"].items():
        actual = current["results"].get(search)
        if actual is None:
            problems.append(f"{search}: not captured")
            continue
        for key in ("status", "total", "notice", "rows", "tree", "url"):
            if expected[key] != actual[key]:
                problems.append(f"{search}: {key} differs: {str(expected[key])[:160]!r} != {str(actual[key])[:160]!r}")
    return problems


def main() -> None:
    mode, target = sys.argv[1], Path(sys.argv[2])
    path = sys.argv[3] if len(sys.argv) > 3 else "/catalogue.html"
    if mode == "capture":
        target.write_text(json.dumps(capture(path), indent=1), encoding="utf-8")
        print(f"Captured {len(SEARCHES)} searches to {target}")
        return
    problems = compare(json.loads(target.read_text(encoding="utf-8")), capture(path))
    if problems:
        print("\n".join(problems))
        raise SystemExit(1)
    print(f"Parity: {len(SEARCHES)} searches match the baseline (IDs, order, counts, URLs)")


if __name__ == "__main__":
    main()
