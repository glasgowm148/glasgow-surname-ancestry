import json
from pathlib import Path
import tempfile
import unittest

from tools.repair_evidence_source_links import repair_source_title


class EvidenceSourceCorrectionTests(unittest.TestCase):
    def test_exact_title_refresh_preserves_imported_and_remote_captures(self):
        prior = "Archive A, dated 10 January 1613"
        reviewed = "Archive A, dated in January 1613 (day unread)"
        correction = {
            "previous_source_title": prior,
            "profile_ids": ["Fixture-1"],
            "record_ids": ["entry-1"],
            "reason": "The image leaves the day unread.",
        }
        record = {"record_id": "fixture", "source_title": reviewed}
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            dossier = web / "people/fixture-1.json"
            index = web / "data/records-index.json"
            export = web / "data/records.csv"
            mirror = web / "data/records.csv.txt"
            detail = web / "assets/research/records/entry-1.json"
            for path in (dossier, index, detail):
                path.parent.mkdir(parents=True, exist_ok=True)
            dossier.write_text(json.dumps({
                "evidence": [{"source": {"title": prior}}],
                "source_summary": [{"title": prior + " from a different source"}],
                "imported": {"evidence": [{"source": {"title": prior}}]},
                "wikitree_comparison": {"remote_wikitext": prior},
            }))
            index.write_text(json.dumps([{"supporting_source_title": prior}]))
            detail.write_text(json.dumps({"supporting_source_title": prior}))
            export.write_text(f'record_id,supporting_source_title\nentry-1,"{prior}"\n')
            mirror.write_bytes(export.read_bytes())

            self.assertEqual(5, repair_source_title(web, correction, record))
            actual = json.loads(dossier.read_text())
            self.assertEqual(reviewed, actual["evidence"][0]["source"]["title"])
            self.assertEqual(prior, actual["imported"]["evidence"][0]["source"]["title"])
            self.assertEqual(prior, actual["wikitree_comparison"]["remote_wikitext"])
            self.assertEqual(prior + " from a different source", actual["source_summary"][0]["title"])
            self.assertEqual(reviewed, json.loads(detail.read_text())["supporting_source_title"])
            self.assertNotIn(prior, index.read_text())
            self.assertIn(reviewed, export.read_text(encoding="utf-8-sig"))
            self.assertEqual(export.read_bytes(), mirror.read_bytes())
            self.assertEqual(0, repair_source_title(web, correction, record))

    def test_combined_title_keeps_other_citation(self):
        correction = {
            "previous_source_title": "Other record; Archive A, dated 10 January 1613",
            "preserved_title_prefix": "Other record; ",
            "profile_ids": ["Fixture-1"],
            "reason": "The image leaves the day unread.",
        }
        record = {"record_id": "fixture", "source_title": "Archive A, day unread in January 1613"}
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            dossier = web / "people/fixture-1.json"
            dossier.parent.mkdir()
            dossier.write_text(json.dumps({"source_summary": [{"title": correction["previous_source_title"]}]}))
            self.assertEqual(1, repair_source_title(web, correction, record))
            self.assertEqual(
                "Other record; Archive A, day unread in January 1613",
                json.loads(dossier.read_text())["source_summary"][0]["title"],
            )

    def test_existing_source_route_retains_its_exact_id_and_historical_text(self):
        prior = "Archive A, dated 10 January 1613"
        reviewed = "Archive A, dated in January 1613 (day unread)."
        ident = "s-abcdef"
        correction = {"previous_source_title": prior, "reason": "The image leaves the day unread."}
        record = {"record_id": "fixture", "source_title": reviewed}
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            index = web / "assets/v3/source-index.json"
            doc = web / "assets/v3/sources" / f"{ident}.json"
            reader = web / "sources" / ident / "index.html"
            browse = web / "sources/browse/index.html"
            for path in (doc, reader, browse):
                path.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(json.dumps([{"id": ident, "title": prior}]))
            doc.write_text(json.dumps({"id": ident, "title": prior, "transcription": prior}))
            reader.write_text(f"<head><title>{prior}</title></head><body><h1>{prior}</h1><blockquote>{prior}</blockquote><noscript><p>Citation: {prior}.</p></noscript></body>")
            browse.write_text(f'<a href="/sources/{ident}/">{prior}</a><p>{prior}</p>')

            self.assertEqual(5, repair_source_title(web, correction, record))
            self.assertEqual(ident, json.loads(index.read_text())[0]["id"])
            self.assertEqual(prior, json.loads(doc.read_text())["transcription"])
            self.assertIn(f"<title>{reviewed}</title>", reader.read_text())
            self.assertIn(f"<blockquote>{prior}</blockquote>", reader.read_text())
            self.assertIn(f"<p>Citation: {reviewed}</p>", reader.read_text())
            self.assertNotIn("..</p>", reader.read_text())
            self.assertIn(f'<a href="/sources/{ident}/">{reviewed}</a>', browse.read_text())
            self.assertIn(f"<p>{prior}</p>", browse.read_text())
            self.assertEqual(0, repair_source_title(web, correction, record))
