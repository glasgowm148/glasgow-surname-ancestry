from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.public_manuscript_previews import (
    approved_preview,
    audit_approved_previews,
    restore_approved_previews,
)


class PublicManuscriptPreviewTests(unittest.TestCase):
    def test_restores_only_hash_approved_assets_and_keeps_private_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web, private = root / "www", root / "private"
            relative = Path("assets/research/testament-crops/approved.jpg")
            private_asset = private / relative
            private_asset.parent.mkdir(parents=True)
            private_asset.write_bytes(b"approved")
            (private / "assets/research/testament-crops/unapproved.jpg").write_bytes(b"unapproved")
            manifest = root / "approvals.json"
            manifest.write_text(json.dumps({"schema_version": 1, "approved_assets": [{
                "url": "/" + relative.as_posix(),
                "sha256": hashlib.sha256(b"approved").hexdigest(),
            }]}))

            self.assertEqual(restore_approved_previews(web, private, manifest), 1)
            self.assertEqual((web / relative).read_bytes(), b"approved")
            self.assertTrue(private_asset.exists())
            self.assertFalse((web / "assets/research/testament-crops/unapproved.jpg").exists())
            self.assertTrue(approved_preview("/" + relative.as_posix(), web, private, manifest))

    def test_audit_rejects_unapproved_and_tampered_public_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web, private = root / "www", root / "private"
            relative = Path("assets/research/testament-originals/approved.pdf")
            source = private / relative
            source.parent.mkdir(parents=True)
            source.write_bytes(b"approved")
            manifest = root / "approvals.json"
            manifest.write_text(json.dumps({"schema_version": 1, "approved_assets": [{
                "url": "/" + relative.as_posix(),
                "sha256": hashlib.sha256(b"approved").hexdigest(),
            }]}))
            restore_approved_previews(web, private, manifest)
            (web / relative).write_bytes(b"changed")
            extra = web / "assets/research/testament-originals/extra.pdf"
            extra.write_bytes(b"extra")

            failures = audit_approved_previews(web, private, manifest)
            self.assertEqual(len(failures), 2)
            self.assertFalse(approved_preview("/" + relative.as_posix(), web, private, manifest))


if __name__ == "__main__":
    unittest.main()
