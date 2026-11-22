import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from tools.build_source_collections import move_branch_tables, publish_collection_redirects

class CollectionRedirectTests(unittest.TestCase):
    def test_former_marriage_draft_anchor_opens_an_existing_master_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            scotland = web / 'branches/scottish-families/index.html'
            scotland.parent.mkdir(parents=True)
            scotland.write_text('<main><!-- opr-marriages-to-1700:start --><!-- opr-marriages-to-1700:end --></main></body>')
            ireland = web / 'branches/early-ireland/index.html'
            ireland.parent.mkdir()
            ireland.write_text('<main></main>')
            sections = {f'{kind}/scotland/opr-to-1700': '' for kind in ('births', 'marriages', 'deaths')}
            sections['marriages/scotland/opr-to-1700'] = '<tr id="opr-marriage-08"></tr><tr id="opr-marriage-32"></tr>'
            move_branch_tables(web, {'rows': [], 'conclusion': ''}, sections)
            soup = BeautifulSoup(scotland.read_text(), 'html.parser')
            target = soup.find(id='opr-marriage-identity-8-32')['data-source-target']
            self.assertEqual(target, soup.find(id='opr-marriage-08')['data-source-target'])
            self.assertIn('id=c-marriages-scotland-opr-to-1700-opr-marriage-08', target)

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
