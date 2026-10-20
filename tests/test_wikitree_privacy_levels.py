"""WikiTree Privacy 35 profiles are published as tree facts only (docs/privacy-policy.md)."""
from pathlib import Path
import unittest

from bs4 import BeautifulSoup

from tests._generated_data import requires_generated_data

ROOT = Path(__file__).resolve().parents[1]
TREE_ONLY = "no separate research has been written"


def privacy_level(profile):
    fields = {**profile, **(profile.get("profile_fields") or {})}
    try:
        return int(fields.get("Privacy", fields.get("privacy")))
    except (TypeError, ValueError):
        return None


@requires_generated_data
class WikiTreePrivacyLevelTests(unittest.TestCase):
    def test_privacy_35_pages_show_tree_facts_only(self):
        from tools.project_paths import merged_map_profiles
        profiles, _ = merged_map_profiles()
        checked = 0
        for profile_id, profile in profiles.items():
            if not isinstance(profile, dict) or privacy_level(profile) != 35:
                continue
            page = ROOT / "www/people" / f"{profile_id.casefold()}.html"
            if not page.is_file():
                continue
            checked += 1
            with self.subTest(profile=profile_id):
                main = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser").select_one("main")
                about = main.select_one("h2").find_parent("section").get_text(" ", strip=True)
                self.assertIn(TREE_ONLY, about)
                self.assertEqual([], main.select("figure, blockquote, .biography-section, .biography-figure"))
                self.assertNotIn("/people/research-material/", str(main))
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
