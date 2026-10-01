import copy
import json
from pathlib import Path
import tempfile
import unittest

from bs4 import BeautifulSoup
from tools import build_latest_findings as findings
from tools.site_analytics import GOOGLE_TAG, with_analytics
from tools import publish_opr_marriage_review


class LatestFindingsTests(unittest.TestCase):
    def fixture(self, directory):
        web = Path(directory) / 'www'
        for filename in ('about/index.html', 'people/glasgow-1.html', 'changes/index.html', 'research/subjects/daniel/index.html'):
            path = web / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(with_analytics('<html><head><title>About</title></head><body><nav class="g-nav"></nav><main><h1>Old heading</h1><p>Preserved history</p></main></body></html>'))
        row = {'id': 'documented-child', 'found_on': '2026-09-30', 'kind': 'relationship',
               'finding': 'The 1673 will names Thomas as a son.', 'status': 'qualified',
               'qualification': 'The son’s identity with the later Lifford man remains unproved.',
               'people': [{'id': 'Glasgow-1', 'name': 'Thomas Glasgow', 'url': '/people/glasgow-1.html'}],
               'sources': [{'title': '1673 will abstract', 'url': 'https://catalogue.nli.ie/example'}],
               'detail_url': '/people/glasgow-1.html', 'provenance': ['private/source-capture.txt']}
        older = {**copy.deepcopy(row), 'id': 'earlier-death-finding', 'found_on': '2026-07-21',
                 'kind': 'vital', 'finding': 'An inspected register gives a death in 1891.'}
        ledger = Path(directory) / 'findings.json'
        ledger.write_text(json.dumps({'schema_version': 1, 'findings': [older, row]}))
        return web, ledger, row

    def test_dates_are_discovery_dates_and_private_provenance_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            web, ledger, _ = self.fixture(directory)
            rows = findings.load_findings(ledger, web)
            self.assertEqual(['2026-09-30', '2026-07-21'], [row['found_on'] for row in rows])
            self.assertTrue(all('provenance' not in row for row in rows))
            findings.repair(web, ledger)
            page = (web / 'latest-findings/index.html').read_text()
            self.assertNotIn('private/source-capture.txt', page)
            self.assertEqual(1, page.count(GOOGLE_TAG))
            self.assertEqual(page, with_analytics(page))
            soup = BeautifulSoup(page, 'html.parser')
            self.assertEqual(2, len(soup.select('tbody tr')))
            self.assertIn('remains unproved', soup.get_text())
            self.assertEqual('../', soup.find('base')['href'])
            self.assertEqual('/latest-findings/', soup.select_one('.g-nav [aria-current]')['href'])
            self.assertEqual({}, dict(findings.repair(web, ledger)))
            self.assertIn('Preserved history', (web / 'changes/index.html').read_text())

    def test_rejects_duplicate_ids_missing_evidence_and_unqualified_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            web, ledger, row = self.fixture(directory)
            for invalid in [copy.deepcopy(row), {**row, 'sources': []},
                            {**row, 'qualification': ''}, {**row, 'found_on': '2026-02-30'},
                            {**row, 'detail_url': '/private/does-not-exist'}]:
                rows = [row, invalid] if invalid == row else [invalid]
                ledger.write_text(json.dumps({'findings': rows}))
                with self.assertRaises(ValueError): findings.load_findings(ledger, web)

    def test_external_wikitree_fallback_is_explicit_and_secure(self):
        with tempfile.TemporaryDirectory() as directory:
            web, ledger, row = self.fixture(directory)
            row['people'][0]['url'] = 'https://www.wikitree.com/wiki/Glasgow-1'
            ledger.write_text(json.dumps({'findings': [row]}))
            html = findings.row_html(findings.load_findings(ledger, web)[0])
            self.assertIn('target="_blank" rel="noopener noreferrer"', html)
            row['people'][0]['url'] = 'https://other.example/Glasgow-1'
            ledger.write_text(json.dumps({'findings': [row]}))
            with self.assertRaises(ValueError): findings.load_findings(ledger, web)

    def test_review_ranges_and_unidentified_record_people_remain_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            web, ledger, row = self.fixture(directory)
            row['found_from'] = '2026-09-29'
            row['people'] = [{'name': 'Daniel Glasco', 'role': 'Unidentified record person; HOLD draft',
                              'url': '/research/subjects/daniel/'}]
            ledger.write_text(json.dumps({'findings': [row]}))
            html = findings.row_html(findings.load_findings(ledger, web)[0])
            self.assertIn('29–30 Sep 2026', html)
            self.assertIn('Unidentified record person', html)
            self.assertIn('href="/research/subjects/daniel/"', html)
            self.assertIn('/latest-findings/#finding-documented-child', html)
            row['found_from'] = '2026-10-01'
            ledger.write_text(json.dumps({'findings': [row]}))
            with self.assertRaises(ValueError): findings.load_findings(ledger, web)

    def test_named_subjects_cannot_silently_lose_profile_or_draft_links(self):
        with tempfile.TemporaryDirectory() as directory:
            web, ledger, row = self.fixture(directory)
            row['people'][0]['draft_url'] = '/research/subjects/daniel/'
            ledger.write_text(json.dumps({'findings': [row]}))
            html = findings.row_html(findings.load_findings(ledger, web)[0])
            self.assertIn('Evidence draft', html)
            self.assertIn('href="/people/glasgow-1.html"', html)
            self.assertIn('href="/research/subjects/daniel/"', html)
            for field, value in [('url', ''), ('draft_url', '/missing-draft/'), ('name', '')]:
                invalid = copy.deepcopy(row)
                invalid['people'][0][field] = value
                ledger.write_text(json.dumps({'findings': [invalid]}))
                with self.assertRaises(ValueError): findings.load_findings(ledger, web)

    def test_record_review_shows_candidates_without_promoting_them_to_matches(self):
        data = json.loads((findings.ROOT / 'surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json').read_text())
        row = copy.deepcopy(data['rows'][0])
        row.update(profile_ids=[], candidate_profile_ids=['Example-12345'], status='HOLD',
                   assessment='A compatible candidate remains under review.',
                   identity_review_url='/research/subjects/example/#person',
                   assessment_history=[{'assessment': 'Former incompatible-profile dismissal'}])
        data['rows'] = [row]
        html = publish_opr_marriage_review.render(data)
        soup = BeautifulSoup(html, 'html.parser')
        rendered = soup.select_one('tbody tr')
        self.assertIn('Possible: Example-12345', rendered.get_text())
        self.assertIn('HOLD', rendered.get_text())
        self.assertIsNotNone(rendered.select_one('a[href="/research/subjects/example/#person"]'))
        self.assertNotIn('Former incompatible-profile dismissal', rendered.get_text())

    def test_current_ledger_has_visible_evidence_and_newest_first_order(self):
        rows = findings.load_findings()
        page = BeautifulSoup((findings.WEB / 'latest-findings/index.html').read_text(), 'html.parser')
        rendered = page.select('#lf-rows > tr')
        self.assertEqual(len(rows), len(rendered))
        self.assertEqual([row['found_on'] for row in rows], [row['data-date'] for row in rendered])
        for row in rendered:
            self.assertTrue(row.select('.lf-sources a'))
            self.assertTrue(row.select_one('.lf-fact').get_text(strip=True))
        self.assertTrue(page.select_one('a[href="/changes/"]'))

    def test_relationship_upgrades_are_scoped_and_keep_previous_evidence_private(self):
        with tempfile.TemporaryDirectory() as directory:
            web, ledger, row = self.fixture(directory)
            row['relationship_changes'] = [{'relationship': 'father', 'subject': 'Thomas Glasgow',
                'relative': 'Archibald Glasgow', 'before': 'unknown', 'after': 'certain',
                'explanation': 'A second original identifies the same family.',
                'previous_status_provenance': ['private/prior-assessment.txt']}]
            ledger.write_text(json.dumps({'findings': [row]}))
            rows = findings.load_findings(ledger, web)
            self.assertNotIn('previous_status_provenance', rows[0]['relationship_changes'][0])
            findings.repair(web, ledger)
            page = (web / 'latest-findings/index.html').read_text()
            soup = BeautifulSoup(page, 'html.parser')
            self.assertEqual('father', soup.select_one('#lf-rows tr')['data-relationship-upgrade'])
            self.assertEqual('30 Sep 2026', soup.select_one('#lf-rows tr time').get_text())
            self.assertEqual('qualified', soup.select_one('#lf-rows tr')['data-status'])
            self.assertIn('Unknown → Certain', soup.get_text())
            self.assertNotIn('private/prior-assessment.txt', page)
            self.assertIsNotNone(soup.select_one('#lf-status option[value="relationship-certain"]'))
            self.assertIsNotNone(soup.select_one('#lf-status option[value="father-certain"]'))
            for replacement in [{'before': 'certain'}, {'after': 'uncertain'},
                                {'previous_status_provenance': []}, {'relationship': 'identity'}]:
                invalid = copy.deepcopy(row)
                invalid['relationship_changes'][0].update(replacement)
                ledger.write_text(json.dumps({'findings': [invalid]}))
                with self.assertRaises(ValueError): findings.load_findings(ledger, web)


if __name__ == '__main__':
    unittest.main()
