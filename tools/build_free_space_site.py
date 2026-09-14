#!/usr/bin/env python3
"""Build the public directory of captured WikiTree free-space pages.

The directory publishes descriptive metadata and canonical WikiTree links.  It
does not republish the captured edit-source bodies, which can contain evolving
hypotheses, DNA material, or references to living people.
"""

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


def public_rows(pages: list[dict]) -> list[dict]:
    """Strip capture internals and raw-source paths from the browser index."""
    keys = (
        "wikitreeId",
        "title",
        "viewUrl",
        "category",
        "editDate",
        "verifiedDate",
        "startDate",
        "endDate",
        "location",
        "tags",
    )
    return [{key: page.get(key, [] if key == "tags" else "") for key in keys} for page in pages]


def study_rows(source: dict, studies: dict) -> list[dict]:
    """Attach public availability labels without exposing capture paths or bodies."""
    local_ids = {page_id for page_id, *_ in (("Space:" + name, title, start, end, location) for name, title, start, end, location in LIVE_LOCAL_PAGES)}
    rows = public_rows(unique_pages(source))
    by_id = {study["wikitreeId"]: study for study in studies["studies"]}
    for row in rows:
        study = by_id.get(row["wikitreeId"])
        row["availability"] = "External WikiTree page; repository-only verified source copy" if row["wikitreeId"] in local_ids else "External WikiTree page"
        if study:
            row["summaryUrl"] = "#study-" + study["id"]
            row["availability"] = "External study with local safe summary"
    return rows


def availability_for(page: dict, studies_by_id: dict) -> tuple[str, str]:
    """Return a short public label and optional local-summary anchor."""
    if page["wikitreeId"] in studies_by_id:
        return "External study · local safe summary below", "#study-" + studies_by_id[page["wikitreeId"]]["id"]
    if page["wikitreeId"] in {"Space:" + name for name, *_ in LIVE_LOCAL_PAGES}:
        return "External canonical page · repository-only verified source copy", ""
    return "External WikiTree page", ""


def _card(page: dict, studies_by_id: dict) -> str:
    dates = "–".join(filter(None, (page.get("startDate", ""), page.get("endDate", ""))))
    details = []
    if dates:
        details.append(f"Page dates: {escape(dates)}")
    if page.get("location"):
        details.append(escape(page["location"]))
    if page.get("editDate"):
        details.append(f"WikiTree edit: {escape(page['editDate'])}")
    elif page.get("verifiedDate"):
        details.append(f"Verified live: {escape(page['verifiedDate'])}")
    tags = ", ".join(page.get("tags", []))
    if tags:
        details.append(f"Tags: {escape(tags)}")
    availability, summary_url = availability_for(page, studies_by_id)
    details.append(escape(availability))
    search = " ".join(
        str(value)
        for value in (
            page["title"],
            page["wikitreeId"],
            page["category"],
            dates,
            page.get("location", ""),
            tags,
        )
    ).lower()
    meta = "<span>" + "</span><span>".join(details) + "</span>" if details else ""
    summary_link = f' <a href="{escape(summary_url, quote=True)}">Read local summary</a>' if summary_url else ""
    return (
        f'<article class="fsp-card" data-category="{escape(page["category"], quote=True)}" '
        f'data-search="{escape(search, quote=True)}">'
        f'<span class="r-kicker">{escape(page["category"])}</span>'
        f'<h2><a href="{escape(page["viewUrl"], quote=True)}" rel="noopener" target="_blank">'
        f'{escape(page["title"].replace("''", ""))} <span aria-hidden="true">↗</span></a></h2>'
        f'<p class="fsp-id">{escape(page["wikitreeId"])}</p>'
        f'<div class="fsp-meta">{meta}</div>{summary_link}'
        "</article>"
    )


def _study_card(study: dict) -> str:
    return (
        f'<article class="fsp-card" id="study-{escape(study["id"], quote=True)}">'
        '<span class="r-kicker">Dated local research summary</span>'
        f'<h2>{escape(study["title"])}</h2>'
        f'<p><strong>Confidence:</strong> {escape(study["confidence"])}</p>'
        f'<p><strong>Provenance:</strong> {escape(study["provenance"])}</p>'
        f'<p><strong>Current conclusion:</strong> {escape(study["conclusion"])}</p>'
        f'<p><strong>Completed searches:</strong> {escape(study["completedSearches"])}</p>'
        f'<p><strong>Next action:</strong> {escape(study["nextAction"])}</p>'
        f'<p class="fsp-meta"><span>{escape(study["localStatus"])}</span></p>'
        f'<p><a href="{escape(study["publicSupport"]["url"], quote=True)}">{escape(study["publicSupport"]["label"])} <span aria-hidden="true">→</span></a></p>'
        '</article>'
    )


