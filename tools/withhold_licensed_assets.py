#!/usr/bin/env python3
"""Preserve approved transcription assets and withhold other licensed scans."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

try:
    from public_manuscript_previews import approved_preview, audit_approved_previews, restore_approved_previews
except ModuleNotFoundError:
    from tools.public_manuscript_previews import approved_preview, audit_approved_previews, restore_approved_previews


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
PRIVATE = ROOT / "data" / "private" / "withheld-public-assets"
LICENSED_PATHS = (
    Path("assets/research/testament-originals"),
    Path("assets/research/testament-crops"),
    Path("assets/research/record-excerpts"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def withhold(web: Path = WEB, private: Path = PRIVATE) -> int:
    """Restore approved material and preserve unapproved assets privately."""
    restore_approved_previews(web, private)
    moved = 0
    for relative in LICENSED_PATHS:
        source = web / relative
        if not source.exists():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            url = "/" + path.relative_to(web).as_posix()
            if approved_preview(url, web, private):
                continue
            destination = private / relative / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if digest(destination) != digest(path):
                    raise ValueError(f"withheld asset differs from public copy: {relative / path.relative_to(source)}")
                path.unlink()
            else:
                shutil.move(str(path), str(destination))
            moved += 1
        if not any(source.rglob("*")):
            source.rmdir()
    return moved


def audit(web: Path = WEB, private: Path = PRIVATE) -> list[str]:
    failures = audit_approved_previews(web, private)
    for relative in LICENSED_PATHS:
        public = web / relative
        if public.exists():
            for path in public.rglob("*"):
                if path.is_file() and not approved_preview("/" + path.relative_to(web).as_posix(), web, private):
                    failures.append(f"public licensed assets remain: {path.relative_to(web)}")
        if not any(path.is_file() for path in (private / relative).rglob("*")):
            failures.append(f"withheld assets missing: {relative}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify assets are withheld")
    args = parser.parse_args()
    if args.check:
        failures = audit()
        for failure in failures:
            print(f"FAIL {failure}")
        return int(bool(failures))
    print(f"withheld assets: {withhold()}")
    failures = audit()
    for failure in failures:
        print(f"FAIL {failure}")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
