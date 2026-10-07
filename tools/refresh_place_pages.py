#!/usr/bin/env python3
"""Refresh the place pages in place, without the full catalogue build.

The place pages are written by ``build_research_catalog._write_place_pages``
as part of the full catalogue build, which regenerates every person page in an
older layout and is not run for routine updates (see
``docs/build-reproducibility.md``). This tool runs only the place writer, on
the published records index and people file, and puts each freshly written
``<main>`` into the page already on the site, keeping that page's shell
(navigation, styles, footer). A place with no page yet is reported, not
created: it needs the shell the full build and its repairs give it.

Usage:
    python tools/refresh_place_pages.py            # write
    python tools/refresh_place_pages.py --check    # report what would change, write nothing
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
EVIDENCE_CSS = '<link rel="stylesheet" href="/assets/research/evidence.css">'


def main_block(page: str) -> tuple[int, int]:
    """Start and end offsets of the page's ``<main>…</main>``, or (-1, -1)."""
    start, end = page.find("<main"), page.rfind("</main>")
    if start < 0 or end < start:
        return -1, -1
    return start, end + len("</main>")


def site_links(fragment: str) -> str:
    """Rewrite the writer's ``../`` links as root links, with clean catalogue URLs."""
    fragment = re.sub(r'((?:href|src)=")\.\./', r"\1/", fragment)
    return fragment.replace('href="/catalogue.html"', 'href="/catalogue/"')


def transplant(existing: str, fresh: str) -> str | None:
    """Return ``existing`` with its main replaced by the main of ``fresh``.

    ``None`` when either page has no main to work with.
    """
    old_start, old_end = main_block(existing)
    new_start, new_end = main_block(fresh)
    if old_start < 0 or new_start < 0:
        return None
    page = existing[:old_start] + site_links(fresh[new_start:new_end]) + existing[old_end:]
    description = re.search(r'<meta name="description" content="[^"]*">', fresh)
    if description:
        page = re.sub(r'<meta name="description" content="[^"]*"\s*/?>', lambda _m: description.group(0), page, count=1)
    if "ev-label-link" in page and "/assets/research/evidence.css" not in page:
        page = page.replace("</head>", EVIDENCE_CSS + "</head>", 1)
    return page


def render(site_root: Path, out: Path) -> int:
    """Run the place writer on the published data into ``out``; return the page count."""
    sys.path.insert(0, str(ROOT / "tools"))
    import build_research_catalog as catalogue

    records = json.loads((site_root / "data/records-index.json").read_text(encoding="utf-8"))
    people = json.loads((site_root / "data/people.json").read_text(encoding="utf-8"))["people"]
    for person in people:
        person.setdefault("catalogue_id", person.get("id"))
        for key in ("last_names_at_birth", "last_names_current", "profile_ids"):
            person.setdefault(key, [])
    known = {person["catalogue_id"] for person in people}
    records = [record for record in records if record.get("catalogue_id") in known]
    location_to_slug = {record["location_id"]: catalogue._slug(record["location_id"])
                        for record in records if record.get("location_id")}
    (out / "places").mkdir(parents=True, exist_ok=True)
    (out / "data").mkdir(parents=True, exist_ok=True)
    saved = catalogue.PLACES_DIR, catalogue.DATA_DIR
    catalogue.PLACES_DIR, catalogue.DATA_DIR = out / "places", out / "data"
    try:
        return len(catalogue._write_place_pages(records, people, location_to_slug))
    finally:
        catalogue.PLACES_DIR, catalogue.DATA_DIR = saved


def refresh(site_root: Path = WEB, *, write: bool = True) -> dict:
    counts = {"rendered": 0, "updated": 0, "unchanged": 0, "no_page_yet": [], "no_main": []}
    with tempfile.TemporaryDirectory() as scratch:
        out = Path(scratch)
        counts["rendered"] = render(site_root, out)
        for fresh_path in sorted((out / "places").glob("*.html")):
            target = site_root / "places" / fresh_path.name
            if not target.exists():
                counts["no_page_yet"].append(fresh_path.name)
                continue
            existing = target.read_text(encoding="utf-8")
            page = transplant(existing, fresh_path.read_text(encoding="utf-8"))
            if page is None:
                counts["no_main"].append(fresh_path.name)
            elif page == existing:
                counts["unchanged"] += 1
            else:
                counts["updated"] += 1
                if write:
                    target.write_text(page, encoding="utf-8")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report what would change and write nothing")
    args = parser.parse_args(argv)
    counts = refresh(write=not args.check)
    print(json.dumps(counts, indent=2))
    return int(bool(args.check and counts["updated"]))


if __name__ == "__main__":
    raise SystemExit(main())
