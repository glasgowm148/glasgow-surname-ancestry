from pathlib import Path
import unittest
import tempfile
import os
from unittest.mock import patch

from tools import sync_familysearch_links as sync


class EmptyWalSnapshotTests(unittest.TestCase):
    def test_reader_metadata_changes_do_not_invalidate_empty_wal_but_data_does(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'data/familysearch/person-links.json'
            (root / 'genealogy.toml').touch()
            database = root / 'research.sqlite'
            database.touch()
            wal = Path(str(database) + '-wal')
            wal.touch()
            with patch.object(sync, '_configured_database', return_value=database):
                empty = sync._project_context(target)
                wal.chmod(0o600)
                self.assertEqual(sync._project_context(target), empty)
                wal.write_bytes(b'first')
                populated = sync._project_context(target)
                self.assertNotEqual(populated, empty)
                wal.chmod(0o640)
                self.assertEqual(sync._project_context(target), populated)
                before = wal.stat()
                wal.write_bytes(b'other')
                os.utime(wal, ns=(before.st_atime_ns, before.st_mtime_ns))
                self.assertNotEqual(sync._project_context(target), populated)
