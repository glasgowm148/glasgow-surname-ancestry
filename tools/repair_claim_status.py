#!/usr/bin/env python3
"""Repair the one qualified Daniel Glasgow identity claim in generated JSON.

This is intentionally a narrow, idempotent migration.  It changes structured
machine copies only; source research prose and historical/superseded claims
are retained as they are.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from catalogue_machine_data import _canonical_status
except ModuleNotFoundError:  # Imported as tools.repair_claim_status by tests.
    from tools.catalogue_machine_data import _canonical_status


ROOT = Path(__file__).resolve().parents[1]
TARGET_IDS = frozenset(("Glasgow-2413", "Glasgow-2416"))
TARGET_CLAIM_ID = "C-db7b2a0378e5"


def _is_current_target(claim: dict) -> bool:
    """Match the known legacy identity assertion, never a retired assertion."""
    if claim.get("lifecycle") == "historical" or claim.get("status") == "superseded":
        return False
    if claim.get("id") == TARGET_CLAIM_ID:
        return True
    return (
        claim.get("type") in {"relationship", "relationship_hypothesis"}
        and frozenset(claim.get("subject_ids") or ()) == TARGET_IDS
        and "strong candidate" in str(claim.get("status_label") or "").casefold()
        and ("not proved" in str(claim.get("status_label") or "").casefold()
             or "unproved" in str(claim.get("status_label") or "").casefold())
    )


def _repair_section(value: object) -> tuple[int, int]:
    """Repair claim/evidence lists in a dossier, import snapshot, or mirror."""
    if not isinstance(value, dict):
        return 0, 0
    claim_changes = evidence_changes = 0
    target_evidence_ids: set[str] = set()
    claims = value.get("claims")
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict) or not _is_current_target(claim):
                continue
            expected = _canonical_status(
                str(claim.get("status_label") or ""),
                claim_type=str(claim.get("type") or "relationship"),
                claim_context=str(claim.get("claim") or ""),
            )
            if claim.get("status") != expected:
                claim["status"] = expected
                claim_changes += 1
            target_evidence_ids.update(str(item) for item in claim.get("evidence_ids") or ())
    evidence = value.get("evidence")
    if isinstance(evidence, list) and target_evidence_ids:
        for item in evidence:
            if not isinstance(item, dict):
                continue
            if str(item.get("id")) not in target_evidence_ids:
                continue
            # The records support a candidate comparison; they do not directly
            # identify these two Daniel Glasgows as the same person.
            if item.get("evidence_status") == "direct":
                item["evidence_status"] = "circumstantial"
                evidence_changes += 1
    for child in value.values():
        if isinstance(child, dict):
            changed_claims, changed_evidence = _repair_section(child)
            claim_changes += changed_claims
            evidence_changes += changed_evidence
        elif isinstance(child, list):
            for item in child:
                changed_claims, changed_evidence = _repair_section(item)
                claim_changes += changed_claims
                evidence_changes += changed_evidence
    return claim_changes, evidence_changes


def _repair_network(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    changes = 0
    relationships = value.get("relationships")
    if isinstance(relationships, list):
        for relation in relationships:
            if not isinstance(relation, dict) or relation.get("claim_id") != TARGET_CLAIM_ID:
                continue
            if relation.get("lifecycle") == "historical" or relation.get("status") == "superseded":
                continue
            expected = _canonical_status(str(relation.get("status_label") or ""), claim_type="relationship")
            if relation.get("status") != expected:
                relation["status"] = expected
                changes += 1
    return changes


def repair(root: Path) -> dict[str, int]:
    """Repair generated JSON below *root* and return counts; safe to rerun."""
    report = {"files": 0, "claims": 0, "evidence": 0, "networks": 0}
    for path in sorted(root.rglob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            if TARGET_CLAIM_ID not in raw and not all(identifier in raw for identifier in TARGET_IDS):
                continue
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            continue
        claim_changes, evidence_changes = _repair_section(payload)
        network_changes = _repair_network(payload)
        if not (claim_changes or evidence_changes or network_changes):
            continue
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        report["files"] += 1
        report["claims"] += claim_changes
        report["evidence"] += evidence_changes
        report["networks"] += network_changes
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT / "www", help="Generated-data root (default: www)")
    args = parser.parse_args()
    print(json.dumps(repair(args.root)))


if __name__ == "__main__":
    main()
