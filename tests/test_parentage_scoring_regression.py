"""Regression checks for targeted, provenance-aware parent scoring."""

import unittest

from tools.build_research_catalog import _potential_parentage


def person(profile_id, name, birth, *, children=None, parents=None, locations=None):
    return {
        "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
        "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
        "birth_year": birth, "death_year": None, "gender": "Male",
        "birth_place": "County Antrim, Ireland", "birth_surnames": ["Glasgow"],
        "current_surnames": ["Glasgow"],
        "locations": locations or ["County Antrim, Ireland"],
        "parent_ids": parents or [], "spouse_ids": [], "spouse_names": [],
        "child_ids": children or [], "child_names": [], "_child_links": [],
        "_parent_links": [], "_sibling_ids": [], "_sibling_links": [],
        "sibling_names": [], "occupations": [], "_dated_records": [],
    }


class ParentageScoringRegressionTests(unittest.TestCase):
    def test_unproved_branch_clues_are_capped_and_target_filter_is_honoured(self):
        ohio = [
            "County Antrim, Ireland",
            "Columbus, Franklin County, Ohio, United States",
        ]
        people = [
            person("Glasgow-1", "Alexander Glasgow", 1800, children=["Glasgow-2"]),
            person("Glasgow-2", "Zephaniah Glasgow", 1825, parents=["Glasgow-1"], locations=ohio),
            person("Glasgow-3", "John Glasgow", 1765, children=["Glasgow-4"]),
            person("Glasgow-4", "Zephaniah Glasgow", 1795, parents=["Glasgow-3"], locations=ohio),
        ]
        result = _potential_parentage(people, requested_subject_ids={"Glasgow-1"})
        self.assertEqual({"Glasgow-1"}, set(result))
        candidate = next(item for item in result["Glasgow-1"]["candidates"] if item["id"] == "Glasgow-3")
        self.assertEqual(39, candidate["score"])
        self.assertIn("unproved or merely possible", " ".join(candidate["conflicts"]))


if __name__ == "__main__":
    unittest.main()
