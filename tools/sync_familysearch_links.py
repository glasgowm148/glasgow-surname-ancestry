#!/usr/bin/env python3
"""Copy the reviewed catalogue-to-FamilySearch person matches into the repository.

The FamilySearch parity work keeps its matches in ``fs-parity/map.tsv``, outside
this repository, one row per review. A person may have several rows, because a
correction is appended rather than edited in place, so the last row for a
catalogue id wins. Only high and medium confidence matches are kept. Person
pages read the result through ``tools/profile_tree_links.py`` to show a
"View on FamilySearch" button. For the normal project target, only individual
entries in the privacy-filtered public people export are eligible.

After applying corrections and withdrawals, each FamilySearch PID must belong
to only one canonical catalogue identity. Distinct ids are unresolved unless
explicitly merged by the workbench; names
are not evidence of aliases. Conflicts abort before creating output directories
or replacing the display crosswalk. Known display consumers also validate existing
JSON through load_matches. Only explicit authoritative workbench merges reconcile
catalogue ids; names never do.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from collections.abc import Mapping
from functools import lru_cache
import json
from pathlib import Path
import re
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "fs-parity" / "map.tsv"
TARGET = ROOT / "data" / "familysearch" / "person-links.json"
FS_ID = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{2,4}$")


def _canonical_aliases(aliases):
    if aliases is None:
        return {}
    if not isinstance(aliases, Mapping):
        raise ValueError("Canonical aliases must be a mapping")
    direct = {}
    for old, new in aliases.items():
        if not all(isinstance(x, str) and x.strip() for x in (old, new)):
            raise ValueError("Canonical aliases must resolve to nonempty catalogue ids")
        old, new = old.strip().lower(), new.strip().lower()
        if old in direct:
            raise ValueError(f"Duplicate normalized canonical alias: {old}")
        direct[old] = new
    resolved = {}
    for old in sorted(direct):
        current, seen = old, set()
        while current in direct:
            if current in seen:
                raise ValueError(f"Cyclic canonical alias involving {current}")
            seen.add(current)
            current = direct[current]
        resolved[old] = current
    return resolved


def validate_matches(people: dict, canonical_aliases=None) -> dict:
    """Return normalized matches or reject malformed/conflicting display data.

    Only supplied explicit canonical aliases reconcile distinct ids. Terminal
    targets need not have FS matches. Empty targets and cycles are invalid.
    Normalized duplicate keys are rejected rather than silently overwritten.
    """
    aliases = _canonical_aliases(canonical_aliases)
    if not isinstance(people, Mapping):
        raise ValueError("FamilySearch people must be an object")
    normalized = {}
    for key, match in people.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("FamilySearch catalogue ids must be nonempty strings")
        key = key.strip().lower()
        if key in normalized:
            raise ValueError(f"Duplicate normalized FamilySearch catalogue id: {key}")
        if not isinstance(match, Mapping):
            raise ValueError(f"Invalid FamilySearch match for {key}: expected an object")
        pid = match.get("id")
        confidence = match.get("confidence")
        if not isinstance(pid, str) or not FS_ID.fullmatch(pid.strip().upper()):
            raise ValueError(f"Invalid FamilySearch PID for {key}")
        if not isinstance(confidence, str) or confidence.strip().lower() not in {"high", "medium"}:
            raise ValueError(f"Invalid FamilySearch confidence for {key}")
        normalized[key] = {**match, "id": pid.strip().upper(), "confidence": confidence.strip().lower()}
    by_pid = {}
    for key, match in sorted(normalized.items()):
        by_pid.setdefault(match["id"], []).append(key)
    conflicts = [f"{pid}: {', '.join(keys)}" for pid, keys in sorted(by_pid.items())
                 if len({aliases.get(key, key) for key in keys}) > 1]
    if conflicts:
        raise ValueError(
            "FamilySearch PID assigned to distinct unresolved catalogue people: " + "; ".join(conflicts)
        )
    return dict(sorted(normalized.items()))


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate FamilySearch JSON key: {key}")
        value[key] = item
    return value


def _stamp(path):
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


@lru_cache(maxsize=16)
def _configured_database(root, config_stamp):
    from genealogy.store.project import StorageSettings, load_config
    return root / StorageSettings.from_config(load_config(root)).database


@lru_cache(maxsize=16)
def _wal_digest(path, stamp):
    # ctime invalidates this digest cache. SQLite readers may change ctime
    # alone, so the snapshot identity below compares the actual bytes.
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").digest()


def _project_context(path):
    """Only the conventional project crosswalk inherits that project's merges."""
    path = Path(path).absolute()
    if path.parts[-3:] != ("data", "familysearch", "person-links.json"):
        return None, ()
    root = path.parents[2]
    primary_stamp = _stamp(root / "genealogy.toml")
    if primary_stamp is None:
        return None, ()
    config_stamp = (primary_stamp, _stamp(root / "genealogy.local.toml"))
    database = _configured_database(root, config_stamp)
    database_stamp = _stamp(database)
    wal_path = Path(str(database) + "-wal")
    stamp = _stamp(wal_path)
    wal_stamp = None
    if stamp and stamp[2]:
        try:
            wal_stamp = (*stamp[:4], _wal_digest(wal_path, stamp))
        except FileNotFoundError:
            # A concurrent checkpoint removed the WAL. The surrounding
            # before/after check also compares the main database stamp.
            pass
    stamps = (database_stamp, wal_stamp)
    return (root if stamps[0] is not None else None), (config_stamp, database, stamps)


