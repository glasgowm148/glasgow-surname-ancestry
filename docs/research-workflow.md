# WikiTree Research Workflow

This is the living handoff guide for every terminal researching this workspace.
Update it whenever the process, file contract, or evidence standard changes.

## Project scope: Glasgow surname study

This workspace belongs to the Glasgow Surname Research Group. The subject is the
entire Glasgow surname, not only the WikiTree ID that prompted a search.

- Evidence about any Glasgow before 1700 is critical. Preserve and index it even
  when it is unrelated to the current profile or proves to be an exclusion.
- Search `data/reference/glasgow-one-tree.xlsx` early to locate existing WikiTree candidates,
  name/date/place clusters, and possible duplicates. It is a snapshot/search
  index, not a source: refresh the live WikiTree profile and retain its date-status
  fields (`before`, `about`, and so on) before drawing a conclusion.
- Never force a surname-wide discovery into one person's case. Store evidence
  with multi-profile or unknown-profile value under `surname-research/`.

## Surname reconstruction objective

The primary goal is to group every documentary Glasgow family, infer the smallest
defensible links between clusters, and then seek evidence that proves or rejects
those links. The few hundred people and occurrences between 1475 and 1700 are the
main bridge population; every pre-1600 occurrence receives the highest priority.

Shared Y-DNA supports a project-wide prior that the paternal Glasgow lines share
a common male ancestor around 1500. It is not proof of an individual parent-child
edge and normally cannot distinguish brothers, uncles, or cousins. Preserve
alternative topologies until documentary evidence or a sufficiently specific,
independently anchored Y-DNA subclade distinguishes them.

Every Glasgow found while researching another person remains useful. Capture the
occurrence, check for an existing profile, place it in a locality/time cluster,
and add it to the early register when applicable. Model occurrences, people,
households, clusters, hypotheses, and proved relationships separately.

## Human-facing WikiTree identity format

Every human-facing WikiTree person mention in CLI output, research briefs,
findings, review queues, dashboards, reports, and assistant responses must be a
clickable live-profile link whose label states name, WikiTree ID, birth date or
estimate, and birthplace:

```markdown
[John Glasgow (Glasgow-1022), born about 1751, County Antrim, Ireland](https://www.wikitree.com/wiki/Glasgow-1022)
```

If a field has not been captured, write `name not captured`, `birth unknown`, or
`birthplace unknown` in the label instead of omitting context. Relationship tables
must apply this format to both endpoints. Terminal programs should emit an OSC 8
link when supported and retain a visible URL when output is redirected.

Bare WikiTree IDs are allowed only in machine data, filenames, directory names,
commands, code, and exact WikiTree markup such as `[[Glasgow-1022]]`. When touching
an older human-facing dashboard row, upgrade its link label to the full format.

Exception: the generated `early-profiles.md` and `early-irish-profiles.md` tables
use compact clickable labels
such as `[John Glasgow (1516)](...)` because century and location are supplied by
the enclosing headings. Each century heading and location subsection includes a
count; each century also begins with a location/count/share summary that breaks
father assessments into confirmed, plausible, uncertain, contradicted, and not
assessed counts. The table has no death column, combines the father with its
assessment, and links only to the case `findings.md`, which must contain the
complete source-to-conclusion audit.

## Two-layer storage framework

Use both layers when a discovery affects an individual and the wider surname:

1. `research/<ID>/` remains the case folder for one WikiTree profile.
2. `surname-research/` holds project-wide evidence and indexes:
   - `surname-research/INDEX.md`: main project navigation and data model;
   - `surname-research/indexes/researched-profiles.md`: generated case navigation;
   - `surname-research/indexes/early-profiles.md`: generated pre-1701 profile list,
     grouped by counted century and area sections with a per-century location summary;
   - `surname-research/indexes/early-irish-profiles.md`: generated Irish cohort
     through 1799, grouped by century and county with the same assessment summary;
   - `surname-research/indexes/father-assessments.json`: manual evidence status for
     fathers displayed in the early index; never infer confirmation from attachment;
   - `surname-research/indexes/irish-cohort-audit.json`: manual working-century
     and inclusion overrides when the raw WikiTree dates misclassify Irish evidence;
   - `surname-research/indexes/relationship-hypotheses.md`: manual proposed-edge
     register with alternatives and proof targets;
   - `surname-research/clusters/README.md`: continuously maintained quick-view
     dashboard of significant findings, grouped by location/family research cluster;
   - `surname-research/to-update.md`: continuously maintained manual work queue
     containing the 20 highest-priority existing-profile updates plus new-profile
     creation and completion tables;
   - `surname-research/clusters/early-ireland-root-clusters.md`: evidence-graded
     Irish root map separating dated occurrences from reconstructed lineages;
   - `surname-research/pre-1700/evidence-register.md`: central early-evidence log;
   - `surname-research/pre-1700/sources/`: complete original publications/records;
   - `surname-research/pre-1700/page-extracts/`: derived images for quick review.

For every pre-1700 Glasgow occurrence, record the name as printed, normalized
place, record date/range, record type, page/archive reference, URL, local artifact,
and evidentiary meaning. Transcribe all Glasgow occurrences in the relevant list,
not only the name that triggered the search. Preserve qualifiers such as elder,
younger, spouse, widow, occupation, Over, Nether, and joint-holding wording.

