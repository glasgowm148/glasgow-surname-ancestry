"""Focused regressions for the full-suite defects found during the site audit."""
import unittest

from tools.catalogue_machine_data import compact_resolver_row
from tools.build_research_catalog import _is_complete_profile_draft
from tools.repair_person_hierarchy import _qualified_life_summary


class SuiteContractsTests(unittest.TestCase):
    def test_compact_resolver_preserves_populated_values_and_imports(self):
        original = {"id": "Example-1", "alternate_ids": [], "birth_year": None,
                    "locations": [], "gender": "", "reviewed_relationships": {},
                    "count": 0, "uncertain": False, "parent_ids": ["Example-2"],
                    "imported": {"birth_year": None}, "birth_status": "identity-dependent"}
        compact = compact_resolver_row(original)
        self.assertEqual({"id", "alternate_ids", "count", "uncertain", "parent_ids",
                          "imported", "birth_status"}, set(compact))
        self.assertEqual({"birth_year": None}, compact["imported"])
        self.assertIsNone(original["birth_year"])
        self.assertEqual(compact, compact_resolver_row(compact))

    def test_date_summary_keeps_full_qualifier_without_repeating_it(self):
        vitals = {"birth": {}, "death": {"qualifier": "identity unresolved"}}
        summary = _qualified_life_summary("1811–1888 (probable death)", vitals)
        self.assertIn("identity unresolved", summary)
        self.assertEqual(summary, _qualified_life_summary(summary, vitals))

    def test_corrected_non_glasgow_draft_is_complete_without_wrong_category(self):
        draft = ("== Biography ==\nJohn Gray.<ref>Source</ref>\n== Research Notes ==\n"
                 "Surname corrected from Glasgow.\n== Sources ==\n<references/>")
        self.assertTrue(_is_complete_profile_draft(draft, subject_surname="Gray"))
        self.assertFalse(_is_complete_profile_draft(draft, subject_surname="Glasgow"))
        self.assertFalse(_is_complete_profile_draft(draft.replace("<references/>", ""), subject_surname="Gray"))
