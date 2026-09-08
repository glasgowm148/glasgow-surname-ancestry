#!/usr/bin/env python3
"""Import a profile-link request downloaded from an unlinked catalogue page."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys

from project_paths import (
    ROOT, WEB_DIR, WIKITREE_CATALOGUE_PROFILE_LINKS, atomic_write_text,
)

sys.path.insert(0, str(ROOT / "src"))
from wikitree_family_export import resolve_wikitree_redirect  # noqa: E402


WIKITREE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path, help="Downloaded catalogue-profile-link-*.json")
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args()


def main() -> int:
    options = arguments()
    request = json.loads(options.request.read_text(encoding="utf-8"))
    catalogue_id = str(request.get("catalogue_id") or "")
    requested_id = str(request.get("wikitree_id") or "")
    if not catalogue_id.startswith("record-") or not WIKITREE_ID.fullmatch(requested_id):
        raise SystemExit("Request must contain a record-* catalogue_id and a valid WikiTree ID.")

    people = json.loads((WEB_DIR / "data" / "people.json").read_text(encoding="utf-8"))["people"]
    person = next((item for item in people if item["catalogue_id"] == catalogue_id), None)
    if not person:
        raise SystemExit(f"Catalogue entry not found: {catalogue_id}")
    if person.get("profile_ids"):
        raise SystemExit(f"Catalogue entry is already linked to: {' | '.join(person['profile_ids'])}")

    canonical_id, _ = resolve_wikitree_redirect(requested_id)
    payload = json.loads(WIKITREE_CATALOGUE_PROFILE_LINKS.read_text(encoding="utf-8"))
    payload.setdefault("entries", {})[catalogue_id] = {
        "profile_id": canonical_id,
        "catalogue_name": person["name"],
        "matched_at": date.today().isoformat(),
        "evidence_note": str(request.get("evidence_note") or "User-submitted catalogue match; identity reviewed before import."),
    }
    atomic_write_text(
        WIKITREE_CATALOGUE_PROFILE_LINKS,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
    print(f"Recorded {catalogue_id} -> {canonical_id}")
    if options.rebuild:
        subprocess.run([str(ROOT / ".venv/bin/python"), "tools/build_family_map.py"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
