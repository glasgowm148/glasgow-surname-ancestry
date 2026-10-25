"""Checks on Glasgow's real migrated research database (private, local only).

These need the private database and inputs. Without them the tests are
*skipped with an explicit reason*, which is not evidence that the migration
passed; ``make check-workbench`` instead fails loudly when the inputs are
absent.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

try:
    from genealogy.store import Research, open_project
    from genealogy.store.project import StorageSettings, load_config
    DATABASE = ROOT / StorageSettings.from_config(load_config(ROOT)).database
except Exception as error:  # pragma: no cover - reported by skip below
    DATABASE, IMPORT_ERROR = None, error
else:
    IMPORT_ERROR = None

REASON = ("private research database not present: run tools/workbench_migrate.py on a checkout with the private "
          "inputs (this skip is NOT a passing migration check)")


@unittest.skipUnless(DATABASE is not None and DATABASE.is_file(), REASON)
class MigratedGlasgowDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = open_project(ROOT, readonly=True)
        cls.research = Research(cls.project.store)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.project.close()

    def test_regression_95_44(self) -> None:
        claim = self.research.find_external("glasgow-assertion", "C-coverage-20261022b-glascow-14-father")[0]
        history = [row["estimate_percent"] for row in self.research.assessment_history(claim)]
        self.assertEqual(history[-1], 95)
        self.assertIn(44, history[:-1])
        for wikitree, role in (("Glascow-14", "father"), ("Glasgow-357", "child")):
            person = self.research.find_external("wikitree", wikitree)[0]
            view = next(v for v in self.research.relationship_views(person) if v["claim_id"] == claim)
            self.assertEqual((view["role"], view["assessment"]["estimate_percent"]), (role, 95))

    def test_both_directions_of_every_claim_share_one_current_estimate(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        import workbench_legacy_views
        rows = workbench_legacy_views.Views(self.project.store).estimates()
        pairs: dict[tuple, set] = {}
        for row in rows:
            key = (row.get("assertion_id"), frozenset((row["subject_id"], row["relative_id"])),
                   "sibling" if row["relationship"] == "sibling" else "parent-line")
            pairs.setdefault(key, set()).add(row["percent"])
        conflicting = {key: values for key, values in pairs.items() if len(values) > 1}
        # The one remaining case files two propositions (brothers, and a father role) under one id.
        self.assertLessEqual(len(conflicting), 1, conflicting)

    def test_unresolved_identity_and_record_defined_people_survive(self) -> None:
        store = self.project.store
        self.assertGreater(store.one("SELECT count(*) n FROM mention")["n"], 0)
        self.assertGreater(store.one("SELECT count(*) n FROM claim WHERE kind='identity'")["n"], 0)
        self.assertGreater(store.one("SELECT count(*) n FROM person WHERE record_defined=1")["n"], 0)

    def test_exact_file_approvals_are_hash_scoped(self) -> None:
        rows = self.project.store.all("SELECT * FROM approval WHERE kind='exact_file'")
        self.assertTrue(rows)
        self.assertTrue(all(row["sha256"] and len(row["sha256"]) == 64 for row in rows))

    def test_reconciliation_report_accounts_for_every_disagreement(self) -> None:
        report = json.loads((ROOT / "data/private/workbench/migration-report.json").read_text())
        resolutions = [row["resolution"] for row in report["reconciliation"]]
        self.assertFalse([r for r in resolutions if r.startswith("unexplained")])
        self.assertEqual(report["conflicts"], [])


if __name__ == "__main__":
    unittest.main()
