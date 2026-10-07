# Website-first research synchronization

## Contract

The website is the primary, current account of this project's research. Source
records and maintained repo files supply evidence and reproducible inputs; they
must not hold important conclusions that readers cannot discover on the site.
The website is not itself a primary historical source.

Research work is not complete until its public-safe results are visible in the
appropriate local `www/` pages and data. Synchronize after each coherent research
batch, including work performed by subagents or elsewhere in the repository.
Do not wait for a separate website-update request.

This is a required agent workflow, not a background file watcher. The current
builders do not automatically ingest every research document. A new research
format must be connected to the existing public model or given an appropriate
visible research section in the same task.

## Research-to-site handoff

1. Record the affected subjects, sources, conclusions, confidence changes and
   open questions in their maintained source files. Keep original citations and
   a dated account of material changes. Reconcile conflicting accounts using
   evidence and superseding findings, not whichever file was built last.
2. Identify every affected public surface: person dossier, records, family or
   locality study, early records, research groups, main questions, map, DNA or
   Timeline. Update overview claims as well as detailed dossiers.
3. Update the durable rendering inputs and synchronize the relevant pages and
   data. Do not apply only a generated HTML edit that the next repair will undo.
4. Read the result in its actual public context. Check affected links, filters
   and visible qualifications, and desktop/mobile layout where changed. A JSON
   field, repository file or link in a general directory is not a substitute for
   integrating a material finding into the relevant account.
5. Report what is synchronized locally, what has actually been published live,
   and any remaining blocker. Never label a local-only update as deployed.

## Current update paths

- Latest findings: record each substantive new concrete finding or supported
  correction in `research/latest-findings.json`, using its actual research
  discovery date, source citations, affected public people, assessment and
  remaining limits. Group a shared record across profiles into one finding.
  Exclude unsuccessful searches, speculative candidates and UI/build updates;
  never infer a discovery date from file modification time. Run
  `.venv/bin/python tools/build_latest_findings.py` after the affected dossiers
  or studies are synchronized. The release and catalogue research pipelines
  also rebuild `/latest-findings/`. The existing `/changes/` history remains
  available for website updates and broader case reviews.
  Every named subject must have a checked existing/candidate profile link or
  a complete sourced public draft after a proper duplicate check. Keep plausible
  matches unless concrete evidence conflicts; missing fields or missing extra
  corroboration alone do not rule them out. Consolidate compatible records and
  reuse existing drafts. For an actual uncertain/unknown-to-certain relationship
  change, record `relationship_changes` with the relationship, subject, relative,
  before/after status, explanation and internal `previous_status_provenance`.
  Do not count previously certain links or ordinary source confirmations.
  Synchronize and rebuild after every coherent batch; this remains an agent
  workflow rather than a background watcher.
  Consolidated public draft handoffs are maintained in
  `research/latest-findings-subjects/subjects.json`; the findings builder invokes
  `tools/build_research_subject_drafts.py` before validating links. Use
  `people[].draft_url` for an additional evidence draft alongside a directly
  linked candidate profile. Update any superseded unmatched assessment in its
  maintained record review and public study, retaining dated history.
  The findings builder also writes an Atom feed (`/latest-findings/feed.xml`),
  per-study pages (`/latest-findings/studies/<study-id>/`), a by-place page
  (`/latest-findings/places/`) and `www/data/findings-by-subject.json` (findings
  by person, study and place, newest first; read it with
  `build_latest_findings.findings_for`). Studies and places are derived from the
  people a finding links (study membership and the places those people are
  recorded at), so the ledger needs no study or place field. Rebuild study pages
  (`tools/build_study_pages.py`) after the findings builder so their "Latest
  findings about this study" blocks are current.

- Person findings: `research/<ID>/findings.md`. Keep one overall
  `## Current conclusion` current; dated or topic conclusions are additions to
  it. Every other `## ` section is published unless its heading marks an editing
  log (`FINDINGS_INTERNAL_HEADINGS` in `tools/build_research_catalog.py`); text
  above the first heading is not. Put a finding in the file of the person it is
  about and cross-reference it from the relatives it concerns. The builders read
  these into person HTML and JSON.
- Publication check: after any change to findings, the WikiTree register or the
  queue, run `make check-research` (or
  `.venv/bin/python tools/check_research_publication.py --id <ID> ...` for the
  profiles touched). It compares the maintained inputs with what the builders
  publish and exits 1 on a problem not in
  `data/site/research-publication-baseline.json`. Fix it, or record it on purpose
  with `--update-baseline --accept-new`; never call research published while it
  reports a new item. `--update-baseline` alone only removes fixed items. The
  release (`tools/publish_research_release.py`,
  `tools/check_release_consistency.py`) runs the same check. Check internal
  links with `make check-links`.
