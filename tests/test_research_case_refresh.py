"""A source refresh must not remove family context outside its small build."""
from copy import deepcopy
import unittest

from tools.add_research_case_dossiers import retain_case_context, retain_catalogue_context


class ResearchCaseRefreshTests(unittest.TestCase):
    def test_new_source_retains_reviewed_person_relatives_and_comparison(self):
        previous = {
            "name": "Hugh Glasgow",
            "vitals": {"birth": {"date": "1705", "status": "possible"}},
            "relationships": {
                "children": [{"id": "Glasgow-1510", "claim_id": "C-child"}],
                "siblings": [{"id": "Glasgow-1143"}],
            },
            "imported": {"sections": {"relationships": {"parents": []}}},
            "wikitree_update": {"pending": True, "draft_wikitext": "complete draft"},
            "evidence": [{"id": "E-old", "assertion": "earlier record"}],
            "claims": [{"id": "C-child", "provenance": "reconstructed_parent_reference"}],
            "source_summary": [{"title": "Earlier record", "url": "https://example.org/old"}],
        }
        fresh = {
            "name": "Hugh Glasgow R.E", "relationships": {"children": [], "siblings": []},
            "evidence": [{"id": "E-new", "assertion": "newly catalogued mortgage"}],
            "claims": [{"id": "C-mortgage", "evidence_ids": ["E-new"]}],
            "source_summary": [{"title": "Mortgage", "url": "https://example.org/new"}],
        }
        saved = deepcopy(previous)
        result = retain_case_context(fresh, previous)
        for field in ("name", "vitals", "relationships", "imported", "wikitree_update"):
            self.assertEqual(result[field], previous[field])
        self.assertEqual({item["id"] for item in result["evidence"]}, {"E-old", "E-new"})
        self.assertEqual({item["id"] for item in result["claims"]}, {"C-child", "C-mortgage"})
        self.assertEqual(len(result["source_summary"]), 2)
        self.assertEqual(retain_case_context(fresh, result), result)
        self.assertEqual(previous, saved)

    def test_refresh_keeps_existing_root_and_location_filters(self):
        previous = {
            "name": "Hugh Glasgow", "family_root": {"id": "Glasgow-3970"},
            "family_roots": [{"id": "Glasgow-3970"}],
            "location_groups": [{"country": "Ireland", "locality": "Larne"}],
            "children": [{"id": "Glasgow-1510"}], "record_count": 4,
            "needs_wikitree_update": True, "source_qualities": ["original"],
            "claim_statuses": ["possible"],
        }
        fresh = {
            "name": "Hugh Glasgow R.E", "family_root": None, "family_roots": [],
            "location_groups": [], "children": [], "record_count": 0,
            "needs_wikitree_update": False, "source_qualities": ["derivative"],
            "claim_statuses": ["unknown"],
        }
        result = retain_catalogue_context(fresh, previous)
        for field in previous.keys() - {"source_qualities", "claim_statuses"}:
            self.assertEqual(result[field], previous[field])
        self.assertEqual(result["source_qualities"], ["original", "derivative"])
        self.assertEqual(result["claim_statuses"], ["possible", "unknown"])


if __name__ == "__main__":
    unittest.main()
