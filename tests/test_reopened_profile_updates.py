import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_research_catalog as catalogue
from tools.publish_resolved_dossiers import resolve as resolve_dossier


class ReopenedProfileUpdatesTest(unittest.TestCase):
    def test_no_public_capture_requires_private_hash_proof_and_exposes_only_safe_addition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            private = root / 'data/private/review'
            private.mkdir(parents=True)
            public_index = root / 'www/data/people-index.json'
            public_index.parent.mkdir(parents=True)
            historical_row = dict(id='Glasgow-1', json_url='/people/glasgow-1.json', birth_year=1760)
            public_index.write_text(json.dumps([historical_row]))
            addition = 'A historical marriage is recorded.<ref>[https://example.org/register Original register].</ref>'
            current = '== Biography ==\nSENTINEL_PRIVATE_DNA_TESTER\n== Sources ==\n<references />'
            proposed = current.replace('== Sources ==', addition + '\n== Sources ==')
            current_path = private / 'current.wiki'
            current_path.write_text(current)
            (private / 'proposed.wiki').write_text(proposed)
            audit = private / 'audit.json'
            audit.write_text(json.dumps({'profiles': {'Glasgow-1': {
                'current_sha256': hashlib.sha256(current.encode()).hexdigest(),
                'proposed_sha256': hashlib.sha256(proposed.encode()).hexdigest(),
                'all_substantive_passages_accounted_for': True}}}))
            specification = dict(private_comparison=True, public_addition_wikitext=addition,
                private_capture_path='data/private/review/current.wiki',
                draft_path='data/private/review/proposed.wiki',
                preservation_review_path='data/private/review/audit.json', pending=True,
                summary='SENTINEL_PRIVATE_DNA_TESTER', significance=80)
            queue = root / 'queue.json'
            queue.write_text(json.dumps({'entries': {'Glasgow-1': specification}}))
            with patch.object(catalogue, 'PROJECT_ROOT', root), patch.object(catalogue, 'PROFILE_UPDATE_QUEUE', queue), \
                 patch.object(catalogue, 'privacy_from_sources') as privacy:
                privacy.return_value.contains_private_id.return_value = False
                update = catalogue._load_profile_updates({'profiles': {}})['Glasgow-1']
                public = json.dumps(update)
                self.assertIn(addition, update['public_addition_wikitext'])
                self.assertTrue(update['comparison_withheld'])
                for secret in ('SENTINEL_PRIVATE_DNA_TESTER', 'data/private', str(private), 'private_capture_path', 'preservation_review_path'):
                    self.assertNotIn(secret, public)
                self.assertEqual('', update['remote_wikitext'])
                self.assertEqual('', update['proposed_wikitext'])
                self.assertEqual('', update['draft_wikitext'])
                for invalid_rows in ([], [dict(historical_row, birth_year=2000)],
                                     [dict(historical_row, birth_year=None)],
                                     [dict(historical_row, json_url='/people/another.json')]):
                    public_index.write_text(json.dumps(invalid_rows))
                    with self.assertRaisesRegex(ValueError, 'already published historical subject'):
                        catalogue._load_profile_updates({'profiles': {}})
                public_index.write_text('[]')
                metadata = dict(Name='Glasgow-1', Privacy=60, IsLiving=False, BirthDate='1753-00-00')
                capture = dict(narrative_withheld=True, profile_fields=metadata,
                               biography_wikitext='', biography_text='', record_passages=[], relations={})
                safe_update = catalogue._load_profile_updates({'profiles': {'Glasgow-1': capture}})['Glasgow-1']
                self.assertTrue(safe_update['comparison_withheld'])
                self.assertNotIn('SENTINEL_PRIVATE_DNA_TESTER', json.dumps(safe_update))
                self.assertNotIn('data/private', json.dumps(safe_update))
                for invalid_fields in (dict(metadata, Name='Glasgow-2'), dict(metadata, Privacy=30),
                                       dict(metadata, IsLiving=True), dict(metadata, BirthDate='2000-01-01'),
                                       dict(metadata, BirthDate='0000-00-00')):
                    with self.assertRaisesRegex(ValueError, 'safe historical metadata'):
                        catalogue._load_profile_updates({'profiles': {'Glasgow-1': dict(capture, profile_fields=invalid_fields)}})
                with self.assertRaisesRegex(ValueError, 'safe historical metadata'):
                    catalogue._load_profile_updates({'profiles': {'Glasgow-1': dict(capture, biography_wikitext=current)}})
                dossier_path = root / 'www/people/glasgow-1.json'
                dossier_path.parent.mkdir()
                html_path = dossier_path.with_suffix('.html')
                public_dossier = dict(id='Glasgow-1', vitals={'birth': {'date': 'c. 1753'}})
                dossier_path.write_text(json.dumps(public_dossier))
                html_path.write_text('<html><body>Existing historical account</body></html>')
                self.assertTrue(catalogue._load_profile_updates({'profiles': {}})['Glasgow-1']['comparison_withheld'])
                for invalid in (dict(public_dossier, id='Glasgow-2'), dict(public_dossier, living=True),
                                dict(public_dossier, vitals={'birth': {'date': '2000-01-01'}}),
                                dict(public_dossier, vitals={'birth': {'date': '1753-99-99'}}),
                                dict(public_dossier, vitals={'birth': {'date': ''}})):
                    dossier_path.write_text(json.dumps(invalid))
                    with self.assertRaisesRegex(ValueError, 'already published historical subject'):
                        catalogue._load_profile_updates({'profiles': {}})
                dossier_path.write_text(json.dumps(public_dossier))
                html_path.unlink()
                with self.assertRaisesRegex(ValueError, 'already published historical subject'):
                    catalogue._load_profile_updates({'profiles': {}})
                html_path.symlink_to(dossier_path)
                with self.assertRaisesRegex(ValueError, 'already published historical subject'):
                    catalogue._load_profile_updates({'profiles': {}})
                html_path.unlink()
                dossier_path.unlink()
                public_index.write_text(json.dumps([historical_row]))
                privacy.return_value.contains_private_id.return_value = True
                with self.assertRaisesRegex(ValueError, 'withheld material'):
                    catalogue._load_profile_updates({'profiles': {}})
                privacy.return_value.contains_private_id.return_value = False
                unsafe = dict(specification, relationship_changes=[{'reason': 'data/private/raw.wiki'}])
                queue.write_text(json.dumps({'entries': {'Glasgow-1': unsafe}}))
                with self.assertRaisesRegex(ValueError, 'withheld material'):
                    catalogue._load_profile_updates({'profiles': {}})
                queue.write_text(json.dumps({'entries': {'Glasgow-1': specification}}))
                (private / 'proposed.wiki').write_text(proposed + '\nTampered proposal.')
                with self.assertRaisesRegex(ValueError, 'preservation review is stale'):
                    catalogue._load_profile_updates({'profiles': {}})
                (private / 'proposed.wiki').write_text(proposed)
                current_path.write_text(current + '\nTampered.')
                with self.assertRaisesRegex(ValueError, 'preservation review is stale'):
                    catalogue._load_profile_updates({'profiles': {}})
                current_path.write_text(current)
                audit.unlink()
                with self.assertRaisesRegex(ValueError, 'private preservation proof'):
                    catalogue._load_profile_updates({'profiles': {}})

    def test_targeted_load_preserves_validation_without_loading_unrelated_draft(self):
        biography = '== Biography ==\nA recorded life.\n== Sources ==\n<references />'
        evidence = {'profiles': {'Glasgow-1': {'biography_wikitext': biography}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'queue.json'
            path.write_text(json.dumps({'entries': {
                'Glasgow-1': {'summary': 'Review', 'manual_update': True},
                'Glasgow-2': {'summary': 'Unfinished draft; no capture'}}}))
            with patch.object(catalogue, 'PROFILE_UPDATE_QUEUE', path), \
                 patch.object(catalogue, 'PROJECT_ROOT', Path(directory)):
                updates = catalogue._load_profile_updates(evidence, profile_ids={'Glasgow-1'})
                self.assertEqual(set(updates), {'Glasgow-1'})
                for scope in (None, {'Glasgow-2'}):
                    with self.assertRaisesRegex(ValueError, 'no captured WikiTree evidence: Glasgow-2'):
                        catalogue._load_profile_updates(evidence, profile_ids=scope)

    def test_record_proved_brother_can_be_published_without_an_imported_parent(self):
        imported = {'id': 'Glasgow-1', 'relationships': {'parents': [], 'siblings': []}, 'claims': []}
        assertion = {'assertion_id': 'C-record-brothers', 'people': ['Glasgow-1', 'Glasgow-2'],
                     'profile_names': {'Glasgow-2': 'Recorded brother'}, 'status': 'proved',
                     'source_ids': ['original-will'], 'allow_new_relationship': True,
                     'publication_status': 'approved',
                     'perspectives': {'Glasgow-1': {'relationship': 'sibling', 'reason': 'The will calls him brother.'}}}
        resolved = resolve_dossier(imported, [], [assertion])
        sibling = resolved['relationships']['siblings'][0]
        self.assertEqual('proved', sibling['status'])
        self.assertFalse(sibling['tree_relationship'])
        self.assertEqual([], resolved['relationships']['parents'])
        self.assertEqual([], imported['relationships']['siblings'])
        self.assertEqual([], resolved['imported']['sections']['relationships']['siblings'])

    def test_completed_amendment_can_reopen_without_losing_history(self):
        biography = '[[Category:Glasgow Name Study]]\n\n== Biography ==\n\nA recorded life.\n\n== Sources ==\n\n<references />'
        capture = {'biography_wikitext': biography, 'profile_url': 'https://www.wikitree.com/wiki/Glasgow-1'}
        evidence = {'profiles': {'Glasgow-1': capture}}
        biography = catalogue._normalise_complete_wikitree_profile(biography, 'Glasgow-1', capture)
        capture['biography_wikitext'] = biography
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'queue.json'
            queue = {'completed_live_profiles': ['Glasgow-1'],
                     'entries': {'Glasgow-1': {'summary': 'Add the new family record.',
                         'addition_wikitext': 'A newly documented brother.<ref>[https://example.org/record Original register].</ref>'}},
                     'reopened_completed_profiles': {'Glasgow-1': {'reopened_at': '2026-09-30'}}}
            path.write_text(json.dumps(queue))
            with patch.object(catalogue, 'PROFILE_UPDATE_QUEUE', path), patch.object(catalogue, 'PROJECT_ROOT', Path(directory)):
                update = catalogue._load_profile_updates(evidence)['Glasgow-1']
                self.assertIn('newly documented brother', update['proposed_wikitext'])
                self.assertEqual(biography, update['remote_wikitext'])
                # A fresh capture containing the amendment must retire its badge.
                capture['biography_wikitext'] = update['proposed_wikitext']
                queue['entries']['Glasgow-1'] = {'summary': 'The completed amendment.'}
                path.write_text(json.dumps(queue))
                self.assertNotIn('Glasgow-1', catalogue._load_profile_updates(evidence))
                self.assertEqual(['Glasgow-1'], json.loads(path.read_text())['completed_live_profiles'])
