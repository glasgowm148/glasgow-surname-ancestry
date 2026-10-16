import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.site_sources.onetree.build import apply_public_families


class PublicFamiliesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / 'people').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_sync(self, people, families, ambiguous=(), years=None):
        for person in people:
            person.setdefault('name', person['id'])
        nodes = {}
        edges = []
        for ident, parents in families.items():
            year = (years or {}).get(ident, 1600)
            nodes[ident] = dict(id=ident, name=ident, url='/people/'+ident.lower()+'.html',
                gender='Male', birth_year=year, death_year=None, birth_status='uncertain',
                year=year, year_basis='birth', year_status='uncertain', first_record_year=None)
            dossier = dict(id=ident, name=ident, vitals={'birth': {'date': str(year), 'place': 'Scotland'}},
                           relationships={'parents': parents})
            (self.site / 'people' / (ident.lower()+'.json')).write_text(json.dumps(dossier))
            edges += [dict(child=ident, father=r['id'], status=r.get('status', 'unknown'))
                      for r in parents if r.get('relationship') == 'father' and ident not in ambiguous]
        with patch('tools.branch_connectivity.load_public_nodes', return_value=(nodes, edges, {'multiple_fathers': list(ambiguous)})):
            return apply_public_families(people, self.site)

    def test_replaces_old_parent_and_preserves_recorded_grade_and_mother(self):
        mother = {'id': 'Mother-1', 'role': 'mother', 'status': 'uncertain'}
        people = [dict(id='Child-1', parents=[dict(id='Old-1', role='father', status='uncertain'), mother], childrenRecorded=[]),
                  dict(id='Old-1', parents=[], childrenRecorded=[{'id': 'Child-1'}, {'id': 'Other-1'}]),
                  dict(id='Father-1', parents=[], childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1': [{'id': 'Father-1', 'relationship': 'father', 'status': 'unknown', 'tree_status': 'uncertain'}], 'Father-1': []})
        child = people[0]
        self.assertEqual([(r['id'],r['status']) for r in child['parents'] if r['role']=='father'], [('Father-1','uncertain')])
        self.assertEqual(child['parents'][0]['id'], mother['id'])
        self.assertEqual(people[1]['childrenRecorded'], [{'id':'Other-1'}])
        self.assertEqual(people[2]['childrenRecorded'][0]['id'], 'Child-1')
        self.assertIn('Child-1', result['publicFamilySyncIds'])

    def test_adds_missing_published_child_and_records_proved_father(self):
        people = [dict(id='Father-1', parents=[], childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1': [{'id':'Father-1','relationship':'father','status':'proved','reason':'Named in a testament'}], 'Father-1': []})
        self.assertEqual(result['publicFamilyNewIds'], ['Child-1'])
        child = next(p for p in people if p['id']=='Child-1')
        self.assertEqual(child['parents'][0]['status'], 'proved')
        self.assertEqual(child['parents'][0]['reason'], 'Named in a testament')
        self.assertTrue(child['parents'][0]['inModel'])

    def test_holds_competing_fathers_without_selecting_a_candidate(self):
        people = [dict(id='Child-1', parents=[dict(id='Father-1',role='father',status='unmarked')], childrenRecorded=[]),
                  dict(id='Father-1',parents=[],childrenRecorded=[{'id':'Child-1'}]),
                  dict(id='Other-1',parents=[],childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1':[{'id':i,'relationship':'father','status':'uncertain'} for i in ['Father-1','Other-1']], 'Father-1':[], 'Other-1':[]}, ambiguous=['Child-1'])
        self.assertFalse(people[0]['parents'])
        self.assertEqual(len(people[0]['publicFatherAlternatives']), 2)
        self.assertEqual(result['publicFatherHoldIds'], ['Child-1'])

    def test_retains_selected_hypothesis_provenance(self):
        father = dict(id='Father-1',role='father',status='uncertain',hypothesis=True,assertion_id='A-selected',reason='Prior selected model')
        people = [dict(id='Child-1',parents=[father],childrenRecorded=[]), dict(id='Father-1',parents=[],childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1':[{'id':'Father-1','relationship':'father','status':'uncertain'}], 'Father-1':[]})
        self.assertEqual(people[0]['parents'][0]['assertion_id'], 'A-selected')
        self.assertEqual(people[0]['parents'][0]['reason'], 'Prior selected model')
        self.assertNotIn('Child-1', result['publicFamilySyncIds'])

    def test_later_profiles_are_outside_the_historical_sync(self):
        people = [dict(id='Early-1',parents=[],childrenRecorded=[])]
        result = self.run_sync(people, {'Early-1':[], 'Later-1':[]}, years={'Later-1':1950})
        self.assertNotIn('Later-1', [p['id'] for p in people])
        self.assertEqual(result['publicFamilyScopeIds'], ['Early-1'])

    def test_unknown_assessment_without_a_tree_flag_remains_unknown(self):
        people = [dict(id='Child-1',parents=[],childrenRecorded=[]),dict(id='Father-1',parents=[],childrenRecorded=[])]
        self.run_sync(people, {'Child-1':[{'id':'Father-1','relationship':'father','status':'unknown'}], 'Father-1':[]})
        self.assertEqual(people[0]['parents'][0]['status'],'unknown')

    def test_withheld_parent_cannot_publish_an_identifier_or_source_url(self):
        people = [dict(id='Child-1',parents=[],childrenRecorded=[])]
        self.run_sync(people, {'Child-1':[{'relationship':'father','id':'Private-1','withheld':True,'url':'/private/capture'}]})
        rendered = json.dumps(people)
        self.assertNotIn('Private-1', rendered)
        self.assertNotIn('/private/capture', rendered)
        self.assertTrue(people[0]['parents'][0]['withheld'])