- Link index: `.venv/bin/python tools/build_backlinks.py` writes
  `www/data/person-links.json`, the "who links to whom" index: for each person
  the family and place studies, place pages, source pages, latest findings,
  research and WikiTree study pages, and other people's notes that mention them,
  plus the links between study pages and place pages. It reads built pages, so
  run it after the section builders (catalogue build, `build_study_pages.py`)
  and before person pages are rendered; it writes only when the content
  changes, and `--check` exits 0 when the index is current. It never reads
  `data/private/` and screens people exactly as the person pages do.
- Link check: `make check-links` runs `tools/check_internal_links.py --site www
  --baseline data/site/internal-link-baseline.json` over every built page
  (about 90 seconds). It groups broken internal links by cause, names the
  builder to fix and exits 1 only for a broken link not in the baseline; it is
  skipped until the baseline exists. Fix the cause in the builder, never in
  `www/`. `--update-baseline` only removes links that are fixed, and
  `--report <file.json>` writes the full list.
- Place pages: `.venv/bin/python tools/refresh_place_pages.py` runs only the
  place writer on the published records index and people file and puts each
  fresh `<main>` into the page already on the site (`--check` reports without
  writing). Use it after changing the place writer or the study and findings
  data it reads. It cannot add a record: the records index
  (`www/data/records-index.json`) is written only by the full catalogue build
  (see `docs/build-reproducibility.md`), so a correction to a record's person,
  date or place shows in the research text at once but in record lists only
  after that build.
- Targeted verification: `.venv/bin/python tools/sync_catalogue_research.py`
  compares every eligible case's current source sections with its rendered
  dossier and compares the maintained update queue with visible drafts and
  search flags. Use `--write` (optionally followed by profile IDs) to refresh
  reviewed content. A missing public case must be resolved through the curated
  `data/wikitree/research-catalogue-cases.json` inclusion/canonical/privacy
  manifest; `tools/add_research_case_dossiers.py` publishes included historical
  cases and their search/context entries. These tools never infer that every
  research file requires a WikiTree amendment.
- Full catalogue generation, when needed:
  `.venv/bin/python tools/build_family_map.py`. This is broader than a person
  update and regenerates several datasets and views. First reconcile manual
  public edits with maintained inputs. Preserve archival snapshots and restore
  the current unified presentation with the applicable repair helpers; never
  leave a full generation at an older site layout.
- Free-space directory: maintain `research/free-space-pages/index.json`, then
  `.venv/bin/python tools/build_free_space_site.py`. This publishes metadata and
  canonical links only. Findings in `surname-research/free-space-pages/*.md`
  also need a substantive public synthesis in the relevant dossier or study;
  indexing a page does not publish its body or a newly written draft.
- Research groups: update the evidence-led definitions and provenance in
  `tools/repair_research_groups.py`, then run that helper. Preserve the distinction
  between documented households, uncertain tree attachments and record networks.
- Main open questions: update `tools/repair_research_questions.py`, then run it.
  Add newly identified main workstreams, revise changed hypotheses, and remove or
  mark resolved questions. Do not restrict this list to user-supplied examples.
- Wills and testament transcriptions: update the maintained reading and its
  source/version metadata, then run `.venv/bin/python tools/build_transcriptions.py`
  to refresh `/research/transcriptions/`. Retain uncertain readings and clearly
  distinguish full saved text from review notes; never invent missing passages.
- Other views: update their maintained source and dedicated repair helper, not
  just a public copy. Map associations must retain source provenance and honest
  coordinate precision; DNA, Timeline and early-record summaries must reflect
  changed evidence where relevant.
- Irish civil-death lookup list: maintain
  `surname-research/indexes/irish-civil-deaths-1864-1900.csv` and its JSON
  provenance, then run `.venv/bin/python tools/publish_irish_death_index.py`.
  This adds the qualified lookup table to the Ireland family account and its
  discovery link to Sources. These unverified index leads are not catalogue
  people, confirmed matches or mapped record associations.
- Scottish OPR deaths and burials: maintain
  `surname-research/indexes/scotlandspeople-opr-deaths-to-1700.json`, then run
  `.venv/bin/python tools/publish_opr_death_review.py`. This renders the seven
  supplied entries, identity assessments and next searches in Scottish families
  with a Sources discovery link. Synchronize affected person findings and the
  explicit WikiTree update queue separately with the targeted sync tool above.
  Unidentified entries remain documentary leads; do not create people or assign
  exact death dates from an unresolved index match.
- Scottish OPR banns and marriages: maintain
  `surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json`, then run
  `.venv/bin/python tools/publish_opr_marriage_review.py`. This publishes all
  55 supplied rows with their matched profiles, provenance and qualifications
  in Scottish families, plus a Sources discovery link. Preserve reciprocal
  results as evidence rows without counting them as separate people or events.
  Synchronize person findings, complete drafts and update flags separately;
  combined collection dates do not automatically establish wedding dates.
