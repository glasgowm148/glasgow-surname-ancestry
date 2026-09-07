---
name: wikitree-research
description: Conduct and maintain evidence-led WikiTree genealogy research, including profile investigation, relationship analysis, duplicate checks, source citations, interlinked WikiTree markup, project stickers, green evidence tables, paste-ready profile drafts, research/<WikiTree-ID>/findings.md handoffs, and the public research catalogue. Use whenever researching or discussing historical people who may have WikiTree profiles; creating, updating, comparing, or connecting profiles; recording findings; or rebuilding person pages in catalogue.html.
---

# WikiTree Research

Verify each claimed identity, relationship, date, and place against the underlying record. Distinguish documented facts, evidence-based inferences, and hypotheses.

## Preserve attached people and locations

- Never clear, detach, blank, or remove an attached person or structured location unless evidence supports a specific replacement and that replacement is applied in the same edit.
- Before every proposed or live structured-data edit, compare the existing and intended values. If a populated person or location would become empty, abort that part of the edit unless the sourced replacement person/profile or replacement location is ready to be entered immediately.
- A weak, uncertain, conflicting, broad, or apparently incorrect attachment/location is not sufficient reason to leave the field empty. Preserve it, mark it uncertain where WikiTree permits, and explain the conflict in Research Notes while investigating the evidenced replacement.
- This rule applies to live edits, WT+ fixes, paste-ready drafts, chronology corrections, and recommendations in `findings.md`. If no evidenced replacement has been established, make no destructive structured-data change.

## Identify and link every person

- Treat documentary rows as evidence about people, not as profile identities. Before creating or queueing anything, cluster compatible records into the fewest defensible people and search whether each cluster fits an existing WikiTree profile.
- Prefer adding a compatible fact to an existing profile. Create a new profile only when the evidence defines a distinct person and a completed duplicate audit finds no compatible profile; if identity is ambiguous or candidate profiles remain, keep one consolidated evidence handoff on **HOLD**. Never create one profile or draft per fact.
- In a batch duplicate audit, compare exact dates, places, named relatives, occupations and residences before counting proposed people. Consolidate compatible repeated records into one person/HOLD, and document any index-date or spelling conflict instead of creating parallel identities from it.
- Search WikiTree before reporting on each named historical person, using name variants, dates, places, relatives, the local One Tree export when relevant, and the live WikiTree API.
- Never create, queue, or prepare a WikiTree person-profile draft for a pre-1500 person. Give each distinct pre-1500 record bearer an individual WikiTree free-space page instead, and link that page from the consolidated early-bearers free-space page. If the individual page does not yet exist, prepare a free-space-page draft outside `surname-research/new-people/`; if it exists, improve and cross-link it. Pre-1500 people remain documentary subjects, not profile-creation tasks.
- A verified canonical individual free-space page is a confirmed WikiTree destination. Catalogue filters labelled “No confirmed WikiTree link” must exclude subjects linked to one even when they correctly have no person-profile ID; store and display the Space-page destination separately rather than pretending it is a person profile.
- When an existing pre-1500 WikiTree person profile is stale or cannot be edited by the requesting manager, do not treat it as the project's main research destination. Keep the attachment intact, maintain the sourced biography on the canonical individual free-space page, and link that page prominently from managed relatives and project pages so readers reach the current account first.
- If a matching profile is established, make the person's name clickable every time the person is introduced: use `[Display Name (WikiTree-ID)](https://www.wikitree.com/wiki/WikiTree-ID)` in ordinary responses and `[[WikiTree-ID|Display Name]]` in paste-ready WikiTree markup.
- If no profile is found after a duplicate check and the evidence distinguishes a person, state **No WikiTree profile found—create a new profile** and recommend or supply a sourced draft, except for pre-1500 people, who must use the free-space-page workflow above. Never leave a named person unlinked without the applicable recommendation or HOLD reason.
- If a possible profile match is not proved, link it explicitly as a possible candidate, explain the conflict or missing evidence, and do not treat it as that person.
- When several record subjects lack profiles, list each one and recommend a separate profile only where the evidence distinguishes separate people.

## Describe groups precisely

