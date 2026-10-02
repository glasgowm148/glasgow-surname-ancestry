import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location("release_readiness", ROOT / "tools" / "repair_release_readiness.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ReleaseReadinessTests(unittest.TestCase):
    def test_homepage_count_preserves_the_new_introduction_and_tree_scope(self):
        helper = module()
        page = '<section class="reader-intro"><h1>Family history</h1></section><span>The family tree · 123 public profiles</span>'
        self.assertEqual(page, helper.homepage_count(page, 456))
        legacy = '<div class="v3-hero-stat"><strong>123</strong> catalogue entries</div>'
        self.assertIn('<strong>456</strong>', helper.homepage_count(legacy, 456))
        with self.assertRaises(ValueError):
            helper.homepage_count('<h1>Unrecognised layout</h1>', 456)

    def test_release_data_is_current_and_explicit(self):
        helper = module()
        health, manifest, generated = helper.release_data()
        self.assertEqual(health["counts"]["people"], next(row["count"] for row in manifest["datasets"] if row["name"] == "people"))
        self.assertEqual("2026-09-27", generated.isoformat())

    def test_snapshot_keeps_catalogue_identity_and_separate_snapshots(self):
        helper = module()
        page = '<a class="g-snapshot-link" href="/status/" title="Old">Catalogue · old</a>'
        repaired = helper.snapshot(page, helper.release_data()[2])
        self.assertIn("Catalogue · 27 Sep 2026", repaired)
        self.assertIn("Tree and DNA have separate snapshot dates.", repaired)

    def test_changes_feed_uses_dated_native_research_updates(self):
        helper = module()
        updates = helper.research_updates()
        self.assertTrue(updates)
        first = helper.entry(*updates[0][:4], "Read the case and evidence", updates[0][4])
        self.assertIn('<time datetime=', first)
        self.assertIn('Read the case and evidence', first)

    def test_snapshot_without_title_and_about_dates(self):
        helper = module()
        generated = helper.release_data()[2]
        page = '<a class="g-snapshot-link" href="/status/">Catalogue · old</a>'
        fixed = helper.snapshot(page, generated)
        self.assertIn('Catalogue · 27 Sep 2026', fixed)
        self.assertEqual(helper.snapshot(fixed, generated), fixed)
        about = '<table><tr><td>Research catalogue</td><td>People</td><td>Old</td></tr><tr><td>Family tree</td><td>Tree</td><td>2026-09-06</td></tr></table>'
        fixed = helper.about_dates(about, generated, {'latest_research_update':'2026-09-30'})
        self.assertIn('<td>27 September 2026</td>', fixed)
        self.assertIn('<td>2026-09-06</td>', fixed)
        self.assertIn('Latest dated person research or review: 2026-09-30', fixed)
        self.assertEqual(helper.about_dates(fixed, generated, {'latest_research_update':'2026-09-30'}), fixed)

    def test_scoped_stylesheet_insertion_is_idempotent(self):
        helper = module()
        page = "<html><head></head><body class=\"example\"></body></html>"
        first = helper.add_css(page)
        self.assertIn(helper.CSS_HREF, first)
        self.assertIn('class="example release-ready"', first)
        self.assertEqual(first, helper.add_css(first))


if __name__ == "__main__":
    unittest.main()
