#!/usr/bin/env python3
"""Render maintained, sourced documentary-person handoffs with stable anchors."""
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
INPUT = ROOT / 'research/latest-findings-subjects/subjects.json'
SAFE_KEY = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
PUBLIC_PERSON_FIELDS = ('anchor', 'name', 'status', 'identity_note', 'minimum_fields',
                        'facts', 'candidates', 'duplicate_check', 'next_test', 'wikitext', 'record_matches', 'related_profiles')


def build():
    data = json.loads(INPUT.read_text())
    template = (ROOT / 'www/about/index.html').read_text()
    changed = 0
    for group in data['groups']:
        if not SAFE_KEY.fullmatch(group['slug']):
            raise ValueError('Unsafe subject group slug')
        url = '/research/subjects/' + group['slug'] + '/'
        sections = []
        links = []
        seen = set()
        for person in group['people']:
            anchor = person['anchor']
            if not SAFE_KEY.fullmatch(anchor) or anchor in seen:
                raise ValueError('Unsafe or duplicate person anchor')
            seen.add(anchor)
            if not person['facts'] or not all(f.get('sources') for f in person['facts']):
                raise ValueError('A person handoff needs sourced record evidence')
            if not all(heading in person['wikitext'] for heading in ('== Biography ==', '== Sources ==', '<references />')):
                raise ValueError('A person handoff needs a complete sourced draft')
            links.append(f'<li><a href="{url}#{anchor}">{escape(person["name"])}</a></li>')
            facts = ''.join('<p>' + escape(fact['finding']) + ' ' +
                            ' '.join(f'<a href="{escape(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(s["title"])}</a>' for s in fact['sources']) + '</p>'
                            for fact in person['facts'])
            candidates = ''.join(f'<li><a href="https://www.wikitree.com/wiki/{escape(c["id"])}">{escape(c["id"])}</a> — {escape(c["reason"])}</li>' for c in person['candidates'])
            check = ''.join('<li>' + escape(s) + '</li>' for s in person['duplicate_check'])
            matches = ''.join('<li><strong>' + escape(m['finding_id']) + '</strong> — ' +
                              escape(m['assessment']) + ' ' +
                              ', '.join(f'<a href="https://www.wikitree.com/wiki/{escape(pid)}">{escape(pid)}</a>' for pid in m['profile_ids']) +
                              '</li>' for m in person.get('record_matches', []))
            matched = person.get('status', '').startswith('MATCHED')
            family_links = ', '.join(escape(r['relationship']) + ': ' +
                                    f'<a href="https://www.wikitree.com/wiki/{escape(r["id"])}">{escape(r["id"])}</a>'
                                    for r in person.get('related_profiles', []))
            sections.append(f'<section id="{anchor}" class="subject-person"><h2>{escape(person["name"])}</h2>'
                            f'<p><strong>{escape(person["status"])}</strong> — {escape(person["identity_note"])}</p>'
                            f'<p><strong>Record fields:</strong> {escape(person["minimum_fields"])}</p>' + facts +
                            ('<p><strong>Identified family in this record:</strong> ' + family_links + '</p>' if family_links else '') +
                            ('<h3>Matched WikiTree profile</h3><ul>' + candidates + '</ul>' if matched else '<h3>Compatible WikiTree candidates</h3><ul>' + candidates + '</ul>' if candidates else '') +
                            ('<details><summary>Matches by record</summary><ul>' + matches + '</ul></details>' if matches else '') +
                            '<details><summary>Duplicate check and relationship limits</summary><ul>' + check + '</ul></details>' +
                            f'<p><strong>Next identity test:</strong> {escape(person["next_test"])}</p>'
                            '<details><summary>Complete sourced WikiTree draft</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">' + escape(person['wikitext']) + '</pre></details></section>')
        content = '<main id="main" class="r-main"><header><p class="r-kicker">People in the records</p><h1>' + escape(group['title']) + '</h1><p>' + escape(group['introduction']) + '</p><p><a href="/latest-findings/">Latest findings</a> · <a href="/catalogue/">People catalogue</a></p><ul>' + ''.join(links) + '</ul></header>' + ''.join(sections) + '</main>'
        page = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: content, template, count=1, flags=re.S)
        page = re.sub(r'<title>.*?</title>', lambda _: '<title>' + escape(group['title']) + ' · Glasgow Surname Project</title>', page, count=1, flags=re.S)
        page = re.sub(r'<link\b[^>]*rel="canonical"[^>]*>', '<link rel="canonical" href="https://glasgow.phenotype.dev' + url + '">', page, count=1)
        page = page.replace('g-kind-about', 'g-kind-research').replace('data-g-path="/about/index.html"', 'data-g-path="' + url + 'index.html"')
        page = re.sub(r'(<div class="g-crumbs">.*?<strong>).*?(</strong>)', lambda m: m[1] + escape(group['title']) + m[2], page, count=1, flags=re.S)
        page = re.sub(r'<nav class="v3-view-nav".*?</nav>', '', page, count=1, flags=re.S)
        page = NAV.sub(lambda _: render_primary_navigation(Path(url.lstrip('/') + 'index.html')), page, count=1)
        page = _with_base(page, url.rstrip('/'))
        # Restore the canonical analytics tag after markup normalization.
        page = with_analytics(page)
        target = ROOT / 'www' / url.lstrip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != page:
            target.write_text(page)
            changed += 1
        public = {key: group[key] for key in ('slug', 'title', 'introduction')}
        public['people'] = [{key: person[key] for key in PUBLIC_PERSON_FIELDS if key in person} for person in group['people']]
        public_path = target.parent / 'subjects.json'
        encoded = json.dumps(public, indent=2, ensure_ascii=False) + '\n'
        if not public_path.exists() or public_path.read_text() != encoded:
            public_path.write_text(encoded)
    return {'subject_pages': len(data['groups']), 'changed': changed}


if __name__ == '__main__':
    print(build())
