#!/usr/bin/env python3
"""Keep Atlas person links pointing at pages that exist.

The Atlas models are built from One-Tree exports, which can lag behind
WikiTree merges and the published catalogue.  Two failure modes produced
404 "Open dossier" links:

* merged WikiTree profiles (``redirects`` in data/wikitree/live-profile-overrides.json)
  -> link to the surviving profile's catalogue page and record ``redirectedTo``;
* people with no published catalogue page -> ``catalogueId: null`` so the Atlas
  links to their WikiTree profile instead.
* documentary people -> preserve an existing explicit local dossier, including
  Free-space pages, without inventing a WikiTree person profile.

Idempotent; touches only ``catalogueId``/``redirectedTo`` fields.

    .venv/bin/python tools/repair_atlas_destinations.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
MODELS = (WEB / "assets/research/atlas-model.json", WEB / "onetree/glasgow-one-tree-polished-3/model.json")
STANDALONE = WEB / "assets/research/atlas-standalone.html"


def page_exists(slug: str) -> bool:
    return bool(slug) and ((WEB / "people" / f"{slug}.html").exists() or (WEB / "people" / slug / "index.html").exists())


def documentary_page_exists(person: dict) -> bool:
    """Record-only people can link to an explicit local Free-space dossier."""
    url = person.get("catalogueUrl") or ""
    if not person.get("documentary") or not url.startswith("/") or url.startswith("//"):
        return False
    path = (WEB / urlsplit(url).path.lstrip("/")).resolve()
    if not path.is_relative_to(WEB.resolve()):
        return False
    return (path.suffix == ".html" and path.is_file()) or (path / "index.html").is_file()


def redirects() -> dict[str, str]:
    data = json.loads((ROOT / "data/wikitree/live-profile-overrides.json").read_text(encoding="utf-8"))
    return data.get("redirects") or {}


def repair_people(people: list[dict], merged: dict[str, str]) -> list[str]:
    changes = []
    for person in people:
        if person.get("kind") != "person":
            continue
        slug = person.get("catalogueId") or ""
        if page_exists(slug) or documentary_page_exists(person):
            continue
        target = merged.get(person["id"])
        target_slug = target.lower() if target else ""
        if target and page_exists(target_slug):
            person["catalogueId"], person["redirectedTo"] = target_slug, target
            changes.append(f"{person['id']}: merged into {target}")
        elif person.get("catalogueId") is not None:
            person["catalogueId"] = None
            changes.append(f"{person['id']}: no catalogue page; links to WikiTree")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report broken destinations; exit 1 if any")
    args = parser.parse_args()
    merged = redirects()
    changes = []
    for path in MODELS:
        if not path.exists():
            continue
        model = json.loads(path.read_text(encoding="utf-8"))
        found = [f"{path.relative_to(WEB)} {c}" for c in repair_people(model["people"], merged)]
        changes += found
        if found and not args.check:
            path.write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    # The offline standalone Atlas embeds its own copy of the model.
    if STANDALONE.exists():
        text = STANDALONE.read_text(encoding="utf-8")
        updated = text
        for person_id, target in merged.items():
            if page_exists(target.lower()):
                updated = re.sub(rf'("id":"{re.escape(person_id)}"[^{{}}]*?"catalogueId":)"{re.escape(person_id.lower())}"',
                                 lambda m, t=target.lower(): f'{m[1]}"{t}"', updated)
        if updated != text:
            changes.append("assets/research/atlas-standalone.html merged-profile links")
            if not args.check:
                STANDALONE.write_text(updated, encoding="utf-8")
    for change in changes:
        print(("BROKEN: " if args.check else "fixed: ") + change)
    if args.check and changes:
        return 1
    print("Atlas destinations OK." if not changes else f"Repaired {len(changes)} destination(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
