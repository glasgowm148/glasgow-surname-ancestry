#!/usr/bin/env python3
"""Audit repeated catalogue identities; apply only evidence-defined native merges.

A name, estimated year or shared locality alone never authorizes a merge.
Original source documents remain unchanged. Native merges can be undone.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genealogy.store import Research, open_project, stable_id
from tools.workbench_legacy_views import Views

MANIFEST = Path("research/queue-review-2026-10-17/catalogue-integration.json")


def fold(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def signatures(entry):
    """Require a recorded role/event, full transcript, or exact provider subject."""
    name = fold(entry["name"])
    for record in entry.get("records", []):
        association = fold(record.get("association"))
        note = fold(record.get("note"))
        year, place = str(record.get("year") or ""), fold(record.get("record_location"))
        # Full event wording includes the named child and exact event date.
        if len(association) > 65 and re.search(r"\b\d{1,2} [a-z]+ \d{4}\b", association):
            yield ("event", name, association, year, place)
        # Literal detailed index fields, excluding editorial consolidation notes.
        if note.startswith("ancestry index transcript;") and re.search(
                r"(?:birth|baptism|marriage|death) date: \d", note):
            yield ("transcript", name, note, year, place)
        # Same provider URL is insufficient if parent and child share a name.
        if len(association) > 65 and record.get("source_url") and re.search(
                r"\b(?:father|mother|parent|born|baptised|christened|marriage|soldier|pensioner)\b", association):
            yield ("provider-subject", name, record["source_url"], association)
        # The reported example: consolidate one unresolved Royal Sussex account,
        # retaining the distinction between a record cluster and proved identity.
        if name == "a e glasgow" and "/collections/1262/" in record.get("source_url", ""):
            if re.search(r"\b(?:royal sussex|r sussex)\b", note):
                yield ("held-regiment", name, "royal sussex", "1914-1920")


def conflicts(entries):
    """Never silently choose between explicit competing structured facts."""
    for field in ("birth", "death", "birth_location", "death_location", "gender"):
        values = {fold(r.get(field)) for r in entries if r.get(field)}
        if len(values) > 1:
            return f"conflicting {field}: {sorted(values)}"
    for field in ("father", "mother", "parents", "spouses", "children"):
        values = {json.dumps(r[field], sort_keys=True) for r in entries if r.get(field)}
        if len(values) > 1:
            return f"competing structured {field}"
    return ""


def scan(entries):
    by_id = {r["catalogue_id"]: r for r in entries}
    parent = {ident: ident for ident in by_id}
    evidence = defaultdict(list)

    def find(ident):
        while parent[ident] != ident:
            ident = parent[ident]
        return ident

    index = defaultdict(set)
    for row in entries:
        for key in signatures(row):
            index[key].add(row["catalogue_id"])
    rejected = []
    for key, ids in sorted(index.items()):
        if len(ids) < 2:
            continue
        roots = {find(i) for i in ids}
        members = [i for i in by_id if find(i) in roots]
        conflict = conflicts([by_id[i] for i in members])
        if conflict:
            rejected.append({"ids": sorted(ids), "reason": conflict})
            continue
        survivor = min(members)
        for ident in members:
            parent[find(ident)] = survivor
        evidence[survivor].append({"kind": key[0], "detail": list(key[1:]), "ids": sorted(ids)})
    groups = defaultdict(list)
    for ident in by_id:
        groups[find(ident)].append(ident)
    result = []
    for survivor, ids in sorted(groups.items()):
        if len(ids) < 2:
            continue
        proof = [item for values in evidence.values() for item in values if set(item["ids"]) <= set(ids)]
        result.append({"survivor": survivor, "retired": sorted(set(ids) - {survivor}),
                       "name": by_id[survivor]["name"], "evidence": proof,
                       "qualification": ("Consolidated unresolved Royal Sussex medal-card account; "
                           "same initials, service period and regiment. This does not prove all cards "
                           "belong to one serviceman; original images and full identity remain to check.")
                           if any(e["kind"] == "held-regiment" for e in proof)
                           else "Same documentary subject and detailed event; original index citations retained. "
                                "Existing-profile identification and any wider family hypothesis remain unresolved."})
    return result, rejected


def apply(root, groups):
    """All decisions preflight before a single reversible workbench transaction."""
    with open_project(root) as project:
        research = Research(project.store)
        active = Views(project.store)._merged_public
        aliases = {r["value"]: r["entity_id"] for r in project.store.all(
            "SELECT value,entity_id FROM external_id WHERE system='glasgow-local' AND status='current'")}
        with project.store.write(actor="catalogue duplicate audit", tool="audit_catalogue_duplicates") as tx:
            for group in groups:
                ids = [group["survivor"], *group["retired"]]
                for ident in ids:
                    if ident in active:
                        continue
                    if ident not in aliases:
                        pid = stable_id("per", "glasgow-local", ident)
                        research.create_person(tx, id=pid, label=group["name"], record_defined=True)
                        research.map_external(tx, pid, "glasgow-local", ident)
                        aliases[ident] = pid
                for retired in group["retired"]:
                    if retired in active:
                        if active[retired] != group["survivor"]:
                            raise ValueError(f"{retired}: already merged elsewhere")
                        continue
                    reason = json.dumps({"reviewed": str(date.today()), "basis": group["qualification"],
                                         "evidence": group["evidence"]}, ensure_ascii=False)
                    research.merge_people(tx, survivor_id=aliases[group["survivor"]],
                                          retired_id=aliases[retired], reason=reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    entries = json.loads((args.root / MANIFEST).read_text())["new_people"]
    catalogue = json.loads((args.root / "www/data/catalogue-search-index.json").read_text())
    all_people = json.loads((args.root / "www/data/people.json").read_text())["people"]
    whole_groups, rejected = scan(all_people)
    known = {row["catalogue_id"] for row in entries}
    groups = [group for group in whole_groups if set([group["survivor"], *group["retired"]]) <= known]
    outside = [group for group in whole_groups if group not in groups]
    names = defaultdict(list)
    for person in catalogue:
        names[fold(person["name"])].append(person["id"])
    repeated = {name: ids for name, ids in names.items() if len(ids) > 1}
    report = {"catalogue_rows_scanned": len(catalogue), "same_name_groups_scanned": len(repeated),
              "reviewed_draft_rows_scanned": len(entries), "merge_groups": groups,
              "retired_count": sum(len(g["retired"]) for g in groups),
              "conflict_holds": rejected, "outside_creation_holds": outside, "same_name_inventory": repeated,
              "limits": "Whole-catalogue name inventory and detailed documentary event/provider comparison. "
                        "Names alone do not establish duplicates. Live WikiTree profiles are not merged."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    if args.apply:
        apply(args.root, groups)
    print(json.dumps({k: report[k] for k in ("catalogue_rows_scanned", "same_name_groups_scanned",
                                           "reviewed_draft_rows_scanned", "retired_count")}))
    print(f"Merge groups: {len(groups)}; conflict holds: {len(rejected)}")


if __name__ == "__main__":
    main()
