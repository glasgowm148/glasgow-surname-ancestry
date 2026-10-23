# Findmypast catalogue workflow

Paths below are relative to the repository root. Use `.venv/bin/python` and `PYTHONPATH=.` for project imports. Inspect the current tool/schema when a field or option is uncertain; do not copy an old batch's counts, IDs, dates or temporary script blindly.

## Resume and capture

1. Inspect `git status`, the active goal, existing `research/findmypast-glasgow-audit/` capture/coverage files, maintained integration decisions, approved saved receipts, `research/canonical_records.json`, the current public records index and relevant current person findings. Preserve concurrent changes. Record the browser resources this task owns before heavy work.
2. Before opening any transcript/detail page, preflight every known provider record ID against those sources. Use `tools/fmp_record_preflight.py` with explicit IDs or a rows file when available; inspect its current help/schema. Until that tool is available, do the same exact-ID comparison from the maintained files; do not skip preflight. Keep the exact disposition for each ID. Prioritize cached but unintegrated records before opening new browser pages. Preserve existing HOLD dispositions. Reuse accessible fields and skip refetching unless the preflight records a specific unanswered field/source question or a requested original-image reinspection. A citation or search row alone is not a full receipt, but obtain a full receipt only when it answers a recorded gap. A reusable ID may remain in its original receipt file: verify its saved pointer and canonical/public mapping instead of copying it into the current capture list. Keep capture-ledger counts distinct from reviewed query rows and whole-catalogue totals. Screening or skipping an ID still advances coverage; classify it as first-seen, newly integrated, duplicate/reused, held or out-of-scope rather than calling it “new” by default. For IDs not yet known from saved rows/receipts, capture only the search-result rows first, then preflight those IDs before opening any transcript/detail page.
3. Reuse the logged-in browser through currently available supported controls. Inventory the current connection after interruptions; browser/tab IDs and REPL bindings are ephemeral. Preserve personal tabs. Do not start a new browser, profile or session to recover a missing handle. Reuse existing local project services where applicable; do not start a duplicate service for file/API checks.
4. Capture the actual search URL/criteria, displayed count, page number and result rows. Record ranges and exclusions explicitly. A birth-filtered BMD query alone does not cover earlier births, variants, other categories or later-life records lacking birth fields. Raw result counts include duplicates and potentially out-of-scope identities. Stop repeating a no-hit query unless a new discriminator changes the search.
5. After row-ID preflight, use the single working tab only for unresolved gaps. Open observed transcript/image links and save a durable receipt before navigating again: provider ID, requested/final URL, access status, capture time, literal labelled fields and source level. Keep interpretation separately from the literal field map. If packing/unpacking fields to reduce context, verify the transfer checksum and retain the original serialization specification; it is not proof of source authenticity.
6. Reconcile dispositions as each documentary group is screened. Do not append a page twice or rerun an append-only temporary script. Save partial progress on interruption. Do not retry authentication, subscription or CAPTCHA problems as a navigation loop; retain the actual access disposition.

At no more than ten navigations (or five applications), on errors/interruptions and before handoff, inventory owned tabs, render processes and memory pressure. Close owned temporary resources when finished; a retained handoff needs a concrete next action. Use `try/finally` for explicitly launched contexts/renderers, release large arrays and reset idle task runtimes when safe. Tab closure alone does not prove that a process/window or RAM was reclaimed. Never use blanket process kills.

## Reconcile each documentary group

Use the row-ID preflight before detail navigation, then check the existing catalogue, maintained person findings, source IDs and bounded reviewed-note searches for unresolved questions. Validate IDs against actual public dossiers: the same numeric suffix can belong to different surnames. Do not repeat a QMD/search lookup already completed for the same unchanged inputs; rerun only when a relevant source/person dependency changed or a new discriminator warrants it.

Use combined name, chronology, parish/residence, occupation, named family and life-course evidence. Check actual current vital fields before describing an existing date as a bound: a findings note may distinguish baptism while the imported model still carries an exact birthday. Qualify that inherited claim explicitly; do not silently treat the note as an already applied vital correction. Distinguish a named parent in a transcript from identification with a particular adult profile. Review mothers independently. A new record does not automatically raise the existing father percentage.

