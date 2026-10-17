import unittest
from pathlib import Path

from tools.approved_restorations import approved_document, documentary_renderer, entries, source, usable_tester_panel
from tools.atlas_whole_tree import MARKER, PATCHES, whole_tree_renderer

ROOT = Path(__file__).resolve().parents[1]


class WholeTreeRendererTest(unittest.TestCase):
    def setUp(self):
        entry = entries().get('assets/research/atlas.js')
        if entry is None:
            self.skipTest('approved atlas renderer source is not available')
        self.original = source(entry)

    def test_every_patch_applies_to_the_approved_source(self):
        for old, _ in PATCHES:
            self.assertEqual(self.original.count(old), 1, old[:70])
        page = documentary_renderer(usable_tester_panel(self.original))
        for _, new in PATCHES:
            self.assertIn(new, page)
        self.assertIn(MARKER, page)

    def test_renderer_is_idempotent(self):
        page = documentary_renderer(usable_tester_panel(self.original))
        self.assertEqual(documentary_renderer(page), page)
        self.assertEqual(whole_tree_renderer(page), page)

    def test_camera_easing_cannot_run_backwards(self):
        page = whole_tree_renderer(self.original)
        self.assertIn('clamp((t-start)/280,0,1)', page)
        self.assertNotIn('Math.min(1,(t-start)/280)', page)

    def test_grandparents_filter_is_wired(self):
        page = whole_tree_renderer(self.original)
        for token in ('function setGrand(', 'id="grand-toggle"', "&filter=grandparents", 'drawGrandLabels(guard,z)'):
            self.assertIn(token, page)

    def test_family_areas_and_pins(self):
        page = whole_tree_renderer(self.original)
        self.assertIn('familyAreaHit(x,y)', page)
        self.assertIn('drawFamilyAreas(c,R)', page)
        self.assertIn(' drawCanopyRim(c,R,guard,fw);\n if(state.pins)for(const d of DNA.values()){', page)

    def test_prism_features_are_wired(self):
        page = whole_tree_renderer(self.original)
        for token in ('function setBranch(', 'id="colour-branch"', "'&colour='+(state.evidence?'evidence':'branch')", 'function drawGapMarks(', "k.id='canopy-key'",
                      'father-uncertain', 'function enterSun(', 'function drawSun(', '&sun=', "case 'sun':enterSun(id)",
                      'function setLayout(', 'id="layout-gen"', '&layout=gen', 'if(atlasGenMode)r='):
            self.assertIn(token, page)

    def test_research_layer_is_wired(self):
        page = whole_tree_renderer(self.original)
        for token in ('function setLineColour(', 'id="colour-evidence"', '&colour=', 'function evidenceColour(',
                      '/assets/research/tree-research-status.json', 'function openHunt(', 'function openYdna(',
                      'function exportMarked(', 'function markFilter(', "data-key-mode=\"all\"", "case 'hunt':openHunt()", '${rsLine(p.id)}', 'a link needs a record'):
            self.assertIn(token, page)

    def test_pages_without_the_canopy_pass_through(self):
        self.assertEqual(whole_tree_renderer('const x=1;'), 'const x=1;')

    def test_public_renderer_matches_the_approved_transform(self):
        path = ROOT / 'www/assets/research/atlas.js'
        if not path.exists():
            self.skipTest('local site not built')
        self.assertTrue(approved_document('assets/research/atlas.js', path.read_text()))


if __name__ == '__main__':
    unittest.main()
