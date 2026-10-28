#!/usr/bin/env python3
"""Keep the vital events in the event index (``www/assets/research/event-index.json``) current.

The event index was last generated as a whole by a builder that is no longer
in the repository. Its personal rows (births and deaths, about nine in ten
rows) follow each person's dossier vitals, so they are produced here:

* a row whose dossier date, place or status changed is rewritten from the
  dossier, and a dossier vital with no row gets one;
* a row's country (the map colour group) is kept while its place is
  unchanged, and otherwise derived from the place;
* reviewed vitals (any basis other than ``imported_vital``) and the mention,
  research, unresolved and family rows are kept as they are until a later
  stage produces them; no row is deleted.

A dossier the privacy policy withholds contributes nothing. Run with
``--check`` to report what would change.

    .venv/bin/python tools/build_event_index.py [--check]
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT)]
import place_gazetteer  # noqa: E402

YEAR = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)")
GROUPS = (("scotland", r"\bscotland\b"), ("ireland", r"\bireland\b"), ("england", r"\bengland\b|\bwales\b"),
          ("america", r"\bunited states\b|\busa\b|\bu\.s\.a?\b"), ("canada", r"\bcanada\b"),
          ("oceania", r"\baustralia\b|\bnew zealand\b"))
US_STATES = {"alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
             "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
             "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
             "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
             "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
             "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia", "washington",
             "west virginia", "wisconsin", "wyoming"}
CANADA = {"ontario", "quebec", "new brunswick", "nova scotia", "manitoba", "british columbia", "alberta",
          "saskatchewan", "prince edward island", "newfoundland"}
IRELAND = {name.lower() for name in place_gazetteer.IRISH_COUNTY_NAMES} | {"belfast", "derry", "coleraine", "ballymena"}
SCOTLAND = {"aberdeenshire", "angus", "argyll", "ayrshire", "banffshire", "berwickshire", "caithness",
            "clackmannanshire", "dumfriesshire", "dunbartonshire", "east lothian", "fife", "inverness-shire",
            "kincardineshire", "kinross-shire", "lanarkshire", "midlothian", "morayshire", "orkney", "peeblesshire",
            "perthshire", "renfrewshire", "roxburghshire", "selkirkshire", "shetland", "stirlingshire", "sutherland",
            "west lothian", "wigtownshire", "edinburgh", "glasgow", "paisley", "greenock", "dundee", "aberdeen"}


def country(place: str | None) -> str:
    text = (place or "").lower()
    hits = [group for group, pattern in GROUPS if re.search(pattern, text)]
    if hits:
        return hits[-1]
    for part in reversed([part.strip() for part in re.split(r"[,;]", text)]):
        bare = re.sub(r"^county ", "", part)
        for names, group in ((US_STATES, "america"), (CANADA, "canada"), (IRELAND, "ireland"), (SCOTLAND, "scotland")):
            if bare in names or part in names:
                return group
    return "other"


def display(date):
    text = str(date or "")
    if match := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text):
        return f"{int(match[3])} {calendar.month_name[int(match[2])]} {match[1]}"
    if match := re.fullmatch(r"(\d{4})-(\d{2})", text):
        return f"{calendar.month_name[int(match[2])]} {match[1]}"
    return date


def year(date):
    match = YEAR.search(str(date or ""))
    return int(match[1]) if match else None


def vital_row(slug: str, dossier: dict, kind: str, vital: dict, previous: dict | None) -> dict:
    place = vital.get("place")
    same_place = previous is not None and previous.get("place") == place
    return {**(previous or {}), "p": slug, "person": dossier.get("name"), "research": False, "id": kind,
            "year": year(vital.get("date")), "date": display(vital.get("date")), "raw_date": vital.get("date"),
            "label": kind.title(), "event_type": kind, "kind": "personal", "role": "Subject",
            "participants": [{"id": dossier.get("id"), "role": "Subject"}], "place": place,
            "status": vital.get("status"), "basis": "imported_vital", "source_url": None, "note": "",
            "country": previous.get("country") if same_place else country(place)}


def build(web: Path, policy=None) -> tuple[list[dict] | None, Counter]:
    """Return (the new index, or None when unchanged, and counts); writes nothing."""
    path = web / "assets/research/event-index.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    position = {(row.get("p"), row.get("id")): index for index, row in enumerate(rows) if row.get("kind") == "personal"}
    counts: Counter = Counter()
    added: list[dict] = []
    updated = list(rows)
    for dossier_path in sorted((web / "people").glob("*.json")):
        if dossier_path.name.endswith(".network.json"):
            continue
        try:
            dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        slug = dossier_path.stem
        if not isinstance(dossier, dict) or dossier.get("likely_living") or dossier.get("withheld") \
                or (policy and slug in policy.blocked):
            continue
        for kind in ("birth", "death"):
            vital = (dossier.get("vitals") or {}).get(kind)
            if not isinstance(vital, dict) or not (vital.get("date") or vital.get("place")):
                continue
            index = position.get((slug, kind))
            if index is None:
                added.append(vital_row(slug, dossier, kind, vital, None))
                counts["vital rows added"] += 1
                continue
            row = rows[index]
            if row.get("basis") != "imported_vital":
                continue   # a reviewed vital is kept
            if (row.get("raw_date"), row.get("place"), row.get("status")) == (vital.get("date"), vital.get("place"), vital.get("status")):
                continue
            updated[index] = vital_row(slug, dossier, kind, vital, row)
            counts["vital rows updated"] += 1
    result = updated + added
    return (result if result != rows else None), counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--web", type=Path, default=ROOT / "www")
    parser.add_argument("--check", action="store_true", help="report what would change; write nothing")
    args = parser.parse_args(argv)
    try:
        from public_privacy import from_sources
        policy = from_sources(all_exports=True)
    except FileNotFoundError:
        policy = None
    result, counts = build(args.web, policy)
    if result is not None and not args.check:
        (args.web / "assets/research/event-index.json").write_text(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"written": bool(result is not None and not args.check), **dict(sorted(counts.items()))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
