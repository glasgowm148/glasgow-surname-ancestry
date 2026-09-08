"""Offline tests for incremental WikiTree change scanning."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import tools.sync_recent_wikitree_changes as recent_changes
from tools.sync_recent_wikitree_changes import (
    ids_from_feed, is_fatal_failure, is_public_historical, profile_changes,
    redirects_from_envelope,
)


class RecentWikiTreeChangesTests(unittest.TestCase):
    def test_network_feed_html_discovers_profile_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network-feed.html"
            path.write_text(
                '<a href="/wiki/Glasgow-3905">profile</a>'
                '<a href="/index.php?title=Special:NetworkFeed&who=Glasgow-951">feed</a>'
                '<a href="/wiki/Space:Not_a_person">space</a>',
                encoding="utf-8",
            )
            self.assertEqual(ids_from_feed(path), {"Glasgow-3905", "Glasgow-951"})

    def test_parent_changes_are_reported_separately_from_timestamps(self):
        changes = profile_changes(
            {"Name": "Glasgow-951", "Father": 27102720, "Touched": "20260805"},
            {"Name": "Glasgow-951", "Father": 50918987, "Touched": "20260809"},
        )
        self.assertEqual(changes["Father"], {"before": 27102720, "after": 50918987})
        self.assertNotIn("Touched", changes)

    def test_only_public_historical_new_profiles_are_admitted(self):
        self.assertTrue(is_public_historical(
            {"Privacy": 60, "BirthDate": "1811-00-00"}, current_year=2026
        ))
        self.assertTrue(is_public_historical(
            {"Privacy": 50, "DeathDate": "1979-01-01"}, current_year=2026
        ))
        self.assertFalse(is_public_historical(
            {"Privacy": 60, "BirthDate": "1980-01-01"}, current_year=2026
        ))
        self.assertFalse(is_public_historical(
            {"Privacy": 20, "BirthDate": "1811-01-01"}, current_year=2026
        ))

    def test_unavailable_old_profiles_warn_without_failing_the_refresh(self):
        self.assertFalse(is_fatal_failure(
            {"profile_id": "Glasgow-2994", "error": "No public profile returned"}
        ))
        self.assertTrue(is_fatal_failure(
            {"profile_id": "Glasgow-951", "error": "WikiTree API timed out"}
        ))

    def test_redirects_are_recovered_from_result_by_key(self):
        self.assertEqual(
            redirects_from_envelope({
                "resultByKey": {
                    "Glasgow-3681": {
                        "Id": 47893381,
                        "status": "Redirected to 13636618/Glasgow-559",
                    },
                    "Glasgow-559": {"Id": 13636618},
                }
            }),
            {"Glasgow-3681": "Glasgow-559"},
        )

    def test_canonicalising_redirects_updates_index_profile_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "profile-evidence.json"
            index = root / "profiles.json"
            records = root / "records.csv"
            evidence.write_text(json.dumps({
                "profiles": {"Glasgow-1": {}, "Glasgow-2": {}},
            }), encoding="utf-8")
            index.write_text(json.dumps({
                "profile_count": 2,
                "profiles": {"Glasgow-1": {}, "Glasgow-2": {}},
            }), encoding="utf-8")
            records.write_text(
                "profile_id,note\nGlasgow-1,redirect this ID\n"
                "Glasgow-10,do not corrupt Glasgow-1-note or Glasgow-10\n",
                encoding="utf-8",
            )
            with patch.multiple(
                recent_changes,
                WIKITREE_PROFILE_EVIDENCE=evidence,
                SURNAME_PROFILE_INDEX=index,
                MAP_RECORDS=records,
            ):
                recent_changes.canonicalise_local_records({"Glasgow-1": "Glasgow-2"})
            payload = json.loads(index.read_text(encoding="utf-8"))
            self.assertEqual(payload["profile_count"], 1)
            self.assertEqual(set(payload["profiles"]), {"Glasgow-2"})
            records_text = records.read_text(encoding="utf-8-sig")
            self.assertIn("Glasgow-2,redirect this ID", records_text)
            self.assertIn(
                "Glasgow-10,do not corrupt Glasgow-1-note or Glasgow-10",
                records_text,
            )
            self.assertNotIn("Glasgow-20", records_text)


if __name__ == "__main__":
    unittest.main()
