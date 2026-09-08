"""Canonical repository paths shared by map and research tooling."""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
DATA_DIR = ROOT / "data"
WIKITREE_DATA_DIR = DATA_DIR / "wikitree"
WIKITREE_PROFILE_EVIDENCE = WIKITREE_DATA_DIR / "profile-evidence.json"
WIKITREE_LIVE_OVERRIDES = WIKITREE_DATA_DIR / "live-profile-overrides.json"
WIKITREE_CHANGE_SCAN = WIKITREE_DATA_DIR / "recent-change-scan.json"
WIKITREE_CATALOGUE_PROFILE_AUDIT = WIKITREE_DATA_DIR / "catalogue-profile-audit.json"
WIKITREE_CATALOGUE_PROFILE_LINKS = WIKITREE_DATA_DIR / "catalogue-profile-links.json"
ONETREE_EXPORT_DIR = DATA_DIR / "exports" / "one-tree"
REFERENCE_DIR = DATA_DIR / "reference"
WORKBOOK_PATH = REFERENCE_DIR / "glasgow-one-tree.xlsx"

WEB_DIR = ROOT / "www"
HUB_HTML = WEB_DIR / "index.html"
MAP_DIR = WEB_DIR / "map"
MAP_HTML = MAP_DIR / "index.html"
MAP_DATA_DIR = MAP_DIR / "data"
MAP_RECORDS = MAP_DATA_DIR / "records.csv"
MAP_YDNA_TIMELINE = MAP_DATA_DIR / "ydna-timeline.json"
MAP_EARLY_BEARERS = MAP_DATA_DIR / "early-bearers.json"
MAP_RECENT_PROFILE_SUPPLEMENT = MAP_DATA_DIR / "recent-profile-supplement.json"
MAP_CACHE_DIR = MAP_DATA_DIR / "cache"
MAP_AUDIT_DIR = MAP_DATA_DIR / "audits"

RESEARCH_DIR = ROOT / "research"
SURNAME_RESEARCH_DIR = ROOT / "surname-research"
SURNAME_PROFILE_INDEX = SURNAME_RESEARCH_DIR / "indexes" / "profiles.json"