- When reviewing or rewriting a Name Study or other surname overview, audit the whole page against the project's maintained research corpus, not only the supplied draft, its predecessor, or examples raised by the user. Carry every material current conclusion into the overview at proportionate length, preserve useful visual signposting, and route record-level detail to supporting free-space pages.
- A whole-page corpus audit is not complete when it merely transfers person-level conclusions. Explain the chronology and record-survival pattern, the social and institutional setting, what each record class can and cannot prove, and why the findings change the wider historical interpretation. Connect the major sections into one coherent surname history while leaving record-level dossiers on supporting pages.
- Never imply that a record-based cluster is a WikiTree family or profile group.
- Name the exact record, date, place, reference, and people forming the cluster.
- State whether the grouping reflects co-tenancy, document order, household membership, proven kinship, or only a research hypothesis.
- In surname and family overviews, do not make strongly supported probable relatives sound like unrelated families merely because no explicit kin term survives. State the leading relationship plainly, label it probable once, summarise the concrete property, occupation and associate evidence, and reserve “separate family” language for genuinely competing or weakly connected groups.
- In an identity comparison, state the exact person-to-person hypothesis first.
  Keep FAN, military, tenancy, church, migration and textual-variant research
  explicitly subordinate as supporting network evidence. Say what the network
  evidence could help locate or test and what it does not establish; do not let
  an unresolved side question become the apparent identity hypothesis or receive
  prominence out of proportion to its genealogical value.

## Prepare WikiTree material

- Cite original images or primary records where available; identify transcriptions as such.
- Use logical, evidence-led speculation constructively when it helps explain a family or property pattern. Label the proposed relationship or reconstruction clearly once, give the concrete reasons for it, and write the surrounding prose naturally; do not smother a sensible hypothesis in repetitive disclaimers. Reserve categorical language for documentary proof.
- Save provenance at discovery time, not during profile drafting: whenever a mapped record is added or materially researched, populate `source_title`, the original external `source_url`, `source_type`, and `source_status` in `www/map/data/records.csv` before moving on. Never rely on browser history, chat, a local capture, or the public catalogue to reconstruct the URL later.
- Verify the saved URL resolves to the claimed record. Prefer an item/image URL; when the archive exposes only session-bound results, save its stable public search/catalogue URL plus the collection, sub-index, reference, date, place and access limitation in the title/status. If no external source can be recovered, mark the work **HOLD** and do not generate paste-ready profile text.
- Treat `glasgow.phenotype.dev`, relative repository paths and local `sources/` files as internal research aids only. They must never populate a public citation or `source_url` field.
- Provide paste-ready native WikiTree syntax, not Markdown, and defensible creation fields.
- Write every paste-ready replacement as a complete, polished profile—not a patch note appended to the old biography. Use the durable `Current conclusion` as the narrative basis, preserve useful sourced material from the live profile, remove obsolete or misleading text, and explain the evidence naturally.
- Never remove an existing source or citation from the captured live WikiTree biography when preparing a replacement. Integrate it naturally into the narrative, Research Notes, or Sources even when it is derivative, weak, duplicated, or supports a rejected claim. Qualify what it proves; do not delete it. Do not mention “the earlier profile,” “retained sources,” or the editing process in the biography. A replacement may improve, supplement, or supersede a citation, but every source must remain identifiable and accessible.
- Write in the voice of a human profile editor. For a corrected relationship, prefer prose such as `[[Glasgow-123|Robert Glasgow]] was previously attached as his father. However, ...` followed by the evidence and outcome. Never put editor commands or headings such as `Required profile change`, `Add`, `Remove`, `Detach`, `Replace`, `Revise`, or `Evidence-led project update` inside the copied biography.
- A replacement profile must normally contain the appropriate templates, `== Biography ==`, a prose life narrative with inline `<ref>` citations, `== Research Notes ==` for identity conflicts, uncertain relationships and rejected claims, and `== Sources ==` with `<references />`. Use named references when a source supports more than one statement. Do not dump bare URLs or an AI work queue into the biography.
- Plausible working relationships may remain attached with an explicit uncertain status. Do not present them as proved. Replace an attachment only when positive evidence establishes the specific replacement; never detach it merely because the current placement is weak or contradicted if that would leave no evidenced replacement.

## Maintain findings and catalogue person pages

