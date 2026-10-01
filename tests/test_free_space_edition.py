import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
from tools import free_space_edition as edition
from tools.public_privacy import PublicPrivacy
from tools.sync_free_space_edition import assessment, compare

class FreeSpaceEditionTests(unittest.TestCase):
    def test_rich_reading_preserves_tables_links_named_refs_and_escapes_scripts(self):
        pages=[{'wikitreeId':'Space:Second study','url':'/free-space/second/'}]
        text="== Evidence ==\nA '''proved''' occurrence [[Space:Second study|follow-up]]<ref name=record>[https://example.org/record Original register], p. 4.</ref>\n\n{| class=wikitable\n! Person !! Year\n|-\n| John || 1400<ref name=record/>\n|}\n\n* Item\n** Nested item\n<script>alert(1)</script>"
        html=edition.Renderer(pages).render(text);s=BeautifulSoup(html,'html.parser')
        self.assertEqual(s.h2.get_text(),'Evidence');self.assertEqual(s.find('a',href='/free-space/second/').get_text(),'follow-up')
        self.assertEqual([c.get_text(strip=True) for c in s.select('table td')],['John','1400[1]'])
        self.assertEqual(len(s.select('.fsp-citations li')),1);self.assertEqual(len(s.select('sup a[href="#citation-1"]')),2)
        self.assertIsNotNone(s.select_one('ul ul li'));self.assertNotIn('alert(1)',html)
    def test_sensitive_matches_are_withheld_without_losing_historical_account(self):
        policy=PublicPrivacy([('Living-1',{'IsLiving':1,'withheld':True})])
        text='== Historical research ==\n[[Glasgow-951|Alexander]] appears in 1851.\n\n== My Matches ==\nA named match with kit_num=SECRET and [[Living-1|Someone]].'
        public,removed=edition.public_text(text,policy,'Space:Personal genetic exploration')
        self.assertIn('1851',public);self.assertNotIn('SECRET',public);self.assertNotIn('Living-1',public);self.assertGreater(removed,0)
    def test_local_edits_survive_source_refresh_and_repeated_builds(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source_file=root/'source.wiki';source_file.write_text('Original source')
            meta={'wikitreeId':'Space:Study','title':'Study','category':'Families and case studies','localFile':'source.wiki'}
            source={'pages':[meta],'capturedAt':'2026-08-29'}
            with patch.object(edition,'ROOT',root),patch.object(edition,'EDITION',root/'edition.json'):
                page=edition.prepare([meta],source,{'studies':[]})[0];local=root/page['editionFile'];local.write_text('Local correction')
                source_file.write_text('Remote/source refresh')
                for _ in range(2):edition.prepare([meta],source,{'studies':[]});self.assertEqual(local.read_text(),'Local correction')
    def test_three_way_states_preserve_conflicts(self):
        self.assertEqual(assessment('a','a'),'Both editions match')
        self.assertIn('First comparison',assessment('a','b'))
        self.assertIn('WikiTree changed',assessment('base','new','base'))
        self.assertIn('Local changes',assessment('local','base','base'))
        self.assertIn('Both editions changed',assessment('local','remote','base'))
    def test_unresolved_first_comparison_stays_unresolved_on_a_repeat_pull(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'local.wiki';p.write_text('Maintained local account')
            page={'wikitreeId':'Space:Study','editionFile':str(p)}
            first=compare(page,'Different remote account',{})
            second=compare(page,'Different remote account',first)
            self.assertIn('First comparison',second['status'])
            self.assertIsNone(second['basePublicText'])

    def test_all_public_entries_have_local_reading_pages_and_safe_drafts(self):
        root=Path(__file__).resolve().parents[1];rows=json.loads((root/'www/assets/research/free-space-index.json').read_text())
        self.assertEqual(len(rows),85);self.assertEqual(len({r['wikitreeId'] for r in rows}),85)
        for row in rows:
            text=(root/'www'/row['url'].strip('/')/'index.html').read_text()
            self.assertIn('fsp-reading',text);self.assertIn('Complete local WikiTree draft',text);self.assertNotIn('kit_num=',text);self.assertNotIn('research/free-space-pages/',text)
        self.assertGreater(rows[0]['importance'],rows[-1]['importance'])
