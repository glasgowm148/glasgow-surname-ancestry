"""Explicit pending family amendments, including recorded confidence changes.

Never turn a biography mention or an already-applied tree flag into new work.
"""
try:
    from relationship_probability import confidence_band, probability_for_relationship
except ModuleNotFoundError:
    from tools.relationship_probability import confidence_band, probability_for_relationship

ROLES = {'father', 'mother', 'spouse', 'child', 'sibling'}


def catalogue_changes(update):
    """Project amendments to existing profiles, excluding new-profile parents.

    Creation drafts retain their full relationships; they are not instructions
    to add or regrade a parent on an existing WikiTree child profile.
    """
    if not update or update.get('new_profile') is True:
        return []
    return update.get('relationship_changes') or []


def normalise_change(change, subject_id=None):
    role = {'son': 'child', 'daughter': 'child', 'brother': 'sibling', 'sister': 'sibling'}.get(
        change.get('relationship'), change.get('relationship'))
    action = {'upgrade': 'regrade', 'confidence': 'regrade', 'change': 'regrade'}.get(
        change.get('action'), change.get('action'))
    if role not in ROLES or action not in {'add', 'replace', 'regrade'}:
        return None
    status = change.get('assessment_after') or change.get('after') or change.get('status') or 'unknown'
    rating = probability_for_relationship({'status': status}, subject_id or change.get('subject_id'), change.get('relative_id'), role)
    return {**change, 'relationship': role, 'action': action, 'status': status,
            'confidence_band': rating['band'], 'probability': rating}


def pending_changes(profile_id, specification, captures, assessments, findings):
    """Enrich an already-pending update; keep explicit before/after provenance."""
    explicit = [c for row in specification.get('relationship_changes', [])
                if (c := normalise_change(row, profile_id))]
    locked = {c['relationship'] for c in explicit if c['action'] in {'add', 'replace'}}
    candidates = list(explicit)
    by_id = {a.get('assertion_id'): a for a in assessments
             if a.get('publication_status') == 'approved'
             and a.get('lifecycle') not in {'alternative', 'historical', 'superseded'}
             and a.get('display') not in {'alternative', 'historical', 'superseded'}}
    fields = captures.get(profile_id, {}).get('profile_fields', {})
    for finding in findings:
        for change in finding.get('relationship_changes', []):
            role = change.get('relationship')
            if (change.get('subject_id') != profile_id or role not in {'father', 'mother'}
                    or role in locked or not change.get('previous_status_provenance')):
                continue
            assessment = by_id.get(change.get('assertion_id'))
            if not assessment or assessment.get('perspectives', {}).get(profile_id, {}).get('relationship') != role:
                continue
            relative = change.get('relative_id')
            if {profile_id, relative} != set(assessment.get('people', [])):
                continue
            # A confidence change concerns the same currently attached relative.
            parent_fields = captures.get(relative, {}).get('profile_fields', {})
            if not fields.get(role.title()) or fields.get(role.title()) != parent_fields.get('Id'):
                continue
            after = assessment.get('status') or change.get('assessment_after') or change.get('after')
            saved = str((fields.get('DataStatus') or {}).get(role.title()) or '')
            if confidence_band(after) == 'confident' and saved in {'20', '30'}:
                continue  # Already confidently marked in the latest capture.
            if confidence_band(change.get('before')) == confidence_band(after):
                continue
            row = normalise_change({**change, 'action': 'regrade', 'status': after,
                                    'assessment_after': after, 'finding_id': finding.get('id'),
                                    'scope': assessment.get('record_scope') or change.get('scope')}, profile_id)
            if row:
                candidates.append(row)
    latest = {}
    for change in candidates:
        latest[(change['relationship'], change.get('relative_id'), change['action'])] = change
    return list(latest.values())
