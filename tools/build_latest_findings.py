#!/usr/bin/env python3
"""Publish the dated, evidence-led discovery ledger as a searchable table."""
from collections import Counter
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

from genealogy.feeds import FeedEntry, atom_feed as shared_atom_feed

try:
    from tools.repair_primary_navigation import NAV, render_primary_navigation
    from tools.publish_clean_urls import _with_base
    from tools.site_analytics import with_analytics
    from tools.evidence_labels import guide_link_html
except ModuleNotFoundError:
    from repair_primary_navigation import NAV, render_primary_navigation
    from publish_clean_urls import _with_base
    from site_analytics import with_analytics
    from evidence_labels import guide_link_html

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
LEDGER = ROOT / 'research/latest-findings.json'
KINDS = {'relationship': 'Family relationships', 'vital': 'Dates & places',
         'property': 'Land & property', 'biographical': 'Life details',
         'record': 'New records', 'dna': 'DNA findings'}
STATUSES = {'confirmed': 'Confirmed', 'qualified': 'Qualified'}
FINDING_LABELS = {'confirmed': 'Finding supported', 'qualified': 'Finding qualified'}
RELATIONSHIPS = {'father': 'Father', 'mother': 'Mother', 'spouse': 'Spouse',
                 'sibling': 'Sibling', 'child': 'Child', 'grandparent': 'Grandparent'}
CHANGE_FIELDS = ('relationship', 'subject', 'relative', 'before', 'after', 'explanation')
PUBLIC_FIELDS = ('id', 'found_on', 'found_from', 'kind', 'finding', 'significance', 'status',
                 'qualification', 'people', 'sources', 'detail_url', 'relationship_changes')
SITE_URL = 'https://glasgow.phenotype.dev'
FEED_URL = '/latest-findings/feed.xml'
FEED_LINK = f'<link rel="alternate" type="application/atom+xml" title="Latest findings · Glasgow Surname Project" href="{FEED_URL}">'
FEED_SIZE = 50
FINDINGS_PER_PAGE = 50
# The opening page shows fewer, keeping it well inside the 500 KB page budget.
LATEST_SHOWN = 30
# Per-subject export for other builders: read it with findings_for().
SUBJECT_INDEX = 'data/findings-by-subject.json'


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
                    or change.get('before') not in ('uncertain', 'unknown', 'unmarked', 'possible', 'probable')
                    or change.get('after') != 'certain'
                    or not all(change.get(key) for key in ('subject', 'relative', 'explanation', 'previous_status_provenance'))):
                raise ValueError(f'Relationship upgrade needs a documented previous assessment and new certain conclusion: {item["id"]}')
        # Internal provenance/captures are kept only in the maintained ledger.
        public = {key: item[key] for key in PUBLIC_FIELDS if key in item}
        if changes:
            public['relationship_changes'] = [{key: change[key] for key in CHANGE_FIELDS} for change in changes]
        rows.append(public)
    return sorted(rows, key=lambda row: (-date.fromisoformat(row['found_on']).toordinal(), row['id']))


def page_url(number):
    return f'/latest-findings/page/{number}/'


def stable_page(index, total, size=FINDINGS_PER_PAGE):
    """The archive page of the finding at ``index`` in newest-first order.

    Pages are numbered from the earliest finding, so a finding's page never
    changes as newer findings are added: page 1 holds the first 50 ever
    recorded, and the highest page fills up before a new one starts.
    """
    return (total - 1 - index) // size + 1


def page_urls(items):
    """Stable ``/latest-findings/page/N/#finding-ID`` links for ledger rows,
    ordered exactly as load_findings orders them."""
    def day(item):
        try:
            return date.fromisoformat(item['found_on']).toordinal()
        except (KeyError, TypeError, ValueError):
            return None
    ordered = sorted((item for item in items if item.get('id') and item.get('finding') and day(item) is not None),
                     key=lambda item: (-day(item), item['id']))
    return {item['id']: f"{page_url(stable_page(index, len(ordered)))}#finding-{item['id']}"
            for index, item in enumerate(ordered)}


