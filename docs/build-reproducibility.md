# Build reproducibility

Status: audited 24 September 2026. The public site in `www/` cannot yet be rebuilt
from the repository with a single command. This note records how it is actually
built, where the generated site has drifted from its generators, and a proposed
route to one reproducible build.

## 1. How the site is built today

`www/` is almost entirely git-ignored. Its pages come from three kinds of step:

- **generators**, which write outputs from data;
- **repairs**, which rewrite existing HTML in place; and
- **targeted publishers**, which add or replace one section, panel or dataset.

Steps are listed in the order they must run.

The recent-edit supplement is maintained in
`tools/site_sources/map/recent-profile-supplement.json`. Run
`tools/sync_recent_profile_supplement.py --source-only` to restore its complete
public manifest using the current privacy policy and merge redirects, without
rewriting map rows. Omit the flag when synchronizing its CSV events as well.

| # | Step (command) | Required inputs | Writes | Safe to rerun alone? |
|---|---|---|---|---|
| 1 | `tools/sync_onetree_ireland_uk_to_1900.py` (`make build`, part 1) | `data/exports/one-tree/ONT_Glas*.json`, `data/wikitree/live-profile-overrides.json`, the existing `www/map/data/records.csv`, geocode cache | `www/map/data/records.csv` (One-Tree lead rows regenerated; researched rows kept), `www/map/data/audits/*` | Yes. It is incremental and fails if a qualifying profile stays unmapped. `--geocode` needs the network. |
| 2 | `tools/build_family_map.py` (`make build`, part 2) | `records.csv`, the exports, `data/wikitree/*.json`, `research/**`, `surname-research/**` | `www/index.html` stats, `www/map/index.html` (only for a legacy shell) and, via `build_research_catalog()`: `www/catalogue*.html`, all of `www/people/**`, `www/data/**`, `www/records|places/**`, `sitemap.xml`, `robots.txt`, `llms.txt`, `_headers` | **No** in isolation. It regenerates about 4,700 person pages in the *pre-unified* layout and must be followed by step 4. |
| 2a | `tools/site_sources/onetree/build.py` (called at the end of step 2) | `www/data/people.json`, the exports | `model.json`, `qa-summary.json`, `wikitree-ids.csv` in the public One Tree directory | Yes. Its HTML now goes to a scratch file (fixed in this audit; see D3). |
| 2b | `tools/sync_onetree_map_assets.py` | Maintained map CSV, public catalogue index/dossiers, local profile privacy metadata and existing modern map assets | Compact record index, record-detail JSON and modern map points; adds missing public historical profile leads and removes withheld record associations | Yes, after CSV sync and `tools/public_privacy.py`. Retains reviewed records and supplied coordinates/precision; never geocodes or rebuilds the catalogue. Run the privacy pass again after other dossier writers, then refresh release indexes/manifests. |
| 3 | `tools/audit_missing_wikitree_profiles.py [--apply-new-draft-matches]` | `people.json`, `records.csv`, drafts, **live WikiTree API** | `data/wikitree/catalogue-profile-audit.json` (+ `catalogue-profile-links.json` with `--apply…`) | Yes, but it needs the network. Run it before step 2 when drafts change. |
| 4 | `tools/repair_unified_site.py` | all of `www/` **and `www_old/`** | Runs, in order: people/records/catalogue/local-route/project-route/free-space/UI repairs; `repair_site_experience`; 17 presentation helpers (`repair_timeline_navigation` … `build_branches_directory`, `build_study_pages`, `build_statistics_page`, `repair_person_hierarchy`, `repair_primary_navigation`, `repair_research_questions`, `repair_exploration_layout`); the Irish death index and three OPR review publishers; `site_analytics`; and `publish_research_release.publish()` | **Cannot run.** `main()` exits with status 2 because `www_old/` is absent. With the guard bypassed, `repair_records` and `restore_archival_snapshots` still fail (see D6). |
| 5 | Targeted publishers run by hand after research batches (`add_research_case_dossiers.py`, `publish_resolved_dossiers.py`, `sync_catalogue_research.py`, `build_research_catalog.sync_generated_marriage_statistics()`, `publish_groni_*`, `build_evidence_page.py`, …) | Research files and existing `www` | Individual pages, panels and JSON indexes | Mostly idempotent, but each assumes the markup left by an earlier step. |
| 6 | Checks: `tools/check_release_consistency.py`, `tools/check_public_catalogue.py`, `tools/audit_site_experience.py`, `tools/stamp_asset_versions.py --check`, `make test`, browser scripts `tests/test_public_catalogue_ui.py` and `tests/test_catalogue_one_tree_ui.py` (`CATALOGUE_TEST_BASE=http://127.0.0.1:8765`) | `www/` | Nothing, except where `--fix`/`--write` is given | Yes |

