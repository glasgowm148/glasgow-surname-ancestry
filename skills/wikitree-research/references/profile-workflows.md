# WikiTree Research — Profile Workflows

This reference preserves the original project skill sections for tasks in this area. Read it when the request matches the section headings below.

## Prepare WikiTree material

- When a live profile update adds a record that names a spouse or other relative, find or create that person's profile in the same task. Use LNAB `Unknown` when the maiden name is unrecorded, and state any relationship the record implies but does not state in that profile's Research Notes. Don't leave a named relative as plain text in the biography.
- Link every person mentioned in a biography who has a WikiTree profile, not only Glasgows: spouses, children, siblings and informants. Before linking a candidate identity, check it against known facts; for example, a man who emigrated or died elsewhere cannot be a later local occupier.
- When a record gives an exact date or place, set that structured field's status to `certain` in the same edit. Check every date and place field the record supports, not only the one you were correcting.

- Cite original images or primary records where available; identify transcriptions as such.
- Use logical, evidence-led speculation constructively when it helps explain a family or property pattern. Label the proposed relationship or reconstruction clearly once, give the concrete reasons for it, and write the surrounding prose naturally; do not smother a sensible hypothesis in repetitive disclaimers. Reserve categorical language for documentary proof.
- Assess the actual proposed multi-generation pedigree against the wider catalogue before ranking parents. Separate immediate parentage, collateral kinship, duplicate identity and the upstream joining generation; evidence against one edge must not reject the others. Do not replace a collateral hypothesis with an invented common-father scenario. Compare record-supported branches, migration, age ranges and DNA together, explaining which connections the combined evidence favours and what would distinguish the remaining models.
- Save provenance at discovery time, not during profile drafting: whenever a mapped record is added or materially researched, populate `source_title`, the original external `source_url`, `source_type`, and `source_status` in `www/map/data/records.csv` before moving on. Never rely on browser history, chat, a local capture, or the public catalogue to reconstruct the URL later.
- Verify the saved URL resolves to the claimed record. Prefer an item/image URL; when the archive exposes only session-bound results, save its stable public search/catalogue URL plus the collection, sub-index, reference, date, place and access limitation in the title/status. If no external source can be recovered, mark the work **HOLD** and do not generate paste-ready profile text.
- Treat `glasgow.phenotype.dev`, relative repository paths and local `sources/` files as internal research aids only. They must never populate a public citation or `source_url` field.
- Provide paste-ready native WikiTree syntax, not Markdown, and defensible creation fields.
- Write every paste-ready replacement as a complete, polished profile—not a patch note appended to the old biography. Use the durable `Current conclusion` as the narrative basis, preserve useful sourced material from the live profile, remove obsolete or misleading text, and explain the evidence naturally.
- Never remove an existing source or citation from the captured live WikiTree biography when preparing a replacement. Integrate it naturally into the narrative, Research Notes, or Sources even when it is derivative, weak, or supports a rejected claim. Qualify what it proves. Exact duplicate occurrences of the same citation may be consolidated while keeping one complete, accessible citation and every distinct record. Do not mention “the earlier profile,” “retained sources,” or the editing process in the biography. A replacement may improve, supplement, or supersede a citation, but every distinct source must remain identifiable and accessible.
- Never overwrite live biography research with a shorter, condensed or reorganised replacement. Before saving a full replacement, compare it with the live biography and confirm every existing sourced statement is preserved; a queue flag such as `preserve_captured_detail: false` or a "concise controlling draft" is not licence to drop researched narrative. If the replacement would reduce the live text, do not save it: apply the new material additively (append or integrate the new section, research note or correction) while leaving the existing account intact, or reconcile the two first. When in doubt, prefer an additive edit and keep the full prior text.
- When a biography corrects a vital fact, apply the same correction to WikiTree's structured fields in the same task — birth/death date and location values plus their certainty statuses, names, and parent/spouse relationships. Never leave a corrected date or place only in the prose while the data fields still hold the old value.
- Never paste editorial or process notes into a profile: no HTML comments such as `<!-- REVIEWED FULL REPLACEMENT ... -->`, no "the profile previously used X", "the structured date should therefore be", "the existing source is retained as a finding aid", or explanations of a baptism-vs-birth or index-vs-field edit. A profile records the person and the evidence, not the edit. Research Notes are only for genuine unresolved research, identity conflicts and source limitations; keep a replaced citation in the text or Sources without narrating that it was retained.
- Write in the voice of a human profile editor. For a corrected relationship, prefer prose such as `[[Glasgow-123|Robert Glasgow]] was previously attached as his father. However, ...` followed by the evidence and outcome. Never put editor commands or headings such as `Required profile change`, `Add`, `Remove`, `Detach`, `Replace`, `Revise`, or `Evidence-led project update` inside the copied biography.
- A replacement profile must normally contain the appropriate templates, `== Biography ==`, a prose life narrative with inline `<ref>` citations, `== Research Notes ==` for identity conflicts, uncertain relationships and rejected claims, and `== Sources ==` with `<references />`. Use named references when a source supports more than one statement. Do not dump bare URLs or an AI work queue into the biography.
- Plausible working relationships may remain attached with an explicit uncertain status. Do not present them as proved. Replace an attachment only when positive evidence establishes the specific replacement; never detach it merely because the current placement is weak or contradicted if that would leave no evidenced replacement.


