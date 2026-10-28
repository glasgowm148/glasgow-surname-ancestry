"""Reader presentation keeps historical qualifications and complete evidence."""
import copy
from tests._generated_data import requires_generated_data
import json
from pathlib import Path
import unittest

from bs4 import BeautifulSoup
from tools import build_latest_findings as findings
from tools import free_space_edition as edition
from tools import repair_person_hierarchy as people
from tools import repair_research_questions as questions


class ReaderAuditRepairsTests(unittest.TestCase):
    @requires_generated_data
    def test_reviewed_index_is_visible_without_upgrading_tree_relationships(self):
        page = BeautifulSoup(people.render_person_dossier('Glasgow-3080'), 'html.parser')
        overview = page.select_one('#overview').get_text(' ', strip=True)
        self.assertIn('original image has not been inspected', overview)
        self.assertNotIn('publication-safe', overview)
        source = page.select_one('#sources')
        self.assertIn('692 / 2, reference 20 / 330', source.get_text(' ', strip=True))
        self.assertIn('not a new event or relationship', source.get_text(' ', strip=True))
        self.assertIsNotNone(source.select_one('a[href="/branches/scottish-families/#opr-births-to-1700"]'))
        # The index row does not upgrade the father; his separate 22 October 2026 rating does.
        self.assertIn('Documented father', page.get_text())
        self.assertIn('Supplied OPR births and baptisms: row 16', page.select_one('#archive-tools').get_text())

    @requires_generated_data
    def test_finding_and_candidate_assessments_are_distinct_and_grades_unchanged(self):
        item = next(row for row in findings.load_findings() if row['status'] == 'confirmed'
                    and any('identity qualified' in person.get('role', '') for person in row['people']))
        original = copy.deepcopy(item)
        page = BeautifulSoup(findings.row_html(item), 'html.parser')
        self.assertEqual('confirmed', page.tr['data-status'])
        self.assertEqual('Finding supported', page.select_one('td[data-label="Finding assessment"] > .lf-status').get_text())
        self.assertIn('Profile identification:', page.select_one('.lf-people').get_text())
        self.assertIn('identity qualified', page.select_one('.lf-people').get_text())
        self.assertEqual(item, original)
        self.assertIn('does not confirm its identification', findings.render_main([item]))

    def test_sentence_previews_do_not_cut_words_or_hide_that_text_continues(self):
        text = 'The documented household is identified. ' + 'Further qualified evidence needs checking. ' * 12
        self.assertEqual('The documented household is identified.…', edition.sentence_excerpt(text, 70))
        words = ' '.join(['qualification'] * 40)
        preview = edition.sentence_excerpt(words, 45)
        self.assertEqual('qualification qualification qualification…', preview)
        self.assertEqual('Short complete account.', edition.sentence_excerpt('Short complete account.'))

    def test_principal_collection_introductions_explain_the_usable_studies(self):
        pages = list(json.loads(edition.EDITION.read_text())['pages'].values())
        directory = BeautifulSoup(edition.directory_main(pages, []), 'html.parser')
        for slug, text in edition.COLLECTION_PREVIEWS.items():
            self.assertEqual(text, directory.select_one(f'#collection-{slug} .fsp-lead-study p').get_text())
        self.assertIn('structured Glasgow burgh protocol index', directory.select_one('#collection-scotland').get_text())
        self.assertNotIn('candidates an', directory.get_text())

    def test_study_metadata_replaces_inherited_description_and_canonical(self):
        shell = '<html><head><title>Research</title><meta name="description" content="Old"><link rel="canonical" href="https://example.org/research/"></head><body><main>Old</main></body></html>'
        page = BeautifulSoup(edition.shell_page(shell, '<main>Full evidence remains</main>', 'Study A', '/free-space/study-a/index.html', 'Study A: a qualified household account.'), 'html.parser')
        self.assertEqual(1, len(page.select('meta[name="description"]')))
        self.assertEqual('Study A: a qualified household account.', page.select_one('meta[name="description"]')['content'])
        self.assertEqual(1, len(page.select('link[rel="canonical"]')))
        self.assertEqual('https://glasgow.phenotype.dev/free-space/study-a/', page.select_one('link[rel="canonical"]')['href'])
        self.assertIn('Full evidence remains', page.get_text())

    def test_questions_lead_with_missing_connection_and_keep_targets_in_details(self):
        keys = [q[0] for q in questions.QUESTIONS] + [q[1] for q in questions.ADDITIONAL_QUESTIONS]
        for key in keys:
            page = BeautifulSoup(questions.question_actions(key, '<p>Full prior evidence.</p>'), 'html.parser')
            self.assertTrue(page.select_one('.repair-question-missing').get_text(strip=True))
            detail = page.select_one('details')
            self.assertFalse(detail.has_attr('open'))
            self.assertIn('Full prior evidence.', detail.get_text())
            for target in questions.QUESTION_ACTIONS[key][1:]:
                if target:
                    self.assertIn(target, detail.get_text())
            self.assertTrue(page.select_one('.repair-question-status').get_text(strip=True))


if __name__ == '__main__':
    unittest.main()
