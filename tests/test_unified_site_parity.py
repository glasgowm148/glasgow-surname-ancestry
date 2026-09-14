import importlib.util
import json
from collections import Counter
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
OLD = ROOT / "www_old"


@unittest.skipUnless(OLD.is_dir(), "www_old migration reference is not present")
class UnifiedSiteParityTests(unittest.TestCase):
    def test_migration_parity_audit(self):
        spec = importlib.util.spec_from_file_location(
            "repair_unified_site", ROOT / "tools/repair_unified_site.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        summary, failures = module.audit()
        self.assertEqual([], failures)
        self.assertEqual(4564, summary["person_metadata"])
        self.assertEqual(71, summary["profile_workbenches"])
        self.assertEqual(62, summary["profile_drafts"])
        self.assertEqual(65, summary["profile_status_controls"])
        self.assertEqual(0, summary["missing_routes"])
        self.assertEqual(0, summary["missing_fragments"])
        self.assertGreater(summary["internal_routes"], 700_000)

    def test_primary_catalogue_includes_complete_search(self):
        page = (WEB / "catalogue/index.html").read_text(encoding="utf-8")
        required = (
            "catalogue-exact-name",
            "catalogue-first-name",
            "catalogue-last-name",
            "catalogue-spouse-name",
            "catalogue-father-name",
            "catalogue-mother-name",
            "catalogue-cluster",
            "catalogue-record-type",
            "catalogue-source-quality",
            "catalogue-date-type",
            "catalogue-location-type",
            "catalogue-death-exclude",
            "catalogue-missing-father",
            "catalogue-missing-mother",
            "catalogue-missing-profile",
            "catalogue-needs-wikitree-update",
            "catalogue-results",
            "statistics-detail",
        )
        for marker in required:
            self.assertIn(f'id="{marker}"', page)
        self.assertIn('src="people/search.js?', page)
        self.assertIn(
            "restoreResultsAnchor=location.hash==='#catalogue-results'",
            (WEB / "people/search.js").read_text(encoding="utf-8"),
        )
        self.assertNotIn("Original detailed catalogue export", page)
        self.assertNotIn('href="/?', page)

    def test_ui_regression_repairs_are_durable(self):
        fragment_marker = 'location.href.split("#")[0]'
        person = (WEB / "people/glasgow-951.html").read_text(encoding="utf-8")
        timeline = (WEB / "timeline/index.html").read_text(encoding="utf-8")
        self.assertIn(fragment_marker, person)
        self.assertIn(fragment_marker, timeline)
        self.assertIn('href="#research"', person)
        self.assertIn('href="#R-U106"', timeline)
        self.assertIn("position:sticky", (WEB / "assets/unified/sections.css").read_text(encoding="utf-8"))

        home_js = (WEB / "assets/research/home.js").read_text(encoding="utf-8")
        self.assertIn("new ResizeObserver(draw).observe(canvas)", home_js)
        self.assertNotIn("R.previewPerson(", home_js)
        css = (WEB / "assets/repair/site.css").read_text(encoding="utf-8")
        self.assertIn(".v3-dossier>.v3-evidence-fold", css)
        atlas = (WEB / "onetree/index.html").read_text(encoding="utf-8")
        self.assertIn('class="repair-atlas-project-links"', atlas)
        for href in ('href="/"', 'href="/catalogue/"', 'href="/map/"', 'href="/timeline/"'):
            self.assertIn(href, atlas)
        for relative in ("assets/research/atlas.js", "assets/research/atlas-standalone.html"):
            atlas_script = (WEB / relative).read_text(encoding="utf-8")
            self.assertIn("replace(/^@geo-/,'')", atlas_script)
            self.assertIn("geoMap.get(geoKey(h.id))", atlas_script)
            self.assertIn("state.geo=id==='all'?null:geoKey(id)", atlas_script)

    def test_british_isles_map_uses_detailed_offline_geometry(self):
        detail = json.loads(
            (WEB / "assets/repair/british-isles-50m.json").read_text(encoding="utf-8")
        )
        self.assertIn("Natural Earth 1:50m", detail["source"])
        self.assertEqual(2, len(detail["countries"]))
        ireland = detail["countries"][1]
        points = [point for polygon in ireland for ring in polygon for point in ring]
        self.assertGreater(len(points), 300)
        self.assertLess(min(point[0] for point in points), -10.3)
        self.assertGreater(max(point[1] for point in points), 55.3)
        map_js = (WEB / "assets/research/map.js").read_text(encoding="utf-8")
        self.assertIn("british-isles-50m.json", map_js)
        self.assertIn("coarseBritish", map_js)
        self.assertIn("1:50m British Isles detail", (WEB / "map/index.html").read_text(encoding="utf-8"))

    def test_record_citation_counts(self):
        source = json.loads((WEB / "data/records-index.json").read_text(encoding="utf-8"))
        compact = json.loads((WEB / "assets/research/record-index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            Counter(row["supporting_source_status"] for row in source),
            Counter(row["citation"] for row in compact),
        )
        page = (WEB / "records/index.html").read_text(encoding="utf-8")
        worker = (WEB / "assets/research/search-worker.js").read_text(encoding="utf-8")
        self.assertIn('id="r-record-citation"', page)
        self.assertIn("Download the source-review queue", page)
        self.assertIn("category.split(' | ').includes", worker)
        self.assertIn("flatMap(r=>r.category.split(' | '))", worker)

    def test_free_space_directory_and_search(self):
        source = json.loads((ROOT / "research/free-space-pages/index.json").read_text(encoding="utf-8"))
        rows = json.loads((WEB / "assets/research/free-space-index.json").read_text(encoding="utf-8"))
        expected_ids = {row["wikitreeId"] for row in source["pages"]}
        self.assertEqual(72, len(source["pages"]))
        self.assertEqual(71, len(expected_ids))
        self.assertTrue(expected_ids.issubset({row["wikitreeId"] for row in rows}))
        self.assertEqual(85, len(rows))
        self.assertTrue(all(row["viewUrl"].startswith("https://www.wikitree.com/wiki/Space:") for row in rows))
        self.assertTrue(all(not ({"localFile", "editUrl", "capturedUrl", "sourceLength"} & set(row)) for row in rows))
        directory = (WEB / "free-space/index.html").read_text(encoding="utf-8")
        self.assertEqual(85, directory.count('class="fsp-card"'))
        self.assertIn("14 individual bearer pages recorded as verified live", directory)
        self.assertIn("Free-space pages are research resources and are not person profiles", directory)
        self.assertNotIn("research/free-space-pages/", directory)
        self.assertIn('/free-space/', (WEB / "index.html").read_text(encoding="utf-8"))
        research = (WEB / "research/index.html").read_text(encoding="utf-8")
        self.assertIn('/free-space/', research)
        self.assertIn('/free-space/', research)
        self.assertIn('/compare/', research)
        self.assertIn("free-space-index.json", (WEB / "assets/research/search-worker.js").read_text(encoding="utf-8"))
        self.assertIn("free-space-index.json", (WEB / "assets/unified/site.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
