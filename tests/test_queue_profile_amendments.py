import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools import build_research_catalog as catalogue
from tools.queue_profile_amendments import merge_amendments, public_additive_update, additive_update_panel
from tools.build_research_catalog import _restore_captured_named_ref_definitions


class ReviewedQueueAmendmentsTests(unittest.TestCase):
    def test_public_capture_supplies_name_and_vitals_for_placeholder_metadata(self):
        evidence = {'profiles': {'Glasgow-1': {'privacy': 60, 'profile_fields': {
            'Name': 'Glasgow-1', 'FirstName': 'James', 'LastNameAtBirth': 'Glasgow',
            'BirthDate': '1700-01-01', 'IsLiving': 0, 'DataStatus': {'BirthDate': 'guess'}}}}}
        person = catalogue._build_people([], {'Glasgow-1': {'full_name': 'Glasgow-1'}}, [], {}, evidence, {'Glasgow-1'})[0]
        self.assertEqual(person['name'], 'James Glasgow')
        self.assertEqual(person['first_names'], ['James'])
        self.assertIn('1700', person['birth'])

    def test_old_covered_elsewhere_decision_does_not_hide_new_own_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data/wikitree').mkdir(parents=True)
            (root / 'data/wikitree/research-catalogue-cases.json').write_text(json.dumps(
                {'cases': {'Glasgow-1': {'status': 'covered', 'profile_id': 'Glasgow-2'}}}))
            manifest = root / 'research/queue-review-2026-10-17/catalogue-integration.json'
            manifest.parent.mkdir(parents=True)
            notes = root / 'research/Glasgow-1/findings.md'
            notes.parent.mkdir()
            notes.write_text('# Person\n\n## Current conclusion\n\nA sourced record about this person.\n')
            with patch.object(catalogue, 'PROJECT_ROOT', root), patch.object(catalogue, 'RESEARCH_DIR', root / 'research'):
                self.assertEqual(catalogue._load_research_findings(['Glasgow-1']), [])
                manifest.write_text(json.dumps({'profile_updates': {'Glasgow-1': {'draft_path': 'reviewed.wiki'}}}))
                self.assertEqual(catalogue._load_research_findings(['Glasgow-1'])[0]['profile_id'], 'Glasgow-1')

    def test_private_comparison_retains_pending_public_additions_without_raw_text(self):
        update = dict(profile_id='Glasgow-1', pending=True, significance=60,
                      remote_wikitext='Private captured family', proposed_wikitext='Private full replacement',
                      public_addition_wikitext='A sourced historical record.<ref>Original source.</ref>')
        safe = public_additive_update(update)
        panel = additive_update_panel(safe)
        self.assertTrue(safe['pending'])
        self.assertNotIn('Private captured family', panel)
        self.assertNotIn('Private full replacement', panel)
        self.assertIn('Sourced additions only', panel)
        self.assertIn('Original source.', panel)

    def test_valid_unquoted_citation_definition_satisfies_quoted_reuse(self):
        text = '<ref name=Protocols1903-1904>Original source.</ref> Later.<ref name="Protocols1903-1904" />'
        self.assertEqual(_restore_captured_named_ref_definitions(text, text, 'Glasgow-1'), text)

    def test_full_replacement_supersedes_old_patch_preserving_manual_actions(self):
        specs = {'Glasgow-1': {'replacements': [{'old': 'x', 'new': 'y'}],
                 'addition_wikitext': 'old addition', 'manual_update': True,
                 'relationship_actions': ['uncertain father'], 'draft_path': 'old.md'}}
        reviewed = {'Glasgow-1': {'draft_path': 'complete.md', 'summary': 'New sourced record'}}
        reopened = merge_amendments(specs, reviewed, {'Glasgow-1': {}})
        self.assertEqual(reopened, {'Glasgow-1'})
        self.assertNotIn('replacements', specs['Glasgow-1'])
        self.assertNotIn('addition_wikitext', specs['Glasgow-1'])
        self.assertEqual(specs['Glasgow-1']['relationship_actions'], ['uncertain father'])
        self.assertEqual(specs['Glasgow-1']['draft_path'], 'complete.md')

    def test_missing_capture_is_reported_without_synthetic_current_biography(self):
        specs, report = {}, []
        self.assertEqual(merge_amendments(specs, {'Glasgow-1': {}}, {}, report), set())
        self.assertEqual(specs, {})
        self.assertEqual(report[0]['kind'], 'no_capture')
