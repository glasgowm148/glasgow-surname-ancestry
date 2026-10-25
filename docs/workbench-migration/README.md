# Glasgow on the research database

Status checkpoint, 25 October 2026. Branch `feat/workbench-sqlite-migration`
(Glasgow) with workbench branch `feat/sqlite-research-core` (0.9.0). Both are
fast-forwarded into `main` (25 October 2026); the workbench pin `cd5c605` is the
workbench's `main`. Nothing is tagged, published or deployed. The research
database was created in the main checkout (`data/private/workbench/`), where the
baseline archive and the earlier migration backups (`backups/worktree-*`) now
also live.

## Architecture and ownership

| Concern | Owner | Where |
| --- | --- | --- |
| Domain model, SQLite schema and migrations, services, validation, audit, concurrency | genealogy-research-workbench | `genealogy.store` |
| Imports (GEDCOM, OneTree), native export/import, backup/restore, GEDCOM 7/5.5.1 export | workbench | `genealogy import`, `native`, `backup`, `gedcom` |
| Public projection, staged site compiler, default theme | workbench | `genealogy.store.projection`, `genealogy build` |
| WikiTree three-way comparison and proposals (no live writes) | workbench | `genealogy wikitree`, `genealogy proposal` |
| Glasgow research, conclusions and evidence | Glasgow | the database `data/private/workbench/glasgow.sqlite` and the files it references |
| Glasgow configuration, branding, editorial presentation, approvals | Glasgow | `genealogy.toml`, `tools/study_stories/`, approval manifests (now also rows in the database) |
| Legacy registry adapter (reads Glasgow's JSON formats) | Glasgow | `tools/workbench_migrate.py` (writes only through workbench services) |
| Generated compatibility views for the existing builders | Glasgow | `tools/workbench_legacy_views.py` |
| Specialised Glasgow site builders (`tools/build_*.py`, `repair_*`, `publish_*`) | Glasgow, **legacy** | read the legacy registries and `www/`; see "Not yet moved" |

Glasgow depends on the workbench as a package (`requirements/toolkit.txt`, the
submodule pin); no workbench code is copied into this repository.

## Authority for each kind of data

| Data | Authority after this change | Notes |
| --- | --- | --- |
| Relationship claims, assessments, revisions, estimates | **database** | Both legacy JSON files are generated views (`make research-views`); `make check-workbench-views` fails on hand edits. |
| People, external ids, former ids, redirects, routes | database (migrated) | WikiTree ids map to opaque person ids; 79 redirects and catalogue routes kept. |
| Canonical records, record mentions, attributions | **database**; `research/canonical_records.json` is a generated view | Mentions exist independently of identification; attributions are identity claims. Record with `tools/research_entry.py upsert record`. |
| Latest findings, vital assessments | **database**; `research/latest-findings.json` and `research/vital_assessments.json` are generated views | Record with `tools/research_entry.py upsert finding|vital`. |
| Research plans, parent candidates, the update queue and its review files | **database**, row by row; the files are generated views | Edit the file, then `tools/research_entry.py document PATH --expected-revision N`. Removed rows are kept, marked removed. |
| Presentation files, findings logs, briefs, drafts | files (editorial), referenced by hash | Questions extracted from presentation files follow them through `make migrate-workbench`. |
| WikiTree captures, OneTree exports | database observations + original files by hash | Observations are never edited; refresh adds a new one. |
| Update queue, queue reviews and overrides | **database** (proposals and review rows) | See the row above. |
| Exact-file publication approvals | database approval rows (migrated) + the three manifests | Hash-scoped: changed bytes lose the approval. |
| Research prose, drafts, captures, images, PDFs | files, referenced by hash | 21,213 asset rows; originals never copied or changed. |
| `www/` | generated output (legacy builders) | 9,791 retained `www/people/*.json` dossiers and `www/map/data/` are referenced as retained input until their builders are moved. |

## Migration results (source commit `bf42d127d21c`)

- **Inventory**: 103,136 files classified by category, access and disposition;
  large scratch, cache, archive and release directories summarised (see
  `inventory-summary.md` for public-safe counts). The private inventory and
  ledger are in `data/private/workbench/`.
- **Baseline backup**: every local-only (ignored or untracked) input, 12,948
  files, 1.67 GB, `data/private/workbench/baseline-backup/`, each archive member
  verified against its SHA-256. Tracked inputs are preserved by the commit.
  Raw DNA sequence files and the `.env` secret are deliberately not included.
- **Coverage ledger**: 0 uncovered inputs, 0 changed since the inventory.
  Dispositions: imported into structured research, retained as referenced
  evidence or prose, replaced by a reproducible derivative (`www/`), preserved as
  unresolved legacy information, or explicitly excluded with a reason
  (`coverage-summary.md`).
- **Database** (counts): 6,515 people (4,869 public catalogue people with 4,872
  catalogue routes; 123 record-defined people), 20,485 external-id mappings
  (including 79 redirects), 14,792 claims (7,406 relationship claims, 2,835
  identity claims for record mentions), 5,427 assessments with 6,833 revisions,
  2,111 records, 2,835 mentions, 7,888 events, 1,111 findings, 1,114 questions,
  41 searches, 15 parent hypotheses, 24 studies, 1,485 proposals, 83 approvals,
  12,884 external observations, 21,213 assets, 636 legacy items: 372 values
  that differ between the four OneTree exports (the newest export is kept, the
  older values preserved), 217 completed live updates without a proposal
  record, 27 authored draft-replacement decisions and 20 ambiguous gazetteer
  names.
- **Repeatability**: a second run against the same inputs changes no row.

### Relationship estimate reconciliation

`relationship_probability_estimates.json` had 30 pair-level disagreements. Each
was resolved by the assessment record's own history, never by file order,
largest value or timestamp alone:

- 29 rows were reverse (or duplicate) views still showing an **earlier
  revision**: the assessment's `assessment_history` contains that value. The
  database keeps the earlier value as history; both directions now derive from
  the current assessment. Example: `C-coverage-20261022b-glascow-14-father` is
  95% (proved, 2026-10-23) in both directions, with 44% (possible, 2026-10-22)
  as revision 2.
- 1 row (`C-role-20261018-glenleslie-hugh-robert-brothers`, father 17%) is a
  **different proposition** filed under a brothers assertion (74%). It is its
  own claim and assessment, linked as dependent on the brothers claim and
  flagged in the review queue (`genealogy review list`).
- 285 assessments had no percentage of their own while their estimate rows
  agreed on one value; that value was adopted as the assessment's estimate with
  its source recorded. No estimate was invented or averaged.

The regenerated `relationship_assessments.json` is byte-identical to the input;
the regenerated estimates file differs only in those 29 rows (`percent`,
`assessment_status`, and the earlier value appended to `assessment_history`).

## Generated registries and the entry tool (26 October 2026)

Five registries are now generated from the database and byte-identical to the
files they replaced: the two relationship files, `canonical_records.json`,
`latest-findings.json` and `vital_assessments.json`. Changes go through
`genealogy assess` (relationships) or `tools/research_entry.py` (the other
three), which takes one row in the file's own format, checks the revision you
read, writes through the audited store and regenerates the file. A hand edit to
any generated registry is refused: `make migrate-workbench` keeps it as a
conflict without applying it and `make check-workbench-views` fails. Research
plans, parent candidates, presentation files and the update queue remain
edited legacy inputs that the migration catches up.

The latest capture of each queued WikiTree profile is now its observed remote
baseline (1,481 of 1,485; four have no capture), so `genealogy wikitree compare`
has a baseline to compare against.

## Documents held row by row (26 October 2026)

All 285 research plans, parent-candidate lists, the update queue and its two
review files are held in the database: each row on its question, search,
finding, hypothesis or proposal (or a row note where the core has no model),
the rest of each file as a frame with a document revision. Regenerated, all 290
generated files match the originals in content; 279 are byte-identical and 11
research plans whose hand-mixed formatting no serialiser reproduces are
normalised once (same content). An edited file is recorded with
`tools/research_entry.py document`; a hand edit that is not recorded is kept as a
conflict by `make migrate-workbench` and fails `make check-workbench-views`.

## Everyday commands

```sh
# Inspect and reassess (ids accept SYSTEM:VALUE)
.venv/bin/genealogy --project . history glasgow-assertion:C-coverage-20261022b-glascow-14-father
.venv/bin/genealogy --project . assess glasgow-assertion:C-… --expected-revision 3 --status probable \
    --grade probable --estimate 80 --reasoning "…" --assessed-on 2026-10-26 --basis currituck-william-glasgow-will-1805
make research-views                      # regenerate the two relationship registries
.venv/bin/genealogy --project . show wikitree:Glasgow-951
.venv/bin/genealogy --project . review list

.venv/bin/python tools/research_entry.py show finding <id>          # current row and revision
.venv/bin/python tools/research_entry.py upsert finding row.json --expected-revision N
.venv/bin/python tools/research_entry.py document research/<ID>/research_plan.json --show
.venv/bin/python tools/research_entry.py document research/<ID>/research_plan.json --expected-revision N
make migrate-workbench                   # pick up new case files and presentation changes
make check-workbench                     # private-data verification (fails without the database)
make backup-workbench                    # verified backup of the database and its own files
make build-workbench-site                # the public projection through the shared compiler
```

## Backups made

- `data/private/workbench/baseline-backup/glasgow-local-inputs-20261025T115352+0000.tar.gz`
  (+ `.manifest.json`): the local-only inputs before migration, verified member by member.
- `data/private/workbench/backups/20261025-post-migration/`: workbench backup of the
  database (logical digest `d3d505a5a52a…`), restored into a fresh directory and
  validated (integrity ok, no broken references, every one of 21,209 hash-referenced
  research files verified against the checkout).

- `data/private/workbench/backups/20261025-after-catch-up-fix/`: the same database
  after the catch-up fix (logical digest `621e6cc19c85…`), verified.

## Recovery

- Database lost or damaged: `.venv/bin/genealogy backup restore <backup> <new-dir>`
  for a workbench backup, or rebuild it from the legacy files with
  `make migrate-workbench` (deterministic; the legacy inputs remain in Git and
  in the baseline archive).
- Local-only inputs lost: extract `data/private/workbench/baseline-backup/glasgow-local-inputs-*.tar.gz`
  (verify first with `tools/workbench_inventory.py verify <archive>`).
- Undo the cutover: revert the branch's commits; the original registries are in
  commit `bf42d127d21c`. The database can be deleted and rebuilt at any time
  before further research is recorded in it.

## Merge status (26 October 2026)

Everything is on `main` in both repositories, and no uncommitted work remains in
either main checkout. The edits another agent had left uncommitted on 25 October
(the workbench's tree workspace and sidebar wordmark, and the matching
`toolkit_research_case.py` change) were committed unchanged apart from merging
both changelog lists, after checking that every pending change is contained in
the committed files (patch backups were kept). The Glasgow pin is workbench
`e76c624`.

## Merging a later change from `main` (owner)

Research continued on `main` during the migration. After merging:

1. Merge the workbench branch into its `main` first (moving the pin if that
   creates a new commit), then `git submodule update --init` and install the
   workbench (see `docs/toolkit-dependency.md`).
2. `make migrate-workbench` in the merged checkout. Each changed legacy item is
   caught up: an edited record, finding, vital assessment, plan item or queue
   entry updates its row (audited, revision-checked); a changed relationship
   assessment becomes a new revision and the stored legacy row follows it. A row
   that was also edited in the database is never overwritten: the incoming
   version is kept as a `legacy_item` conflict for review, and a hand edit to a
   generated relationship registry after a database reassessment is refused the
   same way.
3. `make research-views` and commit the regenerated registries (if `main`
   edited them, take `main`'s version in the merge, then regenerate).
4. `make check-workbench`.

## Scratch review (`tmp/`, 26 October 2026)

`tools/workbench_scratch_review.py` hashed every file in `tmp/` (22.7 GB) except
release-bundle archives and compared it with every hash the project already
holds. Everything that exists nowhere else is listed in the private report
`data/private/workbench/scratch-review.json`. The unique research among it is
recorded in the database by hash, where it is (no copy: the disk had under 1 GB
free): 3,163 research notes, 432 evidence files (PDFs and images) and 10,085
JSON files, as private `scratch_lead` assets with one `scratch_review` note per
folder. They are leads, not evidence, until assessed. If `tmp/` is cleaned, they
show as missing in `genealogy db check` and the ledger, so nothing is lost
silently; `--preserve` copies them into managed storage when there is room.
About 48,000 further JSON files in `tmp/` are copies of files already kept under
`research/`. Not recorded, but listed: 175,096 HTML web captures, 4,477 code and
log files, 8 site-release snapshots (`.tar.gz`) and 1,038 browser or tool cache
files. Nothing in `tmp/` was changed or deleted.

## Site builders

The legacy builders' research inputs are now declared: `make build` and
`tools/rebuild_local_site.sh` begin by regenerating every registry from the
research database and installing the site inputs that no builder produces
(`data/site/declared-inputs.json`, `tools/site_declared_inputs.py`). What
remains is the pipeline's structure: 102 tools read or write `www/`, and 109
generated `www/` files are read by other builders as inputs, so the Glasgow site
still cannot be rebuilt from an empty `www/`. `builder-inputs.md` lists those
files with their readers and the order of the remaining work. Proving an
empty-output rebuild also needs about 3 GB of free disk for a second site tree.

## Not yet moved (precise remaining work)

- Restructuring the Glasgow site builders so they read only declared inputs
  (see `builder-inputs.md`). Until then `www/` remains the published site and is
  rebuilt in place.
- `build/workbench-site` remains a generic reader view built by the shared
  compiler, not a replacement for the Glasgow site.
