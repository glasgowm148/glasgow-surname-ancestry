#!/usr/bin/env python3
"""Restore migration parity after applying the unified-site presentation layer.

The unified pages are generated artifacts.  This repair is intentionally
idempotent and uses ``www_old`` as the unchanged migration reference without
rebuilding the research catalogue.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import runpy
from urllib.parse import unquote, urlsplit

try:
    from records_page import records_body, records_assets
    from site_analytics import audit as audit_analytics, repair as repair_analytics, with_analytics, without_analytics
    from catalogue_theme import CATALOGUE_ASSET_VERSION, ensure_catalogue_stylesheet, refresh_catalogue_stylesheet_references, write_catalogue_css
except ModuleNotFoundError:
    from tools.records_page import records_body, records_assets
    from tools.site_analytics import audit as audit_analytics, repair as repair_analytics, with_analytics, without_analytics
    from tools.catalogue_theme import CATALOGUE_ASSET_VERSION, ensure_catalogue_stylesheet, refresh_catalogue_stylesheet_references, write_catalogue_css


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
OLD_WEB = ROOT / "www_old"
PERSON_DIR = WEB / "people"
OLD_PERSON_DIR = OLD_WEB / "people"
ARCHIVAL_SNAPSHOTS = ()  # Superseded and tester-level originals are now private.

LOCAL_FILE_LINKS = (
    '<script data-local-file-links>addEventListener("DOMContentLoaded",()=>{'
    'document.querySelectorAll(\'a[href^="#"]\').forEach(a=>{const h=a.getAttribute("href");'
    'if(h&&h!=="#")a.href=location.href.split("#")[0]+h});if(location.protocol!=="file:")return;'
    'document.querySelectorAll(\'a[href^="/"]\').forEach(a=>{const h=a.getAttribute("href"),'
    'm=h.match(/^([^?#]*)(.*)$/),p=m[1];a.href=(p==="/"?"index.html":p.endsWith("/")?'
    'p.slice(1)+"index.html":/\\.[^/]+$/.test(p)?p.slice(1):p.slice(1)+"/index.html")+m[2]})});</script>'
)

LOCAL_LINK_SCRIPT_RE = re.compile(
    r'<script\b[^>]*\bdata-local-file-links(?:\s*=\s*["\'][^"\']*["\'])?[^>]*>.*?</script>',
    re.I | re.S,
)

DESCRIPTION_RE = re.compile(
    r'<meta\b(?=[^>]*\bname\s*=\s*["\']description["\'])[^>]*>', re.I | re.S
)
CANONICAL_RE = re.compile(
    r'<link\b(?=[^>]*\brel\s*=\s*["\']canonical["\'])[^>]*>', re.I | re.S
)
ALTERNATE_RE = re.compile(
    r'<link\b(?=[^>]*\brel\s*=\s*["\']alternate["\'])(?=[^>]*\btype\s*=\s*["\']application/json["\'])[^>]*>',
    re.I | re.S,
)
JSON_LD_RE = re.compile(
    r'<script\b(?=[^>]*\btype\s*=\s*["\']application/ld\+json["\'])[^>]*>.*?</script>',
    re.I | re.S,
)


def _tag(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _metadata_signature(text: str, pattern: re.Pattern[str]):
    """Compare metadata values, not serializer-specific attribute ordering."""
    markup = _tag(text, pattern)
    if markup is None:
        return None

    class Tag(HTMLParser):
        name = None
        attributes = ()

        def handle_starttag(self, name, attributes):
            if self.name is None:
                self.name = name
                self.attributes = tuple(sorted(attributes))

    tag = Tag(convert_charrefs=True)
    tag.feed(markup)
    value = None
    if tag.name == 'script':
        content = markup[markup.index('>') + 1:markup.lower().rfind('</script>')].strip()
        try:
            value = json.loads(content)
        except ValueError:
            value = content
    return tag.name, tag.attributes, value


def _replace_or_add_head(text: str, pattern: re.Pattern[str], value: str) -> str:
    if pattern.search(text):
        return pattern.sub(lambda _: value, text, count=1)
    if "</head>" not in text.lower():
        raise ValueError("HTML document has no closing head")
    return re.sub(r"</head>", value + "</head>", text, count=1, flags=re.I)


def _extract_element(text: str, element: str, element_id: str) -> str | None:
    start_match = re.search(
        rf'<{element}\b(?=[^>]*\bid\s*=\s*["\']{re.escape(element_id)}["\'])[^>]*>',
        text,
        re.I,
    )
    if not start_match:
        return None
    token_re = re.compile(rf'</?{element}\b[^>]*>', re.I)
    depth = 0
    for token in token_re.finditer(text, start_match.start()):
        depth += -1 if token.group(0).startswith("</") else 1
        if depth == 0:
            return text[start_match.start() : token.end()]
    raise ValueError(f"Unclosed {element}#{element_id}")


def _with_local_contract(text: str, base: str, *, fallback: str = "") -> str:
    base_tag = f'<base href="{base}">'
    if re.search(r"<base\s+href=", text, re.I):
        text = re.sub(r'<base\s+href=["\'][^"\']*["\']\s*/?>', base_tag, text, count=1, flags=re.I)
    else:
        text = re.sub(r"<head>", "<head>" + base_tag, text, count=1, flags=re.I)
    if LOCAL_LINK_SCRIPT_RE.search(text):
        text = LOCAL_LINK_SCRIPT_RE.sub(lambda _: LOCAL_FILE_LINKS, text, count=1)
    else:
        text = text.replace(base_tag, base_tag + LOCAL_FILE_LINKS, 1)
    if fallback and "data-local-catalogue-fallback" not in text:
        script = (
            '<script data-local-catalogue-fallback>if(location.protocol==="file:")'
            f'location.replace("{fallback}"+location.search+location.hash);</script>'
        )
        text = text.replace(base_tag, base_tag + script, 1)
    # A base pointing at www makes these work over both HTTP and file://.
    text = re.sub(r'((?:href|src)=["\'])/(assets|people)/', r"\1\2/", text)
    return text


def repair_people() -> Counter[str]:
    changed: Counter[str] = Counter()
    for old_path in OLD_PERSON_DIR.glob("*.html"):
        old = old_path.read_text(encoding="utf-8")
        json_ld = _tag(old, JSON_LD_RE)
        if not json_ld:
            continue
        path = PERSON_DIR / old_path.name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        before = text
        for pattern in (DESCRIPTION_RE, CANONICAL_RE, ALTERNATE_RE, JSON_LD_RE):
            value = _tag(old, pattern)
            if value:
                text = _replace_or_add_head(text, pattern, value)

        old_workbench = _extract_element(old, "section", "profile-workbench")
        if old_workbench and 'id="profile-workbench"' not in text:
            # The page base is the site root, so preserve local and web routing.
            old_workbench = re.sub(r'((?:href|src)=["\'])\.\./', r"\1", old_workbench)
            tools_at = text.find('id="research-tools"')
            actions_at = text.find('<div class="r-actions">', tools_at)
            if tools_at < 0 or actions_at < 0:
                raise ValueError(f"No contextual research-tools insertion point in {path}")
            text = text[:actions_at] + old_workbench + text[actions_at:]
            changed["workbenches"] += 1
        if old_workbench and "profile-creation.js" not in text:
            text = text.replace(
                "</body>",
                '<script defer src="people/profile-creation.js?v=20260831-42"></script></body>',
                1,
            )
        text = _with_local_contract(text, "../")
        if text != before:
            path.write_text(text, encoding="utf-8")
            changed["person_pages"] += 1
    return changed


def _record_summary(rows: list[dict]) -> str:
    citation = Counter(row["supporting_source_status"] for row in rows)
    quality = Counter(row["supporting_source_quality"] for row in rows)
    values = (
        (citation["candidate"], "Candidate source links"),
        (citation["explicit"], "Explicit source links"),
        (citation["unresolved"], "Unresolved source links"),
        (quality["derivative"], "Derivative"),
        (quality["original"], "Original"),
        (quality["secondary"], "Secondary"),
        (quality["tree_only"], "Tree only"),
        (quality["unknown"], "Unknown"),
    )
    cards = "".join(
        f'<div style="display:flex;align-items:baseline;gap:6px"><strong>{count:,}</strong> <span>{label}</span></div>'
        for count, label in values
    )
    return (
        '<div class="quality-summary r-record-quality-summary" aria-label="Source link and quality totals" style="display:flex;flex-wrap:wrap;gap:10px 24px;margin:18px 0">'
        + cards
        + "</div>"
        '<details class="r-disclosure r-record-source-method"><summary>How source matching works</summary>'
        '<div class="disclosure-body"><p>An explicit source was attached directly to the mapped association. '
        'A candidate source was conservatively matched from that person’s captured citations using record type, '
        'year and place; it remains a lead until inspected. Unresolved means the catalogue has not found a '
        'sufficiently specific citation.</p><p><a href="/data/source-review.csv">Download the source-review queue</a>.</p>'
        "</div></details>"
    )


def repair_records_shell() -> Counter[str]:
    """Put the generated record-search body in the shared research shell only."""
    changed: Counter[str] = Counter()
    page_path = WEB / "records/index.html"
    existing = page_path.read_text(encoding="utf-8")
    records_main = re.search(r"<main\b[\s\S]*?</main>", existing, flags=re.I)
    shell = (WEB / "sources/index.html").read_text(encoding="utf-8")
    shell_main = re.search(r"<main\b[\s\S]*?</main>", shell, flags=re.I)
    if not records_main or not shell_main:
        raise ValueError("records or unified research shell has no main container")
    rows = json.loads((WEB / "data/records-index.json").read_text(encoding="utf-8"))
    main = f'<main id="main" class="r-main v3-records">{records_body(rows)}</main>'
    page = shell[:shell_main.start()] + main + shell[shell_main.end():]
    page = re.sub(r'<body\b[^>]*>', '<body data-r-integrated="3" class="g-unified g-kind-research r-v2 v3-site" data-g-path="/records/index.html" data-v3="true" data-repair="3.1-repair-1">', page, count=1, flags=re.I)
    title = _tag(existing, re.compile(r"<title\b[^>]*>[\s\S]*?</title>", re.I))
    description = _tag(existing, DESCRIPTION_RE)
    canonical = _tag(existing, CANONICAL_RE) or '<link rel="canonical" href="https://glasgow.phenotype.dev/records/">'
    for pattern, value in ((re.compile(r"<title\b[^>]*>[\s\S]*?</title>", re.I), title), (DESCRIPTION_RE, description), (CANONICAL_RE, canonical)):
        if value:
            page = _replace_or_add_head(page, pattern, value)
    page = with_analytics(records_assets(page, WEB))
    if page != existing:
        page_path.write_text(page, encoding="utf-8")
        changed["records_unified_shell"] += 1
    return changed


def repair_records() -> Counter[str]:
    changed: Counter[str] = Counter()
    source_path = WEB / "data/records-index.json"
    compact_path = WEB / "assets/research/record-index.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    compact = json.loads(compact_path.read_text(encoding="utf-8"))
    citation_by_id = {row["record_id"]: row["supporting_source_status"] for row in source}
    for row in compact:
        row["citation"] = citation_by_id[row["id"]]
    encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    if compact_path.read_text(encoding="utf-8") != encoded:
        compact_path.write_text(encoded, encoding="utf-8")
        changed["record_index"] += 1

    page_path = WEB / "records/index.html"
    page = page_path.read_text(encoding="utf-8")
    before = page
    if 'id="record-query"' in page:
        changed.update(repair_records_shell())
        return changed
    quality = (
        '<label class="r-field">Source quality<select id="r-record-quality">'
        '<option value="">All source qualities</option><option value="original">Original</option>'
        '<option value="derivative">Index / transcription</option><option value="secondary">Secondary</option>'
        '<option value="tree_only">Tree / profile only</option><option value="unknown">Unclassified</option>'
        "</select></label>"
    )
    page, count = re.subn(
        r'<label class="r-field">Source quality<select id="r-record-quality">.*?</select></label>',
        quality,
        page,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise ValueError("Could not locate record source-quality selector")
    if 'id="r-record-citation"' not in page:
        citation = (
            '<label class="r-field">Citation status<select id="r-record-citation">'
            '<option value="">All citation statuses</option><option value="explicit">Explicit source</option>'
            '<option value="candidate">Candidate match</option><option value="unresolved">Citation unresolved</option>'
            "</select></label>"
        )
        page = page.replace(quality, quality + citation, 1)
    marker = '<p class="r-caption">These are source associations'
    summary = _record_summary(source)
    if "r-record-quality-summary" in page:
        page = re.sub(
            r'<div class="quality-summary r-record-quality-summary".*?</details>',
            summary,
            page,
            count=1,
            flags=re.S,
        )
    elif marker in page:
        page = page.replace(marker, summary + marker, 1)
    else:
        raise ValueError("Could not locate record explanatory text")
    if page != before:
        page_path.write_text(page, encoding="utf-8")
        changed["records_page"] += 1

    views_path = WEB / "assets/research/views.js"
    views = views_path.read_text(encoding="utf-8")
    before = views
    views = views.replace(
        "quality:$('#r-record-quality'),historical:$('#r-record-historical')",
        "quality:$('#r-record-quality'),citation:$('#r-record-citation'),historical:$('#r-record-historical')",
        1,
    )
    if "function citationLabel(" not in views:
        old_row = re.search(r"function recordRow\(r\)\{.*?\n", views)
        if not old_row:
            raise ValueError("Could not locate record row renderer")
        row = old_row.group(0).replace(
            "${badge(r.status)}",
            "${badge(r.status)}<span class=\"r-chip\">${esc(citationLabel(r.citation))}</span>",
        )
        views = views[: old_row.start()] + (
            "function citationLabel(value){return ({explicit:'Explicit source',candidate:'Candidate source',"
            "unresolved:'Citation unresolved'})[value]||'Citation status unknown'}\n" + row
        ) + views[old_row.end() :]
    if views != before:
        views_path.write_text(views, encoding="utf-8")
        changed["record_view"] += 1

    worker_path = WEB / "assets/research/search-worker.js"
    worker = worker_path.read_text(encoding="utf-8")
    before = worker
    worker = worker.replace("r.title,r.status].join(' ')", "r.title,r.status,r.citation].join(' ')", 1)
    worker = worker.replace(
        "(!m.quality||r.quality===m.quality)&&(!m.historical",
        "(!m.quality||r.quality===m.quality)&&(!m.citation||r.citation===m.citation)&&(!m.historical",
        1,
    )
    worker = worker.replace(
        "(!m.category||r.category===m.category)",
        "(!m.category||r.category.split(' | ').includes(m.category))",
        1,
    )
    worker = worker.replace(
        "[...new Set(recordRows.map(r=>r.category))]",
        "[...new Set(recordRows.flatMap(r=>r.category.split(' | ')))]",
        1,
    )
    if worker != before:
        worker_path.write_text(worker, encoding="utf-8")
        changed["record_worker"] += 1
    return changed


def repair_catalogue() -> Counter[str]:
    """Make the complete research catalogue the primary clean-route experience."""
    changed: Counter[str] = Counter()
    write_catalogue_css(PERSON_DIR / "catalogue.css")
    source = (WEB / "catalogue.html").read_text(encoding="utf-8")
    nav = (
        '<nav class="v3-view-nav" aria-label="Section views">'
        '<a href="/catalogue/" aria-current="page">People</a><a href="/onetree/">Family atlas</a>'
        '<a href="/branches/">Families &amp; places</a><a href="/map/">Map</a>'
        '<a href="/early-records/">Early records</a><a href="/connections/">Connections</a></nav>'
    )
    for relative in ("catalogue/index.html", "catalogue/advanced.html"):
        fallback = "../catalogue.html" if relative == "catalogue/index.html" else ""
        page = _with_local_contract(source, "../", fallback=fallback)
        page = re.sub(
            r'<link\b[^>]*\brel=["\']canonical["\'][^>]*>',
            '<link href="https://glasgow.phenotype.dev/catalogue/" rel="canonical">',
            page,
            count=1,
            flags=re.I,
        )
        page = re.sub(
            r'data-g-path=["\'][^"\']+["\']', f'data-g-path="/{relative}"', page, count=1
        )
        page = page.replace('<div class="g-page" id="g-page" tabindex="-1">\n<main>', '<div class="g-page" id="g-page" tabindex="-1">\n' + nav + '<main>', 1)
        page = page.replace(
            'href="/catalogue/advanced.html?', 'href="/catalogue/?'
        )
        path = WEB / relative
        if not path.exists() or path.read_text(encoding="utf-8") != page:
            path.write_text(page, encoding="utf-8")
            changed["catalogue_pages"] += 1

    # The catalogue builder owns the search body, but its standalone shell is
    # legacy.  Put that body inside the same unified shell used by the current
    # homepage and person dossiers so /catalogue/ cannot silently regress.
    source = (WEB / "catalogue.html").read_text(encoding="utf-8")
    catalogue_main = re.search(r"<main\b[\s\S]*?</main>", source, flags=re.I)
    unified = (WEB / "index.html").read_text(encoding="utf-8")
    shell_main = re.search(r"<main\b[\s\S]*?</main>", unified, flags=re.I)
    if not catalogue_main or not shell_main:
        raise ValueError("catalogue or unified main container not found")
    page = unified[:shell_main.start()] + catalogue_main.group(0) + unified[shell_main.end():]
    page = re.sub(r'<body\b[^>]*>', '<body data-r-integrated="3" class="g-unified g-kind-catalogue r-v2 v3-site" data-g-path="/catalogue/" data-v3="true" data-repair="3.1-repair-1">', page, count=1, flags=re.I)
    page = page.replace('<main>', '<main id="main" class="r-main v3-catalogue">', 1)
    page = page.replace('<head>', '<head><base href="/">', 1)
    # The maintained catalogue stylesheet supplies layout and the light palette.
    # Keep it before the shared shell rules for the shared navigation and cards.
    page = ensure_catalogue_stylesheet(page)
    page = page.replace(
        '</head>',
        '<style id="catalogue-unified-overrides">'
        '.g-kind-catalogue .catalogue-statistics{background:var(--g-surface);border:1px solid var(--g-line);border-radius:8px;box-shadow:none;color:var(--g-ink)}'
        '.g-kind-catalogue .catalogue-statistics h2{color:var(--g-ink)}'
        '.g-kind-catalogue .statistics-summary>div{background:#f7f8f0;color:var(--g-ink);border-color:var(--g-line)}'
        '.g-kind-catalogue .statistics-summary strong{color:var(--g-forest)}'
        '.g-kind-catalogue .statistics-summary span,.g-kind-catalogue .statistics-panel p,.g-kind-catalogue .statistics-caution{color:var(--g-muted)}'
        '.g-kind-catalogue .statistics-panel{background:var(--g-surface);border-color:var(--g-line);color:var(--g-ink)}'
        '.g-kind-catalogue .statistics-panel h3{color:var(--g-ink)}'
        '.g-kind-catalogue .statistics-bars li{border-color:var(--g-line)}'
        '.g-kind-catalogue #statistics-detail,.g-kind-catalogue #statistics-detail>summary{background:#f1f3e9;color:var(--g-ink);border-color:var(--g-line)}'
        '.g-kind-catalogue .catalogue-featured .browse-card,.g-kind-catalogue .catalogue-legend,.g-kind-catalogue .browse-section,.g-kind-catalogue .catalogue-about{background:var(--g-surface);border-color:var(--g-line);color:var(--g-ink)}'
        '.g-kind-catalogue .catalogue-featured .browse-card strong,.g-kind-catalogue .catalogue-legend strong{color:var(--g-ink)}'
        '.g-kind-catalogue .strong-match-preview,.g-kind-catalogue .wikitree-update-preview,.g-kind-catalogue .profile-workbench,.g-kind-catalogue .candidate-tabs,.g-kind-catalogue .candidate-card,.g-kind-catalogue .candidate-analysis{background:var(--g-surface);border-color:var(--g-line);color:var(--g-ink);box-shadow:none}'
        '.g-kind-catalogue .wikitree-update-grid article,.g-kind-catalogue .strong-match-grid article{background:var(--g-surface)!important;border-color:var(--g-line)!important;color:var(--g-ink)!important;box-shadow:none}'
        '.g-kind-catalogue .wikitree-update-grid article h3,.g-kind-catalogue .strong-match-grid article h4,.g-kind-catalogue .wikitree-update-grid article a,.g-kind-catalogue .strong-match-grid article a{color:var(--g-forest)!important}'
        '.g-kind-catalogue .wikitree-update-grid article p,.g-kind-catalogue .strong-match-grid article p,.g-kind-catalogue .strong-match-grid article small{color:var(--g-muted)!important}'
        '.g-kind-catalogue .strong-match-grid li{border-color:var(--g-line)!important}'
        '.g-kind-catalogue .strong-match-preview h3,.g-kind-catalogue .wikitree-update-preview h2,.g-kind-catalogue .candidate-card h4,.g-kind-catalogue .candidate-role-group>h4{color:var(--g-ink)}'
        '.g-kind-catalogue .strong-match-preview p,.g-kind-catalogue .wikitree-update-preview p,.g-kind-catalogue .candidate-card p,.g-kind-catalogue .candidate-card li,.g-kind-catalogue .match-clue-list li{color:var(--g-muted)}'
        '.g-kind-catalogue .legend-grid p,.g-kind-catalogue .search-result,.g-kind-catalogue .catalogue-result-card,.g-kind-catalogue .page-disclosure{background:var(--g-surface);border-color:var(--g-line);color:var(--g-ink)}'
        '.g-kind-catalogue .table-wrap,.g-kind-catalogue table{background:var(--g-surface);border-color:var(--g-line);color:var(--g-ink)}'
        '.g-kind-catalogue th,.g-kind-catalogue .catalogue-results-table th,.g-kind-catalogue .catalogue-location-group th,.g-kind-catalogue .catalogue-family-group th{background:#e8eddf!important;color:var(--g-ink)!important;border-color:var(--g-line)!important;position:sticky;top:0}'
        '.g-kind-catalogue .catalogue-sort{background:transparent!important;color:var(--g-ink)!important}'
        '.g-kind-catalogue td{background:var(--g-surface);color:var(--g-ink);border-color:var(--g-line)}'
        '.g-kind-catalogue .catalogue-results-table td:first-child{background:var(--g-surface)}'
        '.g-kind-catalogue .catalogue-location-card-heading,.g-kind-catalogue .catalogue-family-group th,.g-kind-catalogue .catalogue-location-path-group th{background:#e8eddf!important;color:var(--g-ink)!important}'
        '.g-kind-catalogue .catalogue-family-toggle,.g-kind-catalogue .catalogue-tree-context-controls{background:#f1f3e9;color:var(--g-ink);border-color:var(--g-line)}'
        '.g-kind-catalogue .catalogue-group-controls,.g-kind-catalogue .catalogue-result-options{color:var(--g-ink)}'
        '.g-kind-catalogue .catalogue-result-options select,.g-kind-catalogue .catalogue-search select{background:var(--g-surface);color:var(--g-ink);border-color:var(--g-line)}'
        '.g-kind-catalogue .catalogue-result-toolbar{color:var(--g-ink)}'
        '.g-kind-catalogue .catalogue-gender-toggle{display:flex;align-items:center;gap:0;min-height:38px;padding:3px;border:1px solid var(--g-line);border-radius:999px;background:#f1f3e9;color:var(--g-ink)}'
        '.g-kind-catalogue .catalogue-gender-toggle>span{margin:0 8px 0 9px;color:var(--g-muted);font-size:.72rem;font-weight:850;text-transform:uppercase}'
        '.g-kind-catalogue .catalogue-gender-toggle label{display:flex;align-items:center;cursor:pointer}'
        '.g-kind-catalogue .catalogue-gender-toggle input{position:absolute;opacity:0;pointer-events:none}'
        '.g-kind-catalogue .catalogue-gender-toggle label span{padding:7px 10px;border-radius:999px;color:var(--g-muted);font-size:.75rem;font-weight:800}'
        '.g-kind-catalogue .catalogue-gender-toggle label:has(input:checked) span{background:var(--g-forest);color:#fff}'
        '</style></head>',
        1,
    )
    page = page.replace('</body>', f'<script src="/people/external-links.js?v={CATALOGUE_ASSET_VERSION}" defer></script><script src="/people/search.js?v={CATALOGUE_ASSET_VERSION}" defer></script></body>', 1)
    path = WEB / "catalogue/index.html"
    if path.read_text(encoding="utf-8") != page:
        path.write_text(page, encoding="utf-8")
        changed["catalogue_unified_shell"] += 1
    changed["catalogue_asset_versions"] += refresh_catalogue_stylesheet_references(WEB)
    return changed


def repair_ui_regressions() -> Counter[str]:
    """Reapply shared interaction and layout fixes after presentation rebuilds."""
    changed: Counter[str] = Counter()

    home_path = WEB / "assets/research/home.js"
    home = home_path.read_text(encoding="utf-8")
    before = home
    if "const small=w<460,ww=small?100:126,hh=49;" in home:
        home = home.replace(
            "const small=w<460,ww=small?100:126,hh=49;",
            "const small=w<460,ww=small?100:126,hh=g=>g.id==='other'||g.id==='ireland'?70:49;",
            1,
        )
        home = home.replace("h-hh-8,oy+y*k-hh/2", "h-hh(g)-8,oy+y*k-hh(g)/2", 1)
        home = home.replace("lane[i-1].top+hh+5", "lane[i-1].top+hh(lane[i-1].g)+5", 1)
        home = home.replace(
            "lane.at(-1).top>h-hh-6", "lane.at(-1).top+hh(lane.at(-1).g)>h-6", 1
        )
        home = home.replace(
            "lane.at(-1).top=h-hh-6", "lane.at(-1).top=h-hh(lane.at(-1).g)-6", 1
        )
        home = home.replace("lane[i+1].top-hh-5", "lane[i+1].top-hh(lane[i].g)-5", 1)
    if home != before:
        home_path.write_text(home, encoding="utf-8")
        changed["canopy_labels"] += 1

    css_path = WEB / "assets/repair/site.css"
    css = css_path.read_text(encoding="utf-8")
    before = css
    css_marker = "/* Unified regression repairs: fragments, dossiers, atlas exits and timeline index. */"
    if css_marker not in css:
        css += (
            "\n" + css_marker + "\n"
            ".v3-site .v3-dossier>.v3-evidence-fold,.v3-site .v3-dossier .v3-section>.v3-evidence-fold{padding-inline:18px}\n"
            ".v3-site .v3-dossier>.v3-evidence-fold[open],.v3-site .v3-dossier .v3-section>.v3-evidence-fold[open]{padding-bottom:18px}\n"
            ".v3-site.g-kind-tree .repair-atlas-project-links{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-left:auto}\n"
            ".v3-site.g-kind-tree .repair-atlas-project-links a{font:500 11px/1.5 var(--g-sans);color:#3f6046}\n"
            "body.g-kind-timeline{overflow:visible!important}\n"
            ".g-kind-timeline .g-timeline-jumps{box-shadow:0 5px 14px #263f3510}\n"
            "@media(max-width:760px){.v3-site .v3-dossier>.v3-evidence-fold,.v3-site .v3-dossier .v3-section>.v3-evidence-fold{padding-inline:14px}.v3-site.g-kind-tree .repair-atlas-project-links{width:100%;margin-left:0;gap:12px}}\n"
        )
    if "#catalogue-results{scroll-margin-top:" not in css:
        css += "\n#catalogue-results{scroll-margin-top:calc(var(--g-bar) + 18px)}\n"
    if "body.g-kind-timeline{overflow:visible!important}" not in css:
        css += "\nbody.g-kind-timeline{overflow:visible!important}\n"
    if css != before:
        css_path.write_text(css, encoding="utf-8")
        changed["shared_layout"] += 1

    atlas_path = WEB / "onetree/index.html"
    atlas = atlas_path.read_text(encoding="utf-8")
    before = atlas
    atlas = atlas.replace(
        '<button class="active" data-view="lanes" id="view-lanes" role="tab"',
        '<button data-view="lanes" id="view-lanes" role="tab"',
        1,
    ).replace(
        '<button data-view="all" id="view-all" role="tab"',
        '<button class="active" data-view="all" id="view-all" role="tab"',
        1,
    )
    if 'class="repair-atlas-project-links"' not in atlas:
        atlas = atlas.replace(
            '<a href="/connections/">Find a connection</a></div>',
            '<a href="/connections/">Find a connection</a><nav class="repair-atlas-project-links" '
            'aria-label="Leave the atlas"><a href="/">Project home</a><a href="/catalogue/">People</a>'
            '<a href="/map/">Map</a><a href="/timeline/">Timeline</a><a href="/research/">Research</a></nav></div>',
            1,
        )
    if atlas != before:
        atlas_path.write_text(atlas, encoding="utf-8")
        changed["atlas_navigation"] += 1

    for relative in ("assets/research/atlas.js", "assets/research/atlas-standalone.html"):
        atlas_script_path = WEB / relative
        atlas_script = atlas_script_path.read_text(encoding="utf-8")
        before = atlas_script
        atlas_script = atlas_script.replace(
            "const geoKey=k=>geoMap.has(k)?k:'other';",
            "const geoKey=k=>{const id=String(k??'').replace(/^@geo-/,'');return geoMap.has(id)?id:'other'};",
            1,
        )
        atlas_script = atlas_script.replace(
            "function highlightGeo(id){state.geo=id==='all'?null:id;",
            "function highlightGeo(id){state.geo=id==='all'?null:geoKey(id);",
            1,
        )
        atlas_script = atlas_script.replace(
            "else if(h.type==='geo'){const g=geoMap.get(h.id);t.innerHTML=",
            "else if(h.type==='geo'){const g=geoMap.get(geoKey(h.id));if(!g){hideTooltip();return}t.innerHTML=",
            1,
        )
        atlas_script = atlas_script.replace(
            "else{const p=P.get(h.id);if(!p)return;const d=state.pins?DNA.get(p.id):null;",
            "else{const p=P.get(h.id);if(!p){hideTooltip();return}const d=state.pins?DNA.get(p.id):null;",
            1,
        )
        # The Canopy (radial "all" view) is the Atlas default; the family-lanes
        # timeline remains one tab away.
        for old, new in (
            ("let state={view:'lanes',early:false", "let state={view:'all',early:false"),
            # People without a catalogue page (catalogueId null) link to WikiTree, not a 404.
            ("const catalogue=p=>'/people/'+encodeURIComponent(p.catalogueId||p.id.toLowerCase())+'.html';",
             "const catalogue=p=>p.catalogueId===null?'https://www.wikitree.com/wiki/'+encodeURIComponent(p.id):'/people/'+encodeURIComponent(p.catalogueId||p.id.toLowerCase())+'.html';"),
            ('<a href="${esc(catalogue(p))}" target="_blank" rel="noopener noreferrer">Catalogue ${icon(\'out\')}</a>',
             '${p.catalogueId===null?\'\':`<a href="${esc(catalogue(p))}" target="_blank" rel="noopener noreferrer">Catalogue ${icon(\'out\')}</a>`}'),
            ('<p><a href="${esc(catalogue(p))}" target="_blank" rel="noopener noreferrer">Open the complete dossier ↗</a></p>',
             '${p.catalogueId===null?\'<p>No catalogue dossier has been published for this person yet.</p>\':`<p><a href="${esc(catalogue(p))}" target="_blank" rel="noopener noreferrer">Open the complete dossier ↗</a></p>`}'),
            ("lanes=makeLanes(state.laneSort);scene=lanes;syncUI();", "lanes=makeLanes(state.laneSort);scene=atlas;syncUI();"),
            ("$('#home').onclick=()=>goView('lanes');$('#brand').onclick=e=>{e.preventDefault();goView('lanes')};",
             "$('#home').onclick=()=>goView('all');$('#brand').onclick=e=>{e.preventDefault();goView('all')};"),
        ):
            atlas_script = atlas_script.replace(old, new, 1)
        if atlas_script != before:
            atlas_script_path.write_text(atlas_script, encoding="utf-8")
            changed["atlas_interactions"] += 1

    map_path = WEB / "assets/research/map.js"
    map_js = map_path.read_text(encoding="utf-8")
    before = map_js
    map_js = map_js.replace(
        "const [ps,world]=await Promise.all([R.json('/assets/research/map-points.json'),R.json('/assets/research/world.json')]);",
        "const [ps,world,britishIsles]=await Promise.all([R.json('/assets/research/map-points.json'),R.json('/assets/research/world.json'),R.json('/assets/repair/british-isles-50m.json')]);",
        1,
    )
    old_land = "points=ps.map((p,i)=>({...p,key:'loc-'+p.lat+'-'+p.lon}));land=world.map("
    if old_land in map_js:
        detailed_land = (
            "points=ps.map((p,i)=>({...p,key:'loc-'+p.lat+'-'+p.lon}));const bounds=polys=>{const rows=polys.flat(2),"
            "xs=rows.map(p=>p[0]),ys=rows.map(p=>p[1]);return [Math.min(...xs),Math.max(...xs),Math.min(...ys),Math.max(...ys)]},"
            "coarseBritish=polys=>{const [x0,x1,y0,y1]=bounds(polys);return x0>-10.2&&x0<-9&&x1>-6.3&&x1<-5.7&&y0>51&&y0<52&&y1>54.7&&y1<55.5||"
            "x0>-8&&x0<-7&&x1>1&&x1<2&&y0>49.5&&y0<50.5&&y1>58&&y1<59};const geography=[...world.filter(polys=>!coarseBritish(polys)),...britishIsles.countries];land=geography.map("
        )
        map_js = map_js.replace(old_land, detailed_land, 1)
    if map_js != before:
        map_path.write_text(map_js, encoding="utf-8")
        changed["map_geography"] += 1
    map_page = WEB / "map/index.html"
    page = map_page.read_text(encoding="utf-8")
    detailed = page.replace(
        "Local geography: Natural Earth. Points: supplied archive.",
        "Local geography: Natural Earth, with 1:50m British Isles detail. Points: supplied archive.",
        1,
    )
    if detailed != page:
        map_page.write_text(detailed, encoding="utf-8")
        changed["map_attribution"] += 1

    catalogue_js_path = WEB / "people/search.js"
    catalogue_js = catalogue_js_path.read_text(encoding="utf-8")
    before = catalogue_js
    if "restoreResultsAnchor=location.hash==='#catalogue-results'" not in catalogue_js:
        catalogue_js = catalogue_js.replace(
            "  let timer;\n", "  let timer;\n  let restoreResultsAnchor=location.hash==='#catalogue-results';\n", 1
        )
        catalogue_js = catalogue_js.replace(
            "    if(options.scroll&&window.matchMedia('(max-width: 800px)').matches){",
            "    if(restoreResultsAnchor){restoreResultsAnchor=false;requestAnimationFrame(()=>out.scrollIntoView({block:'start'}));}\n"
            "    if(options.scroll&&window.matchMedia('(max-width: 800px)').matches){",
            1,
        )
    if catalogue_js != before:
        catalogue_js_path.write_text(catalogue_js, encoding="utf-8")
        changed["catalogue_anchor"] += 1
    return changed


def repair_local_routes() -> Counter[str]:
    changed: Counter[str] = Counter()
    routes = {
        "catalogue.html": ("./", ""),
        "catalogue/index.html": ("../", "../catalogue.html"),
        "catalogue/advanced.html": ("../", ""),
        "timeline/index.html": ("../", ""),
        "ydna/index.html": ("../", ""),
    }
    for relative, (base, fallback) in routes.items():
        path = WEB / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        repaired = _with_local_contract(text, base, fallback=fallback)
        if repaired != text:
            path.write_text(repaired, encoding="utf-8")
            changed["local_routes"] += 1
    index = WEB / "index.html"
    text = index.read_text(encoding="utf-8")
    repaired = re.sub(r"\A(?:\s*<!doctype html>){2,}", "<!DOCTYPE html>", text, count=1, flags=re.I)
    if repaired != text:
        index.write_text(repaired, encoding="utf-8")
        changed["doctype"] += 1
    return changed


def restore_archival_snapshots() -> Counter[str]:
    """Preserve supplied Y-DNA HTML apart from the shared public analytics tag."""
    changed: Counter[str] = Counter()
    for relative in ARCHIVAL_SNAPSHOTS:
        source = OLD_WEB / relative
        target = WEB / relative
        old = with_analytics(source.read_text(encoding="utf-8")).encode("utf-8")
        if not target.exists() or target.read_bytes() != old:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(old)
            changed["archival_snapshots"] += 1
    return changed


def build_free_space_directory() -> Counter[str]:
    """Regenerate the full local reading edition without rebuilding the catalogue."""
    builder = runpy.run_path(str(ROOT / "tools/build_free_space_site.py"))["build"]
    builder()
    return Counter({"free_space_directory": 1})


def repair_project_routes() -> Counter[str]:
    """Expose the research-page directory from the project entry points."""
    changed: Counter[str] = Counter()
    home_path = WEB / "index.html"
    free_count = len(json.loads((WEB / "assets/research/free-space-index.json").read_text(encoding="utf-8")))
    home = home_path.read_text(encoding="utf-8")
    before = home
    if not re.search(r'<nav class="repair-home-routes".*?href="/free-space/"', home, re.S):
        route = (
            '<a href="/free-space/">Free-space Library →'
            f'<small>{free_count} WikiTree research pages</small></a>'
        )
        home, count = re.subn(
            r'(<nav class="repair-home-routes"[^>]*>.*?)(</nav>)',
            lambda match: match.group(1) + route + match.group(2),
            home,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise ValueError("Could not locate homepage project routes")
    home = re.sub(r'<small>\d+ WikiTree research pages</small>', f'<small>{free_count} WikiTree research pages</small>', home, count=1)
    if home != before:
        home_path.write_text(home, encoding="utf-8")
        changed["homepage_routes"] += 1

    research_path = WEB / "research/index.html"
    research = research_path.read_text(encoding="utf-8")
    before = research
    research = re.sub(r"Browse \d+ WikiTree project pages", f"Browse {free_count} local research editions", research)
    if not re.search(r'<div class="repair-research-grid".*?href="/free-space/"', research, re.S):
        card = (
            '<a class="repair-research-card" href="/free-space/">'
            '<h2>Free-space research library</h2>'
            f'<p>Browse {free_count} local research editions covering early bearers, records, family cases and DNA.</p>'
            '<span>Browse the pages →</span></a>'
        )
        research, count = re.subn(
            r'(<div class="repair-research-grid"[^>]*>.*?)(</div><nav class="repair-research-secondary")',
            lambda match: match.group(1) + card + match.group(2),
            research,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise ValueError("Could not locate Research-page card grid")
    research = re.sub(r'Browse \d+ WikiTree project pages', f'Browse {free_count} local research editions', research, count=1)
    research_nav_marker = '<nav class="v3-view-nav" aria-label="Section views"><a href="/research/">Research</a><a href="/free-space/">'
    if research_nav_marker not in research:
        research = research.replace(
            '<nav class="v3-view-nav" aria-label="Section views"><a href="/research/">Research</a>',
            '<nav class="v3-view-nav" aria-label="Section views"><a href="/research/">Research</a><a href="/free-space/">Free-space pages</a>',
            1,
        )
    if 'aria-label="Further research tools"><a href="/free-space/"' not in research:
        research = research.replace(
            'aria-label="Further research tools"><a href="/early-records/">',
            'aria-label="Further research tools"><a href="/free-space/">Free-space pages</a><a href="/early-records/">',
            1,
        )
    if research != before:
        research_path.write_text(research, encoding="utf-8")
        changed["research_routes"] += 1
    return changed


def repair_free_space_search() -> Counter[str]:
    """Install the maintained shared search and its unique public route registry."""
    try:
        from tools.site_search import install_search
    except ModuleNotFoundError:
        from site_search import install_search
    return Counter(install_search(WEB))


def _resolve_public_target(page: Path, href: str, base: str) -> Path | None:
    parsed = urlsplit(unescape(href))
    if parsed.scheme or parsed.netloc or href.startswith(("//", "mailto:", "tel:", "javascript:")):
        return None
    public_path = unquote(parsed.path)
    if not public_path:
        return page
    if public_path.startswith("/"):
        target = WEB / public_path.lstrip("/")
    else:
        target = page.parent / base / public_path
    target = target.resolve()
    try:
        target.relative_to(WEB.resolve())
    except ValueError:
        return target
    if public_path.endswith("/") or target.is_dir():
        return target / "index.html"
    if target.exists():
        return target
    if not target.suffix and target.with_suffix(".html").exists():
        return target.with_suffix(".html")
    if not target.suffix and (target / "index.html").exists():
        return target / "index.html"
    return target


def audit_unified_links() -> tuple[dict[str, int], list[str]]:
    """Check every integrated page, not only the handful of deployment probes."""
    missing_fragments: list[str] = []
    missing_routes: list[str] = []
    pages = anchors = routes = 0
    excluded = {WEB / relative for relative in ARCHIVAL_SNAPSHOTS}
    for page in WEB.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        if "g-unified" not in text or page in excluded:
            continue
        pages += 1
        ids = {unescape(value) for value in re.findall(r'\bid\s*=\s*["\']([^"\']+)', text, re.I)}
        base_match = re.search(r'<base\b[^>]*\bhref\s*=\s*["\']([^"\']*)', text, re.I)
        base = base_match.group(1) if base_match else ""
        hrefs = re.findall(r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']*)', text, re.I)
        for href in hrefs:
            anchors += 1
            if "${" in href or "{{" in href:
                continue
            parsed = urlsplit(unescape(href))
            fragment = unquote(parsed.fragment)
            target = _resolve_public_target(page, href, base)
            if target is None:
                continue
            routes += 1
            try:
                target.relative_to(WEB.resolve())
            except ValueError:
                missing_routes.append(f"{page.relative_to(WEB)} -> {href} (outside site)")
                continue
            if not target.exists():
                missing_routes.append(f"{page.relative_to(WEB)} -> {href}")
                continue
            if fragment and target == page and fragment not in ids:
                missing_fragments.append(f"{page.relative_to(WEB)} -> #{fragment}")
        if base_match and re.search(r'href\s*=\s*["\']#[^"\']+', text, re.I):
            script = LOCAL_LINK_SCRIPT_RE.search(text)
            if not script or 'location.href.split("#")[0]' not in script.group(0):
                missing_fragments.append(f"{page.relative_to(WEB)} -> base breaks same-page fragments")
    details = {
        "unified_pages": pages,
        "unified_anchors": anchors,
        "internal_routes": routes,
        "missing_routes": len(missing_routes),
        "missing_fragments": len(missing_fragments),
    }
    return details, missing_routes + missing_fragments


def audit() -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    old_files = {p.relative_to(OLD_WEB) for p in OLD_WEB.rglob("*") if p.is_file() and p.name != ".DS_Store"}
    new_files = {p.relative_to(WEB) for p in WEB.rglob("*") if p.is_file() and p.name != ".DS_Store"}
    missing = sorted(old_files - new_files)
    if missing:
        failures.append(f"{len(missing)} old public files are missing")

    people = workbenches = drafts = statuses = metadata = local_people = 0
    for old_path in OLD_PERSON_DIR.glob("*.html"):
        old = old_path.read_text(encoding="utf-8")
        if not _tag(old, JSON_LD_RE):
            continue
        people += 1
        path = PERSON_DIR / old_path.name
        if not path.exists():
            continue
        new = path.read_text(encoding="utf-8")
        if all(
            _metadata_signature(new, pattern) == _metadata_signature(old, pattern)
            for pattern in (DESCRIPTION_RE, CANONICAL_RE, ALTERNATE_RE, JSON_LD_RE)
        ):
            metadata += 1
        if re.search(r'<base\b(?=[^>]*\bhref\s*=\s*["\']\.\./["\'])[^>]*>', new, re.I) and LOCAL_LINK_SCRIPT_RE.search(new):
            local_people += 1
        if 'id="profile-workbench"' in old:
            workbenches += 'id="profile-workbench"' in new
            drafts += 'id="profile-draft"' in new
            statuses += 'id="profile-link-status"' in new
    old_workbenches = sum(
        'id="profile-workbench"' in p.read_text(encoding="utf-8") for p in OLD_PERSON_DIR.glob("*.html")
    )
    if metadata != people:
        failures.append(f"person discovery metadata preserved on {metadata}/{people} pages")
    if workbenches != old_workbenches:
        failures.append(f"profile workbenches preserved on {workbenches}/{old_workbenches} pages")
    if local_people != people:
        failures.append(f"local-file contract preserved on {local_people}/{people} person pages")

    shared_data = sorted(
        relative for relative in old_files & new_files if relative.suffix.lower() in {".json", ".csv"}
    )
    changed_data = [
        relative for relative in shared_data if (OLD_WEB / relative).read_bytes() != (WEB / relative).read_bytes()
    ]
    if changed_data:
        failures.append(f"{len(changed_data)} shared JSON/CSV files changed during integration")

    source = json.loads((WEB / "data/records-index.json").read_text(encoding="utf-8"))
    compact = json.loads((WEB / "assets/research/record-index.json").read_text(encoding="utf-8"))
    expected = Counter(row["supporting_source_status"] for row in source)
    actual = Counter(row.get("citation") for row in compact)
    records_page = (WEB / "records/index.html").read_text(encoding="utf-8")
    worker = (WEB / "assets/research/search-worker.js").read_text(encoding="utf-8")
    if expected != actual or 'id="r-record-citation"' not in records_page or "m.citation" not in worker:
        failures.append("record citation status is not fully exposed and filterable")

    local_routes = ("catalogue.html", "catalogue/index.html", "timeline/index.html", "ydna/index.html")
    for relative in local_routes:
        text = (WEB / relative).read_text(encoding="utf-8")
        if "<base href=" not in text or "data-local-file-links" not in text:
            failures.append(f"{relative} lacks its local-file route contract")
    for relative in ARCHIVAL_SNAPSHOTS:
        public_html = without_analytics((WEB / relative).read_text(encoding="utf-8"))
        if public_html != (OLD_WEB / relative).read_text(encoding="utf-8"):
            failures.append(f"{relative} differs from the archival snapshot beyond the shared analytics tag")
    from tools.repair_publication_policy import audit as audit_publication_policy
    failures.extend(audit_publication_policy(WEB))
    if len(re.findall(r"<!doctype html>", (WEB / "index.html").read_text(encoding="utf-8"), re.I)) != 1:
        failures.append("index.html does not have exactly one doctype")

    free_source = json.loads((ROOT / "research/free-space-pages/index.json").read_text(encoding="utf-8"))
    free_rows = json.loads((WEB / "assets/research/free-space-index.json").read_text(encoding="utf-8"))
    free_ids = {row["wikitreeId"] for row in free_rows}
    expected_free_ids = {row["wikitreeId"] for row in free_source["pages"]}
    free_page = (WEB / "free-space/index.html").read_text(encoding="utf-8")
    home_page = (WEB / "index.html").read_text(encoding="utf-8")
    research_page = (WEB / "research/index.html").read_text(encoding="utf-8")
    site_search = (WEB / "assets/unified/site.js").read_text(encoding="utf-8")
    if len(free_rows) < free_source["pageCount"] or not expected_free_ids.issubset(free_ids):
        failures.append("free-space directory does not represent every unique captured page")
    if any(set(row) & {"localFile", "editUrl", "capturedUrl", "sourceLength"} for row in free_rows):
        failures.append("free-space browser index exposes capture internals")
    if any(not row["viewUrl"].startswith("https://www.wikitree.com/wiki/Space:") for row in free_rows):
        failures.append("free-space directory contains a non-canonical WikiTree link")
    if "/free-space/" not in home_page or "/free-space/" not in research_page:
        failures.append("free-space directory is not linked from both project entry points")
    if "free-space-index.json" not in worker or "free-space-index.json" not in site_search:
        failures.append("free-space pages are absent from global search")
    if "research/free-space-pages/" in free_page or "localFile" in free_page:
        failures.append("free-space public page exposes raw capture paths")

    link_summary, link_failures = audit_unified_links()
    if link_failures:
        failures.append(
            f"unified link audit found {len(link_failures)} failures: "
            + "; ".join(link_failures[:8])
        )

    experience_summary, experience_failures = runpy.run_path(str(ROOT / 'tools/audit_site_experience.py'))['audit'](WEB)
    failures.extend(experience_failures)
    analytics_pages, analytics_failures = audit_analytics(WEB)
    if analytics_failures:
        failures.append(f"Google tag missing or duplicated on {len(analytics_failures)} pages")
    summary: dict[str, object] = {
        "analytics_pages": analytics_pages,
        "old_files": len(old_files),
        "missing_old_files": len(missing),
        "person_pages": people,
        "person_metadata": metadata,
        "local_person_pages": local_people,
        "profile_workbenches": workbenches,
        "profile_drafts": drafts,
        "profile_status_controls": statuses,
        "record_citations": dict(sorted(actual.items(), key=lambda item: str(item[0]))),
        "shared_unchanged_data_files": len(shared_data) - len(changed_data),
        "free_space_pages": len(free_rows),
        **experience_summary,
        **link_summary,
    }
    return summary, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Audit only; do not modify www")
    args = parser.parse_args()
    if not WEB.is_dir() or not OLD_WEB.is_dir():
        parser.error("both www and www_old are required")
    changed: Counter[str] = Counter()
    if not args.check:
        changed.update(repair_people())
        changed.update(repair_records())
        changed.update(repair_catalogue())
        changed.update(repair_local_routes())
        changed.update(restore_archival_snapshots())
        changed.update(build_free_space_directory())
        changed.update(repair_project_routes())
        changed.update(repair_free_space_search())
        changed.update(repair_ui_regressions())
        experience = runpy.run_path(str(ROOT / "tools/repair_site_experience.py"))
        changed.update(experience["repair"]())
        for helper in ("repair_timeline_navigation.py", "repair_map_state_fallbacks.py", "repair_map_legacy_routes.py", "repair_early_records.py", "repair_research_groups.py", "repair_family_browsing.py", "build_branches_directory.py", "build_study_pages.py", "build_transcriptions.py", "build_latest_research.py", "build_statistics_page.py", "build_resources_page.py", "repair_profile_wikitree_links.py", "repair_person_hierarchy.py", "repair_primary_navigation.py", "repair_research_questions.py", "repair_exploration_layout.py"):
            presentation = runpy.run_path(str(ROOT / "tools" / helper))
            changed.update(presentation["repair"]())
        death_index = runpy.run_path(str(ROOT / "tools/publish_irish_death_index.py"))
        changed.update(death_index["repair"]())
        opr_deaths = runpy.run_path(str(ROOT / "tools/publish_opr_death_review.py"))
        changed.update(opr_deaths["repair"]())
        opr_marriages = runpy.run_path(str(ROOT / "tools/publish_opr_marriage_review.py"))
        changed.update(opr_marriages["repair"]())
        opr_births = runpy.run_path(str(ROOT / "tools/publish_opr_birth_review.py"))
        changed.update(opr_births["repair"]())
        newspapers = runpy.run_path(str(ROOT / "tools/publish_newspaper_review.py"))
        changed.update(newspapers["repair"]())
        changed.update(repair_analytics(WEB))
        access = runpy.run_path(str(ROOT / 'tools/publish_research_release.py'))
        access['publish']()
    summary, failures = audit()
    if changed:
        print("repaired " + ", ".join(f"{key}={value}" for key, value in sorted(changed.items())))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("Unified-site parity audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
