#!/usr/bin/env python3
"""Build the searchable Notables reader from the maintained WikiTree study list."""
from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re

try:
    from tools.site_identity import SITE_URL, page_title
except ModuleNotFoundError:
    from site_identity import SITE_URL, page_title

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
SOURCE = ROOT / 'surname-research/free-space-pages/Glasgow_Name_Study.md'
PEOPLE = WEB / 'data/people.json'
EVIDENCE = ROOT / 'data/wikitree/profile-evidence.json'
FS_LINKS = ROOT / 'data/familysearch/person-links.json'
ASSESSMENTS = ROOT / 'research/relationship_assessments.json'


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def notables_lines():
    text = SOURCE.read_text(encoding='utf-8')
    match = re.search(r'^== Notables ==\s*$([\s\S]*?)(?=^== |\Z)', text, re.M)
    if not match:
        raise RuntimeError('Notables section missing from maintained Glasgow Name Study')
    return [line for line in match.group(1).splitlines() if line.lstrip().startswith('*') and not line.lstrip().startswith('**')]


def useful_date(value):
    text = str(value or '').strip()
    return '' if text in {'0000-00-00', '0000', 'Unknown'} else text


def clean_citation(value):
    """Turn imported escaped markup into readable citation text, never nested links."""
    text = unescape(str(value or ''))
    text = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def rows():
    people = {p.get('catalogue_id'): p for p in load(PEOPLE, {}).get('people', [])}
    evidence = load(EVIDENCE, {}).get('profiles', {})
    fs = load(FS_LINKS, {}).get('people', {})
    assessments = load(ASSESSMENTS, [])
    estimates = load(ROOT / 'research/relationship_probability_estimates.json', {}).get('estimates', [])
    out, seen = [], set()
    for line in notables_lines():
        ids = re.findall(r'\[\[([A-Za-z]+-\d+)(?:\|[^]]*)?\]\]', line)
        if not ids:
            continue
        # The first linked profile is the subject; spouse/relative links remain in rationale text.
        pid = ids[0]
        subject_link = re.search(r'\[\[' + re.escape(pid) + r'\|([^]]+)\]\]', line)
        if pid in seen:
            continue
        seen.add(pid)
        key = pid.casefold()
        person = people.get(key) or {}
        profile = evidence.get(pid) or {}
        pf = profile.get('profile_fields', {})
        dates = '–'.join(x for x in (useful_date(person.get('birth') or pf.get('BirthDate')),
                                     useful_date(person.get('death') or pf.get('DeathDate'))) if x)
        name = (person.get('name') or (pf.get('FirstName', '') + ' ' + pf.get('LastNameAtBirth', '')).strip()
                or (subject_link.group(1) if subject_link else pid))
        ref_blocks = re.findall(r'<ref\b[^>]*>(.*?)</ref>', line, re.I)
        rationale = re.sub(r'<ref\b[^>]*>.*?</ref>', '', line, flags=re.I)
        rationale = re.sub(r'^\s*\*\s*', '', rationale)
        rationale = re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]', r'\2', rationale)
        rationale = re.sub(r'\[\[([^]]+)\]\]', r'\1', rationale)
        rationale = clean_citation(re.sub(r"'{2,}", '', rationale))
        citations = []
        for block in ref_blocks:
            plain = re.sub(r'\[\[([^]|]+)\|?([^]]*)\]\]', lambda m: m.group(2) or m.group(1), block)
            plain = re.sub(r'\[(https?://\S+)(?:\s+([^]]+))?\]', lambda m: m.group(2) or m.group(1), plain)
            plain = clean_citation(re.sub(r"'{2,}", '', plain))
            if plain:
                citations.append((plain, []))
            for url, label in re.findall(r'\[(https?://\S+)(?:\s+([^]]+))?\]', block):
                citations.append((label or url, [url.rstrip('.,')]))
        for source in profile.get('sources') or []:
            citation = clean_citation(source.get('citation'))
            urls = source.get('urls') or []
            if citation:
                citations.append((citation, urls))
        rels = []
        for a in assessments:
            if a.get('publication_status') != 'approved' or pid not in a.get('people', []):
                continue
            perspective = (a.get('perspectives') or {}).get(pid, {})
            other_ids = [x for x in a.get('people', []) if x != pid]
            if not other_ids:
                continue
            relative = other_ids[0]
            relkey = relative.casefold()
            rel_local = f'/people/{relkey}.html'
            rel_url = rel_local if (WEB / rel_local.lstrip('/')).exists() else f'https://www.wikitree.com/wiki/{relative}'
            estimate = next((e for e in estimates if e.get('assertion_id') == a.get('assertion_id')
                             and {e.get('subject_id'), e.get('relative_id')} == {pid, relative}), None)
            rels.append({'person': relative, 'url': rel_url, 'name': (people.get(relkey) or {}).get('name', relative),
                         'relationship': perspective.get('relationship', 'connection'),
                         'status': (estimate or {}).get('assessment_status', a.get('status', 'unreviewed')),
                         'percent': (estimate or {}).get('percent'), 'selection': a.get('working_selection'),
                         'lifecycle': a.get('lifecycle'), 'basis': (estimate or {}).get('basis') or a.get('basis', ''),
                         'scope': (estimate or {}).get('scope') or a.get('identity_scope', '') or a.get('limitations', '')})
        local_profile = f'/people/{key}.html'
        profile_url = local_profile if (WEB / local_profile.lstrip('/')).exists() else (profile.get('profile_url') or f'https://www.wikitree.com/wiki/{pid}')
        out.append({'id':pid,'name':name,'dates':dates,'profile':profile_url,
                    'fs':(fs.get(key) or {}).get('id',''),'rationale':rationale,'citations':citations,'relationships':rels})
    return out


