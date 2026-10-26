# Site builder inputs

Generated from `tools/*.py` on 26 October 2026. 102 of the Glasgow tools read or write `www/`. The table lists the generated `www/` files that other builders read as inputs, with how many builders read each: the site is built in place, with `www/` serving as both output and intermediate store. This is why the Glasgow site cannot yet be rebuilt from an empty `www/`.

| `www/` file read as an input | Builders reading it | Examples |
| --- | ---: | --- |
| `data/catalogue-search-index.json` | 18 | add_research_case_dossiers.py, build_ancestry_progress.py, catalogue_location_search.py, catalogue_search_index.py |
| `data/people-index.json` | 18 | add_research_case_dossiers.py, branch_connectivity.py, build_backlinks.py, build_latest_research.py |
| `data/people.json` | 16 | add_research_case_dossiers.py, build_research_catalog.py, catalogue_location_search.py, check_release_consistency.py |
| `assets/research/branches.json` | 15 | build_backlinks.py, build_branches_directory.py, build_regional_study_maps.py, build_study_pages.py |
| `data/records-index.json` | 12 | check_public_catalogue.py, check_research_publication.py, fmp_record_preflight.py, ingest_canonical_records.py |
| `data/people-index.js` | 11 | add_research_case_dossiers.py, build_research_catalog.py, catalogue_location_search.py, project_record_locations.py |
| `assets/research/registry.json` | 10 | add_research_case_dossiers.py, build_study_pages.py, public_privacy.py, queue_catalogue_creations.py |
| `map/data/records.csv` | 10 | build_branches_directory.py, build_regional_study_maps.py, build_study_pages.py, check_research_publication.py |
| `assets/research/atlas-model.json` | 9 | approved_restorations.py, build_tree_research_status.py, public_privacy.py, public_ydna_research.py |
| `assets/research/record-index.json` | 9 | ingest_canonical_records.py, project_record_locations.py, reconcile_catalogue_profile_links.py, repair_research_groups.py |
| `assets/research/assessments.json` | 6 | add_research_case_dossiers.py, build_research_catalog.py, publish_research_access.py, publish_resolved_dossiers.py |
| `assets/research/branches-directory.json` | 6 | audit_site_experience.py, build_branches_directory.py, build_regional_study_maps.py, repair_site_experience.py |
| `assets/research/free-space-index.json` | 6 | build_free_space_site.py, check_public_catalogue.py, free_space_edition.py, publish_research_access.py |
| `people/search.js` | 6 | catalogue_search_index.py, check_site_quality.py, finalize_site.py, repair_reader_guidance.py |
| `people/{slug}.json` | 6 | add_research_case_dossiers.py, build_research_catalog.py, catalogue_machine_data.py, project_record_locations.py |
| `assets/research/search-people.json` | 5 | add_research_case_dossiers.py, project_record_locations.py, public_privacy.py, reconcile_catalogue_profile_links.py |
| `data/places-index.json` | 5 | check_public_catalogue.py, project_record_locations.py, site_search.py, site_sitemap.py |
| `data/source-review.csv` | 5 | about_pages.py, build_research_catalog.py, reconcile_catalogue_profile_links.py, records_page.py |
| `assets/research/atlas-boot.js` | 4 | approved_restorations.py, repair_evidence_labels.py, site_payloads.py, sync_ancestry_atlas.py |
| `assets/research/atlas.js` | 4 | repair_evidence_labels.py, repair_public_dna.py, repair_unified_site.py, sync_ancestry_atlas.py |
| `assets/research/map-points.json` | 4 | project_record_locations.py, repair_site_experience.py, repair_unified_site.py, sync_onetree_map_assets.py |
| `assets/research/map.js` | 4 | build_family_map.py, repair_map_state_fallbacks.py, repair_site_experience.py, repair_unified_site.py |
| `assets/research/search-index.json` | 4 | add_research_case_dossiers.py, project_record_locations.py, reconcile_catalogue_profile_links.py, reconcile_retired_record_subjects.py |
| `data/manifest.json` | 4 | finalize_site.py, publish_research_access.py, smoke_test_site.py, verify_dossier_delivery.py |
| `onetree/glasgow-one-tree-polished-3/model.json` | 4 | public_privacy.py, public_ydna_research.py, repair_atlas_destinations.py, repair_public_dna.py |
| `people/{slug}.network.json` | 4 | add_research_case_dossiers.py, catalogue_machine_data.py, queue_catalogue_creations.py, reconcile_catalogue_profile_links.py |
| `assets/research/atlas-import.json` | 3 | public_privacy.py, public_ydna_research.py, repair_public_dna.py |
| `assets/research/atlas-model-packed.json` | 3 | approved_restorations.py, reconcile_catalogue_profile_links.py, site_payloads.py |
| `assets/research/event-index.json` | 3 | project_record_locations.py, reconcile_catalogue_profile_links.py, repair_assessment_dates.py |
| `assets/research/people/{slug}.json` | 3 | add_research_case_dossiers.py, project_record_locations.py, reconcile_catalogue_profile_links.py |

