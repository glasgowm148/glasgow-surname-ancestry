#!/usr/bin/env python3
"""Review tmp/ scratch space: what exists nowhere else, and preserve the research among it.

Every file under ``tmp/`` (except release-bundle archives, which are recorded by
size) is hashed and compared with every hash the project already holds: the
inventory of the repository and the research database's assets. Files found
nowhere else are classified:

* research notes (Markdown, text, CSV/TSV, wiki text, GEDCOM);
* structured research data (JSON);
* evidence (PDF and images);
* web captures (HTML), code and logs, and other files.

With ``--reference``, unique research notes, evidence and JSON are recorded
where they are, by hash, needing no disk space: a later clean-up shows up as
missing files in ``genealogy db check`` and the coverage ledger. With
``--preserve``, unique research notes and evidence up to 25 MB are copied into the database's managed, content-addressed
store and registered as private ``scratch_lead`` assets (one note per scratch
folder links them, marked unreviewed), so cleaning ``tmp/`` can no longer lose
them. Nothing in ``tmp/`` is changed or deleted. The full private report is
``data/private/workbench/scratch-review.json``.

    .venv/bin/python tools/workbench_scratch_review.py [--preserve]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys

from genealogy.store import Research, open_project, stable_id
from genealogy.store.assets import prepare_managed, register_asset

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "private" / "workbench" / "scratch-review.json"
KINDS = {
    "research notes": {".md", ".txt", ".csv", ".tsv", ".wiki", ".wikitext", ".ged", ".gedcom", ".rtf", ".docx"},
    "structured research data": {".json", ".ndjson", ".jsonl"},
    "evidence": {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".gif"},
    "web captures": {".html", ".htm", ".mhtml"},
    "code and logs": {".py", ".js", ".mjs", ".sh", ".log", ".css", ".swift"},
}
PRESERVE_LIMIT = {"research notes": 5_000_000, "evidence": 25_000_000}
# Kept as one compressed, hash-manifested archive each: too many files to hold one by one.
ARCHIVED = ("structured research data", "web captures", "code and logs")


def kind_of(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.name.endswith(".tar.gz") and "site" in path.name:
        return "site release snapshots"
    if suffix in {".index", ".dat", ".pyc", ".bin", ".used", ".restamp", ".ldb", ".sqlite-journal"} or \
            "/Cache" in path.as_posix() or "__pycache__" in path.as_posix():
        return "browser and tool caches"
    return next((kind for kind, suffixes in KINDS.items() if suffix in suffixes), "other")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def known_hashes(project) -> set[str]:
    known = {row["sha256"] for row in project.store.all("SELECT sha256 FROM asset")}
    inventory = ROOT / "data" / "private" / "workbench" / "inventory" / "inventory.json"
    if inventory.is_file():
        known |= {row["sha256"] for row in json.loads(inventory.read_text())["files"] if row.get("sha256")}
    return known


def review(project, scratch: Path) -> dict:
    known = known_hashes(project)
    unique: list[dict] = []
    totals: Counter = Counter()
    sizes: Counter = Counter()
    skipped: Counter = Counter()
    for dirpath, _, files in os.walk(scratch):
        for name in files:
            path = Path(dirpath) / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            relative = path.relative_to(scratch.parent).as_posix()
            if path.suffix.lower() == ".gz" and "bundle" in relative:
                skipped["release bundle archives (recorded by size only)"] += 1
                sizes["skipped bytes"] += size
                continue
            digest = sha256(path)
            kind = kind_of(path)
            totals[kind] += 1
            if digest in known:
                totals["already preserved elsewhere"] += 1
                continue
            known.add(digest)   # later copies of the same bytes are duplicates within tmp/
            unique.append({"path": relative, "sha256": digest, "bytes": size, "kind": kind,
                           "folder": relative.split("/")[1] if relative.count("/") > 1 else "(top level)"})
    by_kind: dict[str, dict] = defaultdict(lambda: {"files": 0, "bytes": 0})
    for row in unique:
        by_kind[row["kind"]]["files"] += 1
        by_kind[row["kind"]]["bytes"] += row["bytes"]
    return {"scratch": str(scratch), "files_by_kind": dict(totals), "skipped": dict(skipped),
            "skipped_bytes": sizes["skipped bytes"], "unique_by_kind": dict(by_kind), "unique": unique}


def preserve(project, report: dict) -> Counter:
    research = Research(project.store)
    counts: Counter = Counter()
    chosen = [row for row in report["unique"]
              if row["kind"] in PRESERVE_LIMIT and row["bytes"] <= PRESERVE_LIMIT[row["kind"]]]
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for row in chosen:
        by_folder[row["folder"]].append(row)
    for folder, rows in sorted(by_folder.items()):
        prepared = [(row, prepare_managed(project, ROOT / row["path"])) for row in rows]   # copies before the write
        with project.store.write(actor="scratch-review", tool="workbench_scratch_review",
                                 source=f"tmp/{folder}", reason="preserve unique scratch research before any clean-up") as tx:
            assets = []
            for row, ready in prepared:
                asset = register_asset(project, tx, ROOT / row["path"], kind="scratch_lead", access="private",
                                       prepared=ready, provenance=f"unique file in {row['path']}, reviewed "
                                       "by tools/workbench_scratch_review.py; not yet assessed as evidence")
                assets.append(asset["id"])
                counts[f"preserved: {row['kind']}"] += 1
            note_id = stable_id("not", "scratch-folder", folder)
            if not project.store.get("note", note_id):
                research.add_note(tx, id=note_id, kind="scratch_review", title=f"tmp/{folder}",
                                  text=f"{len(rows)} unique files from tmp/{folder} preserved unreviewed. They are "
                                       "leads, not evidence, until a researcher assesses them.",
                                  links=[(asset, "preserved_file") for asset in assets])
    return counts


REFERENCED = ("research notes", "evidence", "structured research data")


def reference(project, report: dict) -> Counter:
    """Register unique research files where they are, by hash: no copy, but a clean-up is detected.

    A referenced scratch file that later disappears or changes is reported by
    ``genealogy db check`` and the coverage ledger, so research cannot be lost
    from tmp/ silently. Use --preserve to copy them when the disk has room.
    """
    research = Research(project.store)
    counts: Counter = Counter()
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for row in report["unique"]:
        if row["kind"] in REFERENCED:
            by_folder[row["folder"]].append(row)
    for folder, rows in sorted(by_folder.items()):
        with project.store.write(actor="scratch-review", tool="workbench_scratch_review", source=f"tmp/{folder}",
                                 reason="record unique scratch research by hash before any clean-up") as tx:
            assets = []
            for row in rows:
                path = ROOT / row["path"]
                if not path.is_file():
                    counts["gone since the review"] += 1
                    continue
                asset = register_asset(project, tx, path, root="repository", kind="scratch_lead", access="private",
                                       provenance="unique file in tmp/, recorded by tools/workbench_scratch_review.py; "
                                                  "a lead, not yet assessed as evidence")
                assets.append(asset["id"])
                counts[f"referenced: {row['kind']}"] += 1
            note_id = stable_id("not", "scratch-folder", folder)
            if assets and not project.store.get("note", note_id):
                research.add_note(tx, id=note_id, kind="scratch_review", title=f"tmp/{folder}",
                                  text=f"{len(assets)} unique files in tmp/{folder} recorded by hash, unreviewed. "
                                       "They are leads, not evidence, until a researcher assesses them.",
                                  links=[(asset, "preserved_file") for asset in assets])
    return counts


def archive(project, report: dict, work: Path) -> Counter:
    """One verified tar.gz per bulk kind of unique files, registered as a private asset."""
    import tarfile
    counts: Counter = Counter()
    research = Research(project.store)
    for kind in ARCHIVED:
        rows = [row for row in report["unique"] if row["kind"] == kind]
        if not rows:
            continue
        name = "tmp-unique-" + kind.replace(" ", "-") + ".tar.gz"
        path = work / name
        manifest = {row["path"]: row["sha256"] for row in rows}
        with tarfile.open(path, "w:gz", compresslevel=6) as tar:
            for row in rows:
                tar.add(ROOT / row["path"], arcname=row["path"], recursive=False)
        expected = dict(manifest)
        with tarfile.open(path, "r:gz") as tar:   # verify every member before registering
            for member in tar:
                handle = tar.extractfile(member)
                digest = hashlib.sha256(handle.read()).hexdigest() if handle else None
                if expected.pop(member.name, None) != digest:
                    raise SystemExit(f"archive {name} did not verify at {member.name}")
        if expected:
            raise SystemExit(f"archive {name} is missing {len(expected)} files")
        manifest_path = work / (name + ".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        ready = [(item, prepare_managed(project, item)) for item in (path, manifest_path)]
        with project.store.write(actor="scratch-review", tool="workbench_scratch_review", source="tmp/",
                                 reason=f"archive {len(rows)} unique {kind} files from tmp/ before any clean-up") as tx:
            ids = [register_asset(project, tx, item, kind="scratch_archive", access="private", prepared=prep,
                                  provenance=f"{len(rows)} unique {kind} files from tmp/, verified member by member")["id"]
                   for item, prep in ready]
            note_id = stable_id("not", "scratch-archive", kind)
            if not project.store.get("note", note_id):
                research.add_note(tx, id=note_id, kind="scratch_review", title=f"tmp/ {kind}",
                                  text=f"{len(rows)} unique {kind} files from tmp/, archived unreviewed; the manifest "
                                       "lists each original path and SHA-256.",
                                  links=[(asset, "preserved_file") for asset in ids])
        counts[f"archived: {kind}"] = len(rows)
        counts[f"archive bytes: {kind}"] = path.stat().st_size
        path.unlink()
        manifest_path.unlink()
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--scratch", type=Path, default=ROOT / "tmp")
    parser.add_argument("--preserve", action="store_true", help="copy and register the unique research files")
    parser.add_argument("--archive", action="store_true", help="archive the unique bulk files (JSON, HTML, code, logs)")
    parser.add_argument("--reference", action="store_true",
                        help="record unique notes, evidence and JSON where they are, by hash (needs no disk space)")
    parser.add_argument("--work", type=Path, default=ROOT / "data" / "private" / "workbench" / "exports",
                        help="where archives are built before registration (removed afterwards)")
    args = parser.parse_args(argv)
    with open_project(args.project) as project:
        report = review(project, args.scratch.resolve())
        if args.reference:
            report["referenced"] = dict(reference(project, report))
        if args.preserve:
            report["preserved"] = dict(preserve(project, report))
        if args.archive:
            args.work.mkdir(parents=True, exist_ok=True)
            report["archived"] = dict(archive(project, report, args.work))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    summary = {key: report[key] for key in ("files_by_kind", "skipped", "unique_by_kind")}
    summary["referenced"] = report.get("referenced")
    summary["preserved"] = report.get("preserved")
    summary["archived"] = report.get("archived")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
