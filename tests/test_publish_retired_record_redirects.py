"""Retired record subjects redirect to the person they became (fictional data)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import tools.publish_retired_record_redirects as retired


class RetiredRecordRedirects(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.put('research/reviews/merge.json', {'decisions': [
            {'retired_catalogue_id': 'record-harrow-1801-baptism', 'canonical_profile_id': 'Harrow-1'}]})
        self.put('research/Harrow-2/catalogue-profile-link.json',
                 {'catalogue_id': 'record-fmp-glasgow-aaaaaaaaaaaa', 'wikitree_id': 'Harrow-2'})
        self.put('research/Harrow-3/1720_draft.md', '<!-- BEGIN FMP-GLASGOW-fmp-glasgow-bbbbbbbbbbbb -->')
        self.put('research/Harrow-4/1730_draft.md', '<!-- BEGIN FMP-GLASGOW-fmp-glasgow-cccccccccccc -->')
        self.put('research/old/gray-backup/x.json', {'retired_catalogue_id': 'record-old', 'canonical_profile_id': 'Harrow-1'})
        for person in ('harrow-1', 'harrow-2', 'harrow-3', 'harrow-4'):
            self.put(f'www/people/{person}.html', '<html>dossier</html>')
        self.put('www/people/record-fmp-glasgow-cccccccccccc.html', '<html>current catalogue page</html>')
        self.put('www/data/people.json', {'people': [{'catalogue_id': 'record-fmp-glasgow-cccccccccccc'}]})
        self.put('data/site/retired-record-urls.json', {'published': ['record-harrow-1801-baptism', 'record-fmp-glasgow-aaaaaaaaaaaa']})
        self.put('www/people/record-fmp-glasgow-bbbbbbbbbbbb.html', '<html>stale page</html>')
        self.put('research/Harrow-1/1690_other.md', '<!-- BEGIN FMP-GLASGOW-fmp-glasgow-dddddddddddd -->')

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))

    def test_only_documented_retirements_redirect_and_current_pages_stay(self):
        self.assertEqual(retired.publish(self.root), 3)   # the 1577 reading's survivor has no page here
        people = self.root / 'www/people'
        for old, new in (('record-harrow-1801-baptism', 'harrow-1'), ('record-fmp-glasgow-aaaaaaaaaaaa', 'harrow-2'),
                         ('record-fmp-glasgow-bbbbbbbbbbbb', 'harrow-3')):
            self.assertIn(f'url={new}.html', (people / f'{old}.html').read_text())
        self.assertEqual((people / 'record-fmp-glasgow-cccccccccccc.html').read_text(), '<html>current catalogue page</html>')
        self.assertFalse((people / 'record-old.html').exists())
        self.assertFalse((people / 'record-fmp-glasgow-dddddddddddd.html').exists())   # never published
        self.assertEqual(retired.publish(self.root), 0)

    def test_legacy_ancestry_routes_follow_existing_retired_mapping(self):
        self.put('research/reviews/ancestry.json', {'decisions': [
            {'retired_catalogue_id': target, 'canonical_profile_id': 'Harrow-1'}
            for target in retired.LEGACY_ROUTE_ALIASES.values()]})
        self.put('www/data/people.json', {'people': []})
        for target in retired.LEGACY_ROUTE_ALIASES.values():
            self.put(f'www/people/{target}.html', '<html>retired dossier</html>')
        retired.publish(self.root)
        for alias, target in retired.LEGACY_ROUTE_ALIASES.items():
            text = (self.root / 'www/people' / f'{alias}.html').read_text()
            self.assertIn('url=harrow-1.html', text)


if __name__ == '__main__':
    unittest.main()
