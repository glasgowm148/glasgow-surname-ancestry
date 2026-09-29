# WikiTree live-edit helpers (CDP)

Drive the logged-in local Chrome (remote debugging on port 9333) to edit WikiTree.

- `node wt.mjs '<url>' [waitMs] [jsExpr]` — navigate (or `-` to keep page) and read state.
- `node wt_edit.mjs` — applies a JSON patch written to `/tmp/wt_patch.json`:
  `{ "u":"<numeric uid>", "text":"<full wikitext>", "summary":"<change summary>", "sugid":"summarySuggestion-bio",
     "set":{"mBirthDate":"3 Oct 1887", ...}, "check":{"mStatus_BirthDate":"certain", ...} }`.
  It discards any pending draft, clicks a summary-suggestion radio, fills the required `wpSummary` and performs a trusted
  click on `#wpSave`.
- `node wtmgr.mjs Glasgow-4005 ...` — reports whether the signed-in account manages each profile.

Set `TAB=wikitree` and `TAB=...` to select the tab. See the "Live WikiTree editing"
section of `AGENTS.md` for the full workflow and gotchas.
