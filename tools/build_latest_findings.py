#!/usr/bin/env python3
"""Publish the dated, evidence-led discovery ledger as a searchable table."""
from collections import Counter
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

try:
    from tools.repair_primary_navigation import NAV, render_primary_navigation
    from tools.publish_clean_urls import _with_base
    from tools.site_analytics import with_analytics
except ModuleNotFoundError:
    from repair_primary_navigation import NAV, render_primary_navigation
    from publish_clean_urls import _with_base
    from site_analytics import with_analytics

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
LEDGER = ROOT / 'research/latest-findings.json'
KINDS = {'relationship': 'Family relationships', 'vital': 'Dates & places',
         'property': 'Land & property', 'biographical': 'Life details',
         'record': 'New records', 'dna': 'DNA findings'}
STATUSES = {'confirmed': 'Confirmed', 'qualified': 'Qualified'}
RELATIONSHIPS = {'father': 'Father', 'mother': 'Mother', 'spouse': 'Spouse',
                 'sibling': 'Sibling', 'child': 'Child', 'grandparent': 'Grandparent'}
CHANGE_FIELDS = ('relationship', 'subject', 'relative', 'before', 'after', 'explanation')
PUBLIC_FIELDS = ('id', 'found_on', 'found_from', 'kind', 'finding', 'significance', 'status',
                 'qualification', 'people', 'sources', 'detail_url', 'relationship_changes')


def local_url(value, web):
    if not value.startswith('/') or value.startswith('//') or '..' in Path(value.split('#')[0]).parts:
        raise ValueError(f'Invalid public finding link: {value}')
    path = web / value.split('#')[0].lstrip('/')
    if value.split('#')[0].endswith('/'):
        path /= 'index.html'
    if not path.is_file():
        raise ValueError(f'Missing public finding destination: {value}')


def load_findings(path=LEDGER, web=WEB):
    source = json.loads(path.read_text(encoding='utf-8'))
    rows, seen = [], set()
    for item in source['findings']:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', item['id']) or item['id'] in seen:
            raise ValueError(f'Invalid or repeated finding ID: {item["id"]}')
        seen.add(item['id'])
        if date.fromisoformat(item['found_on']).isoformat() != item['found_on']:
            raise ValueError('Discovery dates must be ISO calendar dates')
        if item.get('found_from') and date.fromisoformat(item['found_from']) > date.fromisoformat(item['found_on']):
            raise ValueError('A research date range must start before it ends')
        if item['kind'] not in KINDS or item['status'] not in STATUSES:
            raise ValueError(f'Unknown finding type/status: {item["id"]}')
        if not item.get('finding') or not item.get('sources'):
            raise ValueError(f'Finding needs a concrete statement and evidence: {item["id"]}')
        if item['status'] == 'qualified' and not item.get('qualification'):
            raise ValueError(f'Qualified finding needs its limitation: {item["id"]}')
        if not any(p.get('id') and item['detail_url'] == f'https://www.wikitree.com/wiki/{p["id"]}' for p in item['people']):
            local_url(item['detail_url'], web)
        for person in item['people']:
            if not person.get('name') or not person.get('url'):
                raise ValueError(f'Named finding subjects need a checked profile/candidate or public draft link: {item["id"]}')
            if person.get('url') and person['url'] != f'https://www.wikitree.com/wiki/{person.get("id", "")}':
                local_url(person['url'], web)
            if person.get('draft_url'):
                local_url(person['draft_url'], web)
        for citation in item['sources']:
            if not re.match(r'^https?://[^/\s]+(?:/|$)', citation['url']):
                raise ValueError(f'Finding source must be an external record URL: {item["id"]}')
        changes = item.get('relationship_changes', [])
        if not isinstance(changes, list):
            raise ValueError('Relationship changes must be a list')
        for change in changes:
            if (change.get('relationship') not in RELATIONSHIPS
                    or change.get('before') not in ('uncertain', 'unknown', 'unmarked')
                    or change.get('after') != 'certain'
                    or not all(change.get(key) for key in ('subject', 'relative', 'explanation', 'previous_status_provenance'))):
                raise ValueError(f'Relationship upgrade needs a documented previous assessment and new certain conclusion: {item["id"]}')
        # Internal provenance/captures are kept only in the maintained ledger.
        public = {key: item[key] for key in PUBLIC_FIELDS if key in item}
        if changes:
            public['relationship_changes'] = [{key: change[key] for key in CHANGE_FIELDS} for change in changes]
        rows.append(public)
    return sorted(rows, key=lambda row: (-date.fromisoformat(row['found_on']).toordinal(), row['id']))


