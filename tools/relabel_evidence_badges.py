#!/usr/bin/env python3
"""Reword and link evidence badges on already-built pages (place pages by default).

``_evidence_badge`` in ``tools/build_research_catalog.py`` now prints every badge
through ``evidence_labels.label_html``. This script applies the same wording
and guide link to pages built before that change, so the coordinator can update
them without a full catalogue build. The next full build produces the same
markup. Idempotent: badges that already contain a link are left alone.

Usage: tools/relabel_evidence_badges.py [--dry-run] [folder ...]   (default: www/places)
"""
from __future__ import annotations

from collections import Counter
from html import escape, unescape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import evidence_labels as ev  # noqa: E402

BADGE = re.compile(r'<span class="(evidence-badge evidence-[^"]*)">((?:(?!</span>|<a\b).)*)</span>', re.S)


def relabel(page: str) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match) -> str:
        nonlocal count
        info = ev.describe(unescape(match[2]))
        count += 1
        return (f'<span class="{match[1]}"><a class="ev-label-link" href="{escape(str(info["url"]), quote=True)}" '
                f'title="{escape(str(info["meaning"]), quote=True)}">{escape(str(info["text"]))}</a></span>')

    return BADGE.sub(replace, page), count


def run(folders, dry_run: bool = False) -> dict[str, int]:
    counts = Counter()
    for folder in folders:
        for path in sorted(Path(folder).glob("*.html")):
            before = path.read_text(encoding="utf-8")
            after, badges = relabel(before)
            if after != before:
                counts["pages"] += 1
                counts["badges"] += badges
                if not dry_run:
                    path.write_text(after, encoding="utf-8")
    return dict(counts)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    print(json.dumps(run(args or [ROOT / "www/places"], dry_run="--dry-run" in sys.argv)))
