import json
from pathlib import Path
import tempfile
import unittest

from tests._generated_data import requires_generated_data
from tools import relink_finding_anchors as relink

ROOT = Path(__file__).resolve().parents[1]


class RelinkFindingAnchorTests(unittest.TestCase):
    def test_links_move_to_the_stable_page_and_the_pass_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "www"
            (web / "people").mkdir(parents=True)
            findings = [{"id": f"f-{n:03d}", "found_on": f"2026-{1 + n // 28:02d}-{1 + n % 28:02d}", "finding": f"Fact {n}."}
                        for n in range(120)]
            ledger = root / "ledger.json"
            ledger.write_text(json.dumps({"findings": findings}))
            # f-119 is the newest (archive page 3); f-000 the earliest (page 1).
            page = web / "people/a.html"
            page.write_text('<a href="/latest-findings/#finding-f-000">old root link</a>'
                            '<a href="/latest-findings/page/2/#finding-f-119">old page link</a>'
                            '<a href="/latest-findings/page/1/#finding-f-001">already right</a>'
                            '<a href="/latest-findings/#finding-gone">unknown</a>'
                            '<a href="/latest-findings/">no anchor</a>')
            data = web / "people/a.json"
            data.write_text(json.dumps({"url": "https://glasgow.phenotype.dev/latest-findings/#finding-f-119"}))
            self.assertEqual({"files": 2, "links": 3, "unknown_findings": ["gone"]}, relink.relink(web, ledger, write=False))
            self.assertIn("/latest-findings/#finding-f-000", page.read_text())
            self.assertEqual({"files": 2, "links": 3, "unknown_findings": ["gone"]}, relink.relink(web, ledger))
            text = page.read_text()
            self.assertIn('href="/latest-findings/page/1/#finding-f-000"', text)
            self.assertIn('href="/latest-findings/page/3/#finding-f-119"', text)
            self.assertIn('href="/latest-findings/page/1/#finding-f-001"', text)
            self.assertIn('href="/latest-findings/#finding-gone"', text)
            self.assertIn('href="/latest-findings/"', text)
            self.assertEqual("https://glasgow.phenotype.dev/latest-findings/page/3/#finding-f-119", json.loads(data.read_text())["url"])
            self.assertEqual({"files": 0, "links": 0, "unknown_findings": ["gone"]}, relink.relink(web, ledger))

    @requires_generated_data
    def test_published_site_links_each_finding_to_its_page(self):
        if not (ROOT / "www/latest-findings/page/1/index.html").is_file():
            self.skipTest("latest findings not built with stable archive pages")
        result = relink.relink(write=False)
        self.assertEqual(0, result["links"], "run tools/relink_finding_anchors.py")


if __name__ == "__main__":
    unittest.main()
