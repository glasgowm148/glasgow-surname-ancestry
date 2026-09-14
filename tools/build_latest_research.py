#!/usr/bin/env python3
"""Add a concise, source-derived research feed to the preserved change log."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import escape, unescape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
PAGE = WEB / "changes" / "index.html"
START, END = "<!-- latest-research:start -->", "<!-- latest-research:end -->"
DATE = re.compile(r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2} [A-Za-z]+ \d{4})\b')


def recorded_date(value: str) -> str | None:
    match = DATE.search(value)
    if not match:
        return None
    for format_ in ('%Y-%m-%d', '%d %B %Y', '%d %b %Y'):
        try:
            return datetime.strptime(match[0], format_).date().isoformat()
        except ValueError:
            continue
    return None


def narrative(markdown: str) -> str:
    """Use a complete source paragraph, never an invented resolution label."""
    markdown = re.sub(r'<!--.*?-->', '', markdown, flags=re.S)
    markdown = re.sub(r'```.*?```', '', markdown, flags=re.S)
    markdown = re.sub(r'<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>', '', markdown, flags=re.S | re.I)
    for paragraph in re.split(r'\n\s*\n', markdown):
        paragraph = paragraph.strip()
        if not paragraph or re.match(r'^(?:[#|>]|[-*+]\s|\d+[.)]\s|```)', paragraph):
            continue
        paragraph = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', paragraph)
        paragraph = re.sub(r'\[\[([^\]]+)\]\]', r'\1', paragraph)
        paragraph = re.sub(r'\[([^\]]+)\]\([^\n]*?\)', r'\1', paragraph)
        paragraph = re.sub(r'\[https?://\S+\s+([^\]]+)\]', r'\1', paragraph)
        paragraph = paragraph.replace('**', '').replace('`', '').replace("'''", '')
        result = text(paragraph)
        if len(result) >= 45 and not result.startswith(('http://', 'https://', 'Last updated:')):
            return result
    return ''


def identity_details(person: dict) -> tuple[str, str, str]:
    def vital(kind):
        year = person.get(kind + '_year')
        status = str(person.get(kind + '_status') or '').lower()
        if status in {'uncertain', 'unproved', 'unknown'}:
            return 'not established'
        if year is None or year == '':
            return 'not recorded'
        if status in {'before', 'after'}:
            return f'{status} {year}'
        if status in {'estimated', 'approximate', 'circa', 'about'}:
            return f'c. {year}'
        return str(year) if status == 'exact' else f'{year} (recorded)'

    dates = f'Birth: {vital("birth")} / Death: {vital("death")}'
    places = list(dict.fromkeys(str(place).strip() for place in person.get('locations', []) if place))
    if not places:
        places = list(dict.fromkeys(str(person[key]).strip() for key in ('birth_place', 'death_place') if person.get(key)))
    return str(person.get('id') or person.get('catalogue_id') or ''), dates, '; '.join(places[:2]) or 'Locality not recorded'


def research_updates() -> list[tuple[str, str, str, str, tuple[str, str, str]]]:
    """Only explicitly dated, publicly represented cases may enter the feed."""
    data = json.loads((WEB / 'data/people-index.json').read_text(encoding='utf-8'))
    people = data if isinstance(data, list) else data.get('people', data.get('items', []))
    public = {}
    for person in people:
        href = person.get('html_url') or ''
        if not href.startswith('/people/') or not (WEB / href.lstrip('/')).is_file():
            continue
        for ident in [person.get('id'), *person.get('alternate_ids', [])]:
            if ident:
                public[str(ident).casefold()] = person
    updates = []
    for source in sorted((ROOT / 'research').glob('*/findings.md')):
        person = public.get(source.parent.name.casefold())
        if not person:
            continue
        markdown = source.read_text(encoding='utf-8')
        headings = list(re.finditer(r'^#{1,6}\s+(.+)$', markdown, flags=re.M))
        sections = [(match[1], markdown[match.end():headings[index + 1].start() if index + 1 < len(headings) else len(markdown)])
                    for index, match in enumerate(headings)]
        candidates = []
        updated = re.search(r'^\s*(?:\*\*)?(?:Last updated|Updated|Last reviewed)\s*:\s*(?:\*\*)?([^\n]+)', markdown, re.M | re.I)
        if updated and (date := recorded_date(updated[1])):
            conclusion = next((body for title, body in sections if re.match(r'Current conclusion\b', title, re.I)), '')
            if summary := narrative(conclusion):
                candidates.append((date, summary))
        for title, body in sections:
            # Historical event dates are not research-update dates.
            if not re.search(r'\b(update|review|correction|corrected|research|audit|reassessment|findings|evidence|conclusion)\b', title, re.I):
                continue
            if (date := recorded_date(title)) and date[:4] >= '2000':
                if summary := narrative(body):
                    candidates.append((date, summary))
        if candidates:
            date, summary = max(candidates, key=lambda item: item[0])
            updates.append((date, person.get('name') or source.parent.name, summary, person['html_url'], identity_details(person)))
    return sorted(updates, key=lambda item: (item[0], item[1]), reverse=True)


def text(markup: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def entry(date: str, title: str, summary: str, href: str, label: str, identity=None) -> str:
    details = ''
    if identity:
        identifier, dates, places = identity
        details = (
            '<dl class="latest-research-identity">'
            f'<div><dt>Profile</dt><dd><a href="{escape(href, quote=True)}">{escape(identifier)}</a></dd></div>'
            f'<div><dt>Dates</dt><dd>{escape(dates)}</dd></div>'
            f'<div><dt>Places</dt><dd>{escape(places)}</dd></div></dl>'
        )
    return (
        '<article class="latest-research-entry">'
        f'<time datetime="{escape(date)}">{escape(date)}</time><h3>{escape(title)}</h3>'
        + details +
        f'<p>{escape(summary)}</p><a href="{escape(href, quote=True)}">{escape(label)} <span aria-hidden="true">→</span></a>'
        "</article>"
    )


def repair() -> Counter[str]:
    changed: Counter[str] = Counter()
    original = PAGE.read_text(encoding="utf-8")
    page = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\s*", "", original, flags=re.S)
    page = re.sub(
        r'<article class="claim-card"(?: id="change-\d{4}-\d{2}-\d{2}")?>(\s*<p class="kicker">(\d{4}-\d{2}-\d{2})</p>)',
        lambda m: f'<article class="claim-card" id="change-{m.group(2)}">{m.group(1)}', page,
    )
    cards = []
    updates = research_updates()
    for date, name, summary, href, identity in updates:
        cards.append(entry(date, f"Research update: {name}", summary, href, "Read the case and evidence", identity))
    release_pattern = re.compile(
        r'<article class="claim-card" id="change-(\d{4}-\d{2}-\d{2})">\s*<p class="kicker">\1</p>\s*<h2>(.*?)</h2>\s*<ul>(.*?)</ul>', re.S)
    for date, title, bullets in sorted(release_pattern.findall(page), reverse=True):
        notes = [text(value) for value in re.findall(r"<li>(.*?)</li>", bullets, re.S)]
        cards.append(entry(date, text(title), notes[0] if notes else "Release note", f"#change-{date}", "Read the dated release note"))
    feed = f'''{START}
<section class="latest-research" id="latest-research" aria-labelledby="latest-research-title">
  <div class="latest-research-heading"><p class="kicker">Maintained updates</p><h2 id="latest-research-title">Latest research</h2><p>Recent assessments from public case files, using their recorded update dates and source wording. An update is not necessarily a resolved question. Undated cases remain on their individual pages; the original release history and machine sources remain below.</p></div>
  <div class="latest-research-links" aria-label="Research destinations"><a href="/research/">Research workspace</a><a href="/branches/#research-studies">Evidence-led groups</a><a href="/catalogue/">Browse people</a></div>
  <div class="latest-research-grid">{''.join(cards[:12])}</div>
</section>
{END}
'''
    page = re.sub(r'<link\b[^>]*href="/?assets/repair/latest-research\.css(?:\?[^"]*)?"[^>]*>', '', page)
    page = page.replace("</head>", '  <link rel="stylesheet" href="/assets/repair/latest-research.css?v=2">\n</head>', 1)
    if '<div class="question-grid">' not in page:
        raise RuntimeError("Could not find preserved release-history grid")
    page = page.replace('<div class="question-grid">', feed + '<div class="question-grid">', 1)
    if page != original:
        PAGE.write_text(page, encoding="utf-8")
        changed["latest_research"] += 1
    return changed


if __name__ == "__main__":
    print(repair())