Do not collapse repeated names. A person may hold more than one property, while
two same-name people may coexist. State the minimum/maximum number of possible
individuals and what evidence would distinguish them.

For every proposed new early profile, audit all of `profiles.json`, the workbook,
generated indexes, existing `new-people` drafts, case captures, redirects and a
live WikiTree name/date search. Generated century indexes omit undated profiles,
so absence there is not a duplicate check. Separate a new documentary
occurrence from a new minimum person: do not create a second profile while an
existing same-name person remains chronologically and geographically possible.
If a post-1599 record is used to infer a sixteenth-century birth, label the
adult-status assumption and estimated boundary explicitly.

For root-cluster work, use this order and do not skip levels:

1. `Documented occurrence`: the record proves a name, date and place only.
2. `Probable repeated identity`: two occurrences likely concern one person, but
   no two-location or relational bridge proves it.
3. `Working cluster`: households share a tight place/time network; kinship is a
   search hypothesis, not a tree edge.
4. `Proved relationship`: an original record names the relationship and the
   identities at both ends are resolved.
5. `Reconstructed lineage`: family testimony, naming, Y-DNA or inherited trees
   propose a descent that remains labelled until documentary edges are found.

Free-space branch pages should lead with documented Irish occurrences and then
show reconstructed lineages separately. Never promote a Scottish baptism into
an Irish founder merely because its name and estimated age fit.

The early-profile index is grouped by century and recorded-birthplace area. Its
father column uses these evidence levels: `confirmed` requires a relational record
and resolved identity; `plausible` requires a conflict-free indirect proof case;
`uncertain` covers an attachment or proposal not yet established; `contradicted`
flags an attachment the reviewed evidence conflicts with or does not support.
Update `surname-research/indexes/father-assessments.json` when a parentage
assessment changes. Absence from local case captures is `not assessed`, not proof
that the live profile has no attached father.

## WikiTree free-space page contract

`surname-research/free-space-pages/` is the project-wide publication queue for
WikiTree free-space pages. These pages synthesise research; they are navigation
and interpretation, not evidence themselves.

- `README.md` is the inventory of all known Glasgow-related free-space pages. A
  page listed there may be relevant even when no local text snapshot exists yet.
- The three current local snapshots cover the Glasgow Name Study and the early
  Scotland and Ireland branch pages.
- In each local page file, the fenced code block is the text copied from WikiTree.
  Treat that block as an immutable snapshot: do not silently edit or rewrite it.
- Put every proposed change after the closing code fence under a single
  `## Suggested amendments` heading. Update an existing proposal instead of
  appending a duplicate.

Review free-space impact whenever research discovers a new Glasgow occurrence,
corrects an identity or date, proves or rejects a relationship, changes a branch
placement, identifies a migration, or materially changes a DNA interpretation.
Check the complete `README.md` inventory, not only the three locally copied pages.

Each amendment proposal must contain:

1. A short descriptive heading and one status: `READY`, `REVIEW`, `BLOCKED`, or
   `APPLIED`.
2. The exact affected section or passage and whether to add, replace, or delete it.
3. A concise explanation of why the current wording is incomplete or unsafe.
4. Fully copy-ready WikiTree WikiText in a fenced `wikitext` block.
5. Complete inline `<ref>...</ref>` citations in that WikiText. Prefer the original
   record or image; include repository, collection, record identifiers, page or
   image number, direct public URL, and access date where applicable.
6. An evidence assessment distinguishing a recorded occurrence from person
   identity, branch membership, and relationship proof. State competing
   interpretations when the evidence does not select one.
7. Links to the relevant local `findings.md`, review queue, or surname evidence
   register for the full internal analysis.

Local files are preservation aids and must not be the citation offered to a
WikiTree reader. If no public item-level URL exists, cite the archive catalogue
and full reference, state that the record is offline or access-restricted, and
identify the local copy as internal preservation only.

Use statuses as follows:

- `READY`: wording and every citation are verified and safe to paste.
- `REVIEW`: the finding is useful, but identity, wording, or page placement needs
  human judgement.
- `BLOCKED`: a material page problem is known, but the necessary source or safe
  replacement is unavailable.
- `APPLIED`: the user reports applying it and a refreshed page snapshot confirms
  the change. Move or retain the proposal as a compact amendment history; do not
  mark it applied solely because text was drafted.

For an inventory-only page that becomes relevant, first obtain or paste its current
text into `surname-research/free-space-pages/<Space_Name>.md` using the same URL,
snapshot code block, and amendments-below structure. Until its current text is
available, record only a `BLOCKED` inventory note; do not draft a blind replacement.

## Start or resume a case

```bash
.venv/bin/python src/wikitree_family_export.py WikiTree-123 \
  --research-dir research/WikiTree-123 \
  --descendant-depth 2
```

The shared API client sends the project application ID and ordinary same-site
browser headers. WikiTree's AWS WAF otherwise returns an empty HTTP 202 challenge
to generic script user agents before `api.php` receives the request. Treat that
response as access failure, not as an empty or private profile.

Read these first:

- `surname-research/clusters/README.md`: current significant findings and pending
  WikiTree transfers across every active cluster;
