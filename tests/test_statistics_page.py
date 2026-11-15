from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from tools import build_statistics_page as statistics


def _source(summary='7'):
    return (
        '<section class="catalogue-statistics" id="statistics">'
        '<div class="statistics-summary"><div><strong>' + summary + '</strong><span>Historical people</span></div></div>'
        '<details id="statistics-detail"><summary>Details</summary>'
        '<div class="statistics-grid"><section class="statistics-panel">panel</section></div>'
        '<p class="statistics-caution">careful</p></details></section>'
    )


def _read_markup(catalogue, artifact=None):
    with TemporaryDirectory() as temporary:
        web = Path(temporary)
        (web / 'catalogue').mkdir()
        (web / 'catalogue/index.html').write_text(catalogue, encoding='utf-8')
        artifact_path = web / 'data/catalogue-statistics.json'
        if artifact is not None:
            artifact_path.parent.mkdir()
            artifact_path.write_text(json.dumps({'html': artifact}), encoding='utf-8')
        with patch.object(statistics, 'WEB', web), patch.object(statistics, 'STATISTICS_ARTIFACT', artifact_path):
            return statistics._statistics_markup()


class StatisticsPageTests(unittest.TestCase):
    def test_statistics_markup_reads_new_artifact_first(self):
        self.assertEqual(_read_markup('old catalogue', artifact=_source('99')), _source('99'))


    def test_statistics_markup_preserves_plain_legacy_detail(self):
        self.assertTrue(_read_markup(_source()).endswith('</details></section>'))


    def test_statistics_markup_unwraps_collapsed_legacy_detail(self):
        collapsed = _source().replace(
            '<div class="statistics-summary">',
            '<details class="catalogue-overview"><summary>About</summary><div class="statistics-summary">',
        ).replace('</details></section>', '</details></details></section>')
        markup = _read_markup(collapsed)
        self.assertNotIn('catalogue-overview', markup)
        self.assertTrue(markup.endswith('</details></section>'))


    def test_repair_prefers_current_catalogue_summary(self):
        with TemporaryDirectory() as temporary:
            web = Path(temporary)
            (web / 'data').mkdir(parents=True)
            (web / 'catalogue').mkdir()
            (web / 'research').mkdir()
            artifact = web / 'data/catalogue-statistics.json'
            artifact.write_text(json.dumps({'html': _source('7')}), encoding='utf-8')
            (web / 'catalogue/index.html').write_text(_source('42'), encoding='utf-8')
            (web / 'research/index.html').write_text(
                '<html><head><title>Research</title></head><body><main class="r-main" id="main">old</main></body></html>',
                encoding='utf-8',
            )
            with patch.object(statistics, 'WEB', web), patch.object(statistics, 'STATISTICS_ARTIFACT', artifact):
                self.assertEqual(statistics.repair(), {'statistics_page': 1})
            page = (web / 'statistics/index.html').read_text(encoding='utf-8')
            self.assertIn('<strong>42</strong>', page)
            self.assertNotIn('<strong>7</strong>', page)


class FirstNameCohortTests(unittest.TestCase):
    def test_birth_surname_and_single_given_name(self):
        base = {'last_names_at_birth': ['Glasgow'], 'first_names': ['Mary Ann'], 'birth': 'c. 1699', 'gender': 'Female'}
        rows = statistics.first_name_rows([base, dict(base, last_names_at_birth=['Smith']), dict(base, likely_living=True)])
        self.assertEqual(rows, [['Mary', 1699, 'Female', 1]])

    def test_bounds_ranges_and_missing_values_remain_undated(self):
        base = {'last_names_at_birth': ['GLASGOW'], 'first_names': ['John'], 'gender': ''}
        people = [dict(base, birth=birth) for birth in ('before 1700', 'after 1690', '1690–1710', '')]
        self.assertEqual(statistics.first_name_rows(people), [['John', None, 'Unknown', 4]])


class PanelChartDataTests(unittest.TestCase):
    def test_complete_denominators_and_migration_endpoints(self):
        from bs4 import BeautifulSoup
        with TemporaryDirectory() as temporary:
            web = Path(temporary)
            (web / 'data').mkdir()
            (web / 'data/people.json').write_text(json.dumps({'people': [
                {'birth_location': 'Ireland', 'death_location': 'United States'},
                {'birth_location': 'Scotland', 'death_location': 'Scotland'},
            ]}))
            (web / 'data/catalogue-search-index.json').write_text(json.dumps([
                {'family_root': {'id': 'root'}}, {'family_root': None},
            ]))
            panels = ''.join('<section class="statistics-panel"><h3>' + title +
                             '</h3></section>' for title in [
                                 'Most frequent given names',
                                 'Largest exported family branches',
                                 'Most common recorded migrations'])
            with patch.object(statistics, 'WEB', web):
                soup = BeautifulSoup(statistics.enrich_panels(panels), 'html.parser')
            self.assertEqual(soup.select_one('#given-names')['data-total'], '2')
            self.assertEqual(soup.select_one('#family-branches')['data-total'], '1')
            self.assertEqual(json.loads(soup.select_one('.statistics-migration-data').string),
                             [['Ireland', 'United States', 1]])


class StatisticsLayoutTests(unittest.TestCase):
    def test_overview_keeps_all_totals_with_four_primary(self):
        from bs4 import BeautifulSoup
        labels = ['Historical people', 'Mapped records', 'Mapped places', 'Cross-region life courses',
                  'Exported family roots', 'People linked to a root']
        summary = '<div class="statistics-summary">' + ''.join(
            '<div><strong>' + str(index + 1) + '</strong><span>' + label + '</span></div>'
            for index, label in enumerate(labels)) + '</div>'
        soup = BeautifulSoup(statistics.overview_markup(summary), 'html.parser')
        self.assertEqual(len(soup.select('.statistics-metric-grid > div')), 4)
        self.assertEqual(len(soup.select('.statistics-extra-grid > div')), 2)
        self.assertEqual([node.text for node in soup.select('strong')], ['1', '2', '3', '4', '5', '6'])
        self.assertFalse(soup.select_one('.statistics-extra-totals').has_attr('open'))

    def test_views_group_all_charts_and_keep_details(self):
        from bs4 import BeautifulSoup
        ids = ['given-names', 'birth-centuries', 'regions', 'family-branches',
               'mapped-places', 'married-surnames', 'migration']
        panels = ''.join('<section class="statistics-panel" id="' + ident +
                         '"><h3>' + ident + '</h3><p>Scope</p><ol class="statistics-bars"><li>Counts</li></ol></section>'
                         for ident in ids)
        with patch.object(statistics, 'first_names_panel', return_value='<section id="first-names">Names</section>'):
            soup = BeautifulSoup(statistics.chart_views(panels), 'html.parser')
        self.assertEqual(len(soup.select('[data-statistics-pane]')), 4)
        self.assertEqual(len(soup.select('.statistics-panel')), 7)
        self.assertTrue(soup.select_one('#statistics-view-time #birth-centuries'))
        self.assertTrue(soup.select_one('#statistics-view-journeys #migration'))
        self.assertEqual(len(soup.select('#statistics-view-places .statistics-panel')), 4)
        self.assertFalse(soup.select_one('.statistics-comparison').has_attr('open'))
        self.assertEqual(len(soup.select('.statistics-panel-method')), 7)
