"""Hand-off sweep (lane I8): linked evidence labels, one breadcrumb, one word per
concept and reader words on the research queue, in builders other lanes did not own."""
import importlib.util
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from tools import build_latest_findings as findings
from tools import build_research_catalog as catalogue
from tools import build_research_queue as queue
from tools import evidence_labels as ev
from tools import repair_research_questions as questions

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_study_pages_i8', ROOT / 'tools/build_study_pages.py')
studies = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studies)


class StudyPageToneLinkTests(unittest.TestCase):
    def render(self):
        branch = dict(id='fixture', label='Fixture study', members=['example-1', 'example-2'])
        authored = {'id': 'fixture', 'ladder': {'proved': ['A record names him.'], 'hypothesis': ['A guess.']},
                    'clusters': [{'id': 'c1', 'title': 'A household', 'status': 'supported', 'people': ['example-1']}]}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(studies, 'WEB', Path(tmp)):
                return BeautifulSoup(studies.render(branch, {}, [], authored, {}, [], {'territories': [], 'counties': []}),
                                     'html.parser')

    def test_ladder_headings_and_pills_link_their_guide_entries(self):
        soup = self.render()
        headings = [a['href'] for a in soup.select('.sp-ladder h3 a.ev-label-link')]
        self.assertEqual([f'/evidence/#tone-{key}' for key in ev.STUDY_TONES], headings)
        self.assertEqual([value['label'] for value in ev.STUDY_TONES.values()],
                         [h.get_text(strip=True) for h in soup.select('.sp-ladder h3')])
        pill = soup.select_one('.sp-pill a.ev-label-link')
        self.assertEqual('/evidence/#tone-supported', pill['href'])
        self.assertTrue(soup.select_one('a[href="/evidence/#study-scale"]'))

    def test_svg_titles_stay_plain_text(self):
        self.assertNotIn('<title><', inspect.getsource(studies))


class GuideLinkTests(unittest.TestCase):
    def test_latest_findings_key_links_the_guide(self):
        soup = BeautifulSoup(findings.render_main([], total=0), 'html.parser')
        self.assertTrue(soup.select_one('.lf-table-heading .evidence-guide-link a[href="/evidence/"]'))

    def test_question_status_links_the_question_guide(self):
        html = questions.question_actions('glasgow-951')
        soup = BeautifulSoup(html, 'html.parser')
        link = soup.select_one('.question-status a.ev-label-link')
        self.assertEqual('/evidence/#open-questions-guide', link['href'])
        self.assertEqual('Open · probable father, not proved', link.get_text())

    def test_home_about_records_and_sources_link_the_guide(self):
        for path in ('tools/site_sources/reader_guidance/home-start.html', 'tools/site_sources/reader_guidance/about-intro.html',
                     'tools/records_page.py', 'tools/repair_sources_page.py'):
            self.assertIn('href="/evidence/', (ROOT / path).read_text(encoding='utf-8'), path)

    def test_search_scripts_link_labels(self):
        catalogue_js = (ROOT / 'tools/catalogue_search.js').read_text(encoding='utf-8')
        records_js = (ROOT / 'tools/record_search.js').read_text(encoding='utf-8')
        self.assertIn('/evidence/#state-${confidence.key.replaceAll', catalogue_js)
        self.assertIn('class="ev-label-link" href="/evidence/#${anchor}"', records_js)
        entries = ev.as_json()['guide_entries']
        for anchor in ('link-documented', 'link-probable', 'link-profile-lead', 'link-kin-inferred-profile-lead',
                       'link-traditional', 'link-estimated', 'quality-'):
            self.assertIn(anchor, records_js)
            if anchor != 'quality-':
                self.assertIn(anchor, entries)
        self.assertIn('id="record-links"', (ROOT / 'tools/build_evidence_page.py').read_text(encoding='utf-8'))


class CatalogueListPageTests(unittest.TestCase):
    def test_list_pages_have_no_in_page_crumb_or_legacy_catalogue_link(self):
        person = dict(catalogue_id='a-1', name='Ann', birth='', death='', birth_location='', death_location='', recorded_in=[])
        html = catalogue._people_list_page('Scotland One-Tree profile leads', 'Intro.', [person], '/people/clusters/x.html')
        self.assertNotIn('class="crumb"', html)
        self.assertNotIn('/catalogue.html"', html.split('<main', 1)[-1].split('</main>', 1)[0])
        source = inspect.getsource(catalogue.build_research_catalog) + inspect.getsource(catalogue._write_candidate_match_worklist)
        self.assertNotIn('<nav class="crumb"><a href="/catalogue.html">', source)

    def test_counts_use_the_right_word(self):
        self.assertEqual('1 person', catalogue._count_words(1, 'person', 'people'))
        self.assertEqual('1,200 people', catalogue._count_words(1200, 'person', 'people'))

    def test_possible_group_wording(self):
        source = inspect.getsource(catalogue.build_research_catalog)
        self.assertNotIn('research cluster', source.replace('A research cluster', ''))
        self.assertIn('Browse by possible group', source)


class RelatedStudyLineTests(unittest.TestCase):
    def test_line_links_curated_studies_only(self):
        from tools import study_place_links as links
        studies = [dict(id='s1', label='Larne & Kilwaughter', kind='place', url='/branches/s1/', type='Place study',
                        members=['glasgow-1', 'glasgow-2']),
                   dict(id='t1', label='John c. 1475', kind='family', url='/branches/t1/', type='WikiTree tree group',
                        members=['glasgow-1'])]
        index = links.studies_by_person(studies)
        ids = links.wikitree_ids('See [[Glasgow-1|John]], Glasgow-2 and Glasgow-1 again; not glasgow-3x.')
        self.assertEqual(['glasgow-1', 'glasgow-2'], ids)
        html = links.render_related_studies(ids, index)
        self.assertIn('<a href="/branches/s1/">Larne &amp; Kilwaughter</a>', html)
        self.assertIn('(2 people named here)', html)
        self.assertNotIn('/branches/t1/', html)
        self.assertEqual('', links.render_related_studies(['nobody-1'], index))

    def test_builders_print_the_line(self):
        for name in ('build_research_subject_drafts.py', 'free_space_edition.py'):
            self.assertIn('render_related_studies(', (ROOT / 'tools' / name).read_text(encoding='utf-8'), name)


class ResearchQueueWordsTests(unittest.TestCase):
    def test_reader_words_and_workroom_kicker(self):
        row = dict(id='t', name='Ann', kind='Profile identity', status='On hold', profiles=[], sources=[],
                   assessment='Checks remain.', url='/research/queue/t/')
        html = queue.render([row])
        self.assertIn('<td>On hold: needs another record</td>', html)
        self.assertIn('data-status="On hold"', html)  # stored value and filter unchanged
        self.assertNotIn('handoff', html.lower())
        source = inspect.getsource(queue.build) + inspect.getsource(queue.publish_match_audit)
        self.assertIn('WORKROOM_KICKER', source)
        self.assertNotIn('Maintained research handoff', source)
        self.assertEqual('Research workroom: leads, not findings', queue.WORKROOM_KICKER)


if __name__ == '__main__':
    unittest.main()
