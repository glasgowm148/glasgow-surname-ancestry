"""Site inputs that no builder produces have a declared home outside www/ (fictional files)."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import site_declared_inputs as declared  # noqa: E402


class DeclaredInputs(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data" / "site").mkdir(parents=True)
        for published, _ in declared.DECLARED:
            path = self.root / "www" / published
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"invented": "%s"}\n' % published, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_an_empty_www_gets_every_declared_input_back(self) -> None:
        declared.adopt(self.root)
        for published, _ in declared.DECLARED:
            (self.root / "www" / published).unlink()
        self.assertTrue(declared.check(self.root))
        self.assertEqual(len(declared.install(self.root)), len(declared.DECLARED))
        self.assertEqual(declared.check(self.root), [])

    def test_a_missing_or_changed_input_stops_the_build(self) -> None:
        declared.adopt(self.root)
        home = self.root / declared.HOME / declared.DECLARED[0][0]
        home.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "changed since it was declared"):
            declared.install(self.root)
        home.unlink()
        with self.assertRaisesRegex(SystemExit, "is missing"):
            declared.install(self.root)


if __name__ == "__main__":
    unittest.main()
