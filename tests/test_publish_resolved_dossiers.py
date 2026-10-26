import importlib.util
from pathlib import Path
import unittest
import json
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('resolver', Path(__file__).resolve().parents[1] / 'tools/publish_resolved_dossiers.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResolvedDossierTests(unittest.TestCase):
    def test_stepmother_correction_preserves_history_and_catalogue_biological_mother(self):
        original = {'id': 'Child-1', 'relationships': {'parents': [
            {'id': 'Martha-1', 'name': 'Martha', 'relationship': 'mother', 'claim_id': 'old-mother'}]},
                    'claims': []}
        assertion = {'assertion_id': 'stepmother-review', 'people': ['Child-1', 'Martha-1'],
                     'publication_status': 'approved', 'status': 'proved', 'source_ids': ['record'],
                     'allow_new_relationship': False,
                     'perspectives': {'Child-1': {'relationship': 'stepmother', 'reason': 'Source identifies a stepmother.'}},
                     'role_correction': {'Child-1': {'from': ['mother'], 'to': 'stepmother'}}}
        resolved = module.resolve(original, [], [assertion])
        self.assertEqual('stepmother', resolved['relationships']['parents'][0]['relationship'])
        self.assertEqual('old-mother', resolved['relationship_history'][0]['claim_id'])
        mary = {'id': 'Mary-1', 'name': 'Mary', 'relationship': 'mother', 'claim_id': 'new-mother',
                'status': 'proved', 'lifecycle': 'current', 'display': 'current'}
        resolved['relationships']['parents'].append(mary)
        rows = [{'id': 'Child-1'}]
        module.project_catalogue_parents(rows, {'child-1': resolved})
        self.assertEqual(['Mary-1'], [p['id'] for p in rows[0]['mother']])

    def test_reviewed_name_replays_and_restores_without_changing_family(self):
        original = {'id': 'Person-1', 'name': 'Wrong record label', 'relationships': {'parents': []}, 'claims': []}
        review = {'id': 'name-review', 'subject': 'Person-1', 'status': 'approved',
                  'identity': {'name': 'Recorded Person'}, 'catalogue_projection': {'name': 'Recorded Person'}}
        resolved = module.resolve(original, [review], [])
        self.assertEqual('Recorded Person', resolved['name'])
        self.assertEqual('Wrong record label', resolved['identity_review']['original_name'])
        self.assertEqual(resolved, module.resolve(resolved, [review], []))
        self.assertEqual('Wrong record label', module.resolve(resolved, [], [])['name'])
        self.assertEqual(original['relationships'], resolved['relationships'])
        rows = [{'id': 'person-1', 'name': original['name']}]
        module.project_catalogue_vitals(rows, [review])
        self.assertEqual('Recorded Person', rows[0]['name'])
        module.project_catalogue_vitals(rows, [])
        self.assertEqual(original['name'], rows[0]['name'])

    def test_shared_review_skips_incomplete_retired_redirect(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subject = {'id': 'Person-1', 'relationships': {'parents': [
                {'id': 'Parent-2', 'relationship': 'father'}]}, 'claims': []}
            stub = {'id': 'Person-1', 'status': 'superseded',
                    'redirect_to': '/people/person-1.json', 'relationships': {}}
            assertion = {'assertion_id': 'parent-review',
                         'people': ['Person-1', 'Parent-2'],
                         'publication_status': 'approved', 'status': 'probable',
                         'allow_new_relationship': False, 'source_ids': ['record'],
                         'perspectives': {'Person-1': {'relationship': 'father',
                                                      'reason': 'The record names the father.'}}}
            files = {'people/person-1.json': subject,
                     'people/record-retired.json': stub,
                     'assets/research/assessments.json': {'assessments': []},
                     'assets/research/relationship-assessments.json': [assertion]}
            for name, value in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            original_stub = (root / 'people/record-retired.json').read_bytes()
            module.publish(root)
            published = json.loads((root / 'people/person-1.json').read_text())
            self.assertEqual('parent-review', published['relationships']['parents'][0]['claim_id'])
            self.assertEqual(original_stub, (root / 'people/record-retired.json').read_bytes())

    def test_new_spouse_point_estimate_reaches_dossier_and_catalogue(self):
        import sys
        probability = sys.modules[module.probability_for_relationship.__module__]
        estimate = {'percent': 88, 'assessment_status': 'probable', 'basis': 'Named couple with qualified adult identity.',
                    'reviewed': '2026-10-21', 'source_ids': ['marriage-record']}
        original = {'id': 'Example-1', 'relationships': {'parents': [], 'spouses': []},
                    'evidence': [], 'claims': [], 'presentation': {}}
        assertion = {'assertion_id': 'couple-review', 'people': ['Example-1', 'Example-2'],
                     'profile_names': {'Example-2': 'Example partner'}, 'publication_status': 'approved',
                     'status': 'probable', 'allow_new_relationship': True,
                     'source_ids': ['marriage-record'],
                     'perspectives': {'Example-1': {'relationship': 'spouse', 'reason': estimate['basis']}}}
        with patch.object(probability, 'reviewed_estimates', return_value={('example-1', 'example-2', 'spouse'): estimate}):
            resolved = module.resolve(original, [], [assertion])
        spouse = resolved['relationships']['spouses'][0]
        self.assertEqual(spouse['probability']['value'], .88)
        self.assertEqual(resolved['presentation']['relationships']['spouses'][0]['probability']['value'], .88)
        rows = [{'id': 'Example-1', 'spouses': []}]
        module.project_catalogue_spouses(rows, {'example-1': resolved})
        self.assertEqual(rows[0]['spouses'][0]['probability']['value'], .88)

    def test_removed_father_releases_primary_root_without_losing_export_leads(self):
        from copy import deepcopy
        root = {'id': 'Root-1', 'catalogued_members': 3}
        original = [{'id': f'child-{i}', 'father': [{'id': 'Father-1'}],
                     'mother': [], 'missing_father': False, 'missing_mother': True,
                     'family_root': deepcopy(root), 'family_roots': [deepcopy(root)]}
                    for i in range(3)]
        reviewed = {'child-0': {'relationships': {'parents': []}}}
        result = module.project_catalogue_parents(deepcopy(original), reviewed)
        self.assertIsNone(result[0]['family_root'])
        self.assertEqual(result[0]['family_roots'], [{'id': 'Root-1', 'catalogued_members': 0}])
        self.assertEqual(result[0]['parent_review']['original_fields']['family_roots']['value'], [root])
        self.assertEqual(result[1]['family_root']['catalogued_members'], 2)
        self.assertEqual(result[1]['family_roots'][0]['catalogued_members'], 2)
        self.assertEqual(module.project_catalogue_parents(deepcopy(result), reviewed), result)
        self.assertEqual(module.project_catalogue_parents(result, {}), original)

    def test_new_source_claim_survives_restoring_an_older_review_import(self):
        original = {'id': 'Example-1', 'vitals': {'birth': {'date': '1800'}}, 'claims': [], 'evidence': []}
        review = {'id': 'review', 'subject': 'Example-1', 'status': 'approved',
                  'vitals': {'birth': {'date': None, 'status': 'unknown'}}}
        current = module.resolve(original, [review])
        claim = {'id': 'source-claim', 'type': 'recorded_occurrence', 'status': 'unknown',
                 'claim': 'A derivative source describes the household; parentage is unknown.',
                 'evidence_ids': ['source-evidence'], 'provenance': 'profile-provenance'}
        evidence = {'id': 'source-evidence', 'claim_ids': ['source-claim'], 'source': {'url': 'https://example.org/record'}}
        current['claims'].append(claim)
        current['evidence'].append(evidence)
        resolved = module.resolve(current, [review])
        self.assertIn(claim, resolved['claims'])
        self.assertIn(claim, resolved['imported']['sections']['claims'])
        self.assertEqual([evidence], resolved['evidence'])
        self.assertEqual(resolved, module.resolve(resolved, [review]))
        revoked = module.resolve(resolved, [])
        self.assertIn(claim, revoked['claims'])
        self.assertEqual([evidence], revoked['evidence'])
        shared = {'assertion_id': 'family-review', 'people': ['Example-1', 'Example-2'],
                  'publication_status': 'approved', 'status': 'possible', 'allow_new_relationship': True,
                  'source_ids': ['family-record'], 'perspectives': {
                      'Example-1': {'relationship': 'father', 'reason': 'An explicitly possible family.'}}}
        shared_only = module.resolve(current, [], [shared])
        self.assertIn(claim, shared_only['claims'])
        self.assertIn(claim, shared_only['imported']['sections']['claims'])
        self.assertEqual(shared_only, module.resolve(shared_only, [], [shared]))

    def test_unknown_vital_location_projection_keeps_blank_filters_and_original_source(self):
        rows = [{'id': 'Example-1', 'birth_location': 'Earlier claim', 'death_location': 'Earlier claim'}]
        review = {'id': 'review', 'subject': 'Example-1', 'status': 'approved',
                  'catalogue_projection': {'birth_location': 'Unknown', 'death_location': ' unknown ',
                                           'birth_location_note': 'No birthplace recorded.'}}
        module.project_catalogue_vitals(rows, [review])
        self.assertEqual('', rows[0]['birth_location'])
        self.assertEqual('', rows[0]['death_location'])
        self.assertEqual('No birthplace recorded.', rows[0]['birth_location_note'])
        self.assertEqual('Earlier claim', rows[0]['vital_review']['original_fields']['birth_location']['value'])
        self.assertEqual('Unknown', review['catalogue_projection']['birth_location'])

    def test_durable_register_replaces_its_rows_and_revokes_without_dropping_other_reviews(self):
        old = {'id': 'review', 'subject': 'Person-1', 'status': 'approved', 'vitals': {'death': {'date': '1841'}}}
        other = {'id': 'other', 'subject': 'Person-2', 'status': 'approved'}
        current = {**old, 'vitals': {'death': {'date': None, 'status': 'unknown'}}}
        registry = {'schema_version': 1, 'assessments': [old, other]}
        merged = module.merge_maintained_assessments(registry, [current])
        self.assertEqual([current, other], merged['assessments'])
        self.assertEqual(merged, module.merge_maintained_assessments(merged, [current]))
        self.assertEqual([other], module.merge_maintained_assessments(merged, [])['assessments'])
        self.assertEqual([old, other], registry['assessments'])
        with self.assertRaisesRegex(ValueError, 'unique IDs'):
            module.merge_maintained_assessments(registry, [current, current])

    def test_publish_reads_durable_register_and_revokes_removed_source_row(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            root = project / 'www'
            original = {'id': 'Person-1', 'vitals': {'death': {'date': 'before 1841'}}, 'claims': []}
            review = {'id': 'withdrawal', 'subject': 'Person-1', 'status': 'approved',
                      'vitals': {'death': {'date': None, 'status': 'unknown'}}}
            files = {'www/people/person-1.json': original,
                     'www/data/ancestry-documentary-people.json': {'chronology': []},
                     'research/vital_assessments.json': {'assessments': [review]},
                     'research/relationship_assessments.json': [],
                     'research/canonical_records.json': [],
                     'research/relationship_probability_estimates.json': {'estimates': []},
                     'research/ancestry-connections/documentary-people.json': {'chronology': []}}
            for name, value in files.items():
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            with patch.object(module, 'ROOT', project):
                module.publish(root)
                current = json.loads((root / 'people/person-1.json').read_text())
                self.assertIsNone(current['vitals']['death']['date'])
                self.assertEqual(original['vitals'], current['imported']['sections']['vitals'])
                (project / 'research/vital_assessments.json').write_text('{"assessments": []}')
                module.publish(root)
            self.assertEqual(original, json.loads((root / 'people/person-1.json').read_text()))

    def test_explicit_withdrawal_projection_updates_catalogue_and_restores_import(self):
        original = [{'profile_ids': ['Person-1'], 'death': 'before 1841', 'death_year': 1841}]
        review = {'subject': 'Person-1', 'id': 'withdrawn-boundary', 'status': 'approved',
                  'catalogue_projection': {'death': 'Death unknown', 'death_year': None}}
        rows = json.loads(json.dumps(original))
        module.project_catalogue_vitals(rows, [review])
        self.assertIsNone(rows[0]['death_year'])
        self.assertEqual('Death unknown', rows[0]['death'])
        module.project_catalogue_vitals(rows, [])
        self.assertEqual(original, rows)

    def test_catalogue_parents_follow_assessments_and_restore_on_withdrawal(self):
        from copy import deepcopy
        original = [{'id': 'child-1', 'father': [], 'missing_father': True,
                     'mother': [{'id': 'Mother-1', 'name': 'Mother'}], 'missing_mother': False}]
        reviewed = {'child-1': {'relationships': {'parents': [
            {'id': 'Father-1', 'name': 'Working father', 'relationship': 'father',
             'status': 'uncertain', 'status_label': 'Selected uncertain father',
             'lifecycle': 'current', 'display': 'hypothesis', 'url': '/people/father-1.html'},
            {'id': 'Old-1', 'relationship': 'father', 'status': 'uncertain',
             'lifecycle': 'alternative'},
            {'id': 'Private-1', 'relationship': 'father', 'publication_status': 'withheld'},
            {'id': 'Mother-1', 'name': 'Mother', 'relationship': 'mother',
             'status': 'unknown', 'tree_status': 'confident', 'tree_status_label': 'Saved tree flag'}]}}}
        result = module.project_catalogue_parents(deepcopy(original), reviewed)
        self.assertEqual([p['id'] for p in result[0]['father']], ['Father-1'])
        self.assertEqual(result[0]['father'][0]['certainty'], 'uncertain')
        self.assertEqual(result[0]['father'][0]['url'], '/people/father-1.html')
        self.assertEqual(result[0]['mother'][0]['certainty'], 'confident')
        self.assertFalse(result[0]['missing_father'])
        self.assertEqual(module.project_catalogue_parents(deepcopy(result), reviewed), result)
        self.assertEqual(module.project_catalogue_parents(result, {}), original)

    def test_catalogue_documentary_father_preserves_account_without_wikitree_url(self):
        rows = [{'id': 'child-1'}]
        dossier = {'relationships': {'parents': [{'id': 'record-father-1450',
            'relationship': 'father', 'status': 'possible', 'name': 'Documentary father',
            'url': '/free-space/early-father/', 'wikitree_url': None}]}}
        module.project_catalogue_parents(rows, {'child-1': dossier})
        self.assertEqual(rows[0]['father'][0]['url'], '/free-space/early-father/')
        self.assertIsNone(rows[0]['father'][0]['wikitree_url'])
        self.assertTrue(rows[0]['missing_mother'])

    def test_unselected_parent_remains_an_alternative_in_claims_and_relationships(self):
        original={'id':'Child-1','relationships':{'parents':[{'id':'Old-1','relationship':'father','status':'uncertain','claim_id':'C-import'}]},'claims':[]}
        alternative={'assertion_id':'A-old','people':['Child-1','Old-1'],'publication_status':'approved',
            'status':'uncertain','status_label':'Unselected father candidate','lifecycle':'alternative',
            'basis':'Prior uncertainty retained','source_ids':['S-1'],
            'perspectives':{'Child-1':{'relationship':'father','reason':'Alternative retained'}}}
        resolved=module.resolve(original,[],[alternative])
        self.assertEqual(resolved['relationships']['parents'][0]['lifecycle'],'alternative')
        self.assertEqual(next(c for c in resolved['claims'] if c['id']=='A-old')['lifecycle'],'alternative')
        self.assertEqual(resolved['relationships']['parents'][0]['status'],'uncertain')
        self.assertEqual(resolved['imported']['sections']['relationships'],original['relationships'])

    def test_redirect_stub_sharing_an_id_does_not_replace_the_dossier_in_projections(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            row = {'id': 'Parent-2', 'name': 'A parent', 'claim_id': 'claim-1', 'json_url': '/people/parent-2.json',
                   'historical_claim_ids': ['claim-0']}
            dossier = {'id': 'Person-1', 'data_view': 'reviewed', 'relationships': {'parents': [row]},
                       'claims': [], 'research_assessments': []}
            stub = {'id': 'Person-1', 'status': 'superseded', 'redirect_to': '/people/person-1.json', 'data_view': 'reviewed',
                    'relationships': {'parents': [{'id': 'Parent-2', 'name': 'A parent', 'claim_id': 'claim-1'}]},
                    'claims': [], 'research_assessments': []}
            files = {'people/person-1.json': dossier, 'people/record-zz-retired.json': stub,
                     'people/person-1.network.json': {'person': {'id': 'Person-1'}, 'relationships': []},
                     'assets/research/assessments.json': {'assessments': []}}
            for name, value in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            module.publish(root)
            network = json.loads((root / 'people/person-1.network.json').read_text())
            published = json.loads((root / 'people/person-1.json').read_text())
            self.assertEqual(published['relationships']['parents'], network['relationships'])
            self.assertEqual('/people/parent-2.json', network['relationships'][0]['json_url'])
            self.assertEqual(['claim-0'], network['relationships'][0]['historical_claim_ids'])

    def test_chronology_vitals_are_published_and_revocable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            original={'id':'Person-1','vitals':{'birth':{'date':'c. 1610','status':'estimated'}},'relationships':{},'claims':[]}
            search=[{'id':'person-1','profile_ids':['Person-1'],'birth':'c. 1610','birth_year':1610,'date_years':[1610]}]
            files={'people/person-1.json':original,'assets/research/assessments.json':{'assessments':[]},
                   'data/catalogue-search-index.json':search,
                   'data/people.json':{'people':search},
                   'data/ancestry-documentary-people.json':{'chronology':[dict(id='Person-1',publication_status='approved',
                       source_ids=['sasine-1601'],assessment_id='chronology-1',reviewed='2026-10-16',reason='Probable married household in 1601',
                       vitals={'birth':{'date':'before 1601','status':'uncertain'}},
                       catalogue_projection={'birth':'Birth unknown; married by 1601, probably','birth_year':None,'date_years':[1601]})]}}
            for name,value in files.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
            module.publish(root)
            current=json.loads((root/'people/person-1.json').read_text())
            self.assertEqual(current['vitals']['birth']['date'],'before 1601')
            self.assertEqual(current['imported']['sections']['vitals'],original['vitals'])
            registry=json.loads((root/'assets/research/assessments.json').read_text())
            self.assertEqual(registry['assessments'][0]['id'],'chronology-1')
            projected=json.loads((root/'data/catalogue-search-index.json').read_text())[0]
            self.assertIsNone(projected['birth_year']);self.assertEqual(projected['date_years'],[1601])
            bulk=json.loads((root/'data/people.json').read_text())['people'][0]
            for field in ('birth', 'birth_year', 'date_years', 'vital_review'):
                self.assertEqual(bulk[field], projected[field])
            frozen=(root/'people/person-1.json').read_bytes();module.publish(root)
            self.assertEqual((root/'people/person-1.json').read_bytes(),frozen)
            (root/'data/ancestry-documentary-people.json').write_text('{"chronology":[]}')
            module.publish(root)
            self.assertEqual(json.loads((root/'people/person-1.json').read_text()),original)
            self.assertEqual(json.loads((root/'data/catalogue-search-index.json').read_text()),search)
            self.assertEqual(json.loads((root/'data/people.json').read_text())['people'],search)

    def test_corrected_sibling_role_retires_parent_row_and_preserves_history(self):
        original = {'id': 'Person-1', 'relationships': {
            'parents': [{'id': 'Father-1', 'relationship': 'father', 'status': 'strongly_supported'},
                        {'id': 'Person-2', 'relationship': 'father', 'status': 'proved', 'claim_id': 'wrong-role'}],
            'siblings': [{'id': 'Person-2', 'relationship': 'sibling', 'status': 'unknown', 'claim_id': 'old-sibling'}]},
            'claims': [{'id': 'wrong-role', 'status': 'proved'}, {'id': 'old-sibling', 'status': 'unknown'}]}
        review = {'assertion_id': 'sibling-review', 'people': ['Person-1', 'Person-2'],
                  'publication_status': 'approved', 'status': 'proved', 'source_ids': ['will'],
                  'perspectives': {'Person-1': {'relationship': 'sibling', 'reason': 'The will says sister'}},
                  'role_correction': {'Person-1': {'from': ['father'], 'to': 'sibling'}},
                  'historical_assertions': [{'profile_id': 'Person-1', 'claim_id': 'wrong-role',
                                             'label': 'Historical role error', 'scope': 'Parent role only'}]}
        result = module.resolve(original, [], [review])
        self.assertEqual([{k:v for k,v in r.items() if k != 'probability'} for r in result['relationships']['parents']], original['relationships']['parents'][:1])
        self.assertEqual(result['relationships']['parents'][0]['probability']['band'], 'confident')
        siblings = result['relationships']['siblings']
        self.assertEqual(len(siblings), 1)
        self.assertEqual((siblings[0]['id'], siblings[0]['relationship'], siblings[0]['status']),
                         ('Person-2', 'sibling', 'proved'))
        self.assertEqual(result['imported']['sections']['relationships'], original['relationships'])
        self.assertEqual(len(result['relationship_history']), 2)
        self.assertEqual(next(c for c in result['claims'] if c['id']=='wrong-role')['status'], 'superseded')
        self.assertEqual(result, module.resolve(result, [], [review]))

    def test_documentary_father_has_no_invented_wikitree_url(self):
        original = {'id': 'Example-1', 'relationships': {}, 'claims': []}
        assessment = {'assertion_id': 'record-father', 'people': ['Example-1', 'record-john-1475'],
                      'publication_status': 'approved', 'status': 'uncertain',
                      'allow_new_relationship': True, 'source_ids': ['stirling-record'],
                      'profile_urls': {'record-john-1475': {'url': '/free-space/stirling-john/'}},
                      'perspectives': {'Example-1': {'relationship': 'father', 'reason': 'Working father'}}}
        result = module.resolve(original, [], [assessment])
        father = result['relationships']['parents'][0]
        self.assertEqual(father['url'], '/free-space/stirling-john/')
        self.assertIsNone(father['wikitree_url'])
        assessment['profile_urls']['record-john-1475']['url'] = '/research/subjects/example/#named-parent'
        father = module.resolve(original, [], [assessment])['relationships']['parents'][0]
        self.assertEqual(father['url'], '/research/subjects/example/#named-parent')
        self.assertIsNone(father['wikitree_url'])
        assessment['profile_urls']['record-john-1475']['url'] = '//example.test/unreviewed'
        with self.assertRaisesRegex(ValueError, 'invalid documentary account URL'):
            module.resolve(original, [], [assessment])

    def test_selected_father_keeps_other_candidate_without_counting_both(self):
        from tools.branch_connectivity import load_public_nodes, summarize

        original = {'id': 'Example-1', 'identity': {'gender': 'Female'},
                    'vitals': {'birth': {'date': '1600'}},
                    'relationships': {'parents': [{'id': 'Example-2', 'relationship': 'father',
                                                   'status': 'possible', 'claim_id': 'old'}]},
                    'claims': [{'id': 'old', 'status': 'possible'}]}
        selected = {'assertion_id': 'selected', 'people': ['Example-1', 'Example-3'],
                    'publication_status': 'approved', 'status': 'uncertain',
                    'hypothesis_status': 'possible', 'working_selection': True,
                    'allow_new_relationship': True, 'source_ids': ['record-context'],
                    'perspectives': {'Example-1': {'relationship': 'father', 'reason': 'Preferred local family'}}}
        alternative = {'assertion_id': 'alternative', 'people': ['Example-1', 'Example-2'],
                       'publication_status': 'approved', 'status': 'possible',
                       'lifecycle': 'alternative', 'display': 'alternative',
                       'perspectives': {'Example-1': {'relationship': 'father',
                                                     'reason': 'Viable other family, still open'}}}
        result = module.resolve(original, [], [selected, alternative])
        parents = {r['id']: r for r in result['relationships']['parents']}
        self.assertEqual(parents['Example-2']['status'], 'possible')
        self.assertEqual(parents['Example-2']['reason'], 'Viable other family, still open')
        self.assertEqual(result['imported']['sections']['relationships'], original['relationships'])
        self.assertEqual(result, module.resolve(result, [], [selected, alternative]))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'people').mkdir(); (root / 'data').mkdir()
            rows = []
            for person in ['Example-1', 'Example-2', 'Example-3']:
                dossier = result if person == 'Example-1' else {
                    'id': person, 'vitals': {'birth': {'date': '1570'}}}
                (root / 'people' / f'{person.lower()}.json').write_text(json.dumps(dossier))
                rows.append({'id': person, 'birth_surnames': ['Example'],
                             'json_url': f'/people/{person.lower()}.json'})
            (root / 'data/people-index.json').write_text(json.dumps(rows))
            nodes, edges, quality = load_public_nodes(root, {'Example'})
            self.assertEqual([(e['child'], e['father']) for e in edges], [('Example-1', 'Example-3')])
            self.assertEqual(quality['multiple_fathers'], [])
            self.assertEqual(summarize(nodes, edges, 1650, 'confident')['edge_count'], 0)

    def test_review_preserves_import_and_is_idempotent(self):
        original = {'id': 'Person-1', 'vitals': {'death': {'place': 'Imported', 'status': 'exact'}},
                    'relationships': {'parents': [{'id': 'Person-2', 'claim_id': 'C1', 'status': 'unknown'}]},
                    'claims': [{'id': 'C1', 'status': 'unknown'}], 'provenance': {'tree': 'export'}}
        review = {'id': 'review-1', 'subject': 'Person-1', 'status': 'approved',
                  'vitals': {'death': {'place': 'Reviewed', 'status': 'strongly_supported'}},
                  'relationships': [{'group': 'parents', 'target': 'Person-2', 'status': 'superseded', 'display': 'alternative'}]}
        result = module.resolve(original, [review])
        self.assertEqual(result['vitals']['death']['place'], 'Reviewed')
        self.assertEqual(result['imported']['sections']['vitals']['death']['place'], 'Imported')
        self.assertEqual(result['claims'][0]['status'], 'superseded')
        self.assertEqual(result, module.resolve(result, [review]))
        self.assertEqual(module.resolve(original, []), module.resolve(result, []))
        review['status'] = 'draft'
        self.assertEqual(module.resolve(original, []), module.resolve(original, [review]))

    def test_narrative_does_not_invent_structured_facts(self):
        dossier = {'id': 'Person-1', 'vitals': {'death': {'place': 'Imported'}}, 'relationships': {}, 'claims': []}
        review = {'id': 'r', 'subject': 'Person-1', 'status': 'approved', 'supersedes': ['Imported death place'], 'summary': 'Died elsewhere'}
        self.assertEqual(module.resolve(dossier, [review])['vitals'], dossier['vitals'])

    def test_latest_review_wins_regardless_of_input_order(self):
        dossier = {'id': 'Person-1', 'vitals': {}, 'relationships': {}, 'claims': []}
        old = {'id': 'old', 'subject': 'Person-1', 'status': 'approved', 'reviewed': '2026-01-01', 'vitals': {'death': {'place': 'Old'}}}
        new = {**old, 'id': 'new', 'reviewed': '2026-02-01', 'vitals': {'death': {'place': 'New'}}}
        self.assertEqual(module.resolve(dossier, [new, old])['vitals']['death']['place'], 'New')

    def test_publish_and_revoke_updates_all_surfaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dossier = {'id': 'Person-1', 'vitals': {'death': {'place': 'Imported'}}, 'relationships': {'parents': []}, 'claims': []}
            row = {'id': 'Person-1', 'death_place': 'Imported', 'parent_ids': ['Person-2']}
            network = {'person': {'id': 'Person-1'}, 'relationships': []}
            assessment = {'id': 'r', 'subject': 'Person-1', 'status': 'approved', 'vitals': {'death': {'place': 'Reviewed', 'status': 'possible'}}}
            files = {'people/person-1.json': dossier, 'people/person-1.network.json': network,
                     'data/people-index.json': [row], 'data/resolve/name.json': {'candidates': [row]},
                     'data/schema/person.schema.json': {'properties': {}},
                     'assets/research/assessments.json': {'assessments': [assessment]}}
            for name, value in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            module.publish(root)
            self.assertEqual(json.loads((root / 'data/resolve/name.json').read_text())['candidates'][0]['death_place'], 'Reviewed')
            self.assertIn('imported', json.loads((root / 'data/schema/person.schema.json').read_text())['properties'])
            contents = {p: p.read_bytes() for p in root.rglob('*.json')}
            module.publish(root)
            self.assertTrue(all(p.read_bytes() == value for p, value in contents.items()))
            (root / 'assets/research/assessments.json').write_text('{"assessments": []}')
            module.publish(root)
            for name in ['people/person-1.json', 'people/person-1.network.json', 'data/people-index.json', 'data/resolve/name.json']:
                self.assertEqual(json.loads((root / name).read_text()), files[name])


if __name__ == '__main__':
    unittest.main()