- `surname-research/free-space-pages/README.md`: inventory of synthesis pages that
  may need an amendment when the case produces a surname-wide finding;
- `research/<ID>/research_brief.md`: generated compact case context.
- `research/<ID>/research_plan.json`: queues and open questions.
- `research/<ID>/findings.md`: complete handoff containing the permanent
  source-to-finding log, current live-profile delta, cautions, and exact WikiTree
  update instructions.
- `research/<ID>/<ID>.md`: legacy review file retained where it already exists;
  its actionable content must also be consolidated into `findings.md`.

Raw API captures stay in `captures/`; downloaded evidence stays in `sources/`.
Do not overwrite either. The exporter may rebuild `research_brief.md` and
`evidence_index.json`, but it never overwrites `findings.md` or a legacy
`<ID>.md`.

## Token and unattended-loop guardrails

Research depth never authorises unlimited token use. Apply these rules to every
interactive, automatic, overnight, or resumed research loop:

- Run one coordinating session per research question. Never start or resume
  duplicate sessions, agents, or model variants on the same question unless the
  user explicitly requests parallel work. Give approved workers exclusive,
  non-overlapping source lanes.
- Treat `keep searching`, `search deeper`, and similar requests as one bounded
  pass, not permission for an indefinite loop.
- Before searching, read the existing `findings.md`, source audits, plan, and
  saved artifacts. Build a short checked-source/query ledger. Do not repeat a
  source or equivalent query unless new evidence gives a stated reason.
- Use a compact task brief rather than replaying the full conversation or whole
  repository. Read targeted sections and cap tool output aggressively. If the
  working context becomes large enough to require repeated compaction, stop and
  write a concise handoff before continuing in a fresh session.
- Every cycle must name one unresolved claim, one new source class or record,
  and the result that could change the conclusion. A broad web search without a
  new proof target does not qualify as another cycle.
- Default unattended-pass ceiling: 10 cycles, 60 total tool calls, or 10% of an
  available quota, whichever comes first. If quota telemetry is unavailable,
  enforce the cycle and tool-call limits. Exceed them only with explicit user
  approval for a new bounded pass.
- Stop early after three consecutive cycles produce no material new evidence.
  Save their bounded negative results once; do not paraphrase them into multiple
  files during the same pass.
- Check quota/process telemetry at the start and during unattended work when it
  is available. Stop immediately if duplicate sessions are detected or usage is
  materially higher than the configured ceiling.
- Report only genuinely new evidence, changed confidence, corrected prior
  claims, and the best unsearched targets. State plainly when a pass found
  nothing new.

## Research loop

1. Scrape the subject and only the relatives required by an open question.
2. Compare the subject's latest raw WikiTree biography with each discovery and add
   only missing sourced facts or corrections to the `WikiTree update instructions`
   section of `findings.md`.
3. Compare every new fact with the downloaded biography. Record working evidence,
   negative results, exact evidentiary effects, and paste-ready wording in
   `findings.md` and the
   structured `findings`/`web_searches` fields of `research_plan.json`.
4. Keep `findings.md` self-contained so it can be pasted into ChatGPT together
   with the live profile without needing another case file. Do not queue facts
   already present on the live profile.
5. Save original images, PDFs, or JSON in `sources/` with descriptive names.
6. Update `research_plan.json`; pursue the next record capable of resolving the
   question, then repeat.
7. In the same turn, add or update the person's row in
   `surname-research/clusters/README.md` whenever the finding materially changes
   a WikiTree fact, relationship, identity assessment, correction, or warning.
8. Update `surname-research/indexes/relationship-hypotheses.md` when a proposed
   edge, competing topology, confidence level, or resolving record changes.
9. Check `surname-research/free-space-pages/README.md`; update the amendment
   section beneath any affected local page snapshot with fully cited WikiText.
10. Update `surname-research/to-update.md` when the discovery creates, resolves,
    raises or lowers a concrete WikiTree edit priority.
11. Run `.venv/bin/python src/surname_research_index.py`; normal exporter case runs do
   this automatically for cases stored under `research/`.

When an original record converts a speculative relationship into a direct one,
propagate it to both people's `findings.md` files. Explicitly retire
the superseded research note and update the relationship certainty, but do not
extend the record to an unnamed parent, sibling, or child. If the relationship is
already attached on WikiTree with uncertain status, the handoff still requires a
clear resolution note so a later terminal does not keep researching it.

## Findings handoff contract

`findings.md` is the single Markdown research and update handoff for a profile.
It is not a replacement biography, but it must contain everything needed to
update the current WikiTree profile safely.

- Refresh/download the profile before editing and record only facts or corrections
  absent from that capture.
- Use `Suggested additions`, `Suggested corrections`, and `Do not add as fact`
  beneath `## WikiTree update instructions`. Every addition needs a source,
  confidence level, and qualification.
- For every `READY` or `REVIEW` item, state the target profile in the heading and
  provide the **exact WikiTree text to add or replace**, including complete inline
  `<ref>...</ref>` citations. A fact/source table may explain the change, but it is
  not a substitute for paste-ready profile wording.
- After the user makes only part of a queued change, refresh the live profile and
  rewrite the update-instructions section so it contains only what is still
  outstanding. Explicitly name
  any stale paragraph or section to delete and supply its replacement text.
