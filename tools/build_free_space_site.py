#!/usr/bin/env python3
"""Build the full public-safe local edition of maintained WikiTree free-space studies."""

from __future__ import annotations

from collections import Counter
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/free-space-pages/index.json"
STUDY_SOURCE = ROOT / "research/free-space-pages/public-study-summaries.json"
WEB = ROOT / "www"
OUTPUT = WEB / "free-space/index.html"
SEARCH_INDEX = WEB / "assets/research/free-space-index.json"

CATEGORY_ORDER = (
    "Project and methods",
    "Early and medieval",
    "Scotland and records",
    "Ireland and migration",
    "DNA and haplogroups",
    "Families and case studies",
)

# Local source copies explicitly recorded as created and verified live on
# 29 August 2026, after the watchlist capture was assembled. Draft-only files
# in the same folder are intentionally excluded.
LIVE_LOCAL_PAGES = (
    ("Robert de Glasgu Dublin guild", "Robert de Glasgu — Dublin guild", "1190", "1265", "Dublin, Ireland"),
    ("Robert de Glascu plea roll 1200", "Robert de Glascu — plea roll, 1200", "1200", "", "England"),
    ("Gilbert de Glascu", "Gilbert de Glascu", "1222", "1223", "Dublin, Ireland"),
    ("Alexander son of Robert de Glascu", "Alexander, son of Robert de Glascu", "1238", "1239", "Dublin, Ireland"),
    ("Robert de Glasgu Dunkeld clerk", "Robert de Glasgu — Dunkeld clerk", "1229", "1236", "Scotland"),
    ("Robert de Glascu Durham witness", "Robert de Glascu — Durham witness", "1248", "1249", "Kippax, Yorkshire, England"),
    ("Hugh de Glasgw", "Hugh de Glasgw", "1283", "", "Glasgow, Scotland"),
    ("Master Walter de Glasgu", "Master Walter de Glasgu", "1291", "", "Scotland"),
    ("John of Glasgow (Holyrood)", "John of Glasgow — Holyrood", "1299", "", "Scotland"),
    ("Richard of Glasgow Arbroath", "Richard of Glasgow — Arbroath", "1312", "", "Arbroath, Scotland"),
    ("John de Glasgu (royal account 1343)", "John de Glasgu — royal account, 1343", "1343", "", "Scotland"),
    ("John de Glasgu (father of Malcolm)", "John de Glasgu — father of Malcolm", "1394", "", "Scotland"),
    ("Malcolm son of John de Glasgu", "Malcolm, son of John de Glasgu", "1394", "", "Perth, Scotland"),
    ("William physician de Glasgu", "William, physician de Glasgu", "1395", "1397", "Scotland"),
)


def category_for(page: dict) -> str:
    """Assign a broad browsing topic without interpreting page claims."""
    title = page["title"].lower()
    if re.match(r"^r-[a-z0-9]", title) or any(word in title for word in ("dna", "genetic", "haplogroup")):
        return "DNA and haplogroups"
    if any(word in title for word in ("ireland", "irish", "ulster", "londonderry", "killycurragh")):
        return "Ireland and migration"
    if title in {"glasgow", "glasgow research", "glasgow surname origins"} or any(
        word in title for word in ("name study", "using ai", "age of discovery")
    ):
        return "Project and methods"
    if any(
        word in title
        for word in (
            "de glasg",
            "medieval",
            "medevil",
            "bearers of",
            "official of glasgow",
            "15th & 16th",
            "15th and 16th",
            "origins (1170",
        )
    ):
        return "Early and medieval"
    year = re.match(r"\s*(\d{3,4})", str(page.get("startDate", "")))
    if year and int(year.group(1)) < 1500:
        return "Early and medieval"
    if any(
        word in title
        for word in (
            "protocol",
            "will",
            "testament",
            "census",
            "unions",
            "marriages",
            "ayrshire",
            "scottish borders",
            "stirling",
            "glasgow history",
        )
    ):
        return "Scotland and records"
    return "Families and case studies"


def unique_pages(source: dict) -> list[dict]:
    """Return one stable public row per WikiTree free-space page."""
    pages: dict[str, dict] = {}
    for raw in source["pages"]:
        page_id = raw["wikitreeId"].strip()
        if page_id in pages:
            # Keep the newest useful metadata while preserving the first position.
            kept = pages[page_id]
            for key, value in raw.items():
                if value and not kept.get(key):
                    kept[key] = value
            continue
        page = dict(raw)
        page["wikitreeId"] = page_id
        page["category"] = category_for(page)
        pages[page_id] = page
    for name, title, start, end, location in LIVE_LOCAL_PAGES:
        page_id = "Space:" + name
        if page_id in pages:
            continue
        pages[page_id] = {
            "wikitreeId": page_id,
            "title": title,
            "viewUrl": "https://www.wikitree.com/wiki/" + quote(page_id.replace(" ", "_"), safe=":/'()"),
            "category": "Early and medieval",
            "editDate": "",
            "verifiedDate": "29 Aug 2026",
            "startDate": start,
            "endDate": end,
            "location": location,
            "tags": ["Pre-1500 bearer"],
        }
    return list(pages.values())


def build() -> dict[str, int]:
    import sys
    sys.path.insert(0, str(ROOT))
    from tools.free_space_edition import build_site
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    studies = json.loads(STUDY_SOURCE.read_text(encoding="utf-8"))
    return build_site(source, unique_pages(source), studies)


def main() -> int:
    result = build()
    print(f"Built {result['pages']} free-space pages from {result['captures']} captures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
