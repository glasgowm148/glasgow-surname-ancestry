"""Physical research-folder moves retain real SQLite asset-version history."""
import tempfile
import unittest
from pathlib import Path

from genealogy.store import open_project
from genealogy.store.assets import register_asset, verify_assets
from tools.workbench_asset_paths import relocate_research_assets
from tools.workbench_ledger import ledger


class AssetPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'genealogy.toml').write_text(
            '[project]\nname="Move fixture"\n[storage]\ndatabase="private/db.sqlite"\n'
            '[storage.asset_roots]\nrepository="."\n')
        self.old = self.root / 'research/subject-fixture/plan.json'
        self.new = self.root / 'research/record-fixture/plan.json'
        self.old.parent.mkdir(parents=True)
        self.new.parent.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_relocation_and_later_edit_preserve_all_versions(self):
        with open_project(self.root, create=True) as project:
            self.old.write_text('first')
            with project.store.write(actor='test', tool='fixture') as tx:
                first = register_asset(project, tx, self.old, root='repository')
            self.old.write_text('second')
            with project.store.write(actor='test', tool='fixture') as tx:
                second = register_asset(project, tx, self.old, root='repository', supersedes_id=first['id'])
            self.old.rename(self.new)
            with project.store.write(actor='test', tool='move') as tx:
                result = relocate_research_assets(project, tx, 'research/subject-fixture', 'research/record-fixture')
            self.assertEqual(2, result['count'])
            for original in (first, second):
                current = project.store.get('asset', original['id'])
                self.assertEqual('research/record-fixture/plan.json', current['path'])
                self.assertEqual(original['sha256'], current['sha256'])
                self.assertEqual(original['supersedes_id'], current['supersedes_id'])
            self.new.write_text('third')
            with project.store.write(actor='test', tool='edit') as tx:
                register_asset(project, tx, self.new, root='repository', supersedes_id=second['id'])
            verified = verify_assets(project, orphans=False)
            self.assertEqual([], verified['missing'])
            self.assertEqual([], verified['changed'])
            self.assertEqual(2, len(verified['superseded']))
            item = {'path': 'research/subject-fixture/plan.json', 'sha256': first['sha256'],
                    'disposition': 'held', 'category': 'research', 'access': 'private', 'tracked': True}
            inventory = {'source_commit': 'fixture', 'files': [item], 'summarised': []}
            self.assertEqual([], ledger(project, inventory)['problems'])
            item['sha256'] = 'unregistered hash'
            self.assertTrue(ledger(project, inventory)['problems'])

    def test_missing_destination_and_collision_leave_metadata_unchanged(self):
        with open_project(self.root, create=True) as project:
            self.old.write_text('original')
            with project.store.write(actor='test', tool='fixture') as tx:
                original = register_asset(project, tx, self.old, root='repository')
            self.old.unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                with project.store.write(actor='test', tool='move') as tx:
                    relocate_research_assets(project, tx, 'research/subject-fixture', 'research/record-fixture')
            self.assertEqual(original, project.store.get('asset', original['id']))
            self.new.write_text('existing destination')
            with project.store.write(actor='test', tool='fixture') as tx:
                register_asset(project, tx, self.new, root='repository')
            with self.assertRaisesRegex(ValueError, 'already registered'):
                with project.store.write(actor='test', tool='move') as tx:
                    relocate_research_assets(project, tx, 'research/subject-fixture', 'research/record-fixture')
            self.assertEqual(original, project.store.get('asset', original['id']))

    def test_registered_derivative_stays_derivative_after_rebuild(self):
        with open_project(self.root, create=True) as project:
            output = self.root / 'www/assets/research/people/record-example.json'
            output.parent.mkdir(parents=True)
            output.write_text('{}')
            with project.store.write(actor='test', tool='fixture') as tx:
                register_asset(project, tx, output, root='repository', kind='derivative')
            item = {'path': output.relative_to(self.root).as_posix(), 'sha256': 'older output hash',
                    'disposition': 'derivative', 'category': 'reproducible derivatives',
                    'access': 'public', 'tracked': False}
            result = ledger(project, {'source_commit': 'fixture', 'files': [item], 'summarised': []})
            self.assertEqual([], result['problems'])
            self.assertEqual('replaced by a reproducible derivative', result['files'][0]['actual'])
            self.assertEqual([], verify_assets(project, orphans=False)['changed'])
            output.write_text('unrecorded bytes')
            self.assertTrue(verify_assets(project, orphans=False)['changed'])
