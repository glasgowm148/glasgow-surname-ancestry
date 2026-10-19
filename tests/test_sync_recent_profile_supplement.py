import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.public_privacy import PublicPrivacy
from tools.sync_recent_profile_supplement import SOURCE, public_supplement, publish_source


class RecentProfileSupplementTests(unittest.TestCase):
    def test_publication_preserves_safe_events_and_filters_both_sides_of_merges(self):
        event = {'latitude': 55.1, 'longitude': -6.2, 'record_precision': 'Parish centroid'}
        safe = {'supplement_id': 'safe', 'profile_id': 'Example-1', 'events': [event]}
        merged = {'supplement_id': 'merged', 'profile_id': 'Example-3', 'events': [event]}
        source = {'profiles': [safe, merged,
                               {'supplement_id': 'private', 'profile_id': 'Example-2'},
                               {'supplement_id': 'private-merge', 'profile_id': 'Example-4'}],
                  'already_mapped_profile_ids': ['Example-1', 'Example-2', 'Example-3', 'Example-4']}
        original = copy.deepcopy(source)
        policy = PublicPrivacy({'Example-2': {'IsLiving': True}})
        redirects = {'Example-3': 'Example-1', 'Example-4': 'Example-2'}
        expected = {'profiles': [safe, {**merged, 'profile_id': 'Example-1'}],
                    'already_mapped_profile_ids': ['Example-1', 'Example-1']}
        projected = public_supplement(source, policy, redirects)
        self.assertEqual(expected, projected)
        self.assertEqual(original, source)
        self.assertEqual(projected, public_supplement(projected, policy, redirects))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            maintained, published = path / 'source.json', path / 'public.json'
            maintained.write_text(json.dumps(source))
            self.assertEqual(expected, publish_source(maintained, published, policy=policy, redirects=redirects))
            first = published.read_bytes()
            publish_source(maintained, published, policy=policy, redirects=redirects)
            self.assertEqual(first, published.read_bytes())
            self.assertEqual(original, json.loads(maintained.read_text()))

    def test_maintained_cohort_retains_the_original_historical_manifest(self):
        source = json.loads(SOURCE.read_text())
        self.assertEqual(23, len(source['profiles']))
        self.assertEqual(23, len({row['supplement_id'] for row in source['profiles']}))
        self.assertTrue(all(int(row['birth_date'][:4]) < 1900 and row['events']
                            for row in source['profiles']))


if __name__ == '__main__':
    unittest.main()
