"""Reverse-link index (tools/build_backlinks.py) on a small fixture site."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import build_backlinks as backlinks
from tools import build_research_catalog as catalogue
from tools.public_privacy import PublicPrivacy


SHELL = """<!doctype html><html><head><title>{title} · Glasgow surname archive</title>{head}</head>
<body><aside class="g-rail"><a href="/people/smith-2.html">rail link</a></aside>
<main id="main">{main}</main><footer class="g-footer"><a href="/people/doe-3.html">footer</a></footer></body></html>"""

PEOPLE = [
    {"id": "Glasgow-1", "alternate_ids": ["Glasgow-100"], "catalogue_id": "glasgow-1", "name": "Adam Glasgow",
     "html_url": "/people/glasgow-1.html"},
    {"id": "Smith-2", "alternate_ids": [], "catalogue_id": "smith-2", "name": "Bea Smith",
     "html_url": "/people/smith-2.html"},
    {"id": "Doe-3", "alternate_ids": [], "catalogue_id": "doe-3", "name": "Cal Doe",
     "html_url": "/people/doe-3.html"},
    {"id": "Living-9", "alternate_ids": [], "catalogue_id": "living-9", "name": "Withheld Person",
     "html_url": "/people/living-9.html"},
    {"id": "Nopage-5", "alternate_ids": [], "catalogue_id": "nopage-5", "name": "No Page",
     "html_url": "/people/nopage-5.html"},
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def page(title, main, head=""):
    return SHELL.format(title=title, main=main, head=head)


def fixture(root: Path) -> dict:
    site, stories, research = root / "www", root / "stories", root / "research"
    write(site / "data/people-index.json", json.dumps(PEOPLE))
    for row in PEOPLE:
        if row["id"] != "Nopage-5":
            write(site / row["html_url"].lstrip("/"), page(row["name"], "<h1>%s</h1>" % row["name"]))
    write(site / "assets/research/branches.json", json.dumps([
        {"id": "larne", "kind": "place", "label": "Larne", "members": ["glasgow-1", "living-9"]},
        {"id": "family-smith-2", "kind": "family", "label": "Bea Smith · c. 1700",
         "description": "Records name Kilwaughter and Glasgow.", "members": ["smith-2", "glasgow-1"]},
        {"id": "scottish-families", "kind": "region", "label": "Scotland", "members": ["glasgow-1", "smith-2", "doe-3"]},
        {"id": "no-page-study", "kind": "research", "label": "Never built", "members": ["doe-3"]},
    ]))
    write(stories / "larne.json", json.dumps({
        "id": "larne", "title": "Larne & Kilwaughter",
        "clusters": [{"id": "c1", "people": ["smith-2"]}],
        "chapters": [{"body": ["No record joins [Cal Doe](/people/doe-3.html) to this family."]}],
    }))
    write(site / "branches/larne/index.html", page("Larne", "<h1>Larne &amp; Kilwaughter</h1><a href='/people/glasgow-1.html'>A</a>"))
    write(site / "branches/family-smith-2/index.html", page("Bea", "<h1>Bea Smith</h1>"))
    write(site / "branches/scottish-families/index.html", page("Scotland", "<h1>Scotland</h1>"))
    write(site / "places/index.html", page("Places", "<a href='/people/doe-3.html'>index</a>"))
    write(site / "places/kilwaughter.html", page("Kilwaughter", "<nav class='crumb'><a href='/places/'>Places</a></nav>"
          "<h1>Kilwaughter</h1><a href='../people/glasgow-1.html'>Adam</a><a href='/people/living-9.html'>x</a>"))
    write(site / "places/ayr.html", page("Ayr", "<h1>Ayr</h1><a href='/people/doe-3.html'>Cal</a>"))
    write(site / "places/glasgow.html", page("Glasgow", "<h1>Glasgow</h1>"))
    citation = lambda person, quality="original": {"person": person, "name": person, "quality": quality}
    write(site / "assets/v3/sources/s-1.json", json.dumps({"id": "s-1", "title": "1851 census, Kilwaughter",
          "citations": [citation("glasgow-1")], "records": [{"person": "smith-2"}]}))
    write(site / "assets/v3/sources/s-2.json", json.dumps({"id": "s-2", "title": "WikiTree profile export for Glasgow-1",
          "citations": [citation("glasgow-1", "tree_only")]}))
    write(site / "assets/v3/sources/s-3.json", json.dumps({"id": "s-3", "title": "Unpublished", "citations": [citation("glasgow-1")]}))
    write(site / "assets/v3/sources/s-4.json", json.dumps({"id": "s-4", "title": "../Glasgow-1/findings.md",
          "citations": [citation("glasgow-1")]}))
    for stem in ("s-1", "s-2", "s-4"):
        write(site / f"sources/{stem}/index.html", page(stem, f"<h1>{stem}</h1>"))
    findings = [{"id": f"f-{n:03d}", "found_on": "2026-01-01", "finding": f"Filler {n}.", "people": []} for n in range(55)]
    findings += [
        {"id": "newest", "found_on": "2026-10-06", "finding": "Adam leased Ballykeel in 1739. A second sentence.",
         "people": [{"id": "Glasgow-1", "name": "Adam", "url": "/people/glasgow-1.html"}]},
        {"id": "older", "found_on": "2025-05-01", "finding": "Bea married in 1720.",
         "people": [{"name": "Bea", "url": "/people/smith-2.html"}, {"id": "Glasgow-100", "name": "Adam", "url": "https://www.wikitree.com/wiki/Glasgow-100"}]},
        {"id": "bad-date", "found_on": "not a date", "finding": "Ignored.", "people": [{"id": "Glasgow-1"}]},
    ]
    write(root / "latest-findings.json", json.dumps({"findings": findings}))
    write(site / "research/subjects/topic/index.html", page("Topic", "<h1>Newspaper notes</h1><p>See Doe-3 and Living-9.</p>",
          head='<base href="../../../">'))
    write(site / "research/transcriptions/index.html", page("All", "<a href='/people/doe-3.html'>listing</a>"))
    write(site / "research/queue/old/index.html", page("Old", "<h1>Research handoff superseded</h1><a href='/people/doe-3.html'>x</a>"))
    write(site / "free-space/notes-abc/index.html", page("Notes", "<h1>Glasgow notes</h1>"
          "<a href='https://www.wikitree.com/wiki/Glasgow-100'>Adam</a><a href='people/smith-2.html'>broken relative</a>"))
    write(research / "Smith-2/findings.md", "# Smith-2\n")
    write(research / "Doe-3/findings.md", "# Doe-3\n")
    return {"site": site, "stories": stories, "ledger": root / "latest-findings.json", "research": research,
            "manifest": root / "missing-manifest.json"}


def fake_loader(identifiers):
    if identifiers[0] == "Smith-2":
        return [{"profile_id": "Smith-2", "source_path": "research/Smith-2/findings.md", "sections": [
            {"title": "Current conclusion", "category": "conclusion",
             "markdown": "Bea is not [[Glasgow-1|Adam]]'s wife. Smith-2 is herself.\n\nLiving-9 shares a household with Doe-3."},
            {"title": "Source findings", "category": "sources",
             "markdown": "A file: [notes](../Doe-3/findings.md). [Profile](https://www.wikitree.com/wiki/Glasgow-100)."},
            {"title": "Current conclusion", "category": "conclusion", "markdown": "Glasgow-1 again."},
        ]}]
    if identifiers[0] == "Doe-3":
        return [{"profile_id": "Doe-3", "source_path": "research/Doe-3/findings.md", "sections": [
            {"title": "Notes on Living-9", "category": "notes", "markdown": "Glasgow-1 appears here."},
        ]}]
    return []


def policy():
    return PublicPrivacy([("Living-9", {"BirthDate": "1990-01-01"}), ("Glasgow-1", {"DeathDate": "1800"})])


class BacklinkIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = fixture(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()
        backlinks.clear_cache()

    def build(self, **kwargs):
        p = self.paths
        options = dict(stories_dir=p["stories"], ledger=p["ledger"], research_root=p["research"],
                       cases_manifest=p["manifest"], findings_loader=fake_loader, policy=policy())
        options.update(kwargs)
        return backlinks.build(p["site"], **options)

    def test_finding_links_match_the_findings_pages(self):
        from tools.build_latest_findings import page_urls
        index = self.build()
        expected = page_urls(json.loads(self.paths["ledger"].read_text())["findings"])
        links = [entry["url"] for person in index["people"].values() for entry in person.get("findings", [])]
        self.assertTrue(links)
        for url in links:
            self.assertEqual(expected[url.split("#finding-", 1)[1]], url)

    def test_person_relations(self):
        index = self.build()
        adam = index["people"]["Glasgow-1"]
        self.assertEqual(adam["studies"], [
            {"title": "Larne & Kilwaughter", "url": "/branches/larne/"},
            {"title": "Family group: Bea Smith · c. 1700", "url": "/branches/family-smith-2/"},
        ])
        self.assertEqual(adam["places"], [{"title": "Kilwaughter", "url": "/places/kilwaughter.html"}])
        self.assertEqual([s["url"] for s in adam["sources"]], ["/sources/s-1/", "/sources/s-2/", "/sources/s-4/"])
        self.assertEqual(adam["sources_total"], 3)
        self.assertEqual(adam["findings"], [
            # Archive pages count from the earliest finding: the oldest is on page 1.
            {"date": "2026-10-06", "title": "Adam leased Ballykeel in 1739.", "url": "/latest-findings/page/2/#finding-newest"},
            {"date": "2025-05-01", "title": "Bea married in 1720.", "url": "/latest-findings/page/1/#finding-older"},
        ])
        self.assertEqual(adam["research"], [{"title": "Glasgow notes", "url": "/free-space/notes-abc/"}])
        anchor = backlinks.research_note_anchor("/research/Smith-2/findings.md", "Current conclusion")
        self.assertEqual(adam["mentioned_by"][0], {"id": "Smith-2", "name": "Bea Smith", "section": "Current conclusion",
                                                    "url": "/people/smith-2.html#" + anchor})
        self.assertEqual([m["section"] for m in adam["mentioned_by"]], ["Current conclusion", "Source findings"])

    def test_studies_separate_members_from_discussion(self):
        index = self.build()
        # Cluster member first; the story only mentions Cal to rule him out.
        self.assertEqual(index["people"]["Smith-2"]["studies"][0]["url"], "/branches/larne/")
        self.assertEqual(index["people"]["Doe-3"]["studies"], [{"title": "Larne & Kilwaughter", "url": "/branches/larne/"}])
        urls = {s["url"] for entry in index["people"].values() for s in entry.get("studies", [])}
        self.assertNotIn("/branches/scottish-families/", urls)
        self.assertNotIn("/branches/no-page-study/", urls)

    def test_chrome_listing_and_superseded_pages_are_ignored(self):
        index = self.build()
        doe = index["people"]["Doe-3"]
        self.assertEqual(doe["places"], [{"title": "Ayr", "url": "/places/ayr.html"}])
        self.assertEqual(doe["research"], [{"title": "Newspaper notes", "url": "/research/subjects/topic/"}])
        # The free-space page's relative link resolves to /free-space/notes-abc/people/... and is not a person.
        self.assertNotIn("research", index["people"]["Smith-2"])

    def test_mentions_exclude_self_links_to_files_and_withheld_sections(self):
        index = self.build()
        smith = index["people"].get("Smith-2", {})
        self.assertNotIn("mentioned_by", smith)  # only mentions herself
        doe = index["people"]["Doe-3"]
        # The paragraph naming a living person is withheld, so Doe-3 is not mentioned; the file link never counts.
        self.assertNotIn("mentioned_by", doe)
        adam = index["people"]["Glasgow-1"]
        self.assertEqual({m["id"] for m in adam["mentioned_by"]}, {"Smith-2"})  # Doe-3's heading names a living person

    def test_without_privacy_screen_paragraph_mentions_count(self):
        index = self.build(policy=None)
        self.assertEqual({m["id"] for m in index["people"]["Doe-3"]["mentioned_by"]}, {"Smith-2"})
        self.assertIn("Living-9", index["people"])

    def test_withheld_person_never_enters_the_index(self):
        index = self.build()
        text = backlinks.serialise(index)
        self.assertNotIn("Living-9", text)
        self.assertNotIn("living-9", text)
        self.assertEqual(index["counts"]["people_withheld_skipped"], 1)
        self.assertNotIn("Nopage-5", text)

    def test_study_place_cross_links(self):
        index = self.build()
        larne = index["pages"]["/branches/larne/"]
        self.assertEqual(larne["places"][0], {"title": "Kilwaughter", "url": "/places/kilwaughter.html",
                                              "shared_people": 1, "via": ["named-in-study-text", "shared-people"]})
        family = index["pages"]["/branches/family-smith-2/"]
        self.assertEqual([p["url"] for p in family["places"]], ["/places/kilwaughter.html"])  # "Glasgow" is a stop word
        kilwaughter = index["pages"]["/places/kilwaughter.html"]
        self.assertEqual([s["url"] for s in kilwaughter["studies"]], ["/branches/family-smith-2/", "/branches/larne/"])
        self.assertEqual(kilwaughter["studies_total"], 2)
        # Cal is only discussed by the Larne study, so Ayr shares no member with it.
        self.assertNotIn("/places/ayr.html", index["pages"])
        self.assertEqual([p["url"] for p in larne["places"]], ["/places/kilwaughter.html"])

    def test_output_is_deterministic(self):
        self.assertEqual(backlinks.serialise(self.build()), backlinks.serialise(self.build()))

    def test_load_person_links_shape_alias_and_missing_index(self):
        out = Path(self.tmp.name) / "person-links.json"
        out.write_text(backlinks.serialise(self.build()), encoding="utf-8")
        with mock.patch.object(backlinks, "INDEX_PATH", out):
            backlinks.clear_cache()
            adam = backlinks.load_person_links("Glasgow-1")
            self.assertEqual(set(adam), set(backlinks.empty_person_links()))
            self.assertEqual(backlinks.load_person_links("glasgow-100"), adam)
            adam["studies"].clear()
            self.assertTrue(backlinks.load_person_links("Glasgow-1")["studies"])  # cached copy unchanged
            self.assertEqual(backlinks.load_person_links("Unknown-1"), backlinks.empty_person_links())
            self.assertEqual(backlinks.load_page_links("/places/kilwaughter.html")["studies"][1]["url"], "/branches/larne/")
            self.assertEqual(backlinks.load_page_links("/places/none.html"), {})
        with mock.patch.object(backlinks, "INDEX_PATH", Path(self.tmp.name) / "absent.json"):
            backlinks.clear_cache()
            self.assertEqual(backlinks.load_person_links("Glasgow-1"), backlinks.empty_person_links())

    def test_published_sections_only_through_catalogue_loader(self):
        root = Path(self.tmp.name)
        notes = root / "repo/research"
        write(notes / "Smith-2/findings.md", "# Smith-2\n\n## Current conclusion\n\nBea is not Glasgow-1's wife.\n\n"
              "## Website synchronisation\n\nDoe-3 page refreshed.\n")
        with mock.patch.object(catalogue, "RESEARCH_DIR", notes), mock.patch.object(catalogue, "PROJECT_ROOT", root / "repo"):
            index = self.build(findings_loader=None, research_root=notes)
        self.assertEqual([m["section"] for m in index["people"]["Glasgow-1"]["mentioned_by"]], ["Current conclusion"])
        self.assertNotIn("mentioned_by", index["people"]["Doe-3"])

    def test_anchor_matches_person_page_renderer(self):
        try:
            from tools.repair_person_hierarchy import _research_note_anchor
        except Exception as error:  # pragma: no cover - renderer unavailable
            self.skipTest(f"renderer not importable: {error}")
        self.assertEqual(backlinks.research_note_anchor("/research/X-1/findings.md", "Source findings"),
                         _research_note_anchor("/research/X-1/findings.md", "Source findings"))


if __name__ == "__main__":
    unittest.main()
