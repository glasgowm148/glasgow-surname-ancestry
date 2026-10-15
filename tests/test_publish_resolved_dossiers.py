import importlib.util
from pathlib import Path
import unittest
import json
import tempfile

spec = importlib.util.spec_from_file_location('resolver', Path(__file__).resolve().parents[1] / 'tools/publish_resolved_dossiers.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResolvedDossierTests(unittest.TestCase):
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
        self.assertEqual(original, module.resolve(result, []))
        review['status'] = 'draft'
        self.assertEqual(original, module.resolve(original, [review]))

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
