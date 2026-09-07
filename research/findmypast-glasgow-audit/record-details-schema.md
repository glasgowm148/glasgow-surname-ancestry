# Findmypast record-detail overlay schema

Save transcript/detail captures separately from immutable `raw-results-*.json`
files. The consolidator reads every `record-details*.json` file in this
directory and joins entries by exact Findmypast `record_id`.

```json
{
  "schema_version": 1,
  "capture_session": {
    "started_at": "2026-09-03T20:00:00Z",
    "completed_at": "2026-09-03T20:05:00Z"
  },
  "records": {
    "SCOT/WILLS/057431": {
      "access_status": "accessible",
      "captured_at": "2026-09-03T20:01:00Z",
      "url": "https://www.findmypast.co.uk/transcript?id=...",
      "title": "...",
      "transcript_fields": {
        "First name": "Geillis",
        "Last name": "Glasgow",
        "Year": "1603"
      },
      "transcript_text": "...",
      "image_url": "https://search.findmypast.co.uk/record?id=...",
      "surname_status": "confirmed",
      "review_reason": "The transcript gives Glasgow in the last-name field."
    }
  }
}
```

Use ISO-8601 UTC timestamps. Preserve field labels and text verbatim. Valid
`access_status` values should be `accessible`, `subscription_locked`,
`not_found`, or `error`; add an `access_note` for every status other than
`accessible`. Use `surname_status` only after full-record review:
`confirmed`, `false hit`, or `unresolved`. A false hit should state whether
Glasgow is a place, office, title, parish, diocese, or other descriptor in
`review_reason`.

A redirect to `steady-sherlock?limit=dailyLimit` is a temporary session-wide
fair-use block, not evidence that the individual record requires a
subscription. Retain schema-compatible `access_status: subscription_locked`,
add `block_reason: daily_limit`, preserve the redirect page and timestamp, and
exclude it from record-specific lock totals. Stop the batch at the first such
redirect and retry that frozen index after the daily allowance resets.

Multiple overlay files may contain the same ID only when their entry objects
are byte-for-byte equivalent after canonical JSON normalization. Conflicting
entries stop consolidation rather than silently replacing evidence.
