from pathlib import Path
import unittest

from tools import approved_restorations, render_testament_kinship


class PublicReferenceLinksTests(unittest.TestCase):
    def test_moved_reference_navigation_retains_fragments_and_evidence(self):
        original = ('<html><head></head><body><p>Original evidence text.</p>'
                    '<a href="timeline.html#R-FT20271">Deep timeline</a>'
                    '<a href="map/">Map</a>'
                    '<a href="https://example.org/timeline.html">External</a></body></html>')
        page = approved_restorations.reference_html(original)
        self.assertIn('href="/timeline/#R-FT20271"', page)
        self.assertIn('href="/map/"', page)
        self.assertIn('<p>Original evidence text.</p>', page)
        self.assertIn('href="https://example.org/timeline.html"', page)
        self.assertEqual(page, approved_restorations.reference_html(page))

    def test_followup_repository_citations_link_published_profile_sections(self):
        page = render_testament_kinship.render_followups()
        for section in ('research', 'wikitree-update'):
            self.assertIn(f'href="/people/glasgow-3078.html#{section}"', page)
        self.assertNotIn('href="research/Glasgow-3078/', page)
        profile = (Path(__file__).resolve().parents[1] / 'www/people/glasgow-3078.html').read_text()
        for section in ('research', 'wikitree-update'):
            self.assertIn(f'id="{section}"', profile)
