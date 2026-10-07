"""Maintained records-page markup and assets, shared by generation and repair."""
from collections import Counter
from html import escape
from pathlib import Path
import hashlib
import re


def records_body(records: list[dict]) -> str:
    regions = sorted({r.get('region') or 'Unspecified' for r in records})
    categories = sorted({c for r in records for c in (r.get('record_category') or 'Other records').split(' | ')})
    statuses = Counter(r.get('supporting_source_status') or 'unresolved' for r in records)
    qualities = Counter(r.get('supporting_source_quality') or 'unknown' for r in records)

    def options(values):
        return ''.join(f'<option>{escape(v)}</option>' for v in values)

    quality_names = {'original': 'Original', 'derivative': 'Index / transcription', 'secondary': 'Secondary', 'tree_only': 'Tree / profile only', 'unknown': 'Unclassified'}
    quality_totals = ''.join(f'<li><span>{label}</span><strong>{qualities[key]:,}</strong></li>' for key, label in quality_names.items())
    return f'''<header class="records-hero">
<div><p class="records-eyebrow">Historical records</p><h1>Research records</h1><p class="records-intro">Find the records behind a person, a place or a family story. <a href="/evidence/">How to read the evidence</a> explains the labels on each record.</p></div>
<div class="records-total"><strong>{len(records):,}</strong><span>record entries</span></div>
</header>
<div class="records-status-strip" aria-label="Citation coverage">
<div><span class="record-status-dot explicit" aria-hidden="true"></span><strong>{statuses['explicit']:,}</strong><span>Source cited</span></div>
<div><span class="record-status-dot candidate" aria-hidden="true"></span><strong>{statuses['candidate']:,}</strong><span>Possible source matches</span></div>
<div><span class="record-status-dot unresolved" aria-hidden="true"></span><strong>{statuses['unresolved']:,}</strong><span>Citation needed</span></div>
</div>
<p id="records-scope" class="records-scope" hidden></p>
<section class="record-search-panel" aria-labelledby="records-search-heading">
<h2 id="records-search-heading" class="sr-only">Find records</h2>
<label class="records-query"><span>Search records</span><input id="record-query" type="search" placeholder="Name, WikiTree ID, place or source…" aria-describedby="records-search-hint"></label>
<p id="records-search-hint" class="records-search-hint">Try Glasgow-951, Lisnagaver or marriage. Filters update results as you type.</p>
<div class="records-filter-grid">
<label><span>Region</span><select id="record-region"><option value="">All regions</option>{options(regions)}</select></label>
<label><span>Record type</span><select id="record-category"><option value="">All record types</option>{options(categories)}</select></label>
<label><span>From year</span><input id="record-from" type="number" placeholder="Any" aria-label="From year"></label>
<label><span>To year</span><input id="record-to" type="number" placeholder="Any" aria-label="To year"></label>
<label><span>Source quality</span><select id="record-quality"><option value="">All qualities</option><option value="original">Original</option><option value="derivative">Index / transcription</option><option value="secondary">Secondary</option><option value="tree_only">Tree / profile only</option><option value="unknown">Unclassified</option></select></label>
<label><span>Citation status</span><select id="r-record-citation"><option value="">All statuses</option><option value="explicit">Source cited</option><option value="candidate">Possible source match</option><option value="unresolved">Citation needed</option></select></label>
</div>
<div class="records-filter-footer"><span>Dates and places refer to the person’s recorded event.</span><button id="record-reset" type="button">Clear filters</button></div>
</section>
<div class="records-results-toolbar"><p id="record-count" role="status" aria-live="polite">Loading records…</p><label class="records-sort"><span>Sort by</span><select id="record-sort"><option value="date-asc">Oldest first</option><option value="date-desc">Newest first</option><option value="name">Person name</option></select></label></div>
<noscript><p class="records-empty">Enable JavaScript to search records, or <a href="/data/records-index.json">download the complete records index</a>.</p></noscript>
<div id="record-results" class="record-results" aria-label="Record results"></div>
<details class="records-method"><summary>Understanding the sources</summary><div>
<p>Each entry links a person to an event or record. One document may have entries for several people. <strong>Source cited</strong> means a source reference is attached to the entry. A <strong>possible source match</strong> was found among that person’s saved citations using record type, year and place; it needs checking against the record. <strong>Citation needed</strong> means no sufficiently specific reference has been found.</p>
<ul class="records-quality-totals">{quality_totals}</ul>
<p><a href="/data/source-review.csv">Download the source-review queue →</a></p></div></details>'''


def records_assets(page: str, web: Path) -> str:
    """Wire assets by path, regardless of prior version or attribute order."""
    for source, target in (('record_search.js', 'records/search.js'), ('records.css', 'records/records.css')):
        path = web / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(Path(__file__).with_name(source).read_text(encoding='utf-8') + '\n', encoding='utf-8')
    # The sources shell's initializer belongs only on the sources page.
    page = re.sub(r'<script\b[^>]*\bsrc=["\']/(?:assets/v3/sources|records/search)\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>', '', page, flags=re.I)
    page = re.sub(r'<link\b[^>]*\bhref=["\']/assets/v3/source-library\.css(?:\?[^"\']*)?["\'][^>]*>', '', page, flags=re.I)
    page = re.sub(r'(<div class="g-crumbs">.*?<strong>).*?(</strong>)', r'\1Records\2', page, count=1, flags=re.S)
    page = re.sub(r'<link\b[^>]*\bhref=["\']/records/records\.css(?:\?[^"\']*)?["\'][^>]*>', '', page, flags=re.I)
    for target, closing in (('records/records.css', '</head>'), ('records/search.js', '</body>')):
        version = hashlib.sha256((web / target).read_bytes()).hexdigest()[:10]
        tag = f'<link rel="stylesheet" href="/{target}?v={version}">' if target.endswith('.css') else f'<script defer src="/{target}?v={version}"></script>'
        page = page.replace(closing, tag + closing, 1)
    return page
