from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools import repair_publication_policy, site_analytics


MANAGED = """<!-- site-analytics:start -->
<script src="https://www.googletagmanager.com/gtag/js?id=G-test"></script>
<script>gtag('config', 'G-test')</script>
<!-- site-analytics:end -->
"""


class SiteAnalyticsTests(unittest.TestCase):
    def test_injection_is_stable_with_original_head_whitespace(self):
        for space in ('\n  ', '\n\n', '\t\n'):
            html = '<html><head>' + space + '<title>Original</title></head></html>'
            restored = site_analytics.with_analytics(html)
            self.assertEqual(restored, site_analytics.with_analytics(restored))
            self.assertEqual(1, restored.count(site_analytics.GOOGLE_TAG))

    def test_helper_restores_exactly_one_managed_tag(self) -> None:
        html = "<html><head>" + MANAGED + "<title>Example</title></head></html>"
        restored = site_analytics.with_analytics(html)
        self.assertEqual(1, restored.count(site_analytics.GOOGLE_TAG))
        self.assertIn(site_analytics.MEASUREMENT_ID, restored)
        self.assertEqual(restored, site_analytics.with_analytics(restored))

    def test_audit_requires_managed_tag_on_full_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "managed.html").write_text("<head>" + MANAGED + "</head>", encoding="utf-8")
            (web / "unmanaged.html").write_text("<head><title>Missing</title></head>", encoding="utf-8")
            (web / "fragment.html").write_text("<script>gtag('config', 'G-fragment')</script>", encoding="utf-8")
            (web / "clean.html").write_text("<head><title>Clean</title></head>", encoding="utf-8")
            pages, failures = site_analytics.audit(web)
        self.assertEqual(3, pages)
        self.assertEqual(["clean.html", "managed.html", "unmanaged.html"], failures)

    def test_repair_restores_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            page = web / "index.html"
            page.write_text("<head>" + MANAGED + "<title>Keep</title></head>", encoding="utf-8")
            self.assertEqual({"analytics_pages": 1}, site_analytics.repair(web))
            self.assertIn(site_analytics.GOOGLE_TAG, page.read_text(encoding="utf-8"))


class PublicationPolicyTests(unittest.TestCase):
    def test_repair_preserves_sources_and_restores_public_references(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "www"
            sources = root / "source"
            private = root / "private"
            sources.mkdir()
            for name in repair_publication_policy.REFERENCE_PATHS:
                (sources / name).write_text(f"<html>{name} supplied source</html>", encoding="utf-8")

            self.assertEqual(
                {"private_archives": 2, "privacy_page": 1, "superseded_pages": 2},
                repair_publication_policy.repair(web, private, sources),
            )
            self.assertEqual(
                {"private_archives": 0, "privacy_page": 0, "superseded_pages": 0},
                repair_publication_policy.repair(web, private, sources),
            )
            self.assertEqual([], repair_publication_policy.audit(web, private, sources))
            for name in repair_publication_policy.REFERENCE_PATHS:
                self.assertEqual(f"<html>{name} supplied source</html>", (private / name).read_text(encoding="utf-8"))
                page = (web / "ydna/glasgow-ydna-story-source/reference" / name).read_text(encoding="utf-8")
                self.assertIn(f"{name} supplied source", page)
            privacy = (web / "privacy/index.html").read_text(encoding="utf-8")
            self.assertIn("Google Analytics is used on this site", privacy)


if __name__ == "__main__":
    unittest.main()
