import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from tools.build_research_catalog import _profile_diff_html


class ProfileUpdateDiffTests(unittest.TestCase):
    def test_preservation_review_cannot_approve_changed_capture_or_replacement(self):
        import hashlib
        from tools.build_research_catalog import _validate_profile_preservation_review
        digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
        review = dict(current_sha256=digest('current'), proposed_sha256=digest('replacement'),
                      all_substantive_passages_accounted_for=True)
        _validate_profile_preservation_review('Glasgow-548', 'current', 'replacement', review)
        for current, proposed in [('changed current', 'replacement'), ('current', 'shortened replacement')]:
            with self.subTest(current=current, proposed=proposed), self.assertRaisesRegex(ValueError, 'stale'):
                _validate_profile_preservation_review('Glasgow-548', current, proposed, review)

    def rows(self, current, replacement):
        soup = BeautifulSoup(_profile_diff_html(current, replacement), "html.parser")
        return soup, soup.select(".profile-diff-row")

    def test_replacement_aligns_lines_and_escapes_profile_markup(self):
        soup, rows = self.rows("keep\nold <tag>", "keep\nnew <tag>")
        self.assertEqual(["is-unchanged", "is-changed"], [row["class"][-1] for row in rows])
        self.assertEqual("2", rows[1].select_one(".profile-diff-line-number").get_text())
        self.assertEqual("2", rows[1].select(".profile-diff-line-number")[1].get_text())
        self.assertIn("new &lt;tag&gt;", str(soup))
        self.assertNotIn("<tag>", str(soup))

    def test_deletion_is_red_left_with_blank_right_line(self):
        soup, rows = self.rows("keep\nremove\nend", "keep\nend")
        deletion = rows[1]
        self.assertIn("is-removed", deletion["class"])
        self.assertEqual("remove", deletion.select(".profile-diff-text")[0].get_text())
        self.assertEqual("", deletion.select(".profile-diff-text")[1].get_text())
        self.assertEqual("", deletion.select(".profile-diff-line-number")[1].get_text())

    def test_insertion_is_green_right_with_blank_left_line(self):
        soup, rows = self.rows("keep\nend", "keep\nadd\nend")
        insertion = rows[1]
        self.assertIn("is-added", insertion["class"])
        self.assertEqual("", insertion.select(".profile-diff-text")[0].get_text())
        self.assertEqual("add", insertion.select(".profile-diff-text")[1].get_text())
        self.assertEqual("", insertion.select(".profile-diff-line-number")[0].get_text())

    def test_completed_legacy_panel_is_migrated_from_full_textareas(self):
        from tools import repair_person_hierarchy as renderer

        legacy = """<html><body><main>
        <section id="wikitree-update" class="profile-update-panel profile-comparison-panel">
          <p class="workbench-audit">Compared with <a href="https://www.wikitree.com/wiki/Glasgow-992">Glasgow-992</a>, captured 2026-09-27T03:22:58+00:00 · 2026-09-18.</p>
          <details class="profile-current-capture"><textarea id="profile-update-current" readonly>same
old &lt;tag&gt;</textarea></details>
          <details open><pre class="profile-update-diff">  same
- old &lt;tag&gt;
+ new &lt;tag&gt;</pre></details>
          <textarea id="profile-update-draft" readonly>same
new &lt;tag&gt;</textarea>
        </section></main></body></html>"""
        replacement = "<html><body><main><section id='overview'><h2>Overview</h2></section></main></body></html>"
        with patch.object(renderer, "_replace_main", return_value=replacement):
            migrated, changed = renderer.revise(legacy, "Glasgow-992")
        self.assertTrue(changed)
        soup = BeautifulSoup(migrated, "html.parser")
        panel = soup.select_one("#wikitree-update")
        self.assertIsNotNone(panel)
        self.assertIsNotNone(panel.select_one(".profile-update-diff[role='table']"))
        self.assertIsNone(panel.select_one(".profile-update-diff pre"))
        self.assertEqual("same\nold <tag>", panel.select_one("#profile-update-current").get_text())
        self.assertEqual("same\nnew <tag>", panel.select_one("#profile-update-draft").get_text())
        self.assertIn("is-changed", [row["class"][-1] for row in panel.select(".profile-diff-row")])
        self.assertIsNotNone(soup.select_one("script[src*='profile-update.js']"))
        with patch.object(renderer, "_replace_main", return_value=replacement):
            rerendered, changed_again = renderer.revise(migrated, "Glasgow-992")
        self.assertEqual(migrated, rerendered)
        self.assertFalse(changed_again)

    def test_diff_scroll_region_is_keyboard_named_and_bounded(self):
        from tools.build_research_catalog import _profile_update_html

        soup = BeautifulSoup(_profile_update_html({
            "profile_id": "Glasgow-1",
            "profile_url": "https://www.wikitree.com/wiki/Glasgow-1",
            "summary": "Update",
            "remote_wikitext": "old",
            "proposed_wikitext": "new",
        }), "html.parser")
        scroll = soup.select_one(".profile-diff-scroll")
        self.assertEqual("region", scroll.get("role"))
        self.assertEqual("0", scroll.get("tabindex"))
        self.assertEqual("Scrollable profile comparison", scroll.get("aria-label"))

    def test_manual_amendment_keeps_diff_even_when_manager_blocked(self):
        from tools.build_research_catalog import _profile_update_html

        for replacement, expected in [("new", "is-changed"), ("old", "is-unchanged")]:
            with self.subTest(replacement=replacement):
                soup = BeautifulSoup(_profile_update_html({
                    "profile_id": "Glasgow-548",
                    "profile_url": "https://www.wikitree.com/wiki/Glasgow-548",
                    "status": "BLOCKED — profile managed by another member",
                    "manual_update": True,
                    "remote_wikitext": "old",
                    "proposed_wikitext": replacement,
                }), "html.parser")
                self.assertIsNotNone(soup.select_one(".profile-update-diff"))
                self.assertIn(expected, soup.select_one(".profile-diff-row")["class"])
                self.assertEqual(replacement, soup.select_one("#profile-update-draft").get_text())
                self.assertNotIn("biography already contains", soup.get_text())

    def test_manual_amendment_without_capture_does_not_invent_deletions(self):
        from tools.build_research_catalog import _profile_update_html

        soup = BeautifulSoup(_profile_update_html({
            "profile_id": "Glasgow-1",
            "profile_url": "https://www.wikitree.com/wiki/Glasgow-1",
            "manual_update": True,
            "proposed_wikitext": "replacement",
        }), "html.parser")
        self.assertIsNone(soup.select_one(".profile-update-diff"))
        self.assertIn("capture is unavailable", soup.get_text())
        self.assertEqual("replacement", soup.select_one("#profile-update-draft").get_text())

    def test_collapsed_changes_only_controls_preserve_complete_biographies(self):
        from tools.build_research_catalog import _profile_update_controls, _profile_update_html
        current, replacement = 'keep\nold\nend', 'keep\nnew\nend'
        markup = _profile_update_html(dict(profile_id='Glasgow-548',
            profile_url='https://www.wikitree.com/wiki/Glasgow-548',
            remote_wikitext=current, proposed_wikitext=replacement))
        soup = BeautifulSoup(markup, 'html.parser')
        self.assertNotIn('open', soup.select_one('.profile-update-disclosure').attrs)
        self.assertNotIn('open', soup.select_one('details.profile-draft-panel').attrs)
        self.assertIn('checked', soup.select_one('.profile-diff-changes-only').attrs)
        self.assertEqual(replacement, soup.select_one('#profile-update-draft').get_text())
        self.assertEqual(2, len(soup.select('.is-unchanged')))
        self.assertEqual(markup, _profile_update_controls(markup))

    def test_identical_biographies_do_not_offer_an_empty_changes_view(self):
        from tools.build_research_catalog import _profile_update_html
        soup = BeautifulSoup(_profile_update_html(dict(profile_id='Glasgow-548',
            profile_url='https://www.wikitree.com/wiki/Glasgow-548',
            remote_wikitext='same', proposed_wikitext='same')), 'html.parser')
        self.assertIn('disabled', soup.select_one('.profile-diff-changes-only').attrs)
        self.assertNotIn('checked', soup.select_one('.profile-diff-changes-only').attrs)
        self.assertIn('No biography changes', soup.get_text())


if __name__ == "__main__":
    unittest.main()
