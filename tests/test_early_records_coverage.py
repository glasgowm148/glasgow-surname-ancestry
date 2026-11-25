"""Check that Early Records leads to searchable, sourced catalogue people."""


import json
import unittest
from pathlib import Path


from tests._generated_data import requires_generated_data


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "www"
ENTRIES = SITE / "assets/v3/early-entries.json"
FULL_INDEX = SITE / "data/catalogue-search-index.json"
FAST_INDEX = SITE / "data/catalogue-search-fast.json"

# Documentary cases whose accepted identity is already represented by a
# canonical catalogue person.  Keep this list explicit so a new held case
# cannot silently disappear from search without a reviewed mapping.
REVIEWED_SUCCESSORS = {
    "record-edinburgh-1577-andrew-glasgow": "Glasgow-3589",
    "record-corsoun-1598-isobel-glasgow": "Glasgow-3336",
    "record-corsoun-1598-janet-glasgow": "Glasgow-3183",
    "record-corsoun-1598-marion-glasgow": "Glasgow-4095",
    "record-corsoun-1598-robert-glasgow": "Glasgow-4006",
}


@requires_generated_data
class EarlyRecordsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads(ENTRIES.read_text())
        cls.full = json.loads(FULL_INDEX.read_text())
        cls.fast = json.loads(FAST_INDEX.read_text())
        cls.full_by_id = {
            ident.casefold(): row
            for row in cls.full
            for ident in [row["id"], *row.get("profile_ids", [])]
        }
        fields = {name: index for index, name in enumerate(cls.fast["fields"])}

        def unpack(value):
            if isinstance(value, int) and value < 0:
                return cls.fast["strings"][-value - 1]
            if isinstance(value, list):
                return [unpack(item) for item in value]
            return value

        cls.fast_by_id = {}
        for packed in cls.fast["rows"]:
            row = {name: unpack(packed[index]) for name, index in fields.items()}
            for ident in [row.get("id", ""), *row.get("profile_ids", [])]:
                if ident:
                    cls.fast_by_id[ident.casefold()] = row

    def test_people_entries_have_public_routes_and_search_membership(self):
        for row in self.entries:
            self.assertTrue(row.get("slug"), row["id"])
            slug = row["slug"]
            page = SITE / "people" / f"{slug}.html"
            self.assertTrue(page.is_file(), f"early entry has no public route: {slug}")
            successor = REVIEWED_SUCCESSORS.get(row["id"])
            if successor:
                self.assertEqual(slug, successor.casefold(), row["id"])
            self.assertIn(slug.casefold(), self.full_by_id, row["id"])
            self.assertIn(slug.casefold(), self.fast_by_id, row["id"])

    def test_held_medieval_occurrences_are_not_creation_ready(self):
        indexed = {row["id"].casefold(): row for row in self.full}
        medieval = [
            row for row in self.entries
            if row["id"].startswith("record-medieval-")
        ]
        self.assertGreaterEqual(len(medieval), 20)
        for row in medieval:
            catalogue = indexed.get(row["id"].casefold())
            self.assertIsNotNone(catalogue, row["id"])
            self.assertNotEqual(
                catalogue.get("profile_work_status"),
                "creation_ready",
                row["id"],
            )

    def test_marjory_reading_keeps_1577_record_on_canonical_profile(self):
        row = next(
            row for row in self.entries
            if row["id"] == "record-edinburgh-1577-andrew-glasgow"
        )
        self.assertEqual(REVIEWED_SUCCESSORS[row["id"]], "Glasgow-3589")
        self.assertIn("Marjory", row["name"])
        self.assertEqual(self.full_by_id["glasgow-3589"]["name"], "Marjory Glasgow")


if __name__ == "__main__":
    unittest.main()
