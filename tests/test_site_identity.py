"""Site identity, correction route, breadcrumb, totals and housekeeping (site audit lane I5)."""
from pathlib import Path
import json
import re
import tempfile
import unittest
from unittest import mock

from tools import about_pages, deploy_site, repair_dna_navigation, repair_reader_guidance, site_identity
from tools import repair_primary_navigation as nav
from tools.site_sitemap import sitemap_entries

ROOT = Path(__file__).resolve().parents[1]
HEALTH = {
    "status": "ok", "generated": "2026-09-27", "source_export": "ONT_Glasco_2026-08-18T16_05.json",
    "counts": {"people": 4800, "records": 4877, "places": 1264, "substantive_findings_files": 757,
               "possible_duplicate_comparisons": 26},
    "source_links": {"unresolved": 3675, "candidate": 1189, "explicit": 13},
}
SHELL = """<!doctype html><html><head><title>{title}</title><meta name="description" content="x"></head>
<body><aside aria-label="Glasgow archive" class="g-rail" id="g-navigation"><a aria-label="Glasgow archive home" class="g-brand" href="/">
<span class="g-brand-copy"><span class="g-brand-name">GLASGOW</span><span class="g-brand-caption">The surname archive</span></span></a>
<nav class="g-nav" aria-label="Main navigation"></nav><div class="repair-quick-links"><a href="/branches/">Families &amp; places →</a><a href="/connections/">Find a connection →</a><a href="/early-records/">Early records →</a></div><div class="g-rail-bottom"><a href="/coverage/">Coverage &amp; method</a><a href="/data/">Data &amp; downloads</a><a href="/about/">About this research</a><div class="v3-rail-note"><span>A living surname archive</span><p>People, places</p></div></div></aside>
<div class="g-bar"><div class="g-crumbs"><a href="/">Glasgow archive</a><i>/</i><strong>{crumb}</strong></div></div>
<main id="main"><nav class="crumb"><a href="/catalogue/">People</a> / {crumb}</nav><h1>{crumb}</h1></main>
<footer class="g-footer"><div><span class="g-footer-name">The Glasgow Surname Project</span></div><nav class="g-footer-links" aria-label="Project information"><a href="/changes/">Latest research</a><a href="/feedback/">Suggest a correction ↗</a></nav></footer></body></html>"""


class SiteNameTests(unittest.TestCase):
    def test_every_legacy_title_suffix_becomes_the_one_site_name(self):
        cases = {
            "Research resources · Glasgow surname archive": "Research resources · Glasgow Surname Project",
            "Sources · Glasgow Sources": "Sources · Glasgow Surname Project",
            "Census 1851 · Glasgow source library": "Census 1851 · Source library · Glasgow Surname Project",
            "Y-DNA Timeline | The Glasgow Surname Project": "Y-DNA Timeline · Glasgow Surname Project",
            "The earliest Glasgow records · Glasgow": "The earliest Glasgow records · Glasgow Surname Project",
            "John Glasgow - Glasgow archive": "John Glasgow · Glasgow Surname Project",
            "Alexander Glasgow · Glasgow Surname Project": "Alexander Glasgow · Glasgow Surname Project",
            "Jane Smith-Glasgow": "Jane Smith-Glasgow · Glasgow Surname Project",
            "Root-Based Clusters": "Root-Based Clusters · Glasgow Surname Project",
            "Glasgow": "Glasgow Surname Project",
        }
        for title, expected in cases.items():
            self.assertEqual(site_identity.normalise_title(title), expected, title)
            self.assertEqual(site_identity.normalise_title(expected), expected, expected)

    def test_page_title_skips_a_repeated_section(self):
        self.assertEqual(site_identity.page_title("Statistics", "About"), "Statistics · About · Glasgow Surname Project")
        self.assertEqual(site_identity.page_title("Sources", "Sources"), "Sources · Glasgow Surname Project")

    def test_owned_builders_no_longer_print_earlier_site_names(self):
        owned = ("build_statistics_page.py", "build_resources_page.py", "free_space_edition.py",
                 "publish_research_access.py", "publish_testament_reviews.py", "repair_dna_navigation.py",
                 "build_research_subject_drafts.py", "site_sources/ydna_story/shell.html")
        for name in owned:
            text = (ROOT / "tools" / name).read_text(encoding="utf-8")
            for legacy in ("Glasgow surname archive", "The surname archive", "living surname archive"):
                self.assertNotIn(legacy, text, f"{name}: {legacy}")

    def test_handoff_builders_read_the_one_site_name(self):
        # Builders moved onto site_identity by the hand-off sweep (lane I8).
        swept = ("build_source_collections.py", "repair_sources_page.py", "build_evidence_page.py",
                 "build_transcriptions.py", "add_research_case_dossiers.py", "repair_research_groups.py",
                 "site_search.py", "repair_publication_policy.py", "reconcile_retired_record_subjects.py",
                 "site_sources/ydna_story/build.py", "site_sources/ydna_story/curated-page.html")
        for name in swept:
            text = (ROOT / "tools" / name).read_text(encoding="utf-8")
            for legacy in ("Glasgow surname archive", "The surname archive", "living surname archive",
                           "Glasgow archive", "Glasgow Sources", "Glasgow source library", "Source library · Glasgow<"):
                self.assertNotIn(legacy, text, f"{name}: {legacy}")


