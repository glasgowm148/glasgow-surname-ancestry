import json
import unittest
from pathlib import Path

from tools import build_tree_research_status as status

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"r", "c", "n", "k", "q", "d"}


class TreeResearchStatusTest(unittest.TestCase):
    def setUp(self):
        if not (ROOT / status.MODEL).exists() or not (ROOT / "research/latest-findings.json").exists():
            self.skipTest("built site or research data not available")
        self.payload = status.build(ROOT, checks=False)
        model = json.loads((ROOT / status.MODEL).read_text(encoding="utf-8"))
        self.public = {p["id"] for p in model["people"] if p.get("kind") == "person"}

    def test_only_public_people_and_flag_fields(self):
        self.assertTrue(self.payload["people"])
        for ident, row in self.payload["people"].items():
            self.assertIn(ident, self.public)
            self.assertTrue(set(row) <= ALLOWED, (ident, row))
            if "q" in row:
                self.assertIn(row["q"], {"open", "blocked", "held", "done"})
            if "n" in row:
                self.assertRegex(row["n"], r"^\d{4}-\d\d-\d\d$")

    def test_no_research_text_is_published(self):
        text = json.dumps(self.payload["people"])
        self.assertNotIn("summary", text)
        self.assertLess(len(text), 400_000)

    def test_queue_states(self):
        self.assertEqual(status.queue_state("BLOCKED — NOT MANAGED", "X", set(), set()), "blocked")
        self.assertEqual(status.queue_state("DONE — VERIFIED LIVE", "X", set(), set()), "done")
        self.assertEqual(status.queue_state(None, "X", {"X"}, set()), "done")
        self.assertEqual(status.queue_state(None, "X", {"X"}, {"X"}), "open")
        self.assertEqual(status.queue_state("OPEN", "X", set(), set()), "open")


if __name__ == "__main__":
    unittest.main()