- After research materially affects a person, update `research/<WikiTree-ID>/findings.md`; do not leave the substantive result only in chat, an agent note, or another file.
- Use headings consumed by the catalogue: `## Current conclusion` or `## Conclusion`; `## Source findings`; assessment headings containing `candidate`, `relationship`, `identity`, `duplicate`, `parentage`, `father`, or `cluster placement`; and action headings containing `unresolved`, `priority`, `recommended`, `suggested`, `correction`, `do not add`, or `next records`.
- Keep the handoff self-contained and source every transferable claim. Put an external record or catalogue URL first when one exists. Treat relative `sources/` links as local research artifacts, not published evidence.
- When integrating a historical-record batch into the research catalogue, list every unresolved new person in the catalogue's new-profile section and every sourced amendment to a matched existing person in the existing-profile update section. Do not treat record rows alone as catalogue integration, and do not mix the two action classes.
- Create a complete paste-ready replacement-profile draft for every substantive amendment to an existing profile, including a newly proved relationship, an evidence-supported relationship-confidence change, an identity correction, or correction of a material factual error. A newly found source that only confirms facts already represented on the profile is not a substantive amendment and must not by itself create an amendment draft or update-queue item; retain it as supporting evidence in `findings.md` and the evidence register.
- Before listing an amendment or new person as catalogue-ready, inspect the draft content rather than testing only that its file exists. Verify that it identifies the documentary person, contains meaningful paste-ready WikiTree markup and citations, records the proposed change or unresolved identity test, and is exposed in the corresponding generated catalogue page/JSON. An empty, generic, unrelated, or legacy draft does not satisfy catalogue integration.
- Never rebuild the public research catalogue unless the user explicitly asks for a catalogue rebuild. Findings, profile edits, free-space-page work and ordinary research synchronization do not imply permission to run `.venv/bin/python tools/build_family_map.py`, even at the end of a task.
- If the user says more research is coming or asks to defer rebuilding, treat any earlier rebuild authorization as withdrawn. Continue integrating source batches without rebuilding, and wait for a new explicit rebuild request after the user says the batch is complete.
- When the user explicitly requests a rebuild, batch all catalogue-affecting changes into that one run. Afterwards verify the affected `www/people/<catalogue-slug>.html` and `.json`, ensure the expected sections appear and the JSON includes `research_findings`, and run `.venv/bin/python -m unittest tests.test_research_catalog -q`.
- Preserve direct local use of generated catalogue pages. Clean-route publishing must not replace `www/catalogue.html` or other legacy `.html` entry points with redirects, or rewrite their relative links; gate every browser redirect so it never runs under `file://`. A clean-route page opened locally must use a relative site-root `<base>` rather than `<base href="/...">`. After route or catalogue build changes, verify under `file://` that `www/catalogue.html` loads its assets and data, its Glasgow Surname Project brand reaches the sibling `www/index.html` from both legacy and clean catalogue pages, and `www/ydna.html` and `www/timeline.html` reach their sibling local pages without resolving to `file:///ydna`, `file:///timeline`, or a directory listing.
- When replacing an evidence-rich public research page with a state/data-driven rebuild, do not count material as preserved merely because it remains in JSON, an archive, or a catch-all evidence page. Inventory the previous page's visible tables, qualifications, links and interactions; integrate each retained evidence unit into the relevant narrative or research-tool section so the site reads as one cohesive account. A standalone full-evidence dossier alone is not sufficient. Keep superseded rankings visibly archival, preserve an unchanged prior-page snapshot, and add tests for contextual rendered coverage as well as data parity.
- For every catalogue statistics link intended to filter people, verify the click-through from both `www/catalogue.html` and the clean `/catalogue` route: it must land at the results table, visibly restore the selected filters, and restrict results by the exact intended field. In particular, a spouse birth-surname statistic must not reuse a combined birth/current-surname match.
- Catalogue marriage-surname statistics must include Glasgow-at-birth people marrying into the named surname as well as people of that birth surname marrying a Glasgow. Derive the associated surname from the structured birth surname or WikiTree ID, group recognised spelling variants under the canonical label, deduplicate the Glasgow-side people or relationships being counted, and exclude middle-name text matches. The statistic's click-through result count must agree with the displayed total.
- In the catalogue One Tree view, show a married-in non-Glasgow spouse inline with the Glasgow-line partner rather than repeating that person as a standalone tree node. Keep the spouse's catalogue link and fold any children below the couple's displayed line so no person or descendant branch is lost.
- In catalogue or standalone One Tree views, make recorded family branch or pedigree structure the primary organisation. Present geography only as a secondary visual cue such as colour, badges, labels, or filters; never partition the main tree primarily by location. Keep large-tree rendering progressive and culling-based so branch navigation remains responsive.
- For large One Tree overviews, collapse descendants into size-scaled branch aggregates at low zoom and progressively reveal recorded generations as the user zooms. When geography must be legible at a glance, prefer branch-local location blooms or petals (area by country count, ordered by the evidenced route) over a single composition ring; let these split into smaller real-pedigree aggregates as zoom increases. Never merge unrelated pedigrees into global country clusters. Show colour transitions along revealed parent lines so migration offshoots remain traceable. Keep the branch landing view selective and readable rather than rendering every anchor and lineage card at once.
- When subdivisions of one large pedigree become navigation anchors, never present those descendant anchors as independent peer roots: keep their shared recorded ancestor structurally above every child offshoot at every level of detail. Represent multi-stage migration with compact ordered country trails on the existing aggregates and parent lines (for example Scotland → Ireland → United States), not with geography-based layout partitions or extra pseudo-ancestor nodes.
- Treat the generated `similar_people` table as a research lead, never as proof. Inspect both subjects and their sources, relatives, locations, and witnesses before proposing a merge or relationship.
- When a branch audit says the tree continues, recursively follow every attached father and mother until the first profile(s) with no attached ancestry; do not label the requested branch subject parentless merely because its own parents are unresolved. Research and report those true endpoints separately.
- When evidence confirms or rules out a possible duplicate or relationship, record the conclusion in each affected existing profile's `findings.md` and update the relevant project register.
- Remember that rebuilding changes local `www/`; it does not publish production until that directory is deployed.

