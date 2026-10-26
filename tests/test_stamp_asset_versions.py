import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.stamp_asset_versions import _scan, find_mismatches, stamp


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()[:10]


class StampAssetVersionsTests(unittest.TestCase):
    def test_chain_shared_dependency_settles_once_and_preserves_original_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = '{"value":2}\n'
            (root / 'data.json').write_text(data)
            old_leaf = 'const data="/data.json?v=old";\n'
            (root / 'leaf.js').write_text(old_leaf)
            # These consumers initially match leaf's old bytes, but must change
            # when the leaf's JSON reference is repaired in this same pass.
            old_middle = f'const leaf="/leaf.js?v={digest(old_leaf)}";\n'
            (root / 'middle.js').write_text(old_middle)
            old_page = f'<script src="/middle.js?v={digest(old_middle)}"></script>\n'
            old_page += f'<script src="/leaf.js?v={digest(old_leaf)}"></script>\n'
            (root / 'index.html').write_text(old_page)
            self.assertEqual(stamp(root, False), (1, 1))
            self.assertEqual((root / 'leaf.js').read_text(), old_leaf)
            self.assertEqual(stamp(root, True), (3, 1))
            self.assertIn(digest(data), (root / 'leaf.js').read_text())
            self.assertEqual(find_mismatches(root), [])
            before = {p: p.stat().st_mtime_ns for p in root.iterdir()}
            self.assertEqual(stamp(root, True), (0, 0))
            self.assertEqual(before, {p: p.stat().st_mtime_ns for p in root.iterdir()})

    def test_scan_retains_compact_metadata_without_source_contents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload = '/*' + 'x' * 100000 + '*/"/data.json?v=old"'
            (root / 'page.js').write_text(payload)
            (root / 'data.json').write_text('{}')
            scan = _scan(root)
            def retained_text_bytes(value):
                if isinstance(value, bytes):
                    self.fail('scan retained file bytes')
                if isinstance(value, str):
                    return len(value.encode())
                if isinstance(value, dict):
                    return sum(retained_text_bytes(k) + retained_text_bytes(v)
                               for k, v in value.items())
                if isinstance(value, (tuple, list)):
                    return sum(map(retained_text_bytes, value))
                return 0
            self.assertLess(retained_text_bytes(scan), 1000)
            self.assertNotIn('x' * 1000, repr(scan))
            self.assertEqual(scan[1][root / 'page.js'],
                             [('/data.json', (root / 'data.json').resolve())])

    def test_missing_and_outside_targets_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            root = parent / 'site'
            root.mkdir()
            (parent / 'outside.js').write_text('outside')
            text = '"../outside.js?v=old"; "/missing.json?v=old"; "https://example.com/x.js?v=old";'
            page = root / 'index.html'
            page.write_text(text)
            self.assertEqual(stamp(root, True), (0, 0))
            self.assertEqual(page.read_text(), text)

    def test_cycle_aborts_before_any_write_and_check_stays_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            originals = {'a.js': '"/b.js?v=old"', 'b.js': '"/a.js?v=old"',
                         'leaf.js': '"/data.json?v=old"', 'data.json': '{}'}
            for name, text in originals.items():
                (root / name).write_text(text)
            self.assertEqual(stamp(root, False), (3, 3))
            with self.assertRaisesRegex(ValueError, 'Cyclic versioned asset dependencies'):
                stamp(root, True)
            self.assertEqual({p.name: p.read_text() for p in root.iterdir()}, originals)
            self.assertEqual(len(find_mismatches(root)), 3)

    def test_self_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'self.js').write_text('"/self.js?v=old"')
            with self.assertRaises(ValueError):
                stamp(root, True)

    def test_excluded_source_is_unchanged_but_consumers_use_its_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = '<script src="/shared.js?v=old"></script>\n'
            (root / 'shared.js').write_text(source)
            page = root / 'index.html'
            page.write_text('<script src="/shared.js?v=old"></script>\n')
            before = (root / 'shared.js').read_bytes()
            self.assertEqual(stamp(root, True, excludes=("shared.js",)), (1, 1))
            self.assertEqual((root / 'shared.js').read_bytes(), before)
            self.assertIn(digest(source), page.read_text())
            self.assertEqual(find_mismatches(root, excludes=("shared.js",)), [])

    def test_invalid_exclusion_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('')
            with self.assertRaisesRegex(ValueError, 'existing'):
                stamp(root, True, excludes=("missing.html",))


if __name__ == '__main__':
    unittest.main()
