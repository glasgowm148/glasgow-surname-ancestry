"""Regression: targeted note refresh must preserve the public boundary."""
import json
import re
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools.public_privacy import PublicPrivacy
from tools.sync_catalogue_research import (
    discrepancies, public_findings, refresh_catalogue_summaries,
    select_profile_update, update_data,
)
from bs4 import BeautifulSoup


class PendingCreationSyncTests(unittest.TestCase):
    def setUp(self):
        self.update = update_data({
            'profile_id': 'record-example-1650', 'new_profile': True,
            'pending': True, 'action': 'create_new_profile', 'significance': 50,
            'summary': 'Resolve this reviewed identity before creation.',
            'draft_wikitext': '== Biography ==\nA named person in a 1650 record.',
            'relationship_changes': [
                {'action': 'add', 'relationship': 'father', 'relative_id': 'Father-2',
                 'probability': {'value': .95}},
                {'action': 'add', 'relationship': 'mother', 'relative_id': 'Mother-3',
                 'probability': {'value': None}},
            ],
        })
        self.dossier = {'id': 'record-example-1650', 'pending_profile_creation': True,
                        'creation_status': 'identity_hold', 'wikitree_update': self.update}
        self.row = {'pending_profile_creation': True, 'needs_wikitree_update': True,
                    'wikitree_update_significance': 50,
                    'wikitree_update_summary': self.update['summary']}

    def test_pending_creation_keeps_its_draft_flag_and_significance(self):
        selected = select_profile_update(None, self.dossier, self.row)
        # Exercise the serializer and actual discrepancy checks used by sync:
        # an unrelated findings refresh must not schedule removal of this update.
        self.assertEqual(update_data(selected), self.update)
        soup = BeautifulSoup('<main class="person-dossier-readable">'
                             '<section id="wikitree-update"><pre id="profile-update-draft">'
                             + self.update['draft_wikitext'] + '</pre></section></main>', 'html.parser')
        issues = discrepancies(self.dossier, soup,
                               [{'sections': [{'markdown': 'New source note.'}]}],
                               selected, self.row, {})
        self.assertIn('findings data', issues)
        self.assertNotIn('update data', issues)
        self.assertNotIn('search update significance', issues)
        self.assertNotIn('search update summary', issues)
        self.assertNotIn('search relationship changes', issues)
        self.assertEqual(update_data(selected)['relationship_changes'], self.update['relationship_changes'])
        self.assertTrue(update_data(selected)['new_profile'])

    def test_creation_amendment_badges_are_scheduled_for_removal(self):
        row = {**self.row, 'wikitree_update_relationship_changes': self.update['relationship_changes']}
        soup = BeautifulSoup('<main class="person-dossier-readable"></main>', 'html.parser')
        selected = select_profile_update(None, self.dossier, row)
        issues = discrepancies(self.dossier, soup, [], selected, row, {})
        self.assertIn('search relationship changes', issues)
        self.assertEqual(update_data(selected)['relationship_changes'], self.update['relationship_changes'])

    def test_queued_existing_profile_amendment_takes_precedence(self):
        queued = {'profile_id': 'Example-1', 'summary': 'A reviewed amendment.'}
        self.assertIs(select_profile_update(queued, self.dossier, self.row), queued)
        empty_queued = {}
        self.assertIs(select_profile_update(empty_queued, self.dossier, self.row), empty_queued)

    def test_stale_or_noncreation_updates_are_not_reused(self):
        for location, field in [('dossier', 'pending_profile_creation'),
                                ('row', 'pending_profile_creation'),
                                ('update', 'pending'), ('update', 'new_profile')]:
            with self.subTest(location=location, field=field):
                dossier, row, update = dict(self.dossier), dict(self.row), dict(self.update)
                {'dossier': dossier, 'row': row, 'update': update}[location][field] = False
                dossier['wikitree_update'] = update
                self.assertIsNone(select_profile_update(None, dossier, row))
        self.assertIsNone(select_profile_update(None, {'pending_profile_creation': True}, self.row))

    def test_retained_creation_still_contains_privacy_checked_draft(self):
        self.update['draft_wikitext'] += ' Private-1 family details.'
        policy = PublicPrivacy({'Private-1': {'birth_date': '2000-01-01'}})
        selected = select_profile_update(None, self.dossier, self.row)
        self.assertTrue(policy.contains_private_id(json.dumps(update_data(selected))))


