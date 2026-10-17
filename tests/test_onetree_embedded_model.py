import copy
import unittest

from tools.site_sources.onetree.build import embedded_model


class EmbeddedModelTest(unittest.TestCase):
    def test_keeps_genealogy_without_duplicating_approved_annotations(self):
        model = {'people': [{'id': 'Glasgow-1', 'parents': ['Glasgow-2']}],
                 'meta': {'dnaCoverage': 'approved model only'},
                 'landmarks': ['Glasgow-1'], 'dna': {'tester': 'fixture-only'}}
        before = copy.deepcopy(model)
        result = embedded_model(model)
        self.assertNotIn('dna', result)
        self.assertEqual(result, {k: v for k, v in before.items() if k != 'dna'})
        self.assertEqual(model, before)

    def test_model_without_annotations_is_unchanged(self):
        model = {'people': [], 'meta': {}}
        self.assertEqual(embedded_model(model), model)
