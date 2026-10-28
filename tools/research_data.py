#!/usr/bin/env python3
"""Research rows for the site builders, read from the research database.

The builders used to read the research registries (``research/*.json``)
directly. Those files are generated views of the research database
(``make research-views``), so builders ask here instead and get the same rows
from the database itself (``workbench_legacy_views.Views``). Where there is no
database (a fresh clone, CI), the generated file is read, as before.

Each function returns exactly what ``json.loads`` of its file would return.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT)]
from workbench_legacy_views import ASSESSMENTS, ESTIMATES, FINDINGS, RECORDS, VITALS, Views, dump  # noqa: E402


@lru_cache(maxsize=4)
def _views(root: Path):
    """The database views, or None when the project has no research database."""
    try:
        from genealogy.store import has_database, open_project
    except ModuleNotFoundError:
        return None
    if not has_database(root):
        return None
    return Views(open_project(root, readonly=True).store)


def _rows(root: Path | None, relative: str, build):
    root = Path(root or ROOT).resolve()
    views = _views(root)
    if views is None:
        path = root / relative
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    return json.loads(dump(build(views)))   # identical to reading the generated file


def relationship_assessments(root: Path | None = None):
    return _rows(root, ASSESSMENTS, Views.assessments) or []


def relationship_estimates(root: Path | None = None):
    return _rows(root, ESTIMATES, Views.estimates_document) or {}


def latest_findings(root: Path | None = None):
    return _rows(root, FINDINGS, Views.findings) or {}


def canonical_records(root: Path | None = None):
    return _rows(root, RECORDS, Views.records) or []


def vital_assessments(root: Path | None = None):
    return _rows(root, VITALS, Views.vitals) or {}
