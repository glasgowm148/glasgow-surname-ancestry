import contextlib
import io
import unittest
from unittest.mock import patch

from tools import publish_research_release as release


class ReleaseCommandTests(unittest.TestCase):
    def test_help_does_not_start_a_release(self):
        output = io.StringIO()
        with patch.object(release, 'publish') as publish, contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                release.main(['--help'])
        self.assertEqual(0, result.exception.code)
        self.assertIn('usage:', output.getvalue())
        publish.assert_not_called()

    def test_unknown_option_does_not_start_a_release(self):
        with patch.object(release, 'publish') as publish, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                release.main(['--typo'])
        self.assertEqual(2, result.exception.code)
        publish.assert_not_called()

    def test_normal_invocation_starts_one_release(self):
        with patch.object(release, 'publish') as publish:
            self.assertEqual(0, release.main([]))
        publish.assert_called_once_with()