def row_html(item):
    esc = lambda value: escape(str(value), quote=True)
    def person_html(person):
        label = esc(person['name'])
        if person.get('url'):
            external = person['url'].startswith('https://')
            attrs = ' target="_blank" rel="noopener noreferrer"' if external else ''
            label = f'<a href="{esc(person["url"])}"{attrs}>{label}' + (' ↗' if external else '') + '</a>'
        details = ''.join(f'<small>{esc(person[key])}</small>' for key in ('id', 'role') if person.get(key))
        if person.get('draft_url') and person['draft_url'] != person.get('url'):
            details += f'<small><a href="{esc(person["draft_url"])}">Evidence draft</a></small>'
        return f'<li>{label}{details}</li>'
    people = ''.join(person_html(person) for person in item['people'])
    if not people:
        people = '<li class="lf-unmatched">Unnamed record subject</li>'
    sources = ''.join(f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
                      f'{esc(s["title"])} <span aria-hidden="true">↗</span></a></li>' for s in item['sources'])
    day = date.fromisoformat(item['found_on'])
    label = f'{day.day} {day:%b %Y}'
    if item.get('found_from'):
        start = date.fromisoformat(item['found_from'])
        label = f'{start.day}–{day.day} {day:%b %Y}' if (start.year, start.month) == (day.year, day.month) else f'{start.day} {start:%b %Y}–{label}'
    search = ' '.join([item['found_on'], item['finding'], item.get('significance', ''),
                       item.get('qualification', ''), KINDS[item['kind']],
                       *[p['name'] + ' ' + p.get('id', '') for p in item['people']],
                       *[' '.join(str(change[key]) for key in CHANGE_FIELDS) for change in item.get('relationship_changes', [])],
                       *[s['title'] for s in item['sources']]]).casefold()
    significance = f'<p class="lf-significance">{esc(item["significance"])}</p>' if item.get('significance') else ''
    qualification = f'<p>{esc(item["qualification"])}</p>' if item.get('qualification') else ''
    changes = item.get('relationship_changes', [])
    upgrades = ' '.join(sorted({change['relationship'] for change in changes}))
    change_groups = {}
    for change in changes:
        key = tuple(change[field] for field in ('relationship', 'relative', 'before', 'explanation'))
        change_groups.setdefault(key, []).append(change['subject'])
    changes_html = ''
    for (relationship, relative, before, explanation), subjects in change_groups.items():
        subject_names = '; '.join(esc(subject) for subject in subjects)
        change_label = RELATIONSHIPS[relationship] + (' relationships' if len(subjects) > 1 else ' relationship')
        changes_html += (
            f'<div class="lf-relationship-change"><span class="lf-status lf-confirmed">{change_label} became certain</span>'
            f'<p><strong>{subject_names} — {esc(relationship)}: {esc(relative)}.</strong> '
            f'{("Unmarked (previously ungraded)" if before == "unmarked" else before.capitalize())} → Certain. {esc(explanation)}</p></div>')
    external_case = item['detail_url'].startswith('https://')
    case_attributes = ' target="_blank" rel="noopener noreferrer"' if external_case else ''
    case_label = 'Open WikiTree profile ↗' if external_case else 'Read the research →'
    return (f'<tr id="finding-{esc(item["id"])}" data-date="{item["found_on"]}" '
            f'data-kind="{item["kind"]}" data-status="{item["status"]}" data-relationship-upgrade="{upgrades}" data-change-count="{len(changes)}" data-ungraded-count="{sum(c["before"] == "unmarked" for c in changes)}" data-father-count="{sum(c["relationship"] == "father" for c in changes)}" data-father-ungraded-count="{sum(c["relationship"] == "father" and c["before"] == "unmarked" for c in changes)}" data-search="{esc(search)}">'
            f'<td data-label="Found"><a class="lf-date" href="{item.get("_page_url", "/latest-findings/")}#finding-{esc(item["id"])}"><time datetime="{item["found_on"]}">{label}</time></a></td>'
            f'<td data-label="People"><ul class="lf-people">{people}</ul></td>'
            f'<td data-label="Finding"><span class="lf-kind">{KINDS[item["kind"]]}</span><p class="lf-fact">{esc(item["finding"])}</p>{significance}</td>'
            f'<td data-label="Assessment"><span class="lf-status lf-{item["status"]}">{STATUSES[item["status"]]}</span>{qualification}{changes_html}</td>'
            f'<td data-label="Evidence"><ul class="lf-sources">{sources}</ul><a class="lf-case" href="{esc(item["detail_url"])}"{case_attributes}>{case_label}</a></td></tr>')


