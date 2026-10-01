# Read-only integration check — 30 September 2026

**No failures found in the requested checks.**

- `www/index.html`: direct main-child order is How to use this site, `study-map`, `research-example` (Alexander); map precedes Alexander.
- `www/onetree/index.html`: role=tab controls with data-view read exactly Whole tree, Timeline, Branch cards, Y-DNA, in that order.
- Glasgow-1101 and Glasgow-3556 complete replacement drafts are present in their maintained Markdown. Public dossier `wikitree_update.draft_wikitext` equals the public page's `#wikitree-export` textarea exactly; each has one Biography and Sources heading. Public catalogue-search-index has `needs_wikitree_update: true` for both (significance55/78 with current summaries). New readable page uses Prepared WikiTree copy/export rather than the older literal Needs updated text; the maintained public update flags are set.
- Smallest sync check: `.venv/bin/python tools/sync_catalogue_research.py Glasgow-1101 Glasgow-3556 Glasgow-1136 Glasgow-428` returned checked4, stale{}, missing_public_cases[].

Read-only: no browser, website write or tar packaging. Systempython lacks bs4; project .venv successfully ran the requested check.
