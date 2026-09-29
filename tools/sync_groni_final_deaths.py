#!/usr/bin/env python3
"""Synchronise the reviewed GRONI death decisions into the local catalogue.

This is deliberately separate from the older live-creation sync.  The review
files are the authority for the final disposition of the 152 death rows and
are safe to apply repeatedly.
"""
from __future__ import annotations

import argparse, csv, json, shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "surname-research/indexes/groni-death-match-audit-2026-09-23.csv"
META = AUDIT.with_suffix(".json")
CASES = ROOT / "data/wikitree/research-catalogue-cases.json"
RESEARCH = ROOT / "research"
NEW = ROOT / "surname-research/new-people"
DURABLE_LOG = ROOT / "surname-research/indexes/groni-created-profiles-2026-09-23.json"

FILES = [
    Path("/tmp/groni-death-attach-reviewed.json"),
    Path("/tmp/groni-death-new-reviewed.json"),
    Path("/tmp/groni-death-remaining-final.json"),
]


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def decision_rows():
    out = {}
    for path in FILES:
        for item in load_json(path, []):
            reg = item.get("registration") or item.get("registration_number")
            if reg:
                out[reg] = item
    # The unnamed decision file is shared with the birth audit.  Its death
    # targets are useful when the final creation agent has recorded them.
    for item in load_json(Path("/tmp/groni-unnamed-decisions.json"), {}).get("decisions", []):
        if item.get("record_type") == "death" and item.get("registration_number"):
            out.setdefault(item["registration_number"], item)
    return out


def creation_items():
    data = load_json(Path("/tmp/groni_death_final_creation_log.json"), {})
    items = list(data.get("created", []))
    # Keep profiles created by the earlier workflow in the durable mapping.
    old = load_json(DURABLE_LOG, {})
    seen = {(x.get("registration"), x.get("id")) for x in items}
    for item in old.get("created", []):
        key = (item.get("registration"), item.get("id"))
        if key not in seen:
            items.append(item); seen.add(key)
    return items


def add_note(wid: str, reg: str, item: dict, row: dict):
    """Add one compact, keyed research note without touching existing prose."""
    path = RESEARCH / wid / "findings.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = f"<!-- groni-death-lead:{reg} -->"
    if path.exists() and marker in path.read_text(encoding="utf-8"):
        return False
    text = path.read_text(encoding="utf-8") if path.exists() else f"# {row['forename_as_supplied']} Glasgow ({wid})\n\n"
    citation = item.get("citation") or (
        f"[https://geni.nidirect.gov.uk/search/death GRONI civil death index], "
        f"{row['forename_as_supplied']} Glasgow, {row['death_date']}, "
        f"{row['district']} registration district, {reg}; indexed details supplied 23 September 2026."
    )
    block = (f"\n\n## GRONI death-index lead\n\n{marker}\n"
             f"The death index records {row['forename_as_supplied']} Glasgow on {row['death_date']} "
             f"in the {row['district']} registration district, aged {row['age_at_death'] or 'unknown'}. "
             f"This is attached as a research lead; the identity is not treated as proved. {citation}\n")
    path.write_text(text.rstrip() + block, encoding="utf-8")
    return True


def generated_finding(item, row):
    wid = item["id"]
    return f'''<!-- generated: groni-final-death-sync -->
# {row['forename_as_supplied']} Glasgow ({wid}): civil death index

## Current conclusion

The death index records {row['forename_as_supplied']} Glasgow on {row['death_date']} in the {row['district']} registration district, aged {row['age_at_death'] or 'unknown'}. This profile was created after the reviewed duplicate check.

## Source findings

- [https://geni.nidirect.gov.uk/search/death General Register Office for Northern Ireland, civil death index], `{row['registration_number']}`.
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    rows = list(csv.DictReader(AUDIT.open(newline="", encoding="utf-8")))
    byreg = {r["registration_number"]: r for r in rows}
    decisions = decision_rows()
    creations = creation_items()
    created_by_reg = {x.get("registration"): x for x in creations if x.get("registration") and x.get("id")}
    actions = []

    for reg, item in decisions.items():
        row = byreg.get(reg)
        if not row:
            continue
        decision = item.get("decision", "")
        wid = item.get("profile") or item.get("best_id") or item.get("target")
        created = created_by_reg.get(reg)
        if created:
            wid = created["id"]
        if decision in {"create", "concrete_conflict_create"} and created:
            status, reason = "new_profile_created", "Reviewed duplicate check resulted in a new profile."
        elif decision in {"safe_attach", "attach"}:
            status, reason = "existing_profile", item.get("evidence", "Reviewed record attached to the existing profile.")
        elif decision in {"hold", "attach_research_note"} and wid:
            status, reason = "lead_attached", item.get("evidence", "Reviewed record attached as a research lead.")
        elif decision in {"create", "concrete_conflict_create"}:
            # Do not claim completion while the live creation log is still growing.
            continue
        else:
            continue
        row.update(assessment=status, candidate_wikitree_ids=wid or "", reason=reason,
                   live_duplicate_review=f"Reviewed final decision: {status}." )
        if args.write and status == "lead_attached" and wid:
            if add_note(wid, reg, item, row): actions.append(f"added lead note {reg} -> {wid}")

    if args.write:
        # Preserve all non-death records and exact registration mapping.
        with AUDIT.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
        log = {"created": creations, "needs_review": [], "errors": []}
        DURABLE_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        meta = load_json(META, {})
        counts = {}
        for row in rows: counts[row["assessment"]] = counts.get(row["assessment"], 0) + 1
        meta["counts"] = counts
        meta["final_death_sync"] = {"updated": date.today().isoformat(), "source": [str(p) for p in FILES], "created_profile_ids": sorted({x["id"] for x in creations if x.get("id")})}
        META.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        manifest = load_json(CASES, {}); cases = manifest.setdefault("cases", {})
        for item in creations:
            wid = item.get("id")
            if not wid: continue
            cases.setdefault(wid, {"status":"pending", "profile_id":wid, "reason":"Created from reviewed GRONI death-index evidence; public metadata capture pending."})
        CASES.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Move only matching drafts; never overwrite a finding that contains later research.
        for item in creations:
            reg, wid = item.get("registration"), item.get("id")
            if not reg or not wid: continue
            for draft in NEW.glob("*.md"):
                if reg not in draft.read_text(errors="ignore"): continue
                dest = RESEARCH / wid; dest.mkdir(parents=True, exist_ok=True)
                target = dest / draft.name
                if not target.exists(): shutil.move(str(draft), str(target))
                break
            finding = RESEARCH / wid / "findings.md"
            if not finding.exists() and reg in byreg:
                finding.write_text(generated_finding(item, byreg[reg]), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "decisions": len(decisions), "created": len(creations), "actions": actions, "write": args.write}, indent=2))


if __name__ == "__main__": main()
