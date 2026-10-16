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
from tools.sync_catalogue_research import public_findings, refresh_catalogue_summaries


class TargetedFindingsPrivacyTests(unittest.TestCase):
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
                self.assertIn('href="/?needsUpdate=1"', page)
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
