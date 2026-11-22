"""Fictional review histories for the FamilySearch display-crosswalk guard."""
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import build_notables, catalogue_search_index, profile_tree_links
from tools import sync_familysearch_links as sync
from tools.sync_familysearch_links import load_matches, main, read_matches, validate_matches


class FamilySearchLinksTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "map.tsv"

    def write_rows(self, rows):
        with self.source.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["catalogue_id", "fs_id", "confidence", "name"])
            writer.writerows([*row, "Fictional Example"] for row in rows)

    def test_repeated_reviews_normalize_and_last_valid_row_wins(self):
        self.write_rows([
            (" Example-2 ", "test-002", " HIGH "),
            ("example-1", "TEST-001", "high"),
            ("example-2", "TEST-002", "medium"),
            ("example-1", "TEST-003", "medium"),
            ("example-1", "invalid", "high"),
            ("", "TEST-004", "high"),
        ])
        self.assertEqual(read_matches(self.source), {
            "example-1": {"id": "TEST-003", "confidence": "medium"},
            "example-2": {"id": "TEST-002", "confidence": "medium"},
        })
        self.assertEqual(list(read_matches(self.source)), ["example-1", "example-2"])

    def test_prior_collision_corrected_before_validation(self):
        self.write_rows([
            ("example-1", "TEST-001", "high"),
            ("example-2", "TEST-001", "high"),
            ("example-2", "TEST-002", "medium"),
        ])
        self.assertEqual(len(read_matches(self.source)), 2)

    def test_tsv_helper_accepts_explicit_merges_but_rejects_cycles(self):
        self.write_rows([
            ("example-1", "TEST-001", "high"),
            ("example-2", "TEST-001", "medium"),
        ])
        self.assertEqual(len(read_matches(self.source, {"example-2": "example-1"})), 2)
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            read_matches(self.source, {"example-2": "example-1", "example-1": "example-2"})

    def test_later_doubtful_review_withdraws_prior_collision(self):
        for confidence in ("low", "rejected", ""):
            with self.subTest(confidence=confidence):
                self.write_rows([
                    ("example-1", "TEST-001", "high"),
                    ("example-2", "TEST-001", "medium"),
                    ("example-2", "TEST-001", confidence),
                ])
                self.assertEqual(read_matches(self.source), {
                    "example-1": {"id": "TEST-001", "confidence": "high"},
                })

    def test_conflicts_are_deterministic_and_names_do_not_reconcile_ids(self):
        rows = [
            ("example-4", "TEST-002", "high"),
            ("example-2", "test-001", "medium"),
            ("example-3", "TEST-002", "medium"),
            ("example-1", "TEST-001", "high"),
        ]
        expected = (
            "FamilySearch PID assigned to distinct unresolved catalogue people: "
            "TEST-001: example-1, example-2; TEST-002: example-3, example-4"
        )
        for order in (rows, list(reversed(rows))):
            self.write_rows(order)
            with self.assertRaises(ValueError) as caught:
                read_matches(self.source)
            self.assertEqual(str(caught.exception), expected)

    def test_conflict_preserves_target_and_creates_no_output_directories(self):
        self.write_rows([
            ("example-1", "TEST-001", "high"),
            ("example-2", "TEST-001", "high"),
        ])
        existing = self.root / "existing.json"
        original = b'{"previous": "display crosswalk"}\n'
        existing.write_bytes(original)
        absent = self.root / "not-created" / "nested" / "links.json"
        for target in (existing, absent):
            with self.subTest(target=target), contextlib.redirect_stderr(io.StringIO()) as errors:
                with self.assertRaises(SystemExit) as caught:
                    main(["--source", str(self.source), "--target", str(target)])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn("TEST-001: example-1, example-2", errors.getvalue())
                self.assertEqual(existing.read_bytes(), original)
                self.assertFalse(absent.parent.parent.exists())

    def test_valid_sync_keeps_consumer_schema_and_is_idempotent(self):
        self.write_rows([("example-1", "TEST-001", "high")])
        target = self.root / "output" / "links.json"
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["--source", str(self.source), "--target", str(target)]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"people": 1})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {
            "source": "fs-parity/map.tsv",
            "people": {"example-1": {"id": "TEST-001", "confidence": "high"}},
        })
        timestamp = target.stat().st_mtime_ns
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--source", str(self.source), "--target", str(target)]), 0)
        self.assertEqual(target.stat().st_mtime_ns, timestamp)


class ExistingCrosswalkTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "data/familysearch/person-links.json"
        self.path.parent.mkdir(parents=True)
        self.conflict = {
            "example-1": {"id": "TEST-001", "confidence": "high"},
            " Example-2 ": {"id": "test-001", "confidence": "medium"},
        }

    def write_map(self, people):
        self.path.write_text(json.dumps({"people": people}), encoding="utf-8")

    def test_missing_file_means_no_links_without_creating_it(self):
        self.assertEqual(load_matches(self.path), {})
        self.assertEqual(profile_tree_links.familysearch_links(self.path), {})
        self.assertFalse(self.path.exists())

    def test_missing_snapshot_notices_new_file_and_nested_copies_are_isolated(self):
        missing = load_matches(self.path)
        self.write_map(self.conflict)
        with self.assertRaisesRegex(ValueError, "distinct unresolved"):
            sync.validated_snapshot(missing)
        self.write_map({"example-1": {
            "id": "TEST-001", "confidence": "high", "metadata": {"notes": ["fictional"]}
        }})
        matches = load_matches(self.path)
        matches["example-1"]["metadata"]["notes"].append("changed")
        self.assertEqual(matches["example-1"]["metadata"]["notes"], ["fictional"])
        self.assertEqual(json.loads(json.dumps(list(matches.values())))[0]["id"], "TEST-001")

    def test_valid_map_normalizes_and_preserves_metadata_without_mutation(self):
        people = {" Example-1 ": {"id": "test-001", "confidence": " HIGH ", "note": "fictional"}}
        self.write_map(people)
        self.assertEqual(load_matches(self.path), {
            "example-1": {"id": "TEST-001", "confidence": "high", "note": "fictional"},
        })
        self.assertEqual(people[" Example-1 "]["id"], "test-001")

    def test_existing_json_conflict_and_changed_file_are_rejected(self):
        self.write_map({"example-1": self.conflict["example-1"]})
        self.assertEqual(len(profile_tree_links.familysearch_links(self.path)), 1)
        self.write_map(self.conflict)
        for reader in (load_matches, profile_tree_links.familysearch_links):
            with self.subTest(reader=reader.__name__), self.assertRaisesRegex(
                ValueError, "TEST-001: example-1, example-2"
            ):
                reader(self.path)

    def test_malformed_crosswalks_are_not_silently_empty(self):
        invalid = [
            "{", "[]", "{}", '{"people": null}', '{"people": []}',
            '{"people": {"": {"id": "TEST-001", "confidence": "high"}}}',
            '{"people": {"example-1": null}}',
            '{"people": {"example-1": {"id": 1, "confidence": "high"}}}',
            '{"people": {"example-1": {"id": "bad", "confidence": "high"}}}',
            '{"people": {"example-1": {"id": "TEST-001"}}}',
            '{"people": {"example-1": {"id": "TEST-001", "confidence": "low"}}}',
            '{"people": {"example-1": {}, "example-1": {}}}',
            '{"people": {}, "people": {}}',
        ]
        for text in invalid:
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_matches(self.path)
        with self.assertRaisesRegex(ValueError, "Duplicate normalized"):
            validate_matches({
                "example-1": {"id": "TEST-001", "confidence": "high"},
                " Example-1 ": {"id": "TEST-002", "confidence": "high"},
            })

    def test_all_consumers_reject_bad_json_before_output(self):
        # Each reader uses only this fictional crosswalk; unrelated inputs are
        # deliberately absent, demonstrating validation precedes their use too.
        web = self.root / "site"
        people_dir = web / "people"
        people_dir.mkdir(parents=True)
        page = people_dir / "example-1.html"
        original = '<div class="dossier-actions">Fictional existing page</div>'
        page.write_text(original, encoding="utf-8")
        # Preserve already-published output, not just the input crosswalk.
        data_dir = web / "data"
        data_dir.mkdir()
        index = data_dir / "catalogue-search-fast.json"
        index.write_text("fictional previous index", encoding="utf-8")
        for value in (self.conflict, [], {"example-1": {"id": "bad"}}):
            self.write_map(value)
            crosswalk = self.path.read_bytes()
            with self.subTest(value=value):
                with patch.object(profile_tree_links, "FS_LINKS", self.path):
                    with self.assertRaises(ValueError):
                        profile_tree_links.apply(web)
                with patch.object(catalogue_search_index, "ROOT", self.root), patch.object(
                    catalogue_search_index.subprocess, "run"
                ) as prepare:
                    with self.assertRaises(ValueError):
                        catalogue_search_index.build(web)
                    prepare.assert_not_called()
                with patch.object(build_notables, "FS_LINKS", self.path), patch.object(
                    build_notables, "load"
                ) as unrelated_load:
                    with self.assertRaises(ValueError):
                        build_notables.render()
                    unrelated_load.assert_not_called()
                self.assertEqual(page.read_text(encoding="utf-8"), original)
                self.assertEqual(set(web.iterdir()), {people_dir, data_dir})
                self.assertEqual(list(people_dir.iterdir()), [page])
                self.assertEqual(list(data_dir.iterdir()), [index])
                self.assertEqual(index.read_text(encoding="utf-8"), "fictional previous index")
                self.assertEqual(self.path.read_bytes(), crosswalk)

    def test_consumers_reject_conflicts_before_creating_output_roots(self):
        self.write_map(self.conflict)
        absent = self.root / "absent-site"
        with patch.object(profile_tree_links, "FS_LINKS", self.path):
            with self.assertRaises(ValueError):
                profile_tree_links.apply(absent)
        with patch.object(catalogue_search_index, "ROOT", self.root):
            with self.assertRaises(ValueError):
                catalogue_search_index.build(absent)
        with patch.object(build_notables, "FS_LINKS", self.path), patch.object(build_notables, "WEB", absent):
            with self.assertRaises(ValueError):
                build_notables.render()
        self.assertFalse(absent.exists())

    def test_profile_valid_and_missing_json_keep_rendering_behavior(self):
        web = self.root / "site"
        (web / "people").mkdir(parents=True)
        page = web / "people/example-1.html"
        page.write_text(
            '<html><head></head><body data-g-person=\'{"id":"Example-1","tree":false}\'>'
            '<div class="dossier-actions">Fictional actions</div></body></html>', encoding="utf-8"
        )
        self.write_map({"example-1": {"id": "TEST-001", "confidence": "medium"}})
        with patch.object(profile_tree_links, "FS_LINKS", self.path):
            self.assertEqual(profile_tree_links.apply(web), {"pages": 1, "changed": 1})
            self.assertIn("/details/TEST-001", page.read_text(encoding="utf-8"))
            self.assertEqual(profile_tree_links.apply(web), {"pages": 1, "changed": 0})
            self.path.unlink()
            self.assertEqual(profile_tree_links.apply(web), {"pages": 1, "changed": 1})
            self.assertNotIn("data-fs-link", page.read_text(encoding="utf-8"))

    def test_profile_explicit_in_memory_matches_cannot_bypass_guard(self):
        with self.assertRaisesRegex(ValueError, "distinct unresolved"):
            profile_tree_links.add_familysearch_link("<div class=actions></div>", {}, self.conflict)

    def test_notables_missing_file_keeps_empty_links_behavior(self):
        with patch.object(build_notables, "FS_LINKS", self.path), patch.object(
            build_notables, "load", side_effect=lambda path, default: default
        ), patch.object(build_notables, "notables_lines", return_value=["* [[Example-1|Fictional Example]]"]), patch.object(
            build_notables, "CATALOGUE_NOTABLES", {}
        ), patch.object(build_notables, "WEB", self.root / "site"):
            rows = build_notables.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fs"], "")
        self.assertFalse(self.path.exists())

    def test_explicit_canonical_aliases_allow_only_resolved_shared_identity(self):
        self.write_map(self.conflict)
        aliases = {"Example-2": "example-middle", "example-middle": "EXAMPLE-1"}
        self.assertEqual(len(validate_matches(self.conflict, aliases)), 2)
        self.assertEqual(len(load_matches(self.path, aliases)), 2)
        # A canonical target need not itself have an FS link.
        self.assertEqual(len(validate_matches(self.conflict, {
            "example-1": "example-survivor", "example-2": "example-survivor"
        })), 2)
        with self.assertRaisesRegex(ValueError, "distinct unresolved"):
            validate_matches(self.conflict, {"example-2": "some-other-person"})
        for aliases in ({"a": "b", "b": "a"}, {"a": "a"}, {"a": ""}, {"a": None}):
            with self.subTest(aliases=aliases), self.assertRaises(ValueError):
                load_matches(self.path, aliases)

    def configure_mock_workbench(self):
        (self.root / "genealogy.toml").write_text(
            '[project]\nid = "fictional"\n[storage]\ndatabase = "mock.sqlite"\n', encoding="utf-8"
        )
        database = self.root / "mock.sqlite"
        # Not a database: all workbench access is mocked and checked read-only.
        database.write_text("mock database stamp", encoding="utf-8")
        return database

    def test_project_context_uses_only_readonly_authoritative_merges(self):
        self.configure_mock_workbench()
        self.write_map(self.conflict)
        with patch("genealogy.store.open_project") as opened, patch(
            "tools.workbench_legacy_views.Views"
        ) as views:
            views.return_value._merged_public = {"example-2": "example-1", "example-1": "Example-1"}
            matches = load_matches(self.path)
            self.assertEqual(len(matches), 2)
            opened.assert_called_once_with(self.root, readonly=True)
            views.assert_called_once_with(opened.return_value.__enter__.return_value.store)
            html = profile_tree_links.add_familysearch_link(
                '<div class="dossier-actions"></div>', {"id": "Example-2"}, matches
            )
            self.assertIn("/details/TEST-001", html)
            # Lookups are isolated JSON-compatible copies, never cache mutations.
            matches["example-2"]["id"] = "TEST-999"
            self.assertEqual(matches["example-2"]["id"], "TEST-001")
            json.dumps(list(matches.values()))
            with self.assertRaises(TypeError):
                matches["example-3"] = {"id": "TEST-001", "confidence": "high"}
            with self.assertRaises(TypeError):
                matches._data = {}

    def test_snapshot_cache_reuses_parse_but_not_changed_file_or_db(self):
        database = self.configure_mock_workbench()
        self.write_map(self.conflict)
        with patch("genealogy.store.open_project"), patch("tools.workbench_legacy_views.Views") as views, patch.object(
            sync.json, "loads", wraps=json.loads
        ) as parse:
            views.return_value._merged_public = {"example-2": "example-1"}
            first = load_matches(self.path)
            self.assertIs(load_matches(self.path), first)
            parse.assert_called_once()
            self.assertEqual(views.call_count, 1)
            # Replacing the JSON invalidates the snapshot, even if content is valid.
            self.write_map({"example-1": {"id": "TEST-002", "confidence": "high"}})
            self.assertEqual(load_matches(self.path)["example-1"]["id"], "TEST-002")
            self.write_map(self.conflict)
            self.assertEqual(len(load_matches(self.path)), 2)
            # Revoking a merge must not be masked by a cached JSON snapshot.
            views.return_value._merged_public = {}
            database.write_text("changed mock stamp", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "distinct unresolved"):
                load_matches(self.path)
            with self.assertRaisesRegex(ValueError, "distinct unresolved"):
                sync.validated_snapshot(first)

    def test_wal_and_config_changes_invalidate_authority_snapshot(self):
        self.configure_mock_workbench()
        self.write_map(self.conflict)
        with patch("genealogy.store.open_project"), patch("tools.workbench_legacy_views.Views") as views:
            views.return_value._merged_public = {"example-2": "example-1"}
            load_matches(self.path)
            views.return_value._merged_public = {}
            (self.root / "mock.sqlite-wal").write_text("fictional WAL stamp", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "distinct unresolved"):
                load_matches(self.path)
            views.return_value._merged_public = {"example-2": "example-1"}
            load_matches(self.path)
            (self.root / "genealogy.toml").write_text(
                '[storage]\ndatabase = "absent.sqlite"\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "distinct unresolved"):
                load_matches(self.path)

    def test_no_project_db_means_conservative_validation_without_opening(self):
        (self.root / "genealogy.toml").write_text('[storage]\ndatabase = "absent.sqlite"\n', encoding="utf-8")
        self.write_map(self.conflict)
        with patch("genealogy.store.open_project") as opened:
            with self.assertRaisesRegex(ValueError, "distinct unresolved"):
                load_matches(self.path)
            opened.assert_not_called()

    def test_cli_uses_target_context_and_read_helper_accepts_explicit_aliases(self):
        self.configure_mock_workbench()
        source = self.root / "reviews.tsv"
        source.write_text(
            "catalogue_id\tfs_id\tconfidence\nexample-1\tTEST-001\thigh\nexample-2\tTEST-001\tmedium\n",
            encoding="utf-8"
        )
        aliases = {"example-2": "example-1"}
        self.assertEqual(len(read_matches(source, aliases)), 2)
        public_export = self.root / "www/data/people.json"
        public_export.parent.mkdir(parents=True)
        public_export.write_text(json.dumps({"people": [
            {"catalogue_id": "Example-1", "profile_ids": ["Example-1"]},
        ]}))
        with patch("genealogy.store.open_project") as opened, patch("tools.workbench_legacy_views.Views") as views:
            views.return_value._merged_public = aliases
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--source", str(source), "--target", str(self.path)]), 0)
            opened.assert_called_once_with(self.root, readonly=True)
            self.assertEqual(set(json.loads(self.path.read_text())["people"]), {"example-1"})
            original = self.path.read_bytes()
            views.return_value._merged_public = {"example-2": "example-1", "example-1": "example-2"}
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["--source", str(source), "--target", str(self.path)])
            self.assertEqual(self.path.read_bytes(), original)
        # A custom destination does not borrow authority from the source/root.
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--source", str(source), "--target", str(self.root / "absent" / "links.json")])
        self.assertFalse((self.root / "absent").exists())

    def test_public_crosswalk_excludes_unlisted_withheld_and_composite_rows(self):
        source = self.root / "reviews.tsv"
        source.write_text(
            "catalogue_id\tfs_id\tconfidence\n"
            "single-1\tTEST-001\thigh\n"
            "unlisted-1\tTEST-002\tmedium\n"
            "combo-1\tTEST-003\thigh\n"
            "private-1\tTEST-004\thigh\n"
            "living-1\tTEST-005\tmedium\n"
            "documentary-1\tTEST-006\tmedium\n",
            encoding="utf-8",
        )
        original_source = source.read_bytes()
        public_export = self.root / "www/data/people.json"
        public_export.parent.mkdir(parents=True)
        public_export.write_text(json.dumps({"people": [
            {"catalogue_id": "Single-1", "profile_ids": ["Single-1"]},
            {"catalogue_id": "Combo-1", "profile_ids": ["Single-1", "Single-2"]},
            {"catalogue_id": "Private-1", "profile_ids": ["Private-1"], "withheld": True},
            {"catalogue_id": "Living-1", "profile_ids": ["Living-1"], "likely_living": True},
            {"catalogue_id": "Documentary-1", "profile_ids": []},
        ]}))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["--source", str(source), "--target", str(self.path)]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"people": 2, "withheld_from_public_crosswalk": 4})
        self.assertEqual(set(json.loads(self.path.read_text())["people"]), {"single-1", "documentary-1"})
        self.assertEqual(source.read_bytes(), original_source)

        original_target = self.path.read_bytes()
        public_export.unlink()
        with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit):
            main(["--source", str(source), "--target", str(self.path)])
        self.assertIn("Build the public people export", errors.getvalue())
        self.assertEqual(self.path.read_bytes(), original_target)


if __name__ == "__main__":
    unittest.main()
