"""The shared evidence vocabulary and the pages generated from it."""
from pathlib import Path
import json
import re
import unittest

from bs4 import BeautifulSoup

from tools import evidence_labels as ev

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_KEYS = {"proved", "strongly_supported", "probable", "possible", "disputed", "contradicted",
                  "dna_confirmed", "confident", "uncertain", "non_biological", "unmarked"}


class VocabularyTests(unittest.TestCase):
    def test_every_catalogue_key_has_a_distinct_text_label(self):
        self.assertLessEqual(CATALOGUE_KEYS, set(ev.STATES))
        labels = [ev.STATES[key]["label"] for key in ev.STATES]
        self.assertEqual(len(labels), len(set(labels)), "labels must be distinguishable without colour")
        for key, state in ev.STATES.items():
            with self.subTest(key=key):
                self.assertTrue(state["label"].strip())
                self.assertTrue(state["meaning"].strip())
                self.assertTrue(state["glyph"].strip())

    def test_labels_do_not_overstate(self):
        documented = [key for key, state in ev.STATES.items() if "document" in state["label"].casefold()]
        self.assertEqual(["proved"], documented)
        self.assertEqual("Possible", ev.label("possible"))
        self.assertIn("unassessed", ev.label("unmarked").casefold())
        for key in ("dna_confirmed", "confident", "non_biological"):
            self.assertTrue(ev.label(key).startswith("Tree-marked"), key)
        self.assertEqual("Documented", ev.study_label("proved"))
        self.assertNotIn("Proved", {value["label"] for value in ev.STUDY_TONES.values()})

    def test_aliases_and_tree_status_codes(self):
        self.assertEqual("unmarked", ev.canonical_key("unknown"))
        self.assertEqual("unmarked", ev.canonical_key(None))
        self.assertEqual("dna_confirmed", ev.canonical_key("DNA-confirmed"))
        self.assertEqual("dna_confirmed", ev.canonical_key("30"))
        self.assertEqual("non_biological", ev.canonical_key("non-biological"))
        self.assertEqual("unmarked", ev.canonical_key("something new"))

    def test_relationship_labels_follow_state(self):
        self.assertEqual("Documented child", ev.relationship_label("proved", "child"))
        self.assertEqual("Strongly supported son", ev.relationship_label("strongly_supported", "son"))
        self.assertEqual("Probable father", ev.relationship_label("probable", "father"))
        self.assertEqual("Contradicted son link", ev.relationship_label("contradicted", "son"))
        self.assertEqual("Unassessed partner link", ev.relationship_label("unknown", "spouse"))

    def test_normalisation_never_upgrades_and_is_idempotent(self):
        cases = {
            ("contradicted", "Possible son"): "Contradicted son link",
            ("probable", "Possible father"): "Probable father",
            ("strongly_supported", "Strongly identified mother"): "Strongly supported mother",
            ("strongly_supported", "Tree relationship"): "Strongly supported spouse",
            ("unknown", "Tree relationship"): "Unassessed partner link",
            ("unknown", "Unassessed sibling link"): "Unassessed sibling link",
            ("unknown", "Documented child"): "Unassessed child link",
            ("possible", "Open father hypothesis"): "Possible · Open father hypothesis",
            ("probable", "Probable; 1892 citation and will"): "Probable; 1892 citation and will",
            ("uncertain", "Relationship unresolved"): "Uncertain · Relationship unresolved",
        }
        for (state, text), expected in cases.items():
            with self.subTest(state=state, text=text):
                result = ev.normalise_status_label(state, text)
                self.assertEqual(expected, result)
                self.assertEqual(result, ev.normalise_status_label(state, result))

    def test_json_mirror_matches_module(self):
        mirror = ROOT / "www/assets/research/evidence-labels.json"
        self.assertEqual(ev.json_text(), mirror.read_text(encoding="utf-8"))
        data = json.loads(mirror.read_text(encoding="utf-8"))
        self.assertEqual("/evidence/", data["guide"]["url"])
        self.assertEqual({key: value["label"] for key, value in ev.STATES.items()},
                         {key: value["label"] for key, value in data["states"].items()})


