import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import sync_catalogue_research as sync


class ConcurrentCatalogueUpdatesTests(unittest.TestCase):
    def test_merges_only_owned_fields_into_latest_rows(self):
        # These are the fields retained by a long-running sync from its old
        # snapshot. Another publisher has since updated confidence and rows.
        updates = {
            "target": {
                "needs_wikitree_update": True,
                "wikitree_update_summary": "Reviewed amendment",
                "wikitree_update_relationship_changes": [{"father": "Example-2"}],
                "wikitree_update_significance": 80,
                "father_probability_percent": 58,  # must never be merged
            },
            "removed": {"needs_wikitree_update": True},
        }
        latest = [
            {"id": "added", "new_field": "concurrent addition"},
            {"id": "target", "father_probability_percent": 95,
             "needs_wikitree_update": False, "wikitree_update_summary": "old",
             "wikitree_update_relationship_changes": [], "wikitree_update_significance": 0,
             "concurrent_field": "keep"},
            {"id": "unrelated", "name": "Concurrent name", "needs_wikitree_update": True},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            index = root / "data/catalogue-search-index.json"
            index.write_text(json.dumps(latest))
            with patch.object(sync, "WEB", root):
                merged = sync.merge_catalogue_updates(updates)
            expected = json.loads(json.dumps(latest))
            expected[1].update({key: updates["target"][key] for key in sync.CATALOGUE_UPDATE_FIELDS})
            self.assertEqual(merged, expected)
            self.assertEqual(json.loads(index.read_text()), expected)
            packed = (root / "data/people-index.js").read_text()
            self.assertEqual(json.loads(packed.removeprefix("window.glasgowPeopleIndex=").removesuffix(";\n")), expected)
            self.assertNotIn("removed", [row["id"] for row in merged])


if __name__ == "__main__":
    unittest.main()
