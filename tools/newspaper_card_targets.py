"""Curated documentary targets for newspaper cards; no identity inference from prose."""
from __future__ import annotations
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'research/source-library/newspaper-targets.json'
KIN_TAGS = frozenset({'spouse', 'parent-child', 'siblings', 'other-kin'})
EVIDENCE_TAGS = KIN_TAGS | {'occupation', 'residence', 'birth', 'death'}
TAG_LABELS = {'spouse': 'Spouse / marriage', 'parent-child': 'Parents & children',
              'siblings': 'Siblings', 'other-kin': 'Other kin', 'occupation': 'Occupation / trade',
              'residence': 'Place / address', 'birth': 'Birth', 'death': 'Death'}


def clean_target(target):
    """Keep only public display fields and require an explanation for birth estimates."""
    tags = target.get('evidence_tags', [])
    if not set(tags) <= EVIDENCE_TAGS:
        raise ValueError('Unknown newspaper evidence tag')
    people = []
    for person in target.get('people', []):
        name = str(person.get('name', '')).strip()
        if not name:
            raise ValueError('A documentary target needs its recorded name')
        birth = str(person.get('birth_label') or 'Birth unknown')
        basis = str(person.get('birth_basis') or '')
        if birth != 'Birth unknown' and not basis:
            raise ValueError('A birth bound or estimate needs its source or inference basis')
        people.append({'name': name, 'place': str(person.get('place') or 'Place not stated'),
                       'birth_label': birth, 'birth_basis': basis,
                       'details': [str(v) for v in person.get('details', []) if str(v).strip()]})
    return {'people': people, 'record_type': str(target.get('record_type') or 'Newspaper notice'),
            'evidence_tags': list(dict.fromkeys(tags)), 'summary': str(target.get('summary') or '')}


@lru_cache(maxsize=1)
def _read_targets(path, mtime):
    data = json.loads(Path(path).read_text())
    return {str(ident): {**clean_target(target), 'reading_sha256': target.get('reading_sha256', '')}
            for ident, target in data['targets'].items()}


def reading_hash(row):
    return sha256(' '.join(row.get('reading', '').casefold().split()).encode()).hexdigest()


def load_targets():
    if not SOURCE.exists():
        return {}
    return _read_targets(str(SOURCE), SOURCE.stat().st_mtime_ns)


def target_for(row):
    if row.get('card_target') is not None:
        return clean_target(row['card_target'])
    target = load_targets().get(str(row.get('image_id')))
    if target is not None and target.get('reading_sha256') == reading_hash(row):
        return target
    label = {'place study': 'Place study', 'reading pending': 'Unresolved newspaper lead',
             'place or ship': 'Excluded search match'}.get(row.get('status'), 'Glasgow surname record')
    return {'people': [{'name': label, 'place': 'Place not stated', 'birth_label': 'Birth unknown',
                        'birth_basis': '', 'details': []}], 'record_type': 'Newspaper notice',
            'evidence_tags': [], 'summary': ''}


def evidence_tags(row, group=None):
    tags = {tag for item in (group or [row]) for tag in target_for(item)['evidence_tags']}
    if tags & KIN_TAGS:
        tags.add('relationships')
    return tags


def identity_status(row, group=None):
    rows = group or [row]
    ids = {pid for item in rows for pid in item.get('profile_ids', [])}
    if not ids:
        return 'unassigned'
    grades = {str(m.get('confidence') or 'unknown').casefold() for item in rows
              for m in item.get('profile_matches', [])
              if (m.get('profile_id') or m.get('id')) in ids}
    return next((grade for grade in ('strong', 'probable') if grade in grades), 'possible')
