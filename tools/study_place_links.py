#!/usr/bin/env python3
"""Data-derived links between family studies, places and source collections.

Studies and places are joined only through people, never through similar names:

* a place is listed on a study page when at least one person the study lists
  has a catalogue record located at that place;
* a study is listed on a place page when at least one person recorded at that
  place is a member of the study.

The counts shown are those people. The same vocabulary for groups of people is
used by the study pages, the Families & places directory and the place pages.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from html import escape
from pathlib import Path
import csv
import json
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'

# One word per concept (site audit S3-04). Keep this list short.
FAMILY_STUDY = 'Family study'
PLACE_STUDY = 'Place study'
HOUSEHOLD = 'Household'
POSSIBLE_GROUP = 'Possible group'
TREE_GROUP = 'WikiTree tree group'
REGION = 'Region'

TYPE_NOTES = {
    FAMILY_STUDY: 'A written study of a family, built from the records.',
    PLACE_STUDY: 'A written study of the families recorded in one locality.',
    HOUSEHOLD: 'People whom a record documents together as one household.',
    POSSIBLE_GROUP: 'People studied together because they appear in the same records or place. They are not proved to be related.',
    TREE_GROUP: 'People joined by links in the WikiTree family tree. These links have not all been checked against records.',
    REGION: 'Everyone with a record in a wide region. Being listed together does not mean being related.',
}

# Curated studies are written research; WikiTree tree groups are exported tree
# links; regions are broad browsing hubs and are never offered as "studies".
STUDY_KINDS = ('place', 'research')
TREE_GROUP_KIND = 'family'
# Written by tools/build_latest_findings.py (see findings_for there).
FINDINGS_INDEX = 'data/findings-by-subject.json'

# Source-library collection folders for the catalogue record categories.
CATEGORY_COLLECTIONS = {
    'Births and baptisms': 'births',
    'Marriages': 'marriages',
    'Deaths and burials': 'deaths',
    'Wills and probate': 'wills-probate',
    'Census and households': 'census',
    'Land and valuation': 'land-tax',
    'Tax and civil lists': 'land-tax',
    'Church records': 'church',
    'Directories and occupations': 'directories',
    'Military records': 'military',
    'Newspapers': 'newspapers',
    'Education': 'education',
}
COLLECTION_LABELS = {
    'births': 'Births and baptisms', 'marriages': 'Marriages', 'deaths': 'Deaths and burials',
    'wills-probate': 'Wills and probate', 'census': 'Census and households', 'land-tax': 'Land and tax',
    'church': 'Church records', 'directories': 'Directories and occupations', 'military': 'Military records',
    'newspapers': 'Newspapers', 'education': 'Education',
}


def esc(value) -> str:
    return escape(str(value if value is not None else ''), quote=True)


def place_slug(location_id: str) -> str:
    """The place-page slug; identical to build_research_catalog._slug."""
    value = str(location_id or '').casefold().replace('’', "'")
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    return value or 'other'


def region_slug(region: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', str(region or '').lower()).strip('-')


def study_type(branch: dict, curated_status: str | None = None) -> str:
    """Return the public label for a group of people.

    ``curated_status`` is the evidence status that tools/repair_family_browsing.py
    gives a curated research group ("Documented household", "Locality / record
    cluster", "Reconstructed branch" or "Evidence-led study").
    """
    kind = branch.get('kind')
    if kind == TREE_GROUP_KIND:
        return TREE_GROUP
    if kind == 'region':
        return REGION
    if kind == 'place':
        return PLACE_STUDY
    status = (curated_status or '').casefold()
    if 'household' in status:
        return HOUSEHOLD
    if 'locality' in status or 'cluster' in status or 'same area' in status:
        return POSSIBLE_GROUP
    return FAMILY_STUDY


def person_key(row: dict) -> str:
    return str(row.get('catalogue_id') or row.get('profile_id') or '').strip().lower()


def person_places(records) -> dict[str, dict[str, str]]:
    """Map each person to the places (slug -> place name) their records name."""
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for row in records:
        key, location = person_key(row), row.get('location_id')
        if not key or not location:
            continue
        slug = place_slug(location)
        result[key].setdefault(slug, (row.get('record_location') or '').strip() or slug.replace('-', ' ').title())
    return result


def load_records(web: Path = WEB) -> list[dict]:
    """The public record associations the place pages are written from."""
    index = web / 'data/records-index.json'
    if index.is_file():
        return json.loads(index.read_text(encoding='utf-8'))
    table = web / 'map/data/records.csv'
    if table.is_file():
        with table.open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))
    return []


def load_place_names(web: Path = WEB) -> dict[str, str]:
    path = web / 'data/places-index.json'
    if not path.is_file():
        return {}
    try:
        return {row['slug']: row['name'] for row in json.loads(path.read_text(encoding='utf-8')) if row.get('slug')}
    except (ValueError, KeyError, TypeError):
        return {}


def places_for_people(people, places_by_person, *, place_exists=None, names=None) -> list[dict]:
    """Places at which at least one of ``people`` is recorded, with the count."""
    counts: Counter = Counter()
    labels: dict[str, str] = {}
    for person in dict.fromkeys(str(p).lower() for p in people or []):
        for slug, name in (places_by_person.get(person) or {}).items():
            counts[slug] += 1
            labels.setdefault(slug, name)
    rows = []
    for slug, count in counts.items():
        if place_exists is not None and not place_exists(slug):
            continue
        rows.append({'slug': slug, 'name': (names or {}).get(slug) or labels[slug], 'url': f'/places/{slug}.html', 'people': count})
    return sorted(rows, key=lambda row: (-row['people'], row['name'].casefold()))


def load_studies(web: Path = WEB) -> list[dict]:
    """Curated studies and WikiTree tree groups with their members and labels."""
    path = web / 'assets/research/branches.json'
    if not path.is_file():
        return []
    branches = json.loads(path.read_text(encoding='utf-8'))
    statuses = {}
    directory = web / 'assets/research/branches-directory.json'
    if directory.is_file():
        try:
            statuses = {g['id']: g.get('status') for g in json.loads(directory.read_text(encoding='utf-8')).get('groups', [])}
        except (ValueError, KeyError, TypeError, AttributeError):
            statuses = {}
    studies = []
    for branch in branches:
        if branch.get('kind') not in (*STUDY_KINDS, TREE_GROUP_KIND):
            continue
        status = statuses.get(branch['id'])
        label = status if status in TYPE_NOTES else study_type(branch, status)
        studies.append({'id': branch['id'], 'label': branch.get('label') or branch['id'], 'kind': branch.get('kind'),
                        'url': branch.get('url') or f"/branches/{branch['id']}/", 'type': label,
                        'members': [str(m).lower() for m in branch.get('members') or []]})
    return studies


def studies_by_person(studies) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    for study in studies:
        for member in dict.fromkeys(study['members']):
            index[member].append(study)
    return index


def studies_for_people(people, index, *, kinds=STUDY_KINDS) -> list[dict]:
    """Studies (of the given kinds) that list at least one of ``people``."""
    counts: Counter = Counter()
    found: dict[str, dict] = {}
    for person in dict.fromkeys(str(p).lower() for p in people or []):
        for study in index.get(person, []):
            if study['kind'] in kinds:
                counts[study['id']] += 1
                found[study['id']] = study
    rows = [{**{k: v for k, v in found[sid].items() if k != 'members'}, 'people': n} for sid, n in counts.items()]
    return sorted(rows, key=lambda row: (-row['people'], row['label'].casefold()))


def source_collections(records, *, collection_exists) -> list[dict]:
    """Source-library collections for the record types and countries given."""
    counts: Counter = Counter()
    for row in records:
        country = region_slug(row.get('region'))
        if not country:
            continue
        for category in str(row.get('record_category') or '').split('|'):
            folder = CATEGORY_COLLECTIONS.get(category.strip())
            if folder:
                counts[(folder, country, (row.get('region') or '').strip())] += 1
    rows = []
    for (folder, country, region), count in counts.items():
        if collection_exists(folder, country):
            rows.append({'url': f'/sources/{folder}/{country}/', 'label': f'{COLLECTION_LABELS[folder]}: {region}', 'records': count})
    return sorted(rows, key=lambda row: (-row['records'], row['label']))


def _count(n: int, one: str, many: str) -> str:
    return f'{n:,} {one if n == 1 else many}'


def render_study_places(places, *, limit: int = 15) -> str:
    """'Places in this study' for a study page; empty when no place is known."""
    if not places:
        return ''
    items = ''.join(f'<li><a href="{esc(p["url"])}">{esc(p["name"])}</a> <small>{_count(p["people"], "person", "people")}</small></li>'
                    for p in places[:limit])
    more = ''
    if len(places) > limit:
        rest = ''.join(f'<li><a href="{esc(p["url"])}">{esc(p["name"])}</a> <small>{_count(p["people"], "person", "people")}</small></li>'
                       for p in places[limit:])
        more = f'<details class="sp-place-more"><summary>{len(places) - limit} more places</summary><ul class="sp-place-list">{rest}</ul></details>'
    return ('<h3 class="sp-subhead" id="study-places">Places in this study</h3>'
            '<p class="sp-caption sp-keep">Places where people listed in this study are recorded, with the number of those people. '
            'Being recorded in the same place does not prove that people were related.</p>'
            f'<ul class="sp-place-list">{items}</ul>{more}')


def render_group_places(places, *, limit: int = 15) -> str:
    """'Places in this group' for a WikiTree tree group or locality page (r- shell)."""
    if not places:
        return ''
    def item(p):
        return f'<li><a href="{esc(p["url"])}">{esc(p["name"])}</a> <small>{_count(p["people"], "person", "people")}</small></li>'
    more = ''
    if len(places) > limit:
        more = (f'<details><summary>{len(places) - limit} more places</summary>'
                f'<ul class="group-place-list">{"".join(item(p) for p in places[limit:])}</ul></details>')
    return ('<section class="r-section group-places" id="group-places"><span class="r-kicker">Places</span><h2>Places in this group</h2>'
            '<p class="r-caption">Places where people listed in this group are recorded, with the number of those people. '
            'Being recorded in the same place does not prove that people were related.</p>'
            f'<ul class="group-place-list">{"".join(item(p) for p in places[:limit])}</ul>{more}</section>')


def insert_group_places(page: str, section: str) -> str:
    """Replace or add the places section just before </main>; idempotent."""
    page = re.sub(r'<section\b(?=[^>]*\bid="group-places")[^>]*>.*?</section>', '', page, count=1, flags=re.S)
    if not section:
        return page
    return page.replace('</main>', section + '</main>', 1)


def render_place_studies(studies, tree_groups, collections, *, tree_limit: int = 8, findings: int = 0, slug: str = '') -> str:
    """'Families studied here' and source-library links for a place page."""
    parts = []
    if studies:
        items = ''.join(
            f'<li><a href="{esc(s["url"])}">{esc(s["label"])}</a> <span class="place-study-type">{esc(s["type"])}</span> '
            f'<small>{_count(s["people"], "person", "people")} recorded here</small></li>' for s in studies)
        parts.append('<p>Written studies that include people recorded at this place.</p>'
                     f'<ul class="place-study-list">{items}</ul>')
    if tree_groups:
        shown = tree_groups[:tree_limit]
        items = ' · '.join(f'<a href="{esc(g["url"])}">{esc(g["label"])}</a> ({g["people"]})' for g in shown)
        extra = f' and {len(tree_groups) - len(shown)} more' if len(tree_groups) > len(shown) else ''
        parts.append(f'<p class="place-tree-groups"><strong>WikiTree tree groups with people here:</strong> {items}{extra}. '
                     'These follow WikiTree family-tree links, which have not all been checked against records.</p>')
    if not parts:
        parts.append('<p class="empty-state">No family study covers the people recorded here yet.</p>')
    if findings and slug:
        parts.append(f'<p class="place-findings"><a href="/latest-findings/places/#place-{esc(slug)}">'
                     f'{_count(findings, "recent finding", "recent findings")} about people recorded here →</a></p>')
    html = '<section id="place-studies"><h2>Families studied here</h2>' + ''.join(parts) + '</section>'
    if collections:
        items = ''.join(f'<li><a href="{esc(c["url"])}">{esc(c["label"])}</a></li>' for c in collections)
        html += ('<section id="place-source-library"><h2>Find more in the source library</h2>'
                 '<p>Source-library collections for the kinds of record found here.</p>'
                 f'<ul class="place-collection-list">{items}</ul></section>')
    return html


class PlaceStudyLinks:
    """Everything a place page needs, loaded once for the whole place build."""

    def __init__(self, web: Path = WEB, studies=None, collection_exists=None):
        self.web = Path(web)
        self.studies = load_studies(self.web) if studies is None else studies
        self.index = studies_by_person(self.studies)
        self.collection_exists = collection_exists or (
            lambda folder, country: (self.web / 'sources' / folder / country / 'index.html').is_file())
        self.findings = {}
        path = self.web / FINDINGS_INDEX
        if path.is_file():
            try:
                self.findings = json.loads(path.read_text(encoding='utf-8')).get('places') or {}
            except (ValueError, AttributeError):
                self.findings = {}

    def html(self, people, records) -> str:
        studies = studies_for_people(people, self.index)
        groups = studies_for_people(people, self.index, kinds=(TREE_GROUP_KIND,))
        slug = next((place_slug(r['location_id']) for r in records if r.get('location_id')), '')
        return render_place_studies(studies, groups, source_collections(records, collection_exists=self.collection_exists),
                                    findings=len(self.findings.get(slug) or []), slug=slug)
