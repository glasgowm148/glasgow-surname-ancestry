"""Public, record-defined ancestors without invented WikiTree identities."""
import json
from pathlib import Path
import re


def load_people(path: Path) -> list[dict]:
    if not path.exists():
        return []
    people = json.loads(path.read_text()).get('people', [])
    seen = set()
    for person in people:
        ident = person.get('id', '')
        if not re.fullmatch(r'record-[a-z0-9-]+', ident) or ident in seen:
            raise ValueError(f'Invalid or duplicate documentary person: {ident}')
        seen.add(ident)
        if person.get('publication_status') != 'approved' or not person.get('source_ids'):
            raise ValueError(f'Documentary person needs approved named records: {ident}')
        if not re.fullmatch(r'/free-space/[a-z0-9-]+/', person.get('url', '')):
            raise ValueError(f'Documentary person needs a complete public research account: {ident}')
        if not isinstance(person.get('first_record_year'), int) or not person.get('name'):
            raise ValueError(f'Documentary person needs a name and record year: {ident}')
        groups = person.get('record_groups', [])
        if len(groups) > 1:
            selection = person.get('identity_selection') or {}
            if not (selection.get('selected') is True and selection.get('model') == 'same_person'
                    and selection.get('status') in {'uncertain', 'strongly_supported', 'proved'}
                    and selection.get('id') and selection.get('basis') and selection.get('limitations')):
                raise ValueError(f'Combined record groups need an explicit graded identity selection: {ident}')
            group_ids = [g.get('id') for g in groups]
            if not all(group_ids) or len(set(group_ids)) != len(groups):
                raise ValueError(f'Duplicate or missing documentary record group: {ident}')
            if any(not g.get('source_ids') or not isinstance(g.get('first_record_year'), int) for g in groups):
                raise ValueError(f'Record groups need source IDs and record years: {ident}')
            if {s for g in groups for s in g['source_ids']} != set(person['source_ids']):
                raise ValueError(f'Combined identity source IDs must cover exactly its record groups: {ident}')
            if person['first_record_year'] != min(g['first_record_year'] for g in groups):
                raise ValueError(f'Combined identity must retain its earliest record year: {ident}')
    return people


def metric_node(person: dict) -> dict:
    uncertain_identity = (person.get('identity_selection') or {}).get('status') == 'uncertain'
    return dict(id=person['id'], name=person['name'], url=person['url'],
                gender=person.get('gender', ''), birth_year=None, death_year=None,
                birth_status=None, year=person['first_record_year'],
                year_basis='dated evidence', year_status='record date; uncertain combined identity' if uncertain_identity else 'record date',
                first_record_year=person['first_record_year'], cohort_member=False)


def load_chronology(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text()).get('chronology', [])
    for row in rows:
        if row.get('publication_status') != 'approved' or not row.get('source_ids'):
            raise ValueError('A local chronology correction needs an approved record basis')
    return rows


def vital_assessments(path: Path) -> list[dict]:
    """Compile explicit chronology corrections into the shared vital review format."""
    result = []
    for row in load_chronology(path):
        if not row.get('vitals'):
            continue
        if not row.get('assessment_id') or not row.get('reviewed') or not row.get('reason'):
            raise ValueError('A vital chronology correction needs an ID, review date and reason')
        result.append(dict(id=row['assessment_id'], subject=row['id'], status='approved',
                           reviewed=row['reviewed'], basis=row['reason'], source_ids=row['source_ids'],
                           vitals=row['vitals'], derived_from='documentary_chronology'))
        if row.get('catalogue_projection'):
            result[-1]['catalogue_projection'] = row['catalogue_projection']
    return result
