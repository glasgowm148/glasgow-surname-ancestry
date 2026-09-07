# Findmypast Glasgow surname result audit

**Status: SEARCHED GAP-FREE; INCOMPLETE ROW ACCESS.**

Derived from captures completed through `2026-09-03T21:20:18.520Z`. Target coverage is 1–1750 inclusive.

## Reconciliation

- Query windows: 61 (49 internally reconciled; 5 capped and superseded; 3 blocking).
- Non-blocking benchmark/control queries: 1 (page-cap limitations remain explicit).
- Partition-attempt mismatch diagnostics: 2 queries / 8 checks (values are non-additive and are not counted as inaccessible records).
- Displayed totals: 58728 across all queries; 17516 across reconciled analysis windows.
- Raw captured row occurrences: 26936; analysis occurrences after cap/supersession checks: 22016.
- Pagination-redirect occurrences preserved but excluded: 1780.
- Unique record IDs: 7208; missing-ID rows: 0.
- Duplicate IDs: 4965 (4498 occur across windows; 14808 repeat occurrences beyond the first).
- Result-action subscription-locked: 146 row occurrences / 20 unique IDs.
- Saved full/detail payloads beyond result rows: 1513; transcript actions: 2393; image actions: 263.
- Separate detail overlays: 646 IDs (646 matched; 0 orphaned); provisional candidates with overlays: 412.
- Record-specific subscription-locked detail overlays: 31 IDs.
- Temporary Findmypast daily-limit blocks awaiting retry: 127 IDs. Their immutable overlays retain schema-valid `access_status=subscription_locked`, but they are not record-specific subscription locks.
- Same-event duplicate group leads: 198.
- Provisional exact-display candidates after ID deduplication: 1052.
- All observed exact-display rows after ID deduplication, including anomaly/out-of-scope review classes: 1461.
- Capped-query result rows inaccessible beyond page 75: 3879 (not assumed empty or non-surname).
- Searched/category-accounted year gaps: []; overlaps: [[1701,1701],[1741,1741]].
- Fully captured/reconciled year gaps: [[1621,1750]]; overlaps: [].
- Displayed totals are per-query audit values; their sum is not a unique-record total when control or replacement windows overlap.

### Transcript-validation outcomes

- Observed exact-display record IDs: 1,461.
- Transcript-validated in-scope record IDs: 252.
- Conservative distinct documentary people: 233.
- Same-event duplicate groups: 16, comprising 35 record IDs.
- Rejected false hits: 19, including records where Glasgow is an office, see, institution, or place rather than the person's surname.
- Currently inaccessible or unreviewed exact-display IDs: 31 record-specific locks, 127 temporary daily-limit blocks, 9 detail errors, and 815 not yet attempted. A further 12 full-record surname verdicts remain unresolved.

These are audited outcomes for the accessible transcript subset, not a claim that every exact-display result has been resolved. The raw rows and rejected records remain preserved in the audit artifacts below.

