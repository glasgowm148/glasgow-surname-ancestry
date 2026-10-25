# Glasgow on the research database

Status checkpoint, 25 October 2026. Branch `feat/workbench-sqlite-migration`
(Glasgow) with workbench branch `feat/sqlite-research-core` (0.9.0). Nothing is
pushed, published or deployed.

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
| Canonical records, record mentions, attributions | database (migrated); legacy file still read by builders | Mentions exist independently of identification; attributions are identity claims. |
| Vital assessments, latest findings, research plans, parent candidates, presentation questions | database (migrated); legacy files still read by builders | Re-run `make migrate-workbench` after editing a legacy file: it catches up. |
| WikiTree captures, OneTree exports | database observations + original files by hash | Observations are never edited; refresh adds a new one. |
| Update queue, queue reviews and overrides | database proposals (migrated); legacy queue still read | Authored workflow state kept verbatim in each proposal. |
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

## Everyday commands

```sh
# Inspect and reassess (ids accept SYSTEM:VALUE)
.venv/bin/genealogy --project . history glasgow-assertion:C-coverage-20261022b-glascow-14-father
.venv/bin/genealogy --project . assess glasgow-assertion:C-… --expected-revision 3 --status probable \
    --grade probable --estimate 80 --reasoning "…" --assessed-on 2026-10-26 --basis currituck-william-glasgow-will-1805
make research-views                      # regenerate the two relationship registries
.venv/bin/genealogy --project . show wikitree:Glasgow-951
.venv/bin/genealogy --project . review list

make migrate-workbench                   # catch up after editing a legacy registry
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

## Merging this branch (owner)

Research continued on `main` during the migration. After merging:

1. `git submodule update --init` and install the workbench (see
   `docs/toolkit-dependency.md`; push the workbench branch first).
2. `make migrate-workbench` in the merged checkout: later legacy edits are
   loaded as new batches and assessment revisions.
3. `make research-views` and commit the regenerated registries (if `main`
   edited them, take `main`'s version in the merge, then regenerate).
4. `make check-workbench`.

## Not yet moved (precise remaining work)

- The specialised Glasgow builders (`tools/build_research_catalog.py` and about
  190 other scripts) still read the legacy registries and earlier `www/` output.
  They now receive relationship data generated from the database, but they are
  not yet rewritten as views over the database or the shared compiler. Until
  they are, `www/` remains the published site and the legacy registries other
  than the two relationship files are still edited directly and caught up with
  `make migrate-workbench`. Next action: move one builder at a time to read
  `genealogy.store.projection.public_case` (start with
  `tools/catalogue_machine_data.py`, the main reader of the assessments), then
  make each remaining registry a generated view as was done for the relationship
  files.
- `build/workbench-site` (the shared compiler's build of Glasgow's public
  projection: 4,431 people, 4,888 files, 88 s, byte-identical across rebuilds
  and hash seeds) is a generic reader view, not a replacement for the Glasgow
  site. It publishes less than `www/`: OneTree tree facts were imported without
  a publication review (Glasgow's privacy levels 35/40/50+ are not yet mapped to
  projection rules), so only catalogue people, approved assessments, approved
  vital assessments, findings and records appear; prose naming a withheld
  person is omitted (27,938 omissions, listed in the private build report).
  Mapping Glasgow's privacy policy onto publication decisions is an owner
  decision and has not been made automatically.
- `tmp/` (22.7 GB of scratch, 255,478 files) was not migrated; it may contain
  unreviewed leads and should be reviewed by the owner before clean-up.
- WikiTree remote baselines: captures are observations, but no capture is yet
  marked as the accepted baseline, so three-way comparisons for the queue need
  `genealogy wikitree capture --accept-baseline` per profile when next reviewed.
