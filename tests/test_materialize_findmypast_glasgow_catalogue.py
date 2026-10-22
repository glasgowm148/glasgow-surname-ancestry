"""Focused identity safeguards for Findmypast integration decisions."""

import unittest

from tools.materialize_findmypast_glasgow_catalogue import decide


class FindmypastIdentityDecisionTests(unittest.TestCase):
    def setUp(self):
        self.person = {
            "group_id": "fmp-glasgow-0123456789ab", "name": "Example Glasgow",
            "event_year_start": 1700, "event_year_end": 1700,
        }

    def test_empty_completed_search_does_not_establish_a_new_person(self):
        result = decide(self.person, {
            "status": "no_wikitree_match_found", "candidates": [],
        }, None)
        self.assertEqual(result["creation_status"], "HOLD")
        self.assertIn("Compatible candidates and identity-match review remain pending", result["notes"])
        self.assertIn("concrete conflicts", result["notes"])

    def test_surviving_candidate_remains_on_hold(self):
        result = decide(self.person, {"candidates": [{"profile_id": "Glasgow-1"}]}, None)
        self.assertEqual(result["creation_status"], "HOLD")
        self.assertEqual(result["candidate_count"], 1)

    def test_explicit_reviewed_concrete_exclusion_is_preserved(self):
        notes = "Glasgow-1 died in 1690 (cited burial); this record names its subject alive in 1700."
        result = decide(self.person, {"candidates": [{"profile_id": "Glasgow-1"}]}, {
            "outcome": "new_person", "creation_status": "READY", "notes": notes,
        })
        self.assertEqual(result["creation_status"], "READY")
        self.assertEqual(result["decision_source"], "human_override")
        self.assertEqual(result["notes"], notes)

    def test_confirmed_existing_match_still_assigns_profile(self):
        result = decide(self.person, {"confirmed_profile_ids": ["Glasgow-1"]}, None)
        self.assertEqual(result["outcome"], "existing_profile")
        self.assertEqual(result["profile_id"], "Glasgow-1")

    def test_pre1500_free_space_rule_is_unchanged(self):
        result = decide({**self.person, "event_year_start": 1490}, {}, None)
        self.assertEqual(result["outcome"], "free_space")
        self.assertEqual(result["creation_status"], "READY")


if __name__ == "__main__":
    unittest.main()
