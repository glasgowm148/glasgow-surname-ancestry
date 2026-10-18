import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools import build_research_catalog as catalogue
from tools import sync_catalogue_research as sync
from bs4 import BeautifulSoup
from tools.queue_profile_amendments import merge_amendments, public_additive_update, additive_update_panel
from tools.build_research_catalog import _restore_captured_named_ref_definitions


class ReviewedQueueAmendmentsTests(unittest.TestCase):
    def test_text_fenced_handoff_extracts_only_native_biography(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            native = '== Biography ==\nA recorded person.<ref>Original record.</ref>\n== Sources ==\n<references />'
            (root / 'draft.md').write_text('# Handoff\n\n```text\n' + native + '\n```\n\n## Relationship cautions\nEditing notes.')
            with patch.object(catalogue, 'PROJECT_ROOT', root):
                self.assertEqual(catalogue._extract_profile_draft({'draft_path': 'draft.md'}), native)
                (root / 'native.wiki').write_text(native + '\n\n```text\nA source quotation.\n```\n\nA further source.')
                self.assertIn('A further source.', catalogue._extract_profile_draft({'draft_path': 'native.wiki'}))

    def test_queue_cards_keep_filters_on_the_catalogue_route(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'catalogue').mkdir()
            markup = '<a href="/?missingProfile=1">No profile</a><a href="?needsUpdate=1">Updates</a>'
            for relative in ('catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html'):
                (web / relative).write_text(markup)
            with patch.object(sync, 'WEB', web):
                sync.refresh_catalogue_summaries([])
            for relative in ('catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html'):
                links = BeautifulSoup((web / relative).read_text(), 'html.parser').select('a')
                self.assertEqual(links[0]['href'], '/catalogue/?missingProfile=1&sort=birth%3Aasc#catalogue-filters')
                self.assertEqual(links[1]['href'], '/catalogue/?needsUpdate=1&sort=significance%3Adesc#catalogue-filters')

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
                      relationship_changes=[dict(action='add', relationship='father',
                                                 relative_id='Glasgow-2', status='uncertain')],
                      public_addition_wikitext='A sourced historical record.<ref>Original source.</ref>')
        safe = public_additive_update(update)
        panel = additive_update_panel(safe)
        self.assertTrue(safe['pending'])
        self.assertNotIn('Private captured family', panel)
        self.assertNotIn('Private full replacement', panel)
        self.assertIn('Sourced additions only', panel)
        self.assertIn('Original source.', panel)
        public = sync.update_data(safe)
        self.assertEqual(public['relationship_changes'], update['relationship_changes'])
        self.assertEqual(public['remote_wikitext'], '')
        self.assertEqual(public['draft_wikitext'], '')

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
