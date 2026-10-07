"""The targeted place-page refresh keeps the site shell and replaces only the main content."""
import unittest

from tools.refresh_place_pages import site_links, transplant

SHELL = ('<!DOCTYPE html><html><head><title>Kilwaughter · Glasgow Surname Project</title>'
         '<meta name="description" content="Old description."><link rel="stylesheet" href="/assets/unified/site.css"></head>'
         '<body><aside class="g-rail">menu</aside><main><h1>Kilwaughter</h1><p>23 mapped associations</p></main>'
         '<footer class="g-footer">footer</footer></body></html>')
FRESH = ('<!doctype html><html><head><title>Kilwaughter · Glasgow Surname Project</title>'
         '<meta name="description" content="New description."></head><body><header>legacy header</header>'
         '<main><h1>Kilwaughter</h1><p>23 records naming 14 people</p>'
         '<a href="../people/glasgow-1143.html">Robert Glasgow</a><a href="../catalogue.html">People</a>'
         '<span class="evidence-badge"><a class="ev-label-link" href="../evidence/#state-probable">Probable</a></span></main>'
         '<footer>legacy footer</footer></body></html>')


class RefreshPlacePagesTests(unittest.TestCase):
    def test_links_become_root_links_with_the_clean_catalogue_url(self):
        fragment = site_links('<a href="../people/x.html">x</a><a href="../catalogue.html">People</a><img src="../a.png">')
        self.assertEqual('<a href="/people/x.html">x</a><a href="/catalogue/">People</a><img src="/a.png">', fragment)

    def test_main_is_replaced_and_the_shell_is_kept(self):
        page = transplant(SHELL, FRESH)
        self.assertIn('<aside class="g-rail">menu</aside>', page)
        self.assertIn('<footer class="g-footer">footer</footer>', page)
        self.assertNotIn('legacy', page)
        self.assertIn('23 records naming 14 people', page)
        self.assertNotIn('mapped associations', page)
        self.assertIn('href="/people/glasgow-1143.html"', page)
        self.assertEqual(1, page.count('<main>'))

    def test_description_follows_the_fresh_page_and_the_label_stylesheet_is_linked(self):
        page = transplant(SHELL, FRESH)
        self.assertIn('content="New description."', page)
        self.assertNotIn('Old description', page)
        self.assertEqual(1, page.count('/assets/research/evidence.css'))
        self.assertEqual(page, transplant(page, FRESH), 'a second run changes nothing')

    def test_a_page_without_a_main_is_left_alone(self):
        self.assertIsNone(transplant('<html><body>no main</body></html>', FRESH))
        self.assertIsNone(transplant(SHELL, '<html><body>no main</body></html>'))


if __name__ == '__main__':
    unittest.main()