class OwnerAndCorrectionTests(unittest.TestCase):
    def test_unset_owner_and_contact_print_honest_text_and_no_dead_link(self):
        with mock.patch.object(site_identity, "OWNER_NAME", None), mock.patch.object(site_identity, "CONTACT_URL", None):
            who = site_identity.who_runs_this_html()
            self.assertIn("Who runs this site", who)
            self.assertIn("not yet published", who)
            self.assertIn("being set up", who)
            self.assertIn('href="/feedback/"', site_identity.contact_link_html())
            body = about_pages.render_feedback_body()
            self.assertNotIn('href="#"', body)
            self.assertIn("Report a correction", body)
            self.assertIn('id="feedback-template"', body)
            self.assertIn('<a id="feedback-wikitree" class="button" hidden>', body)
            self.assertIn("being set up", body)

    def test_set_owner_and_contact_publish_the_route(self):
        with mock.patch.object(site_identity, "OWNER_NAME", "A. Researcher"), \
                mock.patch.object(site_identity, "CONTACT_URL", "mailto:corrections@example.org"):
            self.assertIn("run by A. Researcher", site_identity.who_runs_this_html())
            self.assertIn('href="mailto:corrections@example.org">Send a correction</a>', site_identity.contact_link_html())
            body = about_pages.render_feedback_body()
            self.assertIn('Email it to <a href="mailto:corrections@example.org">corrections@example.org</a>.', body)
            self.assertIn('href="mailto:corrections@example.org">Send a correction</a>', body)
            self.assertNotIn("being set up", body)
            footer = site_identity.footer_html()
            self.assertIn("run by A. Researcher", footer)
            self.assertIn('href="mailto:corrections@example.org"', footer)

    def test_a_form_contact_route_is_not_described_as_email(self):
        with mock.patch.object(site_identity, "OWNER_NAME", "A. Researcher"), \
                mock.patch.object(site_identity, "CONTACT_URL", "https://forms.example.org/correct"):
            self.assertIsNone(site_identity.contact_email())
            body = about_pages.render_feedback_body()
            self.assertIn('Send it with <a href="https://forms.example.org/correct"', body)
            self.assertNotIn("Email it to", body)

    def test_footer_agrees_with_the_menu(self):
        footer = site_identity.footer_html()
        self.assertIn('<a href="/changes/">Change log</a>', footer)
        self.assertIn('<a href="/latest-findings/">Latest findings</a>', footer)
        self.assertIn('<a href="/privacy/">Privacy</a>', footer)
        self.assertIn('<a href="/evidence/">How to read the evidence</a>', footer)
        self.assertNotIn("Latest research", footer)
        for internal in re.findall(r'<a href="/[^"]*">([^<]*)</a>', footer):
            self.assertNotIn("↗", internal)
            self.assertNotIn("&nearr;", internal)

    def test_reader_html_placeholders_are_all_filled(self):
        source = ROOT / "tools/site_sources/reader_guidance"
        for name in ("home-intro.html", "home-start.html", "about-intro.html"):
            filled = repair_reader_guidance.fill_identity((source / name).read_text(encoding="utf-8"), HEALTH)
            self.assertNotIn("<!-- site-", filled, name)
            self.assertNotIn("<!-- people-total", filled, name)
            self.assertNotIn("<!-- correction-link", filled, name)
            self.assertNotIn("<!-- who-runs-this", filled, name)
        home = repair_reader_guidance.fill_identity((source / "home-intro.html").read_text(encoding="utf-8"), HEALTH)
        self.assertIn("<h1 id=\"home-title\">Glasgow Surname Project</h1>", home)
        self.assertIn("Search 4,800 people", home)
        self.assertEqual(3, home.count('class="reader-way"'))
        self.assertIn('href="/evidence/"', home)


