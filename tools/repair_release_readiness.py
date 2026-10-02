#!/usr/bin/env python3
"""Small, repeatable public-page repairs for a release candidate."""
from __future__ import annotations

from collections import Counter
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
CSS_SOURCE = ROOT / "tools" / "release_readiness.css"
CSS_TARGET = WEB / "assets" / "repair" / "release-readiness.css"
CSS_HREF = "/assets/repair/release-readiness.css?v=1"
FEED_START, FEED_END = "<!-- release-readiness-feed:start -->", "<!-- release-readiness-feed:end -->"
LATEST_RESEARCH = runpy.run_path(str(ROOT / "tools" / "build_latest_research.py"))
entry = LATEST_RESEARCH["entry"]
research_updates = LATEST_RESEARCH["research_updates"]


def write(path: Path, value: str, changed: Counter) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != value:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        changed["release_readiness"] += 1


def release_data() -> tuple[dict, dict, date]:
    health = json.loads((WEB / "health.json").read_text(encoding="utf-8"))
    manifest = json.loads((WEB / "data" / "manifest.json").read_text(encoding="utf-8"))
    return health, manifest, date.fromisoformat(health["generated"])


def snapshot(page: str, generated: date) -> str:
    label = generated.strftime("Catalogue · %d %b %Y").replace(" 0", " ")
    title = generated.strftime("Catalogue snapshot: %d %B %Y").replace(" 0", " ")
    title += ". Tree and DNA have separate snapshot dates."
    def replace(match):
        opening = re.sub(r'\s+title=["\'][^"\']*["\']', '', match[1])
        return opening[:-1] + f' title="{escape(title, quote=True)}">{label}</a>'
    return re.sub(r'(<a\b(?=[^>]*\bclass="[^"]*\bg-snapshot-link\b[^"]*")[^>]*>).*?</a>',
                  replace, page, flags=re.S)


def about_dates(page: str, generated: date, manifest: dict) -> str:
    """Keep the catalogue compilation distinct from review and other snapshots."""
    label = generated.strftime('%d %B %Y').lstrip('0')
    page = re.sub(r'(<tr>\s*<td>Research catalogue</td><td>.*?</td><td>).*?(</td>)',
                  lambda m: m[1] + label + m[2], page, count=1, flags=re.S)
    start, end = '<!-- catalogue-dates:start -->', '<!-- catalogue-dates:end -->'
    latest = manifest.get('latest_research_update')
    summary = f'<p>Catalogue compiled {label}.'
    if latest:
        summary += f' Latest dated person research or review: {escape(latest)}.'
    summary += ' Individual findings retain their own dates; the family tree and DNA editions have separate dates above. <a href="/data/">Release assembly and data details →</a></p>'
    block = start + summary + end
    if start in page:
        return re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda _: block, page, flags=re.S)
    return page.replace('</table>', '</table>' + block, 1)


def add_css(page: str) -> str:
    links = re.compile(r'<link\b[^>]*\bhref=["\']/assets/repair/release-readiness\.css(?:\?[^"\']*)?["\'][^>]*>')
    found = False
    def retain_one(match):
        nonlocal found
        if found:
            return ""
        found = True
        return match[0]
    page = links.sub(retain_one, page)
    if not found:
        page = page.replace("</head>", f'<link rel="stylesheet" href="{CSS_HREF}"></head>', 1)
    def body(match: re.Match) -> str:
        attrs = match[1]
        if "release-ready" in attrs:
            return match[0]
        if re.search(r'\bclass="', attrs):
            return re.sub(r'\bclass="([^"]*)"', lambda cls: f'class="{cls[1]} release-ready"', match[0], count=1)
        return "<body" + attrs + ' class="release-ready">'
    return re.sub(r'<body(\b[^>]*)>', body, page, count=1)


