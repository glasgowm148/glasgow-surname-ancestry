"""A precise death date is distinct from the assessed record-to-person identity."""
import json
from tests._generated_data import requires_generated_data
from pathlib import Path
import unittest

from bs4 import BeautifulSoup
from tests._site_html import read_html

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'


@requires_generated_data
class MaryDeathIdentificationTests(unittest.TestCase):
    def test_identity_and_date_precision_agree_in_every_output(self):
        dossier = json.loads((WEB / 'people/mccaughan-222.json').read_text())
        network = json.loads((WEB / 'people/mccaughan-222.network.json').read_text())
        page = BeautifulSoup(read_html(WEB / 'people/mccaughan-222.html'), 'html.parser')
        embedded = json.loads(page.select_one('pre.archive-json').text)
        death = dossier['vitals']['death']
        for output in (network, embedded, dossier['presentation']):
            self.assertEqual(death, output['vitals']['death'])
        self.assertEqual('exact', death['status'])
        self.assertEqual('day', death['date_precision'])
        self.assertEqual('strongly_supported', death['identification_status'])
        self.assertEqual('1892-02-17', death['date'])
        self.assertEqual('1892-02-17', death['date_readings'][0]['date'])
        self.assertEqual('corrected_against_original', death['date_reading_status'])
        self.assertEqual('mary-mccaughan-222-death-identification', death['provenance']['assessment_id'])
        self.assertIn(death['qualifier'], page.select_one('.dossier-life').text)
        alexander = BeautifulSoup(read_html(WEB / 'people/glasgow-951.html'), 'html.parser')
        family_row = alexander.select_one('#family a[href="/people/mccaughan-222.html"]').find_parent('tr')
        self.assertIn(death['qualifier'], family_row.text)
        self.assertEqual('1892-02-27', dossier['imported']['sections']['vitals']['death']['date'])

    def test_current_argument_uses_the_two_actual_records(self):
        dossier = json.loads((WEB / 'people/mccaughan-222.json').read_text())
        presentation = dossier['presentation']
        question = next(q for q in presentation['evidence_questions'] if q['id'] == 'identity')
        self.assertEqual(['death-mary-1892', 'marriage-mary-1871'], question['records'])
        self.assertIn('high confidence', question['answer'])
        self.assertIn('lot 25', question['reasoning'])
        self.assertIn('neither a maiden surname nor a named husband', question['limitation'])
        self.assertIn('89', question['limitation'])
        self.assertNotIn('The original return and a direct marriage', question['missing'])
        page = BeautifulSoup(read_html(WEB / 'people/mccaughan-222.html'), 'html.parser')
        for record in question['records']:
            self.assertIsNotNone(page.find(id=f'record-{record}-identity'))
            self.assertIsNotNone(page.find(id=f'source-{record}'))
        role = page.select_one('#timeline-death-mary-1892 .timeline-role')
        self.assertEqual('Subject', role.text.strip())


if __name__ == '__main__':
    unittest.main()
