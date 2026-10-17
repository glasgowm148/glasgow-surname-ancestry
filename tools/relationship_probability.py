"""Shared, qualitative probability bands for relationship assessments."""

from __future__ import annotations

from typing import Any

SCALE_NOTE = (
    "Grade-derived research judgment bands; ranges are not statistical calibration "
    "and no point probability is implied."
)

BANDS = {
    "confident": {"label": "Confident (90–99%)", "minimum": 0.90, "maximum": 0.99, "rank": 4},
    "probable": {"label": "Probable (60–89%)", "minimum": 0.60, "maximum": 0.89, "rank": 3},
    "possible": {"label": "Possible (30–59%)", "minimum": 0.30, "maximum": 0.59, "rank": 2},
    "uncertain": {"label": "Uncertain/speculative (1–29%)", "minimum": 0.01, "maximum": 0.29, "rank": 1},
    "unrated": {"label": "Unrated", "minimum": None, "maximum": None, "rank": 0},
}

_ALIASES = {
    "proved": "confident", "documented": "confident", "certain": "confident",
    "confirmed": "confident", "strongly_supported": "confident", "dna_confirmed": "confident",
    "confident": "confident", "probable": "probable", "possible": "possible",
    "uncertain": "uncertain", "speculative": "uncertain", "guess": "uncertain",
}
_UNRATED = {"unknown", "unassessed", "unmarked", "conflict", "disputed", "contradicted",
            "rejected", "nonbiological", "non_biological", "withheld", ""}
_TREE_STATUS = {"5": "nonbiological", "10": "uncertain", "20": "confident", "30": "confident"}


def confidence_band(status: Any) -> str:
    """Return a band key for an assessment grade, or ``unrated``."""
    key = str(status or "").strip().casefold().replace(" ", "_").replace("-", "_")
    return _ALIASES.get(key, "unrated") if key not in _UNRATED else "unrated"


def probability_for_relationship(row: dict[str, Any]) -> dict[str, Any]:
    """Project one relationship row into a qualitative probability range."""
    if row.get("withheld") is True:
        value, assessed, origin = "withheld", True, "research"
    else:
        value = next((row.get(key) for key in ("status", "certainty")
                      if row.get(key) not in (None, "", "unknown", "unassessed", "unmarked")), None)
        assessed = value is not None
        origin = "research" if assessed else "unassessed"
    if not assessed:
        tree = row.get("tree_status")
        if tree in (None, ""):
            tree = _TREE_STATUS.get(str(row.get("data_status") or ""))
        if tree:
            value, origin = tree, "wikitree"
    band = confidence_band(value)
    if str(value or '').casefold().replace('-', '_') in {'confident', 'dna_confirmed'}:
        origin = 'wikitree'
    if row.get('dossierStatus') in {'unknown', 'unmarked', 'unassessed'} and row.get('tree_status'):
        origin = 'wikitree'
    result = {"band": band, **BANDS[band], "method": "assessment_band", "origin": origin}
    scope = row.get("record_scope", row.get("recordScope"))
    if scope:
        result["scope"] = scope
    return result


def annotate_model(model: dict[str, Any]) -> dict[str, Any]:
    """Assign the same bands to both directions of public parent links."""
    try:
        import evidence_labels
    except ModuleNotFoundError:
        from tools import evidence_labels
    people = {p['id']: p for p in model.get('people', [])}
    inverse_roles = {}
    for child in people.values():
        for row in child.get('parents', []):
            rating = probability_for_relationship(row)
            row['probability'] = rating
            base = row.get('assessmentLabel') or row.get('statusLabel') or evidence_labels.label(row.get('status'))
            if not row.get('assessmentLabel') and not row.get('statusLabel') and rating['origin'] == 'wikitree':
                base = evidence_labels.label(row.get('tree_status') or row.get('status'))
            row['assessmentLabel'] = base
            band = rating['label'].split('(', 1)[-1].rstrip(')') if rating['minimum'] is not None else 'Unrated'
            row['statusLabel'] = base + ' · ' + band
            parent = people.get(row.get('id'), {})
            for inverse in parent.get('childrenRecorded', []):
                if inverse.get('id') == child['id']:
                    roles = inverse_roles.setdefault((parent['id'], child['id']), {})
                    roles[row.get('role') or 'parent'] = dict(rating)
                    inverse['probability'] = dict(rating)
                    inverse_base = inverse.get('assessmentLabel') or inverse.get('statusLabel') or base.replace('father', 'child').replace('mother', 'child')
                    inverse['assessmentLabel'] = inverse_base
                    inverse['statusLabel'] = inverse_base + ' · ' + band
    for (parent_id, child_id), roles in inverse_roles.items():
        inverse = next(r for r in people[parent_id]['childrenRecorded'] if r.get('id') == child_id)
        inverse.pop('probability_by_role', None)
        if len(roles) > 1:
            # Legacy records can attach one account under two parent roles.
            # Keep their ratings separate instead of overwriting the father.
            inverse['probability_by_role'] = roles
            inverse['probability'] = roles.get('father') or next(iter(roles.values()))
            inverse['statusLabel'] = '; '.join(role.title() + ': ' + value['label'] for role, value in roles.items())
    model.setdefault('meta', {})['relationshipProbabilityScale'] = {'bands': BANDS, 'note': SCALE_NOTE}
    return model