- Scottish OPR births and baptisms: maintain
  `surname-research/indexes/scotlandspeople-opr-births-to-1700.json`, then run
  `.venv/bin/python tools/publish_opr_birth_review.py`. It adds all 127 supplied
  rows and their qualified identity assessments to Scottish families and Sources.
  Preserve unknown day/month values, the assumed-year warning, indexed gender
  and repeated references. Neither a shared reference nor a shared date alone
  establishes duplicate people or twins. Refresh affected findings and pending
  WikiTree drafts with the targeted person sync tool.
- Early newspaper review: maintain
  `surname-research/indexes/glasgow-newspaper-review.json`, then run
  `.venv/bin/python tools/publish_newspaper_review.py`. This publishes inspected
  passage readings, separately labelled relevant place-study notices, city/vessel exclusions and qualified profile candidates to
  the Sources newspaper collection and a linked Scottish-family summary. Keep full scans, browser context and OCR in ignored local captures; explicitly requested historical excerpts may be published only after visual checking and hash-pinned approval in `research/source-library/newspaper-clippings.json`;
  use stable original image links, never signed download URLs. Synchronize
  concrete surname findings, candidate accounts and held drafts separately.
  Count only inspected person-name passages as retained surname records;
  publish irrelevant place/vessel hits in a separate collapsed exclusion log. Relevant locality notices use `place study`, have their own visible table and count, and must never be counted as surname records. Report
  inspected hits, retained surname records and pending readings separately.
- Unified repair: `.venv/bin/python tools/repair_unified_site.py` restores the
  presentation and invokes its registered helpers and audit. It does not replace
  the catalogue builder or discover all new research. Use targeted helpers for
  narrow changes rather than running a broad pipeline unnecessarily.

For a new public page or research type, update its discovery routes and search
data as appropriate. Keep canonical subject IDs and links stable. Preserve
useful previous conclusions as explicitly superseded history, not competing
current statements.

Recovered-file scans keep inventories and audit handoffs internal. Integrate
their findings into the relevant existing person, family or subject accounts;
do not generate a standalone public audit page unless explicitly requested.

## Publication and privacy

Local `www/` is the publishable site, not proof that the hosted site has changed.
Deployment is currently manual; see `docs/public-catalogue-deployment.md`.
Research synchronization does not silently authorize a production deployment,
live WikiTree edit, paid access or publication of private material. If deployment
is authorized, use the established process and confirm the affected live pages.
If it is unavailable, explicitly report that the local site is updated but live
publication remains pending.

Exclude credentials, restricted captures, raw sensitive DNA data and private
living-person information. Incomplete research may be visible as an explicitly
labelled lead or open question with its evidence limits; never make a pending
identity or parentage look established merely to populate the website.

## Catalogue research views and historical confidence audit

The catalogue Table and Map use the same filtered profile set. Map points retain
their recorded precision; unmapped profiles and broad country locations must be
identified explicitly. Branch maps precede long research panels, and clicking
the map background dismisses previews. Profile comparisons retain aligned current
and replacement columns with red removals and green additions.

After each coherent research batch, run `tools/build_research_queue.py` alongside
latest-findings synchronization. It consolidates held OPR identities, public
subject drafts, older creation drafts, pending profile amendments and open
studies in `/catalogue/#research-queue`. Reconcile completed amendments and
superseded drafts; maintain `research/research-queue-overrides.json` for dated
source drafts whose recommendation has been superseded. Preserve the original
evidence and direct readers to the current subject account.

The requested 30 September historical audit is maintained in
`research/historical-relationship-audit-2026-09-30.json` and its Markdown report.
`tools/backfill_relationship_status_audit.py` preserves actual saved grades and
source provenance; `tools/build_relationship_audit.py` renders the public account
at `/research/relationship-audit/`. The reconciled ledger records 38 changes:
14 uncertain/unknown to certain and 24 previously ungraded to certain. These are
historical confidence reviews, not 38 new record discoveries. Already confident
relationships without a recoverable prior grade are excluded from this count.
Release finalization refreshes both the audit and central queue automatically.

### Sources collection organisation

`research/source-library/coverage.json` maintains source-type and jurisdiction guides with primary-repository citations. `tools/build_source_collections.py` derives country/year/type browsing from already-public source references, retains uncertain years and category overlap, and moves reviewed newspaper/parish/civil tables into their own Sources subpages. It preserves linked family conclusions and original-provider access. `research/source-library/legacy-collections/` retains the migrated GRONI public assessment; newly rendered branch audits refresh that maintained section before migration. The release finalizer rebuilds these pages after reviewed-collection publishers, so later releases keep the organisation. Counts describe local references and reviewed rows, never whole-archive coverage. Missing provider links are labelled, not invented. Rebuild with `.venv/bin/python -m tools.build_source_collections`, then run the normal release finalizer and checks.
