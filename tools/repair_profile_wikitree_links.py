#!/usr/bin/env python3
"""Expose only catalogue-confirmed WikiTree destinations on person pages."""
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
STYLE = '<link rel="stylesheet" href="/assets/repair/profile-wikitree.css?v=1">'
MARKER = 'profile-wikitree-actions'
WIKITREE = 'https://www.wikitree.com/wiki/'


def rows(value):
    return value if isinstance(value, list) else value.get('people', value.get('items', []))


def ids(person):
    return {str(value).casefold() for value in person.get('profile_ids', []) if value}


def trusted_free_space(person):
    value = str(person.get('wikitree_free_space_url') or '').strip()
    return value if value.startswith(WIKITREE + 'Space:') else ''


def action(person):
    profile_ids = list(dict.fromkeys(str(value) for value in person.get('profile_ids', []) if value))
    links = [(profile_id, WIKITREE + profile_id) for profile_id in profile_ids]
    if not links:
        free_space = trusted_free_space(person)
        if free_space:
            links = [('Maintained Space page', free_space)]
    if not links:
        return ''
    label = 'WikiTree profiles' if len(links) > 1 else 'WikiTree destination'
    actions = ''.join(
        '<a href="' + escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">'
        + ('View on WikiTree' if ident != 'Maintained Space page' else 'Read the maintained Space page')
        + '<small>' + escape(ident) + ' ↗</small></a>'
        for ident, url in links
    )
    return '<div class="profile-wikitree-actions" aria-label="' + label + '"><span>' + label + '</span>' + actions + '</div>'


def repair():
    # The compact search index intentionally omits identity-work metadata.
    # Use the full catalogue export, where confirmed IDs and canonical Space
    # destinations are maintained.
    index = rows(json.loads((WEB / 'data/people.json').read_text(encoding='utf-8')))
    by_id = {}
    for person in index:
        for ident in ids(person) | {str(person.get(key) or '').casefold() for key in ('id', 'selection_id', 'catalogue_id')}:
            if ident:
                by_id.setdefault(ident, person)
    changed = 0
    for page in (WEB / 'people').glob('*.html'):
        text = page.read_text(encoding='utf-8')
        person_id = re.search(r'data-r-person="([^"]+)"', text)
        person = by_id.get((person_id.group(1) if person_id else page.stem).casefold())
        if not person:
            continue
        text = re.sub(r'<div class="profile-wikitree-actions".*?</div>', '', text, flags=re.S)
        insert = action(person)
        if not insert:
            continue
        text, count = re.subn(r'(<h1\b[^>]*>.*?</h1>)', r'\1' + insert, text, count=1, flags=re.S)
        if not count:
            continue
        if STYLE not in text:
            text = text.replace('</head>', STYLE + '</head>', 1)
        if text != page.read_text(encoding='utf-8'):
            page.write_text(text, encoding='utf-8')
            changed += 1
    return {'profile_wikitree_actions': changed} if changed else {}


if __name__ == '__main__':
    print(repair())
