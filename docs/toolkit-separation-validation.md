# Toolkit separation validation — 19 October 2026

The published [genealogy-research-workbench v0.2.0 release](https://github.com/glasgowm148/genealogy-research-workbench/releases/tag/v0.2.0) is commit `cc7a3d8c657e5813c26f136005c36179e96ee56e`. Glasgow consumes that exact commit as a Git submodule, with a compatible Python package requirement of `>=0.2.0,<0.3.0`.

## Standalone toolkit

Local core checks used Python 3.14.7 on macOS; the separate browser run used Python 3.12. Hosted [main CI](https://github.com/glasgowm148/genealogy-research-workbench/actions/runs/39258877834) and [tag CI](https://github.com/glasgowm148/genealogy-research-workbench/actions/runs/39258878404) both passed all five jobs: package/tests on Python 3.11–3.14, plus browser checks.

- `make check`: 91 tests collected, 87 passed and 4 opt-in browser tests skipped; Ruff passed.
- Separate browser suite: all 4 tests passed, covering desktop/mobile routes, no-JavaScript records, people search/pagination, whole-tree/family/branch views, comparisons, connections, timeline/source filters, map controls and real GEDCOM/OneTree uploads.
- Wheel and source distributions built successfully. Package contents include project templates, website assets, MIT licence and data notices; private workspaces and generated test output are excluded.
- A fresh Git clone was built into a wheel, installed outside the source checkout, and exercised through `init → import → validate → build`. The GEDCOM demo produced 42 people and 3 reviewed sources; the OneTree demo produced 42 people. The installed package loaded from the fresh virtual environment, not the working source tree.
- Documentation links, anchors and all six screenshot assets were checked. README previews were inspected at desktop and mobile widths.
- A synthetic 5,000-person case built a 63 MB site in approximately 54 seconds. The whole tree and catalogue became ready in approximately 3.3 and 2.5 seconds locally, with no browser errors. These are local smoke measurements, not hosting/network performance guarantees.

The final release retains an empty seed case in both project templates, even though generated projects correctly ignore private `cases/` contents. Fresh-clone verification caught and confirmed this packaging detail.

### Real-export checks

Two existing GEDCOM files and two OneTree exports were tested in isolated local directories. The reusable repository, fixtures and release contain none of their data.

| Input | Imported people | Public preview people | Withheld people | Public relationships | Public events |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legacy GEDCOM | 169 | 136 | 33 | 214 | 319 |
| Desktop GEDCOM | 2,079 | 1,460 | 619 | 2,260 | 2,983 |
| Independent OneTree tree | 238 | 139 | 99 | 146 | 278 |
| Large OneTree tree | 4,394 | 3,133 | 1,261 | 4,042 | 6,266 |

Each passed default-private import, explicit deceased-person review, case validation, relationship endpoint checks, withheld narrative/quotation checks, full site generation and dossier counts. Original input hashes remained unchanged. Missing relatives are omitted with warnings, and locations without coordinates remain unmapped. Neither GEDCOM supplied source records; OneTree biography markup is not normalised into source citations. The fictional installed-wheel GEDCOM separately verified its three sources and citation workflow.

These inputs exposed a false raw-DNA rejection of opaque external record IDs containing `VCF`. The release fixes that exact key-shape collision and retains recursive rejection of genetic fields beneath those IDs. Regression tests cover both behaviours. A fresh clone of the hosted `v0.2.0` tag confirmed the exact commit and both seed cases; a separate installed wheel imported and built both 42-person examples outside the source checkout.

## Glasgow consumer

Passed:

- Base/development dependency installation loads toolkit `0.2.0` from the pinned submodule.
- All 11 toolkit integration tests and 6 private research-bundle compatibility tests.
- Full local discovery: 908 tests, 902 passed and 6 skipped, with the generated research/site checks enabled. Ruff and CSV/JSON validation passed. The Linux fixture correction also passed its separate three-test module locally.
- A fresh recursive clone from public GitHub at Glasgow commit `180d55f42e1a51310fc0608f94430c5f290f2dcb` fetched the exact published submodule, installed only `requirements/base.txt` plus constraints in a new virtual environment and passed all 17 integration tests and `pip check`. No local URL overrides, development extras or pre-existing environment were required.
- Hosted [Glasgow CI](https://github.com/glasgowm148/glasgow-surname-ancestry/actions/runs/39271275762) passed Python 3.12, Python 3.13 and browser jobs. Each Python job collected 908 tests, with 200 explicitly skipped for absent local artifacts; fixture checks remained active. A Linux-only filename-case mismatch in a fictional fixture was corrected.
- Ruff and public CSV/JSON data validation.
- Browser fixture smoke: 9 pages, zero failures.
- Real-site browser checks: 12 pages across mobile and desktop, zero JavaScript errors; the loaded tree was additionally checked at both widths and screenshots inspected.
- Research-publication gate: zero new failing items against the existing baseline.
- Internal-link gate: zero new broken page-target pairs against the existing baseline.
- Changed documentation references and Git submodule/tag agreement.

### Pre-repair full-suite baseline

Before the follow-up repair, `make check` ran 871 tests, with 328 assertion failures, 11 errors and 6 skips. Subtests account for most of these results; they occurred in 18 distinct test methods across the following existing modules:

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

Representative issues included disagreement between catalogue snapshot counts, relationship output inconsistencies and an outdated route expectation. The initial separation did not rewrite historical research, generated Glasgow output or test baselines to mask them. The owner subsequently authorised repairing the existing failures and publishing both repositories.

### Follow-up repairs

- Reviewed relationships, curated labels and percentages now agree across HTML, dossiers, network exports and embedded archives. Eight original source claims were recovered with exactly the existing builder's IDs; the all-dossier audit found no dangling evidence/claim references. The six intentionally withheld resolver entries remain placeholders.
- Existing vital assessments now have a maintained source in `research/vital_assessments.json`, including the previously published withdrawal of the unnamed child's death bound. Unknown location placeholders remain in source history and notes rather than becoming searchable places.
- The compact resolver retains operational relationship states and imported history without duplicating dossier narratives. Its 5,103,668 bytes fit the unchanged 5,352,600-byte budget. Workbench summaries retain candidate HOLD counts and use the maintained review overlay.
- The living-person screen recognises redacted birth decades. It removed 27 newly identified likely living subjects from public views, leaving 4,866 catalogue/search entries. Projection now preserves packed-table positions and map tuples, removes direct private pages and orphaned private rows, and retains valid historical namesakes and aliases.
- The maintained modern-map synchroniser reattaches supplied profile leads without geocoding or changing their precision. Map references and record-detail ownership are checked together. Withheld ghost nodes are removed from tree models; previously approved DNA is restored only from authenticated originals in three existing approved paths, with living identifiers still rejected and no approval hashes changed.
- Runtime setup declares Beautiful Soup. Clean-checkout tests use fictional fixtures wherever possible and explicitly mark checks needing ignored local research/site artifacts. Those checks remain enabled locally. The link gate likewise requires generated site data, rather than testing an incomplete Git checkout as a built website. Neither research nor link baselines were expanded.
- Removed reviewed fathers no longer leave a current paternal root attached; retained export roots and prior counts remain reversible. Queue checks distinguish full amendments, privacy-safe additions and reviewed creation tasks. All public comparison candidates remain represented, while blocked candidates and direct subject routes remain absent.
- The complete 23-profile historical map supplement now has a maintained source. Its existing coverage checks remain unchanged; publication filters privacy before and after normalising merged identifiers.

The publication gates reported zero new research failures and zero new broken page-target pairs. The existing link baseline still contains seven broken references (four page-target pairs); 62 missing person-page anchors remain outside that gate. Asset stamping settled with zero stale references.

## Publication boundary

Both repositories are public and their completed implementation commits are pushed. The toolkit's `v0.2.0` tag and GitHub release include wheel and source archives. A hosted tag clone and hosted CI verified upstream availability before Glasgow publication; the public recursive consumer clone then verified the dependency without local substitutions. Package-index publication and deployment of the Glasgow website are separate actions; neither was performed.

The release builds a general research website from the supported export fields. It cannot recreate missing archive research, original source images, researched family studies or DNA findings from a tree export alone. See the standalone README and import-format guide for the supported subset and publication controls.

## Independent re-verification and toolkit 0.3.0 — 19 October 2026 (evening)

The earlier claims were re-run rather than assumed. Checks ran in a Linux VM with Python 3.12 against the local checkouts, and in a separate cloud environment with Python 3.11 and 3.13 against public clones.

Confirmed:

- **Toolkit 0.2.0:** 91 tests, 4 opt-in browser tests skipped; the 4 browser tests pass. The hosted `v0.2.0` tag and `main` resolve to `cc7a3d8`.
- **Glasgow:** 908 tests, 0 failures, 6 skips with local artifacts present.
- **Fresh public recursive clone:** fetches the pinned submodule, installs from base requirements only and passes `pip check` and the 17 integration tests.
- **Sibling-checkout override:** works.
- **Toolkit boundary:** the toolkit contains no Glasgow imports, paths or identifiers.

Found and corrected:

- **WikiTree's own GEDCOM export could not be imported.** Raw line breaks inside notes produced 205 invalid lines. The "four real exports" were two desktop GEDCOMs and two OneTree files; this third format was untested.
- **Relationship roles were flattened.** Family Tree Maker `_FREL Step` and WikiTree non-biological parent links were imported as plain parents, and the tree's own uncertain/confident marks were discarded.
- **Uncertainty was lost from WikiTree dates.** `YYYY-00-00` dates could not be assessed, and guess/before/after qualifiers were dropped.
- **OneTree couples were doubled.** Each couple was imported twice, and marriages were not imported.
- **Non-UTF-8 files were rejected outright.** GEDCOM files declaring ANSI or ANSEL could not be imported at all.
- **Updating from a newer export lost research.** It required `--replace`, which discarded added research without a backup.
- **The fictional demo drew its tree upside down.** It stored parent links from parent to child, against the documented child → parent direction, so the README's family-tree screenshot showed descendants as ancestors.
- **The submodule's local `v0.2.0` tag was stale.** It pointed at the pre-release commit `0a0872f`, not the published tag. It now matches the published tag object.
- **Glasgow code issues.**
  - `sync_recent_wikitree_changes.py` used a 100-year living-person rule where every other screen uses 120 years.
  - `sync_catalogue_research.py` first tried to import a toolkit module that does not exist.
  - Three GRONI tools hard-coded `/Users/m/Downloads/...`; the path can now be overridden with `GLASGOW_CIVIL_RECORDS_CSV`.
  - `check_site_quality.py` hard-coded the macOS Chrome path; `GLASGOW_BROWSER_EXECUTABLE` can now select another browser.

Toolkit 0.3.0 (local commits `1c63d9c`, `9542dba`, `83570c6`, `afb4aa3`) fixes the toolkit issues and adds:

- family dossiers;
- an evidence-label guide;
- a shared data script;
- a surname filter;
- a public GEDCOM download;
- an optional XML sitemap.

The [changelog](../vendor/genealogy-research-workbench/CHANGELOG.md) and [parity matrix](toolkit-parity.md) give the details. One deliberate policy change applies: an approximate birth (`ABT 1800`) now counts as up to ten years later (1810) under the unchanged 120-year rule.

Results with 0.3.0:

- **Toolkit:** 112 tests, 5 opt-in browser tests skipped (Python 3.11, 3.12 and 3.13); the 5 browser tests pass at desktop and mobile widths, including from `file://`.
- **Packages:** the wheel and source distribution build. An installed-wheel `init → import → build` of the fictional GEDCOM produced 42 dossiers. The source distribution ships the examples and screenshots.
- **Real local exports (read-only):** all six now import, including the WikiTree GEDCOM. No withheld person's ID appears in any generated file. Counts are in the parity matrix.
- **Glasgow with the new pin:**
  - 908 tests, 0 failures, 6 skips.
  - Ruff and data validation pass.
  - The research-publication gate shows 0 new failures (5 baseline items now fixed and not yet removed from the baseline).
  - The link gate shows 0 new broken pairs (1 fixed).
  - The browser fixture smoke check passes (9 pages, 0 failures).
- **Public clone with the new pin and these changes (Python 3.13):** 908 tests, 200 skipped for absent private artifacts. One error came from a missing `rsync` binary in that environment, not from the code.

Not yet done: the toolkit commits are local. Push them, and tag `v0.3.0` if wanted, before pushing the Glasgow commit that pins `afb4aa3`.
