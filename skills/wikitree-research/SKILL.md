---
name: wikitree-research
description: Conduct and maintain evidence-led WikiTree genealogy research, including profile investigation, relationship analysis, duplicate checks, source citations, interlinked WikiTree markup, project stickers, green evidence tables, paste-ready profile drafts, research/<WikiTree-ID>/findings.md handoffs, and the public research catalogue. Use whenever researching or discussing historical people who may have WikiTree profiles; creating, updating, comparing, or connecting profiles; recording findings; or rebuilding person pages in catalogue.html.
---

# WikiTree Research

Verify each claimed identity, relationship, date, and place against the underlying record. Distinguish documented facts, evidence-based inferences, and hypotheses.

## Identify and link every person

- Search WikiTree before reporting on each named historical person, using name variants, dates, places, relatives, the local One Tree export when relevant, and the live WikiTree API.
- If a matching profile is established, make the person's name clickable every time the person is introduced: use `[Display Name (WikiTree-ID)](https://www.wikitree.com/wiki/WikiTree-ID)` in ordinary responses and `[[WikiTree-ID|Display Name]]` in paste-ready WikiTree markup.
- If no profile is found after a duplicate check, state **No WikiTree profile found—create a new profile** and recommend or supply a sourced draft. Never leave a named person unlinked without this recommendation.
- If a possible profile match is not proved, link it explicitly as a possible candidate, explain the conflict or missing evidence, and do not treat it as that person.
- When several record subjects lack profiles, list each one and recommend a separate profile only where the evidence distinguishes separate people.

## Describe groups precisely

- Never imply that a record-based cluster is a WikiTree family or profile group.
- Name the exact record, date, place, reference, and people forming the cluster.
- State whether the grouping reflects co-tenancy, document order, household membership, proven kinship, or only a research hypothesis.

## Prepare WikiTree material

- Cite original images or primary records where available; identify transcriptions as such.
- Save provenance at discovery time, not during profile drafting: whenever a mapped record is added or materially researched, populate `source_title`, the original external `source_url`, `source_type`, and `source_status` in `www/map/data/records.csv` before moving on. Never rely on browser history, chat, a local capture, or the public catalogue to reconstruct the URL later.
- Verify the saved URL resolves to the claimed record. Prefer an item/image URL; when the archive exposes only session-bound results, save its stable public search/catalogue URL plus the collection, sub-index, reference, date, place and access limitation in the title/status. If no external source can be recovered, mark the work **HOLD** and do not generate paste-ready profile text.
- Treat `glasgow.phenotype.dev`, relative repository paths and local `sources/` files as internal research aids only. They must never populate a public citation or `source_url` field.
- Provide paste-ready native WikiTree syntax, not Markdown, and defensible creation fields.
- Write every paste-ready replacement as a complete, polished profile—not a patch note appended to the old biography. Use the durable `Current conclusion` as the narrative basis, preserve useful sourced material from the live profile, remove obsolete or misleading text, and explain the evidence naturally.
- Never remove an existing source or citation from the captured live WikiTree biography when preparing a replacement. Integrate it naturally into the narrative, Research Notes, or Sources even when it is derivative, weak, duplicated, or supports a rejected claim. Qualify what it proves; do not delete it. Do not mention “the earlier profile,” “retained sources,” or the editing process in the biography. A replacement may improve, supplement, or supersede a citation, but every source must remain identifiable and accessible.
- Write in the voice of a human profile editor. For a corrected relationship, prefer prose such as `[[Glasgow-123|Robert Glasgow]] was previously attached as his father. However, ...` followed by the evidence and outcome. Never put editor commands or headings such as `Required profile change`, `Add`, `Remove`, `Detach`, `Replace`, `Revise`, or `Evidence-led project update` inside the copied biography.
- A replacement profile must normally contain the appropriate templates, `== Biography ==`, a prose life narrative with inline `<ref>` citations, `== Research Notes ==` for identity conflicts, uncertain relationships and rejected claims, and `== Sources ==` with `<references />`. Use named references when a source supports more than one statement. Do not dump bare URLs or an AI work queue into the biography.
- Plausible working relationships may remain attached with an explicit uncertain status. Do not present them as proved; detach or replace them when positive evidence contradicts the placement or establishes a materially better identity.

## Maintain findings and catalogue person pages

- After research materially affects a person, update `research/<WikiTree-ID>/findings.md`; do not leave the substantive result only in chat, an agent note, or another file.
- Use headings consumed by the catalogue: `## Current conclusion` or `## Conclusion`; `## Source findings`; assessment headings containing `candidate`, `relationship`, `identity`, `duplicate`, `parentage`, `father`, or `cluster placement`; and action headings containing `unresolved`, `priority`, `recommended`, `suggested`, `correction`, `do not add`, or `next records`.
- Keep the handoff self-contained and source every transferable claim. Put an external record or catalogue URL first when one exists. Treat relative `sources/` links as local research artifacts, not published evidence.
- Rebuild after changing findings with `.venv/bin/python tools/build_family_map.py`.
- Verify the affected `www/people/<catalogue-slug>.html` and `.json`; ensure the expected sections appear and the JSON includes `research_findings`. Run `.venv/bin/python -m unittest tests.test_research_catalog -q` for catalogue-affecting changes.
- Treat the generated `similar_people` table as a research lead, never as proof. Inspect both subjects and their sources, relatives, locations, and witnesses before proposing a merge or relationship.
- When evidence confirms or rules out a possible duplicate or relationship, record the conclusion in each affected existing profile's `findings.md` and update the relevant project register.
- Remember that rebuilding changes local `www/`; it does not publish production until that directory is deployed.

## Interlink and format profile text

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

- The project's `surname-research/new-people/` directory is for **Glasgow-surname people only**. Do not create drafts there for landlords, witnesses, spouses, co-tenants, or other associates with different surnames unless the user explicitly requests an exception.
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
- When the user explicitly corrects a repeatable WikiTree research, citation, profile-editing, or catalogue workflow, treat that correction as skill feedback. During the same task, add a narrowly scoped durable instruction to this project-owned skill unless the user says the correction is one-off or the instruction conflicts with higher-priority rules.
- For catalogue records split from a grouped documentary person, assign the exact source title in the parent entry's `record_profiles` map. A top-level link keyed by the generated split-page slug is ignored by the builder and does not close the unlinked entry.

## Glasgow surname boundary

For Glasgow surname research, treat Glasford, Glassford, Glasfurd, and Glasfuird as a distinct family unless a primary record explicitly proves a bridge. Do not search, merge, or cite those names as automatic spelling variants of Glasgow.

## Identity-defining estimated dates

When a profile represents an adult or householder in a dated record, retain a useful approximate birth estimate derived from that record and mark it estimated. Do not replace it with a later broad `before` date that obscures the profile's intended identity.

## Resolve chronology warnings

Never use WikiTree's `Save Anyway` control merely to suppress a chronology warning. Investigate the dates, places and relationships producing it, then correct the weakest unsupported claim. If an uncertain relationship is deliberately retained, any structured boundary inferred from it must be internally coherent and explicitly described as conditional; keep the direct record boundary separate in the biography and findings.
