"""Repair captured public parent identities without assessing relationships."""
from __future__ import annotations

from copy import deepcopy


BLOCKED = frozenset({'withheld', 'blocked', 'rejected', 'disproved', 'contradicted',
                     'non-biological', 'non_biological', 'superseded', 'historical',
                     'excluded', 'alternative'})
PLACEHOLDERS = frozenset({'', 'Parent outside current One-Tree export'})


def current_parent(row: dict) -> bool:
    return (row.get('current') is not False and row.get('lifecycle') in (None, 'current')
            and row.get('display') not in ('historical', 'superseded', 'alternative'))


def repairable_parent(row: dict, target: str, aliases: list[str]) -> bool:
    """An absent export identity is repairable; a named different parent is not."""
    if (not current_parent(row) or row.get('withheld') or row.get('hypothesis')
            or row.get('alternative') or row.get('rejected')
            or row.get('status') in BLOCKED or row.get('publication_status') in BLOCKED):
        return False
    ident = row.get('id') or ''
    return ident == target or ident in aliases or (not ident and row.get('name', '') in PLACEHOLDERS)


def apply_parent_identity_repairs(people: dict[str, dict], repairs: list[dict],
                                  available: dict[str, dict] | None = None) -> None:
    """Replay dossier-verified repairs in either model; never read external state."""
    for repair in repairs:
        child, target, role = (repair.get(k) for k in ('child', 'parent', 'role'))
        aliases = repair.get('aliases', [])
        if (child not in people or (target not in people and target not in (available or {})) or child == target
                or role not in ('father', 'mother') or not aliases or target in aliases
                or repair.get('relationship_source') != 'wikitree_parent_field'
                or repair.get('tree_relationship') is not True):
            continue
        person = people[child]
        rows = [r for r in person.get('parents', []) if r.get('role') == role]
        if len(rows) != 1 or not repairable_parent(rows[0], target, aliases):
            continue
        if target not in people:
            # The retained atlas can predate the surviving public profile.
            # Copy its own public account; retain the old alias person intact.
            people[target] = deepcopy(available[target])
        row = rows[0]
        previous = row.get('id') or ''
        row.update(id=target, name=repair['name'], inModel=True)
        edge = person.get('edge', {})
        if ((previous and edge.get('parent') == previous and edge.get('role') in (None, role))
                or (edge.get('role') == role and not edge.get('parent'))):
            edge['parent'] = target
        elif edge.get('type') == 'group' and not any(
                r is not row and r.get('id') in people and not r.get('withheld')
                for r in person.get('parents', [])):
            person['edge'] = dict(parent=target, type='recorded', semantic='parent',
                                  role=role, status=row.get('status', 'unmarked'))
        # Move only this child's reciprocal row, preserving captured certainty.
        captured = None
        if previous != target and previous in people and not any(
                r.get('id') == previous for r in person.get('parents', [])):
            old_parent = people[previous]
            matches = [r for r in old_parent.get('childrenRecorded', []) if r.get('id') == child]
            captured = deepcopy(matches[0]) if matches else None
            if matches:
                old_parent['childrenRecorded'] = [r for r in old_parent['childrenRecorded']
                                                   if r.get('id') != child]
        children = people[target].setdefault('childrenRecorded', [])
        matches = [r for r in children if r.get('id') == child]
        if not matches:
            reciprocal = captured if captured is not None else dict(
                id=child, role='child', status=row.get('status', 'unmarked'))
            children.append(reciprocal)
            matches = [reciprocal]
        for reciprocal in matches:
            reciprocal.update(name=person['name'], inModel=True)
