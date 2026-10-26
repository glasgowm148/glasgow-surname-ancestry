#!/usr/bin/env python3
"""Declared inputs the Glasgow site needs that no builder produces.

Some files the published site serves were only ever kept inside ``www/`` (an
output directory), so a build from an empty ``www/`` would lose them. Each is
declared here with a home outside the output and its SHA-256 in the tracked
manifest ``data/site/declared-inputs.json``:

    --adopt    move today's copies into their declared home (refuses to overwrite a
               different file) and record their hashes
    --install  copy every declared input into www/, verifying each hash first; a
               missing or changed input stops the build with its name
    --check    report whether www/ holds exactly the declared bytes
    --declare-state PATH...  record www/ files the build reads before writing them
               (build state) with a private home in data/private/site-state/
               (--declare-state-from FILE reads the paths from a file)
    --save-state  after a successful build, carry the state forward to its homes

``--install`` also seeds every declared state file that www/ lacks, without
overwriting one already there, so a build can start from an empty www/.

The homes are private (``data/private/site-inputs/``) because these files'
publication beyond the live site has not been reviewed; they are preserved by the
workbench backups and referenced by hash in the research database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "site" / "declared-inputs.json"
HOME = "data/private/site-inputs"
DECLARED = (   # (published path inside www/, why it is an input)
    ("map/data/early-bearers.json", "map layer of early surname bearers; no builder writes it"),
    ("map/data/ydna-timeline.json", "Y-DNA timeline layer for the map; no builder writes it"),
    ("map/data/recent-profile-supplement.json", "recently added profiles shown on the map; no builder writes it"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def adopt(root: Path) -> list[str]:
    manifest = {"note": "Inputs the site serves that no builder produces; see tools/site_declared_inputs.py.",
                "inputs": []}
    lines = []
    for published, why in DECLARED:
        target, home = root / "www" / published, root / HOME / published
        if not target.is_file() and not home.is_file():
            raise SystemExit(f"declared input {published} exists neither in www/ nor in {HOME}/")
        if home.is_file() and target.is_file() and sha256(home) != sha256(target):
            raise SystemExit(f"{HOME}/{published} differs from www/{published}; resolve which is current first")
        if not home.is_file():
            home.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, home)
            lines.append(f"adopted www/{published} -> {HOME}/{published}")
        manifest["inputs"].append({"published": f"www/{published}", "source": f"{HOME}/{published}",
                                   "sha256": sha256(home), "why": why})
    (root / MANIFEST.relative_to(ROOT)).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return lines


def entries(root: Path) -> list[dict]:
    path = root / MANIFEST.relative_to(ROOT)
    if not path.is_file():
        raise SystemExit(f"{path} is missing; run --adopt on a checkout that has the site's inputs")
    return json.loads(path.read_text(encoding="utf-8"))["inputs"]


def install(root: Path) -> list[str]:
    lines, missing = [], []
    for item in entries(root):
        source = root / item["source"]
        if not source.is_file():
            missing.append(f"{item['source']} (for {item['published']}) is missing")
            continue
        if sha256(source) != item["sha256"]:
            missing.append(f"{item['source']} changed since it was declared; review it and re-run --adopt")
            continue
        target = root / item["published"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or sha256(target) != item["sha256"]:
            shutil.copy2(source, target)
            lines.append(f"installed {item['published']}")
    if missing:
        raise SystemExit("declared site inputs not available, the build would be incomplete:\n  " + "\n  ".join(missing))
    return lines


# Private like the homes: about 28,000 entries that change with every build.
STATE_MANIFEST = ROOT / "data" / "private" / "site-state" / "manifest.json"
STATE_HOME = "data/private/site-state/www"


def state_entries(root: Path) -> list[dict]:
    path = root / STATE_MANIFEST.relative_to(ROOT)
    return json.loads(path.read_text(encoding="utf-8"))["state"] if path.is_file() else []


def write_state(root: Path, rows: list[dict]) -> None:
    payload = {"note": "Files the build reads from www/ before (or without) writing them: carried between builds, "
                       "installed when absent, saved after a successful build. See tools/site_declared_inputs.py.",
               "state": sorted(rows, key=lambda row: row["published"])}
    (root / STATE_MANIFEST.relative_to(ROOT)).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def declare_state(root: Path, published: list[str], why: str) -> list[str]:
    """Record www/ files as build state, with a private home holding today's bytes."""
    rows = {row["published"]: row for row in state_entries(root)}
    lines = []
    for relative in published:
        target = root / "www" / relative
        if not target.is_file():
            raise SystemExit(f"www/{relative} does not exist; nothing to declare")
        home = root / STATE_HOME / relative
        home.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, home)
        rows[f"www/{relative}"] = {"published": f"www/{relative}", "source": f"{STATE_HOME}/{relative}",
                                   "sha256": sha256(home), "why": why}
        lines.append(f"declared www/{relative}")
    write_state(root, list(rows.values()))
    return lines


def install_state(root: Path) -> list[str]:
    """Give www/ every state file it lacks; never overwrite one the build already has."""
    lines, missing = [], []
    for item in state_entries(root):
        target, source = root / item["published"], root / item["source"]
        if target.is_file():
            continue
        if not source.is_file():
            missing.append(f"{item['source']} (for {item['published']}) is missing")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        lines.append(f"seeded {item['published']}")
    if missing:
        raise SystemExit("declared site state not available, the build would be incomplete:\n  " + "\n  ".join(missing))
    return lines


def save_state(root: Path) -> list[str]:
    """After a successful build, carry the current state forward to its home."""
    rows, lines = state_entries(root), []
    for item in rows:
        target, home = root / item["published"], root / item["source"]
        if not target.is_file():
            raise SystemExit(f"{item['published']} is missing after the build; state not saved")
        digest = sha256(target)
        if digest != item["sha256"] or not home.is_file():
            home.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, home)
            item["sha256"] = digest
            lines.append(f"saved {item['published']}")
    write_state(root, rows)
    return lines


def check(root: Path) -> list[str]:
    problems = [f"{item['published']} differs from its declared input" for item in entries(root)
                if not (root / item["published"]).is_file() or sha256(root / item["published"]) != item["sha256"]]
    problems += [f"{item['source']} (home of {item['published']}) is missing" for item in state_entries(root)
                 if not (root / item["source"]).is_file()]
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--adopt", action="store_true")
    mode.add_argument("--install", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--declare-state", nargs="+", metavar="WWW_PATH",
                      help="record these www/ files (paths inside www/) as build state")
    mode.add_argument("--declare-state-from", type=Path, metavar="FILE",
                      help="as --declare-state, reading one path per line from FILE")
    mode.add_argument("--save-state", action="store_true", help="after a successful build, save state to its homes")
    parser.add_argument("--why", default="read by the build before any builder writes it")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.check:
        problems = check(args.root)
        print("\n".join(problems) if problems else
              f"www/ holds every declared site input ({len(DECLARED)}); {len(state_entries(args.root))} state files have homes.")
        return 1 if problems else 0
    if args.declare_state or args.declare_state_from:
        paths = args.declare_state or [line.strip() for line in args.declare_state_from.read_text().splitlines()
                                       if line.strip()]
        lines = declare_state(args.root, paths, args.why)
        lines = lines if len(lines) <= 20 else [f"declared {len(lines)} state files"]
    elif args.save_state:
        lines = save_state(args.root)
    elif args.adopt:
        lines = adopt(args.root)
    else:
        lines = install(args.root) + install_state(args.root)
    print("\n".join(lines) or "nothing to do: every declared input is in place")
    return 0


if __name__ == "__main__":
    sys.exit(main())
