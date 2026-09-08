#!/usr/bin/env python3
"""Incrementally refresh WikiTree profiles changed since local exports.

The compact first pass compares WikiTree ``Touched`` timestamps for every
locally known profile. Only changed/explicit profiles are then expanded to
their current immediate relationships and saved as a small override layer.
An exported NetworkFeed HTML file can supply IDs which are not yet local.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

try:
    from project_paths import (
        MAP_RECORDS, ROOT, SRC_DIR, SURNAME_PROFILE_INDEX, WIKITREE_CHANGE_SCAN,
        WIKITREE_LIVE_OVERRIDES, WIKITREE_PROFILE_EVIDENCE,
        atomic_write_text, merged_map_profiles, normalized_profile_redirects,
        relation_values,
    )
except ModuleNotFoundError:  # Imported as tools.sync_recent_wikitree_changes in tests.
    from tools.project_paths import (
        MAP_RECORDS, ROOT, SRC_DIR, SURNAME_PROFILE_INDEX, WIKITREE_CHANGE_SCAN,
        WIKITREE_LIVE_OVERRIDES, WIKITREE_PROFILE_EVIDENCE,
        atomic_write_text, merged_map_profiles, normalized_profile_redirects,
        relation_values,
    )

sys.path.insert(0, str(SRC_DIR))

from wikitree_family_export import ExportError, post_wikitree  # noqa: E402


WIKITREE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
WIKITREE_ID_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9_'’-])" + WIKITREE_ID.pattern + r"(?![A-Za-z0-9_-])"
)
REDIRECT_STATUS = re.compile(r"Redirected to \d+/([^/\s]+)$")
COMPACT_FIELDS = (
    "Id,PageId,Name,FirstName,MiddleName,MiddleInitial,LastNameAtBirth,"
    "LastNameCurrent,LastNameOther,Nicknames,RealName,ShortName,LongName,"
    "BirthName,Prefix,Suffix,Gender,BirthDate,BirthLocation,DeathDate,"
    "DeathLocation,Father,Mother,DataStatus,Privacy,Connected,Created,Touched,"
    "HasChildren,NoChildren,childrenCount,yDNA,auDNA"
)
COMPARE_FIELDS = (
    "Name", "FirstName", "MiddleName", "LastNameAtBirth", "LastNameCurrent",
    "LastNameOther", "Suffix", "Gender", "BirthDate", "BirthLocation",
    "DeathDate", "DeathLocation", "Father", "Mother", "DataStatus", "Privacy",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan known WikiTree profiles and selectively refresh changed tree data."
    )
    parser.add_argument("--feed-html", type=Path, help="Saved Special:NetworkFeed HTML export")
    parser.add_argument("--profiles", nargs="*", default=[], help="Force-refresh these WikiTree IDs")
    parser.add_argument("--no-scan-known", action="store_true", help="Only inspect feed/explicit IDs")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--apply", action="store_true", help="Write the live override and scan report")
    parser.add_argument("--refresh-evidence", action="store_true", help="Refresh biography/source snapshots for changed profiles")
    parser.add_argument("--rebuild", action="store_true", help="Regenerate map rows, catalogue, JSON dossiers and networks")
    return parser.parse_args()


def chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def ids_from_feed(path: Path | None) -> set[str]:
    if not path:
        return set()
    if not path.exists():
        raise FileNotFoundError(path)
    return set(WIKITREE_ID.findall(path.read_text(encoding="utf-8", errors="replace")))


def redirects_from_envelope(envelope: dict) -> dict[str, str]:
    redirects = {}
    for requested, result in (envelope.get("resultByKey") or {}).items():
        match = REDIRECT_STATUS.search(str((result or {}).get("status") or ""))
        if match and requested != match.group(1):
            redirects[str(requested)] = match.group(1)
    return redirects


def fetch_people(
    profile_ids: set[str] | list[str], batch_size: int
) -> tuple[dict[str, dict], list[dict], dict[str, str]]:
    results: dict[str, dict] = {}
    failures = []
    redirects = {}
    ordered = sorted(set(profile_ids))
    for batch in chunks(ordered, batch_size):
        try:
            envelope = post_wikitree({
                "action": "getPeople", "keys": ",".join(batch),
                "fields": COMPACT_FIELDS, "resolveRedirect": "1",
            })
        except ExportError as exc:
            failures.extend({"profile_id": profile_id, "error": str(exc)} for profile_id in batch)
            continue
        batch_redirects = redirects_from_envelope(envelope)
        redirects.update(batch_redirects)
        people = envelope.get("people") or {}
        if not isinstance(people, dict):
            failures.extend({"profile_id": profile_id, "error": "No people collection returned"} for profile_id in batch)
            continue
        returned_requested = set()
        for requested_key, profile in people.items():
            if not isinstance(profile, dict) or not profile.get("Name"):
                continue
            results[str(profile["Name"])] = profile
            returned_requested.add(str(requested_key))
            returned_requested.add(str(profile["Name"]))
        for profile_id in batch:
            if (
                profile_id not in returned_requested
                and profile_id not in results
                and profile_id not in batch_redirects
            ):
                failures.append({"profile_id": profile_id, "error": "No public profile returned"})
    return results, failures, redirects


def fetch_relationships(profile_ids: set[str], batch_size: int) -> tuple[dict[str, dict], set[str], list[dict]]:
    subjects = {}
    relatives = set()
    failures = []
    for batch in chunks(sorted(profile_ids), batch_size):
        try:
            envelope = post_wikitree({
                "action": "getRelatives", "keys": ",".join(batch),
                "fields": COMPACT_FIELDS,
                "getParents": "1", "getChildren": "1", "getSiblings": "1", "getSpouses": "1",
            })
        except ExportError as exc:
            failures.extend({"profile_id": profile_id, "error": str(exc)} for profile_id in batch)
            continue
        items = envelope.get("items") or []
        returned = set()
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("person"), dict):
                continue
            person = item["person"]
            requested = str(item.get("user_name") or person.get("Name") or "")
            subject_id = str(person.get("Name") or requested)
            if subject_id:
                subjects[subject_id] = person
                returned.update({requested, subject_id})
            for field in ("Parents", "Children", "Siblings", "Spouses"):
                relatives.update(
                    str(value["Name"]) for value in relation_values(person, field) if value.get("Name")
                )
        for profile_id in batch:
            if profile_id not in returned and profile_id not in subjects:
                failures.append({"profile_id": profile_id, "error": "No relationship snapshot returned"})
    return subjects, relatives, failures


def comparable(value):
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value in (None, "") and "" or value


def profile_changes(local: dict, current: dict) -> dict:
    return {
        field: {"before": local.get(field), "after": current.get(field)}
        for field in COMPARE_FIELDS
        if comparable(local.get(field)) != comparable(current.get(field))
    }


def spouse_snapshot(person: dict) -> list[dict]:
    return [
        {
            key: value.get(key)
            for key in (
                "Id", "PageId", "Name", "FirstName", "MiddleName", "LastNameAtBirth",
                "LastNameCurrent", "LongName", "BirthName", "Gender", "BirthDate",
                "BirthLocation", "DeathDate", "DeathLocation", "marriage_date",
                "marriage_location", "MarriageDate", "MarriageLocation",
            )
            if value.get(key) not in (None, "")
        }
        for value in relation_values(person, "Spouses")
    ]


def year_from_date(value) -> int | None:
    match = re.match(r"(\d{4})", str(value or ""))
    if not match or match.group(1) == "0000":
        return None
    return int(match.group(1))


def is_public_historical(profile: dict, current_year: int | None = None) -> bool:
    """Keep newly discovered overrides public and historical by default."""
    privacy = int(profile.get("Privacy") or 0)
    if privacy < 50:
        return False
    if year_from_date(profile.get("DeathDate")) or profile.get("DeathLocation"):
        return True
    birth_year = year_from_date(profile.get("BirthDate"))
    return bool(birth_year and birth_year <= (current_year or datetime.now().year) - 100)


def run_command(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def is_fatal_failure(failure: dict) -> bool:
    # Deleted, merged or newly private IDs are expected in an old bulk export.
    # Transport/API failures should still make automation fail loudly.
    return failure.get("error") != "No public profile returned"


def canonicalise_local_records(redirects: dict[str, str]) -> None:
    """Apply confirmed WikiTree redirects to structured local working data."""
    redirects = normalized_profile_redirects(redirects)
    if not redirects:
        return

    def remap(value):
        if isinstance(value, str):
            return redirects.get(value, value)
        if isinstance(value, list):
            return [remap(item) for item in value]
        if isinstance(value, dict):
            return {key: remap(item) for key, item in value.items()}
        return value

    for path in (WIKITREE_PROFILE_EVIDENCE, SURNAME_PROFILE_INDEX):
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        profiles = payload.get("profiles")
        if isinstance(profiles, dict):
            for source in redirects:
                profiles.pop(source, None)
        payload = remap(payload)
        if "profile_count" in payload and isinstance(payload.get("profiles"), dict):
            payload["profile_count"] = len(payload["profiles"])
        atomic_write_text(
            path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )

    if MAP_RECORDS.exists():
        text = MAP_RECORDS.read_text(encoding="utf-8-sig")
        # Replace complete WikiTree IDs only.  A raw string replacement would
        # also turn e.g. Glasgow-10 into Glasgow-20 when Glasgow-1 redirects.
        text = WIKITREE_ID_REFERENCE.sub(
            lambda match: redirects.get(match.group(0), match.group(0)), text
        )
        atomic_write_text(MAP_RECORDS, text, encoding="utf-8-sig")


def main() -> int:
    options = parse_args()
    local_profiles, export_paths = merged_map_profiles()
    feed_ids = ids_from_feed(options.feed_html)
    explicit_ids = set(options.profiles)
    candidate_ids = set(feed_ids) | explicit_ids
    if not options.no_scan_known:
        candidate_ids.update(local_profiles)
    if not candidate_ids:
        raise SystemExit("No profiles selected; supply IDs/feed HTML or scan the known tree")

    current_profiles, failures, redirects = fetch_people(candidate_ids, options.batch_size)
    if not current_profiles and any(is_fatal_failure(failure) for failure in failures):
        print("WikiTree returned no usable profiles; existing overrides and reports were left unchanged.")
        for failure in failures:
            print(f"  ERROR {failure['profile_id']}: {failure['error']}")
        return 1
    forced = feed_ids | explicit_ids
    changed = set()
    changes = {}
    for profile_id, current in current_profiles.items():
        local = local_profiles.get(profile_id, {})
        current_touched = str(current.get("Touched") or "")
        local_touched = str(local.get("Touched") or "")
        if profile_id in forced or not local or (current_touched and current_touched > local_touched):
            changed.add(profile_id)
            changes[profile_id] = {
                "local_touched": local_touched or None,
                "current_touched": current_touched or None,
                "new_profile": not bool(local),
                "fields": profile_changes(local, current),
            }

    relationship_subjects, related_ids, relation_failures = fetch_relationships(changed, options.batch_size)
    failures.extend(relation_failures)
    new_related_ids = related_ids - set(local_profiles) - set(current_profiles)
    fetched_new_related, related_failures, related_redirects = fetch_people(new_related_ids, options.batch_size)
    redirects.update(related_redirects)
    failures.extend(related_failures)

    # Existing profiles retain the site's existing privacy policy. Newly found
    # profiles are admitted only when the public API clearly identifies them as
    # public historical people; private/living relatives stay out of outputs.
    new_related = {
        profile_id: profile for profile_id, profile in fetched_new_related.items()
        if is_public_historical(profile)
    }
    withheld_new = sorted(set(fetched_new_related) - set(new_related))
    changed_to_save = {
        profile_id: current_profiles[profile_id]
        for profile_id in changed
        if profile_id in current_profiles
        and int(current_profiles[profile_id].get("Privacy") or 0) >= 50
        and (profile_id in local_profiles or is_public_historical(current_profiles[profile_id]))
    }
    withheld_new.extend(sorted(set(changed) - set(changed_to_save)))

    overrides = {**changed_to_save, **new_related}
    for profile_id, person in relationship_subjects.items():
        if profile_id not in overrides:
            continue
        overrides[profile_id]["Spouses"] = spouse_snapshot(person)

    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = {
        "schema_version": 1,
        "scanned_at": captured_at,
        "source_exports": [path.name for path in export_paths],
        "feed_html": str(options.feed_html) if options.feed_html else None,
        "known_profile_count": len(local_profiles),
        "candidate_count": len(candidate_ids),
        "feed_profile_ids": sorted(feed_ids),
        "explicit_profile_ids": sorted(explicit_ids),
        "changed_profile_count": len(changed),
        "changed_profiles": changes,
        "new_immediate_relatives": sorted(new_related),
        "withheld_private_or_living_updates": sorted(set(withheld_new)),
        "failures": failures,
        "redirects": redirects,
    }

    if options.apply:
        existing = {"schema_version": 1, "profiles": {}}
        if WIKITREE_LIVE_OVERRIDES.exists():
            existing = json.loads(WIKITREE_LIVE_OVERRIDES.read_text(encoding="utf-8"))
        stored_redirects = existing.setdefault("redirects", {})
        stored_redirects.update(redirects)
        for source in redirects:
            existing.setdefault("profiles", {}).pop(source, None)
        for profile_id in changed - set(changed_to_save):
            existing.setdefault("profiles", {}).pop(profile_id, None)
        existing.setdefault("profiles", {}).update(overrides)
        existing.update({
            "schema_version": 1, "generated_at": captured_at,
            "source": "WikiTree compact change scan plus current immediate relationships",
            "last_scan": report,
        })
        WIKITREE_LIVE_OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            WIKITREE_LIVE_OVERRIDES,
            json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
        )
        atomic_write_text(
            WIKITREE_CHANGE_SCAN,
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        )

    refresh_ids = sorted(set(overrides))
    if options.refresh_evidence:
        if not options.apply:
            raise SystemExit("--refresh-evidence requires --apply")
        if refresh_ids:
            run_command([
                sys.executable, "tools/sync_wikitree_profile_evidence.py",
                "--profiles", *refresh_ids, "--refresh", "--no-research-cases",
            ])
    if options.apply:
        canonicalise_local_records(existing.get("redirects", {}))
    if options.rebuild:
        if not options.apply:
            raise SystemExit("--rebuild requires --apply")
        run_command([sys.executable, "tools/sync_onetree_ireland_uk_to_1900.py"])
        run_command([sys.executable, "tools/build_family_map.py"])

    print(
        f"Scanned {len(candidate_ids)} profile IDs; {len(changed)} changed/forced; "
        f"{len(new_related)} new public historical relatives; "
        f"{len(set(withheld_new))} private/living API updates withheld; {len(failures)} failures"
    )
    for source, target in sorted(redirects.items()):
        print(f"  REDIRECT {source} -> {target}")
    for profile_id in sorted(changes):
        fields = ", ".join(changes[profile_id]["fields"]) or "timestamp/feed refresh"
        print(f"  {profile_id}: {fields}")
    for failure in failures:
        print(f"  WARNING {failure['profile_id']}: {failure['error']}")
    if not options.apply:
        print("Dry run only; rerun with --apply to save overrides.")
    return 1 if any(is_fatal_failure(failure) for failure in failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
