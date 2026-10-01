#!/usr/bin/env python3
"""Refresh the comparison data asset from already-public dossier JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from build_research_catalog import write_comparison_index
    from public_privacy import from_sources
except ModuleNotFoundError:
    from tools.build_research_catalog import write_comparison_index
    from tools.public_privacy import from_sources


ROOT = Path(__file__).resolve().parents[1]


def _public_dossiers(root: Path) -> dict[str, dict]:
    dossiers = {}
    for path in sorted((root / "www" / "people").glob("*.json")):
        if path.name.endswith(".network.json"):
            continue
        dossier = json.loads(path.read_text(encoding="utf-8"))
        if dossier.get("id") and dossier.get("catalogue_id") and dossier.get("name"):
            dossiers[dossier["catalogue_id"]] = dossier
    return dossiers


def refresh(root: Path = ROOT) -> tuple[int, int]:
    audit_path = root / "data" / "wikitree" / "catalogue-profile-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    policy = from_sources()
    return write_comparison_index(
        _public_dossiers(root), audit.get("entries", {}),
        output=root / "www" / "data" / "compare-index.js", privacy=policy,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    index_count, dossier_count = refresh(args.root.resolve())
    print(f"comparison index refreshed: {index_count} people, {dossier_count} dossiers")


if __name__ == "__main__":
    main()
