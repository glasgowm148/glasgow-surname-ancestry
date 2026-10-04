import json
import tempfile
import unittest
from pathlib import Path

from tools.source_collection_index import build_index


def fixture(doc, row=None):
    root = Path(tempfile.mkdtemp())
    (root / "assets/v3/sources").mkdir(parents=True)
    row = row or {"id": "s-test", "title": doc.get("title", ""), "members": [], "records": 0, "citations": 1}
    (root / "assets/v3/source-index.json").write_text(json.dumps([row]))
    (root / "assets/v3/sources/s-test.json").write_text(json.dumps(doc))
    return root


def row_only_fixture(row):
    root = Path(tempfile.mkdtemp())
    (root / "assets/v3/sources").mkdir(parents=True)
    (root / "assets/v3/source-index.json").write_text(json.dumps([row]))
    return root


class SourceCollectionIndexTest(unittest.TestCase):
    def test_census_title_year_wins_over_person_dates(self):
        root = fixture({"title": "1851 census, Glasgow", "records": [{"date": "1849", "place": "Glasgow"}]})
        item = build_index(root)[0]
        self.assertEqual((item["year"], item["year_basis"]), (1851, "source title"))
        self.assertIn("census", item["categories"])

    def test_profile_wrapper_is_pedigree_not_bmd(self):
        root = fixture({"title": "WikiTree profile export for Glasgow-1", "citations": [{"type": "birth", "date": "1700"}]})
        item = build_index(root)[0]
        self.assertEqual(item["categories"], ["pedigrees"])
        self.assertEqual(item["original_kind"], "profile")

    def test_multiple_explicit_types_and_shared_record_year(self):
        root = fixture({"title": "Birth and marriage parish register", "records": [{"type": "birth and marriage", "date": "1690", "place": "Dublin"}], "url": "https://example.org/register"})
        item = build_index(root)[0]
        self.assertTrue({"births", "marriages", "church"}.issubset(item["categories"]))
        self.assertEqual((item["year"], item["year_basis"]), (1690, "record dates"))

    def test_ambiguous_years_and_surname_do_not_imply_country(self):
        root = fixture({"title": "Glasgow family notes 1700 1750", "records": [{"place": "Unknown locality"}]})
        item = build_index(root)[0]
        self.assertIsNone(item["year"])
        self.assertEqual(item["countries"], [])

    def test_signed_url_is_rejected(self):
        root = fixture({"title": "Newspaper record", "url": "https://example.org/a?signature=secret"})
        item = build_index(root)[0]
        self.assertIsNone(item["original_url"])
        self.assertEqual(item["original_kind"], "none")

    def test_source_name_does_not_inherit_event_categories(self):
        root = fixture({"title": "National Archives 1851 Irish Census", "records": [{"association": "birth and military service", "date": "1840", "place": "Londonderry"}]})
        item = build_index(root)[0]
        self.assertEqual(item["categories"], ["census"])
        self.assertIn("Ireland", item["countries"])
        self.assertNotIn("England", item["countries"])

    def test_opr_is_church_source_and_glasgow_surname_is_not_country(self):
        root = fixture({"title": "Scotland's People OPR register", "records": [{"association": "Glasgow family", "place": "Unknown locality"}]})
        item = build_index(root)[0]
        self.assertIn("church", item["categories"])
        self.assertNotIn("land-tax", item["categories"])
        self.assertIn("Scotland", item["countries"])

    def test_ancestry_census_is_original_provider(self):
        root = fixture({"title": "1851 census", "url": "https://www.ancestry.com/record/123"})
        item = build_index(root)[0]
        self.assertIn("census", item["categories"])
        self.assertNotIn("pedigrees", item["categories"])
        self.assertEqual(item["original_kind"], "record or provider")

    def test_missing_detail_uses_public_index_row(self):
        root = row_only_fixture({"id": "s-test", "title": "1901 census", "members": [], "records": 0, "citations": 1})
        self.assertEqual(build_index(root)[0]["year"], 1901)

    def test_generic_census_does_not_use_unrelated_birth_date(self):
        root = fixture({"title": "Census source", "records": [{"type": "birth", "date": "1849", "place": "Glasgow"}]})
        item = build_index(root)[0]
        self.assertIsNone(item["year"])
        self.assertEqual(item["year_basis"], "unknown")

    def test_profile_dates_never_assign_source_year(self):
        root = fixture({"title": "WikiTree profile export for Glasgow-1851", "events": [{"type": "birth", "date": "1700"}]})
        item = build_index(root)[0]
        self.assertIsNone(item["year"])

    def test_census_access_date_and_archive_numbers_do_not_hide_enumeration(self):
        root = fixture({"title": '1851 Census: "1851 Scotland Census", accessed 11 July 2026; Roll 1114; born 1813'})
        item = build_index(root)[0]
        self.assertEqual(item["years"], [1851])
        self.assertEqual(item["year"], 1851)
        self.assertEqual(item["countries"], ["Scotland"])

    def test_enumeration_district_and_database_date_are_not_census_years(self):
        root = fixture({"title": '1910 Census: "1910 United States Federal Census" Date: 2006; Enumeration District: 1266; Year: 1910; Born in Ireland'})
        item = build_index(root)[0]
        self.assertEqual(item["years"], [1910])
        self.assertEqual(item["countries"], ["United States"])

    def test_unresolved_census_does_not_use_access_date_or_roll_number(self):
        item = build_index(fixture({"title": "Census source; accessed 2026; Roll 1114"}))[0]
        self.assertIsNone(item["year"])
        self.assertEqual(item["years"], [])

    def test_original_nai_household_url_supplies_enumeration_year(self):
        item = build_index(fixture({"title": "Alexander Glasgow household, accessed 2026", "url": "https://www.census.nationalarchives.ie/pages/1851/Antrim/Rasharkin/Lisnagaver/35/"}))[0]
        self.assertEqual(item["years"], [1851])
        self.assertEqual(item["countries"], ["Ireland"])

    def test_shared_census_reference_keeps_both_explicit_years(self):
        item = build_index(fixture({"title": "1901 Census of Ireland and 1911 Census of Ireland, accessed 2026"}))[0]
        self.assertIsNone(item["year"])
        self.assertEqual(item["years"], [1901, 1911])

    def test_access_note_does_not_hide_later_census_in_shared_reference(self):
        item = build_index(fixture({"title": "1901 Census of Ireland, accessed 10 August 2026; 1911 Census of Ireland"}))[0]
        self.assertEqual(item["years"], [1901, 1911])

    def test_linked_census_person_keeps_public_name_for_search(self):
        root = fixture({"title": "1851 Census of Ireland", "citations": [{"person": "Glasgow-951", "name": "Alexander Glasgow"}]}, {"id": "s-test", "title": "1851 Census of Ireland", "members": ["glasgow-951"], "citations": 1})
        self.assertEqual(build_index(root)[0]["people"], [{"id": "glasgow-951", "name": "Alexander Glasgow"}])


if __name__ == "__main__":
    unittest.main()
