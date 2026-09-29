#!/usr/bin/env python3
"""Stamp local CSS and JavaScript query versions from their content hashes."""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


VERSIONED_ASSET = re.compile(
    r"(?P<quote>[\"'])(?P<url>(?:/|\.{1,2}/)?[^\"'()\s?#]+\.(?:css|js))"
    r"\?v=(?P<version>[^\"'&()\s#]+)(?P=quote)"
)
SOURCE_SUFFIXES = {".html", ".js"}


@dataclass(frozen=True)
class Mismatch:
    source: Path
    url: str
    actual: str
    expected: str


def asset_path(site_root: Path, source: Path, url: str) -> Path | None:
    """Resolve a site-local URL, refusing paths outside the site root."""
    candidate = site_root / url.lstrip("/") if url.startswith("/") else source.parent / url
    try:
        resolved = candidate.resolve()
        resolved.relative_to(site_root.resolve())
        return resolved
    except ValueError:
        return None


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def find_mismatches(site_root: Path) -> list[Mismatch]:
    mismatches: list[Mismatch] = []
    hashes: dict[Path, str] = {}
    for source in sorted(path for path in site_root.rglob("*") if path.suffix in SOURCE_SUFFIXES):
        text = source.read_text(encoding="utf-8")
        for match in VERSIONED_ASSET.finditer(text):
            url = match.group("url")
            target = asset_path(site_root, source, url)
            if target is None or not target.is_file():
                continue
            if target not in hashes:
                hashes[target] = content_hash(target)
            expected = hashes[target]
            actual = match.group("version")
            if actual != expected:
                mismatches.append(Mismatch(source, url, actual, expected))
    return mismatches


def stamp(site_root: Path, write: bool) -> tuple[int, int]:
    """Return (changed sources, mismatched references); optionally update sources."""
    mismatches = find_mismatches(site_root)
    by_source: dict[Path, list[Mismatch]] = {}
    for mismatch in mismatches:
        by_source.setdefault(mismatch.source, []).append(mismatch)
    if write:
        for source in by_source:
            original = source.read_text(encoding="utf-8")

            def replace(match: re.Match[str]) -> str:
                target = asset_path(site_root, source, match.group("url"))
                if target is None or not target.is_file():
                    return match.group(0)
                return f"{match.group('quote')}{match.group('url')}?v={content_hash(target)}{match.group('quote')}"

            source.write_text(VERSIONED_ASSET.sub(replace, original), encoding="utf-8")
    return len(by_source), len(mismatches)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report stale versions")
    mode.add_argument("--write", action="store_true", help="replace stale versions")
    parser.add_argument("site_root", type=Path, nargs="?", default=Path(__file__).parents[1] / "www")
    args = parser.parse_args()
    site_root = args.site_root.resolve()
    if args.check:
        mismatches = find_mismatches(site_root)
        sources = sorted({mismatch.source.relative_to(site_root) for mismatch in mismatches})
        for source in sources:
            print(f"stale: {source}")
        print(f"{len(sources)} files with stale versions; {len(mismatches)} stale references")
        return 1 if mismatches else 0
    changed, references = stamp(site_root, args.write)
    print(f"updated {changed} files; {references} version references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
