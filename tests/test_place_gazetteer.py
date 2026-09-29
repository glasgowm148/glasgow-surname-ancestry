import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from apply_place_gazetteer import apply_entries  # noqa: E402
from build_family_map import location_search_index  # noqa: E402
from place_gazetteer import aliases_for_text, derive_gazetteer  # noqa: E402


GAZETTEER = {
    "entries": {
        "rasharkin": {
            "name": "Rasharkin", "county": "Antrim", "country": "Ireland",
            "aliases": ["Northern Ireland", "Ulster"], "provenance": "derived: 2 records",
        }
    },
    "ambiguous": {"cross": {"counties": ["Antrim", "Londonderry"]}},
}


class PlaceGazetteerTests(unittest.TestCase):
    def test_derivation_keeps_unambiguous_and_excludes_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "records.csv"
            with records.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["record_location", "location_basis", "region", "location_id"])
                writer.writeheader()
                writer.writerows([
                    {"record_location": "Rasharkin", "location_basis": "", "region": "Ireland", "location_id": "rasharkin"},
                    {"record_location": "Cross", "location_basis": "", "region": "Ireland", "location_id": "ballymoney_town"},
                    {"record_location": "Cross", "location_basis": "", "region": "Ireland", "location_id": "boveedy"},
                ])
            index = root / "index.json"
            index.write_text("[]", encoding="utf-8")
            result = derive_gazetteer(records, index)
        self.assertEqual(result["entries"]["rasharkin"]["county"], "Antrim")
        self.assertNotIn("cross", result["entries"])
        self.assertEqual(result["ambiguous"]["cross"]["counties"], ["Antrim", "Londonderry"])

    def test_alias_derivation(self):
        aliases = aliases_for_text("Rasharkin civil parish", GAZETTEER)
        self.assertTrue({"Antrim", "County Antrim", "Ireland", "Northern Ireland", "Ulster"} <= aliases)

    def test_future_location_index_uses_gazetteer(self):
        index = location_search_index([{
            "location_id": "rasharkin", "region": "Ireland", "record_location": "Rasharkin", "location_basis": "",
        }])
        self.assertIn("County Antrim", index["rasharkin"])

    def test_tiny_fixture_is_idempotent(self):
        people = [{"id": "test-1", "locations": ["Rasharkin"], "birth_location": "", "death_location": "", "regions": [], "location_aliases": []}]
        self.assertEqual(apply_entries(people, GAZETTEER), 1)
        self.assertIn("County Antrim", people[0]["location_aliases"])
        self.assertEqual(apply_entries(people, GAZETTEER), 0)


if __name__ == "__main__":
    unittest.main()
