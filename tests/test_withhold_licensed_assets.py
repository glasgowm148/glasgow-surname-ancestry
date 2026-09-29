from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import render_testament_fragment, render_testament_walkthrough, withhold_licensed_assets


class WithholdLicensedAssetsTests(unittest.TestCase):
    def test_withhold_preserves_files_privately_and_removes_public_copies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web, private = root / "www", root / "private"
            crop = web / "assets/research/testament-crops/example.jpg"
            original = web / "assets/research/testament-originals/example.pdf"
            excerpt = web / "assets/research/record-excerpts/example.jpg"
            crop.parent.mkdir(parents=True)
            original.parent.mkdir(parents=True)
            excerpt.parent.mkdir(parents=True)
            crop.write_bytes(b"crop")
            original.write_bytes(b"original")
            excerpt.write_bytes(b"excerpt")

            self.assertEqual(withhold_licensed_assets.withhold(web, private), 3)
            self.assertEqual(withhold_licensed_assets.audit(web, private), [])
            self.assertEqual(
                (private / "assets/research/testament-crops/example.jpg").read_bytes(), b"crop"
            )
            self.assertEqual(
                (private / "assets/research/testament-originals/example.pdf").read_bytes(), b"original"
            )
            self.assertEqual((private / "assets/research/record-excerpts/example.jpg").read_bytes(), b"excerpt")

    def test_walkthrough_omits_licensed_scan_urls(self) -> None:
        data = {
            "steps": [{
                "id": "opening", "title": "Opening", "image": "/assets/research/testament-crops/example.jpg",
                "original": "Saved transcription", "reading": "Modern reading", "explanation": "Method",
                "proves": "A limited point", "does_not_prove": "A broader claim",
            }],
        }
        with patch.object(render_testament_walkthrough, "load_walkthrough", return_value=data), patch.object(
            render_testament_walkthrough, "load_letterforms", return_value=None
        ):
            page = render_testament_walkthrough.render_walkthrough({"id": "example", "record": "Cited record"})

        self.assertIn("Licensed scan withheld; consult cited source", page)
        self.assertIn("Saved transcription", page)
        self.assertNotIn("/assets/research/testament-crops", page)
        self.assertNotIn("<img", page)

    def test_associated_fragment_omits_licensed_scan_url(self) -> None:
        fragment = {
            "partial_transcription": {"heading": ["Heading"], "lines": ["Line"]},
            "reading_findings": [], "next_steps": [], "interpretation": "Context",
            "image_url": "/assets/research/testament-crops/example.jpg", "reading_url": "/reading.txt",
            "research_question": "Question", "attachment_limit": "Limit", "family_lead": "Lead",
        }
        page = render_testament_fragment.render_associated_fragment(fragment)
        self.assertIn("Licensed scan withheld; consult cited source", page)
        self.assertNotIn("/assets/research/testament-crops", page)

    def test_associated_fragment_renders_approved_scan(self) -> None:
        fragment = {
            "partial_transcription": {"heading": ["Heading"], "lines": ["Line"]},
            "reading_findings": [], "next_steps": [], "interpretation": "Context",
            "image_url": "/assets/research/testament-crops/example.jpg", "reading_url": "/reading.txt",
            "research_question": "Question", "attachment_limit": "Limit", "family_lead": "Lead",
        }
        with patch.object(render_testament_fragment, "approved_preview", return_value=True):
            page = render_testament_fragment.render_associated_fragment(fragment)
        self.assertIn('<img src="/assets/research/testament-crops/example.jpg"', page)


if __name__ == "__main__":
    unittest.main()