Inputs that no generator produces (hand-maintained or orphaned artefacts):

- `www/assets/research/atlas-model.json` is the public Atlas model loaded by
  `atlas-boot.js`. It is a post-processed copy of `model.json` with display dates
  and `researchUrl` fields; the last copy was made on 8 September. No tool writes it.
- `www/assets/research/record-index.json` is the compact record index read by
  `repair_records`. It contains IDs that are missing from `www/data/records-index.json`.
  `sync_onetree_map_assets.py` now maintains missing One-Tree lead coverage and
  removes withheld associations, while preserving the existing reviewed rows.
  It still requires those existing assets and is not a from-scratch renderer.
- The page shells for `www/map/index.html`, `www/onetree/index.html`,
  `www/timeline/index.html` and the unified home page have no generator. Repairs
  patch them in place.
- `www/map/advanced.html` is the legacy map with embedded data. Step 2 skips it
  because the modern `/map/` shell is detected, so its embedded dataset is frozen.
- `www/status/index.html` and `www/data/index.html` still use the legacy "brand"
  header and have never received the unified rail.

## 2. Drift findings

### Dry run of the repair entry points

Each entry point was run with the writes captured in memory (`Path.write_text`,
`write_bytes`, `open(..., "w")`, `shutil` copies and atomic writers recorded, not
written), then compared with the files on disk. Nothing was written to disk.

| Entry point | Files it would change | Categories of change |
|---|---|---|
| `repair_primary_navigation.repair()` | 2 (the count varies while other agents edit `www`) | `www/evidence/index.html`: marks **Overview** as current instead of About (`/evidence/` is not in the route map). A new GRONI records page lacks the "Latest research" footer link. The submenu assets are otherwise in sync. All other HTML already matches, so this step is converged. |
| `repair_site_experience.repair()` run alone | 13 | Destructive when run out of order. It removes the 21 `research-*` study groups from `branches.json` (352 → 331, later restored by `repair_research_groups`), removes the GRONI death-match section from `/branches/early-ireland/` (69 KB → 33 KB, later restored by `publish_irish_death_index`), and removes the curated Scottish-studies nav. It also re-adds CSS rules to `assets/repair/site.css` and rewrites the `registry*.json`, `onetree/index.html` and `ydna/index.html`. It also **writes the tool source `tools/catalogue_search.js`**. |
| `repair_unified_site.main()` | 0 | Exits with status 2 ("both www and www_old are required"). |
| `repair_unified_site` step sequence (guard bypassed, each step isolated) | 6,165 changed plus 4 created (of 6,216 written) | **Errors:** `repair_records` raises `KeyError` (stale `record-index.json`); `restore_archival_snapshots` needs `www_old`; `build_statistics_page` could not find the statistics pane (fixed, see D4). **By area:** `people/` 4,782, `places/` 1,261, `catalogue/` 49, `research/` 28, `data/` 11, `branches/` 11. **Categories:** (a) serializer churn: attribute reordering and `/>` changes from BeautifulSoup in `repair_profile_wikitree_links` and `repair_person_hierarchy`; (b) asset-version bumps, `catalogue.css?v=…light-2` → `…toolbar-2`, in 1,427 place/catalogue/compare pages; (c) evidence-label wording not yet regenerated ("Unassessed child link" → "Unassessed son/daughter link"; in progress by the evidence-label work); (d) an added `profile-wikitree.css` link on person pages; (e) `catalogue/index.html` `<base>` and fallback-script changes that would undo the current toolbar shell; (f) new public data files (Irish civil deaths CSV and OPR review JSON). |

### Specific defects

- **D1. Path drift (fixed).** `tests/_generated_data.py` and
  `tools/build_family_map.py` pointed at `www/onetree/glasgow-one-tree-polished/`.
  The only directory is `…-polished-3/`, so 69 generated-data tests were skipped
  silently. `tools/project_paths.ONETREE_STANDALONE_DIR` is now the single source of
  this path. `tests/test_ydna_explorer.py` also checked `ROOT/index.html` instead of
  `www/index.html`, so one more test was always skipped.
- **D2. Stale generated data.** These need a regeneration run, not code changes:
  - `records.csv` lacks Glasgow-4031, Glasgow-4179, Glasgow-4180, Glasgow-4181 and Allan-6611; step 1 adds them.
  - `model.json` (21 September) still lists redirected Glasgow-2717 and Glasgow-2869, and Glasgow-3905 and Kyle-3461, which have no pages; step 2a fixes it.
  - `/statistics/` shows 4,564 people against 4,662 in the catalogue.
  - The catalogue marriage panel shows Wilson 9 where the search returns 10.
- **D3. The standalone One-Tree build replaced its redirect stub (fixed).**
  `build.py` wrote a full viewer over the maintained redirect at
  `…-polished-3/index.html` on every `build_family_map.py` run. The HTML now goes to
  a temporary file.
