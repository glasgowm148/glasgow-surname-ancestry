# Free-space second edition

`tools/build_free_space_site.py` publishes all 85 unique project pages: 71 watchlist subjects and 14 verified medieval bearer studies. The duplicated Scottish study is consolidated into one reading page with its additional saved variant retained. Two saved sources were blank and are represented honestly, with related full studies. Original citations, headings, tables and public historical material remain readable locally; specific personal match/private passages are omitted.

Maintained public-safe text lives in `research/free-space-pages/edition/`, with category, priority, source hashes and mappings in `edition.json`. The first build projects the maintained originals. Subsequent local edits survive source refreshes and repeated builds. Edit local text or original maintained sources, then rebuild. Principal studies come first; readers can filter by category/search and sort alphabetically. Global site search opens local editions.

The opening view is a collection-led library: a featured name-study overview, four quick reading routes and six subject collections. Each collection has its principal study, existing conclusion or public excerpt, two related studies and a route to the complete topic list. Existing conclusion qualifications remain visible. The medieval collection leads; Scottish records, Irish branches, family questions, DNA and project guides follow. Original titles remain in the full list; the long medieval overview has a separate compact preview label.

Search opens the complete study list, with 12 results per page. Search, topic, sort, page and list view are restored from the URL; prior search links still work. Collections and study-list controls replace the repeated topic sidebar and dropdowns in the opening view. All 85 entries and collection links remain readable without JavaScript; printing includes every matching study across result pages. Edition notes remain accessible below the library and open for direct links. Study bodies, citations, source comparisons and complete local drafts are retained unchanged.

## WikiTree reconciliation

The API is read-only: [WikiTree getProfile documentation](https://github.com/wikitree/wikitree-api/blob/main/getProfile.md). The tool checks public metadata and requests public edit-source text. No credentials or live writes are used.

```sh
.venv/bin/python tools/sync_free_space_edition.py --pull --limit 5
.venv/bin/python tools/sync_free_space_edition.py --pull --page 'Space:Glasgow DNA'
.venv/bin/python tools/sync_free_space_edition.py --import-remote 'Space:Glasgow DNA' /path/to/current-source.wiki
.venv/bin/python tools/sync_free_space_edition.py --accept-remote 'Space:Glasgow DNA'
.venv/bin/python tools/sync_free_space_edition.py --prepare
.venv/bin/python tools/build_free_space_site.py
```

`sync-state.json` records retrieved public text, metadata timestamps, checked dates, errors and comparison status. It is not published wholesale. Reading pages expose only safe text/status and a diff after a successful source retrieval. The first different comparison requires review; later comparisons distinguish a changed remote version, local version or both. Pulls never overwrite local corrections. Explicit remote acceptance backs up the local text under `.cache/free-space-reconciliation/` before replacement. Outgoing replacements and diffs are saved under `research/free-space-pages/outgoing/`; each reading page also exposes its complete safe local WikiTree draft. Saving on WikiTree is a separate authorized action.

On 30 September 2026, the API returned current metadata for the first three principal studies, but public raw-source requests returned HTTP 202 and empty content. These failures are recorded; no current WikiTree body was fabricated or imported. The local edition is complete from maintained inputs but is not claimed to match every live WikiTree revision. Import a current source obtained through the normal signed-in editor or retry when public source access succeeds.