def _onetree_export_order(path: Path) -> tuple[str, str]:
    """Order timestamped exports by their filename, independent of copy mtime."""
    match = re.match(r"^ONT_Glas[^_]*_(.+)\.json$", path.name, re.I)
    return (match.group(1) if match else "", path.name)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Replace a text file only after its complete contents reach disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def atomic_write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict],
    *,
    encoding: str = "utf-8-sig",
    lineterminator: str = "\r\n",
) -> None:
    """Serialize and atomically replace a CSV file."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        lineterminator=lineterminator,
    )
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(path, output.getvalue(), encoding=encoding)


def relation_values(profile: dict, field: str) -> list[dict]:
    """Normalize WikiTree relationship collections to a list of objects."""
    raw = profile.get(field) or []
    if isinstance(raw, dict):
        values = raw.values()
    elif isinstance(raw, list):
        values = raw
    else:
        values = []
    return [value for value in values if isinstance(value, dict)]


def normalized_profile_redirects(redirects: dict[str, str]) -> dict[str, str]:
    """Collapse WikiTree redirect chains to their current canonical IDs."""
    normalized = {}
    for source in redirects:
        target = redirects[source]
        seen = {source}
        while target in redirects and target not in seen:
            seen.add(target)
            target = redirects[target]
        if target and target != source:
            normalized[source] = target
    return normalized


def apply_profile_redirects(
    profiles: dict[str, dict], redirects: dict[str, str]
) -> dict[str, dict]:
    """Remove merged-away profiles and retarget structured family references."""
    redirects = normalized_profile_redirects(redirects)
    active = {
        source: target for source, target in redirects.items()
        if target in profiles
    }
    numeric_redirects = {
        str(profiles[source].get("Id")): profiles[target].get("Id")
        for source, target in active.items()
        if source in profiles and profiles[source].get("Id") and profiles[target].get("Id")
    }

    def remap_relation(value):
        if isinstance(value, list):
            return [remap_relation(item) for item in value]
        if not isinstance(value, dict):
            return value
        remapped = {}
        for key, item in value.items():
            new_key = numeric_redirects.get(str(key), key)
            if key == "Name" and item in active:
                item = active[item]
            elif key == "Id" and str(item) in numeric_redirects:
                item = numeric_redirects[str(item)]
            remapped[str(new_key)] = remap_relation(item)
        return remapped

    for profile in profiles.values():
        for field in ("Father", "Mother"):
            if str(profile.get(field) or "") in numeric_redirects:
                profile[field] = numeric_redirects[str(profile[field])]
        for field in ("Parents", "Children", "Siblings", "Spouses"):
            if field in profile:
                profile[field] = remap_relation(profile[field])
    for source in active:
        profiles.pop(source, None)
    return profiles


def latest_onetree_export() -> Path:
    """Return the newest One-Tree JSON export in the canonical export folder."""
    exports = sorted(
        ONETREE_EXPORT_DIR.glob("ONT_Glasgow_*.json"),
        key=_onetree_export_order,
    )
    if not exports:
        raise FileNotFoundError(f"No One-Tree export found in {ONETREE_EXPORT_DIR}")
    return exports[-1]


def merged_onetree_profiles() -> tuple[dict[str, dict], list[Path]]:
    """Merge Glasgow-variant JSON exports by WikiTree ID, newest copy winning."""
    exports = sorted(
        ONETREE_EXPORT_DIR.glob("ONT_Glas*.json"),
        key=_onetree_export_order,
    )
    if not exports:
        raise FileNotFoundError(f"No One-Tree export found in {ONETREE_EXPORT_DIR}")
    profiles = {}
    for export_path in exports:
        data = json.loads(export_path.read_text(encoding="utf-8")).get("data", {})
        for profile in data.values():
            if profile.get("Name"):
                profiles[profile["Name"]] = profile
    return profiles, exports


def merged_map_profiles() -> tuple[dict[str, dict], list[Path]]:
    """Merge One-Tree data, local supplements, and newer live API overrides."""
    profiles, exports = merged_onetree_profiles()
    if not SURNAME_PROFILE_INDEX.exists():
        return profiles, exports
    indexed = json.loads(SURNAME_PROFILE_INDEX.read_text(encoding="utf-8")).get("profiles", {})
    for profile_id, profile in indexed.items():
        display_name = profile.get("display_name") or profile_id
        # Placeholder-only index entries carry no usable profile metadata.  A
        # former duplicate also redirects to Glasgow-1150 on WikiTree.
        if display_name == profile_id or profile_id == "Glasgow-3098":
            continue
        name_parts = display_name.replace("(", "").replace(")", "").split()
        first_name = name_parts[0] if name_parts else ""
        middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
        profiles.setdefault(profile_id, {
            "Name": profile_id,
            "FirstName": first_name,
            "RealName": first_name,
            "MiddleName": middle_name,
            "LongName": display_name,
            "BirthName": display_name,
            "LastNameAtBirth": "Glasgow",
            "LastNameCurrent": "Glasgow",
            "BirthDate": profile.get("birth_date") or "",
            "BirthLocation": profile.get("birth_location") or "",
            "DeathDate": profile.get("death_date") or "",
            "DeathLocation": profile.get("death_location") or "",
            "Gender": "",
            "Spouses": [],
        })
    if WIKITREE_LIVE_OVERRIDES.exists():
        payload = json.loads(WIKITREE_LIVE_OVERRIDES.read_text(encoding="utf-8"))
        for profile_id, override in payload.get("profiles", {}).items():
            if not isinstance(override, dict) or not override.get("Name"):
                continue
            current = profiles.get(profile_id, {})
            current_touched = str(current.get("Touched") or "")
            override_touched = str(override.get("Touched") or "")
            if current and current_touched and override_touched and override_touched < current_touched:
                continue
            profiles.setdefault(profile_id, {}).update(override)
        apply_profile_redirects(profiles, payload.get("redirects", {}))
    return profiles, exports
