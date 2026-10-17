import unittest
import json
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from tools.build_research_queue import collect, render, apply_match_reviews, profile_href, consolidate_record_reviews, apply_batch_progress, new_profile_suggestions, render_new_profiles

ROOT = Path(__file__).resolve().parents[1]


class ResearchQueueTests(unittest.TestCase):
    def test_progress_counts_frozen_items_without_finishing_amendments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = root / 'research/batch'
            batch.mkdir(parents=True)
            (root / 'research/research-queue-matches.json').write_text(json.dumps(
                dict(current_batch='research/batch/baseline.json')))
            baseline = [dict(id='group', members=[dict(id='record'), dict(id='draft')]),
                        dict(id='amendment'), dict(id='unreviewed')]
            (batch / 'baseline.json').write_text(json.dumps(dict(rows=baseline)))
            (batch / 'progress.json').write_text(json.dumps(dict(reviewed_on='2026-10-17', baseline_results={
                'group': dict(disposition='existing_profile'),
                'amendment': dict(disposition='existing_profile')})))
            rows = [dict(id='regrouped', kind='Profile identity', status='On hold',
                         members=[dict(id='record'), dict(id='draft')],
                         match_review=dict(status='compatible_candidate')),
                    dict(id='amendment', kind='WikiTree amendment', status='Pending update'),
                    dict(id='unreviewed', kind='Profile identity', status='On hold')]
            progress = apply_batch_progress(rows, root)
            self.assertEqual((2, 1, 66.7), (progress['reviewed_items'], progress['remaining_items'], progress['percent_complete']))
            self.assertEqual('Compatible profile linked', rows[0]['status'])
            self.assertEqual('On hold', rows[0]['research_status'])
            self.assertTrue(rows[1]['identity_review']['complete'])
            self.assertEqual('Pending update', rows[1]['status'])
            self.assertFalse(rows[2]['identity_review']['complete'])
            # A stray result must never lower the remaining baseline count.
            (batch / 'progress.json').write_text(json.dumps(dict(reviewed_on='2026-10-17', baseline_results={
                'outside-baseline': dict(disposition='existing_profile')})))
            with self.assertRaises(ValueError):
                apply_batch_progress(rows, root)

    def test_render_exposes_review_progress_and_filter(self):
        row = dict(id='test', name='Jane', kind='Profile identity', status='On hold',
                   assessment='Compatible profile remains tentative.', url='/research/test/', profiles=[], sources=[],
                   identity_review=dict(complete=True))
        soup = BeautifulSoup(render([row], dict(reviewed_items=1, baseline_items=2,
                                             percent_complete=50.0, remaining_items=1)), 'html.parser')
        self.assertIn('1 records need identity review', soup.select_one('#rq-progress').text)
        self.assertEqual('complete', soup.select_one('tbody tr')['data-reviewed'])
        self.assertEqual(['', 'pending', 'complete'], [o['value'] for o in soup.select('#rq-review option')])

    def test_new_suggestions_require_real_sourced_drafts_and_exclude_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'research/latest-findings-subjects').mkdir(parents=True)
            review = dict(status='no_compatible_profile', profile_ids=[], assessment='Named child; checked candidates conflict.')
            registry = dict(reviewed_on='2026-10-17', reviews={'subject-family-jane': review})
            person = dict(anchor='jane', name='Jane', minimum_fields='Father named; birth unknown.', facts=[],
                          duplicate_check=['Actual dated search scope.'],
                          wikitext='== Biography ==\nJane is named.<ref>Record citation</ref>\n== Sources ==\n<references />')
            path = root / 'research/latest-findings-subjects/subjects.json'
            path.write_text(json.dumps(dict(groups=[dict(slug='family', people=[person])])))
            registry_path = root / 'research/research-queue-matches.json'
            registry_path.write_text(json.dumps(registry))
            suggestions = new_profile_suggestions(root)
            self.assertEqual(1, len(suggestions))
            soup = BeautifulSoup(render_new_profiles(suggestions), 'html.parser')
            self.assertEqual('/research/subjects/family/#jane', soup.select_one('li a')['href'])
            self.assertIn('Needs updated on WikiTree', soup.select_one('h2').text)
            person['wikitext'] = 'Empty placeholder'
            path.write_text(json.dumps(dict(groups=[dict(slug='family', people=[person])])))
            with self.assertRaises(ValueError):
                new_profile_suggestions(root)
            review.update(status='compatible_candidate', profile_ids=['Example-1'])
            registry_path.write_text(json.dumps(registry))
            self.assertEqual([], new_profile_suggestions(root))

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
        subjects = json.loads((ROOT / 'research/latest-findings-subjects/subjects.json').read_text())
        owned = {path for group in subjects['groups'] for person in group['people'] for path in person.get('draft_sources', [])}
        row_ids = {row['id'] for row in rows}
        for source in owned:
            if source.startswith('surname-research/new-people/'):
                self.assertNotIn('draft-' + Path(source).stem.lower().replace('_', '-'), row_ids)

    def test_render_preserves_assessments_and_escapes_markup(self):
        row = dict(id='test', name='A < B', kind='Profile identity', status='On hold',
                   assessment='<script>alert(1)</script>', url='/research/subjects/test/', profiles=[], sources=[])
        soup = BeautifulSoup(render([row]), 'html.parser')
        self.assertIsNone(soup.select_one('script'))
        self.assertEqual('A < B', soup.select_one('tbody a').text)
        self.assertIn('<script>alert(1)</script>', soup.select_one('tbody').text)
        self.assertIsNone(soup.select_one('details').get('open'))