109 generated files are read this way in total.

## What is already declared

- The research inputs (`research/relationship_assessments.json`, `relationship_probability_estimates.json`, `canonical_records.json`, `latest-findings.json`, `vital_assessments.json`, every `research_plan.json` and `parent_candidates.json`, the update queue and its review files) are generated from the research database as the first step of `make build` and `tools/rebuild_local_site.sh`.
- Site inputs that no builder produces (`www/map/data/early-bearers.json`, `ydna-timeline.json`, `recent-profile-supplement.json`) are declared in `data/site/declared-inputs.json` with private homes and installed by `tools/site_declared_inputs.py --install`.

## Rebuild experiment (25 October 2026)

Four runs of `make build` followed by `tools/rebuild_local_site.sh`, each on a
copy-on-write clone of the main checkout. The real `www/`, the research
database and the remotes were not touched.

1. **Empty `www/`.** Stops at the first builder that reads a page it does not
   make: `make build` needs `www/map/data/records.csv` and the rebuild script
   needs `www/about/index.html` as a page template. Neither file is tracked in
   Git, and no tool creates either from nothing. The ignored part of `www/`
   (about 73,000 files) is therefore part of the site's source, not only its
   output. Backups keep it; Git does not.
2. **Copy of the real `www/`.** `make build` and the rebuild both stop in
   `publish_resolved_dossiers.py`: shared assertion
   `C-coverage-20261022g-glasgow-3398-father` has no relationship on Glasgow-1466.
   The link existed only in `www/`. A one-off script
   (`tmp/parent-merge-repair-2026-10-17/integrate.py`) had restored 22
   live-verified WikiTree parent links after a profile merge by editing `www/`
   directly. The catalogue builder recovers such a parent on the child's side
   (`_captured_parent_relations`) but never added the child to the parent's
   side, so every rebuild dropped half of each link. **Fixed:**
   `build_research_catalog._add_captured_children` adds the inverse link (tests
   in `tests/test_captured_parent_relations.py`).
3. **With that fix.** `make build` passes the publish step and stops in
   `branch_connectivity.py`: `Duplicate documentary ancestor:
   record-bessie-lanark-1650`. Reviewed new-person dossiers get their creation
   state from `tools/queue_catalogue_creations.py`, which no build ran; the
   catalogue builder rewrites those dossiers without it. **Fixed:**
   `build_family_map.py` now applies the reviewed creations straight after the
   catalogue, before the tree and the connectivity read them.
4. **With both fixes.** `make build` passes (4,873 catalogue people, 6,313
   pages), and the rebuild runs 24 of its 25 steps (the tolerated research
   publication check reports its usual findings). It stops in `finalize`:
   `ingest_canonical_records.plan` refuses `held-e-827fa902bccc` because three
   existing records share its provider key. For sources other than Findmypast
   the key is the page URL, and that page (Rasharkin baptisms, 1834) holds
   several baptisms. The live `www/` has one record there because records were
   ingested one at a time, while a fresh catalogue lists all three. Deciding
   what identifies a record on a multi-record page is a research-model choice
   (the check is a deliberate review stop). Decided on 26 October: an entry on
   a page is told apart by the people it names
   (`ingest_canonical_records.entry_key`), and two existing rows for the same
   entry still stop for review.

