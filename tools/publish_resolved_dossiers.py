#!/usr/bin/env python3
"""Publish explicit approved assessments into machine dossiers; retain import provenance.

Run after dossier generation. No conclusions are extracted from narrative prose.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

try:
    import evidence_labels
    from relationship_probability import probability_for_relationship
    from catalogue_machine_data import compact_resolver_row
    from documentary_ancestry import valid_account_url
except ModuleNotFoundError:  # imported as tools.publish_resolved_dossiers
    from tools import evidence_labels
    from tools.relationship_probability import probability_for_relationship
    from tools.catalogue_machine_data import compact_resolver_row
    from tools.documentary_ancestry import valid_account_url

ROOT = Path(__file__).resolve().parents[1]
HISTORY_SEED = ROOT / 'research/relationship_history_seed.json'
SECTIONS = ('vitals', 'relationships', 'claims', 'events')
REVIEW_SCHEMA = {'data_view': {'enum': ['reviewed'], 'description': 'Default fields incorporate explicit approved structured assessments.'}, 'imported': {'type': 'object', 'required': ['sections', 'provenance'], 'description': 'Original pre-review sections and their import provenance; retained for comparison.'}, 'research_assessments': {'type': 'array', 'description': 'Approved source assessments applied to default fields, including remaining questions and superseded interpretations.'}, 'events': {'type': 'array', 'description': 'Explicit reviewed events with evidence references, roles and provenance.'}}
REVIEW_SCHEMA.update({
    'vitals': {'type': 'object', 'description': 'Resolved vital assertions. A null date/place is unresolved, not missing display data. Identity-dependent alternatives retain their own provenance and qualifiers; display_date is conditional display text, not a resolved date.'},
    'shared_relationship_assertions': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Current claim IDs resolved from /assets/research/relationship-assessments.json; shared by reciprocal dossier and network views.'},
    'relationship_history': {'type': 'array', 'description': 'Earlier relationship assertions with their original claim IDs and superseded_by links. Not current relationship recommendations.'},
})


def _resolve_approved(dossier, assessments):
    approved = [a for a in assessments if a.get('subject', '').casefold() == dossier['id'].casefold()
                and a.get('status') == 'approved']
    approved.sort(key=lambda a: (a.get('reviewed', ''), a.get('id', '')))
    if not approved and 'imported' not in dossier:
        return deepcopy(dossier)
    result = deepcopy(dossier)
    snapshot = result.get('imported')
    if snapshot is None:
        snapshot = {'provenance': deepcopy(dossier.get('provenance', {})),
                    'sections': {k: deepcopy(dossier[k]) for k in SECTIONS if k in dossier}}
    for key in SECTIONS:
        result.pop(key, None)
        if key in snapshot['sections']:
            result[key] = deepcopy(snapshot['sections'][key])
    result.pop('research_assessments', None)
    result.pop('data_view', None)
    result.pop('imported', None)
    if not approved:
        return result
    result['imported'] = deepcopy(snapshot)
    result['data_view'] = 'reviewed'
    result['research_assessments'] = deepcopy(approved)
    for assessment in approved:
        provenance = {'assessment_id': assessment['id'],
                      'source': '/assets/research/assessments.json',
                      'reviewed': assessment.get('reviewed'),
                      'basis': assessment.get('basis')}
        for kind, value in assessment.get('vitals', {}).items():
            # A reviewed vital is a complete assertion, not a blend with stale import fields.
            result.setdefault('vitals', {})[kind] = deepcopy(value)
            result['vitals'][kind]['provenance'] = deepcopy(provenance)
        for kind, qualifier in assessment.get('vital_qualifications', {}).items():
            # A scoped qualification does not replace the underlying observation.
            result.setdefault('vitals', {}).setdefault(kind, {}).update(
                qualifier=qualifier, qualification_provenance=deepcopy(provenance))
        for review in assessment.get('relationships', []):
            group = review['group']
            rows = result.setdefault('relationships', {}).setdefault(group, [])
            matches = [r for r in rows if r.get('id', '').casefold() == review['target'].casefold()]
            if not matches:
                matches = [{'id': review['target'], 'relationship': group,
                            'tree_relationship': False, 'evidence_ids': []}]
                rows.extend(matches)
            for row in matches:
                for key in ('status', 'display'):
                    if key in review:
                        row[key] = review[key]
                if 'label' in review:
                    row['status_label'] = review['label']
                row['basis'] = 'research_assessment'
                row['assessment_provenance'] = deepcopy(provenance)
                for claim in result.get('claims', []):
                    if row.get('claim_id') and claim.get('id') == row['claim_id']:
                        claim['status'] = row['status']
                        claim['status_label'] = row.get('status_label', row['status'])
                        claim['assessment_provenance'] = deepcopy(provenance)
                        if 'display' in row:
                            claim['display'] = row['display']
        if 'events' in assessment:
            events = result.setdefault('events', [])
            for event in assessment['events']:
                events[:] = [e for e in events if not (event.get('evidence_id') and
                             e.get('evidence_id') == event['evidence_id'])]
                events.append({**deepcopy(event), 'provenance': deepcopy(provenance)})
    return result


def shared_relationship(profile_id, relation, assessments):
    """Resolve one explicitly assessed pair; never infer adjoining relatives."""
    pair = {profile_id.casefold(), str(relation.get('id') or '').casefold()}
    for assessment in assessments:
        if assessment.get('publication_status') != 'approved':
            continue
        if not assessment.get('assertion_id'):
            raise ValueError('Approved shared relationship lacks a stable assertion_id')
        if pair != {person.casefold() for person in assessment.get('people', [])}:
            continue
        result = {k: deepcopy(v) for k, v in assessment.items()
                  if k not in ('people', 'perspectives', 'historical_assertions')}
        result.update(next((deepcopy(v) for k, v in assessment.get('perspectives', {}).items()
                            if k.casefold() == profile_id.casefold()), {}))
        if assessment.get('assertion_id'):
            result.update(claim_id=assessment['assertion_id'], lifecycle=assessment.get('lifecycle') or 'current',
                          display=assessment.get('display') or ('hypothesis' if assessment.get('hypothesis_status') else 'current'), tree_relationship=False,
                          relationship_source='shared_research_assertion')
            role = result.get('relationship', 'relationship')
            # Shared vocabulary: tools/evidence_labels.py.
            if role.casefold() in evidence_labels.ROLE_NOUNS:
                default_label = evidence_labels.relationship_label(result['status'], role)
            else:
                default_label = evidence_labels.label(result['status']) + ' ' + role
            result.setdefault('status_label', default_label)
            result['assessment_source'] = '/assets/research/relationship-assessments.json'
            result['record_source'] = '/assets/research/canonical-records.json'
            result['historical_claim_ids'] = [h['claim_id'] for h in assessment.get('historical_assertions', [])
                                               if h['profile_id'].casefold() == profile_id.casefold()]
        return result
    return None


def _sync_presentation(result):
    # These are derived mirrors of research facts, never decision inputs.
    for row in result.get('relationships', {}).get('parents', []):
        row['probability'] = probability_for_relationship(row, result.get('id'))
    if 'presentation' in result:
        result['presentation']['vitals'] = deepcopy(result.get('vitals', {}))
        result['presentation']['relationships'] = deepcopy(result.get('relationships', {}))
    return result


def _restore_historical_import(dossier):
    """Retain earlier claim provenance after a live tree link is changed."""
    if not HISTORY_SEED.exists():
        return dossier
    seed = json.loads(HISTORY_SEED.read_text()).get('profiles', {}).get(dossier['id'])
    if not seed:
        return dossier
    dossier = deepcopy(dossier)
    sections = dossier.get('imported', {}).get('sections', dossier)
    claims = sections.setdefault('claims', [])
    known = {claim.get('id') for claim in claims}
    claims.extend(deepcopy(claim) for claim in seed.get('claims', []) if claim.get('id') not in known)
    for group, rows in seed.get('relationships', {}).items():
        current = sections.setdefault('relationships', {}).setdefault(group, [])
        ids = {row.get('claim_id') for row in current}
        current.extend(deepcopy(row) for row in rows if row.get('claim_id') not in ids)
    return dossier


def resolve(dossier, assessments, shared_assessments=()):
    # A later source refresh can add evidence and its original occurrence claim
    # after an import snapshot was saved. Retain the pair before either person
    # or shared assessments restore that snapshot.
    if dossier.get('imported'):
        referenced = {cid for item in dossier.get('evidence', []) for cid in item.get('claim_ids', [])}
        retained = {claim['id'] for claim in dossier['imported']['sections'].get('claims', [])}
        additions = [deepcopy(claim) for claim in dossier.get('claims', [])
                     if claim['id'] in referenced and claim['id'] not in retained]
        if additions:
            dossier = deepcopy(dossier)
            dossier['imported']['sections'].setdefault('claims', []).extend(additions)
    dossier = _restore_historical_import(dossier)
    for assessment in shared_assessments:
        if assessment.get('publication_status') == 'approved' and not assessment.get('assertion_id'):
            raise ValueError('Approved shared relationship lacks a stable assertion_id')
    result = _resolve_approved(dossier, assessments)
    result.pop('relationship_history', None)
    result.pop('shared_relationship_assertions', None)
    active = [a for a in shared_assessments if a.get('assertion_id')
              and a.get('publication_status') == 'approved'
              and dossier['id'].casefold() in {p.casefold() for p in a['people']}]
    if not active:
        return _sync_presentation(result)
    result.setdefault('imported', deepcopy(dossier.get('imported') or {
        'provenance': dossier.get('provenance', {}),
        'sections': {k: dossier[k] for k in SECTIONS if k in dossier}}))
    result['data_view'] = 'reviewed'
    result.setdefault('research_assessments', [])
    result['shared_relationship_assertions'] = [a['assertion_id'] for a in active]
    history = result['relationship_history'] = []
    for assessment in active:
        aid = assessment['assertion_id']
        claims = result.setdefault('claims', [])
        previous_ids = []
        for previous in assessment.get('historical_assertions', []):
            if previous['profile_id'].casefold() != dossier['id'].casefold():
                continue
            previous_ids.append(previous['claim_id'])
            for claim in claims:
                if claim['id'] == previous['claim_id']:
                    # Keep the exact original wording/evidence in the import snapshot
                    # and this historical assertion. Retire only its stated scope.
                    claim.update(lifecycle='historical', status='superseded',
                                 status_label=previous['label'], superseded_by=aid,
                                 supersession_scope=previous['scope'])
        found = False
        for group, rows in result.get('relationships', {}).items():
            for index, row in enumerate(rows):
                resolved = shared_relationship(dossier['id'], row, [assessment])
                if not resolved:
                    continue
                correction = (assessment.get('role_correction') or {}).get(dossier['id'])
                if correction and row.get('relationship') not in [correction.get('to'), *correction.get('from', [])]:
                    continue
                historical = deepcopy(row)
                historical.update(lifecycle='historical', superseded_by=aid)
                if historical.get('claim_id') in previous_ids:
                    historical.update(status='superseded', status_label='Historical attachment; not established')
                history.append(historical)
                old_id = row.get('claim_id')
                if old_id and old_id != aid and old_id not in previous_ids:
                    previous_ids.append(old_id)
                    for old_claim in claims:
                        if old_claim.get('id') == old_id:
                            old_claim.update(lifecycle='historical', superseded_by=aid,
                                             supersession_scope='The previous relationship assessment is replaced by the reviewed record basis; this does not reject the relationship.')
                # Do not carry the earlier assessment's evidence or verdict into
                # the new assertion merely because it references the same person.
                clean = {k: deepcopy(row[k]) for k in ('id', 'name', 'url', 'json_url', 'network_url', 'wikitree_url') if k in row}
                resolved['historical_claim_ids'] = list(previous_ids)
                rows[index] = {**clean, **resolved}
                current = rows[index]
                found = True
        if not found:
            # Explicit reviewed record kinship can be absent from WikiTree's
            # parent-derived family links. Publish it as a research edge,
            # preserving the unmodified imported tree underneath.
            if not assessment.get('allow_new_relationship'):
                raise ValueError(f"Shared assertion {aid} has no relationship on {dossier['id']}")
            others = [person for person in assessment['people']
                      if person.casefold() != dossier['id'].casefold()]
            if len(others) != 1:
                raise ValueError(f"Shared assertion {aid} must identify one relative")
            other = others[0]
            current = shared_relationship(dossier['id'], {'id': other}, [assessment])
            groups = {'father': 'parents', 'mother': 'parents', 'son': 'children',
                      'daughter': 'children', 'child': 'children', 'sibling': 'siblings', 'spouse': 'spouses'}
            group = groups.get(current.get('relationship'))
            if not group or not assessment.get('source_ids'):
                raise ValueError(f"Shared assertion {aid} needs a supported family role and sources")
            current.update(id=other, name=assessment.get('profile_names', {}).get(other, other),
                           url=f'/people/{other.lower()}.html',
                           wikitree_url=f'https://www.wikitree.com/wiki/{other}')
            relative_urls = (assessment.get('profile_urls') or {}).get(other)
            if relative_urls is not None:
                if not valid_account_url(relative_urls.get('url', '')):
                    raise ValueError(f'Shared assertion {aid} has an invalid documentary account URL')
                current.update(url=relative_urls['url'], wikitree_url=None)
            result.setdefault('relationships', {}).setdefault(group, []).append(current)
        correction = (assessment.get('role_correction') or {}).get(dossier['id'])
        if correction:
            groups = {'father': 'parents', 'mother': 'parents', 'son': 'children',
                      'daughter': 'children', 'child': 'children', 'sibling': 'siblings', 'spouse': 'spouses'}
            role = current.get('relationship')
            if correction.get('to') != role or role not in groups or not assessment.get('source_ids'):
                raise ValueError(f'Role correction {aid} needs a supported destination role')
            # One reviewed pair may replace both a mistaken parent row and an
            # ungraded sibling row. Preserve both in history, publish one row
            # in the group matching the explicitly corrected relationship.
            for rows in result['relationships'].values():
                rows[:] = [row for row in rows if row.get('claim_id') != aid]
            result['relationships'].setdefault(groups[role], []).append(current)
        # Status, role, interpretation and citations come from the same reviewed
        # pair and its explicit viewing-person perspective, not a UI override.
        claim = {k: deepcopy(current[k]) for k in (
            'status', 'status_label', 'relationship', 'reason', 'basis', 'source_ids',
            'hypothesis_status', 'limitations', 'identity_scope', 'analysis_links',
            'provenance', 'research_basis', 'assessment_date', 'assessment_source', 'record_source') if k in current}
        claim.update(id=aid, type='relationship_hypothesis' if assessment.get('hypothesis_status') else 'assessed_relationship',
                     subject_ids=assessment['people'], perspective_id=dossier['id'],
                     claim=assessment.get('claim') or current['reason'],
                     notes=current['reason'], lifecycle=current.get('lifecycle') or 'current', historical_claim_ids=previous_ids)
        claim['evidence_ids'] = []  # source_ids identify canonical records, not imported evidence items.
        claims[:] = [c for c in claims if c.get('id') != aid]
        claims.append(claim)
    return _sync_presentation(result)


def resolve_index_row(row, reviewed):
    row = deepcopy(row.get('imported', row))
    dossier = reviewed.get(row.get('id', '').casefold())
    if not dossier:
        return row
    row['imported'] = deepcopy(row)
    row['data_view'] = 'reviewed'
    row['assessment_provenance'] = [a['id'] for a in dossier['research_assessments']]
    for assessment in dossier['research_assessments']:
        for kind, vital in assessment.get('vitals', {}).items():
            row[kind + '_place'] = vital.get('place')
            row[kind + '_status'] = vital.get('status')
            date = str(vital.get('date', ''))
            row[kind + '_year'] = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
    row['reviewed_relationships'] = deepcopy(dossier['relationships'])
    row['reviewed_vitals'] = deepcopy(dossier.get('vitals', {}))
    if any(r.get('group') == 'parents' for a in dossier['research_assessments']
           for r in a.get('relationships', [])):
        parents = [r for r in dossier['relationships'].get('parents', [])
                   if r.get('status') in ('proved', 'strongly_supported')
                   and r.get('display') != 'alternative']
        row['parent_ids'] = [r['id'] for r in parents]
        row['parent_names'] = [r.get('name', r['id']) for r in parents]
        for role in ('father', 'mother'):
            row[role + '_id'] = next((r['id'] for r in parents if r.get('relationship') == role), None)
    return row


def project_catalogue_vitals(rows, assessments):
    """Project explicitly approved date/location fields; retain reversible imports."""
    allowed = {'birth','birth_note','birth_year','birth_location','birth_location_note',
               'death','death_year','death_location','date_years','regions','locations',
               'location_aliases','location_groups','estimated_location','missing_vital_location','field_statuses'}
    for row in rows:
        prior = row.pop('vital_review', {})
        for key, original in prior.get('original_fields', {}).items():
            if original['present']: row[key] = deepcopy(original['value'])
            else: row.pop(key, None)
        ids = {str(i).casefold() for i in row.get('profile_ids', []) or [row.get('id', '')]}
        reviews = [a for a in assessments if a.get('status') == 'approved'
                   and str(a.get('subject', '')).casefold() in ids and a.get('catalogue_projection')]
        originals = {}
        for review in reviews:
            projection = review['catalogue_projection']
            if set(projection) - allowed:
                raise ValueError('Catalogue vital projection contains non-vital fields')
            for key, value in projection.items():
                originals.setdefault(key, {'present': key in row, 'value': deepcopy(row.get(key))})
                if key in {'birth_location', 'death_location'} and isinstance(value, str) and value.strip().casefold() == 'unknown':
                    value = ''
                row[key] = deepcopy(value)
        if reviews:
            row['vital_review'] = {'assessment_ids': [a['id'] for a in reviews], 'original_fields': originals}
    return rows


def project_catalogue_parents(rows, reviewed):
    """Use the current assessed parents in search, retaining reversible imports."""
    fields = ('father', 'mother', 'missing_father', 'missing_mother', 'family_root', 'family_roots')
    for row in rows:
        prior = row.pop('parent_review', {})
        for key, original in prior.get('original_fields', {}).items():
            if original['present']:
                row[key] = deepcopy(original['value'])
            else:
                row.pop(key, None)
        dossier = reviewed.get(str(row.get('id', '')).casefold())
        if not dossier:
            continue
        originals = {key: {'present': key in row, 'value': deepcopy(row.get(key))}
                     for key in fields}
        for role in ('father', 'mother'):
            parents = []
            for relation in dossier.get('relationships', {}).get('parents', []):
                if (relation.get('relationship') != role
                        or relation.get('lifecycle') not in (None, 'current')
                        or relation.get('display') in ('alternative', 'historical', 'superseded')
                        or relation.get('status') in ('rejected', 'superseded', 'contradicted')
                        or relation.get('publication_status') in ('withheld', 'blocked', 'rejected')):
                    continue
                item = {key: deepcopy(relation[key]) for key in
                        ('id', 'name', 'url', 'wikitree_url', 'withheld', 'outside_export')
                        if key in relation}
                status = relation.get('status')
                assessed = status not in (None, '', 'unknown', 'unmarked')
                item['certainty'] = status if assessed else relation.get('tree_status') or 'unmarked'
                item['certainty_label'] = (relation.get('status_label') if assessed
                    else relation.get('tree_status_label')) or item['certainty'].replace('_', ' ')
                item['probability'] = probability_for_relationship(relation, row.get('id'))
                parents.append(item)
            row[role] = parents
            row['missing_' + role] = not parents
        row['parent_review'] = {'original_fields': originals}
        # The exported roots remain historical leads, but a removed father
        # cannot continue assigning the subject to a current paternal branch.
        if ('family_root' in row and not any(
                parent.get('id') and not parent.get('outside_export')
                for parent in row.get('father', []))):
            row['family_root'] = None
    counts = {}
    for row in rows:
        if root := row.get('family_root'):
            counts[root['id']] = counts.get(root['id'], 0) + 1
    for row in rows:
        primary = row.get('family_root')
        for root in row.get('family_roots', []):
            root['catalogued_members'] = counts.get(root['id'], 0) if primary and primary['id'] == root['id'] else 0
        if primary and 'catalogued_members' in primary:
            primary['catalogued_members'] = counts[primary['id']]
    return rows


def project_catalogue_spouses(rows, reviewed):
    """Keep proposed couples visible in catalogue cells, retaining captured partners."""
    for row in rows:
        identifiers = row.get('profile_ids') or [row.get('id') or row.get('catalogue_id', '')]
        dossier = next((reviewed[i.casefold()] for i in identifiers if i.casefold() in reviewed), {})
        proposals = [r for r in dossier.get('relationships', {}).get('spouses', [])
                     if r.get('relationship_source') == 'shared_research_assertion'
                     and r.get('allow_new_relationship') and not r.get('withheld')
                     and r.get('display') not in {'alternative', 'historical', 'superseded'}
                     and r.get('lifecycle') not in {'alternative', 'historical', 'superseded'}
                     and r.get('status') not in {'excluded', 'rejected', 'non-biological'}]
        prior = row.get('spouse_review')
        if not proposals and not prior:
            continue
        originals = deepcopy(prior['original_fields'] if prior else row.get('spouses', []))
        if not proposals:
            row['spouses'] = originals
            row.pop('spouse_review', None)
            continue
        partners = {r['id']: r for r in originals if r.get('id')}
        for proposal in proposals:
            ident = proposal['id']
            partners[ident] = {**partners.get(ident, {}), **{
                key: deepcopy(proposal[key]) for key in (
                    'id', 'name', 'url', 'wikitree_url', 'status', 'probability',
                    'record_scope', 'claim_id', 'relationship_source', 'source_ids')
                if key in proposal}}
        row['spouses'] = list(partners.values())
        row['spouse_review'] = {'original_fields': originals}
    return rows


def merge_maintained_assessments(registry, maintained):
    """Replace the durable register's own rows; retain unrelated publications."""
    source = {row['id']: deepcopy(row) for row in maintained}
    if len(source) != len(maintained) or any(not key or not row.get('subject') for key, row in source.items()):
        raise ValueError('Maintained assessments need unique IDs and subjects')
    result = deepcopy(registry)
    previous = set(registry.get('maintained_assessment_ids', []))
    rows = []
    for row in registry.get('assessments', []):
        if row['id'] in source:
            rows.append(source.pop(row['id']))
        elif row['id'] not in previous:
            rows.append(deepcopy(row))
    rows.extend(source.values())
    result['assessments'] = rows
    result['maintained_assessment_ids'] = [row['id'] for row in maintained]
    return result


