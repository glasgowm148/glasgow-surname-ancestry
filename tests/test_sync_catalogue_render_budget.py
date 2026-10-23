import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from tools import sync_catalogue_research as sync
from tools.sync_catalogue_research import discrepancies


class CatalogueRenderBudgetTests(unittest.TestCase):
    def setUp(self):
        self.page = BeautifulSoup(
            '<main class="person-dossier-readable"><section id="family">Old family</section></main>',
            'html.parser',
        )
        self.dossier = {'id': 'Example-1', 'research_findings': []}
        self.row = {}

    def test_findings_change_schedules_refresh_without_preview_render(self):
        findings = [{'profile_id': 'Example-1', 'sections': []}]
        with patch('tools.sync_catalogue_research.render_person_dossier') as render:
            issues = discrepancies(self.dossier, self.page, findings, None, self.row, {})
        self.assertEqual(issues, ['findings data'])
        render.assert_not_called()

    def test_queue_change_schedules_refresh_without_preview_render(self):
        update = {'profile_id': 'Example-1', 'summary': 'New evidence', 'significance': 7,
                  'draft_wikitext': 'Proposed wording', 'pending': True}
        with patch('tools.sync_catalogue_research.render_person_dossier') as render:
            issues = discrepancies(self.dossier, self.page, [], update, self.row, {})
        self.assertIn('update data', issues)
        self.assertIn('update panel', issues)
        render.assert_not_called()

    def test_relationship_only_change_still_renders_for_detection(self):
        changed = '<section id="family">Revised family</section>'
        with patch('tools.sync_catalogue_research.render_person_dossier', return_value=changed) as render:
            issues = discrepancies(self.dossier, self.page, [], None, self.row, {})
        self.assertEqual(issues, ['visible relationships'])
        render.assert_called_once_with('Example-1')

    def test_write_defers_new_layout_html_until_final_hierarchy_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / 'www'
            (web / 'people').mkdir(parents=True)
            (web / 'data').mkdir()
            (root / 'research').mkdir()
            person = web / 'people/example-1.json'
            html = person.with_suffix('.html')
            initial_html = ('<html><head><title>Old</title></head><body data-r-person="Example-1">'
                            '<main class="person-dossier-readable"><section id="family">Old family</section>'
                            '</main></body></html>')
            person.write_text(json.dumps({'id': 'Example-1', 'research_findings': []}))
            html.write_text(initial_html)
            (web / 'data/catalogue-search-index.json').write_text(json.dumps([
                {'id': 'example-1', 'profile_ids': ['Example-1']}
            ]))
            (web / 'data/people-index.json').write_text(json.dumps([
                {'id': 'Example-1', 'slug': 'example-1'}
            ]))
            queue = root / 'queue.json'
            queue.write_text('{}')
            findings = [{'profile_id': 'Example-1', 'sections': []}]
            events = []
            evidence = {}
            updates = {}

            def final_repair(profile_ids):
                events.append('repair')
                self.assertEqual(profile_ids, ['Example-1'])
                self.assertEqual(json.loads(person.read_text())['research_findings'], findings)
                self.assertEqual(html.read_text(), initial_html)
                rendered = render('Example-1')
                html.write_text(initial_html.replace('Old family', rendered))

            with patch.object(sync, 'ROOT', root), patch.object(sync, 'WEB', web), \
                 patch.object(sync.catalogue, 'PROFILE_UPDATE_QUEUE', queue), \
                 patch.object(sync.catalogue, '_load_wikitree_evidence', return_value=evidence), \
                 patch.object(sync.catalogue, '_load_profile_updates', return_value=updates) as load_updates, \
                 patch.object(sync, 'from_sources'), \
                 patch.object(sync, 'completed_comparisons', return_value={}), \
                 patch.object(sync, 'public_findings', return_value=findings), \
                 patch.object(sync, 'refresh_family_branch_parents', return_value=[]), \
                 patch.object(sync, 'refresh_catalogue_summaries'), \
                 patch.object(sync.hierarchy, 'repair', side_effect=final_repair) as repair, \
                 patch.object(sync, 'render_person_dossier', return_value='New family') as render, \
                 patch.dict(sys.modules, {'repair_person_hierarchy': sync.hierarchy}), \
                 patch('tools.catalogue_search_index.refresh'), \
                 patch('tools.genealogy.batch_complete.refresh_after_batch', return_value=0), \
                 patch('tools.check_research_publication.main', return_value=0) as publication, \
                 patch.object(sys, 'argv', ['sync_catalogue_research.py', 'Example-1', '--write']):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(sync._run(), 0)
            repair.assert_called_once_with(['Example-1'])
            report = load_updates.call_args.kwargs['report']
            self.assertIsInstance(report, list)
            self.assertIs(load_updates.call_args.args[0], evidence)
            self.assertIs(publication.call_args.kwargs['wikitree_evidence'], evidence)
            self.assertIs(publication.call_args.kwargs['profile_updates'], updates)
            self.assertIs(publication.call_args.kwargs['profile_update_report'], report)
            render.assert_called_once_with('Example-1')
            self.assertEqual(events, ['repair'])
            self.assertIn('New family', html.read_text())


if __name__ == '__main__':
    unittest.main()
