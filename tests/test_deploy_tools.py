from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools import deploy_site, stamp_asset_versions


class StampAssetVersionsTests(unittest.TestCase):
    def test_stamps_html_and_javascript_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            css = root / "assets" / "site.css"
            script = root / "assets" / "atlas.js"
            css.write_text("body { color: black; }", encoding="utf-8")
            script.write_text("export default 1;", encoding="utf-8")
            page = root / "index.html"
            loader = root / "assets" / "boot.js"
            page.write_text('<link href="/assets/site.css?v=old">', encoding="utf-8")
            loader.write_text('import "atlas.js?v=stale";', encoding="utf-8")

            changed, references = stamp_asset_versions.stamp(root, write=True)

            self.assertEqual((changed, references), (2, 2))
            self.assertIn(hashlib.sha256(css.read_bytes()).hexdigest()[:10], page.read_text())
            self.assertIn(hashlib.sha256(script.read_bytes()).hexdigest()[:10], loader.read_text())
            self.assertEqual(stamp_asset_versions.stamp(root, write=False), (0, 0))


class DeploySiteTests(unittest.TestCase):
    def test_bundle_uses_site_root_and_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "www"
            root.mkdir()
            (root / "index.html").write_text("ok", encoding="utf-8")
            (root / "index.html").chmod(0o600)
            (root / ".DS_Store").write_text("no", encoding="utf-8")
            (root / "glasgow-site-old.tar.gz").write_text("no", encoding="utf-8")
            (root / "private").mkdir()
            (root / "private" / "secret.txt").write_text("no", encoding="utf-8")
            (root / "source").mkdir()
            (root / "source" / "build.py").write_text("no", encoding="utf-8")
            (root / "raw").mkdir()
            (root / "raw" / "capture.txt").write_text("no", encoding="utf-8")
            (root / ".env").write_text("TOKEN=no", encoding="utf-8")
            (root / "deploy.pyc").write_bytes(b"no")
            (root / "notes.md").write_text("public transcription notes", encoding="utf-8")

            archive = deploy_site.make_bundle(root, dt.datetime(2026, 9, 24, 12, 34, 56))

            self.assertEqual(archive.name, "glasgow-site-20260924-123456.tar.gz")
            with tarfile.open(archive, "r:gz") as contents:
                self.assertEqual(contents.getnames(), ["index.html", "notes.md", "release-manifest.json"])
                self.assertEqual(contents.getmember("index.html").mode, 0o644)
                manifest = json.load(contents.extractfile("release-manifest.json"))
                self.assertEqual([entry["path"] for entry in manifest["files"]], ["index.html", "notes.md"])
                for entry in manifest["files"]:
                    data = contents.extractfile(entry["path"]).read()
                    self.assertEqual(entry["bytes"], len(data))
                    self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())

    def test_bundle_rejects_escaped_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "www"
            root.mkdir()
            (root / "index.html").write_text("ok", encoding="utf-8")
            (root / "escaped").symlink_to(Path(temporary) / "outside.txt")

            with self.assertRaisesRegex(ValueError, "escaped symlink"):
                deploy_site.make_bundle(root)

    def test_rsync_command_is_dry_by_default_and_excludes_release_files(self) -> None:
        command = deploy_site.rsync_command(Path("www"), "alice@example.test:/var/www/site")

        self.assertIn("--dry-run", command)
        self.assertIn("--itemize-changes", command)
        self.assertIn("glasgow-site-*.tar.gz", command)
        self.assertIn("private/", command)
        self.assertIn("*.py", command)
        self.assertIn("--safe-links", command)
        self.assertIn("--delete-excluded", command)
        self.assertEqual(command[-1], "alice@example.test:/var/www/site/")

    def test_rsync_normalizes_private_build_modes_for_public_serving(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "www"
            root.mkdir(mode=0o700)
            (root / "index.html").write_text("public", encoding="utf-8")
            (root / "index.html").chmod(0o600)
            (root / "private").mkdir(mode=0o700)
            (root / "private" / "secret.txt").write_text("private", encoding="utf-8")
            (root / "private" / "secret.txt").chmod(0o600)
            target = Path(temporary) / "deployed"
            deploy_site.normalize_public_modes(root)
            subprocess.run(deploy_site.rsync_command(root, str(target), dry_run=False),
                           check=True, capture_output=True)
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertEqual((target / "index.html").stat().st_mode & 0o777, 0o644)
            self.assertEqual((root / "private").stat().st_mode & 0o777, 0o700)
            self.assertEqual((root / "private" / "secret.txt").stat().st_mode & 0o777, 0o600)
            self.assertFalse((target / "private").exists())

    def test_atomic_target_and_switch_command(self) -> None:
        target = "alice@example.test:/var/www/site"
        self.assertEqual(
            deploy_site.release_target(target, "20260924-123456"),
            "alice@example.test:/var/www/site.releases/20260924-123456/",
        )
        self.assertEqual(deploy_site.atomic_switch_command(target, "20260924-123456")[0:2], ["ssh", "alice@example.test"])

    def test_atomic_switch_refuses_existing_directory_and_switches_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "site"
            root.mkdir()
            release = Path(str(root) + ".releases") / "new"
            release.mkdir(parents=True)
            command = deploy_site.atomic_switch_command(f"example.test:{root}", "new")[-1]
            self.assertNotEqual(subprocess.run(["sh", "-c", command]).returncode, 0)
            self.assertTrue(root.is_dir())
            self.assertFalse(root.is_symlink())
            root.rmdir()
            root.symlink_to(release.parent / "old", target_is_directory=True)
            self.assertEqual(subprocess.run(["sh", "-c", command]).returncode, 0)
            self.assertEqual(root.resolve(), release.resolve())


if __name__ == "__main__":
    unittest.main()