def row_html(item):
    esc = lambda value: escape(str(value), quote=True)
    def person_html(person):
        label = esc(person['name'])
        if person.get('url'):
            external = person['url'].startswith('https://')
            attrs = ' target="_blank" rel="noopener noreferrer"' if external else ''
            label = f'<a href="{esc(person["url"])}"{attrs}>{label}' + (' ↗' if external else '') + '</a>'
        details = f'<small>{esc(person["id"])}</small>' if person.get('id') else ''
        if person.get('role'):
            identity_role = bool(person.get('id')) and bool(re.search(r'identity|candidate|identification|match', person['role'], re.I))
            prefix = 'Profile identification: ' if identity_role else ''
            details += f'<small class="lf-person-assessment">{prefix}{esc(person["role"])}</small>'
        if person.get('draft_url') and person['draft_url'] != person.get('url'):
            details += f'<small><a href="{esc(person["draft_url"])}">Evidence draft</a></small>'
        return f'<li>{label}{details}</li>'
    people = ''.join(person_html(person) for person in item['people'])
    if not people:
        people = '<li class="lf-unmatched">Unnamed record subject</li>'
    studies = item.get('_studies') or []
    study_links = ''.join(f'<li><span>{esc(s["type"])}:</span> <a href="{esc(s["url"])}">{esc(s["label"])}</a></li>' for s in studies)
    study_html = f'<ul class="lf-studies" aria-label="Studies this finding concerns">{study_links}</ul>' if study_links else ''
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
                       *[s['title'] for s in item['sources']],
                       *[s['label'] for s in studies], *item.get('_place_names', [])]).casefold()
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
            f'data-kind="{item["kind"]}" data-status="{item["status"]}" data-relationship-upgrade="{upgrades}" data-change-count="{len(changes)}" data-ungraded-count="{sum(c["before"] == "unmarked" for c in changes)}" data-father-count="{sum(c["relationship"] == "father" for c in changes)}" data-father-ungraded-count="{sum(c["relationship"] == "father" and c["before"] == "unmarked" for c in changes)}" data-studies="{esc(' '.join(s['id'] for s in studies))}" data-places="{esc(' '.join(p['slug'] for p in item.get('_places', [])))}" data-search="{esc(search)}">'
            f'<td data-label="Found"><a class="lf-date" href="{item.get("_page_url", "/latest-findings/")}#finding-{esc(item["id"])}"><time datetime="{item["found_on"]}">{label}</time></a></td>'
            f'<td data-label="People"><ul class="lf-people">{people}</ul>{study_html}</td>'
            f'<td data-label="Finding"><span class="lf-kind">{KINDS[item["kind"]]}</span><p class="lf-fact">{esc(item["finding"])}</p>{significance}</td>'
            f'<td data-label="Finding assessment"><span class="lf-status lf-{item["status"]}">{FINDING_LABELS[item["status"]]}</span>{qualification}{changes_html}</td>'
            f'<td data-label="Evidence"><ul class="lf-sources">{sources}</ul><a class="lf-case" href="{esc(item["detail_url"])}"{case_attributes}>{case_label}</a></td></tr>')


