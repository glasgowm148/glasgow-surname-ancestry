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
   (the check is a deliberate review stop), so it is left for the owner. Until
   `finalize` runs, a rebuilt site lists 5,004 records instead of the live
   5,567.

## Remaining work, in order

1. Rerun the experiment to the end and compare the rebuilt `www/` with the
   live one file by file. The record identity for multi-record pages is now
   decided (26 October): on a page URL, an entry is told apart by the people it
   names (`ingest_canonical_records.entry_key`), so the Rasharkin baptisms are
   separate records. Two existing rows for the same entry still stop for
   review. A clone needs a few GB of free disk.
2. Give the untracked `www/` sources declared homes, as was done for the three
   map layers in `data/site/declared-inputs.json`. The first two are not plain
   inputs. `map/data/records.csv` is read and rewritten in place by five sync
   tools (`sync_onetree_*`, `sync_recent_*`), so its home must move with
   `project_paths.MAP_RECORDS` and be installed after those tools run.
   `about/index.html` is both the template other builders read and an output
   of `tools.about_pages`, so the template needs separating from the page.
3. Split each builder into a producer of one intermediate file (written outside `www/`, for example `build/site-data/`) and a renderer that only reads declared files; start with the most-read intermediates above (`data/people-index.json`, `data/catalogue-search-index.json`, `data/people.json`, `assets/research/branches.json`).
4. Make `tools/build_research_catalog.py` (7,079 lines, the producer of `data/people.json` and `map/data/records.csv`) read the research database through `genealogy.store.projection.public_case` instead of the legacy registries.
5. Retire the `repair_*` tools, which edit published pages in place, by moving their corrections into the producers. One-off scripts that edit `www/` (as on 17 October) must become builder steps or declared inputs, or their changes are lost at the next rebuild.
6. Prove the result with a build into an empty directory and a byte comparison of two builds.