- Do not present a candidate parent, same-name identity, estimated date, or inferred
  kinship as established fact.
- Keep full source analysis and repeated negative searches above the update
  instructions; repeat a short negative in the instructions only when it prevents
  a likely WikiTree error.

### Public catalogue integration

Every catalogue rebuild reads `research/<ID>/findings.md`. Substantive sections
are placed into the corresponding public person dossier as follows:

- `## Current conclusion` or `## Conclusion` appears immediately after identity details;
- `## Source findings` appears after the chronological record timeline;
- headings containing `candidate`, `relationship`, `identity`, `duplicate`,
  `parentage`, `father`, or `cluster placement` appear with evidence assessments;
- headings containing `unresolved`, `priority`, `recommended`, `suggested`,
  `correction`, `do not add`, or `next records` appear with research questions.

Untouched template text and profile-scrape dumps are not republished. External
links remain clickable. Relative links into local `sources/` folders are labelled
as local research artifacts because those files are not automatically published.
Known WikiTree IDs are linked to their catalogue person pages.

Run `.venv/bin/python tools/build_family_map.py` after changing `findings.md`.
The rebuilt HTML and person JSON then update together. The public site changes
only after the regenerated `www/` directory is deployed.

### Preserve useful uncertain relationships

The project is reconstructing one extended paternal family, so a plausible
working edge is useful even when no record states it directly.

- Do **not** recommend detaching a parent, child, sibling or spouse merely because
  the relationship is unsupported or less than certain. Preserve it as uncertain
  when chronology, locality, associates, naming or cluster evidence make it a
  reasonable working placement.
- Recommend detachment only when there is a materially better-supported placement,
  a proved alternative identity/relationship, or the user explicitly asks for it.
- A chronological conflict should first trigger review of the estimated dates and
  identities. If no better placement is known, retain the edge as uncertain and
  document the conflict rather than leaving the person isolated.
- When a record proves a smaller nuclear family but omits other attached people,
  do not treat omission alone as automatic exclusion. Mark the omitted people as
  uncertain and test whether they belong one generation lower or in a collateral
  branch.
- Two apparently contemporary living children with the same forename are a
  material topology warning. Rank the competing edges by explicit parentage,
  exact household/land succession, chronology and only then naming patterns;
  do not preserve both merely because both are marked uncertain.
- A spouse's surname or house affiliation proves a marriage network, not the
  subject's parentage. It may support a wider cluster hypothesis, but never use
  it alone to select a mother, father or exact generation.
- Do not give high `to-update.md` priority solely to downgrading or removing an
  unproved relationship. Prioritise newly proved people, relationships, events,
  migrations and materially better placements. Confidence wording and unresolved
  topology belong lower unless they prevent a serious conflation.

### Public-source link contract

Local files under `sources/` preserve evidence for this workspace; they are not
links that a WikiTree reader can open and must never be presented as the citation
to paste into WikiTree.

- Every fact in `findings.md` that is ready for transfer must include paste-ready
  `<ref>...</ref>` text linking to the actual public source record, image, scan,
  publication page, or archive catalogue item whenever one exists.
- Put the external source URL first in each `findings.md` source entry. A local
  scan, transcript, manifest, or capture may be mentioned second and explicitly
  labelled `internal preservation only; not a WikiTree citation`.
- Prefer a direct record or image URL over a database home page or search form.
  Include the repository, collection title, volume/book, page or image number,
  record ID, relevant dates, and access date so the citation remains identifiable
  if the URL changes.
- A paywall or login requirement does not justify replacing the public record URL
  with a local path. Link the actual record/image and state the access restriction.
- If no public item-level URL exists, link the holding archive's catalogue or
  collection page and give the complete call number. State that the source is
  offline or undigitised. Keep the local artifact only as an internal aid.
- Before marking an item `READY`, verify that each external URL resolves to the
  claimed source and that no paste-ready wording or source column relies only on a
  relative `sources/` link.
- A transcription is a reading aid, not a substitute for the original. Cite the
  original source; identify the transcription separately only when it adds useful
  editorial context.

### Live-profile delta and priority

Judge corrections against a fresh live profile, not against a family history,
old capture, index title, or earlier version of the profile.

- Refresh the live profile immediately before updating `findings.md` or assigning a
  dashboard priority. Preserve qualifiers such as `about`, `before`, and `after`.
- If the structured field and biography already contain the substantive point,
  queue only the missing precision, source, or wording. Do not call it a major
  correction merely because the newly inspected source is important.
- Reserve `urgent` or `major correction` for a materially wrong live relationship,
  identity, source attribution, or vital event that is still outstanding and is
  likely to propagate. Exact-day refinements and fuller source details normally
  receive a descriptive lower-priority label.

### Continuous WikiTree update queue

`surname-research/to-update.md` is the canonical ranked work queue for manual
WikiTree edits. Keep it continuously useful rather than rebuilding it only when
requested.

- Maintain **20 outstanding profiles** whenever at least 20 actionable deltas
  exist. Refill vacancies in the same research turn from `findings.md`, review
  files and the cluster dashboard.
- Also maintain a separately ranked `New profiles to create` table for every
  actionable draft under `surname-research/new-people/`. These rows do not count
  against the 20 existing-profile updates. Rank a newly proved family or root
  cluster above an isolated occurrence, and order related creations so the
  connecting parent or evidentiary anchor is created first.
