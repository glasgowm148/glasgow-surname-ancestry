#!/usr/bin/env python3
"""Keep the URLs of retired record subjects usable: each redirects to its survivor.

A record-defined subject (``record-…``) retired into an existing person has no
page of its own once the catalogue is rebuilt. Its old URL redirects to the
person it became, like the WikiTree merge aliases
(``publish_wikitree_redirect_aliases.py``). The survivors come from the research
itself, never from guesses:

* ``retired_catalogue_id`` decisions in research JSON, with the person in
  ``canonical_profile_id``, ``existing_profile_id`` or ``profile_id``;
* catalogue-profile links (``research/<Person>/catalogue-profile-link.json``
  with ``catalogue_id`` and ``wikitree_id``);
* Findmypast drafts kept in a person's research folder
  (``research/<Person>/*.md`` containing ``BEGIN FMP-GLASGOW-fmp-glasgow-<id>``);
* the superseded 1577 Andrew reading (``reconcile_retired_record_subjects.py``).

Only URLs that were published are kept: those listed in
``data/site/retired-record-urls.json`` and any retired subject whose page exists
when this runs. A page the catalogue currently makes is never replaced, and
nothing is written unless the survivor's page exists.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = Path("data/site/retired-record-urls.json")
SKIP = ("gray-backup", "/backups/", "/before/")
DRAFT = re.compile(r"BEGIN FMP-GLASGOW-fmp-glasgow-([0-9a-f]{12})")
PERSON = re.compile(r"[A-Z][A-Za-z'_-]+-\d+")


def _decisions(value):
    if isinstance(value, dict):
        if "retired_catalogue_id" in value:
            yield value
        for item in value.values():
            yield from _decisions(item)
    elif isinstance(value, list):
        for item in value:
            yield from _decisions(item)


def retired_subjects(root: Path = ROOT) -> dict[str, str]:
    """Retired record subject id -> the WikiTree id of the person it became."""
    found: dict[str, str] = {}
    for path in sorted((root / "research").rglob("*.json")):
        if any(part in path.as_posix() for part in SKIP):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for decision in _decisions(data):
            survivor = (decision.get("canonical_profile_id") or decision.get("existing_profile_id")
                        or decision.get("profile_id"))
            if isinstance(survivor, str) and PERSON.fullmatch(survivor):
                found.setdefault(str(decision["retired_catalogue_id"]), survivor)
    for path in sorted((root / "research").glob("*/catalogue-profile-link.json")):
        try:
            link = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(link.get("catalogue_id", "")).startswith("record-") and PERSON.fullmatch(str(link.get("wikitree_id", ""))):
            found.setdefault(link["catalogue_id"], link["wikitree_id"])
    for path in sorted((root / "research").glob("*/*.md")):
        if not PERSON.fullmatch(path.parent.name):
            continue
        for match in DRAFT.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            found.setdefault(f"record-fmp-glasgow-{match[1]}", path.parent.name)
    try:
        from reconcile_retired_record_subjects import OLD, PROFILE
    except ModuleNotFoundError:
        from tools.reconcile_retired_record_subjects import OLD, PROFILE
    found.setdefault(OLD, PROFILE)
    return found


def redirect_page(old: str, new: str) -> str:
    href = f"{new.lower()}.html"
    canonical = f"https://glasgow.phenotype.dev/people/{href}"
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{escape(old)} is now part of {escape(new)}</title>"
        f"<link rel=\"canonical\" href=\"{escape(canonical, quote=True)}\">"
        f"<meta http-equiv=\"refresh\" content=\"0; url={escape(href, quote=True)}\">"
        "</head><body><main>"
        f"<h1>This record subject is now part of {escape(new)}</h1><p>The research on this record is in "
        f"<a href=\"{escape(href, quote=True)}\">{escape(new)}</a>'s account.</p>"
        "</main></body></html>\n"
    )


def publish(root: Path = ROOT) -> int:
    site = root / "www" / "people"
    people = root / "www" / "data" / "people.json"
    current = {row.get("catalogue_id") for row in json.loads(people.read_text(encoding="utf-8"))["people"]} \
        if people.is_file() else set()
    listed = root / PUBLISHED
    published = set(json.loads(listed.read_text(encoding="utf-8"))["published"]) if listed.is_file() else set()
    written = 0
    for old, new in sorted(retired_subjects(root).items()):
        if old in current or not (site / f"{new.lower()}.html").is_file():
            continue
        if old not in published and not (site / f"{old}.html").is_file():
            continue   # never had a public URL: nothing to keep
        page = redirect_page(old, new)
        alias = site / f"{old}.html"
        if not alias.exists() or alias.read_text(encoding="utf-8") != page:
            alias.write_text(page, encoding="utf-8")
            written += 1
    return written


if __name__ == "__main__":
    print(f"Published {publish()} retired record redirect page(s).")
