#!/usr/bin/env python3
"""Focused checks for the unlinked WikiTree profile audit."""

from pathlib import Path
from tempfile import TemporaryDirectory
import csv
from hashlib import sha1
import json
import unittest

from tools.audit_missing_wikitree_profiles import (
    candidate_summary,
    candidate_parent_names,
    complete_profile_draft,
    discover_drafts,
    draft_is_creation_ready,
    draft_is_on_hold,
    free_space_audit_entry,
    load_audit_people,
    new_draft_match,
)


class MissingWikiTreeProfileAuditTest(unittest.TestCase):
    def test_candidate_parents_accept_both_api_collection_shapes(self):
        parents = [
            {"Gender": "Male", "BirthName": "John Glasgow"},
            {"Gender": "Female", "BirthName": "Jean Weir"},
        ]
        expected = {"father": "John Glasgow", "mother": "Jean Weir"}
        self.assertEqual(candidate_parent_names({"Parents": parents}), expected)
        self.assertEqual(
            candidate_parent_names({"Parents": {"1": parents[0], "2": parents[1]}}),
            expected,
        )

    def test_authoritative_records_overlay_precedes_final_catalogue_build(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            people_path = root / "people.json"
            records_path = root / "records.csv"
            people_path.write_text(json.dumps({"people": [
                {"catalogue_id": "record-new-person", "name": "Stale Name", "profile_ids": []},
                {"catalogue_id": "record-linked-person", "name": "Stale Linked", "profile_ids": []},
            ]}), encoding="utf-8")
            fieldnames = (
                "person", "profile_id", "supplement_id", "birth_date", "birth_status",
                "birth_location", "death_date", "death_location", "gender", "record_location",
                "region", "year", "association", "subcluster", "source_title", "family_group",
            )
            with records_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({
                    "person": "Fresh Person", "profile_id": "", "supplement_id": "new-person",
                    "birth_date": "1700-00-00", "birth_status": "before",
                    "record_location": "Irvine", "region": "Scotland", "year": "1720",
                    "association": "Recorded 1720", "source_title": "Primary record",
                })
                writer.writerow({
                    "person": "Linked Person", "profile_id": "Glasgow-1",
                    "supplement_id": "linked-person", "source_title": "Linked record",
                })
            people = load_audit_people(
                people_path, records_path,
                draft_paths={
                    "record-new-person": "surname-research/new-people/Fresh.md",
                    "record-linked-person": "surname-research/new-people/Linked.md",
                },
            )

        by_id = {person["catalogue_id"]: person for person in people}
        self.assertEqual(by_id["record-new-person"]["name"], "Fresh Person")
        self.assertEqual(by_id["record-new-person"]["recorded_in"], ["Irvine"])
        self.assertNotIn("record-linked-person", by_id)

    def test_linked_namesake_does_not_hide_unlinked_row_with_same_fallback_id(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            people_path = root / "people.json"
            records_path = root / "records.csv"
            key = "Hugh Glasgow|Shared research group"
            catalogue_id = f"record-hugh-glasgow-{sha1(key.encode()).hexdigest()[:10]}"
            people_path.write_text(json.dumps({"people": [{
                "catalogue_id": catalogue_id,
                "name": "Hugh Glasgow",
                "profile_ids": [],
            }]}), encoding="utf-8")
            fieldnames = (
                "person", "profile_id", "supplement_id", "birth_date", "birth_status",
                "birth_location", "death_date", "death_location", "gender", "record_location",
                "region", "year", "association", "subcluster", "source_title", "family_group",
            )
            with records_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({
                    "person": "Hugh Glasgow", "profile_id": "Glasgow-1",
                    "family_group": "Shared research group", "year": "1740",
                    "association": "Linked household", "source_title": "1740 return",
                })
                writer.writerow({
                    "person": "Hugh Glasgow", "profile_id": "",
                    "family_group": "Shared research group", "year": "1772",
                    "association": "Unresolved parish declaration",
                    "source_title": "1772 declaration",
                })

            people = load_audit_people(
                people_path, records_path,
                draft_paths={
                    catalogue_id: "surname-research/new-people/Hugh.md",
                },
            )

        by_id = {person["catalogue_id"]: person for person in people}
        self.assertIn(catalogue_id, by_id)
        self.assertEqual(
            [record["association"] for record in by_id[catalogue_id]["records"]],
            ["Unresolved parish declaration"],
        )

    def test_generated_fmp_marker_maps_to_catalogue_identity(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            draft_dir = root / "surname-research" / "new-people"
            draft_dir.mkdir(parents=True)
            path = draft_dir / "1703_Scotland_Irvine_Janet_Glasgow.md"
            path.write_text(
                "<!-- BEGIN FMP-GLASGOW-fmp-glasgow-5333ccc1e75f -->\n",
                encoding="utf-8",
            )

            drafts = discover_drafts(draft_dir, root, known_drafts={})

        self.assertEqual(
            drafts["record-fmp-glasgow-5333ccc1e75f"],
            "surname-research/new-people/1703_Scotland_Irvine_Janet_Glasgow.md",
        )

    def test_explicit_non_marker_drafts_are_registered(self):
        drafts = discover_drafts()
        self.assertIn("record-saltcoats-1637-john-glasgow", drafts)
        self.assertIn("record-saltcoats-1637-katherine-glasgow", drafts)
        self.assertIn("record-james-glasgow-oritor-gentleman-1826-probate-occurrence", drafts)
        self.assertIn("record-james-glasgow-killycurragh-1836-probate-occurrence", drafts)

    def test_canonical_space_page_is_terminal_and_never_searched(self):
        entry = free_space_audit_entry({
            "catalogue_id": "record-medieval-1289-alexander-escheator",
            "name": "Alexander de Glasgow",
            "wikitree_free_space_url": "https://www.wikitree.com/wiki/Space:Andrew_de_Glasgu",
        })
        self.assertEqual(entry["identity_status"], "free_space_only")
        self.assertEqual(entry["recommended_action"], "do_not_create")
        self.assertEqual(entry["searched_profile_count"], 0)
        self.assertEqual(entry["search_terms"], [])
        self.assertEqual(entry["draft_path"], "")

    def test_reviewed_documentary_disposition_is_terminal_without_live_space_url(self):
        entry = free_space_audit_entry({
            "catalogue_id": "record-source-anomaly",
            "name": "Agnes Glasgow",
            "profile_disposition": "free_space_only",
            "free_space_draft_path": "surname-research/free-space-pages/Record_Corrections.md",
        })
        self.assertEqual(entry["recommended_action"], "do_not_create")
        self.assertEqual(entry["identity_status"], "free_space_only")
        self.assertEqual(
            entry["draft_path"],
            "surname-research/free-space-pages/Record_Corrections.md",
        )

    def test_only_top_status_banner_places_complete_draft_on_hold(self):
        ready = """> **READY TO CREATE**

# Janet Glasgow

[[Category:Glasgow Name Study]]
== Biography ==
Janet was baptised.<ref>Register.</ref>
== Research Notes ==
Reviewed HOLD reason: an earlier candidate was rejected.
== Sources ==
<references />
"""
        held = ready.replace("> **READY TO CREATE**", "> **HOLD TO CREATE**")
        self.assertTrue(complete_profile_draft(ready))
        self.assertFalse(draft_is_on_hold(ready))
        self.assertTrue(draft_is_on_hold(held))
        self.assertTrue(draft_is_creation_ready(ready))
        self.assertFalse(draft_is_creation_ready(held))

    def test_periodic_match_accepts_builder_creation_status(self):
        candidate = {
            "profile_id": "Glasgow-9999", "score": 90,
            "birth_year_match": True, "death_year_match": False,
        }
        self.assertEqual(
            new_draft_match(
                [candidate],
                {
                    "recommended_action": "create_new_profile", "candidates": [],
                    "allow_auto_match": True,
                },
            ),
            candidate,
        )
        self.assertIsNone(new_draft_match(
            [candidate], {"recommended_action": "create_new_profile", "candidates": []}
        ))

    def test_baptism_candidates_use_child_chronology_and_birth_surname(self):
        person = {
            "name": "Mary Glasgow",
            "birth": "c. 1745 (estimated)",
            "birth_location": "Irvine, Scotland",
            "recorded_in": ["Irvine, Scotland"],
            "regions": ["Scotland"],
            "records": [{"association": "Baptism 21 Apr 1745", "subcluster": "baptism"}],
        }
        adult = {
            "Name": "Barber-1", "LongName": "Mary (Barber) Glasgow",
            "LastNameAtBirth": "Barber", "LastNameCurrent": "Glasgow",
            "BirthDate": "1730-00-00", "DeathDate": "0000-00-00",
            "BirthLocation": "Irvine, Ayrshire, Scotland", "DeathLocation": "",
        }
        child = {
            "Name": "Glasgow-1", "LongName": "Mary Glasgow",
            "LastNameAtBirth": "Glasgow", "LastNameCurrent": "Glasgow",
            "BirthDate": "1745-00-00", "DeathDate": "0000-00-00",
            "BirthLocation": "Irvine, Ayrshire, Scotland", "DeathLocation": "",
        }
        self.assertIsNone(candidate_summary(adult, person, 1745))
        self.assertIsNotNone(candidate_summary(child, person, 1745))

    def test_candidate_rejects_conflicting_given_name_gender_or_parent(self):
        person = {
            "name": "Joan Glasgow", "gender": "Female",
            "birth": "c. 1702 (estimated)", "birth_location": "",
            "recorded_in": ["Stevenston, Scotland"], "regions": ["Scotland"],
            "documentary_relatives": {"father": "James Glasgow"},
            "records": [{"association": "Baptism 19 Jul 1702", "subcluster": "baptism"}],
        }
        candidate = {
            "Name": "Glasgow-1", "FirstName": "John", "RealName": "John",
            "LongName": "John Glasgow", "Gender": "Male",
            "LastNameAtBirth": "Glasgow", "LastNameCurrent": "Glasgow",
            "BirthDate": "1702-07-19", "DeathDate": "0000-00-00",
            "BirthLocation": "Stevenston, Ayrshire, Scotland", "DeathLocation": "",
            "Parents": {},
        }
        self.assertIsNone(candidate_summary(candidate, person, 1702))

        candidate.update({"FirstName": "Joan", "RealName": "Joan", "Gender": "Female"})
        candidate["Parents"] = {
            "1": {"Gender": "Male", "BirthName": "William Glasgow"},
        }
        self.assertIsNone(candidate_summary(candidate, person, 1702))

    def test_neighbouring_sibling_is_a_lead_not_a_duplicate_hold(self):
        person = {
            "catalogue_id": "test", "name": "John Glasgow", "gender": "Male",
            "birth": "c. 1736 (estimated)", "birth_location": "",
            "recorded_in": ["Irvine, Scotland"], "regions": ["Scotland"],
            "documentary_relatives": {
                "father": "Robt Glasgow", "mother": "Mary Borland",
            },
            "records": [{"association": "Baptism 10 Oct 1736", "subcluster": "baptism"}],
        }
        candidate = {
            "Name": "Glasgow-3478", "FirstName": "John", "Gender": "Male",
            "LastNameAtBirth": "Glasgow", "LastNameCurrent": "Glasgow",
            "BirthDate": "1738-09-04", "DeathDate": "0000-00-00",
            "BirthLocation": "Irvine, Ayrshire, Scotland", "DeathLocation": "",
            "Parents": {
                "1": {"Gender": "Male", "BirthName": "Robert Glasgow"},
                "2": {"Gender": "Female", "BirthName": "Mary Borland"},
            },
        }
        summary = candidate_summary(candidate, person, 1736)
        self.assertIsNotNone(summary)
        self.assertTrue(summary["birth_year_conflict"])
        self.assertEqual(summary["exact_relative_roles"], ["father", "mother"])
        self.assertLessEqual(summary["score"], 65)


if __name__ == "__main__":
    unittest.main()