def _workbench_aliases(root):
    if root is None:
        return {}
    from genealogy.store import open_project
    try:
        from tools.workbench_legacy_views import Views
    except ModuleNotFoundError:
        from workbench_legacy_views import Views
    with open_project(root, readonly=True) as project:
        # Views can include the survivor's own moved alias: it is a no-op,
        # not an additional identity decision or a cyclic merge.
        return {old: new for old, new in Views(project.store)._merged_public.items()
                if old.strip().lower() != new.strip().lower()}


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class _Snapshot(Mapping):
    """Immutable storage; entry lookups return isolated, JSON-compatible copies."""
    __slots__ = ("_data", "_source", "_aliases")

    def __init__(self, people, source=None, canonical_aliases=None):
        object.__setattr__(self, "_data", _freeze(people))
        object.__setattr__(self, "_source", source)
        object.__setattr__(self, "_aliases", _freeze(canonical_aliases))

    def __setattr__(self, name, value):
        raise TypeError("Validated FamilySearch snapshots are immutable")

    def __getitem__(self, key):
        return _thaw(self._data[key])

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


def validated_snapshot(people, canonical_aliases=None):
    if isinstance(people, _Snapshot) and canonical_aliases is None:
        if people._source is not None:
            return load_matches(people._source, people._aliases)
        return people
    return _Snapshot(validate_matches(people, canonical_aliases))


@lru_cache(maxsize=16)
def _load_snapshot(path, stamp, context):
    root, _ = context
    text = path.read_text(encoding="utf-8")
    value = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or "people" not in value:
        raise ValueError("FamilySearch crosswalk must be an object containing people")
    return _Snapshot(validate_matches(value["people"], _workbench_aliases(root)), path)


def load_matches(path: Path = TARGET, canonical_aliases=None) -> Mapping:
    """Load immutable validated data, rechecking file/config/DB stamps per call.

    Explicit aliases override automatic project context. Missing files mean no
    links. A changed input during loading fails closed rather than caching it.
    """
    path = Path(path).absolute()
    stamp = _stamp(path)
    if stamp is None:
        return _Snapshot(validate_matches({}, canonical_aliases), path, canonical_aliases)
    context = _project_context(path) if canonical_aliases is None else (None, ())
    if canonical_aliases is None:
        result = _load_snapshot(path, stamp, context)
    else:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(value, dict) or "people" not in value:
            raise ValueError("FamilySearch crosswalk must be an object containing people")
        result = _Snapshot(validate_matches(value["people"], canonical_aliases), path, canonical_aliases)
    if stamp != _stamp(path) or (canonical_aliases is None and context != _project_context(path)):
        _load_snapshot.cache_clear()
        raise ValueError("FamilySearch validation inputs changed during loading; retry")
    return result


def read_matches(source: Path, canonical_aliases=None) -> dict:
    """Read final reviewed matches, rejecting PIDs shared by distinct ids.

    Rows without a catalogue id or valid PID are ignored, as before. Among valid
    rows for an id, the last row wins; a confidence other than high/medium withdraws
    the match. Validate only that final state so superseded reviews do not conflict.
    Only explicitly supplied canonical aliases reconcile catalogue identities.
    """
    people = {}
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            key = (row.get("catalogue_id") or "").strip().lower()
            fs_id = (row.get("fs_id") or "").strip().upper()
            confidence = (row.get("confidence") or "").strip().lower()
            if not key or not FS_ID.match(fs_id):
                continue
            if confidence not in {"high", "medium"}:
                people.pop(key, None)  # a later doubtful row withdraws an earlier match
                continue
            people[key] = {"id": fs_id, "confidence": confidence}
    return validate_matches(people, canonical_aliases)


def _published_person_ids(path: Path, canonical_aliases) -> set[str]:
    """Use the same public people input as the catalogue builders."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError("Build the public people export before syncing FamilySearch links") from error
    rows = payload.get("people") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("Invalid public people export for FamilySearch links")
    aliases = _canonical_aliases(canonical_aliases)
    published = set()
    for row in rows:
        key = row.get("catalogue_id") if isinstance(row, dict) else None
        profiles = row.get("profile_ids") if isinstance(row, dict) else None
        if not isinstance(key, str) or not key.strip() or not isinstance(profiles, list) or any(
            not isinstance(profile, str) or not profile.strip() for profile in profiles
        ):
            raise ValueError("Invalid person row in the public people export")
        identities = {aliases.get(profile, profile) for profile in (
            value.strip().lower() for value in profiles
        )}
        if not (row.get("withheld") or row.get("likely_living")) and len(identities) <= 1:
            published.add(key.strip().lower())
    return published


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    args = parser.parse_args(argv)
    try:
        context = _project_context(args.target)
        aliases = _workbench_aliases(context[0])
        people = read_matches(args.source, aliases)
        withheld = 0
        target = args.target.absolute()
        if target.parts[-3:] == ("data", "familysearch", "person-links.json"):
            public_path = target.parents[2] / "www" / "data" / "people.json"
            public_stamp = _stamp(public_path)
            published = _published_person_ids(public_path, aliases)
            if public_stamp != _stamp(public_path):
                raise ValueError("Public people export changed during FamilySearch sync; retry")
            filtered = {key: match for key, match in people.items() if key in published}
            withheld = len(people) - len(filtered)
            people = filtered
        if context != _project_context(args.target):
            raise ValueError("FamilySearch target context changed during validation; retry")
    except ValueError as error:
        parser.error(str(error))
    args.target.parent.mkdir(parents=True, exist_ok=True)
    value = json.dumps({"source": "fs-parity/map.tsv", "people": people}, indent=1, ensure_ascii=False) + "\n"
    if not args.target.exists() or args.target.read_text(encoding="utf-8") != value:
        args.target.write_text(value, encoding="utf-8")
    summary = {"people": len(people)}
    if withheld:
        summary["withheld_from_public_crosswalk"] = withheld
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
