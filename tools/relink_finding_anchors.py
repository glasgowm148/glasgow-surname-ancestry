#!/usr/bin/env python3
"""Point every link to a dated finding at the archive page that holds it.

Latest-findings archive pages are numbered from the earliest finding
(``tools/build_latest_findings.stable_page``), so a finding keeps its page.
Builders write those stable links. This pass corrects links in pages built
before that change, or by a builder that has not run since, without
rebuilding them. Links to findings not in the ledger are left alone and
reported. ``--check`` changes nothing and exits 1 when a link is out of date.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_latest_findings import page_urls  # noqa: E402

WEB = ROOT / "www"
LEDGER = ROOT / "research/latest-findings.json"
LINK = re.compile(r"/latest-findings/(?:page/\d+/)?#finding-([a-z0-9]+(?:-[a-z0-9]+)*)")
SUFFIXES = (".html", ".json", ".js")


def relink_text(text: str, urls: dict[str, str]) -> tuple[str, int, set[str]]:
    changed, unknown = 0, set()

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        target = urls.get(match[1])
        if target is None:
            unknown.add(match[1])
            return match[0]
        if target != match[0]:
            changed += 1
        return target

    return LINK.sub(replace, text), changed, unknown


def relink(web: Path = WEB, ledger: Path = LEDGER, *, write: bool = True) -> dict:
    urls = page_urls(json.loads(ledger.read_text(encoding="utf-8"))["findings"])
    counts: Counter[str] = Counter()
    unknown: set[str] = set()
    for directory, _, names in os.walk(web):
        for name in names:
            if not name.endswith(SUFFIXES):
                continue
            path = Path(directory) / name
            text = path.read_text(encoding="utf-8", errors="surrogateescape")
            if "#finding-" not in text:
                continue
            updated, changed, missing = relink_text(text, urls)
            unknown |= missing
            if changed:
                counts["files"] += 1
                counts["links"] += changed
                if write:
                    path.write_text(updated, encoding="utf-8", errors="surrogateescape")
    return {"files": counts["files"], "links": counts["links"], "unknown_findings": sorted(unknown)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report out-of-date links without changing files")
    parser.add_argument("--site", type=Path, default=WEB)
    args = parser.parse_args(argv)
    result = relink(args.site, write=not args.check)
    print(json.dumps(result))
    return 1 if args.check and result["links"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
