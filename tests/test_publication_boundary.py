import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.check_publication_boundary import audit
from tools.public_privacy import PublicPrivacy
from tools.repair_public_mirrors import project_html


class PublicationBoundaryTests(unittest.TestCase):
    def test_restricted_capture_cannot_bypass_release_using_a_historical_id(self):
        policy = PublicPrivacy({})
        capture = {"profile_id": "Example-100", "privacy": 35,
                   "profile_fields": {"LongName": "Restricted subject"}, "sources": [{"citation": "Restricted citation"}]}
        with tempfile.TemporaryDirectory() as directory, patch('tools.check_publication_boundary.audit_approved_research', return_value=[]):
            root = Path(directory)
            mirror = root / "mirror.json"
            page = root / "mirror.html"
            mirror.write_text(json.dumps(capture))
            page.write_text('<script type="application/json">' + json.dumps(capture) + '</script>')
            self.assertEqual(len(audit(root, policy)), 2)
            mirror.write_text(json.dumps(policy.project(capture)))
            page.write_text(project_html(page.read_text(), policy))
            self.assertEqual(audit(root, policy), [])


    def test_empty_or_opaque_files_cannot_publish_a_withheld_id_in_their_path(self):
        policy = PublicPrivacy({"Example-100": {"IsLiving": True}})
        with tempfile.TemporaryDirectory() as directory, patch('tools.check_publication_boundary.audit_approved_research', return_value=[]):
            root = Path(directory)
            for name, content in (("example-100.json", b"[]"), ("example-100.png", b"fixture")):
                (root / name).write_bytes(content)
            self.assertCountEqual(audit(root, policy), [
                "Withheld identifier remains in path: example-100.json",
                "Withheld identifier remains in path: example-100.png",
            ])


if __name__ == "__main__":
    unittest.main()
