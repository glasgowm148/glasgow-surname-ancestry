"""Internal link checker (tools/check_internal_links.py) on a tiny fixture site."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools import check_internal_links as checker


def write(path: Path, text: str = "<!doctype html><html><head></head><body></body></html>") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def page(body: str, head: str = "") -> str:
    return f"<!doctype html><html><head>{head}<link rel=\"stylesheet\" href=\"/assets/site.css?v=1\"></head><body>{body}</body></html>"


GOOD = """
<a href="/">home</a> <a href="/about/">about</a> <a href="/about">no slash</a> <a href="about/index.html?x=1#top">rel</a>
<a href="https://example.org/x">external</a> <a href="mailto:a@b.c">mail</a> <a href="#local">same page</a>
<a href="javascript:void(0)">js</a> <a href="https://glasgow.phenotype.dev/people/a.html#known">canonical-style</a>
<img src="/img/a.png" srcset="/img/a.png 1x, /img/a.png 2x"> <a href="/people/a%2Dx.html">encoded</a>
<a href="${item.url}">template</a>
<script>document.body.innerHTML = '<a href="/missing-in-script/">x</a>';</script>
<!-- <a href="/missing-in-comment/">x</a> -->
<textarea><a href="/missing-in-textarea/">x</a></textarea>
<a href="/people/a.html#lazy-one">lazy anchor</a>
"""

BAD = """
<a href="/research/Glasgow-951/sources/folio52.jpg">note file</a>
<a href="/people/nobody-1.html">no page</a>
<a href="people/a.html#wikitree-update">relative</a>
<a href="Private family details withheld.">withheld</a>
<a href="/legacy">extensionless</a>
<img src="/img/missing.png">
<a href="/people/a.html#no-such-anchor">bad anchor</a>
<a href="https://glasgow.phenotype.dev/gone/">gone</a>
<a href="../../outside.html">outside</a>
"""


class InternalLinkCheckerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.site = root / "www"
        self.baseline = root / "data/site/internal-link-baseline.json"
        site = self.site
        write(site / "assets/site.css", "body{}")
        write(site / "img/a.png", "png")
        write(site / "index.html", page(GOOD))
        write(site / "about/index.html", page("<p id='top'>About</p>"))
        write(site / "legacy.html", page("legacy"))
        write(site / "people/a.html", page("<h2 id='known'>A</h2><details data-r-fragment='/assets/research/fragments/a-0123456789abcdef.html' "
                                           "data-r-fragment-anchors='lazy-one lazy-two'></details>"))
        write(site / "people/a-x.html", page("encoded target"))
        write(site / "people/b.html", page("B"))
        # A lazy fragment is inserted into /people/a.html: its relative links resolve there.
        write(site / "assets/research/fragments/a-0123456789abcdef.html", "<details><a href='b.html'>B</a></details>")
        # <base href> is honoured.
        write(site / "research/subjects/x/index.html", page("<a href='people/b.html'>B</a>", head='<base href="../../../">'))
        write(site / "catalogue/index.html", page(BAD))

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = checker.main(["--site", str(self.site), "--jobs", "1", *map(str, args)])
        return code, out.getvalue()

    def test_resolution_rules_and_causes(self):
        result = checker.check(self.site, jobs=1)
        broken = {(row["page"], row["href"]): row["cause"] for row in result["broken"]}
        self.assertTrue(all(page == "catalogue/index.html" for page, _ in broken), broken)
        self.assertEqual(broken, {
            ("catalogue/index.html", "/research/Glasgow-951/sources/folio52.jpg"): "research-repository-file",
            ("catalogue/index.html", "/people/nobody-1.html"): "person-without-page",
            ("catalogue/index.html", "people/a.html#wikitree-update"): "relative-link-wrong-folder",
            ("catalogue/index.html", "Private family details withheld."): "privacy-placeholder-href",
            ("catalogue/index.html", "/legacy"): "needs-html-extension",
            ("catalogue/index.html", "/img/missing.png"): "missing-asset",
            ("catalogue/index.html", "https://glasgow.phenotype.dev/gone/"): "missing-page",
            ("catalogue/index.html", "../../outside.html"): "missing-page",
        })

    def test_anchors_on_person_pages_are_reported_not_gated(self):
        result = checker.check(self.site, jobs=1)
        self.assertEqual([(a["page"], a["anchor"]) for a in result["missing_anchors"]],
                         [("catalogue/index.html", "no-such-anchor")])

    def test_parallel_scan_matches_serial(self):
        serial = checker.check(self.site, jobs=1)
        parallel = checker.check(self.site, jobs=2)
        self.assertEqual(serial["broken"], parallel["broken"])

    def test_no_baseline_fails_on_any_broken_link_and_writes_report(self):
        report = Path(self.tmp.name) / "report.json"
        code, out = self.run_main("--report", report)
        self.assertEqual(code, 1)
        data = json.loads(report.read_text())
        self.assertEqual(data["broken_pairs"], 8)
        self.assertEqual({c["cause"] for c in data["causes"]}, {
            "research-repository-file", "person-without-page", "relative-link-wrong-folder",
            "privacy-placeholder-href", "needs-html-extension", "missing-asset", "missing-page"})
        self.assertIn("builder", data["causes"][0])
        self.assertIn("8 broken", out)

    def test_missing_baseline_file_counts_as_empty(self):
        code, _ = self.run_main("--baseline", self.baseline)
        self.assertEqual(code, 1)
        self.assertFalse(self.baseline.exists())

    def test_baseline_ratchet(self):
        code, _ = self.run_main("--baseline", self.baseline, "--update-baseline")
        self.assertEqual(code, 0)
        stored = json.loads(self.baseline.read_text())
        self.assertEqual(stored["count"], 8)
        self.assertIn("/people/nobody-1.html", stored["pairs"]["catalogue/index.html"])
        self.assertEqual(self.run_main("--baseline", self.baseline)[0], 0)

        # A new broken link fails, and updating never adds it.
        write(self.site / "about/index.html", page("<a href='/new-missing/'>new</a>"))
        code, out = self.run_main("--baseline", self.baseline)
        self.assertEqual(code, 1)
        self.assertIn("NEW  about/index.html -> /new-missing/", out)
        self.assertEqual(self.run_main("--baseline", self.baseline, "--update-baseline")[0], 1)
        self.assertEqual(json.loads(self.baseline.read_text())["count"], 8)

        # Fixing links shrinks the baseline.
        write(self.site / "about/index.html", page("fixed"))
        write(self.site / "people/nobody-1.html", page("now published"))
        self.assertEqual(self.run_main("--baseline", self.baseline, "--update-baseline")[0], 0)
        stored = json.loads(self.baseline.read_text())
        self.assertEqual(stored["count"], 7)
        self.assertNotIn("/people/nobody-1.html", stored["pairs"]["catalogue/index.html"])

    def test_resolve(self):
        files = {"index.html", "a/index.html", "b.html", "c.txt"}
        self.assertEqual(checker.resolve("/", files), ("index.html", "dir"))
        self.assertEqual(checker.resolve("/a/", files)[0], "a/index.html")
        self.assertEqual(checker.resolve("/a", files)[1], "dir-noslash")
        self.assertEqual(checker.resolve("/b", files), (None, "html-fallback"))
        self.assertEqual(checker.resolve("/c.txt", files)[0], "c.txt")
        self.assertEqual(checker.resolve("/b/", files), (None, "missing"))


if __name__ == "__main__":
    unittest.main()
