"""Tests for canonicalising merged WikiTree profiles."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.project_paths import apply_profile_redirects
from tools.build_family_map import apply_catalogue_profile_links


class ProjectPathTests(unittest.TestCase):
    def test_redirected_profiles_and_family_references_are_canonicalised(self):
        profiles = {
            "Glasgow-1": {"Id": 1, "Name": "Glasgow-1"},
            "Glasgow-2": {"Id": 2, "Name": "Glasgow-2"},
            "Glasgow-3": {
                "Id": 3,
                "Name": "Glasgow-3",
                "Father": 1,
                "Spouses": [{"Id": 1, "Name": "Glasgow-1"}],
            },
        }
        apply_profile_redirects(profiles, {"Glasgow-1": "Glasgow-2"})
        self.assertNotIn("Glasgow-1", profiles)
        self.assertEqual(profiles["Glasgow-3"]["Father"], 2)
        self.assertEqual(
            profiles["Glasgow-3"]["Spouses"],
            [{"Id": 2, "Name": "Glasgow-2"}],
        )

    def test_empty_catalogue_profile_link_registry_is_safe(self):
        records = [{"person": "Test Glasgow", "profile_id": "", "family_group": "Test", "supplement_id": ""}]
        self.assertEqual(apply_catalogue_profile_links(records), 0)
        self.assertEqual(records[0]["profile_id"], "")

    def test_reviewed_catalogue_profile_link_is_applied(self):
        records = [{"person": "Test Glasgow", "profile_id": "", "family_group": "Test", "supplement_id": "test-person"}]
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "links.json"
            registry.write_text(json.dumps({"entries": {"record-test-person": {"profile_id": "Glasgow-123"}}}))
            with patch("tools.build_family_map.WIKITREE_CATALOGUE_PROFILE_LINKS", registry):
                self.assertEqual(apply_catalogue_profile_links(records), 1)
        self.assertEqual(records[0]["profile_id"], "Glasgow-123")


if __name__ == "__main__":
    unittest.main()
