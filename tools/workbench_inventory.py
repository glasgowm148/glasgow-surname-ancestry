#!/usr/bin/env python3
"""Inventory, classify and back up Glasgow's research inputs before migration.

Reads a Glasgow checkout (default: the repository this script is in) without
changing it. Writes private outputs only:

* ``inventory``: every relevant file with its format, location, provenance
  class, access class, SHA-256, consumers and intended migration disposition,
  as ``data/private/workbench/inventory/inventory.json``, plus a public-safe
  count summary for ``docs/workbench-migration/inventory-summary.md``;
* ``backup``: a compressed archive of the ignored and untracked research inputs
  that Git does not preserve, with a per-file hash manifest, verified by
  reading every archived member back and comparing hashes (no extraction).

Tracked files are preserved by the Git commit recorded in the manifest; the
archive covers what only exists on this machine.

    .venv/bin/python tools/workbench_inventory.py inventory --source-root PATH
    .venv/bin/python tools/workbench_inventory.py backup --source-root PATH
    .venv/bin/python tools/workbench_inventory.py verify ARCHIVE
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "data" / "private" / "workbench"

# Directories summarised by size and count only: scratch space, release
# archives and caches that hold no migration input of their own.
SUMMARISED = {
    "tmp": ("workflow scratch", "excluded", "Agent and researcher scratch space; may hold unreviewed leads. Not "
            "migrated; flagged for owner review before any clean-up."),
    "archive": ("historical snapshots and backups", "excluded", "Earlier site releases and dumps; retained as-is."),
    "dist": ("historical snapshots and backups", "excluded", "Release tarballs of built sites; reproducible output."),
    ".cache": ("reproducible derivatives", "excluded", "Download and OCR caches; originals are referenced elsewhere."),
    "artifacts": ("reproducible derivatives", "excluded", "Reports, screenshots and deployment logs."),
    ".venv": ("tooling", "excluded", "Python environment."),
    ".git": ("tooling", "excluded", "Version history; tracked inputs are preserved by commit."),
    ".playwright-cli": ("tooling", "excluded", "Browser automation state."),
    ".ruff_cache": ("tooling", "excluded", "Linter cache."),
    "test-results": ("reproducible derivatives", "excluded", "Test output."),
    "output": ("reproducible derivatives", "excluded", "Verification output and screenshots."),
}

# (pattern, category, access, disposition, consumers) — first match wins.
RULES: list[tuple[str, str, str, str, str]] = [
    (r"^\.env", "secrets", "secret", "excluded", "never migrated or published"),
    (r"^research/relationship_assessments\.json$", "authoritative research", "private", "structured",
     "relationship claims and assessment revisions"),
    (r"^research/relationship_probability_estimates\.json$", "authoritative research", "private", "structured",
     "subjective estimates; reverse rows derived from one assessment"),
    (r"^research/relationship_history_seed\.json$", "authoritative research", "private", "structured",
     "historical tree-relationship claims"),
    (r"^research/vital_assessments\.json$", "authoritative research", "private", "structured", "vital claims"),
    (r"^research/canonical_records\.json$", "authoritative research", "private", "structured",
     "sources, records, mentions and identifications"),
    (r"^research/latest-findings\.json$", "authoritative research", "private", "structured", "dated findings"),
    (r"^research/(ydna-publication-approval|publication-restoration-approval)\.json$", "publication decisions",
     "private", "structured", "exact-file approvals"),
    (r"^research/transcriptions/public-preview-approvals\.json$", "publication decisions", "private", "structured",
     "exact-file approvals"),
    (r"^research/research-queue-(matches|overrides)\.json$", "workflow state", "private", "structured",
     "WikiTree proposal reviews and overrides"),
    (r"^research/[^/]+/captures/", "original evidence and captures", "restricted", "asset",
     "immutable WikiTree API captures"),
    (r"^research/[^/]+/(research_plan|parent_candidates|records_mentions|presentation)\.json$",
     "authoritative research", "private", "structured", "questions, searches, hypotheses, mentions, presentation"),
    (r"^research/[^/]+/(evidence_index|research_state)\.json$", "imported observations and external tree state",
     "restricted", "asset", "capture indexes"),
    (r"^research/[^/]+/.*\.(wiki|wikitext)$", "workflow state", "private", "asset", "WikiTree drafts and diffs"),
    (r"^research/[^/]+/.*\.(pdf|png|jpe?g|tiff?|webp)$", "original evidence and captures", "restricted", "asset",
     "record images and PDFs"),
    (r"^research/[^/]+/.*\.(md|txt|csv|tsv|html|svg)$", "research prose and editorial content", "private", "asset",
     "briefs, findings logs, notes, figures"),
    (r"^research/[^/]+/.*\.json$", "authoritative research", "private", "asset",
     "dated review, audit and batch records kept verbatim"),
    (r"^research/[^/]+\.(md|csv|json)$", "authoritative research", "private", "asset", "batch audits and indexes"),
    (r"^research/.*\.py$", "tooling", "private", "excluded", "one-off scripts"),
    (r"^data/exports/one-tree/.*\.json$", "imported observations and external tree state", "private", "structured",
     "OneTree export: people and tree relationships as observations"),
    (r"^data/exports/", "imported observations and external tree state", "private", "asset", "spreadsheet exports"),
    (r"^data/wikitree/profile-update-queue\.json$", "workflow state", "private", "structured", "WikiTree proposals"),
    (r"^data/wikitree/(profile-evidence|live-profile-overrides)\.json$",
     "imported observations and external tree state", "restricted", "structured", "WikiTree observations, redirects"),
    (r"^data/wikitree/", "workflow state", "private", "asset", "catalogue links, audits, scans"),
    (r"^data/place-gazetteer\.json$", "reference data", "public", "structured", "places and coordinates"),
    (r"^data/private/", "original evidence and captures", "restricted", "asset",
     "private captures and approved publication sources"),
    (r"^data/reference/", "reference data", "licensed", "asset", "discovery datasets"),
    (r"^data/", "presentation configuration", "private", "asset", "site configuration and baselines"),
    (r"^www/map/data/", "generated output containing otherwise unpreserved input", "private", "asset",
     "map records retained under www"),
    (r"^www/data/people\.json$", "generated output containing otherwise unpreserved input", "public", "structured",
     "catalogue people missing from the OneTree export"),
    (r"^www/people/[^/]+\.json$", "generated output containing otherwise unpreserved input", "public", "asset",
     "public dossiers cited as sources by vital assessments"),
    (r"^www/", "reproducible derivatives", "public", "derivative", "generated website"),
    (r"^ydna/.*\.(zip|bam|vcf|fastq|fq)(\.gz)?$", "DNA", "raw_dna", "excluded", "raw sequence files stay private"),
    (r"^ydna/", "DNA", "private", "asset", "Y-DNA study material; publication by approval only"),
    (r"^assets/", "original evidence and captures", "private", "asset", "source images"),
    (r"^surname-research/", "research prose and editorial content", "private", "asset", "surname indexes and notes"),
    (r"^testaments/", "original evidence and captures", "restricted", "asset", "testament transcriptions and images"),
    (r"^chatgpt_dump/", "research prose and editorial content", "private", "asset",
     "exported AI research conversations (leads, not evidence)"),
    (r"^(tools/study_stories|tools/branch_territories|tools/site_sources)/", "presentation configuration", "public",
     "asset", "editorial presentation"),
    (r"^handover\.md$", "research prose and editorial content", "private", "asset", "agent handover notes"),
    (r"^[^/]+$", "tooling", "public", "excluded", "project configuration and scripts at the repository root"),
    (r"^(\.codex|\.github)/", "tooling", "public", "excluded", "automation configuration"),
    (r"^(tools|src|tests|docs|skills|requirements|deploy|config|vendor|\.agents|letterform_examples|pre1800-sprint|newresearch)/",
     "tooling", "public", "excluded", "code, documentation and examples (version-controlled)"),
]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative: str) -> tuple[str, str, str, str]:
    for pattern, category, access, disposition, consumers in RULES:
        if re.search(pattern, relative):
            return category, access, disposition, consumers
    return "unclassified", "private", "unresolved", "no rule; review"


def walk(source: Path):
    tracked = set(git(source, "ls-files", "-z").split("\0")) - {""}
    summarised: dict[str, dict] = {}
    for top in sorted(source.iterdir()):
        name = top.name
        if name in SUMMARISED:
            size = count = 0
            for dirpath, _, files in os.walk(top):
                for file in files:
                    try:
                        size += (Path(dirpath) / file).stat().st_size
                        count += 1
                    except OSError:
                        pass
            category, disposition, reason = SUMMARISED[name]
            summarised[name] = {"category": category, "disposition": disposition, "reason": reason, "files": count,
                                "bytes": size}
            continue
        paths = [top] if top.is_file() else sorted(p for p in top.rglob("*") if p.is_file())
        for path in paths:
            yield path, path.relative_to(source).as_posix(), path.relative_to(source).as_posix() in tracked
    walk.summarised = summarised


def inventory(source: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output.parent, 0o700)
    rows = []
    for path, relative, tracked in walk(source):
        if path.name in (".DS_Store",):
            continue
        category, access, disposition, consumers = classify(relative)
        stat = path.stat()
        row = {"path": relative, "tracked": tracked, "bytes": stat.st_size, "format": path.suffix.lower().lstrip(".") or "none",
               "category": category, "access": access, "disposition": disposition, "consumers": consumers}
        if disposition != "excluded" or category in ("secrets",):
            row["sha256"] = None if category == "secrets" else sha256(path)
        rows.append(row)
    head = git(source, "rev-parse", "HEAD").strip()
    dirty = git(source, "status", "--porcelain").strip().splitlines()
    report = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(), "source_root": str(source),
        "source_commit": head, "source_dirty_files": dirty, "files": rows, "summarised": walk.summarised,
    }
    (output / "inventory.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return report


def summary(report: dict) -> str:
    by = defaultdict(Counter)
    size = defaultdict(int)
    for row in report["files"]:
        key = (row["category"], row["disposition"], "tracked" if row["tracked"] else "local only")
        by[key]["files"] += 1
        size[key] += row["bytes"]
    lines = ["| Category | Disposition | Where | Files | MB |", "| --- | --- | --- | ---: | ---: |"]
    for key in sorted(by):
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {by[key]['files']} | {size[key] / 1e6:.1f} |")
    lines += ["", "| Summarised directory | Category | Disposition | Files | MB | Reason |",
              "| --- | --- | --- | ---: | ---: | --- |"]
    for name, item in sorted(report["summarised"].items()):
        lines.append(f"| `{name}/` | {item['category']} | {item['disposition']} | {item['files']} | "
                     f"{item['bytes'] / 1e6:.0f} | {item['reason']} |")
    return "\n".join(lines) + "\n"


def backup(source: Path, report: dict, destination: Path) -> dict:
    """Archive every local-only (untracked or ignored) file the inventory would migrate or retain."""
    destination.mkdir(parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    members = [row for row in report["files"] if not row["tracked"] and row["disposition"] in
               ("structured", "asset", "unresolved") and row["category"] != "secrets" and row["access"] != "raw_dna"]
    stamp = report["generated_at"].replace(":", "").replace("-", "")
    archive = destination / f"glasgow-local-inputs-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=6) as tar:
        for row in members:
            tar.add(source / row["path"], arcname=row["path"], recursive=False)
    os.chmod(archive, 0o600)
    manifest = {"archive": archive.name, "source_commit": report["source_commit"], "created_at": report["generated_at"],
                "files": {row["path"]: row["sha256"] for row in members},
                "excluded_raw_dna": [row["path"] for row in report["files"] if row["access"] == "raw_dna"],
                "note": "Tracked files are preserved by the source commit; this archive holds local-only inputs."}
    (destination / f"{archive.name}.manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return {"archive": str(archive), "members": len(members), "bytes": archive.stat().st_size}


def verify(archive: Path) -> list[str]:
    manifest = json.loads(Path(f"{archive}.manifest.json").read_text())
    expected = dict(manifest["files"])
    problems = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            handle = tar.extractfile(member)
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
            want = expected.pop(member.name, None)
            if want is None:
                problems.append(f"unexpected member {member.name}")
            elif want != digest.hexdigest():
                problems.append(f"hash mismatch {member.name}")
    problems.extend(f"missing member {name}" for name in sorted(expected))
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "backup"):
        command = sub.add_parser(name)
        command.add_argument("--source-root", type=Path, default=ROOT)
        command.add_argument("--output", type=Path, default=PRIVATE / ("inventory" if name == "inventory" else "baseline-backup"))
    check = sub.add_parser("verify")
    check.add_argument("archive", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        problems = verify(args.archive)
        print("\n".join(problems) if problems else f"Verified every member of {args.archive} against its manifest.")
        return 1 if problems else 0
    source = args.source_root.resolve()
    report = inventory(source, PRIVATE / "inventory")
    print(f"Inventoried {len(report['files'])} files at {source} (commit {report['source_commit'][:12]}).")
    (PRIVATE / "inventory" / "summary.md").write_text(summary(report), encoding="utf-8")
    if args.command == "backup":
        result = backup(source, report, args.output)
        print(json.dumps(result, indent=1))
        problems = verify(Path(result["archive"]))
        print("verified" if not problems else "\n".join(problems[:20]))
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
