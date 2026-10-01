import unittest

from tools.site_assets import deduplicate_assets, duplicate_ids


class SiteAssetTests(unittest.TestCase):
    def test_relative_query_variants_keep_last_at_first_position(self):
        source = ('<html><head><link rel="stylesheet" href="../css/site.css?v=old">'
                  '<script src="https://cdn.example/x.js"></script>'
                  '<link rel="stylesheet" href="/css/site.css?v=new" data-current="yes">'
                  '<script src="../js/app.js?v=1"></script><script src="../js/app.js?v=2"></script>'
                  '<script>window.x=1</script></head></html>')
        result, duplicates = deduplicate_assets(source, base_url="https://example.test/branches/index.html")
        self.assertEqual(['/css/site.css', '/js/app.js'], duplicates)
        self.assertEqual(result.count('site.css'), 1)
        self.assertIn('data-current="yes"', result)
        self.assertLess(result.index('data-current'), result.index('cdn.example'))
        self.assertEqual(result.count('app.js'), 1)
        self.assertIn('app.js?v=2', result)
        self.assertIn('window.x=1', result)

    def test_idempotent_and_duplicate_ids_are_report_only(self):
        source = '<main id="x"><p id="x">x</p><script src="/a.js"></script></main>'
        once, _ = deduplicate_assets(source)
        twice, _ = deduplicate_assets(once)
        self.assertEqual(once, twice)
        self.assertEqual(duplicate_ids(source), ['x'])
        self.assertEqual(source.count('id="x"'), 2)

    def test_images_do_not_deduplicate_and_script_closing_tag_is_removed(self):
        source = '<!DOCTYPE html>\n<base href="/static/"><img src="/a.png"><img src="/a.png">'
        source += '<script src="/x.js?v=1">old</script><script src="/x.js?v=2">new</script>'
        result, _ = deduplicate_assets(source, base_url="https://example.test/page.html")
        self.assertEqual(result.count('a.png'), 2)
        self.assertEqual(result.count('x.js'), 1)
        self.assertIn('new</script>', result)
        self.assertNotIn('old</script>', result)
        self.assertTrue(result.startswith('<!DOCTYPE html>\n'))
        result2, _ = deduplicate_assets(result, base_url="https://example.test/page.html")
        self.assertEqual(result, result2)


if __name__ == '__main__':
    unittest.main()
