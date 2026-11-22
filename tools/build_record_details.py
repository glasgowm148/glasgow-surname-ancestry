#!/usr/bin/env python3
"""Produce the record detail files (``www/assets/research/records/<id>.json``) from the indexes.

Each file is the record's row in ``data/records-index.json`` (written by the
catalogue and the canonical-record ingest), with four fields filled in:

* ``country``: the map colour group from the compact index
  (``assets/research/record-index.json``);
* ``document_id``: the source library document listing the record;
* ``person_url``: the person's catalogue page;
* ``research_date``: whether the compact index marks a research date.

Fields a file has that the row does not (map-lead details, reviewed-location
history) are kept. A file whose record is no longer in the index is left as it
is; nothing is deleted. Run with ``--check`` to report what would change.

    .venv/bin/python tools/build_record_details.py [--check]
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RETIRED_URLS = Path("data/site/retired-record-urls.json")
RECORD_ID = re.compile(r"[0-9a-f]{16}")
CURRENT_RECORD_ID = re.compile(r"[a-zA-Z0-9_-]+")
SOURCE_ID = re.compile(r"s-[0-9a-f]{16}")
NON_PUBLIC = ("private", "living", "likely_living", "withheld", "withdrawn")


def documents_by_record(web: Path) -> dict[str, str]:
    owners: dict[str, str] = {}
    for path in sorted((web / "assets/v3/sources").glob("s-*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for record in doc.get("records") or []:
            rid = isinstance(record, dict) and (record.get("id") or record.get("record_id"))
            if rid:
                owners.setdefault(rid, doc["id"])
    return owners


def build(web: Path) -> tuple[dict[str, dict], Counter]:
    """Return (files to write, counts); writes nothing."""
    rows = json.loads((web / "data/records-index.json").read_text(encoding="utf-8"))
    compact = {row["id"]: row for row in json.loads((web / "assets/research/record-index.json").read_text(encoding="utf-8"))}
    owners = documents_by_record(web)
    folder = web / "assets/research/records"
    counts: Counter = Counter()
    changed: dict[str, dict] = {}
    for row in rows:
        rid = row["record_id"]
        path = folder / f"{rid}.json"
        existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        brief = compact.get(rid, {})
        detail = {**{k: v for k, v in (existing or {}).items() if k not in row}, **row,
                  "country": brief.get("country") or (existing or {}).get("country") or "other",
                  "document_id": owners.get(rid) or (existing or {}).get("document_id"),
                  "person_url": f"/people/{row['catalogue_id']}.html" if row.get("catalogue_id")
                  else row.get("person_url") or (existing or {}).get("person_url"),
                  "research_date": bool(brief.get("research_date"))}
        if detail == existing:
            continue
        changed[rid] = detail
        counts["new record files" if existing is None else "record files updated"] += 1
    return changed, counts


def repair_legacy_lookups(web: Path) -> Counter:
    """Retain verified public record lookups after canonical publication."""
    from tools.project_paths import atomic_write_text
    from tools.source_collection_index import _safe_url

    counts: Counter = Counter()
    path = web.parent / RETIRED_URLS
    if not path.is_file():
        return counts
    lookup = json.loads(path.read_text(encoding="utf-8")).get("record_lookups")
    if not lookup:
        return counts

    release = lookup["published_on"]
    if not re.fullmatch(r"[0-9a-f]{64}", lookup["bundle_sha256"]):
        raise ValueError("Legacy record lookups require a verified release bundle")
    bindings = lookup["records"]
    for old_id, (target_id, source_id, url) in bindings.items():
        if (not RECORD_ID.fullmatch(old_id) or not CURRENT_RECORD_ID.fullmatch(target_id)
                or target_id in bindings or not SOURCE_ID.fullmatch(source_id)
                or not url or _safe_url(url) != url):
            raise ValueError(f"Invalid legacy record lookup: {old_id}")

    def read(path):
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def unavailable(row):
        return any(row.get(key) for key in NON_PUBLIC) or row.get("publish_to_record_index") is False

    full = {row["record_id"]: row for row in read(web / "data/records-index.json")}
    compact = {row["id"]: row for row in read(web / "assets/research/record-index.json")}
    folder = web / "assets/research/records"
    for old_id, (target_id, source_id, url) in bindings.items():
        if old_id in full or old_id in compact:
            continue
        alias = folder / f"{old_id}.json"
        existing = read(alias)
        if existing.get("withdrawn"):
            continue
        owns_existing = existing.get("legacy_lookup_release") == release or (
            existing.get("record_id") == old_id and existing.get("source_url") == url
            and existing.get("document_id") == source_id and existing.get("superseded_by") in (None, target_id)
        )
        target = full.get(target_id, {})
        summary = compact.get(target_id, {})
        detail = read(folder / f"{target_id}.json")
        source = read(web / f"assets/v3/sources/{source_id}.json")
        source_records = {row.get("id") or row.get("record_id") for row in source.get("records", [])}
        if (target.get("source_url") != url or target.get("document_id") != source_id
                or summary.get("document_id") != source_id or detail.get("record_id") != target_id
                or detail.get("source_url") != url or detail.get("document_id") != source_id
                or source.get("url") != url or source.get("id") != source_id
                or source_records.isdisjoint((old_id, target_id))
                or (source.get("annotations") or {}).get("publication_withdrawal")
                or any(unavailable(row) for row in (target, summary, detail, source))):
            if owns_existing:
                alias.unlink()
                counts["removed_legacy_record_lookups"] += 1
            continue
        if existing.get("superseded_by") not in (None, target_id) and not existing.get("legacy_lookup_release"):
            continue

        payload = dict(target, record_id=old_id, canonical_record_id=target_id, superseded_by=target_id,
                       superseded_reason="Record lookup ID changed; the original provider entry is unchanged.",
                       legacy_lookup_release=release)
        if payload != existing:
            atomic_write_text(alias, json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
            counts["legacy_record_lookups"] += 1
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--web", type=Path, default=ROOT / "www")
    parser.add_argument("--check", action="store_true", help="report what would change; write nothing")
    args = parser.parse_args(argv)
    changed, counts = build(args.web)
    if not args.check:
        folder = args.web / "assets/research/records"
        folder.mkdir(parents=True, exist_ok=True)
        for rid, detail in changed.items():
            (folder / f"{rid}.json").write_text(json.dumps(detail, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"written": not args.check, **dict(sorted(counts.items()))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