| Covered years | Displayed | Valid pages / expected | Raw rows | Audit status | Query |
|---|---:|---:|---:|---|---|
| 1–81 | 8 | 1/1 | 8 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=41&eventyear_offset=40&lastname=glasgow) |
| 82–162 | 1 | 1/1 | 1 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=122&eventyear_offset=40&lastname=glasgow) |
| 163–243 | 3 | 1/1 | 3 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=203&eventyear_offset=40&lastname=glasgow) |
| 244–324 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=284&eventyear_offset=40&lastname=glasgow) |
| 325–405 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=365&eventyear_offset=40&lastname=glasgow) |
| 406–486 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=446&eventyear_offset=40&lastname=glasgow) |
| 487–567 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=527&eventyear_offset=40&lastname=glasgow) |
| 568–648 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=608&eventyear_offset=40&lastname=glasgow) |
| 649–729 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=689&eventyear_offset=40&lastname=glasgow) |
| 730–810 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=770&eventyear_offset=40&lastname=glasgow) |
| 811–891 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=851&eventyear_offset=40&lastname=glasgow) |
| 892–972 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=932&eventyear_offset=40&lastname=glasgow) |
| 973–1053 | 0 | 0/0 | 0 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1013&eventyear_offset=40&lastname=glasgow) |
| 1054–1134 | 210 | 11/11 | 210 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1094&eventyear_offset=40&lastname=glasgow) |
| 1135–1215 | 212 | 11/11 | 212 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1175&eventyear_offset=40&lastname=glasgow) |
| 1216–1296 | 266 | 14/14 | 266 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1256&eventyear_offset=40&lastname=glasgow) |
| 1297–1377 | 278 | 14/14 | 278 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1337&eventyear_offset=40&lastname=glasgow) |
| 1378–1458 | 287 | 15/15 | 287 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1418&eventyear_offset=40&lastname=glasgow) |
| 1459–1539 | 929 | 47/47 | 929 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1499&eventyear_offset=40&lastname=glasgow) |
| 1540–1620 | 534 | 27/27 | 534 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1580&eventyear_offset=40&lastname=glasgow&sourcecategory=life%20events%20(bmds)) |
| 1540–1620 | 212 | 11/11 | 212 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1580&eventyear_offset=40&lastname=glasgow&sourcecategory=education%20%26%20work) |
| 1540–1620 | 5 | 1/1 | 5 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1580&eventyear_offset=40&lastname=glasgow&sourcecategory=institutions%20%26%20organisations) |
| 1540–1620 | 1322 | 67/67 | 1322 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1580&eventyear_offset=40&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history) |
| 1540–1620 | 1209 | 61/61 | 1209 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1580&eventyear_offset=40&lastname=glasgow&sourcecategory=travel%20%26%20migration) |
| 1540–1620 | 3282 | 75/165 | 3280 | capped; superseded | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1580&eventyear_offset=40&lastname=glasgow) |
| 1560–1640 | 4500 | 75/225 | 1500 | control; capped observation | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1600&eventyear_offset=40&lastname=glasgow) |
| 1621–1661 | 1008 | 51/51 | 1008 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1641&eventyear_offset=20&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sid=999) |
| 1621–1701 | 16 | 1/1 | 16 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=armed%20forces%20%26%20conflict&sid=999) |
| 1621–1701 | 938 | 47/47 | 938 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=life%20events%20(bmds)) |
| 1621–1701 | 1 | 1/1 | 1 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=census%2c%20land%20%26%20surveys&sid=999) |
| 1621–1701 | 2 | 1/1 | 2 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=churches%20%26%20religion) |
| 1621–1701 | 252 | 13/13 | 252 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=education%20%26%20work&sid=999) |
| 1621–1701 | 16 | 1/1 | 16 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=institutions%20%26%20organisations&sid=999) |
| 1621–1701 | 1661 | 1/84 | 20 | capped; superseded | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sid=999) |
| 1621–1701 | 2814 | 75/141 | 1500 | LIMITED LEAF | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow&sourcecategory=travel%20%26%20migration&sid=999) |
| 1621–1701 | 5700 | 1/285 | 20 | accounted by partitions | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1661&eventyear_offset=40&lastname=glasgow) |
| 1662–1682 | 1012 | 51/51 | 1012 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1672&eventyear_offset=10&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sid=999) |
| 1662–1702 | 1643 | 1/83 | 20 | capped; superseded | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1682&eventyear_offset=20&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sid=999) |
| 1683–1703 | 1195 | 60/60 | 1195 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1693&eventyear_offset=10&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sourcecountry=great%20britain&sid=999) |
| 1683–1703 | 448 | 23/23 | 448 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1693&eventyear_offset=10&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sourcecountry=united%20states~canada&sid=999) |
| 1683–1703 | 1643 | 1/83 | 20 | capped; superseded | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1693&eventyear_offset=10&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sid=999) |
| 1701–1741 | 224 | 12/12 | 224 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=armed%20forces%20%26%20conflict&sid=999) |
| 1701–1741 | 1076 | 54/54 | 1076 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=life%20events%20(bmds)&sid=999) |
| 1701–1741 | 14 | 1/1 | 14 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=census%2c%20land%20%26%20surveys&sid=999) |
| 1701–1741 | 1 | 1/1 | 1 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=churches%20%26%20religion&sid=999) |
| 1701–1741 | 774 | 39/39 | 774 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=education%20%26%20work&sid=999) |
| 1701–1741 | 27 | 2/2 | 27 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=institutions%20%26%20organisations&sid=999) |
| 1701–1741 | 1687 | 1/85 | 20 | capped; superseded | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sid=999) |
| 1701–1741 | 3028 | 75/152 | 1500 | LIMITED LEAF | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=travel%20%26%20migration&sid=999) |
| 1701–1741 | 6831 | 1/342 | 20 | accounted by partitions | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow) |
| 1701–1741 | 1231 | 62/62 | 1231 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sourcecountry=great%20britain&sid=999) |
| 1701–1741 | 456 | 23/23 | 456 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1721&eventyear_offset=20&lastname=glasgow&sourcecategory=newspapers%2c%20directories%20%26%20social%20history&sourcecountry=united%20states~canada&sid=999) |
| 1741–1751 | 237 | 12/12 | 237 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=armed%20forces%20%26%20conflict&sid=999) |
| 1741–1751 | 1102 | 56/56 | 1102 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=life%20events%20(bmds)&sid=999) |
| 1741–1751 | 1 | 1/1 | 1 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=census%2C%20land%20%26%20surveys&sid=999) |
| 1741–1751 | 2 | 1/1 | 2 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=churches%20%26%20religion&sid=999) |
| 1741–1751 | 852 | 43/43 | 852 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=education%20%26%20work&sid=999) |
| 1741–1751 | 15 | 1/1 | 15 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=institutions%20%26%20organisations&sid=999) |
| 1741–1751 | 1140 | 57/57 | 1140 | reconciled | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=newspapers%2C%20directories%20%26%20social%20history&sid=999) |
| 1741–1751 | 2537 | 75/127 | 1500 | LIMITED LEAF | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow&sourcecategory=travel%20%26%20migration&sid=999) |
| 1741–1751 | 5886 | 1/295 | 20 | accounted by partitions | [exact query](https://www.findmypast.co.uk/search/results?eventyear=1746&eventyear_offset=5&lastname=glasgow) |

## Review classes

- `candidate_in_scope`: 1079 row occurrences; 1052 deduplicated records.
- `date_anomaly_review`: 536 row occurrences; 189 deduplicated records.
- `out_of_scope`: 754 row occurrences; 208 deduplicated records.
- `rejected_surname`: 12 row occurrences; 12 deduplicated records.
- `non_exact_display_hit`: 19635 row occurrences; 5747 deduplicated records.

`candidate_in_scope` means an exact displayed Glasgow surname and a non-anomalous visible event year, or where that is blank a visible birth/death year, no later than 1750. It is a lead, not proof of identity or surname usage in the full transcript. `non_exact_display_hit` is likewise not a final rejection: the matched page/transcript must be inspected. Only an explicit saved full-record verdict produces `rejected_surname`. One-to-three-digit years, missing dates, and scope dates outside their query window remain in `date_anomaly_review` because Findmypast can truncate or broadly match dates.

## Artifacts

- `audit-windows.csv`: exact queries, URLs, timestamps, totals, claimed/actual page numbers, cap/supersession status and reconciliation checks.
- `audit-all-rows.csv`: every raw occurrence, including preserved redirect duplicates with an explicit exclusion reason.
- `audit-candidate-in-scope.csv`: exact-surname temporal leads through 1750.
- `audit-provisional-exact-display-unique.csv`: valid observed exact-display leads deduplicated by record ID, including clearly flagged rows from accessible prefixes of incomplete/capped queries.
- `audit-provisional-exact-display-unique.md`: human-readable record-ID list for the same provisional leads.
- `audit-exact-display-all-unique.csv`: every valid observed exact-display ID with its temporal/rejection class.
- `audit-date-anomalies.csv`: undated, truncated, or query-window-inconsistent rows needing transcript review.
- `audit-out-of-scope-and-surname-rejections.csv`: later events, non-exact displayed hits, and explicitly rejected surname hits.
- `audit-subscription-locked.csv`: every occurrence whose result action was subscription-locked.
- `audit-duplicate-record-ids.csv`: repeated IDs, including cross-window duplication.
- `audit-same-event-duplicate-leads.csv`: distinct IDs sharing normalized name, event year and location, with their record sets retained.
- `audit-capped-window-tail.csv`: observed structured/non-exact ordering and the still-unknown inaccessible tail for every capped query.
- `audit-capped-and-travel-tail.csv`: the same analysis plus incomplete or uncapped Travel & Migration partition queries.
- `audit-summary.json`: machine-readable counts and gap audit.
- `audit-consolidated.json`: deterministic machine-readable windows, rows and duplicate leads.
