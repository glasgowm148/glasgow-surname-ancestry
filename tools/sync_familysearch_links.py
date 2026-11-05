#!/usr/bin/env python3
"""Copy the reviewed catalogue-to-FamilySearch person matches into the repository.

The FamilySearch parity work keeps its matches in ``fs-parity/map.tsv``, outside
this repository, one row per review. A person may have several rows, because a
correction is appended rather than edited in place, so the last row for a
catalogue id wins. Only high and medium confidence matches are kept. Person
pages read the result through ``tools/profile_tree_links.py`` to show a
"View on FamilySearch" button.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "fs-parity" / "map.tsv"
TARGET = ROOT / "data" / "familysearch" / "person-links.json"
FS_ID = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{2,4}$")


def read_matches(source: Path) -> dict:
    people = {}
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            key = (row.get("catalogue_id") or "").strip().lower()
            fs_id = (row.get("fs_id") or "").strip().upper()
            confidence = (row.get("confidence") or "").strip().lower()
            if not key or not FS_ID.match(fs_id):
                continue
            if confidence not in {"high", "medium"}:
                people.pop(key, None)  # a later doubtful row withdraws an earlier match
                continue
            people[key] = {"id": fs_id, "confidence": confidence}
    return dict(sorted(people.items()))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    args = parser.parse_args(argv)
    people = read_matches(args.source)
    args.target.parent.mkdir(parents=True, exist_ok=True)
    value = json.dumps({"source": "fs-parity/map.tsv", "people": people}, indent=1, ensure_ascii=False) + "\n"
    if not args.target.exists() or args.target.read_text(encoding="utf-8") != value:
        args.target.write_text(value, encoding="utf-8")
    print(json.dumps({"people": len(people)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
