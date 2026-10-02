"""Reviewed source journeys survive replacement of generated branch pages."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import publish_opr_death_review
from tools.publish_reviewed_collections import publish


class ReviewedCollectionsTests(unittest.TestCase):
    def test_publish_restores_downloads_and_matching_sections_without_dossier_writes(self):
        with TemporaryDirectory() as directory:
            web = Path(directory)
            for relative in ['branches/scottish-families/index.html','sources/index.html','catalogue.html','catalogue/index.html']:
                target = web / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('<html><head></head><body><main><h1>Existing page</h1></main></body></html>')
            with patch.object(publish_opr_death_review, 'qualify_glasgow_3056') as qualify:
                counts = publish(web)
                qualify.assert_not_called()
                self.assertEqual(counts['opr_birth_review_rows'], 127)
                self.assertEqual(counts['opr_death_review_rows'], 7)
                family = (web / 'branches/scottish-families/index.html').read_text()
                sources = (web / 'sources/index.html').read_text()
                for kind, expected in [('births',127),('deaths',7)]:
                    stem = f'scotlandspeople-opr-{kind}-to-1700'
                    self.assertEqual(len(json.loads((web / f'data/{stem}.json').read_text())['rows']), expected)
                    self.assertIn(f'id="opr-{kind}-to-1700"', family)
                    self.assertIn(f'href="/branches/scottish-families/#opr-{kind}-to-1700"', sources)
                    self.assertIn(f'href="/data/{stem}.json"', sources)
                first = {str(p.relative_to(web)):p.read_text() for p in web.rglob('*') if p.is_file()}
                publish(web)
                self.assertEqual(first, {str(p.relative_to(web)):p.read_text() for p in web.rglob('*') if p.is_file()})
                # A branch generator replaces its body; publication restores it.
                (web / 'branches/scottish-families/index.html').write_text('<main><h1>Rebuilt families</h1></main>')
                publish(web)
                rebuilt = (web / 'branches/scottish-families/index.html').read_text()
                self.assertIn('Rebuilt families', rebuilt)
                self.assertIn('id="opr-births-to-1700"', rebuilt)
                self.assertIn('id="opr-deaths-to-1700"', rebuilt)