class NavigationTests(unittest.TestCase):
    def test_identity_pass_gives_one_name_one_breadcrumb_and_shared_footer(self):
        page = SHELL.format(title="Alexander Glasgow · Glasgow surname archive", crumb="Alexander Glasgow")
        result = nav.repair_site_identity_page(page, Path("people/glasgow-951.html"))
        self.assertIn("<title>Alexander Glasgow · Glasgow Surname Project</title>", result)
        self.assertIn('<meta property="og:site_name" content="Glasgow Surname Project">', result)
        self.assertIn('<span class="g-brand-caption">Surname Project</span>', result)
        self.assertIn('aria-label="Glasgow Surname Project home"', result)
        self.assertIn('<div class="g-crumbs"><a href="/">Home</a><i>/</i><a class="g-crumb-section" href="/catalogue/">People</a><i>/</i><strong>Alexander Glasgow</strong></div>', result)
        self.assertNotIn('<nav class="crumb"', result)
        self.assertNotIn("surname archive", result)
        self.assertNotIn("Glasgow archive", result)
        self.assertNotIn('href="/early-records/">Early records', result)
        self.assertIn('href="/connections/">Find a connection', result)
        self.assertNotIn("Latest research", result)
        self.assertEqual(result, nav.repair_site_identity_page(result, Path("people/glasgow-951.html")))

    def test_breadcrumb_levels(self):
        self.assertEqual(nav.render_breadcrumbs(Path("index.html"), "Home"), '<div class="g-crumbs"><strong>Home</strong></div>')
        self.assertNotIn("g-crumb-section", nav.render_breadcrumbs(Path("research/index.html"), "Research questions"))
        self.assertIn('href="/about/">About</a>', nav.render_breadcrumbs(Path("statistics/index.html"), "Statistics"))
        self.assertIn('href="/branches/">Families &amp; places</a>', nav.render_breadcrumbs(Path("places/kilwaughter.html"), "Kilwaughter"))

    def test_redirect_stubs_are_left_alone(self):
        stub = '<html data-clean-route-redirect><head><title>Redirecting</title></head><body></body></html>'
        self.assertEqual(stub, nav.repair_site_identity_page(stub, Path("timeline.html")))

    def test_dna_branch_pages_are_linked_from_the_overview(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            for slug, title in (("r-ft20271", "R-FT20271 · The Scots-Irish cluster · Glasgow surname archive"),
                                ("r-s14827", "R-S14827 · A linked genetic branch · Glasgow surname archive")):
                (web / "dna" / slug).mkdir(parents=True)
                (web / "dna" / slug / "index.html").write_text(f"<title>{title}</title>", encoding="utf-8")
            view = repair_dna_navigation.with_branch_pages('<section id="dna-overview"><h1>x</h1></section>', web)
            self.assertIn('href="/dna/r-ft20271/"><strong>R-FT20271</strong> · The Scots-Irish cluster</a>', view)
            self.assertIn('href="/dna/r-s14827/"', view)
            self.assertTrue(view.endswith("</section></section>"))
            self.assertEqual(view, repair_dna_navigation.remove_overview_views(view) or view)


class TotalsTests(unittest.TestCase):
    def test_status_reads_health_and_hides_the_export_file_name(self):
        body = about_pages.render_status_body(HEALTH)
        self.assertIn("<h1>Catalogue status</h1>", body)
        self.assertIn("4,800</strong><span>People in the index", body)
        self.assertIn("the WikiTree export of 18 August 2026", body)
        self.assertIn("27 September 2026", body)
        self.assertNotIn("ONT_Glasco", body)
        self.assertNotIn("provenance", body.lower())
        self.assertIn('href="/changes/"', body)
        self.assertIn("3,675 still need their source added", body)

    def test_about_and_coverage_use_the_same_totals(self):
        about = '<table><tr><td>Research catalogue</td><td>4,797 people · 4,877 record associations · 1,264 places</td></tr></table>'
        intro = '<header class="g-editorial-hero"><h1>x</h1></header><div class="g-section-heading">'
        about = repair_reader_guidance.about_page('<title>x</title>' + intro + about, HEALTH)
        self.assertIn("<td>4,800 people · 4,877 record entries linked to people · 1,264 places</td>", about)
        coverage = ('<span class="r-kicker">Coverage &amp; method</span><h1>What is here.<br>And what it means.</h1>'
                    '<div class="r-grid2 r-section"><div><strong class="r-coverage-number">4,564</strong><p>Catalogue entries</p></div>'
                    '<div><strong class="r-coverage-number">4,430</strong><p>Public atlas profiles</p></div>'
                    '<div><strong class="r-coverage-number">4,758</strong><p>Record associations</p></div>'
                    '<div><strong class="r-coverage-number">4,355</strong><p>Mapped associations</p></div></div>'
                    '<section class="r-section"><h2>Why the page totals differ</h2><p>The people index contains <strong>4,564 entries</strong>. '
                    'The family tree contains <strong>4,430 public profile IDs</strong>; <strong>4,428</strong> catalogue entries map directly to those identities.</p>'
                    '<p>The geography contains <strong>4,355</strong> associations with a matched supplied coordinate. The other <strong>403</strong> remain searchable.</p></section>')
        once = repair_reader_guidance.coverage_totals(coverage, HEALTH)
        self.assertNotIn("4,564", once)
        self.assertIn("4,800</strong><p>People in the index", once)
        self.assertIn("4,430</strong><p>Family-tree profiles (counted 8 September 2026)", once)
        self.assertIn("of which <strong>4,428</strong> matched", once)
        self.assertIn("<h1>About the data</h1>", once)
        self.assertEqual(once, repair_reader_guidance.coverage_totals(once, HEALTH))


class HousekeepingTests(unittest.TestCase):
    def test_build_reports_and_bundles_are_never_published(self):
        for name in ("dossier-release.json", "integration-report.json", "glasgow-site-20261005-001143.tar.gz", ".x.tmp"):
            self.assertTrue(deploy_site.is_excluded(Path(name)), name)
        self.assertFalse(deploy_site.is_excluded(Path("health.json")))
        self.assertFalse(deploy_site.is_excluded(Path("data/dossier-release.json")))
        command = deploy_site.rsync_command(Path("www"), "alice@example.test:/var/www/site")
        self.assertIn("/integration-report.json", command)

    def test_bundle_is_written_outside_the_web_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "www"
            root.mkdir()
            (root / "index.html").write_text("ok", encoding="utf-8")
            with mock.patch.object(deploy_site, "validate_release_tree"):
                archive = deploy_site.make_bundle(root)
            self.assertEqual(archive.parent, Path(directory) / "dist")
            self.assertFalse(any(root.glob("*.tar.gz")))

    def test_sitemap_lists_source_browse_and_dna_pages_and_leaves_out_workroom_pages(self):
        page = '<!doctype html><html><head><title>{0}</title></head><body>{0}</body></html>'
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for route in ("sources/census/scotland/index.html", "sources/s-0123456789abcdef/index.html",
                          "dna/r-ft20271/index.html", "explore/index.html", "research/queue/draft-1/index.html",
                          "research/index.html", "research/tools.html"):
                (site / route).parent.mkdir(parents=True, exist_ok=True)
                (site / route).write_text(page.format(route), encoding="utf-8")
            (site / "assets/v3").mkdir(parents=True)
            (site / "assets/v3/source-index.json").write_text("[]", encoding="utf-8")
            entries = sitemap_entries(site)
            self.assertIn("/sources/census/scotland/", entries)
            self.assertIn("/dna/r-ft20271/", entries)
            self.assertIn("/research/", entries)
            for route in ("/sources/s-0123456789abcdef/", "/explore/", "/research/queue/draft-1/", "/research/tools.html"):
                self.assertNotIn(route, entries)


if __name__ == "__main__":
    unittest.main()
