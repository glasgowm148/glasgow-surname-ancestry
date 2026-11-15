import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools import catalogue_gender as genders


class CatalogueGenderTests(unittest.TestCase):
    def test_reviewed_names_and_abbreviations(self):
        for name, expected in [('John', 'male'), ('Wm', 'male'), ('Mary Ann', 'female'), ('Issobell', 'female')]:
            self.assertEqual(genders.name_classification({'first_names': [name]}), expected)

    def test_initials_and_ambiguous_names_stay_unknown(self):
        for name in ['J', 'A', 'Ashley', 'Robin', 'Terry', 'Carol', 'Unknown']:
            self.assertIsNone(genders.name_classification({'first_names': [name]}))

    def test_projection_uses_workbench_and_preserves_known_values(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'data/private/workbench/glasgow.sqlite'
            path.parent.mkdir(parents=True)
            path.touch()
            people = [
                {'catalogue_id': 'john', 'gender': ''},
                {'catalogue_id': 'existing', 'gender': 'Female'},
                {'catalogue_id': 'unknown', 'gender': ''},
                {'catalogue_id': 'living', 'gender': '', 'likely_living': True},
            ]
            known = {name: {'sex': 'male'} for name in ['john', 'existing', 'living']}
            with patch.object(genders, 'workbench_people', return_value=known):
                changed = genders.project_genders(people, root)
            self.assertEqual(changed, {'john': 'Male'})
            self.assertEqual(people[1]['gender'], 'Female')
            self.assertEqual(people[2]['gender'], '')
            self.assertEqual(people[3]['gender'], '')
