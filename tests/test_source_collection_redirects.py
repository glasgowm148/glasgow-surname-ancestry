import tempfile
import unittest
from pathlib import Path
from tools.build_source_collections import publish_collection_redirects

class CollectionRedirectTests(unittest.TestCase):
    def test_reclassified_public_route_survives_repeated_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            web=Path(tmp);destination='/sources/deaths/scotland/1850-1899/';old='/sources/other/scotland/1850-1899/'
            target=web/destination.lstrip('/')/'index.html';target.parent.mkdir(parents=True);target.write_text('Reviewed inscriptions')
            template='<html><head><title>Sources</title><link rel="canonical" href="https://glasgow.phenotype.dev/sources/"></head><body><nav>Research</nav><main>Old collection</main></body></html>'
            for _ in range(2):
                self.assertEqual(publish_collection_redirects(web,template,{old:destination}),[old])
                text=(web/old.lstrip('/')/'index.html').read_text()
                self.assertIn('content="0;url='+destination+'"',text)
                self.assertIn('href="https://glasgow.phenotype.dev'+destination+'"',text)
                self.assertIn('<nav>Research</nav>',text)
                self.assertIn('Continue to the source collection',text)
            self.assertEqual(target.read_text(),'Reviewed inscriptions')

    def test_unavailable_or_external_destination_does_not_create_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            web=Path(tmp);old='/sources/other/scotland/1850-1899/'
            for destination in ['/sources/deaths/scotland/1850-1899/','https://example.org/']:
                with self.assertRaises(ValueError):publish_collection_redirects(web,'<head></head><main></main>',{old:destination})
                self.assertFalse((web/old.lstrip('/')).exists())