def publish(root=ROOT / 'www'):
    path = root / 'assets/research/assessments.json'
    maintained_path = ROOT / 'research/vital_assessments.json'
    has_maintained_source = root.resolve() == (ROOT / 'www').resolve() and maintained_path.exists()
    registry = (json.loads(path.read_text()) if path.exists() or not has_maintained_source
                else {'schema_version': 1, 'assessments': []})
    if has_maintained_source:
        merged = merge_maintained_assessments(registry, json.loads(maintained_path.read_text())['assessments'])
        if merged != registry:
            registry = merged
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    try:
        from documentary_ancestry import vital_assessments
    except ModuleNotFoundError:
        from tools.documentary_ancestry import vital_assessments
    chronology_path = root / 'data/ancestry-documentary-people.json'
    if root.resolve() == (ROOT / 'www').resolve():
        chronology_path.write_text((ROOT / 'research/ancestry-connections/documentary-people.json').read_text())
    assessments = [a for a in registry.get('assessments', []) if a.get('derived_from') != 'documentary_chronology']
    assessments += vital_assessments(chronology_path)
    if assessments != registry.get('assessments', []):
        registry['assessments'] = assessments
        path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    search_path = root / 'data/catalogue-search-index.json'
    if search_path.exists():
        search = json.loads(search_path.read_text())
        prior_search = deepcopy(search)
        project_catalogue_vitals(search, assessments)
    shared_path = root / 'assets/research/relationship-assessments.json'
    if root.resolve() == (ROOT / 'www').resolve():
        shared_path.write_text((ROOT / 'research/relationship_assessments.json').read_text())
        (root / 'assets/research/canonical-records.json').write_text((ROOT / 'research/canonical_records.json').read_text())
        (root / 'assets/research/relationship-probabilities.json').write_text((ROOT / 'research/relationship_probability_estimates.json').read_text())
    shared = json.loads(shared_path.read_text()) if shared_path.exists() else []
    changed = 0
    reviewed = {}
    for path in sorted((root / 'people').glob('*.json')):
        if path.name.endswith('.network.json'):
            continue
        original = json.loads(path.read_text())
        resolved = resolve(original, assessments, shared)
        # A superseded record subject's redirect stub carries the id of the
        # person it now points to; only that person's own dossier feeds the
        # network and index projections.
        if resolved.get('data_view') == 'reviewed' and not resolved.get('redirect_to'):
            reviewed[resolved['id'].casefold()] = resolved
        if resolved != original:
            path.write_text(json.dumps(resolved, ensure_ascii=False, separators=(',', ':')) + '\n')
            changed += 1
    for path in [root / 'data/people-index.json', root / 'data/people-index.js',
                 *sorted((root / 'data/resolve').glob('*.json'))]:
        if not path.exists():
            continue
        raw = path.read_text()
        prefix = raw.split('=', 1)[0] + '=' if path.suffix == '.js' else ''
        payload = json.loads(raw[len(prefix):].strip().rstrip(';'))
        before = deepcopy(payload)
        if isinstance(payload, list):
            payload = [resolve_index_row(row, reviewed) for row in payload]
            project_catalogue_spouses(payload, reviewed)
            if path.name == 'people-index.json':
                payload = [compact_resolver_row(row) for row in payload]
        elif 'candidates' in payload:
            payload['candidates'] = [resolve_index_row(row, reviewed) for row in payload['candidates']]
        if payload != before:
            path.write_text(prefix + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + (';\n' if prefix else '\n'))
    for path in sorted((root / 'people').glob('*.network.json')):
        before = json.loads(path.read_text())
        network = deepcopy(before.get('imported', before))
        dossier = reviewed.get(network.get('person', {}).get('id', '').casefold())
        if dossier:
            network['imported'] = deepcopy(network)
            network['data_view'] = 'reviewed'
            network['relationships'] = [deepcopy(r) for rows in dossier['relationships'].values() for r in rows]
            network['vitals'] = deepcopy(dossier.get('vitals', {}))
            network['assessment_provenance'] = [a['id'] for a in dossier['research_assessments']]
            if dossier.get('shared_relationship_assertions'):
                network['shared_relationship_assertions'] = deepcopy(dossier['shared_relationship_assertions'])
                network['relationship_history'] = deepcopy(dossier['relationship_history'])
                ids = set(network['shared_relationship_assertions']) | {r.get('claim_id') for r in network['relationship_history']}
                network['claims'] = [deepcopy(c) for c in dossier.get('claims', [])
                                     if c.get('id') in ids or c.get('superseded_by') in ids]
        if network != before:
            path.write_text(json.dumps(network, ensure_ascii=False, separators=(',', ':')) + '\n')
    schema_path = root / 'data/schema/person.schema.json'
    if schema_path.exists():
        schema = json.loads(schema_path.read_text())
        before = deepcopy(schema)
        schema.setdefault('properties', {}).update(REVIEW_SCHEMA)
        if schema != before:
            schema_path.write_text(json.dumps(schema, indent=2) + '\n')
    if search_path.exists():
        project_catalogue_parents(search, reviewed)
        project_catalogue_spouses(search, reviewed)
        for row in search:
            for role in ('father', 'mother'):
                for parent in row.get(role, []):
                    if not row.get('parent_review'):
                        parent['probability'] = probability_for_relationship(
                            {'tree_status': parent.get('certainty'), 'data_status': parent.get('data_status'),
                             'withheld': parent.get('withheld')}, row.get('id'), parent.get('id'), role)
        if search != prior_search:
            packed = json.dumps(search, ensure_ascii=False, separators=(',', ':'))
            search_path.write_text(packed + '\n')
            (root / 'data/people-index.js').write_text('window.glasgowPeopleIndex=' + packed + ';\n')
            if root.resolve() == (ROOT / 'www').resolve():
                try:
                    from catalogue_search_index import refresh as refresh_browser_index
                except ModuleNotFoundError:
                    from tools.catalogue_search_index import refresh as refresh_browser_index
                refresh_browser_index(root)
    people_path = root / 'data/people.json'
    if people_path.exists():
        people = json.loads(people_path.read_text())
        before = deepcopy(people)
        project_catalogue_vitals(people['people'], assessments)
        project_catalogue_spouses(people['people'], reviewed)
        if people != before:
            people_path.write_text(json.dumps(people, ensure_ascii=False, separators=(',', ':')) + '\n')
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--www', type=Path, default=ROOT / 'www')
    args = parser.parse_args()
    print(f'Resolved dossiers updated: {publish(args.www)}')
