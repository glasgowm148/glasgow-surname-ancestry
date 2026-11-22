import json
import tempfile
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from genealogy.store import open_project
from workbench_documents import Documents, frame_id
from research_integrity import CREATION_DOCUMENT, row_sha256, hold_condition
from genealogy.store import Research

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

    def test_duplicate_subject_is_rejected_inside_document_transaction(self):
        document = {'new_people': [
            {'subject_id': 'subject-example', 'catalogue_id': 'record-first'},
            {'subject_id': 'subject-example', 'catalogue_id': 'record-second'}]}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with self.assertRaisesRegex(ValueError, 'Duplicate canonical subject_id'):
                with p.store.write(actor='test', tool='fixture') as tx:
                    d.store_document(tx, CREATION_DOCUMENT, document)
            self.assertIsNone(d.frame(CREATION_DOCUMENT))
            self.assertEqual([], d.stored_rows(CREATION_DOCUMENT))

    def test_hold_releases_require_current_record_evidence_and_roll_back(self):
        from tools.research_entry import record_document
        held = {'subject_id': 'subject-example', 'catalogue_id': 'record-example',
                'creation_status': 'hold_source_verification',
                'hold_condition': 'Inspect the original year heading.'}
        document = {'new_people': [held]}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                record = Research(p.store).add_record(tx, title='Fictional register')
                d.store_document(tx, CREATION_DOCUMENT, document)
            revision = d.frame(CREATION_DOCUMENT)['note']['revision']
            new = {**held, 'creation_status': 'creation_ready'}
            def save(row):
                return record_document(p, CREATION_DOCUMENT, {'new_people': [row]},
                                       expected_revision=revision, actor='test', reason='Review')
            with self.assertRaisesRegex(ValueError, 'evidence receipt'):
                save(new)
            receipt = {'previous_row_sha256': row_sha256(held), 'condition': hold_condition(held),
                       'decision': 'satisfied', 'reason': 'Original heading inspected.',
                       'reviewed_by': 'fixture-reviewer',
                       'evidence': [{'record_id': record, 'revision': 99, 'locator': 'page 2, heading'}]}
            new['hold_release'] = receipt
            with self.assertRaisesRegex(ValueError, 'missing or stale'):
                save(new)
            self.assertEqual(document, d.compose(CREATION_DOCUMENT))
            self.assertEqual(revision, d.frame(CREATION_DOCUMENT)['note']['revision'])
            receipt['evidence'][0]['revision'] = p.store.get('record', record)['revision']
            save(new)
            self.assertEqual(new, d.compose(CREATION_DOCUMENT)['new_people'][0])

    def test_creation_reordering_preserves_rows_and_cannot_hide_a_hold_release(self):
        held = {'subject_id': 'subject-held', 'catalogue_id': 'record-held', 'creation_status': 'identity_hold'}
        other = {'subject_id': 'subject-other', 'catalogue_id': 'record-other', 'creation_status': 'creation_ready'}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, CREATION_DOCUMENT, {'new_people': [held, other]})
            before = {json.loads(r['row_json'])['catalogue_id']: r['entity']
                      for r in d.stored_rows(CREATION_DOCUMENT)}
            with p.store.write(actor='test', tool='reorder') as tx:
                d.store_document(tx, CREATION_DOCUMENT, {'new_people': [other, held]})
            after = {json.loads(r['row_json'])['catalogue_id']: r['entity']
                     for r in d.stored_rows(CREATION_DOCUMENT)}
            self.assertEqual(before, after)
            added = {'subject_id': 'subject-new', 'catalogue_id': 'record-new'}
            with p.store.write(actor='test', tool='add-after-reorder') as tx:
                d.store_document(tx, CREATION_DOCUMENT, {'new_people': [other, held, added]})
            self.assertEqual([other, held, added], d.compose(CREATION_DOCUMENT)['new_people'])
            self.assertEqual(3, len({r['entity'] for r in d.stored_rows(CREATION_DOCUMENT)}))
            with self.assertRaisesRegex(ValueError, 'evidence receipt'):
                with p.store.write(actor='test', tool='edit') as tx:
                    d.store_document(tx, CREATION_DOCUMENT,
                                     {'new_people': [other, {**held, 'creation_status': 'creation_ready'}]})

    def test_identity_review_cannot_be_closed_or_removed_without_a_receipt(self):
        path = 'research/research-queue-matches.json'
        held = {'status': 'identity_hold', 'assessment': 'Compare both surviving candidates.'}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, path, {'reviews': {'example': held}})
            for reviews in ({}, {'example': {**held, 'status': 'matched'}}):
                with self.subTest(reviews=reviews), self.assertRaises(ValueError):
                    with p.store.write(actor='test', tool='edit') as tx:
                        d.store_document(tx, path, {'reviews': reviews})
            self.assertEqual(held, d.compose(path)['reviews']['example'])
            with self.assertRaisesRegex(ValueError, 'evidence receipt'):
                with p.store.write(actor='test', tool='shadow-status') as tx:
                    d.store_document(tx, path, {'reviews': {'example': {
                        **held, 'status': 'matched', 'creation_status': 'identity_hold'}}})

    def test_held_question_cannot_disappear_or_close_by_reordering(self):
        path = 'research/example/research_plan.json'
        held = {'id': 'heading', 'question': 'Which register year?', 'status': 'blocked'}
        other = {'id': 'other', 'question': 'Which parish?', 'status': 'open'}
        document = {'questions': [held, other]}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, path, document)
            for questions in ([other], [other, {**held, 'status': 'answered'}],
                              [{**held, 'status': 'answered', 'creation_status': 'blocked'}, other]):
                with self.subTest(questions=questions), self.assertRaises(ValueError):
                    with p.store.write(actor='test', tool='edit') as tx:
                        d.store_document(tx, path, {'questions': questions})
            self.assertEqual(document, d.compose(path))

    def test_creation_hold_cannot_move_to_a_field_the_publisher_ignores(self):
        held = {'catalogue_id': 'record-example', 'subject_id': 'subject-example',
                'creation_status': 'identity_hold'}
        with open_project(self.root, create=True) as p:
            d = Documents(p.store)
            with p.store.write(actor='test', tool='fixture') as tx:
                d.store_document(tx, CREATION_DOCUMENT, {'new_people': [held]})
            bypass = {key: value for key, value in held.items() if key != 'creation_status'}
            bypass['status'] = 'identity_hold'
            with self.assertRaisesRegex(ValueError, 'evidence receipt'):
                with p.store.write(actor='test', tool='shadow-status') as tx:
                    d.store_document(tx, CREATION_DOCUMENT, {'new_people': [bypass]})
            self.assertEqual(held, d.compose(CREATION_DOCUMENT)['new_people'][0])