- Keep a `Created new profiles` table in the same file as durable completion and
  duplicate-prevention history. Mark a creation `DONE` only after a live API
  refresh confirms the profile; link its clickable WikiTree ID and retained
  evidence draft, and add the created ID to the top of that draft.
- Refresh every candidate's live WikiTree profile immediately before adding,
  retaining or reprioritising it. The queue must describe only changes still
  absent from the live page.
- Rank direct relationship evidence, severe conflations, wrong-person sources,
  false migrations, and materially wrong vital events first. Then rank substantial
  original-record additions. Do not fill the leading positions with wording
  preferences or complaints that a correctly qualified uncertain link is not
  certain enough.
- Rank by the **magnitude of the outstanding change created by new evidence**.
  A newly identified family, person, branch, migration, or major conflation ranks
  above cleanup left after the main discovery has already been transferred.
  Structured-field mismatches, citation precision, wording cleanup and residual
  qualifiers belong near the bottom even when their source is strong.
- The leading ten should answer: **what new information materially changes the
  tree or our understanding of a branch?** If a row cannot answer that, move it
  below substantive discoveries.
- Each row links the live profile and one complete `findings.md` handoff. Keep the
  exact change, live-check result, evidence, cautions, and paste-ready text inside
  that file rather than duplicating them across queue columns. Person labels
  follow the human-facing identity format in this guide.
- When the user reports working through the queue, do not assume an item is done.
  Refresh the live profile; remove or move it out of the ranked table only after
  the substantive change is visible. If only part was applied, rewrite the row
  and its update-instructions section to contain only the remainder.
- Keep a compact `Checked and not counted` section for important findings whose
  principal change is already live, so later terminals do not requeue them.
- Reconcile both creation tables with the `New-profile status` section of
  `surname-research/clusters/README.md` in every queue-maintenance pass. A draft
  must not remain under `CREATE` after its live profile has been verified.
- Update the queue title, row numbering, live-check date and the link in
  `surname-research/clusters/README.md` whenever its maintained size changes.
- Only the coordinating terminal edits this shared queue during parallel work;
  other workers report candidates through their case files.

## Significant-findings cluster dashboard

`surname-research/clusters/README.md` is the canonical human dashboard. It must
stay current; it is not an occasional summary generated at the end of a project.

- Group people under the best-supported location or research family-group. A
  shared table is navigation and context only, never proof of kinship. Say so in
  the dashboard and preserve uncertainty when cluster membership is provisional.
- Every row for an existing profile must link to its complete
  `research/<ID>/findings.md` handoff. A separate legacy `<ID>.md` link is not
  required once its actionable content has been consolidated.
- Make the person's name in the first column a direct link to their live WikiTree
  profile (`https://www.wikitree.com/wiki/<ID>`). Leave it unlinked only for a
  `CREATE` row where no profile exists yet.
- Make the dashboard answer **what new concrete information can be added, and to
  which profile**. Lead every summary with the positive fact, event or relationship
  found. Put detailed caveats and update instructions in `findings.md`; include only the
  qualification needed to prevent the dashboard fact being misused.
- Plausible identity and relationship links are useful and should remain visible
  when supported by a coherent combination of place, period, associates and family
  evidence. Label them `plausible`, `possible`, `uncertain`, or `working
  hypothesis` rather than suppressing them merely because no single record states
  the link directly.
- Summarise the significant evidentiary change in one short sentence. Do not copy
  the full proof or source table from `findings.md` into the dashboard.
- Add or update a row in the same research turn when a finding:
  - supplies or corrects a date, place, occupation, event, spouse, parent, child,
    sibling, or other relationship;
  - identifies a conflation, wrong citation, wrong record, unsupported attachment,
    or dangerous same-name merge;
  - materially upgrades or downgrades confidence in an existing WikiTree claim; or
  - produces a qualified negative or source limitation that should be preserved on
    WikiTree to prevent a likely error.
- Use only these transfer statuses:
  - `READY`: important sourced text/correction is waiting in `findings.md`;
  - `REVIEW`: significant finding exists, but wording or identity needs human
    judgement before transfer;
  - `BLOCKED`: important evidence exists, but no safe profile addition is possible;
  - `CREATE`: duplicate checks are complete and a new-person draft is ready;
  - `DONE`: a refreshed live profile confirms the queued material was transferred;
  - `NONE`: useful research exists but nothing material should be transferred.
- Never set `DONE` merely because text was drafted or because someone reports an
  edit. Refresh the live WikiTree profile and confirm the material is present.
- When the user has deliberately added a plausible link as an uncertain
  relationship, treat that transfer as complete once the refreshed live profile
  confirms both the link and its qualified wording. Do not keep re-queuing it only
  because a direct parentage record has not been found.
- Keep the dashboard's `Highest-priority work left to add to WikiTree` table
  limited to genuinely outstanding work. Put direct relationship proofs, severe conflations,
  wrong-person sources, major vital-event discoveries and corrections likely to
  propagate there. Remove them once verified `DONE` or no longer actionable;
  retain their ordinary cluster row as history.
