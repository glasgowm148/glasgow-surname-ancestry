#!/usr/bin/env python3
"""Retire only the superseded 1577 Andrew subject; dry run unless --write.

No catalogue rebuild, API calls or live publication. --write saves byte-for-byte
backups; --restore BACKUP restores the previous local files.
"""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
try:
    from site_analytics import with_analytics
except ModuleNotFoundError:
    from tools.site_analytics import with_analytics
try:
    from site_identity import page_title
except ModuleNotFoundError:
    from tools.site_identity import page_title

ROOT = Path(__file__).resolve().parents[1]
OLD = "record-edinburgh-1577-andrew-glasgow"
PROFILE = "Glasgow-3589"
CURRENT = "glasgow-3589"
NAME = "Marjory Glasgow"
DISPLAY_NAME = "Marjorie Glasgow"  # Current checked profile; record reading remains Marjory.
SOURCE = "National Records of Scotland, John Glasgow testament dative, CC8/8/5 images 276-277"
OLD_SOURCE = SOURCE + ": second child [Androw?]"
NEW_SOURCE = SOURCE + ": Marjory Glasgow"
REASON = ("The earlier Androw/Andrew reading is superseded by the accepted human "
          "reading m[ar]iory (Marjory). This is John Glasgow's lawful daughter, "
          "already represented by Glasgow-3589, not a separate Andrew.")
NOTE = ("Accepted human reading: Marjory, lawful child and executor-dative of John "
        "Glasgow. The earlier Androw/Andrew reading and profile-creation conclusion "
        "are superseded; existing profile Glasgow-3589 represents this child. "
        "The testament establishes neither her birth date nor her birthplace.")


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def obsolete(row):
    return row.get("catalogue_id", row.get("id")) == OLD or row.get("id") == OLD


def public_subject(row, slug, profile=None):
    """Exact public identity/URL checks; never search imported prose for names."""
    identities = {slug, profile or slug}
    if any(row.get(key) in identities for key in ("id", "selection_id", "slug", "catalogue_id")):
        return True
    return row.get("url") in {
        f"/people/{slug}.html", f"https://glasgow.phenotype.dev/people/{slug}.html"}


def reconcile_registry(rows):
    result = []
    for row in rows:
        if public_subject(row, OLD):
            continue
        if public_subject(row, CURRENT, PROFILE):
            previous = row.get("name")
            row["name"] = DISPLAY_NAME
            # This is generated search text for this exact person, not evidence.
            if previous and isinstance(row.get("search"), str):
                row["search"] = row["search"].replace(previous, DISPLAY_NAME)
        elif row.get("kind") == "record" and row.get("id") == "0190c9f52d85ab4f":
            # Keep the source record searchable after the synthetic person retires.
            row["name"] = NAME + " · 1577"
            if isinstance(row.get("search"), str):
                row["search"] = row["search"].replace("[Androw?/Andrew] Glasgow", NAME).replace(
                    OLD, CURRENT).replace(OLD_SOURCE, NEW_SOURCE)
        result.append(row)
    return result


def canonical_record(record):
    record = copy.deepcopy(record)
    record.update(person=NAME, profile_id=PROFILE, gender="Female",
                  association="Lawful child and executor-dative of John Glasgow",
                  note=NOTE, source_title=NEW_SOURCE,
                  source_status="Accepted human reading m[ar]iory; matched to existing Glasgow-3589.")
    # The old draft inferred a birth event from being named in a testament.
    for field in ("birth_date", "birth_status", "birth_location"):
        if field in record:
            record[field] = ""
    return record


def record_key(record):
    title = record.get("source_title", "")
    if title in (OLD_SOURCE, NEW_SOURCE):
        title = NEW_SOURCE
    date = str(record.get("year", record.get("filter_year", "")))
    if date.endswith(".0"):
        date = date[:-2]
    return title, date


