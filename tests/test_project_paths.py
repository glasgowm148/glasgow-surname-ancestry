"""Tests for canonical project paths, exports and safe writes."""

import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tools.project_paths as project_paths
from tests._generated_data import requires_generated_data
from tools.project_paths import apply_profile_redirects
from tools.build_family_map import apply_catalogue_profile_links, rebuild_standalone_onetree


class ProjectPathTests(unittest.TestCase):
    def test_relationship_collections_accept_list_and_dictionary_shapes(self):
        parent = {"Name": "Glasgow-1"}
        self.assertEqual(project_paths.relation_values({"Parents": [parent]}, "Parents"), [parent])
        self.assertEqual(
            project_paths.relation_values({"Parents": {"1": parent}}, "Parents"),
            [parent],
        )
        self.assertEqual(
            project_paths.relation_values({"Parents": "malformed"}, "Parents"),
            [],
        )

    @requires_generated_data
    def test_catalogue_build_refreshes_standalone_one_tree(self):
        with patch("tools.build_family_map.subprocess.run") as run:
            rebuild_standalone_onetree()
        run.assert_called_once()
        self.assertTrue(run.call_args.kwargs["check"])

    def test_atomic_text_writer_replaces_complete_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("old", encoding="utf-8")
            project_paths.atomic_write_text(path, "new\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(list(path.parent.glob(f".{path.name}.*")), [])

    def test_atomic_csv_writer_preserves_unicode_and_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.csv"
            project_paths.atomic_write_csv(
                path, ["name", "place"], [{"name": "Élise", "place": "Ayr"}]
            )
            with path.open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(
                    list(csv.DictReader(handle)),
                    [{"name": "Élise", "place": "Ayr"}],
                )

    def test_atomic_csv_writer_accepts_unix_line_endings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.csv"
            project_paths.atomic_write_csv(
                path,
                ["name"],
                [{"name": "Glasgow"}],
                encoding="utf-8",
                lineterminator="\n",
            )
            self.assertEqual(path.read_bytes(), b"name\nGlasgow\n")

    def test_export_filename_timestamp_beats_filesystem_mtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            newer = root / "ONT_Glas_2026-02-01T00_00.json"
            older = root / "ONT_Glas_2026-01-01T00_00.json"
            for path, marker in ((newer, "newer"), (older, "older")):
                path.write_text(json.dumps({"data": {
                    "1": {"Name": "Glasgow-1", "marker": marker}
                }}), encoding="utf-8")

            # Return the files in the opposite order and make the older export
            # the most recently copied file.  Neither should affect precedence.
            older.touch()

            class ReverseDirectory:
                def glob(self, _pattern):
                    return [newer, older]

            with patch.object(project_paths, "ONETREE_EXPORT_DIR", ReverseDirectory()):
                profiles, exports = project_paths.merged_onetree_profiles()

        self.assertEqual([path.name for path in exports], [older.name, newer.name])
        self.assertEqual(profiles["Glasgow-1"]["marker"], "newer")

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
