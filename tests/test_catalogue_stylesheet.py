from pathlib import Path
import importlib.util
import unittest

from tests._generated_data import requires_generated_data


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('catalogue_theme', ROOT / 'tools/catalogue_theme.py')
THEME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(THEME)


class CatalogueStylesheetTests(unittest.TestCase):
    @requires_generated_data
    def test_clean_route_loads_the_catalogue_layout(self):
        page = (ROOT / 'www/catalogue/index.html').read_text()
        self.assertEqual(1, page.count('href="/people/catalogue.css?'))
        self.assertTrue((ROOT / 'www/people/catalogue.css').is_file())

    def test_insertion_handles_hashed_shared_stylesheet(self):
        shell = '<head><link href="/assets/unified/site.css?v=abc123" rel="stylesheet"></head>'
        fixed = THEME.ensure_catalogue_stylesheet(shell)
        self.assertIn('/people/catalogue.css?', fixed)
        self.assertLess(fixed.index('/people/catalogue.css?'), fixed.index('/assets/unified/site.css?'))
        self.assertEqual(fixed, THEME.ensure_catalogue_stylesheet(fixed))