def render_main(rows, total=None, page_number=1):
    total = len(rows) if total is None else total
    pages = max(1, (total + 49) // 50)
    page_url = lambda n: "/latest-findings/" if n == 1 else f"/latest-findings/page/{n}/"
    options = ''.join(f'<option value="{key}">{label}</option>' for key, label in KINDS.items())
    return f'''<main id="main" class="latest-findings-page" data-lf-total="{total}" data-lf-page="{page_number}">
<header class="lf-intro"><p class="r-kicker">What we have learned</p><h1>Latest findings</h1>
<p class="lf-lede">New records and supported corrections from the Glasgow research, newest first.</p>
<p>Dates show when evidence was found or reviewed. Each finding gives its sources and what remains uncertain.</p>
<p>Use Assessment to find relationships that became certain. <a href="/research/relationship-audit/">Read the historical audit and counts →</a></p></header>
<section class="lf-content" aria-labelledby="lf-table-title"><h2 id="lf-table-title" class="lf-sr-only">Dated research findings</h2>
<form class="lf-controls" id="lf-controls" role="search">
<div class="lf-search"><label for="lf-query">Search findings</label><input type="search" id="lf-query" placeholder="Name, place, record or finding" autocomplete="off"></div>
<div><label for="lf-kind">Finding type</label><select id="lf-kind"><option value="">All types</option>{options}</select></div>
<div class="lf-assessment"><label for="lf-status">Assessment</label><select id="lf-status"><option value="">All findings</option><option value="confirmed">Confirmed</option><option value="qualified">Qualified</option><option value="relationship-certain">Relationships newly certain</option><option value="father-certain">Fathers newly certain</option><option value="relationship-ungraded">Previously ungraded → certain</option></select></div>
<div><label for="lf-order">Order</label><select id="lf-order"><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></div>
<button type="reset" class="lf-reset">Reset</button></form>
<div class="lf-table-heading"><p id="lf-count" role="status" aria-live="polite">{(page_number-1)*50+1}–{(page_number-1)*50+len(rows)} of {total:,} findings · newest first</p>
<p class="lf-key"><span class="lf-status lf-confirmed">Confirmed</span> Supported fact or correction <span class="lf-status lf-qualified">Qualified</span> Evidence or identification has a stated limit</p></div>
<div class="lf-table-wrap"><table class="lf-table"><caption class="lf-sr-only">Concrete findings ordered by research discovery date, newest first. Evidence and limitations accompany each finding.</caption>
<colgroup><col class="lf-col-date"><col class="lf-col-people"><col class="lf-col-finding"><col class="lf-col-assessment"><col class="lf-col-evidence"></colgroup>
<thead><tr><th scope="col">Found</th><th scope="col">People</th><th scope="col">Finding</th><th scope="col">Assessment</th><th scope="col">Evidence</th></tr></thead>
<tbody id="lf-rows">{''.join(row_html(row) for row in rows)}</tbody></table></div>
<noscript><style>.lf-controls{{display:none}}</style></noscript>
<p class="lf-empty" id="lf-empty" hidden>No findings match those filters. Try another name or place, or reset the filters.</p>
<nav class="lf-pagination" id="lf-pagination" aria-label="Finding pages"><a id="lf-prev" href="{page_url(max(1,page_number-1))}" aria-disabled="{str(page_number==1).lower()}">← Previous</a><span id="lf-page">Page {page_number} of {pages}</span><a id="lf-next" href="{page_url(min(pages,page_number+1))}" aria-disabled="{str(page_number==pages).lower()}">Next →</a></nav>
<p class="lf-context">Undated findings remain on the person and family pages. <a href="/changes/">Website change log →</a></p>
</section></main>'''


def repair(web=WEB, ledger=LEDGER):
    changed = Counter()
    if web == WEB and (ROOT / 'research/latest-findings-subjects/subjects.json').exists():
        try:
            from tools.build_research_subject_drafts import build as build_subject_drafts
        except ModuleNotFoundError:
            from build_research_subject_drafts import build as build_subject_drafts
        result = build_subject_drafts()
        if result['changed']:
            changed['subject_draft_pages'] += result['changed']
    rows = load_findings(ledger, web)
    if not rows:
        raise ValueError('The latest-findings page needs reviewed findings')
    for index, row in enumerate(rows):
        row['_page_url'] = '/latest-findings/' if index < 50 else f'/latest-findings/page/{index//50+1}/'
    page = (web / 'about/index.html').read_text(encoding='utf-8')
    page, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: render_main(rows[:50], len(rows)), page, count=1, flags=re.S)
    if count != 1:
        raise ValueError('The site template has no main element')
    page = re.sub(r'<title>.*?</title>', '<title>Latest findings · Glasgow Surname Project</title>', page, count=1, flags=re.S)
    page = re.sub(r'<meta\b[^>]*name="description"[^>]*>', '<meta name="description" content="New Glasgow genealogy findings, with discovery dates, evidence, profile links and clear qualifications.">', page, count=1)
    canonical = '<link rel="canonical" href="https://glasgow.phenotype.dev/latest-findings/">'
    if re.search(r'<link\b[^>]*rel="canonical"[^>]*>', page):
        page = re.sub(r'<link\b[^>]*rel="canonical"[^>]*>', canonical, page, count=1)
    else:
        page = page.replace('</head>', canonical+'</head>', 1)
    page = page.replace('g-kind-about', 'g-kind-latest-findings').replace('data-g-path="/about/index.html"', 'data-g-path="/latest-findings/index.html"')
    page = page.replace('href="#g-page"', 'href="/latest-findings/#g-page"')
    page = re.sub(r'(<div class="g-crumbs">.*?<strong>).*?(</strong>)', r'\1Latest findings\2', page, count=1, flags=re.S)
    page = re.sub(r'<nav class="v3-view-nav".*?</nav>', '', page, count=1, flags=re.S)
    page = NAV.sub(lambda _: render_primary_navigation(Path('latest-findings/index.html')), page, count=1)
    page = _with_base(page, '/latest-findings')
    for extension in ('css', 'js'):
        source = ROOT / 'tools' / f'latest_findings.{extension}'
        content = source.read_text(encoding='utf-8')
        target = web / 'assets/repair' / f'latest-findings.{extension}'
        version = sha256(content.encode()).hexdigest()[:10]
        reference = f'/assets/repair/latest-findings.{extension}?v={version}'
        asset = f'<link rel="stylesheet" href="{reference}">' if extension == 'css' else f'<script src="{reference}" defer></script>'
        closing = '</head>' if extension == 'css' else '</body>'
        page = page.replace(closing, asset + closing, 1)
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8'); changed['latest_findings_assets'] += 1
    # The clean-URL parser normalizes markup; restore the exact managed tag.
    page = with_analytics(page)
    from html.parser import HTMLParser
    class RowAttributes(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'tr': self.attributes = dict(attrs)
    manifest = []
    for row in rows:
        parser = RowAttributes(); parser.feed(row_html(row))
        manifest.append({**parser.attributes, 'url':row['_page_url']})
    data_path = web / 'data/latest-findings-index.json'
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')) + '\n')
    for start in range(0, len(rows), 50):
        number = start//50+1
        rendered = re.sub(r'<main\b[^>]*>.*?</main>', lambda _:render_main(rows[start:start+50], len(rows), number), page, count=1, flags=re.S)
        rendered = rendered.replace('https://glasgow.phenotype.dev/latest-findings/', 'https://glasgow.phenotype.dev'+('/latest-findings/' if number == 1 else f'/latest-findings/page/{number}/'), 1)
        if number == 1:
            esc = lambda value: escape(str(value), quote=True)
            fallback = '<noscript><nav aria-label="Earlier findings"><p>Earlier findings:</p><ul>' + ''.join(f'<li id="finding-{esc(r["id"])}"><a href="{r["_page_url"]}#finding-{esc(r["id"])}">{esc(r["found_on"])}: {esc(r["finding"][:100])}</a></li>' for r in rows[50:]) + '</ul></nav></noscript>'
            rendered = rendered.replace('</main>', fallback+'</main>')
        target = web / ('latest-findings/index.html' if number == 1 else f'latest-findings/page/{number}/index.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != rendered:
            target.write_text(rendered); changed['latest_findings'] += 1
    for stale in (web/'latest-findings/page').glob('*/index.html'):
        if stale.parent.name.isdigit() and int(stale.parent.name)>(len(rows)+49)//50:
            stale.unlink();changed['stale_finding_pages_removed']+=1
    changes_path = web / 'changes/index.html'
    if changes_path.exists():
        original = changes_path.read_text(encoding='utf-8')
        notice = '<p class="lf-changes-link">Looking for new facts? <a href="/latest-findings/">Latest findings: the dated evidence table →</a></p>'
        updated = re.sub(r'<p class="lf-changes-link">.*?</p>', '', original, flags=re.S)
        updated = updated.replace('</h1>', '</h1>' + notice, 1)
        if updated != original:
            changes_path.write_text(updated, encoding='utf-8'); changed['latest_findings_links'] += 1
    return changed


if __name__ == '__main__':
    print(dict(repair()))
