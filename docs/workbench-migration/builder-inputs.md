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

## Remaining work, in order

1. Split each builder into a producer of one intermediate file (written outside `www/`, for example `build/site-data/`) and a renderer that only reads declared files; start with the most-read intermediates above (`data/people-index.json`, `data/catalogue-search-index.json`, `data/people.json`, `assets/research/branches.json`).
2. Make `tools/build_research_catalog.py` (7,054 lines, the producer of `data/people.json` and `map/data/records.csv`) read the research database through `genealogy.store.projection.public_case` instead of the legacy registries.
3. Retire the `repair_*` tools, which edit published pages in place, by moving their corrections into the producers.
4. Prove the result with a build into an empty directory and a byte comparison of two builds; this needs about 3 GB of free disk for a second site tree.