def link(url, label):
    if not str(url).startswith(('https://','http://','/')):
        return escape(label)
    external = ' target="_blank" rel="noopener"' if url.startswith(('https://','http://')) else ''
    return f'<a href="{escape(url, quote=True)}"{external}>{escape(label)}</a>'


def brief_summary(person):
    """Short, source-maintained-fact summaries for the public index."""
    summaries = {
        'Glasgow-1030': 'Jhone Glasgow completed a master’s degree; reviewed records do not identify him as Kilbirnie minister, and no family connection is established.',
        'Glasgow-1101': 'The 1635 Glasgow graduate is probably the Donegal cleric appointed in 1661; this identification does not prove migration or birthplace.',
        'Glasgow-1073': 'Rev. John Glasgow served Kilbirnie; Jean Cunningham is named as his wife, while his parents remain uncertain.',
        'Glasgow-1077': 'Ayrshire records identify a merchant namesake; the reported Irvine provost identity remains unverified and is not linked to the minister’s household.',
        'Glasgow-1136': 'A Glasgow M.A. identified in the maintained study; its current entry gives dates but no further biography or family connection.',
        'Glasgow-1075': 'Surgeon Robert Glasgow was Rev. John’s son and Jean Cunningham’s son; Paterson names Margaret Allan as his wife.',
        'Glasgow-3410': 'A Glasgow M.A. identified in the maintained study; its current entry gives dates but no further biography or family connection.',
        'Glasgow-634': 'James Glasgow served as North Carolina Secretary of State; published biography names Maryland minister James Patrick Glasgow as his father.',
        'Glasgow-1076': 'Robert Glasgow owned plantations and enslaved people on St Vincent and commissioned Montgreenan; his assessed father link remains unselected.',
        'Glasgow-1220': 'William Glass founded the British settlement on Tristan da Cunha; the catalogue’s birth year differs from the inherited date.',
        'Glasgow-971': 'Alexander Glasgow was a Scottish merchant and Cork landowner; his proposed ancestry through John remains possible, not established.',
        'Glasgow-473': 'Ellen Glasgow was an American novelist who won the 1942 Pulitzer Prize; no family connection to earlier Scottish branches is stated.',
        'Glasgow-773': 'Sir Thomas Glasgow was an Australian soldier, politician and diplomat; his career does not establish an early Scottish family connection.',
        'Hutcheson-1648': 'George Hutcheson co-founded Glasgow’s hospital and school with his brother Thomas; both were sons of Thomas Hutcheson of Lambhill.',
        'Hutcheson-1649': 'Thomas Hutcheson continued the hospital endowment and school; his maintained father assessment names Thomas Hutcheson of Lambhill.',
        'Glasgow-3958': 'Jemima Glasgow was the mother of novelist Baroness von Tautphoeus; her proposed father James Glasgow remains unselected.',
        'Montgomery-24362': 'Jemima Montgomery, Baroness von Tautphoeus, was an Irish novelist and daughter of Jemima Glasgow and James Montgomery.',
        'Boyle-1708': 'David Boyle was a Scottish politician and University of Glasgow rector; Earl of Glasgow is a title, not his surname.',
        'Glasgow-635': 'Patrick Glasgow ministered at Manokin and All Hallows; identifying him as politician James Glasgow’s father remains unverified.',
    }
    return summaries.get(person['id'], person['rationale'])


def render():
    try:
        from tools.notables_cards import render as render_cards
    except ModuleNotFoundError:
        from notables_cards import render as render_cards
    return render_cards(rows(), WEB, page_title, SITE_URL, link, brief_summary)


if __name__ == '__main__':
    print({'notables':render()})
