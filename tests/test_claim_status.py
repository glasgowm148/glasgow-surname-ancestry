import json
from pathlib import Path

from tools.catalogue_machine_data import _canonical_status, _profile_assessment_flags
from tools.repair_claim_status import repair


def test_qualified_labels_do_not_promote_to_proved():
    assert _canonical_status("Strong candidate; not proved", claim_type="relationship") == "strongly_supported"
    assert _canonical_status("Probable; unproved", claim_type="relationship") == "probable"
    assert _canonical_status("Documented occurrence / identity unproved", claim_type="relationship") == "unknown"
    assert _canonical_status("Documented occurrence", claim_type="relationship", claim_context="identity unproved") == "unknown"


def test_documented_occurrence_keeps_its_narrow_scope():
    assert _canonical_status("Documented occurrence / identity unproved", claim_type="recorded_occurrence") == "proved"
    assert _canonical_status("Documented father", claim_type="relationship") == "proved"


def test_profile_assessment_flags_survive_redacted_capture():
    person = {"wikitree_evidence": [{"assessment_flags": {
        "_structural_placeholder": True,
        "_family_links_disclaimed": True,
    }}]}
    flags = _profile_assessment_flags(person)
    assert flags["_structural_placeholder"] is True
    assert flags["_family_links_disclaimed"] is True
    assert flags["_birth_details_disclaimed"] is False


def test_repair_updates_current_claim_evidence_and_import_without_touching_history(tmp_path):
    claim = {
        "id": "C-db7b2a0378e5", "type": "relationship",
        "subject_ids": ["Glasgow-2413", "Glasgow-2416"],
        "status": "proved", "status_label": "Strong candidate; not proved",
        "evidence_ids": ["E-a242af2fc8f9"],
    }
    payload = {
        "claims": [claim],
        "evidence": [{"id": "E-a242af2fc8f9", "evidence_status": "direct"}],
        "imported": {"sections": {"claims": [dict(claim)]}},
        "relationship_history": [{**claim, "lifecycle": "historical", "status": "superseded"}],
    }
    path = tmp_path / "people" / "glasgow-2416.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert repair(tmp_path) == {"files": 1, "claims": 2, "evidence": 1, "networks": 0}
    repaired = json.loads(path.read_text(encoding="utf-8"))
    assert repaired["claims"][0]["status"] == "strongly_supported"
    assert repaired["evidence"][0]["evidence_status"] == "circumstantial"
    assert repaired["imported"]["sections"]["claims"][0]["status"] == "strongly_supported"
    assert repaired["relationship_history"][0]["status"] == "superseded"
    assert repair(tmp_path) == {"files": 0, "claims": 0, "evidence": 0, "networks": 0}


# The repository test gate uses unittest discovery.
import tempfile
import unittest


class ClaimStatusTests(unittest.TestCase):
    def test_qualified_labels(self):
        test_qualified_labels_do_not_promote_to_proved()

    def test_occurrence_scope(self):
        test_documented_occurrence_keeps_its_narrow_scope()

    def test_retained_cautions(self):
        test_profile_assessment_flags_survive_redacted_capture()

    def test_targeted_migration(self):
        with tempfile.TemporaryDirectory() as root:
            test_repair_updates_current_claim_evidence_and_import_without_touching_history(Path(root))
