import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from tools import smoke_test_site as smoke
from tools import check_public_catalogue as catalogue


class SiteSmokeSemanticsTests(unittest.TestCase):
    def test_changed_wording_keeps_structural_page_check(self):
        body = b'<title>New wording</title><h1>Alexander Glasgow</h1><main data-r-person="Glasgow-951">Updated</main>'
        self.assertTrue(smoke.page_matches(body, "Alexander Glasgow", "Glasgow-951"))

    def test_missing_or_wrong_person_fails(self):
        self.assertFalse(smoke.page_matches(b"<h1>Alexander Glasgow</h1>", "Alexander Glasgow", "Glasgow-951"))
        self.assertFalse(smoke.page_matches(b'<h1>Alexander Glasgow</h1><main data-r-person="Other-1">', "Alexander Glasgow", "Glasgow-951"))

    def test_fetch_applies_browser_user_agent(self):
        seen = {}
        class Response(BytesIO):
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def fake(request, timeout):
            seen.update(request.headers)
            return Response(b"ok")
        with patch.object(smoke, "urlopen", fake):
            smoke.fetch("https://example.test/")
        self.assertIn("Mozilla/5.0", seen["User-agent"])

    def test_403_is_access_failure(self):
        with patch.object(smoke, "fetch", return_value=(403, b"blocked")):
            self.assertIn("access/WAF failure", smoke.smoke_test("https://example.test", __import__('pathlib').Path('/tmp'))[0])


if __name__ == "__main__":
    unittest.main()
