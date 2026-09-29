import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_family_map import location_search_index  # noqa: E402


class LocationSearchIndexTests(unittest.TestCase):
    def test_unmapped_records_do_not_share_aliases(self):
        records = [
            {"location_id": "", "region": "Scotland", "record_location": "Mid Calder, Scotland", "location_basis": ""},
            {"location_id": "", "region": "Ireland", "record_location": "County Antrim", "location_basis": ""},
            {"location_id": "larne", "region": "Ireland", "record_location": "Larne, County Antrim", "location_basis": ""},
        ]
        index = location_search_index(records)
        self.assertNotIn("", index)
        self.assertIn("Ireland", index["larne"])
        self.assertIn("County Antrim", index["larne"])


if __name__ == "__main__":
    unittest.main()
