#!/usr/bin/env python3
"""Keep the research-person models (``www/assets/research/people/<id>.json``) current.

The atlas person panel reads one model per person. They were last built as a
whole on 8 September 2026 by a model builder that is no longer in the
repository, so this produces them field by field from their current inputs
(stage 1):

* ``name``, ``identity``, ``open_questions`` and the evidence and claim counts
  from the person's dossier (``www/people/<id>.json``);
* ``relationships`` from the dossier, each relative marked ``external`` when
  they have no public dossier;
* ``record_ids`` from the records index;
* ``evidence_documents`` and ``source_documents`` from the source library;
* ``branches`` from the person's family and place groups in ``branches.json``.

Every other field (vitals, the review, events, mentions, DNA) is kept as it is
until a later stage produces it. Models that redirect, and models whose person
has no dossier, are left alone; nothing is deleted. Run with ``--check`` to
report what would change.

    .venv/bin/python tools/build_person_models.py [--check]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("parents", "spouses", "children", "siblings")
BRANCH_KINDS = ("family", "place")


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def inputs(web: Path) -> dict:
    documents: dict[tuple[str, str], str] = {}
    for path in sorted((web / "assets/v3/sources").glob("s-*.json")):
        doc = _load(path) or {}
        for cited in doc.get("citations") or []:
            documents.setdefault((cited.get("person"), cited.get("evidence_id")), doc.get("id"))
    records: dict[str, list[str]] = defaultdict(list)
    for row in _load(web / "data/records-index.json") or []:
        if row.get("catalogue_id"):
            records[row["catalogue_id"]].append(row["record_id"])
    branches: dict[str, list[dict]] = defaultdict(list)
    for branch in _load(web / "assets/research/branches.json") or []:
        if branch.get("kind") in BRANCH_KINDS:
            entry = {key: branch.get(key) for key in ("id", "label", "url", "kind")}
            for member in branch.get("members") or []:
                branches[member].append(entry)
    public = {path.stem for path in (web / "people").glob("*.json") if not path.name.endswith(".network.json")}
    return {"documents": documents, "records": records, "branches": branches, "public": public}


def stage_one(slug: str, dossier: dict, data: dict) -> dict:
    evidence = [item for item in dossier.get("evidence") or [] if isinstance(item, dict)]
    linked = {item["id"]: data["documents"][(slug, item["id"])] for item in evidence
              if (slug, item.get("id")) in data["documents"]}
    relationships = {}
    for group in GROUPS:
        rows = []
        for relation in (dossier.get("relationships") or {}).get(group) or []:
            relative = str(relation.get("id") or "").lower()
            rows.append({**relation, "external": relative not in data["public"]})
        relationships[group] = rows
    return {"name": dossier.get("name"), "identity": dossier.get("identity"),
            "open_questions": dossier.get("open_questions") or [],
            "evidence_count": len(evidence), "claims_count": len(dossier.get("claims") or []),
            "relationships": relationships, "record_ids": sorted(data["records"].get(slug, [])),
            "evidence_documents": linked, "source_documents": sorted(set(linked.values())),
            "branches": data["branches"].get(slug, [])}


def build(web: Path) -> tuple[dict[str, dict], Counter]:
    """Return (models to write, counts); writes nothing."""
    data = inputs(web)
    counts: Counter = Counter()
    changed: dict[str, dict] = {}
    for path in sorted((web / "assets/research/people").glob("*.json")):
        model = _load(path)
        if not isinstance(model, dict) or model.get("redirect_to"):
            continue
        dossier = _load(web / "people" / path.name)
        if not isinstance(dossier, dict):
            counts["models without a dossier, kept"] += 1
            continue
        updated = {**model, **stage_one(path.stem, dossier, data)}
        if updated != model:
            changed[path.stem] = updated
            counts["models updated"] += 1
    missing = data["public"] - {path.stem for path in (web / "assets/research/people").glob("*.json")}
    counts["dossiers without a model (not yet produced)"] = len(missing)
    return changed, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--web", type=Path, default=ROOT / "www")
    parser.add_argument("--check", action="store_true", help="report what would change; write nothing")
    args = parser.parse_args(argv)
    changed, counts = build(args.web)
    if not args.check:
        for slug, model in changed.items():
            (args.web / "assets/research/people" / f"{slug}.json").write_text(
                json.dumps(model, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": not args.check, **dict(sorted(counts.items()))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