class TargetedFindingsPrivacyTests(unittest.TestCase):
    def test_workbench_preserves_existing_profile_hold_count(self):
        rows = [{'name': str(i), 'missing_profile': True, 'profile_work_status': status}
                for i, status in enumerate(['creation_ready', 'creation_ready',
                                            'existing_profile_candidate', 'identity_hold'])]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for route in ['catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html']:
                path = root / route
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<html><body><a class="browse-card" href="/?missingProfile=1">'
                                '<span>Old workbench count</span></a></body></html>')
            with patch('tools.sync_catalogue_research.WEB', root):
                refresh_catalogue_summaries(rows)
            page = (root / 'catalogue.html').read_text()
            self.assertIn('4 documentary identities without confirmed destinations', page)
            self.assertIn('2 creation-ready, 1 possible existing-profile matches on HOLD', page)
            self.assertIn('1 with identity, source or supporting-page work remaining', page)

    def test_update_card_count_survives_reader_label_and_clean_route(self):
        rows = [{'name': str(i), 'needs_wikitree_update': i < 2,
                 'wikitree_update_significance': 50} for i in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for route, label in [('catalogue.html', 'Needs updated on WikiTree'),
                                 ('catalogue/index.html', 'WikiTree profiles to update'),
                                 ('catalogue/advanced.html', 'WikiTree profiles to update')]:
                path = root / route
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<html><body><a href="/?needsUpdate=1"><strong>' + label +
                                '</strong><span>108 profiles ranked by significance, with prepared corrections</span></a></body></html>')
            with patch('tools.sync_catalogue_research.WEB', root):
                refresh_catalogue_summaries(rows)
            for route in ['catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html']:
                page = (root / route).read_text()
                self.assertIn('2 profiles ranked by significance', page)
                self.assertIn('href="/catalogue/?needsUpdate=1&amp;sort=significance%3Adesc#catalogue-filters"', page)
                self.assertNotIn('108 profiles', page)

    def test_script_can_import_browser_refresh_outside_checkout(self):
        root = Path(__file__).resolve().parents[1]
        script = "import runpy,sys;sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[2]);from tools.catalogue_search_index import refresh;print('ok')"
        with tempfile.TemporaryDirectory() as directory:
            output = subprocess.check_output(
                [sys.executable, '-c', script, str(root / 'tools'), str(root / 'tools/sync_catalogue_research.py')],
                cwd=directory, env={k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}, text=True)
        self.assertEqual(output.strip(), 'ok')

    def test_targeted_findings_withhold_private_paragraph_and_keep_record(self):
        policy = PublicPrivacy({'Private-1': {'birth_date': '2000-01-01'}})
        policy.tester_ids = frozenset({'kit-secret'})
        policy.tester_pattern = re.compile(r'kit-secret')
        raw = [{'sections': [{'markdown': 'Private-1 family narrative.\n\n'
                'Public record: [1775 postal list](https://example.org/record).\n\n'
                'Tester kit-secret family narrative.'}]}]
        with patch('tools.sync_catalogue_research.catalogue._load_research_findings', return_value=raw):
            published = json.dumps(public_findings(['Historical-1'], policy))
        self.assertNotIn('Private-1', published)
        self.assertNotIn('kit-secret', published)
        self.assertIn('1775 postal list', published)
        self.assertIn('https://example.org/record', published)
        self.assertIn('Private-1', raw[0]['sections'][0]['markdown'])
