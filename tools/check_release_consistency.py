#!/usr/bin/env python3
"""Check that headline totals agree across the published data and pages.

Targeted additions can update the people data without regenerating every
summary, leaving pages that say 4,660 people while the data has 4,662.  This
check derives each total from the published search index and compares it with
people.json, health.json and the catalogue statistics.  ``--fix`` rewrites
only the numbers it verifies.

    .venv/bin/python tools/check_release_consistency.py [--fix]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "www"
PAGES = ("catalogue.html", "catalogue/index.html", "catalogue/advanced.html", "people/index.html", "status.html", "status/index.html", "statistics/index.html")


def expected_totals() -> dict[str, int]:
    index = json.loads((WEB / "data/catalogue-search-index.json").read_text(encoding="utf-8"))
    return {
        "Historical people": len(index),
        "Exported family roots": len({p["family_root"]["id"] for p in index if p.get("family_root")}),
        "People linked to a root": sum(1 for p in index if p.get("family_root")),
        "People with original evidence": sum(1 for p in index if p.get("has_original_record")),
        "Creation-ready profiles": sum(1 for p in index if p.get("profile_work_status") == "creation_ready"),
    }


STAT = r'(<strong>)([\d,]+)(</strong><span>{label}</span>)'
LLMS = re.compile(r"catalogue contains ([\d,]+) historical or deceased individuals")
LEDE = re.compile(r"Search ([\d,]+) historical people")


def check(fix: bool) -> list[str]:
    totals = expected_totals()
    people = totals["Historical people"]
    problems = []
    people_json = json.loads((WEB / "data/people.json").read_text(encoding="utf-8"))
    for label, value in (("people.json people", len(people_json["people"])), ("people.json count", people_json.get("count", len(people_json["people"])))):
        if value != people:
            problems.append(f"{label}: {value:,} != search index {people:,}")
    health_path = WEB / "health.json"
    if health_path.exists():
        health = json.loads(health_path.read_text(encoding="utf-8"))
        counts = health.get("counts", {})
        if counts.get("people") not in (None, people):
            problems.append(f"health.json people: {counts['people']:,} != {people:,}")
            if fix:
                counts["people"] = people
                health_path.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for relative in PAGES:
        path = WEB / relative
        if not path.exists():
            continue
        page = original = path.read_text(encoding="utf-8")
        for label, value in totals.items():
            pattern = re.compile(STAT.format(label=re.escape(label)))
            for match in pattern.finditer(page):
                if int(match[2].replace(",", "")) != value:
                    problems.append(f"{relative} '{label}': {match[2]} != {value:,}")
            page = pattern.sub(lambda m, v=value: f"{m[1]}{v:,}{m[3]}", page)
        for match in LEDE.finditer(page):
            if int(match[1].replace(",", "")) != people:
                problems.append(f"{relative} lede: {match[1]} != {people:,}")
        page = LEDE.sub(f"Search {people:,} historical people", page)
        total = re.search(r'<strong id="catalogue-total">([\d,]+)</strong>', page)
        if total and int(total[1].replace(",", "")) != people:
            problems.append(f"{relative} header total: {total[1]} != {people:,}")
            page = page.replace(total[0], f'<strong id="catalogue-total">{people:,}</strong>')
        if fix and page != original:
            path.write_text(page, encoding="utf-8")
    llms = WEB / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        match = LLMS.search(text)
        if match and int(match[1].replace(",", "")) != people:
            problems.append(f"llms.txt people: {match[1]} != {people:,}")
            if fix:
                llms.write_text(LLMS.sub(f"catalogue contains {people:,} historical or deceased individuals", text), encoding="utf-8")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="rewrite verified totals in place")
    args = parser.parse_args()
    problems = check(args.fix)
    for problem in problems:
        print(("fixed: " if args.fix else "MISMATCH: ") + problem)
    if problems and not args.fix:
        sys.exit(1)
    print("Release totals consistent." if not problems else f"Fixed {len(problems)} total(s).")


if __name__ == "__main__":
    main()
