"""Rules that decide which findings.md sections reach a person page.

A section must never disappear because its heading was worded in a way the
builder did not expect. Only editing logs are kept back, and only on purpose.
"""
import unittest

from tools.build_research_catalog import _findings_section_body, findings_section_category
from tools.dossier_resolution import resolve_presentation


def _dossier(*titles):
    sections = [{'title': title, 'category': 'conclusion', 'markdown': f'Text of {title}.'} for title in titles]
    return {'research_findings': [{'updated': '2026-10-07', 'source_path': 'research/X-1/findings.md', 'sections': sections}]}


class FindingsHeadingRules(unittest.TestCase):
    def test_established_headings_keep_their_category(self):
        cases = {
            'Current conclusion': 'conclusion',
            'Current conclusion — newspaper identity review, 6 October 2026': 'conclusion',
            'Source findings': 'sources',
            'Prior relationship assessment — superseded by the 1905 case': 'assessment',
            'Candidate fathers': 'assessment',
            'Unresolved questions': 'actions',
            'Suggested corrections': 'actions',
        }
        for title, expected in cases.items():
            self.assertEqual(expected, findings_section_category(title), title)

    def test_topic_source_sections_are_published(self):
        for title in ('Source findings — Larne session minutes, 7 October 2026',
                      'Source findings - repository integration audit',
                      'Sources',
                      'Negative searches',
                      'Evidence for the 1731 lease',
                      'Parish register reread, 6 October 2026'):
            self.assertEqual('sources', findings_section_category(title), title)

    def test_next_question_sections_are_published(self):
        for title in ('Next questions', 'Proof targets', 'Open questions', 'Remaining work', 'Do not infer'):
            self.assertEqual('actions', findings_section_category(title), title)

    def test_editing_logs_are_internal(self):
        for title in ('WikiTree update instructions', 'Live profile update — 19 August 2026',
                      'Complete WikiTree handoff', 'Public profile scrape review (2026-08-01)',
                      'Error 966 link migration — 2 September 2026', 'Paste-ready biography addition',
                      'Website synchronization', 'Prior assessment — superseded by merge'):
            self.assertEqual('internal', findings_section_category(title), title)

    def test_source_findings_about_the_live_profile_are_still_sources(self):
        self.assertEqual('sources', findings_section_category(
            'Source findings — Glencorse children cited on the live profile, 6 October 2026'))

    def test_an_unexpected_heading_is_published_as_notes_not_dropped(self):
        for title in ('Tree effect', 'Newtown title succession — 2026', 'Documented household',
                      'A heading nobody has used before'):
            self.assertEqual('notes', findings_section_category(title), title)


class FindingsTemplateRows(unittest.TestCase):
    TEMPLATE = '| _Add a URL, archive reference, or precise citation_ | No sourced conclusion recorded yet. | Unreviewed |'

    def test_template_only_section_is_empty(self):
        body = '| Source | Finding | Assessment |\n| --- | --- | --- |\n' + self.TEMPLATE
        self.assertEqual('', _findings_section_body(body))

    def test_real_rows_beside_the_template_row_are_kept(self):
        body = ('| Source | Finding | Assessment |\n| --- | --- | --- |\n' + self.TEMPLATE
                + '\n| [Deed, 1786](https://example.org/deed) | John Glasgow of Tullyhogue grants a lease. | Direct |')
        kept = _findings_section_body(body)
        self.assertIn('John Glasgow of Tullyhogue', kept)
        self.assertIn('| Source | Finding | Assessment |', kept)
        self.assertNotIn('No sourced conclusion recorded yet', kept)

    def test_text_after_an_emptied_table_is_kept_without_the_empty_header(self):
        body = ('| Source | Finding | Assessment |\n| --- | --- | --- |\n' + self.TEMPLATE
                + '\n\n### Later review\n\nThe 1841 census places the household at Lisnagaver.')
        kept = _findings_section_body(body)
        self.assertIn('The 1841 census places the household at Lisnagaver.', kept)
        self.assertNotIn('| Source | Finding | Assessment |', kept)

    def test_section_without_template_text_is_unchanged(self):
        body = 'A paragraph.\n\n| A | B |\n| --- | --- |\n| 1 | 2 |'
        self.assertEqual(body, _findings_section_body(body))


class ConclusionResolution(unittest.TestCase):
    def test_single_conclusion_resolves(self):
        result = resolve_presentation('X-1', _dossier('Current conclusion'), {})
        self.assertEqual('resolved', result['resolution']['state'])
        self.assertEqual('Text of Current conclusion.', result['position']['answer'])

    def test_dated_topic_review_adds_to_the_overall_conclusion(self):
        dossier = _dossier('Current conclusion — newspaper identity review, 6 October 2026', 'Current conclusion')
        result = resolve_presentation('X-1', dossier, {})
        self.assertEqual('resolved', result['resolution']['state'])
        self.assertEqual('Text of Current conclusion.', result['position']['answer'])
        self.assertEqual(['Current conclusion — newspaper identity review, 6 October 2026'],
                         result['resolution']['additions'])
        self.assertNotIn('conflict', result['position']['answer'].casefold())

    def test_one_dated_review_alone_resolves(self):
        result = resolve_presentation('X-1', _dossier('Current conclusion — will review, 2 October 2026'), {})
        self.assertEqual('resolved', result['resolution']['state'])

    def test_two_overall_conclusions_are_a_real_conflict(self):
        result = resolve_presentation('X-1', _dossier('Current conclusion', 'Conclusion'), {})
        self.assertEqual('conflict', result['resolution']['state'])

    def test_several_dated_reviews_without_an_overall_conclusion_are_not_a_conflict(self):
        dossier = _dossier('Current conclusion — will review, 2 October 2026',
                           'Current conclusion — census review, 6 October 2026')
        result = resolve_presentation('X-1', dossier, {})
        self.assertEqual('unmapped', result['resolution']['state'])
        self.assertNotIn('conflict', result['position']['answer'].casefold())


if __name__ == '__main__':
    unittest.main()
