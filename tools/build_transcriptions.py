#!/usr/bin/env python3
"""Build the public Wills & Testaments transcription ledger from saved research."""
from __future__ import annotations

from collections import Counter
from html import escape
import json
from pathlib import Path
import re
try:
    from tools.site_identity import SITE_NAME, page_title
except ModuleNotFoundError:
    from site_identity import SITE_NAME, page_title

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/transcriptions/index.json"
OUT = ROOT / "www/research/transcriptions/index.html"
RESEARCH_SHELL = ROOT / "www/research/index.html"


def extracted_text(item: dict) -> str:
    if not item.get("start"):
        return ""
    source = (ROOT / item["source"]).read_text(encoding="utf-8")
    start = source.find(item["start"])
    if start < 0:
        raise ValueError(f"Missing start marker for {item['id']}")
    start += len(item["start"])
    end = source.find(item["end"], start) if item.get("end") else len(source)
    if end < 0:
        raise ValueError(f"Missing end marker for {item['id']}")
    text = source[start:end].strip()
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[\[([^]|]+)\|([^]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^]]+)\]\]", r"\1", text)
    text = re.sub(r"'{2,5}", "", text)
    return text


def profile_links(profiles: list[list[str]]) -> str:
    return " · ".join(
        f'<a href="https://www.wikitree.com/wiki/{escape(profile_id)}">{escape(name)}</a>'
        for profile_id, name in profiles
    )


def inline(text: str) -> str:
    """Render the limited WikiTree markup used in saved readings, safely."""
    text = re.sub(r"\[\[([^]|]+)\|([^]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^]]+)\]\]", r"\1", text)
    return escape(re.sub(r"'{2,5}", "", text))


def render_table(lines: list[str]) -> str:
    rows, cells, headers = [], [], False
    for raw in lines[1:-1]:
        line = raw.strip()
        if not line or line.startswith("|-"):
            if cells:
                rows.append((headers, cells)); cells = []
            headers = False
        elif line.startswith("!"):
            headers = True
            cells.extend(part.split("|")[-1].strip() for part in line[1:].split("!!"))
        elif line.startswith("|"):
            cells.extend(part.split("|")[-1].strip() for part in line[1:].split("||"))
    if cells:
        rows.append((headers, cells))
    body = []
    for is_header, row in rows:
        tag = "th" if is_header else "td"
        body.append("<tr>" + "".join(f"<{tag}>{inline(cell)}</{tag}>" for cell in row) + "</tr>")
    return '<div class="tx-table-wrap"><table class="tx-table">' + "".join(body) + "</table></div>"


def render_reading(text: str) -> str:
    """Separate saved manuscript excerpts from modern notes without inventing text."""
    lines, output, paragraph, quote = text.splitlines(), [], [], []
    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph = []
    def flush_quote():
        nonlocal quote
        if quote:
            output.append('<blockquote class="tx-source-excerpt"><p>' + "<br>".join(inline(line) for line in quote) + "</p></blockquote>")
            quote = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("{|"):
            flush_paragraph(); flush_quote(); end = index + 1
            while end < len(lines) and not lines[end].startswith("|}"):
                end += 1
            output.append(render_table(lines[index:end + 1])); index = end + 1; continue
        heading = re.match(r"^(={2,4})\s*(.*?)\s*\1$", line)
        if heading:
            flush_paragraph(); flush_quote(); level = min(heading.group(1).count("=") + 1, 5)
            output.append(f"<h{level}>{inline(heading.group(2))}</h{level}>"); index += 1; continue
        if line.startswith(":"):
            flush_paragraph(); quote.append(line[1:].strip()); index += 1; continue
        if line.startswith(("* ", "# ")):
            flush_paragraph(); flush_quote(); items = []
            while index < len(lines) and lines[index].startswith(("* ", "# ")):
                items.append("<li>" + inline(lines[index][2:]) + "</li>"); index += 1
            output.append("<ul>" + "".join(items) + "</ul>"); continue
        if not line.strip():
            flush_paragraph(); flush_quote(); index += 1; continue
        flush_quote(); paragraph.append(line.strip()); index += 1
    flush_paragraph(); flush_quote()
    return "".join(output)


