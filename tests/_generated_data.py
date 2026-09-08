"""Availability marker for tests that inspect ignored generated artefacts."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_GENERATED_PATHS = (
    ROOT / "data" / "exports" / "one-tree",
    ROOT / "data" / "wikitree" / "profile-evidence.json",
    ROOT / "www" / "data" / "people.json",
    ROOT / "www" / "map" / "data" / "records.csv",
    ROOT / "www" / "onetree" / "glasgow-one-tree-polished" / "model.json",
)
GENERATED_DATA_AVAILABLE = all(path.exists() for path in REQUIRED_GENERATED_PATHS)
requires_generated_data = unittest.skipUnless(
    GENERATED_DATA_AVAILABLE,
    "requires local generated catalogue/One-Tree artefacts (omitted from CI checkout)",
)
