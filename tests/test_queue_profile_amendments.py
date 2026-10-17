import unittest
from tools.queue_profile_amendments import merge_amendments
from tools.build_research_catalog import _restore_captured_named_ref_definitions


class ReviewedQueueAmendmentsTests(unittest.TestCase):
    def test_valid_unquoted_citation_definition_satisfies_quoted_reuse(self):
        text = '<ref name=Protocols1903-1904>Original source.</ref> Later.<ref name="Protocols1903-1904" />'
        self.assertEqual(_restore_captured_named_ref_definitions(text, text, 'Glasgow-1'), text)

    def test_full_replacement_supersedes_old_patch_preserving_manual_actions(self):
        specs = {'Glasgow-1': {'replacements': [{'old': 'x', 'new': 'y'}],
                 'addition_wikitext': 'old addition', 'manual_update': True,
                 'relationship_actions': ['uncertain father'], 'draft_path': 'old.md'}}
        reviewed = {'Glasgow-1': {'draft_path': 'complete.md', 'summary': 'New sourced record'}}
        reopened = merge_amendments(specs, reviewed, {'Glasgow-1': {}})
        self.assertEqual(reopened, {'Glasgow-1'})
        self.assertNotIn('replacements', specs['Glasgow-1'])
        self.assertNotIn('addition_wikitext', specs['Glasgow-1'])
        self.assertEqual(specs['Glasgow-1']['relationship_actions'], ['uncertain father'])
        self.assertEqual(specs['Glasgow-1']['draft_path'], 'complete.md')

    def test_missing_capture_is_reported_without_synthetic_current_biography(self):
        specs, report = {}, []
        self.assertEqual(merge_amendments(specs, {'Glasgow-1': {}}, {}, report), set())
        self.assertEqual(specs, {})
        self.assertEqual(report[0]['kind'], 'no_capture')
