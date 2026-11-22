# Research-entry integrity gates

For bounded model extraction and machine-readable review without database writes,
see [the proposal-only batch controller](research-batch-controller.md).

These checks prevent structural mistakes. They do not prove a source reading,
identify a historical person or authenticate a reviewer's identity. Substantive
identity, relationship and hold-release decisions still need evidence review.

## Creation identities

`tools/research_integrity.py` validates the complete creation registry before a
targeted or full catalogue update, and inside `Documents.store_document`'s write
transaction. One canonical `subject_id` cannot own multiple unreconciled
creation accounts. Case and surrounding whitespace do not create distinct IDs.
Only explicit workbench merges reconcile aliases; names never do.

Use the existing canonical account. When identity really changes, record the
reviewed reversible workbench merge before regenerating its views. Do not change
an ID to avoid a validation failure. Creation-row storage now follows account
identity rather than list position, including after a reorder.

## Releasing a hold

The document writer protects held creation accounts, identity-review rows and
blocked/parked research-plan questions. Removing or renaming the row is not a
way to resolve it. A held question must retain its list position because the
legacy native question adapter still uses positional IDs.

A transition out of a held state must carry `hold_release` in the proposed row:

```json
{
  "hold_release": {
    "previous_row_sha256": "SHA256_OF_THE_EXACT_PREVIOUS_ROW",
    "condition": "Inspect the original register year heading.",
    "decision": "satisfied",
    "reason": "Explain the inspected evidence and how it answers this condition.",
    "reviewed_by": "reviewer identifier",
    "evidence": [
      {
        "record_id": "NATIVE_WORKBENCH_RECORD_ID",
        "revision": 2,
        "locator": "image 4, year heading"
      }
    ]
  }
}
```

This is a template, not an applicable research decision. Obtain the previous
row from the authoritative document using `Documents` on
`open_project(project_path, readonly=True)`. Compute its digest with
`tools.research_integrity.row_sha256(previous_row)` and copy
`hold_condition(previous_row)` exactly. The condition uses `hold_condition`,
`resume_condition`, `assessment`, or `question`, in that order; a legacy row
with none of these falls back to its held status. The hash binds the review to
all the previous row's details, not just this condition label.

The evidence must name existing native record IDs, their current revisions and
exact locators. `decision` may instead be `superseded` when the review explains,
with evidence, why the old test is no longer appropriate. Merely having no
profile match is not satisfaction of an original-source inspection condition.

Record the updated document through the existing revision-checked entry tool:

```sh
.venv/bin/python tools/research_entry.py document PATH --show
.venv/bin/python tools/research_entry.py document PATH --expected-revision N \
  --actor REVIEWER --reason "Evidence-backed hold review"
```

The gates run before row changes, inside the transaction. Missing/stale record
evidence or an outdated held-row hash rejects the document. The catalogue
publisher also refuses a hand-edited ready status while the authoritative
creation document still holds that account.

These guards belong to the project document APIs. They do not restrict arbitrary
SQLite access or generic low-level workbench table updates; workers must use the
supported document entry path, not edit `document_row` metadata or question
tables through generic proposals. First-time legacy ingestion preserves its
initial statuses; it does not retroactively certify old hold releases.

## FamilySearch crosswalks

`tools/sync_familysearch_links.py` first applies each catalogue ID's ordered TSV
corrections/withdrawals, then validates the resulting complete map. A PID shared
by unresolved canonical people fails before output creation. A conventional
`data/familysearch/person-links.json` path reads its existing workbench merge
context read-only; custom paths require explicitly supplied canonical aliases.
There is no name-based reconciliation or blanket grandfathering of old conflicts.

The conventional public crosswalk is projected from the privacy-filtered
`www/data/people.json` export. It includes individually represented people,
including record-defined people without a WikiTree profile. A multi-profile
row requires an authoritative merge into one identity. Missing, withheld,
or likely-living identities stay in the local review TSV. A verified alias
that no longer has its own published row stays private while its published
canonical person's reviewed link remains available. If the people export is
unavailable, the sync leaves the existing public crosswalk in place.

The person-page, catalogue-search and notables readers validate pre-existing
JSON too, including malformed or duplicate keys. Validation snapshots are cached
and invalidated by crosswalk/configuration/database/WAL changes. This is a
consumer precondition, not an atomic whole-site build or a live FamilySearch
write authorization. Resolve existing conflicts through evidence review rather
than suppressing the guard; already generated pages are not changed by these checks.

An empty SQLite WAL can acquire new filesystem metadata during a read-only
connection. It contains no data frames and does not invalidate the snapshot;
nonempty WAL changes and checkpointed database changes still invalidate it.

## Withdrawing an incorrectly attributed public record

Record the correction through the revision-checked canonical-record entry API.
For an explicit public withdrawal, retain the record and its provenance, set
`publish_to_record_index` to `false`, and supply a specific
`publication_withdrawal_reason`. `tools.withdraw_canonical_records.apply` removes
that exact source entry from public record/event chronology and retains neutral
notices at the old record/source routes. The normal `publish_reviewed` replay
also reapplies these withdrawals after broader generators.

This bounded path refuses mixed sources, unrelated entries and non-generated
claims. Those need a separately reviewed source reconciliation. A missing date
must not be repaired by borrowing another child's date or a candidate profile's
birth year. Original evidence and earlier interpretations remain in the
authoritative research history, not in a stale public chronology.

## Focused regression checks

All new cases use fictional data and temporary databases/directories:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest \
  tests.test_research_integrity \
  tests.test_workbench_documents \
  tests.test_queue_catalogue_creations \
  tests.test_sync_familysearch_links \
  tests.test_workbench_migration \
  tests.test_research_entry_regeneration
```
