#!/usr/bin/env python3
"""Clean tmp/ scratch space, deleting only what is checked to be disposable.

Every candidate is re-checked at run time; a dry run is the default. Classes
deleted with ``--delete``:

* **duplicate**: the same bytes exist outside ``tmp/`` now (a repository file
  from the inventory, re-hashed, or a managed asset), so nothing is lost;
* **cache**: browser and tool caches;
* **staged site copy**: HTML of an earlier build output kept under a
  ``staged/``, ``site-snapshot/`` or ``www/`` folder, except in the newest such
  scratch folder, which is kept whole as a record of an earlier site state;
* **older release bundle**: release archives and site snapshots except the
  newest, and only if the newest release in ``dist/`` passes a gzip check.

Never deleted: any file the research database references (a ``scratch_lead``
or any other asset), research notes, evidence, JSON data, code and logs, and
anything not in a class above. Every deletion is listed with its SHA-256 in
the private report ``data/private/workbench/tmp-cleanup.json``.

    .venv/bin/python tools/workbench_tmp_cleanup.py [--delete]
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import sys

from genealogy.store import open_project

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workbench_scratch_review import kind_of, sha256  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "private" / "workbench" / "tmp-cleanup.json"
INVENTORY = ROOT / "data" / "private" / "workbench" / "inventory" / "inventory.json"
STAGED = {"staged", "site-snapshot", "www"}


def is_bundle(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return (name.endswith(".gz") and "bundle" in relative) or (name.endswith(".tar.gz") and "site" in name)


def gzip_ok(path: Path) -> bool:
    try:
        with gzip.open(path, "rb") as handle:
            while handle.read(1 << 24):
                pass
        return True
    except (OSError, EOFError):
        return False


class Elsewhere:
    """Bytes held outside tmp/: inventory files (re-hashed when used) and managed assets."""

    def __init__(self, project) -> None:
        self.by_hash: dict[str, list[Path]] = {}
        if INVENTORY.is_file():
            for row in json.loads(INVENTORY.read_text())["files"]:
                path = row.get("path") or ""
                if row.get("sha256") and path and not path.startswith(("tmp/", "data/private/workbench/")):
                    self.by_hash.setdefault(row["sha256"], []).append(ROOT / path)
        managed = project.root("managed")
        for asset in project.store.all("SELECT sha256, path FROM asset WHERE root='managed'"):
            self.by_hash.setdefault(asset["sha256"], []).append(managed / asset["path"])
        self.checked: dict[Path, str | None] = {}

    def holds(self, digest: str) -> Path | None:
        for path in self.by_hash.get(digest, []):
            if path not in self.checked:
                self.checked[path] = sha256(path) if path.is_file() else None
            if self.checked[path] == digest:
                return path
        return None


def plan(project, scratch: Path) -> tuple[list[dict], Counter]:
    referenced = {row["path"] for row in project.store.all(
        "SELECT path FROM asset WHERE root='repository' AND path LIKE 'tmp/%'")}
    elsewhere = Elsewhere(project)
    files = []
    for dirpath, _, names in os.walk(scratch):
        for name in names:
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            files.append(path)
    staged_folders = {p.relative_to(scratch).parts[0] for p in files
                      if STAGED & set(p.relative_to(scratch).parts[1:-1]) and len(p.relative_to(scratch).parts) > 2}
    newest_staged = max(staged_folders, key=lambda f: (scratch / f).stat().st_mtime, default=None)
    bundles = sorted((p for p in files if is_bundle(p.relative_to(scratch.parent).as_posix())),
                     key=lambda p: p.stat().st_mtime)
    releases = sorted((ROOT / "dist").glob("glasgow-site-*.tar.gz"), key=lambda p: p.stat().st_mtime)
    release_ok = bool(releases) and gzip_ok(releases[-1])
    deletions, counts = [], Counter()
    for path in files:
        relative = path.relative_to(scratch.parent).as_posix()
        parts = path.relative_to(scratch).parts
        if relative in referenced:
            counts["kept: referenced by the research database"] += 1
            continue
        if is_bundle(relative):
            if path == bundles[-1] or not release_ok:
                counts["kept: newest release bundle, or dist/ release not verified"] += 1
                continue
            cls = "older release bundle"
            digest = None
        else:
            digest = sha256(path)
            kind = kind_of(path)
            if elsewhere.holds(digest):
                cls = "duplicate"
            elif kind == "browser and tool caches":
                cls = "cache"
            elif (kind == "web captures" and len(parts) > 2 and STAGED & set(parts[1:-1])
                  and parts[0] != newest_staged):
                cls = "staged site copy"
            else:
                counts[f"kept: {kind}"] += 1
                continue
        size = path.stat().st_size
        deletions.append({"path": relative, "class": cls, "bytes": size, "sha256": digest})
        counts[f"delete: {cls}"] += 1
        counts[f"bytes: {cls}"] += size
    counts["newest staged folder kept"] = newest_staged or ""
    counts["dist release verified"] = str(release_ok)
    return deletions, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--scratch", type=Path, default=ROOT / "tmp")
    parser.add_argument("--delete", action="store_true", help="delete the planned files (default: report only)")
    args = parser.parse_args(argv)
    scratch = args.scratch.resolve()
    with open_project(args.project) as project:
        deletions, counts = plan(project, scratch)
    deleted = 0
    if args.delete:
        for row in deletions:
            path = scratch.parent / row["path"]
            if row["sha256"] and sha256(path) != row["sha256"]:
                row["skipped"] = "changed since planning"
                continue
            path.unlink()
            row["deleted"] = True
            deleted += 1
        for dirpath, dirnames, filenames in os.walk(scratch, topdown=False):
            if Path(dirpath) != scratch and not os.listdir(dirpath):
                os.rmdir(dirpath)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"deleted": deleted, "counts": counts, "files": deletions}, indent=1) + "\n",
                      encoding="utf-8")
    print(json.dumps({"deleted": deleted, "counts": dict(sorted(counts.items(), key=lambda i: str(i[0])))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
