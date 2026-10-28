"""Vital rows of the event index follow the dossiers (fictional data)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools import build_event_index as index


class EventIndex(unittest.TestCase):
    def test_vital_rows_are_updated_added_and_reviewed_rows_kept(self):
        with TemporaryDirectory() as directory:
            web = Path(directory)
            def put(relative, value):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            put('people/harrow-1.json', {'id': 'Harrow-1', 'name': 'Ada Harrow', 'vitals': {
                'birth': {'date': '1801-05-03', 'place': 'Fennick, Ayrshire', 'status': 'exact'},
                'death': {'date': '1870', 'place': 'Ohio', 'status': 'certain'}}})
            put('people/harrow-2.json', {'id': 'Harrow-2', 'name': 'Ben Harrow', 'vitals': {'birth': {'date': 'c. 1805', 'place': None}}})
            put('people/harrow-9.json', {'id': 'Harrow-9', 'likely_living': True, 'vitals': {'birth': {'date': '1990'}}})
            put('assets/research/event-index.json', [
                {'p': 'harrow-1', 'id': 'birth', 'kind': 'personal', 'basis': 'imported_vital', 'raw_date': '1800',
                 'place': 'Fennick, Ayrshire', 'status': 'uncertain', 'country': 'scotland'},
                {'p': 'harrow-1', 'id': 'death', 'kind': 'personal', 'basis': 'reviewed_vital', 'raw_date': '1871'},
                {'p': 'harrow-1', 'id': 'E-aaaaaaaaaaaa', 'kind': 'mention', 'label': 'Kept'}])
            rows, counts = index.build(web)
            self.assertEqual(dict(counts), {'vital rows updated': 1, 'vital rows added': 1})
            birth = rows[0]
            self.assertEqual((birth['date'], birth['raw_date'], birth['year'], birth['status']), ('3 May 1801', '1801-05-03', 1801, 'exact'))
            self.assertEqual(birth['country'], 'scotland')                      # same place: country kept
            self.assertEqual(rows[1]['raw_date'], '1871')                       # reviewed row kept
            self.assertEqual(rows[2]['label'], 'Kept')                          # other kinds kept
            self.assertEqual(rows[3]['p'], 'harrow-2')                          # added, in order
            self.assertNotIn('harrow-9', json.dumps(rows))
            self.assertEqual(index.country('Currituck, North Carolina'), 'america')
            self.assertEqual(index.country('Rasharkin, Antrim'), 'ireland')
            index.main(['--web', str(web)])
            self.assertIsNone(index.build(web)[0])


if __name__ == '__main__':
    unittest.main()
