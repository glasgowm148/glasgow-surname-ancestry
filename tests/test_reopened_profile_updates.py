import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_research_catalog as catalogue
from tools.publish_resolved_dossiers import resolve as resolve_dossier


class ReopenedProfileUpdatesTest(unittest.TestCase):
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
            with patch.object(catalogue, 'PROFILE_UPDATE_QUEUE', path):
                update = catalogue._load_profile_updates(evidence)['Glasgow-1']
                self.assertIn('newly documented brother', update['proposed_wikitext'])
                self.assertEqual(biography, update['remote_wikitext'])
                # A fresh capture containing the amendment must retire its badge.
                capture['biography_wikitext'] = update['proposed_wikitext']
                queue['entries']['Glasgow-1'] = {'summary': 'The completed amendment.'}
                path.write_text(json.dumps(queue))
                self.assertNotIn('Glasgow-1', catalogue._load_profile_updates(evidence))
                self.assertEqual(['Glasgow-1'], json.loads(path.read_text())['completed_live_profiles'])