def render_main(rows, total=None, page_number=None, studies=(), browse=False, places=()):
    """``page_number`` None renders the newest findings at /latest-findings/;
    a number renders that stable archive page."""
    total = len(rows) if total is None else total
    place_options = ''.join(f'<option value="{escape(p["slug"], quote=True)}">{escape(p["name"])} ({p["count"]})</option>' for p in places)
    place_filter = (f'<div><label for="lf-place">Place</label><select id="lf-place"><option value="">All places</option>{place_options}</select></div>'
                    if place_options else '')
    study_options = ''.join(f'<option value="{escape(s["id"], quote=True)}">{escape(s["label"])} ({s["count"]})</option>' for s in studies)
    study_filter = (f'<div><label for="lf-study">Family or place study</label><select id="lf-study"><option value="">All studies</option>{study_options}</select></div>'
                    if study_options else '')
    routes = (' · <a href="/latest-findings/studies/">Findings by study</a> · <a href="/latest-findings/places/">Findings by place</a>'
              if browse else '')
    follow = f'<p class="lf-follow"><a href="{FEED_URL}">Follow new findings (Atom feed)</a>{routes}</p>'
    pages = max(1, (total + FINDINGS_PER_PAGE - 1) // FINDINGS_PER_PAGE)
    if page_number is None:
        # "Older" continues on the newest archive page unless the opening page
        # already shows all of it, then on the page before.
        on_top_page = total - (pages - 1) * FINDINGS_PER_PAGE
        older = pages if on_top_page > len(rows) else (pages - 1 or None)
        newer = None
        position = f'Newest {len(rows)} of {total:,} findings'
        place_label = 'Latest findings'
    else:
        older = page_number - 1 if page_number > 1 else None
        newer = page_number + 1 if page_number < pages else 0
        position = f'Page {page_number} of {pages}: {len(rows)} findings, newest first'
        place_label = f'Page {page_number} of {pages}'
    nav_link = lambda target, ident, text: (
        f'<a id="{ident}" href="/latest-findings/" aria-disabled="false">{text}</a>' if target == 0 else
        f'<a id="{ident}" href="{page_url(target)}" aria-disabled="false">{text}</a>' if target else
        f'<a id="{ident}" href="/latest-findings/" aria-disabled="true">{text}</a>')
    options = ''.join(f'<option value="{key}">{label}</option>' for key, label in KINDS.items())
    return f'''<main id="main" class="latest-findings-page" data-lf-total="{total}" data-lf-page="{page_number or 'latest'}">
<header class="lf-intro"><p class="r-kicker">What we have learned</p><h1>Latest findings</h1>
<p class="lf-lede">New records and supported corrections from the Glasgow research, newest first.</p>
<p class="lf-progress"><a href="/onetree/progress/?through=1650&amp;links=confident#progress-history">Research progress charts →</a><span>See how father-link confidence and branch connectivity change over time.</span></p>
<p>Dates show when evidence was found or reviewed. Each finding gives its sources and what remains uncertain.</p>
<p>The finding assessment applies to the statement in that row. A supported record fact does not confirm its identification with a linked WikiTree profile. Profile identification limits appear beside the person and in the research.</p>
<p>Use Assessment to find relationships that became certain. <a href="/research/relationship-audit/">Read the historical audit and counts →</a></p>{follow}</header>
<section class="lf-content" aria-labelledby="lf-table-title"><h2 id="lf-table-title" class="lf-sr-only">Dated research findings</h2>
<form class="lf-controls" id="lf-controls" role="search">
<div class="lf-search"><label for="lf-query">Search findings</label><input type="search" id="lf-query" placeholder="Name, place, record or finding" autocomplete="off"></div>
<div><label for="lf-kind">Finding type</label><select id="lf-kind"><option value="">All types</option>{options}</select></div>
<div class="lf-assessment"><label for="lf-status">Assessment</label><select id="lf-status"><option value="">All findings</option><option value="confirmed">Confirmed</option><option value="qualified">Qualified</option><option value="relationship-certain">Relationships newly certain</option><option value="father-certain">Fathers newly certain</option><option value="relationship-ungraded">Previously ungraded → certain</option></select></div>
{study_filter}{place_filter}<div><label for="lf-order">Order</label><select id="lf-order"><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></div>
<button type="reset" class="lf-reset">Reset</button></form>
<div class="lf-table-heading"><p id="lf-count" role="status" aria-live="polite">{position}</p>
<p class="lf-key"><span class="lf-status lf-confirmed">Finding supported</span> Supported fact or correction <span class="lf-status lf-qualified">Finding qualified</span> The finding has a stated evidence or identification limit</p>{guide_link_html("How to read the evidence")}</div>
<div class="lf-table-wrap"><table class="lf-table"><caption class="lf-sr-only">Concrete findings ordered by research discovery date, newest first. Evidence and limitations accompany each finding.</caption>
<colgroup><col class="lf-col-date"><col class="lf-col-people"><col class="lf-col-finding"><col class="lf-col-assessment"><col class="lf-col-evidence"></colgroup>
<thead><tr><th scope="col">Found</th><th scope="col">People</th><th scope="col">Finding</th><th scope="col">Finding assessment</th><th scope="col">Evidence</th></tr></thead>
<tbody id="lf-rows">{''.join(row_html(row) for row in rows)}</tbody></table></div>
<noscript><style>.lf-controls{{display:none}}</style></noscript>
<p class="lf-empty" id="lf-empty" hidden>No findings match those filters. Try another name or place, or reset the filters.</p>
<nav class="lf-pagination" id="lf-pagination" aria-label="Finding pages">{nav_link(newer, 'lf-prev', '← Newer')}<span id="lf-page">{place_label}</span>{nav_link(older, 'lf-next', 'Older →')}</nav>
<p class="lf-context">Archive pages are numbered from the earliest finding, so a finding keeps its page and its link. Undated findings remain on the person and family pages. <a href="/changes/">Website change log →</a></p>
</section></main>'''


def _links_module():
    try:
        import study_place_links
    except ModuleNotFoundError:
        from tools import study_place_links
    return study_place_links


def attach_subjects(rows, web=WEB):
    """Give each finding the people, studies and places it concerns.

    People come from the finding's own profile links. Studies are the written
    family and place studies that list one of those people (or that the finding
    links directly). Places are those where one of those people is recorded.
    Nothing is matched by name.
    """
    links = _links_module()
    studies = links.load_studies(web)
    curated = {s['id']: s for s in studies if s['kind'] in links.STUDY_KINDS}
    index = links.studies_by_person(studies)
    places_by_person = links.person_places(links.load_records(web))
    names = links.load_place_names(web)
    place_exists = lambda slug: (web / 'places' / f'{slug}.html').is_file()
    for row in rows:
        people = []
        for person in row['people']:
            match = re.fullmatch(r'/people/([a-z0-9][a-z0-9_.-]*)\.html', person.get('url', ''))
            slug = match[1] if match else str(person.get('id') or '').lower()
            if slug and slug not in people:
                people.append(slug)
        found = {s['id']: s for s in links.studies_for_people(people, index)}
        for url in [row.get('detail_url', ''), *[p.get('url', '') for p in row['people']]]:
            match = re.fullmatch(r'/branches/([a-z0-9-]+)/', url or '')
            if match and match[1] in curated and match[1] not in found:
                found[match[1]] = {k: v for k, v in curated[match[1]].items() if k != 'members'}
        places = links.places_for_people(people, places_by_person, place_exists=place_exists, names=names)
        row['_people'] = [slug for slug in people if (web / 'people' / f'{slug}.html').is_file()]
        row['_studies'] = sorted(found.values(), key=lambda s: s['label'].casefold())
        row['_places'] = places
        row['_place_names'] = [p['name'] for p in places[:12]]
    return rows


def _summary(text, limit=220):
    text = ' '.join(str(text).split())
    return text if len(text) <= limit else text[:limit].rsplit(' ', 1)[0].rstrip(',;:') + '…'


def subject_index(rows):
    """The per-person, per-study and per-place export other builders read."""
    data = {'schema_version': 1, 'findings': {}, 'people': {}, 'studies': {}, 'places': {}, 'study_pages': {}}
    for row in rows:  # rows are newest first, so every list is newest first
        data['findings'][row['id']] = {'date': row['found_on'], 'url': f"{row['_page_url']}#finding-{row['id']}",
                                       'summary': _summary(row['finding']), 'kind': row['kind'], 'status': row['status']}
        for key, values in (('people', row.get('_people', [])), ('studies', [s['id'] for s in row.get('_studies', [])]),
                            ('places', [p['slug'] for p in row.get('_places', [])])):
            for value in values:
                data[key].setdefault(value, []).append(row['id'])
    data['study_pages'] = {sid: f'/latest-findings/studies/{sid}/' for sid in sorted(data['studies'])}
    return data


def findings_for(subject, kind='people', web=WEB):
    """Findings about one subject, newest first, from the published export.

    ``kind`` is 'people' (a catalogue slug or WikiTree ID such as Glasgow-951),
    'studies' (a study id such as larne-kilwaughter) or 'places' (a place slug).
    Each item has id, date, url (into /latest-findings/), summary, kind and status.
    """
    path = Path(web) / SUBJECT_INDEX
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    key = str(subject).lower() if kind == 'people' else str(subject)
    return [dict(data['findings'][fid], id=fid) for fid in data.get(kind, {}).get(key, []) if fid in data['findings']]


def atom_feed(rows, size=FEED_SIZE):
    """An Atom feed of the newest findings. Deterministic: no build timestamp."""
    entries = []
    for row in rows[:size]:
        people = ', '.join(p['name'] for p in row['people']) or 'Unnamed record subject'
        summary = row['finding'] + (f" Limits: {row['qualification']}" if row.get('qualification') else '') + f' People: {people}.'
        entries.append(FeedEntry(
            id=f'tag:glasgow.phenotype.dev,2026:finding-{row["id"]}', title=f'{row["found_on"]}: {_summary(row["finding"], 110)}',
            link=f'{SITE_URL}{row["_page_url"]}#finding-{row["id"]}', published=row['found_on'], updated=row['found_on'],
            category=(row['kind'], KINDS[row['kind']]), summary=summary))
    return shared_atom_feed(
        title='Latest findings · Glasgow Surname Project',
        subtitle='New records and supported corrections from the Glasgow surname research, newest first.',
        self_url=f'{SITE_URL}{FEED_URL}', alternate=f'{SITE_URL}/latest-findings/', feed_id=f'{SITE_URL}/latest-findings/',
        updated=rows[0]['found_on'] if rows else '2026-01-01', author='Glasgow Surname Project', entries=entries)


def _table(rows):
    return ('<div class="lf-table-wrap"><table class="lf-table"><colgroup><col class="lf-col-date"><col class="lf-col-people"><col class="lf-col-finding"><col class="lf-col-assessment"><col class="lf-col-evidence"></colgroup>'
            '<thead><tr><th scope="col">Found</th><th scope="col">People</th><th scope="col">Finding</th><th scope="col">Finding assessment</th><th scope="col">Evidence</th></tr></thead>'
            f'<tbody>{"".join(row_html(row) for row in rows)}</tbody></table></div>')


def render_study_findings(study, rows):
    """A plain, followable page of the findings about one study (no JavaScript needed)."""
    e = lambda value: escape(str(value), quote=True)
    noun = 'finding' if len(rows) == 1 else 'findings'
    return (f'<main id="main" class="latest-findings-page lf-subject-page"><header class="lf-intro"><p class="r-kicker">Latest findings · {e(study["type"])}</p>'
            f'<h1>{e(study["label"])}: latest findings</h1>'
            f'<p class="lf-lede">{len(rows)} dated {noun} about people in this study, newest first. <a href="{e(study["url"])}">Read the study →</a></p>'
            f'<p class="lf-follow"><a href="/latest-findings/">All latest findings</a> · <a href="/latest-findings/studies/">Other studies</a> · <a href="{FEED_URL}">Follow new findings (Atom feed)</a></p></header>'
            f'<section class="lf-content">{_table(rows)}</section></main>')


def render_study_directory(studies):
    e = lambda value: escape(str(value), quote=True)
    items = ''.join(f'<li><a href="/latest-findings/studies/{e(s["id"])}/">{e(s["label"])}</a> <small>{e(s["type"])} · {s["count"]} finding{"s" if s["count"] != 1 else ""}</small></li>' for s in studies)
    return ('<main id="main" class="latest-findings-page lf-subject-page"><header class="lf-intro"><p class="r-kicker">Latest findings</p><h1>Findings by study</h1>'
            '<p class="lf-lede">Choose a family or place study to see the dated findings about the people it lists. A finding appears under every study that lists one of its people.</p>'
            f'<p class="lf-follow"><a href="/latest-findings/">All latest findings</a> · <a href="/latest-findings/places/">Findings by place</a> · <a href="{FEED_URL}">Follow new findings (Atom feed)</a></p></header>'
            f'<section class="lf-content"><ul class="lf-subject-list">{items}</ul></section></main>')


def render_place_directory(rows):
    """Findings grouped by the places where their people are recorded, as anchor lists."""
    e = lambda value: escape(str(value), quote=True)
    by_place, names = {}, {}
    for row in rows:
        for place in row.get('_places', []):
            by_place.setdefault(place['slug'], []).append(row)
            names[place['slug']] = place['name']
    ordered = sorted(by_place, key=lambda slug: (names[slug].casefold(), slug))
    jump = ' · '.join(f'<a href="#place-{e(slug)}">{e(names[slug])}</a> ({len(by_place[slug])})' for slug in ordered)
    sections = ''.join(
        f'<section class="lf-place" id="place-{e(slug)}"><h2><a href="/places/{e(slug)}.html">{e(names[slug])}</a></h2><ul>'
        + ''.join(f'<li><a href="{e(r["_page_url"])}#finding-{e(r["id"])}"><time datetime="{r["found_on"]}">{e(r["found_on"])}</time></a> {e(_summary(r["finding"], 160))}</li>' for r in by_place[slug])
        + '</ul></section>' for slug in ordered)
    return ('<main id="main" class="latest-findings-page lf-subject-page"><header class="lf-intro"><p class="r-kicker">Latest findings</p><h1>Findings by place</h1>'
            '<p class="lf-lede">Findings listed under each place where one of their people is recorded, newest first. A person recorded in several places appears under each of them; being listed under a place does not mean the finding happened there.</p>'
            f'<p class="lf-follow"><a href="/latest-findings/">All latest findings</a> · <a href="/latest-findings/studies/">Findings by study</a> · <a href="{FEED_URL}">Follow new findings (Atom feed)</a></p></header>'
            f'<section class="lf-content"><details class="lf-place-jump"><summary>Jump to a place ({len(ordered)})</summary><p>{jump}</p></details>{sections}</section></main>')


def _write_if_changed(target, content, changed, key):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_text(encoding='utf-8') != content:
        target.write_text(content, encoding='utf-8')
        changed[key] += 1


def _subject_page(template, main, clean, title, description):
    page = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: main, template, count=1, flags=re.S)
    page = re.sub(r'<title>.*?</title>', f'<title>{escape(title)} · Glasgow Surname Project</title>', page, count=1, flags=re.S)
    page = re.sub(r'<meta\b[^>]*name="description"[^>]*>', f'<meta name="description" content="{escape(description, quote=True)}">', page, count=1)
    page = page.replace('https://glasgow.phenotype.dev/latest-findings/"', f'https://glasgow.phenotype.dev{clean}/"', 1)
    page = page.replace('data-g-path="/latest-findings/index.html"', f'data-g-path="{clean}/index.html"')
    return _with_base(page, clean)


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
        row['_page_url'] = page_url(stable_page(index, len(rows)))
    attach_subjects(rows, web)
    subjects = subject_index(rows)
    study_info = {s['id']: s for row in rows for s in row['_studies']}
    study_options = sorted(({'id': sid, 'label': study_info[sid]['label'], 'type': study_info[sid]['type'], 'url': study_info[sid]['url'], 'count': len(ids)}
                            for sid, ids in subjects['studies'].items()), key=lambda s: s['label'].casefold())
    place_info = {p['slug']: p['name'] for row in rows for p in row['_places']}
    place_options = sorted(({'slug': slug, 'name': place_info[slug], 'count': len(ids)} for slug, ids in subjects['places'].items()),
                           key=lambda p: (p['name'].casefold(), p['slug']))
    browse = bool(study_options or subjects['places'])
    page = (web / 'about/index.html').read_text(encoding='utf-8')
    page, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: render_main(rows[:LATEST_SHOWN], len(rows), None, study_options, browse, place_options), page, count=1, flags=re.S)
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
    page = re.sub(r'<link\b[^>]*type="application/atom\+xml"[^>]*>', '', page)
    page = page.replace('</head>', FEED_LINK + '</head>', 1)
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
    archive = {}
    for row in rows:
        archive.setdefault(int(row['_page_url'].rstrip('/').rsplit('/', 1)[1]), []).append(row)
    for number in [None, *sorted(archive)]:
        selected = rows[:LATEST_SHOWN] if number is None else archive[number]
        rendered = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: render_main(selected, len(rows), number, study_options, browse, place_options), page, count=1, flags=re.S)
        if number is not None:
            rendered = rendered.replace('https://glasgow.phenotype.dev/latest-findings/', 'https://glasgow.phenotype.dev' + page_url(number), 1)
            rendered = re.sub(r'<title>.*?</title>', f'<title>Latest findings, page {number} · Glasgow Surname Project</title>', rendered, count=1, flags=re.S)
        target = web / ('latest-findings/index.html' if number is None else f'latest-findings/page/{number}/index.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != rendered:
            target.write_text(rendered); changed['latest_findings'] += 1
    _write_if_changed(web / 'latest-findings/feed.xml', atom_feed(rows), changed, 'latest_findings_feed')
    _write_if_changed(web / SUBJECT_INDEX, json.dumps(subjects, ensure_ascii=False, separators=(',', ':')) + '\n', changed, 'latest_findings_subject_index')
    if browse:
        _write_if_changed(web / 'latest-findings/studies/index.html', _subject_page(page, render_study_directory(study_options), '/latest-findings/studies', 'Findings by study', 'Latest Glasgow genealogy findings, grouped by family and place study.'), changed, 'latest_findings_subject_pages')
        _write_if_changed(web / 'latest-findings/places/index.html', _subject_page(page, render_place_directory(rows), '/latest-findings/places', 'Findings by place', 'Latest Glasgow genealogy findings, grouped by the places where their people are recorded.'), changed, 'latest_findings_subject_pages')
        for study in study_options:
            selected = [row for row in rows if any(s['id'] == study['id'] for s in row['_studies'])]
            clean = f"/latest-findings/studies/{study['id']}"
            _write_if_changed(web / clean.lstrip('/') / 'index.html', _subject_page(page, render_study_findings(study, selected), clean, f"{study['label']}: latest findings", f"Dated findings about people in the {study['label']} study."), changed, 'latest_findings_subject_pages')
    for stale in (web/'latest-findings/page').glob('*/index.html'):
        if stale.parent.name.isdigit() and int(stale.parent.name) not in archive:
            stale.unlink();changed['stale_finding_pages_removed']+=1
    changes_path = web / 'changes/index.html'
    if changes_path.exists():
        original = changes_path.read_text(encoding='utf-8')
        notice = '<p class="lf-changes-link">Looking for new facts? <a href="/latest-findings/">Latest findings: the dated evidence table →</a></p>'
        updated = re.sub(r'<p class="lf-changes-link">.*?</p>', '', original, flags=re.S)
        updated = updated.replace('</h1>', '</h1>' + notice, 1)
        if updated != original:
            changes_path.write_text(updated, encoding='utf-8'); changed['latest_findings_links'] += 1
    # The whole-tree view's research marks follow the latest findings.
    if Path(web).resolve() == WEB.resolve():
        try:
            try:
                from tools.build_tree_research_status import write as write_tree_status
            except ModuleNotFoundError:
                from build_tree_research_status import write as write_tree_status
            write_tree_status(ROOT)
            changed['tree_research_status'] += 1
            # Person pages carry the descendant counts in their tree-view links.
            try:
                from tools.profile_tree_links import apply as refresh_tree_links
            except ModuleNotFoundError:
                from profile_tree_links import apply as refresh_tree_links
            changed['profile_tree_links'] += refresh_tree_links(web)['changed']
        except Exception as error:  # the findings pages are already written
            print(f'tree research status not refreshed: {error}')
    return changed


if __name__ == '__main__':
    print(dict(repair()))