## Full rebuild and what `www/` holds (26 October 2026)

With records on a shared page told apart by the people they name, the fifth run
(a copy of the live `www/`, every `www/` file access logged by a Python audit
hook) completed **all 25 build steps**. Then the checks were compared with the
same checks run on the live site:

| Check | Live `www/` | Rebuilt `www/` |
| --- | --- | --- |
| Privacy: withheld identifiers present | 0 | 29 (one likely-living spouse, Harris-58431, and the pages and indexes that list him) |
| New research/release failures against their baselines | 0 / 0 | 4 / 4 |
| New broken internal links | 1 | 20 |
| Person pages whose tree links would change | 0 | 415 |

The rebuild is therefore **not yet equivalent to the live site**, and a rebuilt
`www/` must not be published until these match. The live site holds corrections
that no builder makes; they were applied in place by repair scripts.

- **Fixed:** the privacy leak. The catalogue builder made its privacy policy
  from only the profiles it was given (the 4,566 qualifying ones), while
  Harris-58431's living status is recorded only in another export. It now uses
  every merged export as well (`public_privacy.from_sources(..., all_exports=True)`).
- **Not yet fixed:** the 20 broken links, the 415 tree-link pages and the
  research and release items. Each is a correction the live site has and the
  builders do not make.
- The build also deletes 6,574 files from a copy of the live `www/` (988 MB):
  5,778 old catalogue detail files and 624 orphaned research-material pages,
  but also, for example, `people/allan-8249.html` and
  `data/irish-civil-deaths-1864-1900.csv`. Each needs a check before a rebuilt
  site replaces the live one.

The access log sorts the 90,177 files in `www/`:

| Class | Files |
| --- | ---: |
| Tracked in Git | 17,108 |
| Read by the build, never written (sources that exist only in `www/`) | 27,577 |
| Read first, then rewritten in place (build state, such as `map/data/records.csv`) | 454 |
| Written before any read (outputs) | 19,611 |
| Neither read nor written | 22,493 |
| Deleted by the build | 6,574 |

The 28,031 read-first files (318 MB), the 19,172 untouched files still in the
live `www/` (153 MB; static parts of the published site no build step makes),
the four builder ownership markers and `.htaccess` are now **declared build
state** (47,207 files)
(`tools/site_declared_inputs.py --declare-state`). Each has a private home in
`data/private/site-state/`, recorded with its SHA-256 in a private manifest.
`--install`, the first step of `make build` and of the rebuild script, seeds
any of them that `www/` lacks and never overwrites one that is present. After
reviewing a rebuild's checks, `--save-state` carries the current versions
forward. This is deliberate rather than automatic, so a rebuild that failed the
privacy check cannot become the next build's input.

**From an empty `www/`** (only the Git-tracked files plus the declared homes),
`make build` now passes with the same output as from the live copy: 4,873
catalogue people across 6,313 pages. The first such run found that the
builder ownership markers had to be declared too. They are only checked for
existence, so the access log, which records file opens, missed them. The full
rebuild script from an empty `www/` then reached step 20, which reads a file
that the instrumented run had not opened. That is why the untouched files are
declared as well. With every source declared, **all 25 build steps pass from an
empty `www/`**. The last gap was 36 files another session had added to the
live site after the experiment's clone; they are declared too.

From empty, the checks match the run from the live copy except privacy. The
likely-living spouse is now withheld. The change-log pages, however, named a
private DNA tester's kit number taken from the hand-written
`data/catalogue-changelog.json`, which the live pages do not show. The page
builder now withholds any change-log line that names a withheld person or a
private tester (three lines today).

### Closing the gap (26 October 2026)

The differences come mostly from one omission: the live site is the rebuild
**plus** `tools/publish_research_release.py`, the release repairs (privacy and
DNA withholding, licensed assets, the WikiTree merge redirect pages, the
newspaper review and about 20 more), which the rebuild never ran. Of the 97
person pages the rebuild lacked, 83 are merge redirect stubs that the release
writes. The catalogue also resets `www/data/`, `www/people/`, `www/places/` and
`www/records/` on every run, removing what other publishers wrote there. The
rebuild script now runs, before `finalize`:

