"""Reviewed creation work must enter the actual catalogue, with complete evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

from bs4 import BeautifulSoup
from tools.site_analytics import with_analytics

spec = importlib.util.spec_from_file_location("queue_creations", Path(__file__).resolve().parents[1] / "tools/queue_catalogue_creations.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class QueueCatalogueCreationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.slug = "record-jane-glasgow-1775"
        self.url = "https://www.scotlandspeople.gov.uk/record/1775-jane"
        self.draft = '''[[Category:Glasgow Name Study]]
== Biography ==
Jane Glasgow was named as John Smith's wife in a deed in 1775.<ref>[https://www.scotlandspeople.gov.uk/record/1775-jane Deed, 1775], Jane Glasgow, wife of John Smith.</ref>
== Research Notes ==
The deed does not give her birth date. No compatible profile survived the documented review.
== Sources ==
<references />'''
        self.entry = {
            "subject_id": "jane-1775", "catalogue_id": self.slug, "name": "Jane Glasgow",
            "source_subject_url": self.url, "draft_path": "research/drafts/jane.wiki", "draft_wikitext": self.draft,
            "assessment": "The deed identifies Jane Glasgow as John Smith's wife; the 1775 occurrence is not a birth date.",
            "first_names": ["Jane"], "last_names_at_birth": ["Glasgow"], "last_names_current": ["Smith"], "gender": "Female",
            "birth": "", "birth_location": "", "death": "", "death_location": "",
            "records": [{"person": "Jane Glasgow", "year": "1775", "filter_year": 1775, "family_group": "Scottish deeds",
                "record_location": "Edinburgh, Scotland", "association": "Wife of John Smith in a deed", "note": "Her husband John Smith was a merchant.",
                "evidence": "Proved", "source_title": "Deed, 1775", "source_url": self.url, "source_type": "original"}],
        }
        path = self.root / self.entry["draft_path"]
        path.parent.mkdir(parents=True)
        path.write_text(self.draft)
        (self.root / "www/people").mkdir(parents=True)
        (self.root / "www/people/glasgow-1521.html").write_text('''<!doctype html><html><head><title>William Glasgow</title></head>
<body><aside class="g-rail">Shared navigation</aside><main class="v3-dossier"></main></body></html>''')
        self.save()

    def save(self):
        path = self.root / module.MANIFEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"new_people": [self.entry], "profile_updates": {}}))

    def read(self, relative):
        return json.loads((self.root / "www" / relative).read_text())

    def test_native_merge_into_existing_profile_does_not_recreate_duplicate(self):
        web = self.root / 'www'
        target = 'Example-2'
        (web / 'people/example-2.html').write_text('Existing profile')
        for relative, value in [
            ('data/people.json', {'people': [{'catalogue_id': 'example-2', 'records': []},
                                           {'catalogue_id': self.slug, 'records': []}]}),
            ('assets/research/record-index.json', [{'id': 'original-record', 'p': self.slug}]),
        ]:
            path = web / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        route = web / 'assets/unified/routes.js'
        route.parent.mkdir(parents=True, exist_ok=True)
        route.write_text('window.GlasgowRoutes=' + json.dumps({self.slug: 'example-2'}) + ';')
        original = (self.root / module.MANIFEST).read_bytes()
        with patch.object(module, 'native_creation_merges', return_value=({self.slug: target}, {})):
            result = module.apply_creations(self.root)
        self.assertEqual(0, result['count'])
        self.assertEqual(['example-2'], [p['catalogue_id'] for p in self.read('data/people.json')['people']])
        self.assertEqual('example-2', self.read('people/' + self.slug + '.json')['native_merge_redirect'])
        self.assertEqual('original-record', self.read('assets/research/record-index.json')[0]['id'])
        self.assertEqual('example-2', self.read('assets/research/record-index.json')[0]['p'])
        self.assertEqual(original, (self.root / module.MANIFEST).read_bytes())
        with patch.object(module, 'native_creation_merges', return_value=({}, {})):
            restored = module.apply_creations(self.root)
        self.assertEqual(1, restored['count'])
        self.assertNotIn('native_merge_redirect', self.read('people/' + self.slug + '.json'))
        self.assertEqual(self.slug, self.read('assets/research/record-index.json')[0]['p'])

    def test_targeted_statistics_refreshes_hero_panels_and_artifact_preserving_shell(self):
        web = self.root / 'www'
        for relative in ('catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html'):
            path = web / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<main><section class="catalogue-hero"><p class="lede">Search 9 people.</p>'
                '<strong id="catalogue-total">9</strong></section><section id="statistics">Old counts</section>'
                '<section id="catalogue-search-panel">Keep search controls</section></main>')
        stats = web / 'statistics/index.html'
        stats.parent.mkdir(parents=True)
        stats.write_text('<main><h1>Keep statistics layout</h1><div class="statistics-summary">Old</div>'
            '<div class="statistics-grid">Old</div><p class="statistics-caution">Old</p></main>')
        module.apply_creations(self.root)
        for relative in ('catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html'):
            soup = BeautifulSoup((web / relative).read_text(), 'html.parser')
            self.assertIn('Search 1 historical people', soup.select_one('.lede').text)
            self.assertEqual('1', soup.select_one('#catalogue-total').text)
            self.assertIn('catalogue-statistics-compact', soup.select_one('#statistics')['class'])
            self.assertEqual('Keep search controls', soup.select_one('#catalogue-search-panel').text)
        self.assertIn('Keep statistics layout', stats.read_text())
        self.assertNotIn('>Old<', stats.read_text())
        artifact = BeautifulSoup(self.read('data/catalogue-statistics.json')['html'], 'html.parser')
        self.assertEqual('1', artifact.select_one('.statistics-summary strong').text)
        self.assertEqual('1', artifact.select('.statistics-summary strong')[1].text)

    def test_retired_context_removes_search_identity_preserves_record_event_rows(self):
        old, current = 'record-retired', self.slug
        web = self.root / 'www'
        fixtures = {
            'assets/research/registry.json': [{'slug': old}, {'slug': current}],
            'assets/research/search-people.json': [{'id': old}, {'id': current}],
            'assets/research/search-index.json': [{'id': old}, {'id': 'source-id'}],
            'assets/v3/search-people.json': [[old, 'Old'], [current, 'Current']],
            'assets/v3/people-quick.json': [[old, 'Old'], [current, 'Current']],
            'assets/v3/registry-packed.json': {'fields': ['name', 'slug'], 'rows': [['Old', old], ['Current', current]]},
            'assets/research/record-index.json': [{'id': 'record-1', 'p': old, 'title': 'Original wording'}],
            'assets/research/event-index.json': [{'p': old, 'participants': [{'id': old, 'role': 'father'}]}],
        }
        for relative, value in fixtures.items():
            target = web / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value))
        module.retire_creation_context(web, {old: current})
        self.assertEqual([{'slug': current}], self.read('assets/research/registry.json'))
        self.assertEqual([[current, 'Current']], self.read('assets/v3/people-quick.json'))
        self.assertEqual([['Current', current]], self.read('assets/v3/registry-packed.json')['rows'])
        record = self.read('assets/research/record-index.json')[0]
        self.assertEqual(('record-1', current, 'Original wording'), (record['id'], record['p'], record['title']))
        self.assertEqual(old, record['native_merge_original_person'])
        participant = self.read('assets/research/event-index.json')[0]['participants'][0]
        self.assertEqual(current, participant['id'])
        self.assertEqual(old, participant['native_merge_original_id'])
        self.assertIn(current, self.read('assets/research/people/' + old + '.json')['redirect_to'])
        module.retire_creation_context(web, {}, restored={old})
        self.assertEqual(old, self.read('assets/research/record-index.json')[0]['p'])
        self.assertEqual(old, self.read('assets/research/event-index.json')[0]['participants'][0]['id'])

    def test_merge_fills_only_consistent_empty_scalars_and_filters_self_candidates(self):
        other = deepcopy(self.entry)
        other.update(catalogue_id='record-other', birth='1700', gender='Female',
                     candidates=[{'profile_id': self.slug}, {'profile_id': 'record-other'}, {'profile_id': 'Example-2'}])
        projected = module._project_creation_merges([self.entry, other], {'record-other': self.slug}, {})[0]
        self.assertEqual('1700', projected['birth'])
        self.assertEqual([{'profile_id': 'Example-2'}], projected['candidates'])
        self.assertEqual(3, len(projected['merged_source_accounts'][1]['candidates']))
        other['gender'] = 'Male'
        with self.assertRaisesRegex(ValueError, 'conflicting gender'):
            module._project_creation_merges([self.entry, other], {'record-other': self.slug}, {})

    def test_native_merge_projects_all_sources_preserves_hold_and_undo(self):
        from genealogy.cli import initialize_project
        from genealogy.store import Research, open_project
        other = deepcopy(self.entry)
        old = 'record-jane-another-account'
        other.update(catalogue_id=old, subject_id='jane-other',
                     source_subject_url='https://example.org/deed-1785',
                     draft_path='research/drafts/other.wiki', creation_status='identity_hold',
                     candidates=[{'profile_id': 'Example-2', 'note': 'Still a candidate'}])
        other['records'][0]['source_url'] = other['source_subject_url']
        other['draft_wikitext'] = self.draft.replace(self.url, other['source_subject_url']).replace(
            '<ref>', '<ref name="shared citation">').replace('== Research Notes ==',
            'A reused citation.<ref name="shared citation" />\n== Research Notes ==')
        (self.root / other['draft_path']).write_text(other['draft_wikitext'])
        manifest = self.root / module.MANIFEST
        manifest.write_text(json.dumps({'new_people': [self.entry, other]}))
        original_manifest = manifest.read_bytes()
        import shutil
        native = self.root / 'native'
        initialize_project(native, 'Fictional duplicate research')
        (self.root / 'genealogy.toml').write_text((native / 'genealogy.toml').read_text())
        with open_project(native) as project:
            relative_database = project.settings.database
            database = project.database_path
        target_database = self.root / relative_database
        target_database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(database, target_database)
        with open_project(self.root) as project:
            research = Research(project.store)
            with project.store.write(actor='test') as tx:
                for ident, alias in [('survivor', self.slug), ('retired', old)]:
                    research.create_person(tx, id=ident)
                    research.map_external(tx, ident, 'glasgow-local', alias)
                merge = research.merge_people(tx, survivor_id='survivor', retired_id='retired',
                    reason='Same deed subject; wider identity remains on hold')
        projected = module.reviewed_people(self.root, [self.slug])
        self.assertEqual(1, len(projected))
        entry = projected[0]
        self.assertEqual('identity_hold', entry['creation_status'])
        self.assertEqual(2, len(entry['records']))
        self.assertEqual(2, len(entry['merged_source_accounts']))
        self.assertEqual(other['candidates'], entry['candidates'])
        self.assertIn('wider identity remains on hold', entry['assessment'])
        self.assertIn('name="merged1-shared citation"', entry['draft_wikitext'])
        self.assertEqual(2, entry['draft_wikitext'].count('name="merged1-shared citation"'))
        self.assertIn(other['source_subject_url'], entry['draft_wikitext'])
        self.assertEqual([self.slug], [row['catalogue_id'] for row in
            module.reviewed_people(self.root, [old])])
        web = self.root / 'www'
        route = web / 'assets/unified/routes.js'
        route.parent.mkdir(parents=True)
        route.write_text('window.GlasgowRoutes=' + json.dumps({old: old}) + ';')
        for path, data in [('data/people.json', {'people': [{'catalogue_id': old}]}),
                           ('data/catalogue-search-index.json', [{'id': old}]),
                           ('data/people-index.json', [{'catalogue_id': old, 'id': old}])]:
            target = web / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data))
        module.apply_creations(self.root, [self.slug])
        self.assertEqual([self.slug], [row['catalogue_id'] for row in self.read('data/people.json')['people']])
        self.assertNotIn(old, [row['id'] for row in self.read('data/catalogue-search-index.json')])
        self.assertIn(self.slug + '.html', (web / 'people' / (old + '.html')).read_text())
        self.assertEqual(self.slug, self.read('people/' + old + '.json')['native_merge_redirect'])
        self.assertEqual(2, len(self.read('people/' + self.slug + '.json')['provenance']['merged_source_accounts']))
        self.assertEqual(original_manifest, manifest.read_bytes())
        with open_project(self.root) as project:
            with project.store.write(actor='test') as tx:
                Research(project.store).undo_merge(tx, merge, reason='Test reversal')
        self.assertEqual(2, len(module.reviewed_people(self.root)))
        module.apply_creations(self.root)
        self.assertEqual(2, len(self.read('data/people.json')['people']))
        self.assertNotIn('native_merge_redirect', self.read('people/' + old + '.json'))

    def test_external_relative_links_use_existing_accounts_without_new_people(self):
        row={'id':'Example-2','url':'/people/example-2.html',
             'wikitree_url':'https://www.wikitree.com/wiki/Example-2'}
        dossier={'relationships':{'parents':[row]}}
        with module._root_paths(self.root) as cases:
            cases.resolve_relative_urls(dossier,{'Example-2':'example-2'})
            self.assertEqual('/people/example-2.html',row['url'])
            cases.resolve_relative_urls(dossier,{})
            self.assertEqual(row['wikitree_url'],row['url'])
            self.assertEqual('Example-2',row['id'])
            # Imported external relatives can explicitly have no local URL.
            missing={'id':'Example-3','url':None}
            cases.resolve_relative_urls({'relationships':{'parents':[missing]}},{})
            self.assertIsNone(missing['url'])
            account=self.root/'research/ancestry-connections/documentary-people.json'
            account.parent.mkdir(parents=True,exist_ok=True)
            account.write_text(json.dumps({'people':[{'id':'record-parent-1600','name':'Parent',
                'publication_status':'approved','source_ids':['record-1600'],'first_record_year':1600,
                'url':'/research/subjects/ancient/#parent'}]}))
            page=self.root/'www/research/subjects/ancient/index.html'
            page.parent.mkdir(parents=True);page.write_text('<h1 id="parent">Parent</h1>')
            parent={'id':'record-parent-1600','url':'/people/record-parent-1600.html'}
            cases.resolve_relative_urls({'relationships':{'parents':[parent]}},{})
            self.assertEqual('/research/subjects/ancient/#parent',parent['url'])

    def test_source_subject_url_redirects_to_canonical_case(self):
        module.apply_creations(self.root)
        path=self.root/'www/people/jane-1775.html'
        self.assertIn(self.slug+'.html',path.read_text())
        canonical_legacy=self.root/'www/people/jane-glasgow-1775.html'
        self.assertIn(self.slug+'.html',canonical_legacy.read_text())
        self.assertEqual(0,module.publish_creation_aliases(self.root,[self.entry]))

    def test_source_subject_alias_never_overwrites_an_active_person(self):
        module.apply_creations(self.root)
        path=self.root/'www/people/jane-1775.html';path.write_text('Different existing person')
        data=self.read('data/people.json');data['people'].append({'catalogue_id':'jane-1775'})
        (self.root/'www/data/people.json').write_text(json.dumps(data))
        self.assertEqual(0,module.publish_creation_aliases(self.root,[self.entry]))
        self.assertEqual('Different existing person',path.read_text())

    def test_canonical_record_from_another_builder_keeps_its_legacy_url(self):
        module.apply_creations(self.root)
        data=self.read('data/people.json');data['people'].append({'catalogue_id':'record-other-case'})
        (self.root/'www/data/people.json').write_text(json.dumps(data))
        (self.root/'www/people/record-other-case.html').write_text('Existing complete account')
        self.assertEqual(1,module.publish_creation_aliases(self.root,[]))
        self.assertIn('record-other-case.html',(self.root/'www/people/other-case.html').read_text())

    def test_batch_keeps_same_name_people_and_their_sources_distinct(self):
        other = deepcopy(self.entry)
        other.update(subject_id='jane-1785', catalogue_id='record-jane-glasgow-1785')
        other['source_subject_url'] = 'https://www.scotlandspeople.gov.uk/record/1785-jane'
        other['draft_wikitext'] = other['draft_wikitext'].replace(self.url, other['source_subject_url'])
        other['draft_path'] = 'research/drafts/jane-1785.wiki'
        (self.root / other['draft_path']).write_text(other['draft_wikitext'])
        other['records'][0].update(year='1785', filter_year=1785,
                                   source_url='https://www.scotlandspeople.gov.uk/record/1785-jane')
        (self.root / module.MANIFEST).write_text(json.dumps({'new_people': [self.entry, other]}))
        with patch.object(module.catalogue, '_build_people', wraps=module.catalogue._build_people) as build:
            result = module.apply_creations(self.root)
        self.assertEqual(1, build.call_count)
        self.assertEqual(2, result['count'])
        people = {r['catalogue_id']: r for r in self.read('data/people.json')['people']}
        for entry in (self.entry, other):
            self.assertEqual([entry['records'][0]['source_url']],
                             [r['source_url'] for r in people[entry['catalogue_id']]['records']])

    def test_plain_catalogue_main_can_supply_a_case_shell(self):
        template = self.root / 'www/people/glasgow-1521.html'
        template.write_text('<html><head><title>Old subject</title></head><body>'
                            '<aside>Shared navigation</aside><main id="main">Old subject body</main></body></html>')
        result = module.apply_creations(self.root)
        self.assertEqual(1, result['count'])
        html = (self.root / 'www/people' / (self.slug + '.html')).read_text()
        soup = BeautifulSoup(html, 'html.parser')
        self.assertIsNotNone(soup.select_one('main.v3-dossier'))
        self.assertIn('Shared navigation', soup.get_text())
        self.assertNotIn('Old subject body', soup.get_text())

    def test_creation_search_uses_reviewed_father_and_keeps_unknown_mother(self):
        assessment = {
            "assertion_id": "C-reviewed-jane-father", "people": [self.slug, "Glasgow-9001"],
            "profile_names": {self.slug: "Jane Glasgow", "Glasgow-9001": "William Glasgow"},
            "status": "strongly_supported", "publication_status": "approved",
            "working_selection": True, "allow_new_relationship": True,
            "basis": "Reviewed deed identifies Jane's father.",
            "source_ids": ["test-deed-1775"],
            "perspectives": {
                self.slug: {"relationship": "father", "reason": "The reviewed deed names her father."},
                "Glasgow-9001": {"relationship": "daughter", "reason": "The reviewed deed names Jane."},
            },
        }
        path = self.root / "research/relationship_assessments.json"
        path.write_text(json.dumps([assessment]))
        for _ in range(2):
            module.apply_creations(self.root)
            dossier = self.read(f"people/{self.slug}.json")
            row = self.read("data/catalogue-search-index.json")[0]
            self.assertEqual(dossier["relationships"]["parents"][0]["id"], "Glasgow-9001")
            self.assertEqual([p["id"] for p in row["father"]], ["Glasgow-9001"])
            self.assertFalse(row["missing_father"])
            self.assertTrue(row["missing_mother"])
            self.assertEqual(row["mother"], [])

    def test_integrates_main_filters_complete_draft_evidence_and_is_idempotent(self):
        self.assertEqual(module.apply_creations(self.root)["count"], 1)
        module.apply_creations(self.root)
        people = self.read("data/people.json")
        self.assertEqual(people["count"], 1)
        person = people["people"][0]
        self.assertEqual(person["last_names_current"], ["Smith"])
        self.assertEqual(person["birth"], "")
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertTrue(row["missing_profile"])
        self.assertTrue(row["needs_wikitree_update"])
        self.assertEqual(row["profile_work_status"], "creation_ready")
        self.assertFalse(person["uncertain_identity"])
        self.assertFalse(row["uncertain_identity"])
        self.assertGreater(row["wikitree_update_significance"], 0)
        self.assertIsNone(row["birth_year"])
        self.assertEqual(row["date_years"], [1775])
        self.assertEqual(row["record_count"], 1)
        self.assertEqual(self.read("data/people-index.json")[0]["catalogue_id"], self.slug)
        dossier = self.read(f"people/{self.slug}.json")
        self.assertEqual(dossier["wikitree_update"]["proposed_wikitext"], self.draft)
        self.assertEqual(dossier["evidence"][0]["source"]["url"], self.url)
        self.assertTrue(dossier["research_findings"])
        self.assertTrue((self.root / f"www/people/{self.slug}.network.json").exists())
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        html = (self.root / f"www/people/{self.slug}.html").read_text()
        self.assertEqual(html, with_analytics(html))
        self.assertEqual(soup.select_one("#profile-update-draft").get_text(), self.draft)
        self.assertIsNotNone(soup.select_one(f'a[href="/people/{self.slug}.json"]'))
        self.assertIn("Create a new WikiTree profile", soup.get_text())
        self.assertIn("John Smith was a merchant", soup.get_text())
        self.assertIn(self.url, [link["href"] for link in soup.select("a[href]")])
        self.assertIsNotNone(soup.select_one("aside.g-rail"))
        self.assertNotIn("Side-by-side", soup.get_text())
        self.assertNotIn("baptism", soup.get_text())

    def test_creation_registers_local_route_and_preserves_other_script_data(self):
        path = self.root / 'www/assets/unified/routes.js'
        path.parent.mkdir(parents=True)
        suffix = ';\nwindow.GlasgowIcons={"keep":"icon"};\n'
        path.write_text('window.GlasgowRoutes={"glasgow-1521":"glasgow-1521"}' + suffix)
        module.apply_creations(self.root)
        text = path.read_text()
        routes, _ = json.JSONDecoder().raw_decode(text[len('window.GlasgowRoutes='):])
        self.assertEqual(routes[self.slug], self.slug)
        self.assertEqual(routes['glasgow-1521'], 'glasgow-1521')
        self.assertTrue(text.endswith(suffix))
        module.apply_creations(self.root)
        self.assertEqual(path.read_text(), text)

    def test_creation_does_not_overwrite_a_reviewed_route_alias(self):
        path = self.root / 'www/assets/unified/routes.js'
        path.parent.mkdir(parents=True)
        text = 'window.GlasgowRoutes=' + json.dumps({self.slug: 'glasgow-1521'}) + ';'
        path.write_text(text)
        with self.assertRaisesRegex(ValueError, 'existing route alias'):
            module.apply_creations(self.root)
        self.assertEqual(path.read_text(), text)
        self.assertFalse((self.root / f'www/people/{self.slug}.html').exists())

    def test_canonical_findings_override_manifest_and_preserve_hold_candidates(self):
        self.entry.update(creation_status="identity_hold", candidates=[
            {"name": f"Candidate {i}", "profile_id": f"Glasgow-{9000+i}", "status": "HOLD"} for i in range(6)
        ])
        self.save()
        findings = self.root / "research" / self.slug / "findings.md"
        findings.parent.mkdir(parents=True)
        findings.write_text("Last updated: 2026-10-26\n\n## Fresh source review\nCanonical body.\n")
        module.apply_creations(self.root, [self.slug])
        dossier = self.read(f"people/{self.slug}.json")
        self.assertEqual(dossier["provenance"]["research_findings"], f"research/{self.slug}/findings.md")
        self.assertIn("Canonical body.", json.dumps(dossier["research_findings"]))
        self.assertEqual(len(dossier["profile_work"]["candidates"]), 6)
        self.assertEqual(dossier["creation_status"], "identity_hold")
        html = (self.root / f"www/people/{self.slug}.html").read_text()
        self.assertIn("Canonical body.", html)
        self.assertIn(self.draft.replace("<", "&lt;").replace(">", "&gt;"), html)

    def test_reconciles_existing_canonical_rows_without_duplicates(self):
        module.apply_creations(self.root)
        self.entry["assessment"] = "Revised, reviewed identity explanation."
        self.save()
        module.apply_creations(self.root)
        self.assertEqual(len(self.read("data/catalogue-search-index.json")), 1)
        self.assertEqual(len(self.read("data/people-index.json")), 1)
        self.assertEqual(self.read(f"people/{self.slug}.json")["research_findings"][0]["sections"][0]["markdown"], self.entry["assessment"])

    def test_second_apply_refreshes_four_context_indexes_in_place(self):
        files = ("assets/research/search-people.json", "assets/research/search-index.json",
                 "assets/v3/search-people.json", "assets/v3/people-quick.json")
        registry = self.root / "www/assets/research/registry.json"
        registry.parent.mkdir(parents=True)
        (registry.parent / "people").mkdir()
        registry.write_text(json.dumps([{"id": "unrelated-before", "slug": "unrelated-before"}]))
        packed = self.root / "www/assets/v3/registry-packed.json"
        packed.parent.mkdir(parents=True)
        packed.write_text(json.dumps({"fields": ["id", "slug", "name"], "rows": []}))
        before_rows = {}
        after_rows = {}
        for relative in files:
            compact = "/v3/" in relative
            before_rows[relative] = (["unrelated-before", "1786 Glasgow remains unchanged", "x", "y", "z"] if compact else
                                     {"id": "unrelated-before", "life": "1786", "place": "Glasgow", "custom": True})
            after_rows[relative] = (["unrelated-after", "Keep", "a", "b", "c"] if compact else
                                    {"id": "unrelated-after", "custom": "Keep"})
            (self.root / "www" / relative).write_text(json.dumps([before_rows[relative]]))
        self.entry.update(birth="1775", birth_location="Glasgow, Scotland")
        self.save()
        module.apply_creations(self.root, [self.slug])
        # Existing selected rows keep their position, and any old duplicate is retired.
        for relative in files:
            path = self.root / "www" / relative
            rows = json.loads(path.read_text())
            rows.extend([after_rows[relative], rows[1]])
            path.write_text(json.dumps(rows))
        self.entry.update(birth="on or before 1775", birth_location="", birth_note="Bound from the documented event.")
        self.save()
        module.apply_creations(self.root, [self.slug])
        for relative in files:
            rows = self.read(relative)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0], before_rows[relative])
            self.assertEqual(rows[2], after_rows[relative])
            if "/v3/" in relative:
                self.assertEqual(rows[1][0], self.slug)
                self.assertIn("on or before 1775", rows[1][2 if "people-quick" in relative else 3])
                self.assertNotIn("Glasgow, Scotland", json.dumps(rows[1]))
                if "people-quick" in relative:
                    self.assertEqual(rows[1][3], "")
            else:
                self.assertEqual(rows[1]["id"], self.slug)
                self.assertIn("on or before 1775", rows[1]["life"])
                self.assertEqual(rows[1]["place"], "")

    def test_fresh_page_shows_approved_family_without_captured_attachments(self):
        study = '/branches/scottish-deeds/#chapter-family'
        self.entry['assessment'] += f' [Family study]({study}). [Local notes](research/private.md).'
        self.save()
        brother = 'record-peter-glasgow-1775'
        assessments = [{
            'assertion_id': 'C-test-record-siblings', 'people': [self.slug, brother],
            'publication_status': 'approved', 'status': 'proved', 'allow_new_relationship': True,
            'profile_names': {brother: 'Peter Glasgow'},
            'profile_urls': {brother: {'url': f'/people/{brother}.html'}},
            'claim': 'Jane and Peter are siblings', 'basis': 'Named in the deed.',
            'source_ids': ['test-deed-1775'],
            'perspectives': {self.slug: {'relationship': 'sibling', 'reason': 'Named in the deed.'},
                             brother: {'relationship': 'sibling', 'reason': 'Named in the deed.'}},
        }]
        path = self.root / 'research/relationship_assessments.json'
        path.write_text(json.dumps(assessments))
        module.apply_creations(self.root)
        soup = BeautifulSoup((self.root / f'www/people/{self.slug}.html').read_text(), 'html.parser')
        family = soup.select_one('#family')
        self.assertIn('Siblings', family.get_text())
        self.assertIn('Peter Glasgow', family.get_text())
        self.assertIsNotNone(family.select_one(f'a[href="/people/{brother}.html"]'))
        self.assertNotIn('No family attachments', family.get_text())
        self.assertNotIn('wikitree.com/wiki/record-', str(family))
        self.assertIsNotNone(soup.select_one(f'a[href="{study}"]'))
        self.assertIsNone(soup.select_one('a[href="research/private.md"]'))
        siblings = self.read(f'people/{self.slug}.json')['relationships']['siblings']
        self.assertEqual([row['id'] for row in siblings], [brother])
        network = self.read(f'people/{self.slug}.network.json')
        self.assertTrue(any(row['id'] == brother for row in network['relationships']))

    def test_rejects_uncited_incomplete_or_nonhistorical_entries_before_writes(self):
        for field, value in (("draft_wikitext", "== Biography ==\nEmpty"), ("records", []), ("living", True)):
            with self.subTest(field=field):
                original = self.entry.get(field)
                self.entry[field] = value
                self.save()
                with self.assertRaises(ValueError):
                    module.apply_creations(self.root)
                self.assertFalse((self.root / "www/data/people.json").exists())
                if original is None:
                    del self.entry[field]
                else:
                    self.entry[field] = original

    def test_rejects_editorial_footer_even_when_the_biography_is_complete(self):
        for footer in ('\n```\n\n## Relationship and source cautions\nDo not copy this.',
                       '\n\n## Identity review — editing log\nNot profile text.'):
            self.entry['draft_wikitext'] = self.draft + footer
            (self.root / self.entry['draft_path']).write_text(self.entry['draft_wikitext'])
            self.save()
            with self.assertRaisesRegex(ValueError, 'editorial Markdown'):
                module.apply_creations(self.root)

    def test_rejects_canonical_collision_with_linked_profile(self):
        data = self.root / "www/data"
        data.mkdir()
        (data / "people.json").write_text(json.dumps({"people": [{"catalogue_id": self.slug, "profile_ids": ["Glasgow-123"]}]}))
        with self.assertRaisesRegex(ValueError, "collision"):
            module.apply_creations(self.root)
        self.assertFalse((data / "catalogue-search-index.json").exists())

    def test_explicit_case_ignores_unrelated_invalid_draft_before_validation(self):
        broken = dict(self.entry, catalogue_id="record-unrelated-walter",
                      draft_path="research/drafts/walter.wiki")
        broken_path = self.root / broken["draft_path"]
        broken_path.write_text("Unrelated existing draft awaiting its own review.")
        manifest = self.root / module.MANIFEST
        manifest.write_text(json.dumps({"new_people": [broken, self.entry]}))
        before_manifest = manifest.read_bytes()
        before_draft = broken_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "maintained draft does not contain reviewed text"):
            module.reviewed_people(self.root)
        selected = [self.slug]
        self.assertEqual(module.reviewed_people(self.root, selected), [self.entry])
        self.assertEqual(len(module.reviewed_records(self.root, selected)), 1)
        self.assertEqual(set(module.reviewed_audits(self.root, selected)), {self.slug})
        self.assertEqual(module.apply_creations(self.root, selected)["integrated"], selected)
        self.assertEqual(broken_path.read_bytes(), before_draft)
        self.assertEqual(manifest.read_bytes(), before_manifest)
        self.assertFalse((self.root / "www/people/record-unrelated-walter.json").exists())
        self.assertEqual([p["catalogue_id"] for p in self.read("data/people.json")["people"]], selected)

    def test_unknown_or_duplicate_explicit_selection_fails_before_writes(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for selected, error in (([self.slug, "record-unknown"], "Unknown requested"),
                                ([self.slug, self.slug], "Duplicate requested")):
            with self.subTest(selected=selected):
                with self.assertRaisesRegex(ValueError, error):
                    module.apply_creations(self.root, selected)
                after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                self.assertEqual(after, before)

    def test_source_verification_hold_remains_visible_without_creation_ready_claim(self):
        self.entry["creation_status"] = "hold_source_verification"
        self.save()
        module.apply_creations(self.root)
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertTrue(row["missing_profile"])
        self.assertTrue(row["needs_wikitree_update"])
        self.assertFalse(row["creation_ready"])
        self.assertEqual(row["profile_work_status"], "identity_hold")
        self.assertFalse(row["uncertain_identity"])
        self.assertFalse(self.read("data/people.json")["people"][0]["uncertain_identity"])
        self.assertIn("verify the source before creation", row["wikitree_update_summary"])
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        self.assertIn("source verification on HOLD", soup.get_text())
        self.assertNotIn("Create a new WikiTree profile", soup.get_text())
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["recommended_action"], "hold")
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["identity_status"], "hold_source_verification")
        self.assertNotIn("identity on HOLD", soup.get_text())

    def test_identity_hold_preserves_reviewed_candidates_and_counts(self):
        candidates = [{"profile_id": "Glasgow-321", "name": "Jane Glasgow",
                       "url": "https://www.wikitree.com/wiki/Glasgow-321",
                       "assessment": "Compatible locality; spouse unresolved.",
                       "status": "compatible", "reviewed_at": "2026-10-17"}]
        self.entry.update(creation_status="identity_hold", candidates=candidates)
        self.save()
        audit = module.reviewed_audits(self.root)[self.slug]
        self.assertEqual(audit["identity_status"], "identity_hold")
        self.assertEqual(audit["candidates"], candidates)
        module.apply_creations(self.root)
        person = self.read("data/people.json")["people"][0]
        row = self.read("data/catalogue-search-index.json")[0]
        dossier = self.read(f"people/{self.slug}.json")
        self.assertEqual(person["creation_candidates"], candidates)
        self.assertEqual(person["profile_work_candidate_count"], 1)
        self.assertEqual(row["profile_work_candidate_count"], 1)
        self.assertEqual(row["profile_work_status"], "existing_profile_candidate")
        self.assertTrue(person["uncertain_identity"])
        self.assertTrue(row["uncertain_identity"])
        self.assertEqual(dossier["profile_work"]["candidates"], candidates)
        self.assertEqual(dossier["wikitree_update"]["candidates"], candidates)
        self.assertEqual(dossier["wikitree_update"]["candidate_count"], 1)
        self.assertFalse(row["creation_ready"])
        self.assertIn("resolve the identity before creation", row["wikitree_update_summary"])
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        panel = soup.select_one("#wikitree-update")
        self.assertIn("identity on HOLD", panel.get_text())
        self.assertIn("Reviewed possible existing-profile matches (1)", panel.get_text())
        self.assertIsNotNone(panel.select_one('a[href="https://www.wikitree.com/wiki/Glasgow-321"]'))
        self.assertNotIn("source verification on HOLD", soup.get_text())
        self.assertNotIn("verify the source before creation", soup.get_text())

    def test_identity_hold_classification_tracks_compatible_candidates(self):
        self.entry["creation_status"] = "identity_hold"
        candidates = [{"profile_id": "Glasgow-1227", "status": "compatible_candidate"},
                      {"profile_id": "Glasgow-1235", "status": "compatible_candidate"}]
        for reviewed_candidates, expected in ((candidates, "existing_profile_candidate"), ([], "identity_hold")):
            with self.subTest(candidate_count=len(reviewed_candidates)):
                self.entry["candidates"] = reviewed_candidates
                person = module.decorate_person({}, self.entry)
                self.assertEqual(person["profile_work_status"], expected)
                self.assertEqual(person["profile_work_candidate_count"], len(reviewed_candidates))
                self.assertEqual(person["creation_status"], "identity_hold")
                self.assertTrue(person["pending_profile_creation"])
                self.assertFalse(person["creation_ready"])
                self.assertTrue(person["uncertain_identity"])
                audit = {"recommended_action": "hold", "candidates": reviewed_candidates}
                self.assertEqual(module.catalogue._profile_work_status(person, audit), expected)

    def test_age_supported_later_record_does_not_fabricate_birth(self):
        self.entry["records"][0].update(year="1911", filter_year=1911)
        self.entry["historical_basis"] = {"earliest_birth_year": 1840, "latest_birth_year": 1841, "source_url": self.url}
        self.save()
        module.apply_creations(self.root)
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertIsNone(row["birth_year"])
        self.assertEqual(row["birth"], "")
        del self.entry["historical_basis"]
        self.save()
        with self.assertRaisesRegex(ValueError, "historical"):
            module.reviewed_people(self.root)

    def test_builder_hooks_keep_unknown_vitals_and_pending_creation(self):
        records = module.reviewed_records(self.root)
        self.assertEqual(records[0]["birth_status"], "unknown")
        people = module.catalogue._build_people(records, {}, [], {}, {"profiles": {}})
        person = module.decorate_person(people[0], self.entry)
        self.assertEqual(person["birth"], "")
        self.assertEqual(person["birth_location"], "")
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["recommended_action"], "create_new_profile")
        self.assertEqual(module.creation_update(person)["action"], "create_new_profile")
        self.assertIsNone(module.creation_update({"profile_ids": ["Glasgow-123"]}))

    def test_reviewed_person_occupations_override_relative_mentions_in_dossiers(self):
        cases = [
            ([], "Her husband John Smith was a merchant."),
            (["gardener"], "Charles was a gardener; his father Thos was a labourer."),
            (["labourer"], "John appears in the family roster."),
        ]
        for occupations, note in cases:
            with self.subTest(occupations=occupations):
                self.entry["occupations"] = occupations
                self.entry["records"][0]["note"] = note
                self.save()
                records = module.reviewed_records(self.root)
                people = module.catalogue._build_people(records, {}, [], {}, {"profiles": {}})
                person = module.decorate_person(people[0], self.entry)
                dossiers, resolver = module.build_machine_models([person])
                dossier = dossiers[self.slug]
                self.assertEqual(dossier["identity"]["occupations"], occupations)
                person = next(row for row in resolver if row["id"] == self.slug)
                self.assertEqual(person["occupations"], occupations)
                compact = module.compact_resolver_row(person)
                self.assertEqual(compact.get("occupations", []), occupations)

    def test_creation_keeps_parents_but_not_existing_profile_amendment_badges(self):
        self.entry["relationship_changes"] = [{"action": "add", "relationship": "father",
                                                "relative_id": "Glasgow-428", "status": "proved", "confidence_percent": 95},
                                               {"action": "add", "relationship": "mother",
                                                "relative_id": "Example-3", "status": "strongly_supported"}]
        self.save()
        module.apply_creations(self.root)
        dossier = self.read(f"people/{self.slug}.json")
        row = self.read("data/catalogue-search-index.json")[0]
        changes = dossier["wikitree_update"]["relationship_changes"]
        self.assertEqual(changes[0]["relative_id"], "Glasgow-428")
        self.assertEqual(changes[0]["relationship"], "father")
        self.assertEqual(changes[0]["confidence_band"], "confident")
        self.assertEqual(changes[0]["probability"]["minimum"], .9)
        self.assertEqual(changes[0]["confidence_percent"], 95)
        self.assertEqual(changes[1]["relationship"], "mother")
        self.assertIsNone(changes[1]["probability"]["value"])
        self.assertEqual(row["wikitree_update_relationship_changes"], [])
        self.assertTrue(row["needs_wikitree_update"])
        source_queue = json.loads((self.root / module.MANIFEST).read_text())
        self.assertEqual(source_queue["new_people"][0]["relationship_changes"], self.entry["relationship_changes"])


if __name__ == "__main__":
    unittest.main()