def plan(root: Path) -> dict[str, bytes]:
    """Build all changes in memory before touching any maintained file."""
    changes = {}

    def read(path):
        return json.loads((root / path).read_text())

    def put(path, value):
        changes[path] = dump(value)

    links = read("data/wikitree/catalogue-profile-links.json")["entries"]
    if links.get(OLD, {}).get("profile_id") != PROFILE:
        raise ValueError("Durable reviewed mapping must identify Glasgow-3589")
    family = links.get("record-edinburgh-1577-john-family", {})
    if family.get("record_profiles", {}).get(NEW_SOURCE) != PROFILE:
        raise ValueError("Canonical Marjory source mapping is missing")

    dossier = read(f"www/people/{CURRENT}.json")
    if dossier.get("id") != PROFILE:
        raise ValueError("Current public dossier does not identify Glasgow-3589")
    people = read("www/data/people.json")
    current = [p for p in people["people"] if p.get("catalogue_id") == CURRENT]
    if len(current) != 1:
        raise ValueError("Expected exactly one current public person")
    person = current[0]
    old = [p for p in people["people"] if obsolete(p)]

    csv_path = "www/map/data/records.csv"
    reader = csv.DictReader(io.StringIO((root / csv_path).read_text(encoding="utf-8-sig")))
    fields, records = reader.fieldnames, list(reader)
    matching = [r for r in records if r.get("source_title") in (OLD_SOURCE, NEW_SOURCE)]
    if not matching:
        raise ValueError("The original 1577 child record is missing from the maintained CSV")
    for record in matching:
        if record.get("profile_id") not in ("", PROFILE):
            raise ValueError("1577 child record has a conflicting profile destination")
        record.update(canonical_record(record))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(records)
    changes[csv_path] = stream.getvalue().encode("utf-8-sig")

    merged = list(person.get("records", []))
    for previous in old:
        merged.extend(previous.get("records", []))
        for field in ("clusters", "evidence", "recorded_in", "regions"):
            person[field] = list(dict.fromkeys(person.get(field, []) + previous.get(field, [])))
    # On a repeat run there is no old person: retain the already merged record.
    result, seen = [], set()
    for record in merged:
        if record.get("source_title") in (OLD_SOURCE, NEW_SOURCE):
            record = canonical_record(record)
        key = record_key(record)
        if key not in seen:
            result.append(record)
            seen.add(key)
    if not any(r.get("source_title") == NEW_SOURCE for r in result):
        raise ValueError("No retained public testament record; refusing to lose evidence")
    person.update(name=DISPLAY_NAME, first_names=["Marjorie"], records=result,
                  profile_work_status="linked_existing", has_wikitree_destination=True)
    people["people"] = [p for p in people["people"] if not obsolete(p)]
    people["count"] = len(people["people"])
    put("www/data/people.json", people)

    compact = [p for p in read("www/data/people-index.json") if not obsolete(p)]
    compact_current = [p for p in compact if p.get("catalogue_id") == CURRENT]
    if len(compact_current) != 1:
        raise ValueError("Expected exactly one current resolver entry")
    compact_current[0]["name"] = DISPLAY_NAME
    compact_current[0]["research_clusters"] = person.get("clusters", [])
    put("www/data/people-index.json", compact)

    search = [p for p in read("www/data/catalogue-search-index.json") if not obsolete(p)]
    search_current = [p for p in search if p.get("id") == CURRENT]
    if len(search_current) != 1:
        raise ValueError("Expected exactly one current catalogue search entry")
    item = search_current[0]
    item.update(name=DISPLAY_NAME, first_names=["Marjorie"], record_count=len(result),
                profile_work_status="linked_existing", has_profile=True,
                missing_profile=False, has_wikitree_destination=True, has_original_record=True)
    for field in ("clusters", "evidence", "recorded_in", "regions"):
        item[field] = person.get(field, [])
    item["date_years"] = sorted(set(item.get("date_years", []) + [1577]))
    item["record_types"] = list(dict.fromkeys(item.get("record_types", []) + ["Wills and probate"]))
    item["evidence_terms"] = list(dict.fromkeys(item.get("evidence_terms", []) + [NEW_SOURCE]))
    put("www/data/catalogue-search-index.json", search)
    changes["www/data/people-index.js"] = ("window.glasgowPeopleIndex=" +
        json.dumps(search, ensure_ascii=False, separators=(",", ":")) + ";\n").encode()

    # Remove the old name lead, rather than suggesting Marjory for an Andrew query.
    for path in sorted((root / "www/data/resolve").glob("*.json")):
        bundle = json.loads(path.read_text())
        candidates = bundle.get("candidates", [])
        filtered = [p for p in candidates if not obsolete(p)]
        changed = len(candidates) != len(filtered)
        for candidate in filtered:
            if candidate.get("catalogue_id") == CURRENT or candidate.get("id") == PROFILE:
                if candidate.get("name") != DISPLAY_NAME:
                    candidate["name"] = DISPLAY_NAME
                    changed = True
        if changed:
            bundle.update(candidates=filtered, candidate_count=len(filtered))
            put(str(path.relative_to(root)), bundle)

    dossier["name"] = DISPLAY_NAME
    put(f"www/people/{CURRENT}.json", dossier)
    alias = dict(schema_version="1.0", id=PROFILE, catalogue_id=CURRENT, name=DISPLAY_NAME,
                 status="superseded", superseded_catalogue_id=OLD, reason=REASON,
                 canonical_url=f"/people/{CURRENT}.html", json_url=f"/people/{CURRENT}.json",
                 network_url=f"/people/{CURRENT}.network.json",
                 wikitree_url=f"https://www.wikitree.com/wiki/{PROFILE}",
                 redirect_to=f"/people/{CURRENT}.json")
    put(f"www/people/{OLD}.json", alias)
    put(f"www/people/{OLD}.network.json", dict(schema_version="1.0", status="superseded",
        redirect_to=f"/people/{CURRENT}.network.json", person={
            "id": PROFILE, "name": DISPLAY_NAME, "html_url": f"/people/{CURRENT}.html",
            "json_url": f"/people/{CURRENT}.json"}, depth=1, relationships=[]))

    # Optional secondary browser indexes. Restrict edits to exact identities;
    # existing imported/history fields and unrelated people remain untouched.
    for relative in ("www/assets/research/registry.json",
                     "www/assets/research/search-people.json",
                     "www/assets/research/search-index.json"):
        if (root / relative).exists():
            rows = read(relative)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError(f"Unsupported registry schema: {relative}")
            put(relative, reconcile_registry(rows))
    packed_path = "www/assets/v3/registry-packed.json"
    if (root / packed_path).exists():
        packed = read(packed_path)
        fields = packed["fields"]
        if not {"id", "slug", "name"}.issubset(fields) or any(
                len(row) != len(fields) for row in packed["rows"]):
            raise ValueError("Unsupported packed registry fields")
        rows = reconcile_registry([dict(zip(fields, row)) for row in packed["rows"]])
        packed["rows"] = [[row.get(field) for field in fields] for row in rows]
        put(packed_path, packed)
    # These compact formats have fixed, explicitly named columns in the browser.
    for relative, fields in (
        ("www/assets/v3/search-people.json", ("id", "name", "url", "meta", "search")),
        ("www/assets/v3/people-quick.json", ("id", "name", "life", "place", "slug")),
    ):
        if (root / relative).exists():
            packed = read(relative)
            if not isinstance(packed, list) or any(not isinstance(row, list) or len(row) < 2 for row in packed):
                raise ValueError(f"Unsupported quick registry schema: {relative}")
            result = []
            for raw in packed:
                row = dict(zip(fields, raw))
                if not public_subject(row, OLD) and not public_subject(row, CURRENT, PROFILE):
                    result.append(raw)  # Preserve unrelated compact variants exactly.
                    continue
                rows = reconcile_registry([row])
                if rows:
                    result.append([rows[0].get(field) for field in fields[:len(raw)]] + raw[len(fields):])
            put(relative, result)
    for relative in (f"www/assets/research/people/{CURRENT}.json",
                     "www/assets/research/people/glasgow3589.json"):
        if (root / relative).exists():
            context = read(relative)
            if not public_subject(context, CURRENT, PROFILE):
                raise ValueError(f"Conflicting person context: {relative}")
            context["name"] = DISPLAY_NAME
            for event in context.get("events", []):
                if event.get("p") == CURRENT:
                    event["person"] = DISPLAY_NAME
            put(relative, context)
    old_context = f"www/assets/research/people/{OLD}.json"
    if (root / old_context).exists():
        put(old_context, dict(alias, redirect_to=f"/assets/research/people/{CURRENT}.json"))

    html_path = f"www/people/{OLD}.html"
    soup = BeautifulSoup((root / html_path).read_text(), "html.parser")
    main = soup.find("main")
    if main is None:
        raise ValueError("Old page has no site-shell main element")
    replacement = BeautifulSoup(f'<main class="r-main person-dossier-readable" id="main">'
        f'<nav class="crumb"><a href="/catalogue/">People</a> / Superseded reading</nav>'
        f'<article><h1>Superseded reading: Androw/Andrew Glasgow</h1><p>{REASON}</p>'
        f'<p><a href="/people/{CURRENT}.html">Read Marjorie Glasgow’s biography and sources</a>'
        f' · <a href="https://www.wikitree.com/wiki/{PROFILE}">WikiTree {PROFILE}</a></p>'
        '<p>The testament record remains attached to Marjory: National Records of Scotland, '
        'Edinburgh Commissary Court, CC8/8/5, images 276–277 (1577). '
        'Her later identity and maternity remain separate research questions.</p>'
        '</article></main>', "html.parser").main
    main.replace_with(replacement)
    if soup.title:
        soup.title.string = page_title("Superseded reading · Marjory Glasgow")
    crumb = soup.select_one(".g-crumbs strong")
    if crumb:
        crumb.string = "Superseded reading"
    for canonical in soup.select('link[rel="canonical"]'):
        canonical["href"] = f"https://glasgow.phenotype.dev/people/{CURRENT}.html"
    for description in soup.select('meta[name="description"]'):
        description["content"] = REASON
    for context in soup.select('script[type="application/ld+json"]'):
        context.string = json.dumps({"@context": "https://schema.org", "@type": "Person",
            "name": DISPLAY_NAME, "url": f"https://glasgow.phenotype.dev/people/{CURRENT}.html",
            "sameAs": f"https://www.wikitree.com/wiki/{PROFILE}"})
    changes[html_path] = with_analytics(str(soup)).encode()

    audit = read("data/wikitree/catalogue-profile-audit.json")
    entry = audit["entries"][OLD]
    if not entry.get("confirmed_profile_id") and "unlinked_count" in audit:
        audit["unlinked_count"] = max(0, audit["unlinked_count"] - 1)
    entry.update(name=NAME, identity_status="individual", identity_note=REASON,
                 recommended_action="verified_existing_profile", confirmed_profile_id=PROFILE,
                 matched_at="2026-09-30", draft_path=
                 "research/Glasgow-3589/2026-09-30_superseded_1577_Scotland_Hirmenschelis_Andrew_Glasgow.md")
    put("data/wikitree/catalogue-profile-audit.json", audit)
    return {path: content for path, content in changes.items()
            if (root / path).read_bytes() != content}


