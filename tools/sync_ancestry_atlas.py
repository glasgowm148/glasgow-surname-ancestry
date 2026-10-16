"""Carry selected public working families into the primary Whole tree viewer."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


def overlay_model(retained: dict, fresh: dict) -> dict:
    """Refresh working subjects without replacing the approved atlas publication."""
    result = deepcopy(retained)
    incoming = {p['id']: p for p in fresh['people']}
    selected = {p['id'] for p in fresh['people'] if p.get('edge', {}).get('type') == 'hypothesis'}
    prior_people = {p['id']: p for p in retained['people']}
    prior_selected = set(result['meta'].get('workingOverlayIds', []))
    documentary = {p['id'] for p in fresh['people'] if p.get('documentary')}
    reviewed = set(fresh['meta'].get('reviewedParentReplacementIds', []))
    refresh = selected | set(result['meta'].get('workingOverlayIds', [])) | documentary | reviewed | set(result['meta'].get('reviewedParentReplacementIds', []))
    existing = {p['id']: p for p in result['people']}
    for ident in refresh:
        if ident not in incoming:
            raise ValueError('Working subject absent from current public model: ' + ident)
        existing[ident] = deepcopy(incoming[ident])
    managed_children = selected | prior_selected
    family_parents = {incoming[i].get('edge', {}).get('parent') for i in selected}
    family_parents |= {prior_people[i].get('edge', {}).get('parent') for i in prior_selected if i in prior_people}
    for father in family_parents:
        if father not in incoming or father not in existing:
            continue
        # Refresh reciprocal working children while retaining the parent's
        # approved biography, dates and every unrelated family record.
        children = [r for r in existing[father].get('childrenRecorded', []) if r.get('id') not in managed_children]
        children += deepcopy([r for r in incoming[father].get('childrenRecorded', []) if r.get('id') in managed_children])
        existing[father]['childrenRecorded'] = children
    result['people'] = list(existing.values())
    for p in result['people']:
        parent = p.get('edge', {}).get('parent')
        if parent and parent not in existing:
            raise ValueError('Working tree attachment missing: ' + parent)
    sections = {s['id']: s for s in result['sections']}
    for section in fresh['sections']:
        if section['id'] in documentary:
            sections[section['id']] = deepcopy(section)
    result['sections'] = list(sections.values())
    result['landmarks'] = list(dict.fromkeys(result['landmarks'] + sorted(documentary)))
    people = [p for p in result['people'] if p.get('kind') == 'person']
    result['meta'].update(people=len(people), groups=len(sections),
                          hypotheses=len(selected), documentaryPeople=len(documentary),
                          identityHypotheses=fresh['meta'].get('identityHypotheses', 0),
                          reviewedParentReplacementIds=sorted(reviewed),
                          parentRelationships=sum(len(p.get('parents', [])) for p in people),
                          workingOverlayIds=sorted(selected),
                          workingUpdated=fresh['meta']['date'],
                          workingMethod='Selected uncertain family connections are synchronized from the current public research model. Documentary record periods are not birth dates; other profiles retain the approved atlas publication.')
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
