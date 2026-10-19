# Toolkit separation validation — 19 October 2026

The standalone `genealogy-research-workbench` release is `v0.2.0`, commit `0a0872f5f02d612859c92e67c384b6e9c9bdfd21`. Glasgow consumes that exact commit as a Git submodule, with a compatible Python package requirement of `>=0.2.0,<0.3.0`.

## Standalone toolkit

Local checks used Python 3.14.7 on macOS. CI is configured for Python 3.11–3.14; those remote jobs have not been run as part of this local handoff.

- `make check`: 90 tests collected, 86 passed and 4 opt-in browser tests skipped; Ruff passed.
- Separate browser suite: all 4 tests passed, covering desktop/mobile routes, no-JavaScript records, people search/pagination, whole-tree/family/branch views, comparisons, connections, timeline/source filters, map controls and real GEDCOM/OneTree uploads.
- Wheel and source distributions built successfully. Package contents include project templates, website assets, MIT licence and data notices; private workspaces and generated test output are excluded.
- A fresh Git clone was built into a wheel, installed outside the source checkout, and exercised through `init → import → validate → build`. The GEDCOM demo produced 42 people and 3 reviewed sources; the OneTree demo produced 42 people. The installed package loaded from the fresh virtual environment, not the working source tree.
- Documentation links, anchors and all six screenshot assets were checked. README previews were inspected at desktop and mobile widths.
- A synthetic 5,000-person case built a 63 MB site in approximately 54 seconds. The whole tree and catalogue became ready in approximately 3.3 and 2.5 seconds locally, with no browser errors. These are local smoke measurements, not hosting/network performance guarantees.

The final release retains an empty seed case in both project templates, even though generated projects correctly ignore private `cases/` contents. Fresh-clone verification caught and confirmed this packaging detail.

## Glasgow consumer

Passed:

- Base/development dependency installation loads toolkit `0.2.0` from the pinned submodule.
- All 11 toolkit integration tests and 6 private research-bundle compatibility tests.
- A fresh Glasgow Git clone, with the exact submodule seeded from the independent local repository, installed only `requirements/base.txt` plus constraints in a new virtual environment and passed all 17 integration tests. No development extras or pre-existing environment were required.
- Ruff and public CSV/JSON data validation.
- Browser fixture smoke: 9 pages, zero failures.
- Research-publication gate: zero new failing items against the existing baseline.
- Internal-link gate: zero new broken page-target pairs against the existing baseline.
- Changed documentation references and Git submodule/tag agreement.

### Existing full-suite failures

`make check` is **not green**: 871 tests ran, with 328 assertion failures, 11 errors and 6 skips. Subtests account for most of these results; they occur in 18 distinct test methods across the following existing modules:

- `test_resolved_public_model`
- `test_research_catalog`
- `test_onetree_output`
- `test_robert_hypothesis_exports`
- `test_dossier_parents`
- `test_onetree_map_coverage`
- `test_release_readiness`
- `test_site_experience`
- `test_sync_catalogue_privacy`

The failing methods were checked against unchanged Glasgow revision `e0cf4d2aec` and its original toolkit `0.1.0`, using the same local research/site inputs. They also fail before the dependency upgrade. Three research-catalogue checks are sensitive to symlink resolution; those were additionally checked at their original paths, with unchanged implementation/test files and the original toolkit imported explicitly. This avoids attributing temporary-worktree path errors to the migration. A comparison of all 339 failure/error identities then matched the pre-upgrade outcomes exactly: zero new identities and zero removed identities.

Representative existing issues include disagreement between catalogue snapshot counts, a missing canonical profile destination, historical relationship output inconsistencies and an outdated route expectation. No historical research, generated Glasgow site output or test baseline was rewritten to mask these failures. The focused tests for changed dependency/identity paths pass.

## Publication boundary

No repository was pushed and no website was deployed. The toolkit remote/commit must be published before another person or CI can fetch Glasgow’s new submodule. Publish the toolkit first, then the Glasgow consumer commit. Local dependency checks can seed the submodule from the standalone checkout; that does not verify a hosted upstream fetch.

The release builds a general research website from the supported export fields. It cannot recreate missing archive research, original source images, researched family studies or DNA findings from a tree export alone. See the standalone README and import-format guide for the supported subset and publication controls.