Apply the birth cutoff to each relevant recorded person, not only the search-result subject. A later-born child's entry may supply evidence for an eligible Glasgow parent. Retain such records for secondary-role review rather than classifying the whole record as excluded from the child's birth year alone; do not infer an adult-profile identity merely from a parent name.

Retain explicit dispositions in the existing matching review:

- **Matched existing subject:** evidence identifies the existing child/event; keep independently supported birth and baptism roles distinct.
- **Candidate comparison:** retain the possible existing person and actual reason/limits; do not assign their dates, parents or military service from an unresolved index.
- **Identity/natal-surname HOLD:** retain the indexed source and unresolved question without inventing a person. A source-only record may remain unassigned.
- **New-person proposal:** only after documented concrete exclusions. Prepare one consolidated, complete sourced draft using the project's normal creation workflow and supported family context.

For reviewed creations use `tools/queue_catalogue_creations.py --catalogue-id <id>` selection; preflight before applying. Do not globally replay unrelated creation cases to publish one held account.

For a stale duplicate case, preserve the exact provider-ID evidence in the maintained Findmypast integration override and reviewed profile link. Use `tools/reconcile_catalogue_profile_links.py --catalogue-id <id>` dry-run, then `--write` when the match is established. Withdraw stale READY/new-person wording in the audit, plans, original draft and register. Preserve genuine outstanding amendments and the retired redirect; do not delete that history or count reconciliation as a new discovery.

## Maintain the shared account

Use existing records, cases and schemas, not a parallel person registry:

| Input | Role |
|---|---|
| Existing Findmypast capture and matching review | Literal receipts, groups, candidates, surname/access qualifications and remaining coverage |
| `research/canonical_records.json` | Reviewed documentary assertions, source URL, event year/place/country, qualified profile roles and provenance |
| `research/<ID>/findings.md` | One current conclusion plus cited findings, identity limits and next questions |
| `research/vital_assessments.json` | Explicit approved vital correction and catalogue/tree projections, preserving prior/imported evidence |
| `research/queue-review-2026-10-17/catalogue-integration.json` | Complete current proposals and genuine pending amendments |
| `tools/study_stories/` and relevant person `presentation.json` | Cohesive current studies and overviews; update superseded summaries |
| `research/latest-findings.json` | Dated discoveries/corrections linked to checked subjects/candidates and original sources |

Findings about one person belong in that person's account, cross-referenced from relatives. Use checked local destinations for canonical profile roles. If a named relative has only an external WikiTree profile, cite that checked link and explain the role without fabricating a local destination. Synchronize only changed source/person surfaces, in this order: reviewed record ingestion, affected person/source findings, latest findings, affected study, then backlinks. Coverage-only or skipped-held-record updates do not trigger site builds.

For a vital correction, update the approved current model and complete proposed biography, preserve distinct event dates, and queue the exact field action. Preserve unrelated life events, citations and relationship assessments. A revised biography can invalidate a preservation-review hash: compare the complete captured and revised texts, record justified retained/superseded content, then refresh the review. Never merely bless a new hash or bypass the guard.

Before an expensive synchronization, validate each changed preservation review against the loader's normalized complete proposal, including restored references and stripped boundary whitespace; the raw draft-file hash can differ. Account for normalization changes and source preservation as well as the substantive edit.

A newly established date can invalidate an earlier newspaper or other identity comparison. Reconcile its maintained review, subject draft, current findings, study and queued wording; retain the previous dated assessment as superseded history. Do not erase competing candidates or extend the exclusion to a different later event without evidence.

## Guarded record publication

`tools/ingest_canonical_records.py` reuses provider/source identities and supports source-only records. Preflight explicitly selected reviewed records, then apply:

```sh
PYTHONPATH=. .venv/bin/python tools/ingest_canonical_records.py --record-id <canonical-record-id>
PYTHONPATH=. .venv/bin/python tools/ingest_canonical_records.py --record-id <canonical-record-id> --apply
```

Repeat `--record-id` for a batch, or use a deliberately reviewed `--source-file` selection. `publish_to_record_index=true` opts a canonical row into reviewed replay. The ingester does not itself decide a person's identity or authorize vital/relationship changes.

Review literal country/place conflicts explicitly. The Glasgow surname is not a Scottish-location signal. Age-derived and baptism-derived years need their real roles. Preserve both indexed values when unresolved.