def write_plan(root: Path, changes: dict[str, bytes], backup: Path) -> None:
    backup.mkdir(parents=True, exist_ok=False)
    for path in changes:
        target = backup / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / path).read_bytes())
    (backup / "manifest.json").write_bytes(dump({"root": str(root.resolve()), "paths": list(changes)}))
    for path, content in changes.items():
        target = root / path
        temporary = target.with_name(target.name + ".reconcile-tmp")
        temporary.write_bytes(content)
        temporary.replace(target)


def restore(root: Path, backup: Path) -> None:
    manifest = json.loads((backup / "manifest.json").read_text())
    if manifest["root"] != str(root.resolve()):
        raise ValueError("Backup belongs to a different workspace")
    for relative in manifest["paths"]:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Invalid backup path")
        (root / path).write_bytes((backup / path).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--restore", type=Path)
    args = parser.parse_args()
    if args.restore:
        if args.write or args.backup_dir:
            parser.error("--restore cannot be combined with --write or --backup-dir")
        restore(args.root, args.restore)
        print("Restored local files from", args.restore)
        return
    changes = plan(args.root)
    print(f"{'Write' if args.write else 'Dry run'}: {len(changes)} files")
    for path in changes:
        print(path)
    if args.write and changes:
        backup = args.backup_dir or args.root / ".cache/retired-record-reconciliation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        write_plan(args.root, changes, backup)
        print("Backup:", backup)


if __name__ == "__main__":
    main()
