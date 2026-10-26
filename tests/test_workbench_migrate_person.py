import unittest
from unittest.mock import Mock

from tools.workbench_migrate import Migration


class PersonStore:
    def __init__(self):
        self.people = {"per-native": {"id": "per-native"}}

    def get(self, table, key):
        return self.people.get(key) if table == "person" else None


class MigrationPersonTests(unittest.TestCase):
    def migration(self, *, wikitree=None, local=None):
        migration = Migration.__new__(Migration)
        migration._people = {}
        migration.store = PersonStore()
        migration.research = Mock()
        migration.research.find_external.side_effect = lambda system, value: (
            ["per-wt"] if system == "wikitree" and value == "Glasgow-589" else
            ["per-native"] if system == "glasgow-local" and value == "glasgow-local-john" else [])
        return migration

    def test_canonical_local_alias_reuses_record_defined_person(self):
        migration = self.migration()
        tx = Mock()
        person = migration.person(tx, "glasgow-local-john", name="John Cameron Glasgow")
        self.assertEqual("per-native", person)
        migration.research.create_person.assert_not_called()
        migration.research.map_external.assert_not_called()

    def test_wikitree_alias_still_has_priority(self):
        migration = self.migration()
        tx = Mock()
        person = migration.person(tx, "Glasgow-589", name="Moses Glasgow")
        self.assertEqual("per-wt", person)
        migration.research.find_external.assert_any_call("wikitree", "Glasgow-589")

    def test_unknown_local_id_uses_stable_native_person(self):
        migration = self.migration()
        tx = Mock()
        person = migration.person(tx, "glasgow-local-new", name="New record person")
        self.assertTrue(person.startswith("per-"))
        migration.research.create_person.assert_called_once()
        migration.research.map_external.assert_called_once()


if __name__ == "__main__":
    unittest.main()
