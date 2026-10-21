"""Individual evidence-based probability estimates; grades remain separate."""

from __future__ import annotations

from typing import Any
from functools import lru_cache
from pathlib import Path
import json
import re

SCALE_NOTE = (
    "Individual subjective estimates from the maintained evidence, not measured "
    "frequencies. Categories are guides; unreviewed tree marks have no percentage."
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


@lru_cache(maxsize=1)
def reviewed_estimates():
    path = Path(__file__).resolve().parents[1] / 'research/relationship_probability_estimates.json'
    if not path.exists():
        return {}
    rows = json.loads(path.read_text())['estimates']
    result = {}
    for row in rows:
        key = (row['subject_id'].casefold(), row['relative_id'].casefold(), row['relationship'])
        if key in result or not 0 < row['percent'] < 100 or not row.get('basis'):
            raise ValueError(f'Invalid or duplicate relationship estimate: {key}')
        result[key] = row
    return result


def probability_for_relationship(row: dict[str, Any], subject_id=None, relative_id=None, role=None) -> dict[str, Any]:
    """Keep the grade; attach a reviewed point estimate for this exact pair/role."""
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
    result = {"band": band, **BANDS[band], "value": None,
              "method": "not_individually_assessed", "origin": origin}
    scope = row.get("record_scope", row.get("recordScope"))
    if scope:
        result["scope"] = scope
    child = subject_id or row.get('subject_id')
    parent = relative_id or row.get('relative_id') or row.get('id')
    role = role or row.get('relationship') or row.get('role')
    estimate = reviewed_estimates().get((str(child).casefold(), str(parent).casefold(), role))
    # A stale estimate must not override a changed assessment or excluded link.
    if estimate and band != 'unrated' and confidence_band(estimate['assessment_status']) == band:
        result.update(value=estimate['percent'] / 100, method='individual_evidence_assessment', origin='research',
                      label=f"{BANDS[band]['label'].split(' (')[0]} · {estimate['percent']}%",
                      basis=estimate['basis'], reviewed=estimate['reviewed'],
                      source_ids=estimate.get('source_ids', []))
        if estimate.get('assertion_id'):
            result['assertion_id'] = estimate['assertion_id']
        if estimate.get('scope'):
            result['scope'] = estimate['scope']
    return result


def percentage_text(rating):
    return f"{round(rating['value'] * 100)}%" if rating.get('value') is not None else 'Not individually rated'


def _rated_label(base, rating):
    """A reviewed display may already carry its individual percentage."""
    base = re.sub(r'(?:\s*·\s*(?:\d+%|Not individually rated))+$', '', base)
    return base + ' · ' + percentage_text(rating)


def annotate_model(model: dict[str, Any]) -> dict[str, Any]:
    """Assign the same bands to both directions of public parent links."""
    try:
        import evidence_labels
    except ModuleNotFoundError:
        from tools import evidence_labels
    people = {p['id']: p for p in model.get('people', [])}
    inverse_roles = {}
    for person in people.values():
        for partner in person.get('partners', []):
            rating = probability_for_relationship(partner, person['id'], role='spouse')
            if rating.get('value') is not None:
                partner['probability'] = rating
                base = partner.get('assessmentLabel') or partner.get('statusLabel') or evidence_labels.label(partner.get('status'))
                partner['assessmentLabel'] = base
                partner['statusLabel'] = _rated_label(base, rating)
    for child in people.values():
        for row in child.get('parents', []):
            rating = probability_for_relationship(row, child['id'])
            row['probability'] = rating
            base = row.get('assessmentLabel') or row.get('statusLabel') or evidence_labels.label(row.get('status'))
            if not row.get('assessmentLabel') and not row.get('statusLabel') and rating['origin'] == 'wikitree':
                base = evidence_labels.label(row.get('tree_status') or row.get('status'))
            row['assessmentLabel'] = base
            row['statusLabel'] = _rated_label(base, rating)
            parent = people.get(row.get('id'), {})
            for inverse in parent.get('childrenRecorded', []):
                if inverse.get('id') == child['id']:
                    roles = inverse_roles.setdefault((parent['id'], child['id']), {})
                    roles[row.get('role') or 'parent'] = dict(rating)
                    inverse['probability'] = dict(rating)
                    inverse_base = inverse.get('assessmentLabel') or inverse.get('statusLabel') or base.replace('father', 'child').replace('mother', 'child')
                    inverse['assessmentLabel'] = inverse_base
                    inverse['statusLabel'] = _rated_label(inverse_base, rating)
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
