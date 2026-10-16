"""Carry selected public working families into the primary Whole tree viewer."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


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
    refresh = selected | set(result['meta'].get('workingOverlayIds', [])) | documentary | reviewed | set(result['meta'].get('reviewedParentReplacementIds', []))
    refresh |= restored | set(result['meta'].get('reviewedFamilyRestorationIds', []))
    existing = {p['id']: p for p in result['people']}
    for ident in refresh:
        if ident not in incoming:
            raise ValueError('Working subject absent from current public model: ' + ident)
        existing[ident] = deepcopy(incoming[ident])
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
        if father not in incoming or father not in existing:
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
                          maternalHypotheses=fresh['meta'].get('maternalHypotheses', 0),
                          parentRelationships=sum(len(p.get('parents', [])) for p in people),
                          workingOverlayIds=sorted(selected),
                          **{k: deepcopy(v) for k, v in fresh['meta'].items() if k.startswith('publicFamily') or k == 'publicFatherHoldIds'},
                          workingUpdated=fresh['meta']['date'],
                          workingMethod='Selected uncertain connections and historical father fields are synchronized from current public dossiers. Existing research grades and approved atlas accounts are retained; this publication reconciliation is not a new genealogical inference.')
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