- For a person without a WikiTree profile, add a `CREATE` row linking the paste-ready
  file under `surname-research/new-people/` and ensure the duplicate audit is in the
  surname evidence register. Once a WikiTree ID is created or confirmed, move the
  draft to `research/<WikiTree-ID>/` and update the row and all inbound links.
- Update the dashboard's `Last updated` date whenever any row or status changes.
- Before ending a research turn, compare every changed `findings.md` or
  new-person draft with the dashboard. Missing or stale rows are unfinished work.

## Strict merge gate

- **Never recommend or perform a WikiTree merge unless the two profile
  identities are proved to be the same person.** Strong likelihood, matching
  names, compatible dates, shared locality, naming patterns and apparent tree
  duplication are not enough.
- Before proposing a merge, compare all available parent, spouse, child,
  occupation, residence, baptism, marriage, testament, apprenticeship, burgess
  and land records. A conflicting named parent blocks the merge until resolved.
- Record merely probable duplicates as separate `possible duplicate` research
  targets. Preserve both profiles and explain the test needed to decide them.
- Refresh both WikiTree IDs immediately before giving merge or separation
  instructions. Query with redirect resolution: a merged-away profile may still
  be returned as an archived object unless `resolveRedirect=1` is used.
- If an incorrect merge has already completed, preserve the surviving ID's
  original record-defined identity, create one replacement profile for the
  conflated person, move only record-supported relationships, and document the
  redirect. Never create further duplicates merely to make an uncertain
  existing-profile match appear certain.

## Proposed new profiles

Every named historical person in research reports must be introduced with a
clickable WikiTree profile link. If no matching profile is found after the
required duplicate audit, say **No WikiTree profile found—create a new
profile** and recommend or provide a sourced draft. If a possible match is
unproved, link it as a candidate and state why it cannot yet be identified as
the record subject. Never leave an unlinked person as an implied member of a
record cluster or family.

When evidence identifies a Glasgow who needs a new WikiTree profile, create
`surname-research/new-people/<year>_<country>_<precise-location>_<name>.md`.
This directory is only the unresolved Glasgow creation queue. As soon as the
person receives or is matched to a WikiTree ID, move the draft to
`research/<WikiTree-ID>/<year>_<country>_<precise-location>_<name>.md`, update
all inbound links, and move the dashboard entry to the resolved-profile section.
Store non-Glasgow collateral drafts under the relevant Glasgow research folder,
not in `new-people`.

- First search `data/reference/glasgow-one-tree.xlsx` and the live WikiTree API for likely
  duplicates, including spelling variants. When one source names several
  Glasgows, complete this check for every person represented, not only the name
  that triggered the research. Record the complete audit in the surname-wide
  evidence register.
- Before proposing creation, inspect every record-identified child and spouse on
  WikiTree. A missing parent search result does not establish that the parent is
  absent: the person may already exist as the structured or biography-linked
  parent of a child's profile. Record the child IDs checked and their current
  parents in the duplicate audit.
- Write a complete, paste-ready biography using the same native WikiTree syntax
  and sourcing rules as the update-instructions section of `findings.md`.
- Give defensible creation-field suggestions under `=== Research Notes ===`. For
  an adult record with no birth date, normally use `before <record year minus 18>`
  and mark it uncertain. For a date range, use its latest year so the estimate
  does not claim more precision than the source supports.
- Do not treat a recorded holding or residence as a birthplace. Estimate a wider
  place only when justified and mark it uncertain.
- State unknown relationships and warn against any tempting but unproved
  identification or family link.
- Create the minimum number of people established by the evidence. If a repeated
  same-name occurrence could be one multi-holding tenant or two people, base one
  draft on a certain occurrence and explain the other occurrence without merging
  it as fact; create a second person only when evidence distinguishes them.
- If a matching profile exists, do not create a new draft. Link it in the
  evidence register and record any conflation or source-interpretation problem.

Before using a transcription or database export, audit its layout. Confirm whether
name order, adjacent rows, headings, and place labels reproduce the original record
or are artifacts of columns, OCR, sorting, or indexing. Save enough surrounding
context to make that interpretation independently reviewable.

For Registry of Deeds leads, keep book/page/memorial together and check the same
number across every secondary index used. A conflicting memorial citation is
unusable until verified against the original. Never transfer a townland, party or
relationship from the preceding or following memorial. When the original is
login-only, save the film/DGS mapping and record `inaccessible`, not a negative
finding about its contents.

For year-addressable register transcriptions, sweep a bounded date range for every
surname spelling rather than trusting search-engine coverage. Preserve the full
source page and record parents, residence, witnesses, denomination, and negative
years before deciding whether a same-name person belongs to the case.

Before searching a church collection, verify the exact surviving dates and record
types in an archive inventory. A session or discipline book is not a baptismal or
membership register, and a synod/delegate roll is not a congregational roster.
Record a date gap as a coverage limitation, not a negative search result.

Apply the same rule to petitions, censuses, tax lists, and name indexes: inspect the
collection's surviving-place inventory before searching it. If the target parish or
congregation is absent, log an untestable coverage gap rather than a surname negative.

Treat Irish census search forms as claimant-created evidence rather than surviving
census returns. A form can state an applicant's claimed parents, childhood townland,
and household members even when the official search failed, but the claims still need
corroboration. For the six northern counties, audit both the NAI collection and the
separate PRONI holdings; a blank NAI result is not an exhaustive negative. If a public
result exposes only surname/place metadata and the detail page is inaccessible, save
the result ID as an uninspected lead and make no claim about its household contents.