## Interlink and format profile text

- When a free-space research page discusses people who have compatible live WikiTree profiles, link each profile at first substantive mention and include a compact linked profile table when three or more profiles form the page's subject network. Add a reciprocal link to the canonical free-space page in every relevant live profile managed by the requesting account, normally in Biography or Research Notes. Verify both directions on the rendered public pages. If a relevant profile is outside management scope, do not edit it; record that limitation and provide the free-space link through managed relatives or project pages instead.
- On each individual pre-1500 Glasgow-bearer free-space page, place a prominent green relationship box near the start of the biography linking to the strongest defensible father or earlier-generation candidate and, where useful, the leading son or next-generation candidate. Label each link as documented, probable, or possible, give the short evidential reason, and continue the navigation chain across the linked individual pages until no defensible candidate exists. Do not manufacture a parent merely because another bearer is chronologically earlier.
- Convert every reference to another Glasgow with a confirmed WikiTree profile into `[[Glasgow-123|Display Name]]`, including mentions in prose, family lists, research notes and tables. Never leave a known Glasgow profile as unlinked plain text or expose its URL in paste-ready markup.
- Search for a WikiTree ID before leaving any named Glasgow unlinked. If no compatible profile exists, say so explicitly in the research notes; never invent an ID or silently link an uncertain candidate.
- Use native headings such as `== Biography ==`, `=== Census ===`, `== Research Notes ==`, `== Sources ==` and `<references />`. Preserve valid markup already on the profile and avoid duplicate templates.
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
## Source provenance and durable corrections

- On live WikiTree profiles, cite the underlying primary record directly. Never cite `glasgow.phenotype.dev`, a generated catalogue page, a local findings file, or another project-owned research summary as evidence. The catalogue may be used to locate provenance only.
- Prefer an original record image or an official archive record page. If no public image exists, cite the official archival catalogue or index and state that limitation. Use a named transcription only when the underlying image is unavailable, and identify it as a transcription.
- For WT+ broken-link suggestions involving Irish census or archive URLs, never resolve the warning by deleting the citation or merely removing its hyperlink. Identify the collection, year, place, household or person, archive reference and any image number from the live citation; then replace the dead URL with the current official record/image URL, a stable official catalogue or search URL, or a verified archival snapshot in that order. Preserve enough record metadata for a reader to recover the item independently. If no equivalent can be verified, leave the suggestion active and record the unresolved lookup rather than weakening the profile.
- Whenever a useful RootsIreland hit is found but cannot be inspected without a subscription, immediately add it to `research/rootsireland-subscription-backlog.md`. Record the linked WikiTree profile(s), search date, county/database and record type, exact search fields, hit count, stable source-inventory or search-portal URL, why the result matters, and the next inspection action. Include an exact-name zero result only when it is needed to interpret a broader surname result. Treat counts as leads, not record evidence. Do not purchase access without explicit user authorization. During a later subscribed session, work every open backlog item as one batch; preserve the audit entry, mark its outcome, and transfer any inspected record and provenance into each affected profile's `findings.md` and live WikiTree research notes where material.
- When the user explicitly asks for a **concrete record** proving a relationship and asks the research to persist, locating an archive reference, restricted index, promising record group, or pending lookup is not completion. Continue until the actual record or an image/transcription of its relevant entry has been inspected and assessed; keep the task active rather than presenting an unresolved target as the requested result.
- When the user requires research to **uncover new evidence before upgrading a relationship**, an already-known citation, an unset status, or a previously obvious but unapplied conclusion does not satisfy the threshold. Locate and inspect a materially new record or independent witness that was absent from the maintained findings and live biography, show how it resolves the specific record-to-profile identity or kinship gap, and only then change the relationship to confident. Do not relabel existing evidence as a new discovery merely to complete the task.
- When the user authorizes live integration and directs research to continue afterwards, treat that as standing authorization for the same task: publish each subsequent genuinely new, profile-relevant finding on every affected managed profile after normal source and manager checks, then continue researching. Do not stop after each research batch merely to request another approval; pause only for a materially different edit, missing authority, destructive change, paid access beyond the approved amount, or another genuine blocker.
- When the user explicitly corrects a repeatable WikiTree research, citation, profile-editing, or catalogue workflow, treat that correction as skill feedback. During the same task, add a narrowly scoped durable instruction to this project-owned skill unless the user says the correction is one-off or the instruction conflicts with higher-priority rules.
- For catalogue records split from a grouped documentary person, assign the exact source title in the parent entry's `record_profiles` map. A top-level link keyed by the generated split-page slug is ignored by the builder and does not close the unlinked entry.

