"""Shared, deterministic research-entry preconditions; no identity inference.

Hold receipts preserve a review of the exact previous row. They require evidence,
but do not establish that the evidence proves a historical conclusion or authenticate
the reviewer. That remains a separate semantic review.
"""
from __future__ import annotations

import hashlib
import json


CREATION_DOCUMENT = "research/queue-review-2026-10-17/catalogue-integration.json"
MATCH_DOCUMENT = "research/research-queue-matches.json"
HELD_STATUSES = {"identity_hold", "hold_source_verification", "on_hold", "hold", "blocked", "parked"}


def canonical_id(value, aliases=None):
    """Follow explicit identity decisions only, rejecting cycles or empty targets."""
    current = str(value or "").strip().casefold()
    mapping = {str(k).strip().casefold(): str(v).strip().casefold()
               for k, v in (aliases or {}).items()}
    seen = set()
    while current in mapping and mapping[current] != current:
        if current in seen or not mapping[current]:
            raise ValueError(f"Invalid or cyclic canonical identity mapping: {value}")
        seen.add(current)
        current = mapping[current]
    return current


def validate_creation_subjects(entries, aliases=None):
    """One source subject may have only one unreconciled creation account."""
    subjects = {}
    accounts = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Creation account must be an object")
        for key in ("subject_id", "catalogue_id"):
            if key in entry and (not isinstance(entry[key], str) or not entry[key].strip()):
                raise ValueError(f"Creation account needs a non-empty string {key}")
        subject = canonical_id(entry.get("subject_id"), aliases)
        account = canonical_id(entry.get("catalogue_id") or entry.get("subject_id"), aliases)
        original_account = canonical_id(entry.get("catalogue_id") or entry.get("subject_id"))
        if original_account in accounts:
            raise ValueError(f"Repeated canonical catalogue ID: {original_account}")
        accounts.add(original_account)
        if not subject:
            raise ValueError("Creation account needs a non-empty subject_id")
        if subject in subjects and subjects[subject] != account:
            raise ValueError(f"Duplicate canonical subject_id {subject}: {subjects[subject]}, {account}; "
                             "reuse the existing account or record an explicit identity merge")
        subjects[subject] = account


def row_sha256(row):
    """Hash the complete held row, not a model-generated paraphrase of its hold."""
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def hold_status(row, *, status_field="creation_status"):
    # Match the consuming adapter: creation accounts default to ready, while
    # questions and identity reviews use status and must not be shadowed by an
    # unrelated creation_status field.
    default = "creation_ready" if status_field == "creation_status" else ""
    return str(row.get(status_field, default)).strip().casefold().replace(" ", "_").replace("-", "_")


def hold_condition(row, *, status_field="creation_status"):
    return next((row[key] for key in ("hold_condition", "resume_condition", "assessment", "question")
                 if isinstance(row.get(key), str) and row[key].strip()), hold_status(row, status_field=status_field))


def hold_receipts(proposed):
    """Every release receipt on a row; a merged target may supersede several holds."""
    receipts = []
    if isinstance(proposed.get("hold_release"), dict):
        receipts.append(proposed["hold_release"])
    if isinstance(proposed.get("hold_releases"), list):
        receipts.extend(item for item in proposed["hold_releases"] if isinstance(item, dict))
    return receipts


def _validate_hold_receipt(receipt, previous, evidence_revision, status_field="creation_status"):
    if receipt.get("previous_row_sha256") != row_sha256(previous):
        raise ValueError("Hold release does not match the exact previous held row")
    if receipt.get("condition") != hold_condition(previous, status_field=status_field):
        raise ValueError("Hold release must retain the previous verification condition")
    if receipt.get("decision") not in {"satisfied", "superseded"}:
        raise ValueError("Hold release decision must be satisfied or superseded")
    for key in ("reason", "reviewed_by"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            raise ValueError(f"Hold release needs {key}")
    evidence = receipt.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Hold release needs explicit record evidence")
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("Hold release evidence must be an object")
        for key in ("record_id", "locator"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Hold release evidence needs {key}")
        revision = item.get("revision")
        if type(revision) is not int or revision < 1:
            raise ValueError("Hold release evidence needs a positive record revision")
        if evidence_revision is not None and evidence_revision(item["record_id"]) != revision:
            raise ValueError(f"Hold release evidence is missing or stale: {item['record_id']}")


def validate_hold_release(previous, proposed, *, evidence_revision=None, status_field="creation_status"):
    """Require an evidence-backed receipt before a held row becomes actionable.

    A merged target may carry ``hold_releases`` with one exact receipt for each
    held source row, in addition to the legacy single ``hold_release``.
    """
    if (hold_status(previous, status_field=status_field) not in HELD_STATUSES
            or hold_status(proposed, status_field=status_field) in HELD_STATUSES):
        return
    receipts = hold_receipts(proposed)
    if not receipts:
        raise ValueError("Hold release requires a hold_release evidence receipt; status text alone is insufficient")
    sha = row_sha256(previous)
    matching = [receipt for receipt in receipts if receipt.get("previous_row_sha256") == sha]
    if not matching:
        raise ValueError("Hold release does not match the exact previous held row")
    if len(matching) != 1:
        raise ValueError("Duplicate hold release receipt for the same held row")
    _validate_hold_receipt(matching[0], previous, evidence_revision, status_field=status_field)


def validate_held_questions(previous, proposed, *, evidence_revision=None):
    """Match held questions by explicit ID/text or an exact receipt, never index."""
    for old_index, old in enumerate(previous):
        if not isinstance(old, dict) or hold_status(old, status_field="status") not in HELD_STATUSES:
            continue
        matches = [(index, row) for index, row in enumerate(proposed) if isinstance(row, dict) and (
            (old.get("id") and row.get("id") == old["id"])
            or (not old.get("id") and row.get("question") == old.get("question"))
            or (isinstance(row.get("hold_release"), dict)
                and row["hold_release"].get("previous_row_sha256") == row_sha256(old)))]
        if len(matches) != 1:
            raise ValueError("Held research question cannot be silently removed, renamed or duplicated")
        index, row = matches[0]
        # Native legacy questions still use positional IDs. Until that adapter
        # supports stable question IDs, a reorder must not update another core
        # question while the document appears to preserve the original hold.
        if index != old_index:
            raise ValueError("Keep held research questions in their existing positions during review")
        validate_hold_release(old, row, evidence_revision=evidence_revision, status_field="status")


def validate_creation_document(document, previous=None, *, aliases=None, evidence_revision=None):
    """Validate the complete document, including rows outside a targeted publish."""
    entries = document.get("new_people", [])
    validate_creation_subjects(entries, aliases)
    prior = {}
    held = {}
    for row in (previous or {}).get("new_people", []):
        if hold_status(row) in HELD_STATUSES:
            held[row_sha256(row)] = row
            for key in ("subject_id", "catalogue_id"):
                if row.get(key):
                    prior.setdefault(canonical_id(row[key], aliases), []).append(row)
    matched = set()
    for row in entries:
        matches = {}
        for key in ("subject_id", "catalogue_id"):
            for old in prior.get(canonical_id(row.get(key), aliases), []):
                matches[row_sha256(old)] = old
        for old in matches.values():
            matched.add(row_sha256(old))
            validate_hold_release(old, row, evidence_revision=evidence_revision)
    if held.keys() - matched:
        raise ValueError("Held creation account cannot be silently removed or renamed; retain its identity and hold review")
