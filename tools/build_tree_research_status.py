#!/usr/bin/env python3
"""Write the research-status layer the whole-tree view draws over people.

Output: ``www/assets/research/tree-research-status.json``, read by the atlas
(``tools/atlas_whole_tree.py``) when a research mark is switched on.

For every person who is already in the public atlas model it records only
flags, dates and counts, never research text:

- ``r``: a ``research/<ID>/findings.md`` file exists; ``c``: it has an overall
  ``## Current conclusion``.
- ``n`` / ``k``: date of the newest entry in ``research/latest-findings.json``
  that names the person, and how many entries do.
- ``q``: WikiTree update state: ``open`` (the built catalogue shows an update
  for the profile), ``blocked`` (queued, but the profile is managed by another
  account), ``held`` (queued but not shown, e.g. kept back for privacy) or
  ``done``.
- ``d``: research-check codes that need an editor's decision for this person
  (from ``tools/check_research_publication.py``; see ``DECISION_CODES``).

Run after a research batch; ``tools/build_latest_findings.py`` calls it at the
end of every run, so the tree follows the latest findings automatically.

    python tools/build_tree_research_status.py [--no-checks]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "www/assets/research/atlas-model.json"
OUTPUT = "www/assets/research/tree-research-status.json"

# Research-check findings that ask for an editor's decision, with the short,
# text-free reason shown in the tree.
DECISION_CODES = {
    "CONCLUSION_CONFLICT": "two overall conclusions disagree",
    "CONCLUSION_OLDER_THAN_CORRECTION": "conclusion older than a later correction",
    "OPENING_FALLBACK": "no overall conclusion written",
    "NO_PAGE_UNDECIDED": "findings with no page decision",
    "OVERVIEW_OLDER_THAN_FINDINGS": "overview older than its findings",
    "CORRECTION_NOT_IN_BUILT_RECORDS": "record list still shows a corrected reading",
}


def queue_state(status: object, ident: str, completed: set[str], reopened: set[str]) -> str:
    text = str(status or "").strip().upper()
    if text.startswith("BLOCKED"):
        return "blocked"
    if text.startswith("DONE"):
        return "done"
    if text in ("", "NONE"):
        return "done" if ident in completed and ident not in reopened else "open"
    return "open"


def site_update_flags(root: Path) -> set[str] | None:
    """Profiles the built catalogue marks ``needs_wikitree_update`` (None if not built)."""
    path = root / "www/data/catalogue-search-fast.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    fields, strings = data["fields"], data["strings"]
    flag, ids = fields.index("needs_wikitree_update"), fields.index("profile_ids")

    def text(value):
        return strings[-value - 1] if isinstance(value, int) and not isinstance(value, bool) and value < 0 else value

    found: set[str] = set()
    for row in data["rows"]:
        if row[flag] is True:
            found.update(text(v) for v in (row[ids] or []))
    return found


def decision_items(root: Path) -> list[tuple[str, str]]:
    """(subject, code) pairs from the research publication check."""
    sys.path.insert(0, str(root))
    from tools.check_research_publication import run  # noqa: E402

    checker = run(root, None, site=True)
    return [(item.subject, item.code) for item in checker.items if item.code in DECISION_CODES]


def build(root: Path = ROOT, checks: bool = True) -> dict:
    model = json.loads((root / MODEL).read_text(encoding="utf-8"))
    public = {p["id"] for p in model["people"] if p.get("kind") == "person"}
    people: dict[str, dict] = {}

    def entry(ident: str) -> dict:
        return people.setdefault(ident, {})

    for folder in sorted((root / "research").iterdir()):
        findings = folder / "findings.md"
        if folder.name in public and findings.is_file():
            row = entry(folder.name)
            row["r"] = 1
            if "\n## Current conclusion" in "\n" + findings.read_text(encoding="utf-8", errors="replace"):
                row["c"] = 1

    ledger = json.loads((root / "research/latest-findings.json").read_text(encoding="utf-8"))
    for finding in ledger.get("findings", []):
        found = str(finding.get("found_on") or "")[:10]
        for person in finding.get("people", []):
            ident = person.get("id")
            if ident not in public:
                continue
            row = entry(ident)
            row["k"] = row.get("k", 0) + 1
            if found and found > row.get("n", ""):
                row["n"] = found

    queue_path = root / "data/wikitree/profile-update-queue.json"
    flagged = site_update_flags(root)
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        completed = set(queue.get("completed_live_profiles") or [])
        reopened = set(queue.get("reopened_completed_profiles") or [])
        for ident, item in (queue.get("entries") or {}).items():
            if ident not in public:
                continue
            state = queue_state(item.get("status") if isinstance(item, dict) else None, ident, completed, reopened)
            # The catalogue decides which updates are shown; follow it when it is built.
            if flagged is not None and state == "open" and ident not in flagged:
                state = "done" if ident in completed else "held"
            entry(ident)["q"] = state
    for ident in flagged or ():
        if ident in public and entry(ident).get("q") not in ("blocked",):
            entry(ident)["q"] = "open"

    if checks:
        for subject, code in decision_items(root):
            if subject in public:
                codes = entry(subject).setdefault("d", [])
                if code not in codes:
                    codes.append(code)

    counts = {
        "researched": sum(1 for r in people.values() if r.get("r")),
        "concluded": sum(1 for r in people.values() if r.get("c")),
        "withFindings": sum(1 for r in people.values() if r.get("k")),
        "queueOpen": sum(1 for r in people.values() if r.get("q") == "open"),
        "queueBlocked": sum(1 for r in people.values() if r.get("q") == "blocked"),
        "queueHeld": sum(1 for r in people.values() if r.get("q") == "held"),
        "needsDecision": sum(1 for r in people.values() if r.get("d")),
    }
    return {
        "schema_version": 1,
        "generated": date.today().isoformat(),
        "about": "Research flags for people in the public tree: findings file, newest dated finding, "
                 "WikiTree update queue state and research-check items needing a decision. No research text.",
        "decisionLabels": DECISION_CODES,
        "decisionsChecked": checks,
        "counts": counts,
        "people": dict(sorted(people.items())),
    }


def write(root: Path = ROOT, checks: bool = True) -> dict:
    payload = build(root, checks)
    target = root / OUTPUT
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    if not target.exists() or target.read_text(encoding="utf-8") != text:
        target.write_text(text, encoding="utf-8")
    return payload["counts"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-checks", action="store_true", help="skip the research check (no 'needs a decision' flags)")
    args = parser.parse_args(argv)
    print(json.dumps(write(ROOT, not args.no_checks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