def card(item: dict) -> str:
    full_text = extracted_text(item)
    content = ""
    if full_text:
        content = f'''<details class="tx-reading"><summary>Read saved excerpts and research notes <span>Manuscript wording is set apart; tables and explanatory prose are modern research interpretation.</span></summary><div class="tx-manuscript"><p class="tx-reading-label">Saved working reading</p><p class="tx-key"><span>Manuscript excerpt</span> Historic wording retained, with bracketed uncertainty where saved. <span>Research interpretation</span> Modern explanation, evidence table or editorial context.</p>{render_reading(full_text)}</div></details>'''
    else:
        content = '<p class="tx-no-text"><strong>No full transcription is saved in this repository.</strong> The reviewed conclusion below is a source-checked note, not reconstructed manuscript text.</p>'
    return f'''<article class="tx-card" id="{escape(item['id'])}">
      <header><p class="tx-number">{escape(item['date'])}</p><h2>{escape(item['title'])}</h2><p class="tx-status">{escape(item['status'])}</p></header>
      <dl class="tx-meta"><div><dt>Record</dt><dd>{escape(item['record'])}</dd></div><div><dt>Latest saved review</dt><dd>{escape(item['updated'])}</dd></div><div><dt>Original record access</dt><dd><a href="https://www.scotlandspeople.gov.uk/search-records/legal-records/wills" rel="noopener" target="_blank">Scotland's People wills search</a> <span class="tx-access-note">Search the reference shown above; no direct image URL is recorded here.</span></dd></div><div><dt>Reading provenance</dt><dd>Assisted reading and review are recorded, but the model and individual reviewer are not identified in the saved provenance.</dd></div></dl>
      <p class="tx-summary">{escape(item['summary'])}</p>
      <p class="tx-profiles"><span>Associated profiles</span>{profile_links(item['profiles'])}</p>
      {content}
    </article>'''


def repair() -> Counter:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    cards = "\n".join(card(item) for item in data["attempts"])
    full_count = sum(bool(item.get("start")) for item in data["attempts"])
    main = f'''<main class="r-main tx-main" id="main"><header class="tx-hero"><p class="r-kicker">Research transcriptions</p><h1>Wills &amp; testaments,<br>read with care.</h1><p>Eight source-bounded attempts to read Scottish testament records. They preserve what the manuscript appears to say, what remains unclear, and the profile conclusions that can safely follow.</p><a class="tx-overview" href="{escape(data['overview_url'])}">Open the canonical Wills &amp; Testaments index <span>↗</span></a></header><section class="tx-method" aria-labelledby="method-title"><div><p class="r-kicker">How to read this ledger</p><h2 id="method-title">A working reading is not the record.</h2></div><p>{escape(data['method'])}</p><p><strong>{full_count} full saved readings</strong> are expandable below. The remaining {len(data['attempts']) - full_count} entries preserve only their reviewed conclusions; no manuscript wording has been recreated for them.</p></section><section class="tx-ledger" aria-label="Testament transcription ledger">{cards}</section></main>'''
    shell = RESEARCH_SHELL.read_text(encoding="utf-8")
    shell = re.sub(r"<title>.*?</title>", lambda _: f"<title>{escape(page_title(data['title']))}</title>", shell, count=1)
    shell = shell.replace('data-g-path="/research/index.html"', 'data-g-path="/research/transcriptions/index.html"', 1)
    shell = shell.replace('class="g-unified g-kind-research r-v2 v3-site"', 'class="g-unified g-kind-research r-v2 v3-site tx-page"', 1)
    shell = shell.replace('<link rel="stylesheet" href="/assets/research/research.css?v=3.1-repair-1">', '<link rel="stylesheet" href="/assets/research/research.css?v=3.1-repair-1"><link rel="stylesheet" href="/assets/research/transcriptions.css">', 1)
    main_start = shell.find('<main class="r-main" id="main">')
    if main_start < 0:
        raise ValueError("Research shell main element not found")
    main_end = shell.find('</main>', main_start)
    if main_end < 0:
        raise ValueError("Research shell main close tag not found")
    html = shell[:main_start] + main + shell[main_end + len('</main>'):]
    changed = Counter()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != html:
        OUT.write_text(html, encoding="utf-8")
        changed["transcriptions"] += 1
    return changed


build_saved_ledger = repair


def repair():
    """Keep prior readings available while publishing the maintained original-image reviews."""
    if not any((ROOT / "research/transcriptions").glob("originals-*/*.json")):
        return build_saved_ledger()
    try:
        from tools.publish_testament_reviews import repair as publish_reviews
    except ModuleNotFoundError:
        from publish_testament_reviews import repair as publish_reviews
    return publish_reviews(extracted_text, render_reading)


if __name__ == "__main__":
    print(dict(repair()))
