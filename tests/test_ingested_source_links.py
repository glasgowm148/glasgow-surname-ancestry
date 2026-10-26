import tempfile
import unittest
from pathlib import Path

from tools.ingest_canonical_records import source_page


class IngestedSourceLinksTests(unittest.TestCase):
    shell = '<html><head><title>old</title></head><body><main></main></body></html>'

    def test_existing_local_profile_uses_local_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'people').mkdir(); (root / 'people' / 'Known-1.html').write_text('x')
            html = source_page(self.shell, {'id': 's', 'title': 'Source', 'url': 'https://example.invalid',
                'citations': [{'person': 'Known-1', 'name': 'Known'}]}, site_root=root)
        self.assertIn('/people/Known-1.html', html)

    def test_absent_local_known_wikitree_id_uses_canonical_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = source_page(self.shell, {'id': 's', 'title': 'Source', 'url': 'https://example.invalid',
                'citations': [{'person': 'glasgow-3905', 'name': 'Unknown Glasgow'},
                              {'person': 'glasgow-3905', 'name': 'Second citation',
                               'claims': [{'subject_ids': ['Glasgow-3905']}]}]}, site_root=Path(tmp))
        self.assertIn('https://www.wikitree.com/wiki/Glasgow-3905', html)
        self.assertNotIn('/people/glasgow-3905.html', html)

    def test_local_documentary_id_is_not_promoted_to_wikitree(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = source_page(self.shell, {'id': 's', 'title': 'Source', 'url': 'https://example.invalid',
                'citations': [{'person': 'record-john-1740', 'name': 'John Glasgow'},
                              {'person': 'record-other', 'name': 'Other',
                               'claims': [{'subject_ids': ['record-john-1740']}]}]}, site_root=Path(tmp))
        self.assertNotIn('wikitree.com/wiki', html)
        self.assertIn('John Glasgow', html)

    def test_absent_unrecognized_id_stays_plain(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = source_page(self.shell, {'id': 's', 'title': 'Source', 'url': 'https://example.invalid',
                'citations': [{'person': 'local-unknown', 'name': 'Unrecognized'}]}, site_root=Path(tmp))
        self.assertIn('Unrecognized', html)
        self.assertNotIn('/people/local-unknown.html', html)
        self.assertNotIn('wikitree.com/wiki/local-unknown', html)


if __name__ == '__main__':
    unittest.main()
