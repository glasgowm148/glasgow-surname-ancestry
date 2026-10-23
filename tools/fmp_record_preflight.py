#!/usr/bin/env python3
"""Offline exact-ID Findmypast preflight; never opens a browser or writes state."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.ingest_canonical_records import provider_key
from tools.project_paths import ROOT

DETAIL_GLOB = "record-details*.json"
SCOPE_GLOB = "birth-scope-records*.json"

def _read(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _provider_id(row: dict) -> str:
    value = row.get("record_id") or row.get("provider_record_id")
    if value:
        value = str(value)
        key = provider_key({"url": value}) if value.startswith(("https://", "http://")) else _findmypast_key(value)
        return key[1] if key[0] == "findmypast" else value
    # Search result links may carry the ID even when the row lacks record_id.
    for link in row.get("links", []) or []:
        key = provider_key({"url": link.get("url", "")})
        if key[0] == "findmypast":
            return key[1]
    return ""


def _load_selected(args) -> list[dict]:
    if args.record_id:
        return [{"record_id": value} for value in args.record_id]
    value = _read(Path(args.rows_file))
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict) and isinstance(value.get("rows"), list):
        rows = value["rows"]
    elif isinstance(value, dict) and isinstance(value.get("search_page"), dict):
        rows = value["search_page"].get("rows", [])
    elif isinstance(value, dict) and isinstance(value.get("pages"), list):
        rows = [row for page in value["pages"] for row in page.get("rows", [])]
    else:
        raise ValueError("rows-file must be a list, an object with rows, search_page.rows, or pages[].rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("selected rows must be JSON objects")
    return rows


def _findmypast_key(provider_id: str):
    # IDs copied from a URL may still be percent-escaped. Canonicalize through
    # the same URL parser used for provider records and source URLs.
    decoded = unquote(provider_id)
    return provider_key({"url": "https://www.findmypast.co.uk/transcript?id=" + quote(decoded, safe="")})


def _row_key(row: dict):
    explicit = row.get("provider_record_id")
    if explicit:
        return _findmypast_key(str(explicit))
    return provider_key(row)


def _receipt_candidates(audit_dir: Path) -> dict[str, list[dict]]:
    candidates: dict[str, list[dict]] = {}
    paths = sorted(audit_dir.glob(DETAIL_GLOB)) + sorted(audit_dir.glob(SCOPE_GLOB))
    for path in paths:
        data = _read(path)
        records = data.get("records", {}) if isinstance(data, dict) else {}
        if not isinstance(records, dict):
            continue
        for record_id, receipt in records.items():
            if not isinstance(receipt, dict):
                continue
            key = _findmypast_key(str(record_id))
            if key[0] != "findmypast":
                continue
            candidates.setdefault(key[1], []).append({
                "path": str(path),
                "json_pointer": "#/records/" + _pointer_token(str(record_id)),
                "receipt": receipt,
            })
    return candidates


def _scope_holds(audit_dir: Path) -> dict[str, list[dict]]:
    holds: dict[str, list[dict]] = {}
    for path in sorted(audit_dir.glob(SCOPE_GLOB)):
        data = _read(path)
        if not isinstance(data, dict):
            continue
        records = data.get("records", {})
        if isinstance(records, dict):
            for record_id, row in records.items():
                if not isinstance(row, dict):
                    continue
                status = str(row.get("matching_status") or "").casefold()
                if "hold" in status:
                    canonical_id = _findmypast_key(str(record_id))[1]
                    holds.setdefault(canonical_id, []).append({
                        "path": str(path), "json_pointer": "#/records/" + _pointer_token(str(record_id)),
                        "matching_status": row.get("matching_status"),
                        "reason": row.get("matching_reason") or row.get("assessment") or "Explicit matching HOLD in scope record",
                    })
        scope = data.get("scope", {})
        if isinstance(scope, dict):
            for field in ("unassigned_record_ids", "held_record_ids", "hold_record_ids"):
                for record_id in scope.get(field, []) or []:
                    holds.setdefault(_findmypast_key(str(record_id))[1], []).append({
                        "path": str(path), "json_pointer": f"#/scope/{field}",
                        "matching_status": "scope_hold", "reason": f"Listed in scope.{field}",
                    })
        assignments = ((data.get("matching_review") or {}).get("record_assignments") or {})
        if isinstance(assignments, dict):
            for record_id, assignment in assignments.items():
                if not isinstance(assignment, dict):
                    continue
                status = str(assignment.get("status") or "")
                assessment = str(assignment.get("assessment") or "")
                if "hold" in status.casefold() or re.search(r"\bHOLD\b", assessment, re.I):
                    holds.setdefault(_findmypast_key(str(record_id))[1], []).append({
                        "path": str(path),
                        "json_pointer": "#/matching_review/record_assignments/" + _pointer_token(str(record_id)),
                        "matching_status": status or "scope_hold",
                        "reason": assessment or f"Assignment status: {status}",
                    })
    return holds


def _successful(candidate: dict) -> bool:
    receipt = candidate["receipt"]
    return (receipt.get("access_status") == "accessible"
            and isinstance(receipt.get("transcript_fields"), dict)
            and bool(receipt["transcript_fields"]))


def _normalized_field_label(label) -> str:
    return re.sub(r"\s+", " ", str(label)).strip().casefold()


def _normalized_field_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip()
        if value.casefold() in {"", "-", "–", "—", "n/a"}:
            return None
        return value.casefold()
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _conflicting_fields(successes: list[dict]) -> list[dict]:
    observations: dict[str, list[dict]] = {}
    for candidate in successes:
        for label, value in (candidate["receipt"].get("transcript_fields") or {}).items():
            normalized = _normalized_field_value(value)
            if normalized is None:
                continue
            key = _normalized_field_label(label)
            observations.setdefault(key, []).append({
                "label": str(label), "value": value, "normalized": normalized,
                "path": candidate["path"], "json_pointer": candidate["json_pointer"],
            })
    conflicts = []
    for key, items in sorted(observations.items()):
        if len({item["normalized"] for item in items}) > 1:
            conflicts.append({
                "field": key,
                "observations": [{k: item[k] for k in ("label", "value", "path", "json_pointer")} for item in items],
            })
    return conflicts


def _candidate_sort(candidate: dict):
    receipt = candidate["receipt"]
    captured = str(receipt.get("captured_at") or "")
    try:
        timestamp = datetime.fromisoformat(captured.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.timestamp()
    except ValueError:
        timestamp = 0
    fields = receipt.get("transcript_fields") or {}
    richness = sum(_normalized_field_value(value) is not None for value in fields.values())
    return (_successful(candidate), timestamp, richness, candidate["path"], candidate["json_pointer"])


def _provider_index(rows: list[dict]) -> dict[str, list[dict]]:
    """Build a one-pass provider-ID index while retaining duplicate rows."""
    result: dict[str, list[dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = _row_key(row)
        if key[0] == "findmypast":
            result.setdefault(key[1], []).append(row)
    return result


def preflight(root: Path, rows: list[dict], reinspect_reason: str = "") -> dict:
    audit_dir = root / "research/findmypast-glasgow-audit"
    candidates = _receipt_candidates(audit_dir)
    holds = _scope_holds(audit_dir)
    canonical = _read(root / "research/canonical_records.json")
    public = _read(root / "www/data/records-index.json")
    if not isinstance(canonical, list) or not isinstance(public, list):
        raise ValueError("canonical and public record indexes must be JSON arrays")
    canonical_by_provider = _provider_index(canonical)
    public_by_provider = _provider_index(public)

    output = []
    seen = set()
    for row in rows:
        provider_id = _provider_id(row)
        if not provider_id:
            raise ValueError("selected row lacks record_id/provider_record_id or a Findmypast transcript link")
        key = _findmypast_key(provider_id)
        if key[0] != "findmypast":
            raise ValueError(f"not a Findmypast provider ID: {provider_id}")
        if provider_id in seen:
            continue
        seen.add(provider_id)
        matched_receipts = candidates.get(provider_id, [])
        successes = [item for item in matched_receipts if _successful(item)]
        failures = [item for item in matched_receipts if not _successful(item)]
        conflicts = _conflicting_fields(successes)
        receipt = None
        if conflicts:
            disposition = "blocked_receipt"
            receipt_state = "conflicting_successful_receipts"
            reason = "Accessible receipts disagree on overlapping substantive transcript fields; review the listed captures."
        elif successes:
            receipt = max(successes, key=_candidate_sort)
            disposition = "reusable_receipt"
            receipt_state = "accessible"
            reason = "Compatible cached accessible receipt has nonempty transcript_fields."
        elif matched_receipts:
            receipt = max(matched_receipts, key=_candidate_sort)
            disposition = "blocked_receipt"
            receipt_state = receipt["receipt"].get("access_status") or "incomplete"
            reason = ("Cached receipt has no nonempty transcript_fields; do not automatically retry."
                      if receipt_state == "accessible" else "Cached access failure; do not automatically retry.")
        else:
            disposition = "detail_needed"
            receipt_state = "missing"
            reason = "No saved full-transcript receipt for this exact provider ID."

        canonical_matches = canonical_by_provider.get(provider_id, [])
        public_matches = public_by_provider.get(provider_id, [])
        source_ids = sorted({str(item.get("document_id")) for item in public_matches if item.get("document_id")})
        indexed_record_ids = sorted({str(item.get("record_id")) for item in canonical_matches + public_matches if item.get("record_id")})
        hold_rows = holds.get(provider_id, [])
        matching_hold = bool(hold_rows)

        if disposition != "blocked_receipt" and not successes and (canonical_matches or public_matches):
            disposition = "review_existing_index"
            reason = "An exact provider record is already represented in canonical/public indexes; review that record before recapture."
        elif disposition != "blocked_receipt" and not successes:
            disposition = "detail_needed"
            if matching_hold:
                reason = "Full transcript is missing; acquiring it may resolve the recorded identity HOLD. No identity assignment is made."

        output.append({
            "provider_id": provider_id,
            "disposition": disposition,
            "receipt_status": receipt_state,
            "cached_receipt": ({"path": receipt["path"], "json_pointer": receipt["json_pointer"],
                                 "access_status": receipt["receipt"].get("access_status"),
                                 "transcript_fields_present": bool(receipt["receipt"].get("transcript_fields")),
                                 "captured_at": receipt["receipt"].get("captured_at")}
                                if receipt else None),
            "receipt_pointers": [{"path": item["path"], "json_pointer": item["json_pointer"],
                                  "access_status": item["receipt"].get("access_status"),
                                  "captured_at": item["receipt"].get("captured_at")}
                                 for item in sorted(matched_receipts, key=_candidate_sort)],
            "conflicting_fields": conflicts,
            "matching_hold": matching_hold,
            "matching_hold_evidence": hold_rows,
            "canonical_record_ids": sorted({str(item.get("record_id")) for item in canonical_matches if item.get("record_id")}),
            "public_record_ids": sorted({str(item.get("record_id")) for item in public_matches if item.get("record_id")}),
            "already_indexed": bool(indexed_record_ids),
            "source_ids": source_ids,
            "reason": reason,
            "reinspect": ({"requested": bool(reinspect_reason and receipt and _successful(receipt)),
                           "reason": reinspect_reason if reinspect_reason and receipt and _successful(receipt) else None}
                          if reinspect_reason else None),
        })
    return {"schema_version": 1, "read_only": True, "records": output}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--record-id", action="append", help="Exact provider record ID; repeatable")
    selection.add_argument("--rows-file", help="JSON list or search-page rows object; IDs only are read from it")
    parser.add_argument("--reinspect-reason", help="Specific evidence gap justifying reinspection of cached accessible details")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reinspect_reason is not None and not args.reinspect_reason.strip():
        parser.error("--reinspect-reason must state a specific gap")
    try:
        result = preflight(args.root, _load_selected(args), (args.reinspect_reason or "").strip())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
