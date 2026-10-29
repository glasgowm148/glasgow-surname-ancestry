"""The standing check that research written in findings.md reaches the site.

Each test builds a small research tree in a temporary folder and runs
tools/check_research_publication.py against it.
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import build_research_catalog as catalog
from tools import check_research_publication as check

CONCLUSION = "## Current conclusion\n\nJohn was a weaver in Rasharkin; the 1841 entry names him.\n"


class Tree:
    def __init__(self, root: Path):
        self.root = root
        for folder in ("research", "www/people", "www/data", "data/wikitree", "data/site", "surname-research"):
            (root / folder).mkdir(parents=True, exist_ok=True)
        self.people = []
        self.cases = {}
        self.write("surname-research/to-update.md", "# WikiTree work queue\n")
        self.write("data/wikitree/profile-update-queue.json", json.dumps({"include_open_register": True, "entries": {}}))

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def findings(self, ident: str, text: str, page: bool = True) -> None:
        self.write(f"research/{ident}/findings.md", f"# Findings: {ident}\n\nLast updated: 2026-10-07\n\n{text}")
        if page:
            self.people.append({"id": ident, "name": ident})
            self.write(f"www/people/{ident.lower()}.html", "<html></html>")

    def page_data(self, ident: str, titles: list[str]) -> None:
        sections = [{"title": t, "category": "notes", "markdown": "x"} for t in titles]
        self.write(f"www/people/{ident.lower()}.json", json.dumps(
            {"research_findings": [{"profile_id": ident, "source_path": f"research/{ident}/findings.md",
                                    "sections": sections}]}))

    def finish(self) -> None:
        self.write("www/data/people-index.json", json.dumps(self.people))
        self.write("data/wikitree/research-catalogue-cases.json", json.dumps({"cases": self.cases}))


class PublicationCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = Tree(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, ids=None, evidence=None):
        self.tree.finish()
        return check.run(self.tree.root, ids, wikitree_evidence=evidence or {"profiles": {}})

    def codes(self, checker, subject=None):
        return {i.code for i in checker.items if subject is None or i.subject == subject}

    def test_a_clean_file_reports_nothing_that_fails(self):
        self.tree.findings("Glasgow-1", CONCLUSION + "\n## Source findings\n\n- [Register](https://example.org/r1)\n")
        self.tree.page_data("Glasgow-1", ["Current conclusion", "Source findings"])
        checker = self.run_check()
        self.assertEqual([], [i for i in checker.items if i.level == "fail"])

    def test_text_above_the_first_heading_is_reported_but_template_lines_are_not(self):
        self.tree.findings("Glasgow-1", "Checked against the live profile and the parish register on 26 September 2026.\n\n"
                           + CONCLUSION)
        self.tree.findings("Glasgow-2", "Record every useful result and negative search here as it is found.\n"
                           "Do not treat an unsourced tree or naming pattern as proof.\n\n" + CONCLUSION)
        checker = self.run_check()
        self.assertIn("PREAMBLE_NOT_PUBLISHED", self.codes(checker, "Glasgow-1"))
        self.assertNotIn("PREAMBLE_NOT_PUBLISHED", self.codes(checker, "Glasgow-2"))

    def test_internal_sections_are_listed_and_a_source_only_there_fails(self):
        self.tree.findings("Glasgow-1", CONCLUSION
                           + "\n## WikiTree update instructions\n\nCite [the deed](https://example.org/deed-1786).\n"
                           + "\n## WikiTree handoff\n\nAlready cited: [census](https://example.org/census).\n"
                           + "\n## Source findings\n\n- [census](https://example.org/census)\n")
        checker = self.run_check()
        internal = [i for i in checker.items if i.code == "INTERNAL_SECTION"]
        self.assertEqual(2, len(internal))
        orphaned = [i for i in checker.items if i.code == "SOURCE_ONLY_IN_INTERNAL_SECTION"]
        self.assertEqual(["WikiTree update instructions"], [i.key for i in orphaned])
        self.assertEqual({"Glasgow-1": 2}, checker.internal_counts)

    def test_a_source_the_live_profile_already_cites_is_not_reported(self):
        self.tree.findings("Glasgow-1", CONCLUSION + "\n## Public profile scrape review (2026-07-22)\n\n"
                           "The profile cites [a baptism](https://example.org/bap).\n")
        evidence = {"profiles": {"Glasgow-1": {"external_urls": ["https://example.org/bap"]}}}
        checker = self.run_check(evidence=evidence)
        self.assertNotIn("SOURCE_ONLY_IN_INTERNAL_SECTION", self.codes(checker))

    def test_unrecognised_heading_is_published_as_notes_and_listed(self):
        self.tree.findings("Glasgow-1", CONCLUSION + "\n## Birth-estimate audit\n\nBorn about 1790.\n")
        checker = self.run_check()
        notes = [i for i in checker.items if i.code == "NOTES_HEADING"]
        self.assertEqual(["Birth-estimate audit"], [i.key for i in notes])
        self.assertEqual("info", notes[0].level)

    def test_openings_without_one_overall_conclusion(self):
        self.tree.findings("Glasgow-2", "## Source findings\n\n- A record.\n")
        self.tree.findings("Glasgow-3", "## Current conclusion — newspaper review, 6 October 2026\n\nA.\n\n"
                           "## Current conclusion — Findmypast evidence, 7 October 2026\n\nB.\n")
        self.tree.findings("Glasgow-4", "## Current conclusion\n\nA.\n\n## Conclusion\n\nB.\n")
        self.tree.findings("Glasgow-5", "## Current conclusion\n\n| Date | Source |\n| --- | --- |\n"
                           "| No sourced conclusion recorded yet. | |\n\n## Source findings\n\n- A record.\n")
        self.tree.findings("Glasgow-6", CONCLUSION + "\n## Current conclusion — newspaper review, 6 October 2026\n\nC.\n")
        checker = self.run_check()
        fallback = {i.subject: i.key for i in checker.items if i.code == "OPENING_FALLBACK"}
        self.assertEqual({"Glasgow-2": "missing", "Glasgow-3": "additions", "Glasgow-5": "placeholder"}, fallback)
        self.assertEqual({"Glasgow-4"}, {i.subject for i in checker.items if i.code == "CONCLUSION_CONFLICT"})

    def test_correction_dated_after_the_conclusion_is_a_warning(self):
        self.tree.findings("Glasgow-1", "## Current conclusion\n\nReviewed: 2026-09-01\n\nHe was a weaver.\n\n"
                           "## Source findings — re-read, 6 October 2026\n\nThe 1841 identification is withdrawn.\n")
        self.tree.findings("Glasgow-2", "## Current conclusion\n\nReviewed: 2026-10-07\n\nHe was a weaver.\n\n"
                           "## Source findings — re-read, 6 October 2026\n\nThe 1841 identification is withdrawn.\n")
        checker = self.run_check()
        stale = [i for i in checker.items if i.code == "CONCLUSION_OLDER_THAN_CORRECTION"]
        self.assertEqual(["Glasgow-1"], [i.subject for i in stale])
        self.assertEqual("warn", stale[0].level)

    def test_findings_without_a_page(self):
        self.tree.findings("Glasgow-7", CONCLUSION, page=False)
        self.tree.findings("Glasgow-8", CONCLUSION, page=False)
        self.tree.findings("Glasgow-9", CONCLUSION, page=False)
        self.tree.cases = {"Glasgow-8": {"status": "pending", "profile_id": "Glasgow-8"},
                           "Glasgow-9": {"status": "include", "profile_id": "Glasgow-9"}}
        checker = self.run_check()
        found = {i.subject: i.code for i in checker.items if i.code.startswith("NO_PAGE")}
        self.assertEqual({"Glasgow-7": "NO_PAGE_UNDECIDED", "Glasgow-8": "NO_PAGE_PENDING",
                          "Glasgow-9": "NO_PAGE_INCLUDED"}, found)

    def test_folder_that_no_tool_reads(self):
        self.tree.findings("opr-test-to-1700", "## Source findings\n\n- 1650 baptism.\n", page=False)
        self.tree.findings("larne-read-2026", "## Source findings\n\n- 1700 session.\n", page=False)
        self.tree.write("tools/publish_larne.py", 'SOURCE = ROOT / "research/larne-read-2026/findings.md"\n'
                        'ANCHOR = "opr-test-to-1700"\n')
        checker = self.run_check()
        self.assertEqual({"opr-test-to-1700"}, {i.subject for i in checker.items if i.code == "FOLDER_NOT_READ"})
        self.assertFalse(check.is_profile_id("opr-births-to-1700"))
        self.assertTrue(check.is_profile_id("McClure-6341"))

    def test_page_not_resynchronised_after_the_file_changed(self):
        self.tree.findings("Glasgow-1", CONCLUSION + "\n## Source findings — re-read, 6 October 2026\n\n- New.\n")
        self.tree.page_data("Glasgow-1", ["Current conclusion"])
        checker = self.run_check()
        stale = [i for i in checker.items if i.code == "PAGE_NOT_RESYNCED"]
        self.assertEqual(1, len(stale))
        self.assertIn("not on the page", stale[0].message)

    def test_correction_still_in_canonical_records(self):
        self.tree.findings("Glasgow-3188", CONCLUSION)
        self.tree.write("research/canonical_records.json", json.dumps(
            [{"record_id": "r1", "date": "Testament made 10 January 1613; confirmed 8 May 1613"},
             {"record_id": "r2", "note": "The earlier reading 10 January 1613 is superseded."}]))
        self.tree.write("www/data/records-index.json", json.dumps([{"date": "10 January 1613"}]))
        self.tree.write(check.SUPERSEDED_READINGS, json.dumps({"readings": [{
            "id": "ninian", "profile": "Glasgow-3188", "superseded": "10 January 1613",
            "corrected": "an unread day of January 1613", "allowed_context": "earlier|supersed"}]}))
        checker = self.run_check()
        maintained = [i for i in checker.items if i.code == "CORRECTION_NOT_IN_RECORDS"]
        self.assertEqual(1, len(maintained))
        self.assertIn("research/canonical_records.json", maintained[0].message)
        self.assertIn("(1x)", maintained[0].message)
        self.assertEqual(["warn"], [i.level for i in checker.items if i.code == "CORRECTION_NOT_IN_BUILT_RECORDS"])

    def test_open_register_entry_and_completed_queue_entry_are_reported(self):
        self.tree.findings("Glasgow-1", CONCLUSION)
        self.tree.write("surname-research/to-update.md", "# WikiTree work queue\n\n## Review — 6 October 2026\n\n"
                        "- [[Glasgow-1]] — Add the 1841 census entry.\n\n## Completed profiles\n\n"
                        "- [[Glasgow-2]] — Applied.\n")
        self.tree.write("data/wikitree/profile-update-queue.json", json.dumps({
            "include_open_register": True, "completed_live_profiles": ["Glasgow-7"],
            "entries": {"Glasgow-7": {"summary": "Old amendment.", "manual_update": True}}}))
        checker = self.run_check()
        self.assertEqual({"Glasgow-1"}, {i.subject for i in checker.items if i.code == "REGISTER_ENTRY_DROPPED"})
        closed = [i for i in checker.items if i.code == "QUEUE_ENTRY_CLOSED"]
        self.assertEqual(["Glasgow-7"], [i.subject for i in closed])
        self.assertEqual("info", closed[0].level)

    def test_preloaded_models_preserve_queue_diagnostics_without_reloading(self):
        self.tree.findings("Glasgow-1", CONCLUSION)
        self.tree.write("surname-research/to-update.md", "# WikiTree work queue\n\n"
                        "## Review — 6 October 2026\n\n"
                        "- [[Glasgow-1]] — Add the 1841 census entry.\n\n")
        self.tree.write("data/wikitree/profile-update-queue.json", json.dumps({
            "include_open_register": True, "completed_live_profiles": ["Glasgow-7"],
            "entries": {"Glasgow-7": {"summary": "Old amendment.", "manual_update": True}}}))
        evidence = {"profiles": {}}
        expected = self.run_check(evidence=evidence)
        report = []
        with check.builder_paths(self.tree.root):
            updates = catalog._load_profile_updates(evidence, report=report)
        with patch.object(catalog, '_load_wikitree_evidence', side_effect=AssertionError('evidence reloaded')), \
             patch.object(catalog, '_load_profile_updates', side_effect=AssertionError('updates reloaded')):
            actual = check.run(self.tree.root, wikitree_evidence=evidence,
                               profile_updates=updates, profile_update_report=report)
        signature = lambda checker: [(i.code, i.subject, i.key, i.message) for i in checker.items]
        self.assertEqual(signature(expected), signature(actual))
        self.assertIn("QUEUE_ENTRY_CLOSED", self.codes(actual))
        self.assertIn("REGISTER_ENTRY_DROPPED", self.codes(actual))

    def test_id_limits_the_check_to_named_profiles(self):
        self.tree.findings("Glasgow-1", "Stray note above the headings that never reaches the page at all.\n\n" + CONCLUSION)
        self.tree.findings("Glasgow-2", "## Source findings\n\n- A record.\n")
        checker = self.run_check(ids=["Glasgow-2"])
        self.assertEqual({"Glasgow-2"}, {i.subject for i in checker.items})
        self.assertEqual(1, checker.files_checked)

    def test_targeted_check_does_not_validate_an_unrelated_unfinished_queue_entry(self):
        self.tree.findings('Glasgow-1', CONCLUSION)
        self.tree.write('data/wikitree/profile-update-queue.json', json.dumps({
            'entries': {'Glasgow-2': {'summary': 'Unfinished draft without capture'}}}))
        self.assertNotIn('QUEUE_ENTRY_DROPPED', self.codes(self.run_check(ids=['Glasgow-1'])))
        self.assertIn('QUEUE_ENTRY_DROPPED', self.codes(self.run_check()))

    def test_every_rule_has_a_level_and_explanation(self):
        for code, (level, title, explanation) in check.RULES.items():
            self.assertIn(level, check.LEVEL_ORDER, code)
            self.assertTrue(title and explanation, code)


class RegisterAndQueueParserTest(unittest.TestCase):
    """S4-R3: every entry form in the register is read; completion keeps its meaning."""

    BIOGRAPHY = "[[Category:Glasgow Name Study]]\n\n== Biography ==\n\nA recorded life.\n\n== Sources ==\n\n<references />"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tree = Tree(self.root)
        for ident in ("Glasgow-1", "Glasgow-2", "Glasgow-3", "Glasgow-4"):
            self.tree.findings(ident, CONCLUSION + "\n## Source findings\n\n- [Register](https://example.org/" + ident + ")\n")
        self.tree.findings("Glasgow-5", CONCLUSION)
        paths = check.builder_paths(self.root)
        paths.__enter__()
        self.addCleanup(paths.__exit__, None, None, None)
        self.addCleanup(self.tmp.cleanup)

    def evidence(self, *ids):
        profiles = {}
        for ident in ids:
            capture = {"profile_url": f"https://www.wikitree.com/wiki/{ident}"}
            capture["biography_wikitext"] = catalog._normalise_complete_wikitree_profile(self.BIOGRAPHY, ident, capture)
            profiles[ident] = capture
        return {"profiles": profiles}

    def register(self, text):
        self.tree.write("surname-research/to-update.md", "# WikiTree work queue\n\n" + text)

    def test_bullet_and_table_forms_are_read_and_closed_sections_are_not(self):
        self.register(
            "## Newspaper identity review — 6 October 2026\n\n"
            "- [[Glasgow-1]] — Add the 1838 assize notice.\n"
            "- [[Glasgow-2|Mary Glasgow]] — DONE 7 October 2026.\n\n"
            "## OPR banns — 10 September 2026\n\n| Profile | Status | Change |\n| --- | --- | --- |\n"
            "| [[Glasgow-3]] | **OPEN — NEEDS UPDATED ON WIKITREE:** add the 1674 banns. | |\n"
            "| 7 | [John](https://www.wikitree.com/wiki/Glasgow-4) | OPEN (held) | Note the 1698 index. |\n\n"
            "## Completed Larne profiles — 21 September 2026\n\n- [[Glasgow-2]] — Applied.\n")
        report = []
        entries = catalog._registered_profile_updates(self.evidence(), report)
        self.assertEqual({"Glasgow-1", "Glasgow-3", "Glasgow-4"}, set(entries))
        self.assertEqual("Add the 1838 assize notice.", entries["Glasgow-1"]["work_queue_summary"])
        self.assertEqual("add the 1674 banns.", entries["Glasgow-3"]["work_queue_summary"])
        self.assertEqual("Note the 1698 index.", entries["Glasgow-4"]["work_queue_summary"])
        self.assertEqual(3, sum(1 for r in report if r["accepted"]))

    def test_several_entries_for_one_profile_are_combined_and_unsourced_ones_reported(self):
        self.register("## Review — 6 October 2026\n\n- [[Glasgow-1]] — Add the 1841 census.\n"
                      "- [[Glasgow-5]] — Add the burial.\n\n## Older — 1 September 2026\n\n"
                      "| [Glasgow-1](https://www.wikitree.com/wiki/Glasgow-1) | OPEN | Correct the birth year. |\n")
        report = []
        entries = catalog._registered_profile_updates(self.evidence(), report)
        self.assertEqual("Add the 1841 census.\n\nCorrect the birth year.", entries["Glasgow-1"]["work_queue_summary"])
        dropped = [r for r in report if not r["accepted"]]
        self.assertEqual(["Glasgow-5"], [r["profile_id"] for r in dropped])
        self.assertIn("no source link", dropped[0]["reason"])

    def queue(self, entries, completed=()):
        self.tree.write("data/wikitree/profile-update-queue.json", json.dumps({
            "include_open_register": True, "completed_live_profiles": list(completed), "entries": entries}))

    def test_entry_dated_after_completion_reopens_and_older_or_undated_entries_do_not(self):
        self.register("## Done — 17 September 2026\n\n"
                      + "".join(f"| [{i}](https://www.wikitree.com/wiki/{i}) | **DONE — APPLIED LIVE 17 SEPTEMBER 2026** | x |\n"
                                for i in ("Glasgow-1", "Glasgow-2", "Glasgow-3")))
        self.queue({
            "Glasgow-1": {"summary": "Newspaper identity review 6 Oct 2026. Add sourced facts.", "manual_update": True,
                          "replacements": [{"old": "text that is no longer there", "new": "x"}]},
            "Glasgow-2": {"summary": "Add the census.", "manual_update": True},
            "Glasgow-3": {"summary": "Review of 2 September 2026.", "manual_update": True},
        }, completed=("Glasgow-1", "Glasgow-2", "Glasgow-3"))
        report = []
        updates = catalog._load_profile_updates(self.evidence("Glasgow-1", "Glasgow-2", "Glasgow-3"), report)
        self.assertEqual({"Glasgow-1"}, set(updates))
        self.assertTrue(updates["Glasgow-1"]["manual_update"])
        self.assertNotIn("replacements", updates["Glasgow-1"])
        closed = {r["profile_id"]: r for r in report if r.get("kind") == "completed"}
        self.assertEqual({"Glasgow-2", "Glasgow-3"}, set(closed))
        self.assertIn("2026-09-17", closed["Glasgow-3"]["reason"])

    def test_queue_entry_without_a_capture_is_reported(self):
        self.register("")
        self.queue({"Glasgow-4": {"summary": "Add the 1850 deed.", "manual_update": True, "registered_update": True}})
        report = []
        self.assertEqual({}, catalog._load_profile_updates(self.evidence(), report))
        self.assertEqual([("Glasgow-4", "no_capture")], [(r["profile_id"], r["kind"]) for r in report])


class BaselineRatchetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = Tree(Path(self.tmp.name))
        self.tree.findings("Glasgow-2", "## Source findings\n\n- A record.\n")
        self.tree.finish()
        self.baseline = str(self.tree.root / "data/site/baseline.json")
        patcher = patch.object(catalog, "_load_wikitree_evidence", return_value={"profiles": {}})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *args):
        with redirect_stdout(io.StringIO()) as out:
            code = check.main(["--root", str(self.tree.root), *args])
        return code, out.getvalue()

    def test_existing_items_are_tolerated_and_new_ones_fail(self):
        self.assertEqual(1, self.main()[0])
        self.assertEqual(2, self.main("--baseline", self.baseline)[0])  # missing baseline file
        self.assertEqual(0, self.main("--baseline", self.baseline, "--update-baseline")[0])
        code, out = self.main("--baseline", self.baseline)
        self.assertEqual(0, code, out)
        self.tree.findings("Glasgow-3", "## Source findings\n\n- Another record.\n")
        self.tree.finish()
        code, out = self.main("--baseline", self.baseline)
        self.assertEqual(1, code)
        self.assertIn("Glasgow-3", out)

    def test_update_baseline_only_shrinks_unless_new_items_are_accepted(self):
        self.main("--baseline", self.baseline, "--update-baseline")
        self.tree.findings("Glasgow-3", "## Source findings\n\n- Another record.\n")
        self.tree.findings("Glasgow-2", "## Current conclusion\n\nFixed.\n")
        self.tree.finish()
        code, _ = self.main("--baseline", self.baseline, "--update-baseline")
        self.assertEqual(1, code)  # Glasgow-3 is new and was not recorded
        items = json.loads(Path(self.baseline).read_text())["items"]
        self.assertEqual({}, items)  # Glasgow-2 is fixed, so the baseline shrank to nothing
        self.assertEqual(0, self.main("--baseline", self.baseline, "--update-baseline", "--accept-new")[0])
        items = json.loads(Path(self.baseline).read_text())["items"]
        self.assertEqual(["Glasgow-3|missing"], items["OPENING_FALLBACK"])

    def test_update_baseline_refuses_a_partial_run(self):
        self.assertEqual(2, self.main("--baseline", self.baseline, "--update-baseline", "--id", "Glasgow-2")[0])


if __name__ == "__main__":
    unittest.main()
