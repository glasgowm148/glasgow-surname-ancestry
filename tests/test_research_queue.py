import unittest
import json
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from tools.build_research_queue import collect, render, apply_match_reviews, profile_href, consolidate_record_reviews

ROOT = Path(__file__).resolve().parents[1]


class ResearchQueueTests(unittest.TestCase):
    def test_consolidation_retains_people_and_separates_distinct_events(self):
        def row(ident, person, keys, profile):
            return dict(id=ident, name=person, kind='Profile identity', status='On hold',
                        assessment='Identity remains qualified.', url='/research/' + ident + '/',
                        profiles=[profile], sources=[], canonical_groups=keys)
        rows = [row('bride', 'Jane', ['marriage-1'], 'Glasgow-1'),
                row('groom', 'John', ['marriage-1'], 'Smith-1'),
                row('other-marriage', 'Jane', ['marriage-2'], 'Glasgow-2'),
                row('comparison', 'Jane', ['marriage-1', 'marriage-2'], 'Glasgow-3')]
        grouped = consolidate_record_reviews(rows)
        self.assertEqual(3, len(grouped))
        group = next(r for r in grouped if r.get('members'))
        self.assertEqual(['bride', 'groom'], [m['id'] for m in group['members']])
        soup = BeautifulSoup(render(grouped), 'html.parser')
        self.assertIn('/research/groom/', [a['href'] for a in soup.select('a[href]')])
        self.assertTrue(any(r['id'] == 'comparison' for r in grouped))

    def test_baseline_reviews_are_complete_and_shared_names_are_scoped(self):
        baseline = json.loads((ROOT / 'research/queue-match-audit-2026-09-30/baseline.json').read_text())['rows']
        registry = json.loads((ROOT / 'research/research-queue-matches.json').read_text())['reviews']
        self.assertEqual(140, len(baseline))
        self.assertTrue({row['id'] for row in baseline} <= set(registry))
        self.assertEqual('partly_matched', registry['subject-rasharkin-john-elder-marriages-john-elder']['status'])
        subjects = json.loads((ROOT / 'research/latest-findings-subjects/subjects.json').read_text())
        john = next(p for g in subjects['groups'] if g['slug'] == 'rasharkin-john-elder-marriages' for p in g['people'] if p['anchor'] == 'john-elder')
        records = {r['finding_id']: r for r in john['record_matches']}
        self.assertEqual(['Elder-5907'], records['new-17sep-8b874ec0e8e2']['profile_ids'])
        self.assertEqual('matched', records['new-17sep-8b874ec0e8e2']['status'])
        self.assertNotIn('Elder-5907', records['new-17sep-5c3f1cfb8d0b']['profile_ids'])
        self.assertEqual('compatible_candidate', records['new-17sep-0652ac06be27']['status'])

    def test_review_replaces_rejected_leads_without_completing_amendments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'research').mkdir()
            reviews = {'identity': dict(status='matched', profile_ids=['Glasgow-1152'], assessment='Same dated marriage.'),
                       'amendment': dict(status='already_linked', profile_ids=['Glasgow-4010'], assessment='Still pending.')}
            (root / 'research/research-queue-matches.json').write_text(json.dumps(dict(reviewed_on='2026-09-30', reviews=reviews)))
            rows = [dict(id='identity', kind='Profile identity', status='On hold', profiles=['Glasgow-3118']),
                    dict(id='amendment', kind='WikiTree amendment', status='Pending update', profiles=['Glasgow-4010'])]
            apply_match_reviews(rows, root)
            self.assertEqual(['Glasgow-1152'], rows[0]['profiles'])
            self.assertEqual('Matched profile', rows[0]['status'])
            self.assertEqual('Pending update', rows[1]['status'])
            self.assertEqual('2026-09-30', rows[0]['match_review']['reviewed_on'])
            self.assertEqual('https://www.wikitree.com/wiki/Glasgow-1152', profile_href('Glasgow-1152', root))

    def test_registers_are_joined_and_completed_updates_excluded(self):
        rows, drafts = collect()
        self.assertGreater(len(rows), 100)
        self.assertEqual(len(rows), len({(r['url'], r['name']) for r in rows}))
        self.assertTrue(any(r['id'] == 'opr-47' and r['status'] == 'On hold' for r in rows))
        self.assertTrue(any(r['id'] == 'update-glasgow-4010' and r['status'] == 'Pending update' for r in rows))
        self.assertTrue(any('1648-scotland-edinburgh-john' in r['id'] for r in rows))
        self.assertTrue(any(r['status'] == 'Draft review' for r in rows))
        for row in rows:
            if row['kind'] == 'WikiTree amendment':
                self.assertTrue(row['url'].startswith('/people/'))
        self.assertTrue(all(d['wikitext'] for d in drafts))

    def test_render_preserves_assessments_and_escapes_markup(self):
        row = dict(id='test', name='A < B', kind='Profile identity', status='On hold',
                   assessment='<script>alert(1)</script>', url='/research/subjects/test/', profiles=[], sources=[])
        soup = BeautifulSoup(render([row]), 'html.parser')
        self.assertIsNone(soup.select_one('script'))
        self.assertEqual('A < B', soup.select_one('tbody a').text)
        self.assertIn('<script>alert(1)</script>', soup.select_one('tbody').text)
        self.assertIsNone(soup.select_one('details').get('open'))
