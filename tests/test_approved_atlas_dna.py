"""Immutable publication approval survives genealogy-only privacy projection."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import approved_restorations as restorations
from tools import public_ydna_research as research
from tools.public_privacy import PublicPrivacy, tester_identifier_pattern


class ApprovedAtlasDnaTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.private = self.root / 'data/private/withheld-public-assets'
        self.private.mkdir(parents=True)
        self.web = self.root / 'www'
        self.manifest = self.root / 'approval.json'
        for name, value in [('ROOT', self.root), ('PRIVATE', self.private), ('MANIFEST', self.manifest)]:
            replacement = patch.object(restorations, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.policy = PublicPrivacy({'Living-1': {'birth_date': '2000-01-01'}})
        self.policy.tester_ids = frozenset({'KIT-EXAMPLE'})
        self.policy.tester_pattern = tester_identifier_pattern(self.policy.tester_ids)

    def approve(self, relative, dna):
        source = 'data/private/original.json'
        content = json.dumps({'dna': dna}).encode()
        (self.root / source).write_bytes(content)
        self.manifest.write_text(json.dumps({
            'schema_version': 1, 'scope': 'previous-public-research-restoration',
            'publications': [{'path': relative, 'kind': 'atlas-model', 'source': source,
                              'sha256': hashlib.sha256(content).hexdigest()}],
        }))

    def test_exact_approved_dna_restored_without_changing_filtered_genealogy(self):
        for relative in research.APPROVED_ATLAS_MODELS:
            with self.subTest(relative=relative):
                dna = [{'id': 'Historical-1', 'kits': ['KIT-EXAMPLE'], 'summary': 'KIT-EXAMPLE comparison.'}]
                self.approve(relative, dna)
                path = self.web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                current = {'dna': [], 'people': [{'id': 'Historical-1'}], 'meta': {'people': 1},
                           'landmarks': ['Historical-1']}
                path.write_text(json.dumps(current))
                self.assertEqual(1, research.restore_approved_atlas_dna(self.web, self.policy, self.private))
                self.assertEqual({**current, 'dna': dna}, json.loads(path.read_text()))
                self.assertEqual(0, research.restore_approved_atlas_dna(self.web, self.policy, self.private))

    def test_approval_does_not_extend_to_other_paths_or_private_roots(self):
        relative = 'unapproved/model.json'
        self.approve(relative, [{'kits': ['KIT-EXAMPLE']}])
        self.assertIsNone(research.approved_atlas_dna(relative, self.policy, self.private))
        self.assertIsNone(research.approved_atlas_dna(research.APPROVED_ATLAS_MODELS[0], self.policy,
                                                     self.root / 'another-private-root'))

    def test_newly_living_person_in_approved_original_is_withheld(self):
        relative = research.APPROVED_ATLAS_MODELS[0]
        self.approve(relative, [{'id': 'Historical-1', 'kits': ['KIT-EXAMPLE'],
                                'summary': 'Comparison with Living-1.'}])
        path = self.web / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"dna":[],"people":[]}')
        self.assertIsNone(research.approved_atlas_dna(relative, self.policy, self.private))
        self.assertEqual(0, research.restore_approved_atlas_dna(self.web, self.policy, self.private))
        self.assertEqual({'dna': [], 'people': []}, json.loads(path.read_text()))

    def test_source_hash_change_cannot_be_blessed(self):
        relative = research.APPROVED_ATLAS_MODELS[0]
        self.approve(relative, [{'kits': ['KIT-EXAMPLE']}])
        (self.root / 'data/private/original.json').write_text('{"dna":[{"kits":["NEW-KIT"]}]}')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            research.approved_atlas_dna(relative, self.policy, self.private)

    def test_scoped_projection_keeps_approved_tester_strings_but_filters_living(self):
        value = {'kits': ['KIT-EXAMPLE'], 'summary': 'KIT-EXAMPLE comparison.',
                 'relatives': [{'id': 'Living-1', 'name': 'Private person'}]}
        self.assertNotIn('kits', self.policy.project(value))
        self.policy.allow_approved_dna = True
        projected = self.policy.project(value)
        self.assertEqual(['KIT-EXAMPLE'], projected['kits'])
        self.assertEqual('KIT-EXAMPLE comparison.', projected['summary'])
        self.assertEqual([], projected['relatives'])
        self.assertTrue(self.policy.contains_private_id('Living-1'))
        self.assertFalse(self.policy.contains_private_id('KIT-EXAMPLE'))
