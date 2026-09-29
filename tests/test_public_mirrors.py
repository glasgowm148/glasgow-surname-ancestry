import json
import unittest
from tools.public_privacy import PublicPrivacy
from tools.repair_public_mirrors import project_html, project_script, project_csv


class PublicMirrorTests(unittest.TestCase):
    def setUp(self):
        self.policy = PublicPrivacy({"Example-200": {"BirthDate": "2000-01-01"}})

    def test_cached_html_withholds_name_beside_private_url_and_embedded_json(self):
        raw = '<p>Historic account</p><p>Private Name <a href="https://www.wikitree.com/wiki/Example-200">Example-200</a></p><script type="application/json">' + json.dumps({"relations": [{"id": "Example-200", "name": "Private Name"}]}) + '</script>'
        rendered = project_html(raw, self.policy)
        self.assertNotIn("Private Name", rendered)
        self.assertNotIn("Example-200", rendered)
        self.assertIn("Historic account", rendered)

    def test_data_scripts_and_csv_withhold_relationship_mirrors(self):
        raw = 'window.Example=' + json.dumps([{"id": "Example-100", "relatives": [{"id": "Example-200", "name": "Private Name"}]}]) + ';'
        projected = project_script(raw, self.policy)
        self.assertNotIn("Private Name", projected)
        self.assertIn("Example-100", projected)
        csv = 'profile_id,name,relatives\nExample-100,Historic name,Private Name [Example-200]\nExample-200,Private subject,\n'
        projected = project_csv(csv, self.policy)
        self.assertNotIn("Private Name", projected)
        self.assertNotIn("Private subject", projected)
        self.assertIn("Historic name", projected)

    def test_restricted_capture_without_living_tokens_is_projected(self):
        capture = {"profile_id": "Example-100", "privacy": 35,
                   "profile_fields": {"LongName": "Restricted name"}, "sources": [{"citation": "Restricted source"}]}
        for raw, project in [(f'<script type="application/json">{json.dumps(capture)}</script>', project_html),
                             (f'window.Capture={json.dumps(capture)};', project_script)]:
            rendered = project(raw, self.policy)
            self.assertNotIn("Restricted name", rendered)
            self.assertNotIn("Restricted source", rendered)


if __name__ == "__main__":
    unittest.main()
