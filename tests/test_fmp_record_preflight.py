"""Deterministic tests for exact-ID offline Findmypast preflight."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import fmp_record_preflight as preflight_tool
from tools.fmp_record_preflight import preflight


class FmpPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.audit = self.root / "research/findmypast-glasgow-audit"
        self.audit.mkdir(parents=True)
        (self.root / "research").mkdir(exist_ok=True)
        (self.root / "www/data").mkdir(parents=True)
        self.write_json("research/canonical_records.json", [])
        self.write_json("www/data/records-index.json", [])

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")
        return target

    def detail(self, record_id, receipt, filename="record-details-test.json"):
        current = self.audit / filename
        if current.exists():
            data = json.loads(current.read_text(encoding="utf-8"))
        else:
            data = {"records": {}}
        data["records"][record_id] = receipt
        current.write_text(json.dumps(data), encoding="utf-8")

    def run_one(self, record_id, reason=""):
        return preflight(self.root, [{"record_id": record_id}], reason)["records"][0]

    def test_accessible_nonempty_receipt_outranks_cached_error(self):
        self.detail("R_1", {"access_status": "error", "transcript_fields": {}, "captured_at": "2026-10-01"}, "record-details-error.json")
        self.detail("R_1", {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}, "captured_at": "2026-10-02", "transcript_text": "Transcript"}, "record-details-good.json")
        result = self.run_one("R_1")
        self.assertEqual(result["disposition"], "reusable_receipt")
        self.assertEqual(result["cached_receipt"]["access_status"], "accessible")
        self.assertTrue(result["cached_receipt"]["transcript_fields_present"])

    def test_result_citation_is_not_a_transcript_receipt(self):
        result = preflight(self.root, [{"record_id": "R_2", "title": "Search result", "links": [{"label": "View transcript", "url": "https://www.findmypast.co.uk/transcript?id=R_2"}]}])["records"][0]
        self.assertEqual(result["disposition"], "detail_needed")
        self.assertIsNone(result["cached_receipt"])

    def test_encoded_provider_url_reuses_existing_index_and_source_id(self):
        provider_id = "SCOT/OPR/BAP/42"
        self.write_json("www/data/records-index.json", [{
            "record_id": "public-record-42", "provider_record_id": None,
            "source_url": "https://www.findmypast.co.uk/transcript?id=SCOT%2FOPR%2FBAP%2F42&tab=this",
            "document_id": "s-source-42",
        }, {
            "record_id": "public-record-42-duplicate", "provider_record_id": "SCOT%2FOPR%2FBAP%2F42",
            "document_id": "s-source-42-duplicate",
        }])
        result = self.run_one(provider_id)
        self.assertEqual(result["disposition"], "review_existing_index")
        self.assertEqual(result["public_record_ids"], ["public-record-42", "public-record-42-duplicate"])
        self.assertEqual(result["source_ids"], ["s-source-42", "s-source-42-duplicate"])
        self.assertIsNone(result["cached_receipt"])

    def test_matching_hold_is_preserved_even_with_cached_receipt(self):
        self.detail("R_3", {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}})
        self.write_json("research/findmypast-glasgow-audit/birth-scope-records-test.json", {
            "records": {"R_3": {"matching_status": "scope_hold", "matching_reason": "Birth surname unresolved"}},
            "scope": {"unassigned_record_ids": ["R_3"]},
        })
        result = self.run_one("R_3")
        self.assertEqual(result["disposition"], "reusable_receipt")
        self.assertTrue(result["matching_hold"])
        self.assertEqual(result["matching_hold_evidence"][0]["matching_status"], "scope_hold")

    def test_non_allowlisted_files_are_not_read(self):
        (self.audit / "private-browser-capture.json").write_text("not valid json", encoding="utf-8")
        result = self.run_one("R_4")
        self.assertEqual(result["disposition"], "detail_needed")

    def test_cached_inaccessible_receipt_requires_explicit_gap_to_reinspect(self):
        self.detail("R_5", {"access_status": "subscription_locked", "transcript_fields": {}, "captured_at": "2026-10-01"})
        result = self.run_one("R_5", "Need mother's maiden surname, absent from saved transcript.")
        self.assertEqual(result["disposition"], "blocked_receipt")
        self.assertFalse(result["reinspect"]["requested"])
        self.assertIsNone(result["reinspect"]["reason"])

    def test_cached_accessible_receipt_reinspect_needs_specific_reason(self):
        self.detail("R_6", {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}})
        result = self.run_one("R_6", "The saved fields omit the named spouse needed to check this relationship.")
        self.assertTrue(result["reinspect"]["requested"])
        self.assertIn("omit the named spouse", result["reinspect"]["reason"])

    def test_compatible_receipts_ignore_text_layout_blank_values_and_field_extras(self):
        self.detail("R_7", {
            "access_status": "accessible", "captured_at": "2026-10-01T00:00:00Z",
            "transcript_fields": {" Last   name ": "Glasgow", "Birth year": "1780", "Age": "—"},
            "transcript_text": "Full transcript as first captured",
        }, "record-details-old.json")
        self.detail("R_7", {
            "access_status": "accessible", "captured_at": "2026-10-02T00:00:00Z",
            "transcript_fields": {"last name": " Glasgow ", "Birth year": "1780", "Age": "-", "County": "Midlothian"},
        }, "record-details-new.json")
        result = self.run_one("R_7")
        self.assertEqual(result["disposition"], "reusable_receipt")
        self.assertEqual(result["conflicting_fields"], [])
        self.assertEqual(len(result["receipt_pointers"]), 2)
        self.assertTrue(result["cached_receipt"]["path"].endswith("record-details-new.json"))

    def test_real_substantive_conflict_reports_fields_and_all_pointers(self):
        self.detail("R_8", {
            "access_status": "accessible", "captured_at": "2026-10-01",
            "transcript_fields": {"Last name": "Glasgow", "Birth year": "1780"},
        }, "record-details-one.json")
        self.detail("R_8", {
            "access_status": "accessible", "captured_at": "2026-10-02",
            "transcript_fields": {" Last name ": "Glascow", "Birth year": "1780"},
        }, "record-details-two.json")
        result = self.run_one("R_8")
        self.assertEqual(result["disposition"], "blocked_receipt")
        self.assertEqual(len(result["receipt_pointers"]), 2)
        self.assertEqual([item["field"] for item in result["conflicting_fields"]], ["last name"])
        self.assertEqual({item["value"] for item in result["conflicting_fields"][0]["observations"]}, {"Glasgow", "Glascow"})

    def test_scope_assignment_hold_is_read_without_matching_status_on_record(self):
        self.detail("R_9", {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}})
        self.write_json("research/findmypast-glasgow-audit/birth-scope-records-older.json", {
            "records": {"R_9": {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}}},
            "matching_review": {"record_assignments": {"R_9": {"status": "identity_hold", "assessment": "HOLD — natal surname unresolved."}}},
        })
        result = self.run_one("R_9")
        self.assertTrue(result["matching_hold"])
        self.assertTrue(any("record_assignments" in item["json_pointer"] for item in result["matching_hold_evidence"]))

    def test_nested_no_eligible_role_disposition_is_exposed_without_blocking_receipt(self):
        self.detail("R_11", {
            "access_status": "accessible",
            "transcript_fields": {"First name(s)": "Child", "Father's last name": "Glasgow"},
        })
        self.write_json("research/findmypast-glasgow-audit/birth-scope-records-review.json", {
            "matching_review": {
                "cached180_review": {
                    "record_dispositions": {
                        "R_11": {
                            "status": "no_eligible_role_proved",
                            "reason": "Named parent has no established eligible profile yet.",
                            "previous_disposition_2026": {"status": "out_of_scope"},
                        }
                    }
                }
            }
        })
        result = self.run_one("R_11")
        self.assertEqual(result["disposition"], "reusable_receipt")
        self.assertTrue(result["matching_hold"])
        evidence = result["matching_hold_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["matching_status"], "no_eligible_role_proved")
        self.assertEqual(evidence[0]["reason"], "Named parent has no established eligible profile yet.")
        self.assertEqual(
            evidence[0]["json_pointer"],
            "#/matching_review/cached180_review/record_dispositions/R_11",
        )

    def test_indexed_followup_does_not_resurrect_historical_hold(self):
        self.detail("R_12", {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}})
        self.write_json("research/findmypast-glasgow-audit/birth-scope-records-review.json", {
            "matching_review": {
                "cached_review": {
                    "record_dispositions": {
                        "R_12": {
                            "status": "cached_secondary_role_indexed",
                            "indexed": True,
                            "previous_disposition_2026": {
                                "status": "no_eligible_role_proved",
                                "reason": "Old pending parent review.",
                            },
                        }
                    }
                }
            }
        })
        result = self.run_one("R_12")
        self.assertEqual(result["disposition"], "reusable_receipt")
        self.assertFalse(result["matching_hold"])
        self.assertEqual(result["matching_hold_evidence"], [])

    def test_percent_encoded_selection_id_normalizes_to_provider_id(self):
        self.detail("SCOT/OPR/BAP/43", {"access_status": "accessible", "transcript_fields": {"Last name": "Glasgow"}})
        result = self.run_one("SCOT%2FOPR%2FBAP%2F43")
        self.assertEqual(result["provider_id"], "SCOT/OPR/BAP/43")
        self.assertEqual(result["disposition"], "reusable_receipt")

    def test_identity_hold_without_transcript_still_needs_detail(self):
        self.write_json("research/findmypast-glasgow-audit/birth-scope-records-test.json", {
            "records": {},
            "matching_review": {"record_assignments": {"R_10": {
                "status": "identity_hold", "assessment": "HOLD — original transcript needs checking."
            }}},
        })
        result = self.run_one("R_10")
        self.assertEqual(result["disposition"], "detail_needed")
        self.assertTrue(result["matching_hold"])
        self.assertIn("may resolve", result["reason"])
        self.assertIsNone(result["cached_receipt"])

    def test_twenty_cached_rows_remain_reusable_with_holds_retained(self):
        rows = []
        held_ids = []
        for index in range(20):
            record_id = f"R_PAGE_{index:02d}"
            rows.append({"record_id": record_id})
            self.detail(record_id, {
                "access_status": "accessible", "transcript_fields": {"Last name": "Glasgow", "Event year": str(1700 + index)}
            })
            if index % 2 == 0:
                held_ids.append(record_id)
        self.write_json("research/findmypast-glasgow-audit/birth-scope-records-test.json", {
            "records": {}, "scope": {"unassigned_record_ids": held_ids}
        })
        result = preflight(self.root, rows)["records"]
        self.assertEqual(len(result), 20)
        self.assertEqual({row["disposition"] for row in result}, {"reusable_receipt"})
        self.assertEqual(sum(row["matching_hold"] for row in result), 10)

    def test_indexes_are_parsed_once_then_looked_up_by_provider_id(self):
        count = 80
        canonical = []
        public = []
        for index in range(count):
            provider_id = f"R_IDX_{index:03d}"
            canonical.append({"record_id": f"c-{index}", "provider_record_id": provider_id})
            public.append({"record_id": f"p-{index}", "source_url": f"https://www.findmypast.co.uk/transcript?id={provider_id}", "document_id": f"s-{index}"})
        self.write_json("research/canonical_records.json", canonical)
        self.write_json("www/data/records-index.json", public)
        with patch.object(preflight_tool, "provider_key", wraps=preflight_tool.provider_key) as parsed:
            result = preflight(self.root, [{"record_id": "R_IDX_001"}, {"record_id": "R_IDX_079"}])["records"]
        self.assertEqual([row["public_record_ids"] for row in result], [["p-1"], ["p-79"]])
        # One pass over each 80-row index, plus a small constant for the two queries.
        self.assertLessEqual(parsed.call_count, count * 2 + 4)


if __name__ == "__main__":
    unittest.main()
