import json
import tempfile
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from genealogy.store import open_project
from workbench_documents import Documents, frame_id

class DocumentMoveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        (self.root / 'genealogy.toml').write_text('[project]\nname="T"\n[storage]\ndatabase="db.sqlite"\n')
    def tearDown(self): self.tmp.cleanup()
    def test_candidate_reordering_keeps_candidate_identity(self):
        path = 'research/example/parent_candidates.json'
        rows = [{'id': 'alpha', 'candidate': 'Parent A'}, {'id': 'beta', 'candidate': 'Parent B'}]
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, path, rows)
            before = {json.loads(r['row_json'])['id']: r['entity'] for r in d.stored_rows(path)}
            with p.store.write(actor='test', tool='edit') as tx:
                d.store_document(tx, path, rows[::-1])
            after = {json.loads(r['row_json'])['id']: r['entity'] for r in d.stored_rows(path)}
            self.assertEqual(before, after)

    def test_partial_folder_move_rolls_back(self):
        from tools.research_entry import record_document
        old = 'research/example/research_plan.json'
        new = 'research/record-example/research_plan.json'
        doc = {'questions': [], 'web_searches': [], 'findings': []}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, old, doc)
                d.store_document(tx, 'research/example/parent_candidates.json', [])
            revision = d.frame(old)['note']['revision']
            with self.assertRaisesRegex(ValueError, 'other held documents'):
                record_document(p, new, doc, expected_revision=revision, actor='test', reason='move', move_from=old)
            self.assertEqual(revision, d.frame(old)['note']['revision'])
            self.assertIsNone(d.frame(new))
    def test_move_preserves_ids_and_later_edit(self):
        old='research/subject-old/research_plan.json'; new='research/record-new/research_plan.json'
        doc={'questions':[{'question':'Q'}], 'web_searches':[{'query':'X','result':'none'}], 'findings':[{'note':'Retained narrative'}]}
        with open_project(self.root,create=True) as p:
            d=Documents(p.store)
            with p.store.write(actor='t',tool='t',source='t',reason='t') as tx: d.store_document(tx,old,doc)
            oldrev=d.frame(old)['note']['revision']; rows=d.stored_rows(old); ids={(r['field'],r['entity']) for r in rows}
            with p.store.write(actor='t',tool='t',source='t',reason='move') as tx: d.move_document(tx,old,new,oldrev)
            self.assertIsNone(d.frame(old)); self.assertIsNotNone(d.frame(new))
            self.assertEqual(ids,{(r['field'],r['entity']) for r in d.stored_rows(new)})
            changed={'questions':[{'question':'Q2'}], 'web_searches':doc['web_searches'], 'findings':doc['findings']}
            with p.store.write(actor='t',tool='t',source='t',reason='edit') as tx: d.store_document(tx,new,changed)
            self.assertEqual('Q2', d.compose(new)['questions'][0]['question'])
            self.assertEqual(ids, {(r['field'],r['entity']) for r in d.stored_rows(new)})
            self.assertNotIn(old, d.files())
            self.assertIn(new, d.files())
            self.assertEqual('document_frame_history', p.store.get('note',frame_id(old))['kind'])
    def test_stale_and_destination_conflict(self):
        old='research/a/research_plan.json'; new='research/b/research_plan.json'; doc={'questions':[],'web_searches':[],'findings':[]}
        with open_project(self.root,create=True) as p:
            d=Documents(p.store)
            with p.store.write(actor='t',tool='t',source='t',reason='t') as tx: d.store_document(tx,old,doc)
            rev=d.frame(old)['note']['revision']
            with self.assertRaises(ValueError):
                with p.store.write(actor='t',tool='t',source='t',reason='x') as tx: d.move_document(tx,old,new,rev-1)
            self.assertIsNotNone(d.frame(old))
            self.assertIsNone(d.frame(new))
            with p.store.write(actor='t',tool='t',source='t',reason='x') as tx: d.move_document(tx,old,new,rev)
            with self.assertRaises(ValueError):
                with p.store.write(actor='t',tool='t',source='t',reason='x') as tx: d.move_document(tx,new,old,d.frame(new)['note']['revision'])

    def test_catalogue_integration_profile_updates_and_new_people_round_trip(self):
        path = 'research/queue-review-2026-10-17/catalogue-integration.json'
        document = {
            'schema_version': 1,
            'profile_updates': {
                'Glasgow-589': {'draft_path': 'research/Glasgow-589/parent-review-2026-10-27.wiki',
                                'summary': 'Current review'}
            },
            'new_people': [{'subject_id': 'record-example', 'name': 'Example'}],
            'reviewed_on': '2026-10-27'
        }
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, path, document)
            self.assertEqual(document, d.compose(path))
            self.assertEqual({'profile_updates', 'new_people'},
                             {row['field'] for row in d.stored_rows(path)})
