"""Regression coverage for hashed shell assets and records-page rebuilds."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import build_research_catalog, repair_unified_site
from tools.records_page import records_assets, records_body


SHELL = '''<!doctype html><html><head><title>Sources</title>
<link rel="stylesheet" href="/assets/unified/site.css?v=abcd1234">
<link rel="stylesheet" href="/assets/v3/source-library.css?v=hashed1234">
</head><body><div class="g-crumbs"><strong>Sources</strong></div><main id="main">Sources</main>
<script defer src="/assets/v3/sources.js?v=hashed1234"></script>
<script defer src="/assets/unified/site.js?v=other1234"></script></body></html>'''
RECORDS = [{'record_id': 'r1', 'person': 'Jane Glasgow', 'region': 'Ireland',
            'record_category': 'Marriages', 'supporting_source_status': 'explicit',
            'supporting_source_quality': 'original'}]


class RecordsPageTests(unittest.TestCase):
    def check_assets(self, page):
        self.assertEqual(page.count('src="/records/search.js?v='), 1)
        self.assertEqual(page.count('href="/records/records.css?v='), 1)
        self.assertNotIn('/assets/v3/sources.js', page)
        self.assertNotIn('/assets/v3/source-library.css', page)
        self.assertIn('<strong>Records</strong>', page)
        self.assertIn('/assets/unified/site.js?v=other1234', page)

    def test_hashed_shell_wires_assets_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = records_assets(SHELL, root)
            self.check_assets(first)
            self.assertEqual(first, records_assets(first, root))
            self.assertTrue((root / 'records/search.js').is_file())
            self.assertTrue((root / 'records/records.css').is_file())

    def test_catalogue_generator_keeps_search_in_hashed_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sources').mkdir()
            (root / 'sources/index.html').write_text(SHELL)
            with patch.object(build_research_catalog, 'WEB_DIR', root):
                page = build_research_catalog._unified_records_page('Research records', 'Find records', records_body(RECORDS))
            self.check_assets(page)
            self.assertIn('id="record-query"', page)
            self.assertIn('id="record-sort"', page)

    def test_targeted_repair_restores_omitted_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('sources', 'records', 'data'):
                (root / folder).mkdir()
            (root / 'sources/index.html').write_text(SHELL)
            page = root / 'records/index.html'
            page.write_text(SHELL.replace('Sources', 'Research records'))
            (root / 'data/records-index.json').write_text(json.dumps(RECORDS))
            with patch.object(repair_unified_site, 'WEB', root):
                repair_unified_site.repair_records_shell()
                first = page.read_text()
                self.check_assets(first)
                self.assertIn('Ireland', first)
                self.assertIn('id="r-record-citation"', first)
                self.assertEqual({}, dict(repair_unified_site.repair_records_shell()))
                self.assertEqual(first, page.read_text())


if __name__ == '__main__':
    unittest.main()
