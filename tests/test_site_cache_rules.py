import tempfile
import unittest
from pathlib import Path

from tools.finalize_site import write_cache_rules


class CacheRulesTests(unittest.TestCase):
    def test_rules_keep_security_mime_and_versioned_cache_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_cache_rules(root)
            htaccess = (root / ".htaccess").read_text()
            headers = (root / "_headers").read_text()
            for text in (htaccess, headers):
                self.assertIn("nosniff", text)
                self.assertIn("strict-origin-when-cross-origin", text)
                self.assertIn("SAMEORIGIN", text)
            self.assertIn('AddType "application/json; charset=UTF-8" .json', htaccess)
            self.assertIn("v=[a-f0-9]{10}", htaccess)
            self.assertIn("max-age=31536000, immutable", htaccess)
            self.assertIn("/assets/research/fragments/*", headers)
            self.assertIn("/data/catalogue-details/*", headers)


if __name__ == "__main__":
    unittest.main()
