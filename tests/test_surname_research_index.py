import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from surname_research_index import rebuild_surname_indexes


class SurnameIndexTests(unittest.TestCase):
    def test_builds_contextual_profile_and_early_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "TableData"
            sheet.append(
                [
                    "WT ID",
                    "First",
                    "LNAB",
                    "Current",
                    "Birth Date",
                    "Birth Place",
                    "Death Date",
                    "Death Place",
                    "Modified",
                ]
            )
            sheet.append(
                [
                    "Glasgow-2",
                    "William",
                    "Glasgow",
                    "Glasgow",
                    "1550-00-00",
                    "Glasgow, Lanarkshire, Scotland",
                    None,
                    None,
                    None,
                ]
            )
            sheet.append(
                [
                    "Glasgow-1",
                    "John",
                    "Glasgow",
                    "Glasgow",
                    "1590-00-00",
                    "Ayrshire, Scotland",
                    None,
                    None,
                    None,
                ]
            )
            sheet.append(
                [
                    "Glasgow-3",
                    "James",
                    "Glasgow",
                    "Glasgow",
                    "1750-00-00",
                    "County Antrim, Ireland",
                    None,
                    None,
                    None,
                ]
            )
            sheet.append(
                [
                    "Glasgow-4",
                    "Robert",
                    "Glasgow",
                    "Glasgow",
                    "1790-00-00",
                    None,
                    None,
                    "County Tyrone, Ireland",
                    None,
                ]
            )
            sheet.append(
                [
                    "Glasgow-5",
                    "Andrew",
                    "Glasgow",
                    "Glasgow",
                    "1750-00-00",
                    "Scotland",
                    None,
                    "County Antrim, Ireland",
                    None,
                ]
            )
            workbook.save(workspace / "glasgow-one-tree.xlsx")

            case_dir = workspace / "research" / "Glasgow-1"
            case_dir.mkdir(parents=True)
            (case_dir / "evidence_index.json").write_text(
                json.dumps(
                    {
                        "profiles": {
                            "Glasgow-1": {
                                "display_name": "John Glasgow",
                                "birth_date": "1590-00-00",
                                "birth_location": "Ayrshire, Scotland",
                                "relations": {"parents": ["Glasgow-2"]},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "surname-research" / "clusters").mkdir(parents=True)
            (workspace / "surname-research" / "pre-1700").mkdir(parents=True)
            index_dir = workspace / "surname-research" / "indexes"
            index_dir.mkdir(parents=True)
            (index_dir / "father-assessments.json").write_text(
                json.dumps(
                    {
                        "assessments": {
                            "Glasgow-1": {
                                "father_id": "Glasgow-2",
                                "status": "confirmed",
                                "basis": "Original baptism names and identifies him.",
                                "evidence": [],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            rebuild_surname_indexes(workspace)

            researched = (
                workspace / "surname-research" / "indexes" / "researched-profiles.md"
            ).read_text(encoding="utf-8")
            early = (
                workspace / "surname-research" / "indexes" / "early-profiles.md"
            ).read_text(encoding="utf-8")
            early_irish = (
                workspace
                / "surname-research"
                / "indexes"
                / "early-irish-profiles.md"
            ).read_text(encoding="utf-8")

        link = (
            "[John Glasgow (Glasgow-1), born 1590, Ayrshire, Scotland]"
            "(https://www.wikitree.com/wiki/Glasgow-1)"
        )
        self.assertIn(link, researched)
        self.assertIn(
            "[John Glasgow (1590)](https://www.wikitree.com/wiki/Glasgow-1)",
            early,
        )
        self.assertIn("**Total indexed: 2 profiles", early)
        self.assertIn("16th century (1500-1599): highest priority (2)", early)
        self.assertIn(
            "| Location | Profiles | Share | Confirmed | Plausible | Uncertain | Contradicted / unsupported | Not assessed |",
            early,
        )
        self.assertIn(
            "| Scotland: Ayrshire | 1 | 50.0% | 1 | 0 | 0 | 0 | 0 |",
            early,
        )
        self.assertIn(
            "| **Total** | **2** | **100.0%** | **1** | **0** | **0** | **0** | **1** |",
            early,
        )
        self.assertIn("### Scotland: Ayrshire (1)", early)
        self.assertIn("| Person | Father / assessment | Assessment basis | Findings |", early)
        self.assertNotIn("| Person | Death |", early)
        self.assertIn("**Confirmed by record**", early)
        self.assertIn("Original baptism names and identifies him.", early)
        self.assertIn("**Total indexed: 2 profiles.**", early_irish)
        self.assertIn("## 18th century (1700-1799) (2)", early_irish)
        self.assertIn("| Ireland: County Antrim | 1 | 50.0%", early_irish)
        self.assertIn("| Ireland: County Tyrone | 1 | 50.0%", early_irish)
        self.assertNotIn("Andrew Glasgow", early_irish)

    def test_irish_cohort_audit_reclassifies_and_excludes_snapshot_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "TableData"
            sheet.append(
                [
                    "WT ID",
                    "First",
                    "LNAB",
                    "Current",
                    "Birth Date",
                    "Birth Place",
                    "Death Date",
                    "Death Place",
                ]
            )
            sheet.append(
                [
                    "Glasgow-1",
                    "James",
                    "Glasgow",
                    "Glasgow",
                    "1650-00-00",
                    None,
                    "1728-00-00",
                    "County Donegal, Ireland",
                ]
            )
            sheet.append(
                [
                    "Glasgow-2",
                    "Janet",
                    "Glasgow",
                    "Woodside",
                    "1678-00-00",
                    "Ireland",
                    None,
                    None,
                ]
            )
            workbook.save(workspace / "glasgow-one-tree.xlsx")
            (workspace / "research").mkdir()
            (workspace / "surname-research" / "clusters").mkdir(parents=True)
            (workspace / "surname-research" / "pre-1700").mkdir(parents=True)
            index_dir = workspace / "surname-research" / "indexes"
            index_dir.mkdir(parents=True)
            (index_dir / "irish-cohort-audit.json").write_text(
                json.dumps(
                    {
                        "assessments": {
                            "Glasgow-1": {
                                "action": "reclassify",
                                "working_birth_date": "1728",
                                "working_band": "18th century (1700-1799)",
                                "basis": "The record is an account dated 1728.",
                            },
                            "Glasgow-2": {
                                "action": "exclude",
                                "basis": "No Irish event is documented.",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            rebuild_surname_indexes(workspace)
            early_irish = (index_dir / "early-irish-profiles.md").read_text(
                encoding="utf-8"
            )

        self.assertIn(
            "**Snapshot candidates: 2 profiles. Evidence-audited working cohort: 1.**",
            early_irish,
        )
        self.assertIn("## 18th century (1700-1799) (1)", early_irish)
        self.assertNotIn("## 17th century (1600-1699)", early_irish)
        self.assertIn("Exclude pending Irish evidence", early_irish)


if __name__ == "__main__":
    unittest.main()