For estate-sale schedules, distinguish current purchase tenants from historic head
lessees, under-tenants, and named lease lives. A later schedule without lease
recitals can close an occupancy timeline but cannot prove earlier absence or kinship.

Treat ordinal child descriptions such as `sixth daughter` as direct minimum-family-size
evidence. Open a separate search lane for every missing older child, but do not invent
names, assume all were living, or equate ordinal birth order with surviving-child order.
For newspaper compilations, log the first issue date, transcription periods, variants
searched, and whether the page is selective; silence in such a compilation is not a
negative marriage or death record.

For dynamic archival portals, preserve the search payload, result metadata, and
original image or IIIF manifest. Read the full original-page context before treating
an OCR name hit as the target person; record unlinked namesakes as exclusions.

For Internet Archive texts, query the metadata API first, save the original PDF when
relevant, and search the derived DjVu text only as an OCR aid. Verify every useful
hit against the scan and identify whether a printed list is a full roster, a delegate
roll, an index, or selected names before drawing negative conclusions.

For legacy ASP.NET archive searches, preserve the session cookie and submit the
returned `__VIEWSTATE`, `__VIEWSTATEGENERATOR`, and `__EVENTVALIDATION` values with
the search fields. Save the result HTML and any linked original image, then run an
independent place-name search to test geographic coverage. A missing person is not
negative evidence when the target townland is absent from the database.

ASP.NET control names often contain literal `$` characters. URL-encode the complete
button name or pass it without shell interpolation, then inspect the submitted body;
a collapsed field such as `ctl00=More` silently posts the wrong control.

The Virtual Record Treasury public full-text endpoint is:

```text
POST https://by2022-prod.adaptcentre.ie/IR_REST_V2/webapi/doc_search
Content-Type: application/json
{"indexDBName":"beyond_2022","totalElementsInt":100,"kwOperList":["EXACT"],"kwList":["Adam Glasco"],"kwSearchFieldList":["all"],"resultSorting":"relevance","pageNumberInt":0}
```

Start with an exact full name, then spelling variants and exact locality. Save the
payload, result count, references, snippets, and raw JSON. Deduplicate continuation-
page OCR hits and repeated snippets from compiled volumes. `Glasgow` is also a place,
so generic hits need original-page context. Treasury silence covers only its indexed
and reconstructed corpus, not undigitized PRONI, church, estate, or destroyed records.

For a decisive FamilySearch image set, keep it a bounded exception rather than
expanding the main loop. Resolve an old `pal:/MM9.3.1/...` URL to its modern ARK,
then query the official image resource and waypoint endpoints. The waypoint JSON
preserves every ordered image ARK and thumbnail link even when the viewer requires
sign-in:

```text
GET https://api.familysearch.org/platform/records/images/<image-id>?cc=<collection>&wc=<waypoint>
GET https://api.familysearch.org/platform/records/waypoints/<waypoint>?cc=<collection>
Accept: application/x-fs-v1+json
```

Save the waypoint response under the case `sources/` directory. Treat its citation,
image order, access rights, and thumbnail links as metadata only; do not claim names
or relationships from an unviewed image. Check both the recorded will book and the
separate loose will-packet film when the catalog identifies both.

Before attempting FamilySearch Full-Text Search, check the public collection list at
`/en/search/full-text/collection/list?count=100`. A collection's existence in the
image catalog does not mean it has a Full-Text transcript. If the image API reports
`restricted=true` and `authorized=false`, record the access limitation and pivot to
the packet film, a published abstract, or the holding archive; do not try to bypass
the restriction or infer text from a low-resolution thumbnail.

For a loose packet film, use the catalog's stated opening docket and count ordered
packet covers to isolate the target. Save the target cover, all images up to but not
including the next cover, the next cover as boundary evidence, and a manifest with
every sequence ID and ARK. Preserve public thumbnails unchanged; label enlargements
as derived. A cover count locates a packet but does not prove its name, docket, or
contents: verify those from a permitted full-resolution image, transcript, abstract,
or repository copy before reporting beneficiaries or relationships.

For Irish civil records, search the official IrishGenealogy index, open the detail
page, then download the linked original register PDF. The detail page alone usually
contains only names, date, district and group ID; occupations, residences, marital
status, fathers and informants must be read from the image. Preserve both the stable
`/view/?record_id=...` URL and PDF locally. Elderly death ages are estimates, and
`present at death` does not state the informant's relationship.

When a subject lacks a parent record, test a census-proved sibling's post-1845 Irish
marriage. Build the proof chain explicitly: direct sibling statement, unique identity
match across spouse/date/residence/occupation, then the marriage's father statement.
This can strongly identify or exclude a shared father, but record the residual
half-sibling possibility unless another source proves full siblinghood. Never extend
a sibling's named father through mere surname or locality without that identity chain.

Run a tree-topology consistency check whenever an original source states `brother`,
`sister`, `son`, `daughter`, `uncle`, or `nephew`. Compare the direct relationship
with every attached parent link. If the source makes an attached uncle into a brother,
the current links cannot all be true; flag the exact alternatives instead of choosing
one by intuition. A late descendant account cannot override the original statement.

