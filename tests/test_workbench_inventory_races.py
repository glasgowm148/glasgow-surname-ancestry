import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import workbench_inventory as inventory


class InventoryRaceTests(unittest.TestCase):
    def test_records_disappearing_sidecar_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            kept = root / "research" / "evidence.txt"
            kept.parent.mkdir()
            kept.write_text("source")
            missing = root / "data/private/workbench/glasgow.sqlite-shm"

            def walk(source):
                yield missing, missing.relative_to(source).as_posix(), False
                yield kept, kept.relative_to(source).as_posix(), True

            walk.summarised = {}
            with patch.object(inventory, "walk", walk), patch.object(inventory, "git", return_value="abc"):
                report = inventory.inventory(root, root / "output")
            self.assertEqual(report["vanished_during_inventory"], ["data/private/workbench/glasgow.sqlite-shm"])
            self.assertEqual([row["path"] for row in report["files"]], ["research/evidence.txt"])
            self.assertEqual(report["files"][0]["sha256"], inventory.sha256(kept))


if __name__ == "__main__":
    unittest.main()
