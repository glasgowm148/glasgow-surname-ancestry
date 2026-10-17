import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import repair_atlas_destinations as atlas


class DocumentaryDestinationsTest(unittest.TestCase):
    def test_existing_free_space_dossier_preserves_record_node(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / 'free-space/john/index.html'
            page.parent.mkdir(parents=True)
            page.write_text('John dossier')
            person = {'id': 'record-john', 'kind': 'person',
                      'documentary': True, 'catalogueId': 'record-john',
                      'catalogueUrl': '/free-space/john/#evidence'}
            before = dict(person)
            with patch.object(atlas, 'WEB', root):
                self.assertEqual(atlas.repair_people([person], {}), [])
            self.assertEqual(person, before)

    def test_absent_external_or_escaped_routes_do_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(atlas, 'WEB', root):
                for url in ['/missing/', 'https://example.com/',
                            '//example.com/', '/../outside.html']:
                    with self.subTest(url=url):
                        person = {'id': 'record-john', 'kind': 'person',
                                  'documentary': True, 'catalogueId': 'record-john',
                                  'catalogueUrl': url}
                        self.assertTrue(atlas.repair_people([person], {}))

    def test_ordinary_person_still_requires_people_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / 'free-space/john/index.html'
            page.parent.mkdir(parents=True)
            page.write_text('John dossier')
            person = {'id': 'Glasgow-1', 'kind': 'person',
                      'catalogueId': 'glasgow-1',
                      'catalogueUrl': '/free-space/john/'}
            with patch.object(atlas, 'WEB', root):
                self.assertTrue(atlas.repair_people([person], {}))