## Interlink and format profile text

- When a free-space research page discusses people who have compatible live WikiTree profiles, link each profile at first substantive mention and include a compact linked profile table when three or more profiles form the page's subject network. Add a reciprocal link to the canonical free-space page in every relevant live profile managed by the requesting account, normally in Biography or Research Notes. Verify both directions on the rendered public pages. If a relevant profile is outside management scope, do not edit it; record that limitation and provide the free-space link through managed relatives or project pages instead.
- On each individual pre-1500 Glasgow-bearer free-space page, place a prominent green relationship box near the start of the biography linking to the strongest defensible father or earlier-generation candidate and, where useful, the leading son or next-generation candidate. Label each link as documented, probable, or possible, give the short evidential reason, and continue the navigation chain across the linked individual pages until no defensible candidate exists. Do not manufacture a parent merely because another bearer is chronologically earlier.
- Convert every reference to another Glasgow with a confirmed WikiTree profile into `[[Glasgow-123|Display Name]]`, including mentions in prose, family lists, research notes and tables. Never leave a known Glasgow profile as unlinked plain text or expose its URL in paste-ready markup.
- Search for a WikiTree ID before leaving any named Glasgow unlinked. If no compatible profile exists, say so explicitly in the research notes; never invent an ID or silently link an uncertain candidate.
- Use native headings such as `== Biography ==`, `=== Census ===`, `== Research Notes ==`, `== Sources ==` and `<references />`. Preserve valid markup already on the profile and avoid duplicate templates.
- After creating a profile, check its live Gender field and biography for repeated citation definitions. When only a strongly sex-associated given name supports the Gender value, mark WikiTree's uncertain/guess status and explain the inference in the change summary. Consolidate exact duplicate named `<ref>` definitions while retaining all distinct sources, then verify the rendered citation list.
- Add `[[Category:Glasgow Name Study]]` above the Biography heading in Glasgow profile drafts and substantive Glasgow-profile updates unless it is already present. Do not use the deprecated `{{One Name Study|name=Glasgow}}` sticker.
- Add evidence-supported location and life-course stickers: `{{Ireland Native}}` for a person proved born in Ireland, `{{Scotland Sticker}}` for a person proved born in Scotland, and `{{Migrating Ancestor ...}}` only when records support movement between countries. Populate the migration template with the documented origin and destination; use the project's existing flag parameters where verified.
- Add `{{Estimated Date}}` when key dates are estimates. Add specialist stickers such as `{{Notables Sticker}}` only when the profile meets that sticker's criteria. Do not infer birthplace, migration or notability merely to obtain a label.
- Use a green WikiTree table when three or more comparable household members, children, land entries, events or hypotheses are clearer in rows and columns. Use this pattern and interlink every known Glasgow profile within it:

```text
{| class="wikitable sortable" style="padding: 5px; width:100%;"
|+ '''Table title'''
|-
! style="background-color:#E1F0B4;" | Name
! style="background-color:#E1F0B4;" | Relationship
! style="background-color:#E1F0B4;" | Evidence
|-
| [[Glasgow-123|Alexander Glasgow]] || Head || Census or record detail
|}
```

- Prefer concise prose or a list when a table would not improve comparison.


## Create new-person drafts immediately

- When creating or completing a managed historical profile, do not leave a
  birth or death location blank if the evidence supplies a usable location for
  the person's own marriage, child's birth or baptism, spouse, or immediate
  family context. Use the most specific supported location and mark the
  inferred birth/death location uncertain. Explain which event or relative
  supplied the location; do not present it as the actual place of birth or
  death. Leave a location blank only when neither the biography nor the
  documented immediate-family context supplies any usable place.