class EvidencePageTests(unittest.TestCase):
    def test_page_generation_is_idempotent_and_keeps_the_rail(self):
        from tools import build_evidence_page as builder
        template = builder.TEMPLATE.read_text(encoding="utf-8")
        page = builder.render(template)
        self.assertEqual(page, builder.render(template))
        self.assertEqual(builder.nav_rail(template), builder.nav_rail(page))
        # Asset ?v= values are content hashes owned by tools/stamp_asset_versions.py.
        unversioned = lambda text: __import__("re").sub(r"\?v=[^\"'\s<>]+", "?v=", text)
        self.assertEqual(unversioned(page), unversioned(builder.OUTPUT.read_text(encoding="utf-8")))

    def test_page_explains_every_label_and_the_cluster_warning(self):
        soup = BeautifulSoup((ROOT / "www/evidence/index.html").read_text(encoding="utf-8"), "html.parser")
        main = soup.select_one("main")
        self.assertEqual("How to read the evidence", main.select_one("h1").get_text(strip=True))
        text = main.get_text(" ", strip=True)
        for state in ev.STATES.values():
            self.assertIn(state["label"], text)
        for quality in ev.RECORD_QUALITY.values():
            self.assertIn(quality["label"], text)
        self.assertIn("does not prove", text)
        self.assertIn("Estimated", text)
        self.assertIn(ev.NOT_YET_IDENTIFIED, text)
        self.assertEqual(1, len(soup.select('link[href^="/assets/research/evidence.css"]')))
        self.assertEqual(1, len(soup.select("nav.g-nav")))


class PublishedSurfaceTests(unittest.TestCase):
    def test_dossier_labels_are_canonical_and_linked_to_the_guide(self):
        soup = BeautifulSoup((ROOT / "www/people/glasgow-951.html").read_text(encoding="utf-8"), "html.parser")
        family = soup.select_one("#family")
        self.assertTrue(family.select_one('a[href="/evidence/"]'))
        for row in family.select("tr[data-state]"):
            label = row.select_one(".status-label").get_text()
            self.assertEqual(ev.normalise_status_label(row["data-state"], label), label)
            self.assertNotIn("Strongly identified", label)
        self.assertTrue(soup.select_one('link[href^="/assets/research/evidence.css"]'))
        self.assertTrue(soup.select_one('.dossier-meta a.dossier-evidence-guide[href="/evidence/"]'))

    def test_dossier_generator_and_repair_add_the_header_guide_once(self):
        from tools import repair_evidence_labels as repair
        from tools import repair_person_hierarchy as dossiers
        self.assertIn('href="/evidence/"', dossiers.DOSSIER_GUIDE_META)
        page = '<div class="dossier-meta"><span>Research assessment: <time>2026</time></span></div>'
        once = repair.add_meta_guide(page)
        self.assertEqual(1, once.count('dossier-evidence-guide'))
        self.assertEqual(once, repair.add_meta_guide(once))

    def test_open_research_tasks_show_resolution_fields(self):
        soup = BeautifulSoup((ROOT / "www/people/glasgow-951.html").read_text(encoding="utf-8"), "html.parser")
        tasks = soup.select('#research li.task[data-question-status="open"]')
        self.assertTrue(tasks)
        for task in tasks:
            terms = [dt.get_text(strip=True) for dt in task.select(".question-actions dt")]
            self.assertEqual(list(ev.QUESTION_FIELDS.values()), terms)
            self.assertTrue(task.select_one(".question-status"))

    def test_research_page_questions_never_leave_fields_blank(self):
        soup = BeautifulSoup((ROOT / "www/research/index.html").read_text(encoding="utf-8"), "html.parser")
        section = soup.select_one("#open-questions")
        blocks = section.select(".question-actions")
        self.assertEqual(13, len(blocks))
        for block in blocks:
            values = [dd.get_text(strip=True) for dd in block.select("dd")]
            self.assertEqual(2, len(values))
            self.assertTrue(all(values))
        self.assertIn(ev.NOT_YET_IDENTIFIED, section.get_text())

    def test_study_pages_use_canonical_tones_and_link_the_guide(self):
        page = (ROOT / "www/branches/larne-kilwaughter/index.html").read_text(encoding="utf-8")
        soup = BeautifulSoup(page, "html.parser")
        self.assertTrue(soup.select_one('main a[href="/evidence/"]'))
        keys = [node.get_text(strip=True) for node in soup.select(".sp-key")]
        if keys:
            self.assertEqual([value["label"] for value in ev.STUDY_TONES.values()], keys)
        self.assertNotIn(">Proved<", page)

    def test_atlas_uses_canonical_tree_marks(self):
        script = (ROOT / "www/assets/research/atlas.js").read_text(encoding="utf-8")
        match = re.search(r"const EVIDENCE_MARKS=(\{[^}]*\});", script)
        self.assertIsNotNone(match)
        marks = json.loads(match[1])
        self.assertEqual(ev.label("unmarked"), marks["unmarked"])
        self.assertEqual(ev.label("dna_confirmed"), marks["DNA-confirmed"])
        self.assertIn('href="/evidence/"', script)


if __name__ == "__main__":
    unittest.main()