def replace_once(page: str, pattern: str, replacement: str) -> str:
    value, count = re.subn(pattern, replacement, page, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Release-ready source changed near {pattern!r}")
    return value


def homepage_count(page: str, people: int) -> str:
    # The reader introduction replaces the old count strip. Its tree preview
    # has a different scope and must not receive the catalogue total.
    if 'class="reader-intro"' in page and 'class="v3-hero-stat"' not in page:
        return page
    return replace_once(page, r'(<div class="v3-hero-stat"><strong>)[\d,]+(</strong> catalogue entries)', rf'\g<1>{people:,}\2')


def repair_counts(health: dict, manifest: dict, generated: date, changed: Counter) -> None:
    counts = health["counts"]
    datasets = {row["name"]: row["count"] for row in manifest["datasets"]}
    people, records, places = counts["people"], counts["records"], counts["places"]
    pages = {
        "index.html": lambda page: homepage_count(page, people),
        "about/index.html": lambda page: replace_once(page, r'(<td>Research catalogue</td><td>)[^<]+(</td>)', rf'\g<1>{people:,} people · {records:,} record associations · {places:,} places\2'),
        "data/index.html": lambda page: replace_once(page, r'(<strong>people\.csv</strong><span>)[\d,]+ historical or deceased people(</span>)', rf'\g<1>{datasets["people"]:,} historical or deceased people\2'),
    }
    for relative, transform in pages.items():
        path = WEB / relative
        page = snapshot(path.read_text(encoding="utf-8"), generated)
        write(path, transform(page), changed)
    for relative in ("catalogue/index.html",):
        path = WEB / relative
        write(path, snapshot(path.read_text(encoding="utf-8"), generated), changed)


def repair_changes(changed: Counter) -> None:
    path = WEB / "changes" / "index.html"
    original = path.read_text(encoding="utf-8")
    page = add_css(original)
    page = re.sub(re.escape(FEED_START) + r".*?" + re.escape(FEED_END) + r"\s*", "", page, flags=re.S)
    cards = [entry(day, f"Research update: {name}", summary, href, "Read the case and evidence", identity)
             for day, name, summary, href, identity in research_updates()]
    feed = (
        f"{FEED_START}<section class=\"latest-research\" id=\"latest-research\" aria-labelledby=\"latest-research-title\">"
        '<div class="latest-research-heading"><p class="kicker">Maintained updates</p><h2 id="latest-research-title">Latest research</h2>'
        '<p>Public case files appear here only when they include a recorded research or review date. Their dates describe the research update, rather than the catalogue build or a claim that every case was reviewed then.</p></div>'
        '<div class="latest-research-links" aria-label="Research destinations"><a href="/research/">Research workspace</a><a href="/branches/#research-studies">Evidence-led groups</a><a href="/catalogue/">Browse people</a></div>'
        f'<div class="latest-research-grid">{"".join(cards[:12])}</div></section>{FEED_END}\n'
    )
    if '<div class="question-grid">' not in page:
        raise ValueError("Preserved release history is missing")
    page = page.replace('<div class="question-grid">', feed + '<div class="question-grid">', 1)
    write(path, page, changed)


def repair_direct_change_links(changed: Counter) -> None:
    paths = [WEB / "status.html", WEB / "catalogue.html", WEB / "catalogue" / "advanced.html", WEB / "status/index.html", WEB / "catalogue/index.html"]
    paths.extend((WEB / "people").glob("*.html"))
    for path in paths:
        page = path.read_text(encoding="utf-8")
        updated = re.sub(r'href="(?:\.\./)?changes\.html"', 'href="/changes/"', page)
        if not re.search(r'href=["\']/changes(?:/|["\'])', updated) and "</main>" in updated:
            updated = updated.replace("</main>", '<p class="release-links"><a href="/changes/">Research changes</a> · <a href="/privacy/">Privacy and publication policy</a></p></main>', 1)
        if updated != page:
            write(path, updated, changed)


def repair_contrast(changed: Counter) -> None:
    for relative in ("people/glasgow-951.html", "statistics/index.html", "compare/index.html", "places/index.html"):
        path = WEB / relative
        write(path, add_css(path.read_text(encoding="utf-8")), changed)
    write(CSS_TARGET, CSS_SOURCE.read_text(encoding="utf-8"), changed)


def repair() -> Counter:
    changed: Counter = Counter()
    health, manifest, generated = release_data()
    repair_counts(health, manifest, generated, changed)
    repair_direct_change_links(changed)
    repair_contrast(changed)
    repair_changes(changed)
    return changed


if __name__ == "__main__":
    print(dict(repair()))
