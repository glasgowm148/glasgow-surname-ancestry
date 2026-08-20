# Tools

- `project_paths.py` defines canonical repository paths.
- `sync_onetree_*.py` updates map coverage from the latest One-Tree export.
- `build_family_map.py` embeds map records and tree metadata into `www/map/index.html`.
- `scrape_profile_leads.py` captures profile-only research leads.
- `sync_wikitree_profile_evidence.py` enriches the Irish pre-1700 cohort from the public WikiTree API and saves biographies, citations, locations, and immediate relationships.
- `proni_catalog_search.py` and `cdp_public_page.mjs` are focused research helpers.
- `audit_missing_wikitree_profiles.py` checks unlinked documentary people against WikiTree's live person search.
- `apply_catalogue_profile_link.py` imports a reviewed profile-link request downloaded from a catalogue person page.

Run tools from the repository root so documented relative command examples and
the local virtual environment remain consistent.
