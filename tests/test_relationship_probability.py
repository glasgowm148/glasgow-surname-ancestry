import unittest

from tools.relationship_probability import BANDS, probability_for_relationship, confidence_band


class RelationshipProbabilityTests(unittest.TestCase):
    def test_bands_and_aliases(self):
        self.assertEqual((BANDS["confident"]["minimum"], BANDS["confident"]["maximum"], BANDS["confident"]["rank"]), (.9, .99, 4))
        self.assertEqual(confidence_band("proved"), "confident")
        self.assertEqual(confidence_band("strongly_supported"), "confident")
        self.assertEqual(confidence_band("dna-confirmed"), "confident")
        self.assertEqual(confidence_band("speculative"), "uncertain")
        self.assertEqual(confidence_band("guess"), "uncertain")

    def test_unknown_falls_back_to_tree_status(self):
        result = probability_for_relationship({"status": "unknown", "data_status": "20"})
        self.assertEqual((result["band"], result["origin"]), ("confident", "wikitree"))

    def test_reviewed_uncertain_beats_confident_tree(self):
        result = probability_for_relationship({"status": "uncertain", "tree_status": "confident"})
        self.assertEqual((result["band"], result["origin"]), ("uncertain", "research"))

    def test_assessed_certainty_beats_unknown_status(self):
        result = probability_for_relationship({"status": "unknown", "certainty": "probable", "tree_status": "confident"})
        self.assertEqual((result["band"], result["origin"]), ("probable", "research"))

    def test_withheld_and_conflict_do_not_fallback(self):
        self.assertEqual(probability_for_relationship({"status": "confident", "withheld": True})["band"], "unrated")
        self.assertEqual(probability_for_relationship({"status": "conflict", "data_status": "20"})["band"], "unrated")

    def test_raw_tree_confident_is_wikitree_origin(self):
        result = probability_for_relationship({"tree_status": "dna_confirmed"})
        self.assertEqual((result["band"], result["origin"]), ("confident", "wikitree"))

    def test_unrated_states_and_scope(self):
        for status in ("unknown", "unmarked", "conflict", "rejected", "nonbiological", "withheld"):
            result = probability_for_relationship({"status": status, "recordScope": "documentary"})
            self.assertEqual((result["band"], result["minimum"], result["rank"]), ("unrated", None, 0))
            self.assertEqual(result["scope"], "documentary")

    def test_no_point_probability(self):
        result = probability_for_relationship({"status": "probable"})
        self.assertEqual((result["minimum"], result["maximum"]), (.6, .89))
        self.assertNotIn("probability", result)



class ModelProbabilityTests(unittest.TestCase):
    def test_legacy_dual_parent_role_keeps_father_rating_separate(self):
        from tools.relationship_probability import annotate_model
        model={'people':[{'id':'C','parents':[{'id':'P','role':'father','status':'unmarked'},{'id':'P','role':'mother','status':'confident'}]}, {'id':'P','childrenRecorded':[{'id':'C'}]}]}
        annotate_model(model)
        child=model['people'][1]['childrenRecorded'][0]
        self.assertEqual(child['probability']['band'],'unrated')
        self.assertEqual(child['probability_by_role']['father']['band'],'unrated')
        self.assertEqual(child['probability_by_role']['mother']['band'],'confident')
        self.assertEqual(model['people'][0]['parents'][0]['status'],'unmarked')

    def test_projection_is_idempotent_and_reciprocal(self):
        from copy import deepcopy
        from tools.relationship_probability import annotate_model
        model = {'people':[{'id':'C','parents':[{'id':'F','role':'father','status':'proved','recordScope':'Recorded child; adult identity possible'}]}, {'id':'F','childrenRecorded':[{'id':'C','role':'child','status':'proved'}]}]}
        annotate_model(model)
        father = model['people'][0]['parents'][0]
        child = model['people'][1]['childrenRecorded'][0]
        self.assertEqual(father['probability'], child['probability'])
        self.assertEqual(father['probability']['scope'], 'Recorded child; adult identity possible')
        self.assertIn('90–99%', father['statusLabel'])
        self.assertEqual(annotate_model(deepcopy(model)), model)

if __name__ == "__main__":
    unittest.main()
