#!/usr/bin/env python3
"""Check that headline totals agree across the published data and pages.

Targeted additions can update the people data without regenerating every
summary, leaving pages that say 4,660 people while the data has 4,662.  This
check derives each total from the published search index and compares it with
people.json, health.json and the catalogue statistics.  ``--fix`` rewrites
only the numbers it verifies.

    .venv/bin/python tools/check_release_consistency.py [--fix] [--no-research]

It also runs tools/check_research_publication.py with its baseline, so the
release fails when research would not reach a reader (a new item only).
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "www"
PAGES = ("index.html", "coverage/index.html", "records/index.html", "catalogue.html", "catalogue/index.html", "catalogue/advanced.html", "people/index.html", "status.html", "status/index.html", "statistics/index.html")


def expected_totals() -> tuple[dict[str, int], dict[str, int] | None]:
    index = json.loads((WEB / "data/catalogue-search-index.json").read_text(encoding="utf-8"))
    totals = {
        "Historical people": len(index),
        "Exported family roots": len({p["family_root"]["id"] for p in index if p.get("family_root")}),
        "People linked to a root": sum(1 for p in index if p.get("family_root")),
        "People with original evidence": sum(1 for p in index if p.get("has_original_record")),
        "Creation-ready profiles": sum(1 for p in index if p.get("profile_work_status") == "creation_ready"),
    }
    source_links = None
    for label, filename in (("Mapped records", "records-index.json"), ("Research places", "places-index.json")):
        path = WEB / "data" / filename
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
            totals[label] = len(rows)
            if label == "Mapped records":
                source_links = dict(Counter(row.get("supporting_source_status") or "unresolved" for row in rows))
    return totals, source_links


STAT = r'(<strong>)([\d,]+)(</strong><span>{label}</span>)'
LLMS = re.compile(r"catalogue contains ([\d,]+) historical or deceased individuals")
LEDE = re.compile(r"Search ([\d,]+) historical people")


def check(fix: bool) -> list[str]:
    totals, expected_links = expected_totals()
    people = totals["Historical people"]
    # The home, coverage, status and records pages present the same units with different markup.
    patterns = [(label, re.compile(STAT.format(label=re.escape(label)))) for label in totals]
    patterns.extend([
        ("Historical people", re.compile(r'(Search )([\d,]+)( people by name)')),
        ("Historical people", re.compile(r'(The people index contains <strong>)([\d,]+)( people</strong>)')),
    ])
    for name, label in (("Historical people", "People in the index"), ("Mapped records", "Record entries linked to people"),
                        ("Mapped records", "record entries"), ("Research places", "Places")):
        if name in totals:
            patterns.append((name, re.compile(r'(<strong(?: class="r-coverage-number")?>)([\d,]+)(</strong><(?:p|span)>' + label + r'</(?:p|span)>)')))
    problems = []
    people_json = json.loads((WEB / "data/people.json").read_text(encoding="utf-8"))
    for label, value in (("people.json people", len(people_json["people"])), ("people.json count", people_json.get("count", len(people_json["people"])))):
        if value != people:
            problems.append(f"{label}: {value:,} != search index {people:,}")
    manifest_path = WEB / "data/manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        datasets = {row["name"]: row["count"] for row in manifest["datasets"]}
        for name, label in (("people", "Historical people"), ("records", "Mapped records")):
            if label in totals and datasets.get(name) != totals[label]:
                actual = f"{datasets[name]:,}" if name in datasets else "missing"
                problems.append(f"manifest.json {name}: {actual} != {totals[label]:,}")
    health_path = WEB / "health.json"
    if health_path.exists():
        health = json.loads(health_path.read_text(encoding="utf-8"))
        counts = health.get("counts", {})
        changed = False
        for key, label in (("people", "Historical people"), ("records", "Mapped records"), ("places", "Research places")):
            expected = totals.get(label)
            if expected is not None and counts.get(key) not in (None, expected):
                problems.append(f"health.json {key}: {counts[key]:,} != {expected:,}")
                if fix:
                    counts[key] = expected
                    changed = True
        if expected_links is not None and health.get("source_links") != expected_links:
            problems.append(f"health.json source_links: {health.get('source_links')} != {expected_links}")
            if fix:
                health["source_links"] = expected_links
                changed = True
        if changed:
            health_path.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for relative in PAGES:
        path = WEB / relative
        if not path.exists():
            continue
        page = original = path.read_text(encoding="utf-8")
        if relative == "records/index.html" and expected_links is not None:
            strip = re.search(r'<div class="records-status-strip"[^>]*>(.*?)<p id="records-scope"', page, re.S)
            if strip:
                displayed = sum(int(number.replace(",", "")) for number in re.findall(r'<strong>([\d,]+)</strong>', strip[1]))
                if displayed != totals["Mapped records"]:
                    problems.append(f"{relative} citation-status counts: {displayed:,} != {totals['Mapped records']:,}")
        for label, pattern in patterns:
            value = totals[label]
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


def repair_totals() -> list[str]:
    """Report completed repairs and return discrepancies still present."""
    before = check(fix=True)
    if not before:
        return []
    remaining = check(fix=False)
    unresolved = set(remaining)
    for problem in before:
        if problem not in unresolved:
            print("fixed:", problem)
    return remaining


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="rewrite verified totals in place")
    parser.add_argument("--no-research", action="store_true", help="skip the research publication check")
    args = parser.parse_args()
    problems = repair_totals() if args.fix else check(fix=False)
    for problem in problems:
        print("MISMATCH:", problem)
    research_failed = False if args.no_research else research_check() != 0
    if problems or research_failed:
        sys.exit(1)
    print("Release totals consistent.")


def research_check() -> int:
    """Research written in findings.md, the register and the queue must reach the site."""
    root = WEB.parent
    if not (root / "data/wikitree/research-catalogue-cases.json").exists():
        print("Research publication check skipped: no research data here.")
        return 0
    try:
        from tools import check_research_publication as research
    except ModuleNotFoundError:
        sys.path.insert(0, str(root))
        from tools import check_research_publication as research
    return research.main(["--baseline", str(root / research.DEFAULT_BASELINE)])


if __name__ == "__main__":
    main()
