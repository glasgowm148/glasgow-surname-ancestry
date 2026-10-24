#!/usr/bin/env python3
"""Stamp local CSS, JavaScript and JSON query versions from their content hashes."""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


VERSIONED_ASSET = re.compile(
    r"(?P<quote>[\"'])(?P<url>(?:/|\.{1,2}/)?[^\"'()\s?#]+\.(?:css|js|json))"
    r"\?v=(?P<version>[^\"'&()\s#]+)(?P=quote)"
)
SOURCE_SUFFIXES = {".html", ".js"}


@dataclass(frozen=True)
class Mismatch:
    source: Path
    url: str
    actual: str
    expected: str


def asset_path(site_root: Path, source: Path, url: str, cache: dict | None = None) -> Path | None:
    """Resolve a site-local URL, refusing paths outside the site root."""
    candidate = site_root / url.lstrip("/") if url.startswith("/") else source.parent / url
    if cache is not None and candidate in cache:return cache[candidate]
    try:
        resolved = candidate.resolve()
        resolved.relative_to(site_root.resolve())
        if cache is not None:cache[candidate]=resolved
        return resolved
    except ValueError:
        if cache is not None:cache[candidate]=None
        return None


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()[:10]


def _scan(site_root: Path, *, graph: bool = True):
    """Stream source contents; retain hashes and compact references, never text."""
    sources = sorted(path for path in site_root.rglob("*")
                     if path.suffix in SOURCE_SUFFIXES and path.is_file())
    targets, hashes, mismatches = {}, {}, []
    resolved_assets = {}
    for source in sources:
        data = source.read_bytes()
        hashes[source.resolve()] = hashlib.sha256(data).hexdigest()[:10]
        text = data.decode("utf-8")
        del data
        refs = []
        for match in VERSIONED_ASSET.finditer(text):
            url = match.group("url")
            target = asset_path(site_root, source, url, resolved_assets)
            if target is None or not target.is_file():
                continue
            if target not in hashes:
                hashes[target] = content_hash(target)
            actual, expected = match.group("version"), hashes[target]
            if actual != expected:
                mismatches.append(Mismatch(source, url, actual, expected))
            if graph:
                # Match objects retain their complete source string: store only
                # these small values so the source can be released immediately.
                refs.append((url, target))
        match = None  # A regex match otherwise keeps the last source alive.
        del text
        if graph:
            targets[source] = refs
    return sources, targets, hashes, mismatches


def find_mismatches(site_root: Path) -> list[Mismatch]:
    return _scan(site_root, graph=False)[-1]


def stamp(site_root: Path, write: bool) -> tuple[int, int]:
    """Return (changed sources, original stale references).

    Write dependencies before consumers, so an acyclic asset chain settles in
    one pass. Cycles cannot be assigned stable content hashes by this method;
    reject them before writing anything and leave the check failure visible.
    """
    sources, targets, hashes, mismatches = _scan(site_root, graph=write)
    if not write:
        return len({m.source for m in mismatches}), len(mismatches)

    by_resolved = {source.resolve(): source for source in sources}
    dependencies = {source: {by_resolved[target] for _, target in refs
                             if target in by_resolved}
                    for source, refs in targets.items()}
    consumers = {source: [] for source in sources}
    for source, deps in dependencies.items():
        for dependency in deps:
            consumers[dependency].append(source)
    # Kahn ordering avoids recursion limits for long generated JS chains.
    pending = [source for source, deps in dependencies.items() if not deps]
    counts = {source: len(deps) for source, deps in dependencies.items()}
    order = []
    while pending:
        source = pending.pop()
        order.append(source)
        for consumer in consumers[source]:
            counts[consumer] -= 1
            if not counts[consumer]:
                pending.append(consumer)
    if len(order) != len(sources):
        blocked = sorted(str(source.relative_to(site_root)) for source, count in counts.items() if count)
        raise ValueError("Cyclic versioned asset dependencies (including blocked consumers): "
                         + ", ".join(blocked[:10]))

    changed = 0
    for source in order:
        original = source.read_bytes()
        text = original.decode("utf-8")
        versions = {url: hashes[target] for url, target in targets[source]}

        def replace(match):
            expected = versions.get(match.group("url"))
            if expected is None:
                return match.group(0)
            return (match.string[match.start():match.start("version")] + expected
                    + match.string[match.end("version"):match.end()])

        final = VERSIONED_ASSET.sub(replace, text).encode("utf-8")
        if final != original:
            source.write_bytes(final)
            changed += 1
        hashes[source.resolve()] = hashlib.sha256(final).hexdigest()[:10]
        # Bound retained content to one source even across loop iterations.
        del original, text, final
    return changed, len(mismatches)


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