## Glasgow surname boundary

For Glasgow surname research, treat Glasford, Glassford, Glasfurd, and Glasfuird as a distinct family unless a primary record explicitly proves a bridge. Do not search, merge, or cite those names as automatic spelling variants of Glasgow.

For Findmypast surname research, search the surname field alone unless the user
explicitly requests a place restriction. Preserve the exact surname-only query
URL and inspect the displayed event, birth and death fields before calling a
result pre-1600; Findmypast's broad date filter can return later records and
generic or unnamed hits. Keep those raw hits in the export, but map or create
people only after the underlying transcript and duplicate audit support them.
Never treat a displayed “Last name Glasgow” value as surname proof when the
transcript or title shows that Glasgow is an office, place, see, or other
descriptor. Inspect the full transcript/title and distinguish an actual
surname from “of Glasgow,” “Archdeacon/Bishop/Deacon of Glasgow,” and similar
phrasing before adding the result to the surname catalogue.
A Findmypast result scrape is not complete until every pagination page in
every date window has been enumerated, the site's displayed result total has
been recorded, and saved rows reconcile to that total after explicitly
reported record-ID deduplication. Check that adjacent date windows cover the
entire requested period without gaps. A final-page sample or partial window
must be labelled **INCOMPLETE** and must never be reported as “all records.”
If a transcript request redirects to `steady-sherlock?limit=dailyLimit`, record
it as a temporary daily fair-use block with `block_reason=daily_limit`; do not
count it as a record-specific subscription lock or a captured transcript. Stop
opening further record IDs in that limited session, preserve the frozen ID
order and first affected index, and retry from that index only after the
allowance resets. Keep the audit **INCOMPLETE** until those retries succeed or
produce a separately evidenced record-specific restriction.

## Identity-defining estimated dates

When a profile represents an adult or householder in a dated record, retain a useful approximate birth estimate derived from that record and mark it estimated. Do not replace it with a later broad `before` date that obscures the profile's intended identity.

## Resolve chronology warnings

Never use WikiTree's `Save Anyway` control merely to suppress a chronology warning. When a Full Save exposes a warning, stop and inspect the exact dates, places and relationships producing it; do not click `Save Anyway` during automated profile work. Correct the weakest unsupported claim only when the correction is positively evidenced, or hold the profile with the warning documented. Reverify the manager before any later save attempt. Never clear an attached person or location without applying its evidenced replacement in the same edit. If an uncertain relationship is deliberately retained, any structured boundary inferred from it must be internally coherent and explicitly described as conditional; keep the direct record boundary separate in the biography and findings.

Before changing a WikiTree relationship status, inspect the visible labels and the currently checked control. Select the control explicitly labelled `uncertain`; never infer status from radio-button order or treat `non-biological` as a synonym. After saving, read back the rendered relationship or reopen the edit form and verify that every changed parent status is `uncertain` rather than `non-biological`, `confident`, or DNA-confirmed.

## Resolve WT+ missing-location suggestions

- For WT+ `No location, has Marriage location` suggestions, copy the profile's marriage location into the missing target location and mark it uncertain.
- For WT+ `No location, has Relatives location` suggestions, use the relevant relative's location for the target profile and mark it uncertain.
- For general WT+ `No location` suggestions, use the most specific location already supported by the managed profile's biography and mark it uncertain (for example, use Belfast when the biography places the person in Belfast). A birth record is not required: use the location of the profile subject's own earliest documented life event, appearance, or residence. A spouse's or other close relative's documented location in the profile's family context may also supply an uncertain location when no subject location is available. Skip only when the biography and family context contain no usable place; do not derive a place only from a source-collection title.
- Apply these rules only to profiles explicitly managed by the requesting WikiTree account; do not add a location that is absent from both the biography and the suggested marriage/relative context.

## Preserve live WikiTree edits during browser work

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
