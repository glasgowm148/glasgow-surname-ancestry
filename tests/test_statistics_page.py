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
