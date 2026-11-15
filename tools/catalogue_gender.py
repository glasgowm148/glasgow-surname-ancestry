"""Project workbench gender classifications into the maintained catalogue outputs.

The workbench remains authoritative. Name-based corrections are reviewed proposal
operations, never chart-time guesses or changes to raw provider captures.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MALE_NAMES = set("""john william james george thomas robert alexander arthur david henry
albert charles joseph benjamin patrick alfred harry peter samuel bernard graham andrew
tom garry johnathan justin kyle neal scot hugh nicholas owen patrik gyles adam fred
edgar stephen ernest clement stanley edwin jabez anthony edward walter allan archie
antony norman augustus dougal malcolm frank jas geo thos wm alexr male""".split())
FEMALE_NAMES = set("""mary margaret sarah elizabeth jane ellen marrion annie margret
ann lillias elizth matilda harriet florence emily celia martha christina margrat
dora isob rose may alice darlene georgina heather janae ronda starla wilhemina
issobella caroline sara alison harriett adelaide harriette daughter alicia female
selina eleanor rachel elsie johanna rebecca lizzie williamina anselina euphemie
prudence rosina jeane margarat roseann euphema issobell jonat alisone margarate
hilda lily anne maggie eva dorothy anna catherine blanche constance susan lilian
olive ada frances catherin rachael jenet rosana joanna cathrine issobel eliz
isobella anabella rebekah betsy agness nanse ratchel allison holly helen maria amy
mildred jemima henrietta""".split())


def name_classification(person):
    names = person.get('first_names') or []
    words = str(names[0]).strip().split() if names else []
    first = words[0].strip('[]?.').casefold() if words else ''
    if first in MALE_NAMES:
        return 'male'
    if first in FEMALE_NAMES:
        return 'female'
    return None


def workbench_people(root=ROOT):
    from genealogy.store import open_project
    project = open_project(Path(root), readonly=True)
    try:
        people = {row['id']: row for row in project.store.all('SELECT * FROM person')}
        result = {}
        for row in project.store.all(
                "SELECT value,entity_id FROM external_id WHERE system IN ('wikitree','glasgow-local') "
                "AND status NOT IN ('candidate','retired')"):
            if row['entity_id'] in people:
                result[row['value'].casefold()] = people[row['entity_id']]
        for row in project.store.all('SELECT path,entity_id FROM route_alias'):
            if row['path'].startswith('people/') and row['path'].endswith('.html') and row['entity_id'] in people:
                result[Path(row['path']).stem.casefold()] = people[row['entity_id']]
        return result
    finally:
        project.store.close()


def project_genders(people, root=ROOT):
    path = Path(root) / 'data/private/workbench/glasgow.sqlite'
    if not path.exists():
        return {}
    known = workbench_people(root)
    changed = {}
    for person in people:
        if person.get('gender') in ('Male', 'Female') or person.get('likely_living'):
            continue
        row = known.get(str(person.get('catalogue_id', '')).casefold())
        if not row or row.get('sex') not in ('male', 'female'):
            continue
        person['gender'] = row['sex'].title()
        person['gender_basis'] = 'Maintained research workbench classification; raw source values retained.'
        changed[person['catalogue_id']] = person['gender']
    return changed


def proposal(root=ROOT):
    people = json.loads((Path(root) / 'www/data/people.json').read_text())['people']
    known = workbench_people(root)
    operations = {}
    for person in people:
        if person.get('gender') in ('Male', 'Female') or person.get('likely_living'):
            continue
        sex = name_classification(person)
        row = known.get(person['catalogue_id'])
        if not row or row.get('sex') in ('male', 'female', 'other') or not sex:
            continue
        operations[row['id']] = {
            'op': 'update', 'table': 'person', 'id': row['id'],
            'expected_revision': row['revision'], 'set': {'sex': sex},
            'reason': 'Owner-authorized historical given-name classification: ' +
                      person['name'] + '; ' + person['catalogue_id'] +
                      '. Name-based inference, not a newly inspected source record.'}
    return {'format': 'genealogy-change-proposal', 'format_version': 1,
            'title': 'Classify missing historical genders from reviewed unambiguous given names; '
                     'preserve known genders and leave initials and ambiguous names unclassified.',
            'actor': 'codex:gender-classification', 'operations': list(operations.values())}


def sync(root=ROOT):
    root = Path(root)
    web = root / 'www'
    def read(path):
        return json.loads(path.read_text())
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
    payload_path = web / 'data/people.json'
    payload = read(payload_path)
    changed = project_genders(payload['people'], root)
    if not changed:
        return {'classified': 0}
    write(payload_path, payload)
    by_id = {key.casefold(): gender for key, gender in changed.items()}
    def patch_row(row):
        key = str(row.get('catalogue_id') or row.get('slug') or row.get('id') or '').casefold()
        gender = by_id.get(key)
        if gender:
            if isinstance(row.get('identity'), dict):
                row['identity']['gender'] = gender
            else:
                row['gender'] = gender
    for relative in ('data/catalogue-search-index.json', 'data/people-index.json',
                     'assets/research/search-people.json'):
        path = web / relative
        if path.exists():
            data = read(path)
            rows = data if isinstance(data, list) else data.get('people', [])
            for row in rows:
                if isinstance(row, dict):
                    patch_row(row)
            write(path, data)
    for key in changed:
        for relative in (f'people/{key}.json', f'assets/research/people/{key}.json'):
            path = web / relative
            if path.exists():
                data = read(path)
                patch_row(data)
                write(path, data)
    full = read(web / 'data/catalogue-search-index.json')
    (web / 'data/people-index.js').write_text(
        'window.glasgowPeopleIndex=' + json.dumps(full, ensure_ascii=False, separators=(',', ':')) + ';\n')
    from tools.catalogue_search_index import refresh
    return {'classified': len(changed), 'genders': dict(Counter(changed.values())), **refresh(web)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proposal', type=Path)
    parser.add_argument('--sync', action='store_true')
    args = parser.parse_args()
    if args.proposal:
        args.proposal.parent.mkdir(parents=True, exist_ok=True)
        document = proposal()
        args.proposal.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
        print({'proposed': len(document['operations'])})
    if args.sync:
        print(sync())
