"""Focused tests for birth-qualified, separately inspected Findmypast records."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import prepare_findmypast_glasgow_integration as prep


def detail(**fields):
    return {
        "access_status": "accessible", "surname_status": "confirmed",
        "title": "Inspected transcript", "url": "https://example.org/transcript",
        "transcript_fields": {"First name(s)": "John", "Last name": "Glasgow", **fields},
    }


class BirthScopeTests(unittest.TestCase):
    def test_explicit_unproved_birth_surname_is_scope_hold_only(self):
        for status in ("unknown", "unproved", "conflicting"):
            with self.subTest(status=status):
                item = detail(**{"Burial year": "1700"})
                item["birth_surname_status"] = status
                record, reason = prep.detail_identity("a", {}, item, 1800)
                self.assertIsNone(record)
                self.assertEqual(prep.outcome_for(reason, item, True), "unresolved_review")
                self.assertIsNotNone(prep.detail_identity("a", {}, item)[0])
        # No inferred LNAB policy: ordinary surname-confirmed records still qualify.
        self.assertIsNotNone(prep.detail_identity("b", {}, detail(**{"Burial year": "1700"}), 1800)[0])

    def test_reinspection_merges_fields_and_updates_access_metadata(self):
        original = detail(**{"Birth year": "1786", "Country": "Scotland", "Age": "-"})
        original.update({"captured_at": "2026-09-03", "block_reason": "daily_limit"})
        inspected = {"access_status": "accessible", "captured_at": "2026-10-22", "title": "New title",
                     "url": "https://example.org/new", "transcript_fields": {"Birth year": "1786", "Country": " Scotland ", "Age": "42"}}
        before = json.dumps(original, sort_keys=True)
        merged = prep.merge_reinspection(original, inspected, "a", "old.json")
        self.assertEqual(merged["surname_status"], "confirmed")
        self.assertEqual(merged["transcript_fields"]["Age"], "42")
        self.assertEqual(merged["transcript_fields"]["First name(s)"], "John")
        self.assertEqual(merged["captured_at"], "2026-10-22")
        self.assertNotIn("block_reason", merged)
        self.assertEqual(merged["reinspection_provenance"]["original_detail_source_file"], "old.json")
        self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_reinspection_documentary_disagreement_requires_review(self):
        with self.assertRaisesRegex(ValueError, "conflict requires review.*Birth year.*1786.*1787"):
            prep.merge_reinspection(detail(**{"Birth year": "1786"}), detail(**{"Birth year": "1787"}), "a", "old.json")

    def test_later_event_keeps_own_year(self):
        item = detail(**{"Death year": "1830", "Birth year": "1780"})
        record, reason = prep.detail_identity("a", {}, item, 1800)
        self.assertEqual(reason, "")
        self.assertEqual(record["event_year"], 1830)
        self.assertIn("birth year 1780", record["temporal_basis"])
        self.assertIsNone(prep.detail_identity("a", {}, item)[0])

    def test_earlier_dated_event_proves_existence(self):
        self.assertTrue(prep.birth_temporal_scope(detail(**{"Marriage year": "1799"}), 1800)["accepted"])

    def test_later_unknown_birth_and_collection_ranges_held(self):
        for fields in ({"Death year": "1830"}, {"Record set": "Burials 1600-1750"},
                       {"Year Range": "1600-1750"}, {"Year Range": "1600-1850", "Death year": "1600"},
                       {"Year": "1830", "Birth year": "1800"}):
            with self.subTest(fields=fields):
                self.assertFalse(prep.birth_temporal_scope(detail(**fields), 1800)["accepted"])

    def test_birth_only_keeps_event_year_and_source_date(self):
        record, _ = prep.detail_identity("birth", {}, detail(**{"Birth date": "1 Jan 1799"}), 1800)
        self.assertEqual(record["event_year"], 1799)
        self.assertEqual(record["event_date"], "1 Jan 1799")
        later, _ = prep.detail_identity("death", {}, detail(**{"Birth date": "1 Jan 1799", "Death year": "1840"}), 1800)
        self.assertEqual(later["event_year"], 1840)
        self.assertEqual(later["event_date"], "")

    def test_age_is_bounded_estimate(self):
        result = prep.birth_temporal_scope(detail(**{"Death year": "1830", "Age": "51"}), 1800)
        self.assertTrue(result["accepted"])
        self.assertIn("estimated birth 1778–1779", result["basis"])
        self.assertFalse(prep.birth_temporal_scope(detail(**{"Death year": "1830", "Age": "30"}), 1800)["accepted"])

    def test_explicit_year_age_units_and_non_year_or_implausible_ages(self):
        for age in ("89y", "89 years", "89 year", "89 Y"):
            with self.subTest(age=age):
                scope = prep.birth_temporal_scope(detail(**{"Burial year": "1818", "Age at death": age}), 1800)
                self.assertTrue(scope["accepted"])
                self.assertIn("estimated birth 1728–1729", scope["basis"])
        for age in ("89 months", "89m", "89 weeks", "89 days", "89y 3m", "150", "150 years"):
            with self.subTest(age=age):
                scope = prep.birth_temporal_scope(detail(**{"Burial year": "1818", "Age at death": age}), 1800)
                self.assertFalse(scope["accepted"])

    def test_conflicting_birth_years_held(self):
        self.assertFalse(prep.birth_temporal_scope(detail(**{"Birth date": "1 Jan 1780", "Birth year": "1801"}), 1800)["accepted"])

    def test_supplement_keeps_paginated_counts_and_stable_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"record_id": "old", "last_name": "Glasgow", "first_name": "John",
                   "page_url_matches_claim": True, "page_url_number": 1, "included_in_analysis": True}
            (root / "audit-consolidated.json").write_text(json.dumps({"rows": [row], "summary": {
                "all_observed_exact_display_unique_ids": 1, "complete_and_reconciled": True}}))
            (root / "record-details.json").write_text(json.dumps({"records": {"old": detail(**{"Marriage year": "1700"})}}))
            supplement = root / "inspected.json"
            supplement.write_text(json.dumps({"records": {"new": detail(**{"Death year": "1830", "Birth year": "1780"})}}))
            args = ["prepare", "--input-dir", str(root)]
            with patch.object(prep, "load_profiles", return_value=({}, [])), contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", args):
                    prep.main()
                before = json.loads((root / "audit-distinct-people.json").read_text())
                (root / prep.IDENTITY_CLUSTERS_FILE).write_text(json.dumps([{
                    "record_ids": ["old", "out-of-scope"], "reason": "Retained prior reviewed identity",
                }]))
                with patch("sys.argv", args + ["--born-before", "1800", "--supplemental-records", str(supplement)]):
                    prep.main()
            result = json.loads((root / "audit-distinct-people.json").read_text())
            people = {p["record_ids"][0]: p for p in result["people"]}
            self.assertEqual(people["old"]["group_id"], before["people"][0]["group_id"])
            self.assertEqual(result["summary"]["observed_exact_display_unique_record_ids"], 1)
            self.assertEqual(result["summary"]["exact_display_outcome_record_ids"], 1)
            self.assertFalse(result["summary"]["birth_scope_corpus_complete"])
            self.assertIn("not paginated", people["new"]["records"][0]["inspection_provenance"])
            new_outcome = next(item for item in result["record_outcomes"] if item["record_id"] == "new")
            self.assertFalse(new_outcome["included_in_reconciled_analysis"])
            self.assertEqual(result["unapplied_identity_clusters"][0]["withheld_record_ids"], ["out-of-scope"])

            # An invocation-local reviewed identity can consolidate different
            # events. Missing or overlapping members remain explicit errors.
            data = json.loads(supplement.read_text())
            data["identity_clusters"] = [{"record_ids": ["old", "new"], "reason": "Inspected common identity evidence"}]
            supplement.write_text(json.dumps(data))
            scoped_args = args + ["--born-before", "1800", "--supplemental-records", str(supplement)]
            with patch.object(prep, "load_profiles", return_value=({}, [])), contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", scoped_args):
                    prep.main()
                grouped = json.loads((root / "audit-distinct-people.json").read_text())
                self.assertEqual(len(grouped["people"]), 1)
                self.assertEqual(set(grouped["people"][0]["record_ids"]), {"old", "new"})
                self.assertEqual(grouped["supplemental_identity_clusters"][0]["source_file"], str(supplement.resolve()))
                data["identity_clusters"].append({"record_ids": ["old", "new"], "reason": "Overlapping duplicate decision"})
                supplement.write_text(json.dumps(data))
                with patch("sys.argv", scoped_args), self.assertRaisesRegex(ValueError, "repeated="):
                    prep.main()
                data["identity_clusters"] = [{"record_ids": ["old", "missing"], "reason": "Missing member"}]
                supplement.write_text(json.dumps(data))
                with patch("sys.argv", scoped_args), self.assertRaisesRegex(ValueError, "missing=.*missing"):
                    prep.main()


if __name__ == "__main__":
    unittest.main()
