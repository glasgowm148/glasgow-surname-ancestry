import json
from pathlib import Path
import tempfile
import unittest

from tools.documentary_ancestry import load_people, metric_node


class DocumentaryIdentityTests(unittest.TestCase):
    def person(self):
        return dict(id='record-john', name='John', publication_status='approved',
                    url='/free-space/john/', first_record_year=1447, source_ids=['act-a', 'act-b'],
                    record_groups=[dict(id='burgh-a', first_record_year=1447, source_ids=['act-a']),
                                   dict(id='burgh-b', first_record_year=1475, source_ids=['act-b'])],
                    identity_selection=dict(id='I-1', selected=True, model='same_person', status='uncertain',
                                            basis='Compatible career and civic role', limitations='Different men remain possible'))

    def load(self, person):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'people.json'
            path.write_text(json.dumps({'people': [person]}))
            return load_people(path)[0]

    def test_uncertain_identity_extends_record_period_without_inventing_vitals(self):
        node = metric_node(self.load(self.person()))
        self.assertEqual(node['year'], 1447)
        self.assertIn('uncertain combined identity', node['year_status'])
        self.assertIsNone(node['birth_year'])
        self.assertIsNone(node['death_year'])
        self.assertFalse(node['cohort_member'])

    def test_grouping_without_a_selected_identity_is_rejected(self):
        person = self.person()
        person['identity_selection']['selected'] = False
        with self.assertRaisesRegex(ValueError, 'explicit graded identity'):
            self.load(person)

    def test_probable_identity_can_link_to_a_complete_research_subject(self):
        person = self.person()
        person['url'] = '/research/subjects/example-records/#named-adult'
        person['identity_selection']['status'] = 'probable'
        node = metric_node(self.load(person))
        self.assertIn('probable combined identity', node['year_status'])
        self.assertFalse(node['cohort_member'])
        self.assertIsNone(node['birth_year'])
        person['url'] = '//example.test/unreviewed'
        with self.assertRaisesRegex(ValueError, 'complete public research account'):
            self.load(person)

    def test_uncited_or_duplicated_groups_are_rejected(self):
        person = self.person()
        person['source_ids'] = ['act-a']
        with self.assertRaisesRegex(ValueError, 'source IDs'):
            self.load(person)
        person = self.person()
        person['record_groups'][1]['id'] = 'burgh-a'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.load(person)
