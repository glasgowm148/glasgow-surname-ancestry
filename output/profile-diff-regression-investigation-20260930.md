# Profile diff regression — 2026-09-30

## Finding

The public person pages are now rendered by `tools/repair_person_hierarchy.py`.
`_replace_main()` replaces the previous `<main>` wholesale (lines 1642–1648),
so the old `build_research_catalog._profile_update_html()` panel is discarded.
The replacement `_archive_html()` only reads `dossier["wikitree_update"]` and
renders its `draft_wikitext` as **Prepared WikiTree copy/export** (current code
around lines 1363–1364). It does not render `remote_wikitext`, the capture date
and revision, or the `ndiff` additions/removals. Thus even still-pending updates
such as Glasgow-1101 and Glasgow-3556 retain a draft but lose the current
capture and diff; the affected pages have no `#wikitree-update`,
`.profile-update-diff`, or `.profile-evidence` elements.

The loader has a second, independent regression for reopened work. In
`tools/build_research_catalog.py:4574–4587`, every ID in
`completed_live_profiles` is skipped unless it also appears in the current
OPEN register. `reopened_completed_profiles` is never consulted. On the current
queue, Glasgow-3896 and Glasgow-987 are both completed and reopened, have
captures and complete drafts, but `_load_profile_updates()` returns neither;
their pages consequently have no draft or diff. Glasgow-4010 is completed but
not reopened, so its absence is expected under the current queue semantics
unless the project intends to reopen it too.

Current counts from `data/wikitree/profile-update-queue.json` and the private
capture store: 92 queue entries; 91 captured; 85 with draft paths; 84 marked
completed; 5 both completed and reopened. The five reopened queue entries are
Glasgow-3896, Glasgow-987, Glasgow-3902, Glasgow-2304 and Glasgow-2769. The
other reopened IDs (Glasgow-4070 and Glasgow-951) are not queue entries and are
already still pending. Glasgow-4010 is captured and has a draft path but is a
completed-only stale queue entry.

## Minimal durable fix

1. Make `_load_profile_updates()` treat an entry in
   `reopened_completed_profiles` as active again (and preserve the existing
   completed handling for IDs that were not reopened). This restores the
   current capture, complete replacement draft and update metadata for the five
   reopened profiles.
2. Have the hierarchy renderer consume the same private update object used by
   `_profile_update_html()` and render the capture metadata, proposed complete
   draft, and line diff in its archive/update area. Do not reconstruct a diff
   from the public dossier JSON: it intentionally omits raw biography text.
   A small cached call to `_load_profile_updates(_load_wikitree_evidence())`
   during rendering is sufficient; keep raw biography text out of public JSON.
   Preserve the existing `public_privacy` projection and the page's current
   “raw narrative is private” wording.
3. Extend `sync_catalogue_research.discrepancies()` for the new layout to
   check the visible update panel/draft/diff and capture metadata. It currently
   returns after only comparing dossier/search metadata (`lines 66–79`), so
   `--write` cannot detect this exact presentation regression.

## Targeted verification/sync commands

After the loader/renderer change, run the narrow queue sync and renderer pass:

```sh
.venv/bin/python tools/sync_catalogue_research.py --write \
  Glasgow-3896 Glasgow-987 Glasgow-3902 Glasgow-2304 Glasgow-2769
.venv/bin/python tools/repair_person_hierarchy.py \
  Glasgow-3896 Glasgow-987 Glasgow-3902 Glasgow-2304 Glasgow-2769
.venv/bin/python -m unittest tests.test_research_catalog -q
```

Then verify `www/people/glasgow-{3896,987,3902,2304,2769}.html` contains the
captured revision text, `#wikitree-update`, a complete replacement textarea and
`.profile-update-diff`. The same sync can include Glasgow-4010 only if its
maintained queue status is intentionally reopened; otherwise leave its
completed-only row suppressed.

