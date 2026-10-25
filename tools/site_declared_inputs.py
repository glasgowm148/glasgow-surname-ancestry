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


def check(root: Path) -> list[str]:
    return [f"{item['published']} differs from its declared input" for item in entries(root)
            if not (root / item["published"]).is_file() or sha256(root / item["published"]) != item["sha256"]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--adopt", action="store_true")
    mode.add_argument("--install", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.check:
        problems = check(args.root)
        print("\n".join(problems) if problems else f"www/ holds every declared site input ({len(DECLARED)}).")
        return 1 if problems else 0
    lines = adopt(args.root) if args.adopt else install(args.root)
    print("\n".join(lines) or "nothing to do: every declared input is in place")
    return 0


if __name__ == "__main__":
    sys.exit(main())