Do not assign an undated or name-only tithe, rental, or land entry when two same-name
adults could have occupied the locality. A useful place match still needs age, spouse,
occupation, adjoining holding, or another identifier before it can carry a relationship.

For a well-documented emigrant collateral, search the destination death registration,
probate notice, obituary, and institutional biography. These often name parents or
siblings omitted from Irish records. First prove that the emigrant is the correct
collateral; an explicitly different birthplace, generation, or already documented
parent family makes it an exclusion, not a bridge to the target.

## Evidence standard

- Trees, profile attachments, naming patterns, and unsourced dates are clues only.
- State whether evidence is direct, indirect, negative, or exclusionary.
- Do not infer a relationship merely from shared surname, locality, or land succession.
- Distinguish original images from indexes and modern transcriptions.
- Record failed searches so another terminal does not repeat them.
- Do not identify or attach a parent without a relational record or a documented,
  conflict-free proof argument.

For sparse pre-1600 surname work, count **minimum people**, not name hits. A
testament clause naming four children proves four people even when only forenames
are repeated; first audit every plausible existing profile before creating the
missing minimum. Conversely, a land occurrence with the same name as a living
profile is an identity candidate, not automatically a new person. Every draft
must state the direct record, date/place/spouse or parent discriminator, all
serious duplicate candidates, and whether the birth estimate is proved or only
back-calculated from adult status.

Mine testament indexes in both directions: the Glasgow surname heading and the
maiden-surname heading for `spouse`, `relict`, and `widow`. Spouse-side entries
often reveal surname bearers omitted from the Glasgow heading's dated entries.
Verify printed page versus scan page (`page/n...`) and retain the exact record
place form before normalising it with an authoritative place gazetteer. For every
quoted relationship, visually inspect the linked scan itself: OCR may locate the
entry but cannot validate the wording or the leaf link. Record the protocol/item
number, printed page and scan leaf, and test that the public link opens on the
page containing the quoted text before marking the finding ready.

## Parallel terminals

Use a separate case folder per root WikiTree ID. Within one case, give each worker
its own `agent_<scope>.md`; only the coordinating terminal edits `findings.md` and
`research_plan.json`. This prevents concurrent overwrite.

If research on one case produces a new fact about another existing WikiTree person,
also create or update `research/<Affected-ID>/findings.md`. Put the full
source-to-finding entry and update instructions in that person's file and copy the
necessary source artifact into its `sources/`
directory. The root case keeps only the finding's effect on its own question. This
applies even when the affected person is only a comparator or excluded candidate.

Run offline verification after exporter changes:

```bash
.venv/bin/python -m unittest -v
```

FamilySearch is optional and separate; the main loop is WikiTree plus public and
archival web research. See `README.md` for FamilySearch setup if it is genuinely needed.

## Reconstructing same-surname locality clusters

Do not translate census household sequence into literal next-door residence or a
minimum kinship degree. Record every intervening household and describe the result
as an enumeration cluster. Then combine it with independent evidence such as an
explicit relationship, marriage father statement, occupation, church residence,
valuation plot, or revision-book succession.

When a land index contains a common given name, enumerate every age-compatible
namesake before assigning it. A later marriage can be decisive identity evidence
when it links the same occupation and both adjoining townlands. Keep these levels
separate:

- `proved`: a source states the relationship;
- `probable`: a conflict-free multi-record identity or kinship argument;
- `working`: the best current tree placement, explicitly marked uncertain;
- `possible`: one of multiple unresolved topologies.

Save both an evidence tree and, when useful, a connected working tree. A working
parent link must state the complete supporting argument and the adverse evidence.
For alternative topologies such as `brothers` versus `father and son`, do not add
either structural link merely to make nearby families cousins. Record the dotted
or narrative connection until a relational source distinguishes the alternatives.

Audit every census marriage-year field against attached spouse metadata. In the
1851 returns, the last three occupant fields are first, second, and third marriage
years. A marriage year copied from a nephew or other household member is an
identity error, not evidence for the head and wife.

In PRONI valuation-revision books, use the folio number in the upper-right corner,
not the printed spread page at the bottom, when following the manuscript index.
Compare the primary valuation's map reference with the opening entry and every
coloured revision. A same-plot cottage sequence can establish occupation and
succession, but separate letters such as `18b` and `18c` identify separate houses
and do not establish a family relationship. Save the full folio scan, reference,
volume date range, and the identity argument in every affected profile folder.

## Root-first generational clustering

When the project has genetic or accumulated evidence for one remote surname root,
do not turn every unproved later family into a separate root. Start from the
working common ancestor, lay out generation bands, and count the exact missing
parent-child steps. For each later profile:

1. place it in the best locality and generation cluster;
2. show the shortest plausible route to the root using clickable WikiTree IDs;
3. mark every edge `proved`, `probable`, `working` or `possible`;
4. insert documented unconnected households into the gaps as candidates;
5. test same-name, same-age profiles as duplicates before creating two children
   with the same name under one parent;
6. maintain the result in a cluster map and link every affected `findings.md`.

An unsourced profile can be a useful topology placeholder, but must never be
presented as evidence. Prefer a record-led missing-person slot over silently
accepting tree-derived names and dates.
