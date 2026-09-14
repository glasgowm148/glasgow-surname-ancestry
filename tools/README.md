# Tools

- `project_paths.py` defines canonical repository paths.
- `sync_onetree_*.py` updates map coverage from the latest One-Tree export.
- `build_family_map.py` embeds map records and tree metadata into `www/map/index.html`.
- `scrape_profile_leads.py` captures profile-only research leads.
- `migrate_research_bundle.py` converts one explicitly named legacy research directory to a private toolkit bundle offline; it does not scan cases or rebuild the catalogue.
- `build_free_space_site.py` builds the metadata-only public directory of live WikiTree free-space research pages.
- `repair_unified_site.py` restores migration parity and project routes after applying the unified-site presentation layer; it does not rebuild the research catalogue.
- `sync_wikitree_profile_evidence.py` enriches the Irish pre-1700 cohort from the public WikiTree API and saves biographies, citations, locations, and immediate relationships.
- `proni_catalog_search.py` and `cdp_public_page.mjs` are focused research helpers.
- `audit_missing_wikitree_profiles.py` checks unlinked documentary people against WikiTree's live person search.
- `apply_catalogue_profile_link.py` imports a reviewed profile-link request downloaded from a catalogue person page.
- `sync_catalogue_research.py` checks maintained findings against visible person sections, complete drafts and update-filter metadata; `--write` refreshes existing dossiers without a full site rebuild. Optional profile IDs restrict the work.
- `add_research_case_dossiers.py` adds reviewed historical cases from `data/wikitree/research-catalogue-cases.json` to person pages and search/context indexes. The manifest explicitly distinguishes included subjects, canonical destinations, documentary identities and withheld/internal cases.

Run tools from the repository root so documented relative command examples and
the local virtual environment remain consistent.
