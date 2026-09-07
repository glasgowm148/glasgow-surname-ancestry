# Findmypast Glasgow catalogue integration overrides

The materializer reads `catalogue-integration-overrides.json`. Keys in
`groups` must be exact `group_id` values from `audit-distinct-people.json`.
Unknown keys, invalid targets, unsafe pre-1500 outcomes, incomplete scrape
reconciliation, missing WikiTree audits, conflicting matches, and handoff-path
collisions make `--apply` fail before catalogue files are changed.

An override replaces the automated integration decision; it does not change
the underlying transcript, surname, date, or grouping verdict.

```json
{
  "schema_version": 1,
  "groups": {
    "fmp-glasgow-example": {
      "outcome": "existing_profile",
      "profile_id": "Glasgow-123",
      "notes": "Exact date, place and named-relative bridge."
    },
    "fmp-glasgow-example-2": {
      "outcome": "new_person",
      "creation_status": "HOLD",
      "handoff_path": "surname-research/new-people/1650_Scotland_Edinburgh_Jane_Glasgow.md",
      "notes": "Candidate remains unresolved."
    },
    "fmp-glasgow-example-3": {
      "outcome": "free_space",
      "creation_status": "HOLD",
      "handoff_path": "surname-research/free-space-pages/Findmypast_1400_Scotland_Glasgow_John_Glasgow.md",
      "notes": "Pre-1500 documentary subject; never a person-profile draft."
    }
  }
}
```

Allowed outcomes:

- `existing_profile`: requires a syntactically valid `profile_id`.
- `new_person`: post-1500 only; requires `creation_status` `READY` or `HOLD`.
- `free_space`: requires `creation_status` `READY` or `HOLD`; this is the only
  allowed unmatched pre-1500 workflow.

`handoff_path` is optional. If supplied it must remain inside the appropriate
project directory. `notes` is optional but recommended for every judgment.

Run without arguments to refresh the provisional plan only:

```sh
.venv/bin/python tools/materialize_findmypast_glasgow_catalogue.py
```

After the source audit is fully reconciled, every person group has a complete
live WikiTree match audit, and human overrides are final, apply once with:

```sh
.venv/bin/python tools/materialize_findmypast_glasgow_catalogue.py --apply
```

The apply step owns only rows marked with source type
`findmypast-glasgow-surname-audit` or stable supplement IDs beginning
`fmp-glasgow-`, exact Findmypast URLs belonging to audited groups, bounded
generated sections, and `record-fmp-glasgow-*` entries in
`data/wikitree/catalogue-profile-audit.json`. It leaves unrelated content in
shared files and hand-edited drafts intact.
