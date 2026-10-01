import unittest

from tools.catalogue_field_status import field_statuses


class CatalogueFieldStatusTests(unittest.TestCase):
    def test_date_and_place_marks_are_independent(self):
        person = {
            "birth": "1811", "birth_location": "County Antrim",
            "death": "1888-05-16", "death_location": "Gortahar",
            "wikitree_evidence": [{"profile_fields": {"DataStatus": {
                "BirthDate": "certain", "BirthLocation": "guess",
                "DeathDate": "guess", "DeathLocation": "certain",
            }}}],
        }
        self.assertEqual(field_statuses(person), {
            "birth": "certain", "birth_location": "uncertain",
            "death": "uncertain", "death_location": "certain",
        })

    def test_qualifiers_and_conflicting_marks_keep_caution(self):
        person = {
            "birth": "c. 1811", "birth_location": "County Antrim — locality unproved",
            "death": "after 1891-10-31", "death_location": "Belfast",
            "wikitree_evidence": [
                {"profile_fields": {"DataStatus": {key: "certain" for key in
                    ("BirthDate", "BirthLocation", "DeathDate", "DeathLocation")}}},
                {"profile_fields": {"DataStatus": {"DeathLocation": "guess"}}},
            ],
        }
        self.assertEqual(field_statuses(person), {
            "birth": "estimated", "birth_location": "uncertain",
            "death": "after", "death_location": "uncertain",
        })

    def test_missing_marks_and_full_dates_do_not_imply_certainty(self):
        person = {"birth": "1811-01-01", "birth_location": "", "death": "",
                  "death_location": "Belfast", "wikitree_evidence": [{"profile_fields": {}}]}
        self.assertEqual(field_statuses(person), {"birth": "unmarked", "death_location": "unmarked"})
