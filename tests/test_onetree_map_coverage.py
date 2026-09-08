#!/usr/bin/env python3
"""Regression checks for additive One-Tree map synchronization."""

from __future__ import annotations

import csv
import json
import re
import sys
import unittest
from pathlib import Path

from tests._generated_data import requires_generated_data


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from project_paths import (  # noqa: E402
    MAP_AUDIT_DIR,
    MAP_RECORDS,
    MAP_RECENT_PROFILE_SUPPLEMENT,
    WIKITREE_LIVE_OVERRIDES,
    merged_map_profiles,
    normalized_profile_redirects,
)
import sync_onetree_ireland_uk_to_1900 as sync  # noqa: E402


@requires_generated_data
class OneTreeMapCoverageTests(unittest.TestCase):
    def test_dictionary_shaped_spouses_supply_marriage_events(self):
        profile = {
            "Spouses": {
                "123": {"MarriageLocation": "Irvine, Ayrshire, Scotland"}
            }
        }
        self.assertEqual(
            sync.events(profile),
            [("MarriageLocation", "Irvine, Ayrshire, Scotland")],
        )
        self.assertEqual(
            sync.scotland_sync.scottish_event(profile),
            ("MarriageLocation", "Irvine, Ayrshire, Scotland"),
        )
        irish_profile = {
            "Spouses": {"123": {"MarriageLocation": "Larne, County Antrim, Ireland"}}
        }
        self.assertEqual(
            sync.ireland_sync.event_for(irish_profile),
            ("MarriageLocation", "Larne, County Antrim, Ireland"),
        )

    def test_recent_pre_1900_edit_supplement_is_fully_mapped(self):
        import json

        source = json.loads(MAP_RECENT_PROFILE_SUPPLEMENT.read_text(encoding="utf-8"))
        with MAP_RECORDS.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        mapped = {row.get("supplement_id") for row in rows if row.get("supplement_id")}
        expected = {profile["supplement_id"] for profile in source["profiles"]}
        mapped_profile_ids = {
            profile_id
            for row in rows
            for profile_id in sync.PROFILE_ID.findall(row["profile_id"])
        }
        live = json.loads(WIKITREE_LIVE_OVERRIDES.read_text(encoding="utf-8"))
        redirects = normalized_profile_redirects(live.get("redirects", {}))
        already_mapped = {
            redirects.get(profile_id, profile_id)
            for profile_id in source["already_mapped_profile_ids"]
        }
        self.assertEqual(23, len(expected))
        self.assertEqual(47, len(source["already_mapped_profile_ids"]))
        self.assertFalse(expected - mapped)
        self.assertFalse(already_mapped - mapped_profile_ids)
        self.assertEqual(66, len(expected) + len(source["already_mapped_profile_ids"]) - 4)
        self.assertTrue(all(int(profile["birth_date"][:4]) < 1900 for profile in source["profiles"]))
        self.assertTrue(all(sync.PROFILE_ID.fullmatch(profile["profile_id"]) for profile in source["profiles"]))
        for newly_linked in ("Glasgow-3943", "Glasgow-3950", "Glasgow-3956", "Glasgow-3962"):
            self.assertIn(newly_linked, mapped_profile_ids)

    def test_all_qualifying_export_profiles_are_mapped_without_regression(self):
        profiles, exports = merged_map_profiles()
        by_numeric_id = {
            str(profile.get("Id")): profile
            for profile in profiles.values()
            if profile.get("Id")
        }
        with MAP_RECORDS.open(encoding="utf-8-sig", newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if row["family_group"] != "Associated person"
            ]
        mapped = {
            profile_id.lower()
            for row in rows
            for profile_id in sync.PROFILE_ID.findall(row["profile_id"])
        }
        expected = {
            profile["Name"].lower()
            for profile in profiles.values()
            if sync.included_person(profile, profiles, by_numeric_id)
        }

        self.assertGreaterEqual(len(exports), 2)
        self.assertFalse(expected - mapped)
        self.assertGreaterEqual(len(expected), 4250)
        self.assertIn("glasgow-2712", mapped)  # July-only profile
        self.assertIn("garvin-1831", mapped)  # August-only profile
        self.assertNotIn("glasgow-3905", mapped)  # structural placeholder, not a historical occurrence
        for formerly_missing in ("glasgow-3910", "glasgow-3921", "glasgow-3923"):
            self.assertIn(formerly_missing, mapped)

        early_james = {
            profile["Name"]
            for profile in profiles.values()
            if (profile.get("FirstName") or "").strip().lower() == "james"
            and (profile.get("LastNameAtBirth") or "").strip().lower() == "glasgow"
            and sync.year(profile.get("BirthDate"))
            and sync.year(profile.get("BirthDate")) <= 1650
        }
        # Glasgow-3374 was merged into Glasgow-3332. Glasgow-3971 was then
        # added for the separately documented 1645 Scottish baptism.
        self.assertEqual(15, len(early_james))
        self.assertNotIn("Glasgow-3374", early_james)
        self.assertIn("Glasgow-3332", early_james)
        self.assertIn("Glasgow-3971", early_james)
        self.assertTrue({"Glasgow-3910", "Glasgow-3921", "Glasgow-3923"} <= early_james)

    def test_available_kin_locations_replace_unlocated_holding_points(self):
        profiles, _ = merged_map_profiles()
        by_numeric_id = {
            str(profile.get("Id")): profile
            for profile in profiles.values()
            if profile.get("Id")
        }
        children = sync.children_index(profiles)
        with MAP_RECORDS.open(encoding="utf-8-sig", newline="") as handle:
            generated = [
                row for row in csv.DictReader(handle)
                if row["family_group"].endswith("One-Tree profile leads")
            ]
        inferred = [row for row in generated if row["association"].startswith("Kin-inferred")]
        # The source tree changes as profiles are merged and locations are
        # filled.  Assert the feature remains active, then verify every row and
        # exact audit parity below instead of freezing a historical row count.
        self.assertTrue(inferred)
        self.assertTrue(all(row["record_precision"] == "Kin-inferred relationship locality" for row in inferred))
        self.assertTrue(all(not row["record_location"].startswith("Location not supplied") for row in inferred))

        for row in generated:
            if not row["record_location"].startswith("Location not supplied"):
                continue
            profile_ids = sync.PROFILE_ID.findall(row["profile_id"])
            if not profile_ids or profile_ids[0] not in profiles:
                continue
            profile = profiles[profile_ids[0]]
            self.assertIsNone(
                sync.infer_location_from_kin(profile, profiles, by_numeric_id, children),
                profile_ids[0],
            )

        audit = json.loads((MAP_AUDIT_DIR / "onetree_ireland_uk_all.json").read_text(encoding="utf-8"))
        self.assertEqual(len(inferred), len(audit["kin_inferred_associations"]))


if __name__ == "__main__":
    unittest.main()