- the release repairs, without the release gate (the rebuild reports the
  research check itself) or the local search-index refresh;
- the Irish death index and the OPR marriage review;
- `profile_tree_links.py`, so the tree-link check no longer reports 415 pages.

The next run stopped inside the release repairs: `publish_static_sources.py`
refuses `sources/s-631ba517c2120641/index.html`, whose shell (from commit
`b14337e`, "reconcile Findmypast page 27 records") lacks the source reader block
it anchors on. The live page is identical, so the release script would stop
the same way on the live site. The page shell needs the standard reader, or
the publisher needs to learn the new shell; the guard itself stays.

Still not reproduced by any build step: 14 record-defined person pages
(`record-fmp-glasgow-*`, written by the Findmypast catalogue integration
`materialize_findmypast_glasgow_catalogue.py`, a scoped research tool, and one
superseded-reading page from `reconcile_retired_record_subjects.py`), and four
place pages that branch pages link to under place ids no current tool assigns.

### Full rebuild from an empty `www/` (26 October 2026, afternoon)

With the release repairs, the source-page layout fix and the other session's
committed research, the rebuild from an empty `www/` runs **all 29 build
steps**, and its checks compare with the live site's as follows:

| Check | Live `www/` | Rebuilt from empty |
| --- | --- | --- |
| Research publication | passes | passes |
| Tree links | 0 pages to change | 0 pages to change |
| Finding links, site experience, asset stamps | pass | pass |
| Release consistency: new items against the baseline | 0 | 0 |
| Internal links: new broken links | 0 | 4 |
| Privacy | 7 missing analytics tags | 3 atlas models with individual DNA annotations |

The privacy difference comes from step order: steps after the release repairs
rewrite the three atlas models, which then no longer match their approved
restoration. Running the DNA repair again leaves the rebuilt site with **0
privacy failures**. The rebuild script now does that as its last build step.
The four broken links were tree-group pages (`branches/family-*`) linking to
place pages the catalogue no longer makes. The catalogue resets `places/` and
writes a page only for places in its own records. Three of the places no longer
appear in any research or data file. The fourth, Govan, has only a record from
the canonical-record ingest, which reaches the records index after the
catalogue has written its place pages. Tree-group pages are rewritten from
their earlier copy, so their "Places in this group" lists kept the old links;
the one tool that recalculates them (`repair_site_experience.py`) was never part
of the build. The rebuild now runs `tools/study_place_links.py`
(`refresh_group_places`), which recalculates those lists from the people's
current records and links only place pages that exist. The live site still has
the four old place pages from earlier builds, so its next normal build would
have broken the same links.

**Result (26 October 2026, 16:46).** From an empty `www/`, all 31 build steps
pass and the rebuilt site matches or beats the live site on every check:
research publication, release consistency (the same baseline items, 0 new),
internal links (0 new broken), finding links, tree links, site experience,
asset stamps and privacy (0 failures, against the live site's 7 missing
analytics tags).

## Remaining work, in order

1. Review the files the rebuild no longer makes before a rebuilt `www/`
   replaces the live one (old catalogue detail files, the 14 Findmypast record
   pages and the superseded-reading page). Then run
   `site_declared_inputs.py --save-state` from the reviewed rebuild.
2. Replace the build state with producers. Most of it is
   `assets/v3/sources/*.json` (16,318 source documents written by the canonical
   record ingest) and `assets/research/*` (10,338 files). Each should be
   produced from the research database instead of carried forward.
3. Split each builder into a producer of one intermediate file (written outside `www/`, for example `build/site-data/`) and a renderer that only reads declared files; start with the most-read intermediates above (`data/people-index.json`, `data/catalogue-search-index.json`, `data/people.json`, `assets/research/branches.json`).
4. Make `tools/build_research_catalog.py` (7,079 lines, the producer of `data/people.json` and `map/data/records.csv`) read the research database through `genealogy.store.projection.public_case` instead of the legacy registries.
5. Retire the `repair_*` tools, which edit published pages in place, by moving their corrections into the producers. One-off scripts that edit `www/` (as on 17 October) must become builder steps or declared inputs, or their changes are lost at the next rebuild.
6. Prove the result with a build into an empty directory and a byte comparison of two builds.
