"""Carry selected public working families into the primary Whole tree viewer."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


WORKING_PERSON_FIELDS = (
    'name', 'first', 'surname', 'currentSurname', 'sex', 'born', 'died', 'year',
    'birthDisplay', 'deathDisplay', 'birthplace', 'deathplace', 'bornApprox',
    'birthLocationRegion', 'deathLocationRegion', 'locationRegion', 'locationLabel',
    'locationColor', 'cluster', 'researchUrl',
)

CHRONOLOGY_DISPLAY_FIELDS = (
    'born', 'died', 'year', 'birthDisplay', 'deathDisplay', 'lifeLabel',
    'birthplace', 'deathplace', 'deathLocationRegion', 'bornApprox',
)

def parent_order(row: dict) -> tuple:
    """One layout attachment; the other independently graded parent stays listed."""
    status = str(row.get('status', '')).replace('-', '_').casefold()
    ranks = {'dna_confirmed': 0, 'confident': 1, 'certain': 1, 'proved': 1,
             'confirmed': 1, 'documented': 1, 'strongly_supported': 1,
             'uncertain': 3, 'possible': 3, 'probable': 3, 'guess': 3}
    return (not row.get('hypothesis', False), ranks.get(status, 2),
            row.get('role') != 'father', row.get('id', ''))


def overlay_model(retained: dict, fresh: dict) -> dict:
    """Refresh working subjects without replacing the approved atlas publication."""
    result = deepcopy(retained)
    incoming = {p['id']: p for p in fresh['people']}
    selected = {p['id'] for p in fresh['people'] if p.get('edge', {}).get('type') == 'hypothesis'}
    prior_people = {p['id']: p for p in retained['people']}
    prior_selected = set(result['meta'].get('workingOverlayIds', []))
    documentary = {p['id'] for p in fresh['people'] if p.get('documentary')}
    reviewed = set(fresh['meta'].get('reviewedParentReplacementIds', []))
    restored = set(fresh['meta'].get('reviewedFamilyRestorationIds', []))
    public_families = set(fresh['meta'].get('publicFamilyScopeIds', fresh['meta'].get('publicFamilySyncIds', [])))
    previous_public = set(result['meta'].get('publicFamilyScopeIds', result['meta'].get('publicFamilySyncIds', [])))
    maternal_scope = fresh['meta'].get('publicMotherGradeScope', {})
    previous_maternal_scope = result['meta'].get('publicMotherGradeScope', {})
    refresh = selected | set(result['meta'].get('workingOverlayIds', [])) | documentary | reviewed | set(result['meta'].get('reviewedParentReplacementIds', []))
    refresh |= restored | set(result['meta'].get('reviewedFamilyRestorationIds', []))
    existing = {p['id']: p for p in result['people']}
    mother_ids = set(fresh['meta'].get('workingMotherIds', []))
    for child, mothers in maternal_scope.items():
        recorded = [r.get('id') for r in existing.get(child, {}).get('parents', []) if r.get('role') == 'mother']
        mother_ids |= {mother for mother in mothers if not recorded or mother in recorded}
    for mother in mother_ids:
        if mother in incoming and mother not in existing:
            existing[mother] = deepcopy(incoming[mother])
    for ident in refresh:
        if ident not in incoming:
            raise ValueError('Working subject absent from current public model: ' + ident)
        previous = existing.get(ident, {})
        existing[ident] = deepcopy(incoming[ident])
        if ident in selected | prior_selected and ident not in documentary | reviewed | restored:
            # A working parent selection is not a review of the subject's
            # approved identity, dates, geography or evidence navigation.
            for key in WORKING_PERSON_FIELDS:
                if key in previous:
                    existing[ident][key] = deepcopy(previous[key])
    for ident in public_families | previous_public:
        if ident not in incoming:
            raise ValueError('Published family subject absent from current public model: ' + ident)
        if ident not in existing:
            existing[ident] = deepcopy(incoming[ident])
    for ident in public_families | previous_public:
        if ident not in refresh:
            # A family correction must preserve the approved person's account,
            # geographic annotations and public DNA material.
            existing[ident]['parents'] = ([r for r in existing[ident].get('parents', []) if r.get('role') != 'father']
                                         + deepcopy([r for r in incoming[ident].get('parents', []) if r.get('role') == 'father']))
            for mother in set(maternal_scope.get(ident, [])) | set(previous_maternal_scope.get(ident, [])):
                rows = [r for r in incoming[ident].get('parents', [])
                        if r.get('role') == 'mother' and r.get('id') == mother]
                if len(rows) == 1:
                    if not any(r.get('role') == 'mother' for r in existing[ident]['parents']):
                        # The fresh scope requires an approved assessment of
                        # this same captured mother, not a new parent choice.
                        existing[ident]['parents'].insert(0, deepcopy(rows[0]))
                    else:
                        existing[ident]['parents'] = [deepcopy(rows[0])
                            if r.get('role') == 'mother' and r.get('id') == mother else r
                            for r in existing[ident]['parents']]
            for key in ('priorPublishedFathers', 'publicFamilySource', 'publicFatherAlternatives'):
                if key in incoming[ident]:
                    existing[ident][key] = deepcopy(incoming[ident][key])
                else:
                    existing[ident].pop(key, None)
            options = [r for r in existing[ident]['parents'] if r.get('id') in existing
                       and r.get('status') not in ('non-biological', 'non_biological')]
            options.sort(key=parent_order)
            existing[ident]['edge'] = (dict(parent=options[0]['id'], semantic='parent', role=options[0]['role'],
                type='hypothesis' if options[0].get('hypothesis') else 'recorded', status=options[0].get('status', 'unmarked'))
                if options else dict(parent='@smaller-families', type='group', semantic='collection'))
    managed_children = selected | prior_selected | public_families | previous_public
    family_parents = {incoming[i].get('edge', {}).get('parent') for i in selected}
    family_parents |= {prior_people[i].get('edge', {}).get('parent') for i in prior_selected if i in prior_people}
    alternative_parents = set(fresh['meta'].get('workingParentAlternativeIds', []))
    prior_alternatives = set(result['meta'].get('workingParentAlternativeIds', []))
    family_parents |= alternative_parents | prior_alternatives
    working_mothers = set(fresh['meta'].get('workingMotherIds', []))
    family_parents |= working_mothers | set(result['meta'].get('workingMotherIds', []))
    family_parents |= set(fresh['meta'].get('publicFamilyRelatedIds', []))
    family_parents |= set(result['meta'].get('publicFamilyRelatedIds', []))
    for ident in public_families | previous_public:
        for model in (incoming, prior_people):
            family_parents |= {r.get('id') for r in model.get(ident, {}).get('parents', []) if r.get('role') == 'father'}
    for father in family_parents:
        if father not in existing:
            continue
        if father not in incoming:
            if father in alternative_parents | prior_alternatives:
                # A retained placeholder may be absent from the generated model.
                # Keep its captured children as history, not active second fathers.
                moved = {i for i in selected if any(r.get('id') == father
                    for r in incoming[i].get('priorWorkingParents', []))}
                history = {r['id']: deepcopy(r) for r in existing[father].get('priorWorkingChildren', [])}
                children = []
                for row in existing[father].get('childrenRecorded', []):
                    if row.get('id') in moved:
                        history.setdefault(row['id'], deepcopy(row))
                    else:
                        children.append(row)
                for child, row in list(history.items()):
                    if child in managed_children and any(r.get('role') == 'father' and r.get('id') == father
                            for r in incoming.get(child, {}).get('parents', [])):
                        if not any(r.get('id') == child for r in children):
                            children.append(row)
                        del history[child]
                existing[father]['childrenRecorded'] = children
                if history:
                    existing[father]['priorWorkingChildren'] = list(history.values())
                else:
                    existing[father].pop('priorWorkingChildren', None)
            continue
        # Refresh reciprocal working children while retaining the parent's
        # approved biography, dates and every unrelated family record.
        children = [r for r in existing[father].get('childrenRecorded', []) if r.get('id') not in managed_children]
        children += deepcopy([r for r in incoming[father].get('childrenRecorded', []) if r.get('id') in managed_children])
        existing[father]['childrenRecorded'] = children
        if father in alternative_parents:
            existing[father]['priorWorkingChildren'] = deepcopy(incoming[father].get('priorWorkingChildren', []))
        elif father in prior_alternatives:
            existing[father].pop('priorWorkingChildren', None)
    # Explicitly reviewed chronology may correct a parent's retained display.
    # A new working relationship alone still preserves the approved dates.
    chronology = fresh['meta'].get('reviewedChronologyDisplay', {})
    for ident, fields in chronology.items():
        if ident not in existing:
            raise ValueError('Reviewed chronology subject absent from atlas: ' + ident)
        existing[ident].update({key: deepcopy(value) for key, value in fields.items()
                               if key in CHRONOLOGY_DISPLAY_FIELDS})
    result['people'] = list(existing.values())
    for p in result['people']:
        parent = p.get('edge', {}).get('parent')
        if parent and parent not in existing:
            raise ValueError('Working tree attachment missing: ' + parent)
    sections = {s['id']: s for s in result['sections']}
    for section in fresh['sections']:
        if section['id'] in documentary | public_families:
            sections[section['id']] = deepcopy(section)
    result['sections'] = list(sections.values())
    result['landmarks'] = list(dict.fromkeys(result['landmarks'] + sorted(documentary)))
    people = [p for p in result['people'] if p.get('kind') == 'person']
    result['meta'].update(people=len(people), groups=len(sections),
                          hypotheses=len(selected), documentaryPeople=len(documentary),
                          identityHypotheses=fresh['meta'].get('identityHypotheses', 0),
                          reviewedParentReplacementIds=sorted(reviewed),
                          reviewedFamilyRestorationIds=sorted(restored),
                          workingParentAlternativeIds=sorted(alternative_parents),
                          workingMotherIds=sorted(working_mothers),
                          reviewedChronologyDisplay=deepcopy(chronology),
                          maternalHypotheses=fresh['meta'].get('maternalHypotheses', 0),
                          parentRelationships=sum(len(p.get('parents', [])) for p in people),
                          workingOverlayIds=sorted(selected),
                          **{k: deepcopy(v) for k, v in fresh['meta'].items() if k.startswith(('publicFamily', 'publicMotherGrade')) or k == 'publicFatherHoldIds'},
                          workingUpdated=fresh['meta']['date'],
                          workingMethod='Selected uncertain connections, historical father fields and approved existing maternal grades are synchronized from current public dossiers. Approved atlas accounts are retained; publication reconciliation is not a new genealogical inference.')
    return result


def sync(site_root: Path, fresh: dict) -> bool:
    from tools.approved_restorations import documentary_renderer
    from tools.site_payloads import build
    from tools.stamp_asset_versions import VERSIONED_ASSET, asset_path, content_hash
    target = site_root / 'assets/research/atlas-model.json'
    if not target.exists():
        return False
    model = overlay_model(json.loads(target.read_text()), fresh)
    target.write_text(json.dumps(model, ensure_ascii=False, separators=(',', ':')) + '\n')
    renderer = site_root / 'assets/research/atlas.js'
    renderer.write_text(documentary_renderer(renderer.read_text()))
    build(site_root)
    # Dependencies first: the HTML cache stamp must cover the finished loader.
    for path in [site_root / 'assets/research/atlas-boot.js', site_root / 'onetree/index.html']:
        if not path.exists():
            continue
        def version(match):
            asset = asset_path(site_root, path, match['url'])
            return match[0] if asset is None or not asset.is_file() else (
                match['quote'] + match['url'] + '?v=' + content_hash(asset) + match['quote'])
        path.write_text(VERSIONED_ASSET.sub(version, path.read_text()))
    return True
