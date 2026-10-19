"""The modern map must expose safe CSV leads without changing their precision."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from tools.public_privacy import PublicPrivacy
from tools.sync_onetree_map_assets import sync, merge_points


class ModernMapSyncTests(unittest.TestCase):
    def test_coincident_points_keep_all_records_and_original_precision_labels(self):
        public = ['one', 'public-1', 1700, False]
        other = ['two', 'public-2', 1710, False]
        merged = merge_points([
            {'lat': 55, 'lon': -3, 'country': 'scotland', 'precision': 'Recorded locality', 'items': [public]},
            {'lat': 55, 'lon': -3, 'country': 'scotland', 'precision': 'Kin-inferred locality', 'items': [other]},
        ])
        self.assertEqual(1, len(merged))
        self.assertEqual([public, other], merged[0]['items'])
        self.assertEqual(['Recorded locality', 'Kin-inferred locality'], merged[0]['source_precisions'])
        self.assertEqual(merged, merge_points(merged))

    def fixture(self, web):
        payloads = {
            'data/catalogue-search-index.json': [
                {'id': 'public-1', 'name': 'Historical Example', 'profile_ids': ['Public-1']},
                {'id': 'private-1', 'name': 'Withheld Example', 'profile_ids': ['Private-1']},
            ],
            'assets/research/record-index.json': [
                {'id': 'reviewed', 'p': 'reviewed-1', 'status': 'Documented', 'review': 'Retain verbatim'},
                {'id': 'private', 'p': 'private-1', 'status': 'Profile lead'},
            ],
            'assets/research/map-points.json': [
                {'lat': 50, 'lon': 1, 'country': 'scotland', 'precision': 'Reviewed locality',
                 'items': [['reviewed', 'reviewed-1', 1700, False], ['private', 'private-1', 1980, False]]},
            ],
            'assets/v3/map-country-associations.json': [],
            'assets/research/records/private.json': {'person': 'Withheld Example', 'catalogue_id': 'private-1'},
        }
        for relative, value in payloads.items():
            path = web / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        (web / 'people').mkdir()
        for slug in ('public-1', 'private-1'):
            (web / f'people/{slug}.html').write_text('Dossier')
        fields = ['profile_id', 'person', 'family_group', 'year', 'filter_year', 'region',
                  'record_location', 'record_precision', 'location_basis', 'location_id',
                  'association', 'evidence', 'note', 'latitude', 'longitude']
        row = dict(zip(fields, ['Public-1', 'Historical Example', 'Scotland One-Tree profile leads',
                               'b. 1700', '1700', 'Scotland', 'Supplied parish',
                               'Kin-inferred relationship locality', 'Inferred from child; not a recorded residence',
                               'supplied-place', 'Profile-stated birthplace: Supplied parish',
                               'One-Tree profile lead', 'Not an independent source', '55.12345', '-3.98765']))
        path = web / 'map/data/records.csv'
        path.parent.mkdir(parents=True)
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerow(row)
            writer.writerow(dict(row, profile_id='Private-1'))
        profiles = {'Public-1': {'BirthDate': '1700-01-01'}, 'Private-1': {'BirthDateDecade': '1980s'}}
        return profiles, payloads, row

    def test_adds_supplied_lead_and_detail_once_and_removes_private_refs(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            profiles, original, row = self.fixture(web)
            policy = PublicPrivacy(profiles)
            result = sync(web, profiles=profiles, policy=policy)
            self.assertEqual(1, result['added_profile_leads'])
            self.assertEqual(1, result['removed_private_records'])
            compact = json.loads((web / 'assets/research/record-index.json').read_text())
            self.assertEqual(original['assets/research/record-index.json'][0], compact[0])
            lead = next(r for r in compact if r['p'] == 'public-1')
            detail = json.loads((web / f'assets/research/records/{lead["id"]}.json').read_text())
            self.assertEqual(row['record_precision'], detail['record_precision'])
            self.assertEqual('unresolved', detail['supporting_source_status'])
            self.assertEqual('profile-export', detail['source_type'])
            points = json.loads((web / 'assets/research/map-points.json').read_text())
            self.assertEqual([["reviewed", "reviewed-1", 1700, False]], points[0]['items'])
            self.assertEqual((55.12345, -3.98765, row['record_precision']),
                             (points[1]['lat'], points[1]['lon'], points[1]['precision']))
            self.assertFalse((web / 'assets/research/records/private.json').exists())
            before = {str(p): p.read_bytes() for p in web.rglob('*') if p.is_file()}
            self.assertEqual(0, sync(web, profiles=profiles, policy=policy)['files'])
            self.assertEqual(before, {str(p): p.read_bytes() for p in web.rglob('*') if p.is_file()})

    def test_unpublished_profile_is_withheld(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            profiles, _, _ = self.fixture(web)
            (web / 'people/public-1.html').unlink()
            self.assertEqual(0, sync(web, profiles=profiles, policy=PublicPrivacy(profiles))['added_profile_leads'])

    def test_privacy_then_sync_retains_safe_tuples_and_deletes_private_details(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            profiles, _, _ = self.fixture(web)
            policy = PublicPrivacy(profiles)
            for path in web.rglob('*.json'):
                path.write_text(json.dumps(policy.project(json.loads(path.read_text()))))
            sync(web, profiles=profiles, policy=policy)
            point = json.loads((web / 'assets/research/map-points.json').read_text())[0]
            self.assertEqual([['reviewed', 'reviewed-1', 1700, False]], point['items'])
            self.assertFalse((web / 'assets/research/records/private.json').exists())
            self.assertEqual(0, sync(web, profiles=profiles, policy=policy)['files'])

    def test_detail_identity_with_custom_slug_removes_its_compact_row(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            profiles, _, _ = self.fixture(web)
            path = web / 'assets/research/record-index.json'
            compact = json.loads(path.read_text())
            compact[1]['p'] = 'private-draft'
            path.write_text(json.dumps(compact))
            (web / 'assets/research/records/private.json').write_text(json.dumps({
                'record_id': 'private', 'catalogue_id': 'private-draft', 'profile_ids': ['Private-1'],
                'person': 'Withheld Example'}))
            policy = PublicPrivacy(profiles)
            for path in web.rglob('*.json'):
                path.write_text(json.dumps(policy.project(json.loads(path.read_text()))))
            sync(web, profiles=profiles, policy=policy)
            self.assertNotIn('private', {r['id'] for r in json.loads((web / 'assets/research/record-index.json').read_text())})

    def test_canonical_nested_record_owner_recovers_safe_masked_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            profiles, _, _ = self.fixture(web)
            marker = 'Private family details withheld.'
            record = {'record_id': 'reviewed', 'catalogue_id': marker, 'person': 'Historical Example'}
            (web / 'data/records-index.json').write_text(json.dumps([record]))
            (web / 'data/people.json').write_text(json.dumps({'people': [{
                'catalogue_id': 'public-1', 'name': 'Historical Example', 'profile_ids': ['Public-1'],
                'records': [{'record_id': 'reviewed', 'note': 'Preserve the source record'}]}]}))
            path = web / 'assets/research/record-index.json'
            compact = json.loads(path.read_text()); compact[0]['p'] = marker
            path.write_text(json.dumps(compact))
            sync(web, profiles=profiles, policy=PublicPrivacy(profiles))
            self.assertEqual('public-1', json.loads(path.read_text())[0]['p'])
            self.assertEqual('Retain verbatim', json.loads(path.read_text())[0]['review'])
            self.assertEqual('public-1', json.loads((web / 'data/records-index.json').read_text())[0]['catalogue_id'])
            self.assertEqual('Preserve the source record',
                             json.loads((web / 'assets/research/records/reviewed.json').read_text())['note'])
            self.assertEqual(0, sync(web, profiles=profiles, policy=PublicPrivacy(profiles))['files'])

    def test_missing_coordinates_and_non_geographic_points_stay_unmapped(self):
        for field, value in [('latitude', ''), ('record_precision', 'Non-geographic holding point')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                web = Path(directory)
                profiles, _, _ = self.fixture(web)
                path = web / 'map/data/records.csv'
                with path.open(newline='') as handle:
                    reader = csv.DictReader(handle)
                    fields, rows = reader.fieldnames, list(reader)
                rows[0][field] = value
                with path.open('w', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader(); writer.writerows(rows)
                self.assertEqual(0, sync(web, profiles=profiles, policy=PublicPrivacy(profiles))['added_profile_leads'])
