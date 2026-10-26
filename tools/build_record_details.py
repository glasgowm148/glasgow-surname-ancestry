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
import sys

ROOT = Path(__file__).resolve().parents[1]


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