- **D4. `build_statistics_page.py` broke when the catalogue was restructured (fixed).**
  The pane is now a sibling section after the results, and the research shell is
  reserialized with `/>`. Both regular expressions now accept either form.
  `check_release_consistency.py` now also checks `statistics/index.html`.
- **D5. Marriage-surname statistics disagreed with the search (fixed in the generator).**
  `_marriage_surname_values` grouped surnames by exact spelling. The search folds
  case, accents and punctuation. So "Wilson" and "WIlson", "Ross" and "ROSS", and
  "McLean" and "Mclean" appeared as separate bars, with counts below what their
  links return. The generator now groups with the same normalisation as the search.
  A test proves that all 1,110 bars equal the search result counts. Cunningham was
  already consistent in the current data (10 = 10); the earlier panel value of 9 was
  a stale render.
- **D6. The unified repair depends on artefacts outside the repository.** `www_old/`
  is not present. `record-index.json` has no generator. `atlas-model.json` has no
  generator.
- **D7. Out-of-order repairs undo each other.** `repair_site_experience` deletes
  content that later helpers add back. Presentation state therefore depends on the
  whole ordered chain, and any single repair run on its own is unsafe.
- **D8. Repairs write sources.** `repair_site_experience` rewrites
  `tools/catalogue_search.js`, and `build_family_map` → `build_research_catalog`
  copies tool sources into `www`.
- **D9. Owned by other work streams (reported, not changed):**
  - `add_research_case_dossiers.py` appends compact-index rows without removing internal `_sibling_ids` and similar fields (Hewitt-8271, Glasgow-4342).
  - `publish_resolved_dossiers.py` forces `tree_relationship=False` on shared assertions, but WikiTree still links Glasgow-938 to Glasgow-951.
  - The person-dossier layout (`repair_person_hierarchy.py`) drops the WikiTree snapshot, dataset provenance and record source links, and renders queued update drafts on candidate comparison pages (5 rendered against 3 queued).
  - Evidence-label HTML adds a "Possible ·" prefix that the dossier JSON `status_label` lacks.
  - `catalogue/index.html` has no "Latest research" footer link.

## 3. Proposed path to one reproducible build

1. **Make `www/` a pure output.** Move every hand-maintained shell (home, map,
   Atlas, timeline, Y-DNA, status, data and statistics pages) into
   `templates/<route>.html`, using the unified shell once, as a Jinja or
   `string.Template` layout with blocks. Commit the templates. Keep `www/`
   ignored and deletable.
2. **Replace the in-place repairs with render functions.** Each
   `repair_*`/`build_*_page` becomes `render(context) -> {relative_path: text}`
   and never reads the page it writes. Rail, footer, analytics tag and submenu
   assets become template partials. That removes D7, D8 and the serializer churn
   (so no BeautifulSoup round-trips on output).
3. **Commit or generate the orphaned inputs.** Generate `atlas-model.json` from
   `model.json` with a small transform in the One-Tree step. Generate
   `record-index.json` from `records-index.json`. Retire the `www_old` parity
   audit or freeze its reference into `tests/fixtures/`.
4. **Use one command.** `make site`, running `tools/build_site.py`, would:
   `sync_onetree` (without the network by default) → catalogue data → One-Tree
   model → render all templates into `build/www.tmp` → targeted publishers as
   render steps → `site_analytics` → `stamp_asset_versions --write` → atomically
   swap `build/www.tmp` for `www`. It would then run `check_release_consistency`,
   `check_public_catalogue`, `audit_site_experience` and `make test`. Live WikiTree
   audits (step 3) stay a separate `make refresh-live` that writes only `data/`.
5. **Guard reproducibility in CI.** Add a test that builds twice and diffs the
   outputs (expecting no differences), and one that runs every render step on a
   fixture dataset. Until then, treat `repair_unified_site.py` as the only safe
   entry point for presentation changes, and do not run individual repairs.

## 4. Commands still to run (orchestrator)

These write `www/` or `data/` and were deliberately not run during the audit. Run
them in this order:

```sh
.venv/bin/python tools/sync_onetree_ireland_uk_to_1900.py            # records.csv: +5 missing profiles
.venv/bin/python tools/site_sources/onetree/build.py \
  --output /tmp/onetree-standalone.html                               # model.json without redirected IDs
.venv/bin/python -c "import sys; sys.path.insert(0, 'tools'); from build_research_catalog import sync_generated_marriage_statistics as s; s()"
.venv/bin/python tools/build_statistics_page.py                       # /statistics/ totals and panels
.venv/bin/python tools/check_release_consistency.py                   # expect "Release totals consistent."
```

A full `tools/build_family_map.py` also covers the first two commands, but it
regenerates every person page in the pre-unified layout. After it, the unified
repair chain would have to run, and that chain is blocked (D6).
