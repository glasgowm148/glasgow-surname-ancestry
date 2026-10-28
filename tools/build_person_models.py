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

Stage 2 adds the person's event lists (``events``, ``mentions``,
``research_events``, ``unresolved_events``, ``family_events``) from the event
index, whose vital rows ``build_event_index.py`` keeps current.

Stage 3 produces the ``vitals`` from the dossier. A vital the model enriches
(imported vitals: ``basis``, ``country`` and ``display_date``) keeps that
form, with the country taken from the person's event-index row so the panel
and the map agree; any other vital (reviewed vitals, research-case models)
is the dossier's own. It also writes a model for each public dossier that has
none, so the atlas panel can open every catalogue person.

Kept as they are: ``original_vitals`` (the WikiTree vitals before review, a
snapshot no current input reproduces), ``review`` (its summaries exist only
in the models), ``dna`` (restored from the approved atlas models by
``repair_public_dna``) and ``override``. Models that redirect, and models
whose person has no dossier, are left alone; nothing is deleted. A dossier the
privacy policy withholds gets no new model. Run with ``--check`` to report
what would change.

    .venv/bin/python tools/build_person_models.py [--check]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT)]
from build_event_index import country, display  # noqa: E402

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
    events: dict[str, list[dict]] = defaultdict(list)
    for row in _load(web / "assets/research/event-index.json") or []:
        if isinstance(row, dict) and row.get("p"):
            events[row["p"]].append(row)
    atlas = {str(person.get("id")) for person in (_load(web / "assets/research/atlas-import.json") or {}).get("people") or []
             if isinstance(person, dict) and person.get("kind") == "person"}
    return {"documents": documents, "records": records, "branches": branches, "public": public, "events": events,
            "atlas": atlas}


EVENT_LISTS = {"events": "personal", "mentions": "mention", "research_events": "research",
               "unresolved_events": "unresolved", "family_events": "family"}


def stage_two(slug: str, data: dict) -> dict:
    """The person's rows of the event index, by kind (built by build_event_index.py)."""
    rows = data["events"].get(slug, [])
    return {field: [row for row in rows if row.get("kind") == kind] for field, kind in EVENT_LISTS.items()}


ENRICHED = ("basis", "country", "display_date")


def stage_three(slug: str, dossier: dict, model: dict, data: dict) -> dict:
    """The vitals, from the dossier, in the form the model already uses."""
    vitals = dict(model.get("vitals") or {})
    rows = {row.get("id"): row for row in data["events"].get(slug, []) if row.get("kind") == "personal"}
    for kind, vital in (dossier.get("vitals") or {}).items():
        if not isinstance(vital, dict):
            continue
        previous = vitals.get(kind)
        if not (isinstance(previous, dict) and all(key in previous for key in ENRICHED)):
            vitals[kind] = vital
            continue
        row = rows.get(kind) or {}
        place = vital.get("place")
        shown = display(vital.get("date"))
        if vital.get("date") == previous.get("date"):
            shown = previous["display_date"]   # the display form is the earlier builder's; keep it
        elif shown is None:
            shown = "Not recorded"
        vitals[kind] = {**vital, "display_date": shown,
                        "country": row.get("country") if row.get("place") == place and row.get("country") else country(place),
                        "basis": previous.get("basis") or "imported_vital"}
    return {"vitals": vitals} if vitals or "vitals" in model else {}


def new_model(slug: str, dossier: dict, data: dict) -> dict:
    """A model for a public dossier that has none, in the research-case form."""
    wikitree = str(dossier.get("id") or slug)
    return {"schema_version": "3.0", "id": wikitree, "catalogue_id": slug, "name": dossier.get("name"),
            "url": f"/people/{slug}.html", "source_json": f"/people/{slug}.json", "build": "build_person_models",
            "vitals": {}, "original_vitals": dict(dossier.get("vitals") or {}), "review": None, "override": None,
            "dna": [], "atlas": wikitree in data["atlas"], "selection_id": wikitree, "composite_entry": False}


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


def build(web: Path, policy=None) -> tuple[dict[str, dict], Counter]:
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
        updated = {**model, **stage_one(path.stem, dossier, data), **stage_two(path.stem, data),
                   **stage_three(path.stem, dossier, model, data)}
        if updated != model:
            changed[path.stem] = updated
            counts["models updated"] += 1
    for slug in sorted(data["public"] - {path.stem for path in (web / "assets/research/people").glob("*.json")}):
        dossier = _load(web / "people" / f"{slug}.json")
        if not isinstance(dossier, dict) or dossier.get("likely_living") or dossier.get("withheld") \
                or (policy and slug in policy.blocked):
            counts["dossiers withheld, no model"] += 1
            continue
        model = new_model(slug, dossier, data)
        model = {**model, **stage_one(slug, dossier, data), **stage_two(slug, data)}
        changed[slug] = {**model, "vitals": dict(dossier.get("vitals") or {})}
        counts["models created"] += 1
    return changed, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--web", type=Path, default=ROOT / "www")
    parser.add_argument("--check", action="store_true", help="report what would change; write nothing")
    args = parser.parse_args(argv)
    try:
        from public_privacy import from_sources
        policy = from_sources(all_exports=True)
    except FileNotFoundError:
        policy = None
    changed, counts = build(args.web, policy)
    if not args.check:
        for slug, model in changed.items():
            (args.web / "assets/research/people" / f"{slug}.json").write_text(
                json.dumps(model, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"written": not args.check, **dict(sorted(counts.items()))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