For a historically bounded receipt without an event date, use `year: null`, `date_status: "undated"`, a clear display label, and a cited `historical_basis` with an explanation and either `latest_event_year <= 1900` or an independently proved historical birth bound. A register or collection span can establish that bound; never turn its first year into the person's event year. Without a defensible bound, retain a scope HOLD without publishing potentially modern details.

When enriching an existing canonical row, preserve its maintained place, source title and other substantive fields when the reused receipt is blank, a dash or less specific. Keep the literal blank separately from the reviewed account; do not erase an established location while reusing its record ID. Qualify actual conflicting readings explicitly.

Follow `docs/website-research-sync.md` for targeted synchronization. Relevant maintained entry points include:

- `tools/sync_catalogue_research.py --write <IDs>` for findings, proposals, public person accounts and browser search derivatives.
- `tools.build_study_pages.repair({<affected-study-ids>})` and `tools.build_latest_findings.repair()` for current studies, dated findings and complete subject drafts.
- `tools.publish_newspaper_review.repair()` when an existing newspaper identity review changes.
- `tools.build_backlinks.write_index()` for reciprocal subject/study/source links.
- `tools.catalogue_search_index.refresh()` for fast search, detail shards and worker; `tools.site_search.install_search()` for shared search.
- `tools.site_sitemap.build_sitemap()` for approved XML routes and the reader `/sitemap/`.

Use the approved assessment resolver/projection for vital fields. Verify both standalone and main packed tree displays when dates change; do not rebuild family topology from unrelated pending research. Avoid a full catalogue/site rebuild for a small batch. Complete content first, then refresh data-version manifests and settle asset stamps once. With concurrent writers, inspect changed dependencies; do not restart completed builds or overwrite another task's changes blindly. Prefer atomic writes for regenerated artifacts.

## Verify before committing

Derive assertions from actual current schemas and the selected scope; use no hardcoded retired-alias abbreviations, assumed date formats or old result counts.

- For newly ingested or changed provider IDs, verify the public index/source mapping and inspect actual source-reader content: nonempty HTML, one main heading, correct provider link and visible HOLD/identity limits where applicable. File existence and an index entry are insufficient. Recheck prior records only when a changed shared source/person/rendering dependency affects them. Recover an empty reader from approved maintained metadata or the preserved original; never overwrite an unrelated authored account with a generic shell.
- When search/index/vital data changed, compare affected full, fast and hydrated detail rows and the relevant `has_profile`, `missing_profile` and `needs_wikitree_update` memberships/counts. Do not rerun a global index check for unchanged dependencies. Open one representative affected UI flow when needed; a text search can also return people who mention the queried ID.
- Verify complete current/proposed/diff views and the actual outstanding amendment. Retired duplicate stubs must resolve to the established profile and disappear as active people, while remaining inspectable as history.
- For added/changed routes, verify source routes in approved XML and the relevant source-directory entries. The human `/sitemap/` intentionally links directories rather than listing every individual person/source. Run one final selected-batch or corpus-wide consistency gate when appropriate, rather than repeating it after each unchanged batch.
- Run the publication gate after findings/register/queue changes and `make check-links`. A successful selected `sync_catalogue_research.py --write <IDs>` already invokes `check_research_publication` for those IDs: retain its log, confirm the reported subject count and reuse that result when those inputs remain unchanged. Otherwise run `tools/check_research_publication.py --id <IDs>`. Use one `--id` followed by all selected IDs; repeating the flag checks only the last selection. Fix caused failures; distinguish existing baselines and non-gated anchor reports. Record material unverified behavior honestly.
- Verify unchanged relationship topology/grades when the batch only adds sources or refines dates. Distinguish new transcript captures, derivative-image inspections and original-record inspections, and new relationships from confirmations.

Commit coherent verified work with a Conventional Commit; do not push. Stage selected JSON entries or hunks when shared files have concurrent changes. Keep unrelated source edits, styling, personal files and temporary captures out of the commit. Inventory task resources again and leave no owned browser/render/scanner work running after completion.

The handoff should identify the committed batch, local-site state, held questions, exact next search step and coverage still outstanding. Do not claim live publication or mark the full audit complete from a passing batch verifier.