- Keep creation drafts and catalogue search rows consistent. When a draft
  supplies a usable uncertain birth location from a documented non-migration
  life event, carry it into generated person data, the search index, and the
  visible birth-location column. Continue to exclude migration destinations
  and source-grouping places that are not evidence of the person's location.

- The project's `surname-research/new-people/` directory is for **Glasgow-surname people only**. Do not create drafts there for landlords, witnesses, spouses, co-tenants, or other associates with different surnames unless the user explicitly requests an exception.
- Do not place pre-1500 people in `surname-research/new-people/`. Maintain one individual free-space page per distinct bearer and cross-link it from the consolidated early-bearers page instead.
- When the evidence distinguishes a Glasgow-surname person and no compatible WikiTree profile is found, create a complete draft during the same turn at `surname-research/new-people/<year>_<country>_<precise-location>_<name>.md`; do not merely recommend that the user create one. Use underscores between every component, the year of the defining record or event, the documented country, the smallest documented location, and the record subject's name.
- Include minimum creation fields, a paste-ready sourced biography, a duplicate audit, relationship cautions, and the evidence needed to resolve any uncertainty.
- If an existing-profile candidate or record ambiguity prevents safe creation of a Glasgow profile, still save an evidence draft there, label it **HOLD** at the top, link every candidate, and state the test needed before creating or merging.
- Record non-Glasgow associates inside the relevant `research/<Glasgow-ID>/` folder, linking their WikiTree profiles when found; never leave their drafts in `/new-people`.
- Add each new draft to `surname-research/to-update.md` and list the files created when reporting completion.


## Retire drafts after profile creation or identification

- As soon as a draft person receives or is matched to a confirmed WikiTree ID, move the draft out of `surname-research/new-people/` and into `research/<WikiTree-ID>/<year>_<country>_<precise-location>_<name>.md`.
- Update every inbound repository link and move the person from the creation queue to the resolved-profile section of `surname-research/to-update.md` in the same turn.
- Never keep ID-only placeholder files or completed profile drafts in `new-people`; that directory is only the unresolved Glasgow creation queue.

## Preserve live WikiTree edits during browser work

- WikiTree biography text uses WikiTree markup, not Markdown: use `'''bold'''`, `''italic''`, `[[WikiTree-ID|Display Name]]`, `[https://example.com display text]` and `<ref>...</ref>`. Before saving a profile, inspect inserted text for Markdown `**bold**` or other syntax that WikiTree will not render.
- G2G forum posts use a separate rich-text editor. Do not supply profile/free-space WikiTree markup as paste-ready G2G text. Use plain text with literal bullets and full URLs, or apply headings and labelled links through the G2G editor toolbar; check the rendered post after submission.

- When the user asks to apply or “do all” items in a profile-evidence queue, do not
  treat triage, a HOLD decision, or a no-change review as a completed profile edit.
  Compare every managed live biography and its citations line by line with the
  underlying evidence, publish every defensible missing item, and report the exact
  numbers of person profiles actually saved, already complete, held, and outside
  management scope before calling the batch complete. Keyword overlap, recent
  modification dates, and aggregate coverage scores are not sufficient proof that
  an item is already present.