def _main(source: dict, pages: list[dict], studies: dict) -> str:
    counts = Counter(page["category"] for page in pages)
    options = "".join(f'<option value="{escape(c, quote=True)}">{escape(c)} ({counts[c]})</option>' for c in CATEGORY_ORDER)
    summary = "".join(
        f'<button type="button" data-fsp-topic="{escape(c, quote=True)}"><strong>{counts[c]}</strong><span>{escape(c)}</span></button>'
        for c in CATEGORY_ORDER
    )
    studies_by_id = {study["wikitreeId"]: study for study in studies["studies"]}
    cards = "".join(_card(page, studies_by_id) for page in pages)
    captured = source["capturedAt"]
    capture_label = f"{captured[8:10]} {('January','February','March','April','May','June','July','August','September','October','November','December')[int(captured[5:7])-1]} {captured[:4]}"
    return (
        '<main class="r-main fsp-main" id="main">'
        '<header class="v3-page-head"><span class="r-kicker">The research library</span>'
        '<h1>Free-space research pages.</h1>'
        f'<p>Browse {len(pages)} project pages, record studies, family cases and DNA notes maintained on WikiTree.</p></header>'
        '<aside class="fsp-notice"><strong>A directory, not a second edition.</strong> '
        f'This catalogue combines {source["pageCount"]} pages from a watchlist capture made on {escape(capture_label)} '
        f'with {len(pages) - source["pageCount"]} individual bearer pages recorded as verified live that day. Each result opens the canonical live '
        'WikiTree page, where the text and evidence may have changed. Free-space pages are research resources and '
        'are not person profiles; hypotheses should be checked against their cited evidence. '
        'Every entry opens an external WikiTree page. Any repository source copy is not publicly linked; the dated summaries below instead link their public supporting accounts and identify any local draft as repository-only.</aside>'
        '<section class="fsp-studies" aria-labelledby="fsp-studies-title"><header class="v3-page-head">'
        '<span class="r-kicker">Research status</span><h2 id="fsp-studies-title">Important external studies, locally summarised.</h2>'
        f'<p>Updated {escape(studies["updated"])} from maintained project dossiers and reviewed studies. These summaries record conclusions, completed searches and next actions without reproducing private captures.</p>'
        '</header><div class="fsp-grid">' + "".join(_study_card(study) for study in studies["studies"]) + '</div></section>'
        f'<div class="fsp-topics" aria-label="Browse by topic">{summary}</div>'
        '<form class="fsp-controls" role="search"><label>Search the pages'
        '<input id="fsp-search" type="search" autocomplete="off" placeholder="A page, place, period or topic…"></label>'
        '<label>Topic<select id="fsp-category"><option value="">All topics</option>'
        f'{options}</select></label><button class="r-button quiet" id="fsp-clear" type="button">Clear</button></form>'
        f'<p class="fsp-count" id="fsp-count" aria-live="polite">{len(pages)} pages</p>'
        f'<section class="fsp-grid" id="fsp-results" aria-label="Free-space page directory">{cards}</section>'
        '<div class="g-empty fsp-empty" id="fsp-empty" hidden><h2>No matching pages.</h2>'
        '<p>Try fewer words or choose another topic.</p></div></main>'
    )


def build() -> dict[str, int]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    studies = json.loads(STUDY_SOURCE.read_text(encoding="utf-8"))
    pages = unique_pages(source)
    expected = source["pageCount"] + len(LIVE_LOCAL_PAGES)
    if len(pages) != expected:
        raise ValueError(f"expected {expected} unique pages, found {len(pages)}")
    shell = (WEB / "research/index.html").read_text(encoding="utf-8")
    shell = re.sub(r"<title>.*?</title>", "<title>Free-space research pages · Glasgow surname archive</title>", shell, count=1)
    shell = re.sub(
        r'<meta content="[^"]*" name="description">',
        '<meta content="A searchable directory of the Glasgow surname project’s WikiTree free-space research pages." name="description">',
        shell,
        count=1,
    )
    shell = shell.replace(
        '<link rel="stylesheet" href="/assets/repair/site.css?v=3.1-repair-1">',
        '<link rel="stylesheet" href="/assets/repair/site.css?v=3.1-repair-1"><link rel="stylesheet" href="/assets/free-space/site.css?v=1">',
        1,
    )
    shell = re.sub(r'class="g-unified g-kind-[^"]+ r-v2', 'class="g-unified g-kind-free-space r-v2', shell, count=1)
    shell = re.sub(r'data-g-path="[^"]+"', 'data-g-path="/free-space/index.html"', shell, count=1)
    shell = shell.replace('<strong>Research</strong>', '<a href="/research/">Research</a><i>/</i><strong>Free-space pages</strong>', 1)
    shell = shell.replace('<a href="/research/">Research</a><a href="/compare/">', '<a href="/research/">Research</a><a href="/free-space/" aria-current="page">Free-space pages</a><a href="/compare/">', 1)
    shell, count = re.subn(r'<main\b.*?</main>', _main(source, pages, studies), shell, count=1, flags=re.S)
    if count != 1:
        raise ValueError("could not replace the Research-page main element")
    shell = shell.replace('</body>', '<script defer src="/assets/free-space/site.js?v=1"></script></body>', 1)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_INDEX.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(shell, encoding="utf-8")
    SEARCH_INDEX.write_text(json.dumps(study_rows(source, studies), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"captures": len(source["pages"]), "pages": len(pages)}


def main() -> int:
    result = build()
    print(f"Built {result['pages']} free-space pages from {result['captures']} captures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
