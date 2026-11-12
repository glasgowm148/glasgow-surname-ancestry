import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools import research_entry as entry


class EntryRegenerationTests(unittest.TestCase):
    def test_each_entry_kind_exports_only_its_own_view(self):
        cases = [(entry.views.RECORDS, 'records', [{'record_id': 'example'}]),
                 (entry.views.FINDINGS, 'findings', {'findings': []}),
                 (entry.views.VITALS, 'vitals', {'assessments': []})]
        for relative, method, expected in cases:
            with self.subTest(kind=method), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / relative).parent.mkdir(parents=True)
                generated = Mock()
                getattr(generated, method).return_value = expected
                generated.files.side_effect = AssertionError('Unrelated views were requested')
                with patch.object(entry.views, 'Views', return_value=generated):
                    entry.regenerate(SimpleNamespace(store=object()), relative, root)
                self.assertEqual(json.loads((root / relative).read_text()), expected)
                self.assertEqual([call[0] for call in generated.method_calls], [method])

    def test_other_view_paths_keep_the_existing_fallback(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            generated = Mock()
            generated.files.return_value = {'other.json': '{"preserved": true}\n'}
            with patch.object(entry.views, 'Views', return_value=generated):
                entry.regenerate(SimpleNamespace(store=object()), 'other.json', root)
            self.assertEqual(json.loads((root / 'other.json').read_text()), {'preserved': True})


if __name__ == '__main__':
    unittest.main()
