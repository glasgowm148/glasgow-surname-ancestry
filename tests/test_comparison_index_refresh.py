import json
import tempfile
import unittest
from pathlib import Path

from tools.build_research_catalog import write_comparison_index
from tools.public_privacy import PublicPrivacy
from tools.refresh_comparison_index import _public_dossiers


class ComparisonIndexRefreshTests(unittest.TestCase):
    def test_reviewed_candidates_are_added_and_existing_dossiers_preserved(self):
        dossiers = {
            "record-existing": {
                "id": "Glasgow-1", "catalogue_id": "record-existing", "name": "Existing",
                "relationships": {}, "identity": {}, "evidence": [], "open_questions": [],
            }
        }
        candidates = [
            {"profile_id": profile_id, "name": "John Gray", "url": f"https://www.wikitree.com/wiki/{profile_id}"}
            for profile_id in ("Gray-16804", "Gray-25428", "Gray-32315", "Gray-42340")
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "compare-index.js"
            write_comparison_index(
                dossiers, {"record-john": {"candidates": candidates}}, output=output
            )
            text = output.read_text(encoding="utf-8")
        self.assertIn('"catalogue_id":"record-existing"', text)
        for profile_id in ("Gray-16804", "Gray-25428", "Gray-32315", "Gray-42340"):
            self.assertIn(f'"id":"{profile_id}"', text)

    def test_privacy_projection_excludes_withheld_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "compare-index.js"
            write_comparison_index(
                {}, {"audit": {"candidates": [
                    {"profile_id": "Public-1", "name": "Public"},
                    {"profile_id": "Living-2", "name": "Withheld"},
                ]}}, output=output, privacy=PublicPrivacy({"Living-2": {"BirthDate": "2000-01-01"}})
            )
            text = output.read_text(encoding="utf-8")
        self.assertIn('"id":"Public-1"', text)
        self.assertNotIn("Living-2", text)

    def test_broken_public_dossier_is_reported_instead_of_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "www/people"
            folder.mkdir(parents=True)
            (folder / "example-1.json").write_text("broken JSON")
            with self.assertRaises(json.JSONDecodeError):
                _public_dossiers(root)


if __name__ == "__main__":
    unittest.main()