- For every live WikiTree person-profile edit, first verify that the requesting user's WikiTree account appears in the profile's manager list. Do not edit a person profile merely because it is connected to, cited by, or suggested from a managed profile. Free-space-page ownership and collaboration are a separate check; when edit authority is unclear, do not save.
- Before creating, moving, copying, or saving a WikiTree free-space project page, search the live site and the local free-space index for the intended title, aliases, redirects, and pages with equivalent content. Reuse the established canonical page. Never create a replacement page to correct a title or consolidate content; use a controlled move or an explicit redirect only after confirming the target does not already exist, and verify the old URL afterwards.
- Do not bulk-rewrite, restyle, or standardize existing haplogroup/SNP free-space pages as part of a wider Name Study audit. Preserve their established visual design and substantive structure. Limit changes to explicitly requested, evidence-specific corrections, and capture the current live source before editing so the exact prior version can be restored if needed.
- During automated WikiTree browser work for this project, leave at least 30 seconds between successful or attempted Full Save clicks. A failed or blocked submission still starts a new interval. Publish one page at a time and complete its acknowledgement and public readback before preparing the next save.
- Write concise, natural change explanations describing what a human editor changed. Avoid process labels such as “manager audit”, “architecture review”, or repetitive bot-like wording.
- Write free-space pages as enduring research pages, not edit reports: do not mention an earlier version, replacement narrative, prior cleanup, consolidation process, or what the page “used to” claim. Preserve useful speculation when it is clearly labelled as a hypothesis or research lead; distinguish it from documented fact without deleting it merely because it is unproved.
- When a WT+ cleanup request prioritizes low-count categories, finish only those low-count categories before moving to larger suggestion groups; do not continue a high-count group after the user redirects the work to low-count categories.
- For WT+ suggestion-cleanup work, edit only profiles whose manager list explicitly includes the requesting user's WikiTree account. A suggestion appearing because a managed relative is involved does not authorize editing the related profile; leave it active and report the access/scope blocker instead.
- Keep every WikiTree edit tab open until its save navigation has completed and the resulting live profile or edit form confirms the submitted relationship, status, or biography change.
- Treat a save click as only the start of submission, never as proof of completion. Wait for the post-save navigation, verify the live profile contains the intended change, and confirm the edit form is no longer dirty before navigating, reusing, or closing the tab. If WikiTree presents an unsaved-changes/before-unload dialog, cancel the navigation and return to the form; do not accept the exit or assume the save succeeded.
- On WikiTree free-space pages, a successful Full Save may change the URL to `/wiki/...` while leaving the editing form open. Require the visible `Changes Saved. Thank you.` acknowledgement and no JavaScript dialog, then explicitly open the canonical public view and verify the rendered change with no `#wpSave` edit control. A `/wiki/...` URL alone is never save verification.
- Never close, release, or finalize a WikiTree tab immediately after clicking save. Finish the complete edit batch and catalogue synchronization first; only then perform the browser's required final tab cleanup.
- If browser control is interrupted after submission, recover or reclaim the existing tab rather than opening a replacement or assuming the save failed. Inspect the current page before taking another action so an in-flight or completed change is not overwritten.
- Keep browser-backed WT+ batches bounded: reuse one edit/status tab sequentially where practical, and do not enumerate or proliferate tabs merely to recover agent-side bindings. A browser-control timeout or reset is not evidence that the Chrome plugin is faulty when its diagnostics pass; reconnect with small, separately verified operations before attributing the failure externally.
- A successful `browser.user.openTabs()` call proves that the Chrome session is reachable. If `claimTab()` or managed-tab creation then times out, describe that narrowly as a control-path timeout; do not blame Chrome, declare the extension broken, or recommend reinstalling it from that timeout alone. When live editing remains authorized and the Computer Use skill is available, preserve the existing edit tab and switch to direct UI control after reading that skill.
- When Chrome is running and the extension and native-host diagnostics all pass, a browser-client `Browser is not available` result is not evidence that installation is damaged. Never recommend reinstalling the Browser plugin from that result. Retry only small supported connection operations; if the binding remains unavailable, describe it as an agent-side session/binding failure and use the already-authorized Computer Use fallback when available.
- If Chrome is absent from browser discovery even though those diagnostics pass, keep the existing browser runtime, wait briefly, and retry the exact Chrome selector once instead of resetting the runtime. When that bounded retry restores Chrome, read its browser documentation, inspect the existing tabs, and continue with the stale-tab recovery below when needed.
- If the prescribed new-window retry also fails while those diagnostics still pass, do not ask the user to reinstall the plugin. Continue with bounded agent-side binding recovery or the authorized fallback, and report the internal control failure accurately if neither path attaches.
- After a browser-control reset, recover a tab returned by `browser.user.openTabs()` with `browser.user.claimTab(tabInfo)`; do not pass that user-tab ID to `browser.tabs.get()`, which is a different control path and may hang. Claim one relevant WT+ tab and continue sequentially from it.
- If `browser.user.openTabs()` succeeds but claiming the relevant Findmypast tab reports that it is already held by another automation session while `browser.tabs.list()` is empty, preserve the exact Findmypast URL and open it in a fresh managed tab with `browser.tabs.new()`. Navigate that tab to the preserved URL, wait for `DOMContentLoaded` and about three additional seconds, then verify its title, URL, and `domSnapshot`; successful checks restore the existing signed-in DOM-controlled session. Do not recommend reinstalling or reconnecting the browser plugin for this stale-tab condition.


