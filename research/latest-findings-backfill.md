# Latest findings ledger backfill

Created 30 September 2026. `research/latest-findings.json` is the maintained event ledger; website generation and presentation belong to the main task.

## Coverage

460 dated concrete findings, newest first, spanning **21 July–30 September 2026**:

- 178 distinct saved Findmypast transcript events, captured 3 September. Repeated transcript versions of the same named event are grouped; the nine apprenticeship entries distinguish apprentice, father and master correctly.
- 172 newly recovered GRONI record-defined subjects in the supplied 23 September civil-record batch. Registration districts remain districts; certificates are uninspected unless a separate original-image finding says otherwise.
- 52 selected 10 September OPR findings: 16 new birth/baptism details or attribution conflicts, 30 marriage/banns entries with new facts or unresolved documentary subjects, and six death/burial entries. Pure confirmations and locator-only additions are excluded.
- 58 curated factual discoveries and corrections from dated record readings and maintained case sections, including the Irish/colonial records, Nancy notice/docket, Scottish candidate, Joseph Cunningham birth match, Joseph of Wythe probate-date correction, Larne deeds and local collateral records.

Each row preserves its internal source paths, external evidence, documentary qualification and a verified public detail route. Existing local person links were checked against generated files. Attested WikiTree IDs without a local page use their exact public WikiTree URL (134 linked-person occurrences); unresolved named documentary subjects now link to sourced identity drafts (30 September follow-up below). Candidate identities use explicit roles. A case link does not turn its subject into a person named in the source.

## Date and evidence rules

`found_on` records an explicitly stated research retrieval, supplied-record review or dated factual-correction review, never file modification time, a historical event date, a build date or an undifferentiated case update. Discovery may precede its first recoverable dated review; this limitation is stated in the ledger scope.

Nancy's original death notice was inspected **30 September**, as confirmed by the preceding session's inspection history supplied to this task. Its retained case heading and `Last updated` say 29 September; those metadata are not the inspection date. The saved excerpt has no separate capture manifest. The ledger follows the explicit inspection-date correction and records this note as provenance.

All transcript/index rows remain qualified. An inspected record can establish a named family at the documentary level while its identification with a WikiTree person remains unproved. Betham's explicit Archibald–Thomas relationship does not close the son-to-Lifford identity gap. The Norfolk witness and Princess Anne deed identify documentary Daniels; William-428 is only the linked research case. No completed-father-goal claim is made.

## Exclusions and recovery gaps

Excluded: negative searches; profile scrape prose; routine saves, merges, attachments and build logs without a material sourced fact; speculative parent rankings and pedigree placements; private correspondence, DNA tester identifiers and sensitive living-person data. The 370 GRONI existing-profile attachments and 19 deferred Robert rows are not themselves new findings.

The 18 September 57-profile creation report mixes previously captured sources, already-known facts and uncertain identity corrections. Its reported creation count is not imported as 57 new historical conclusions.

The six explicit Scottish full-text occurrences in `surname-research/pre-1700/familysearch-full-text-glasgow-scotland-1699-2026-09-22.md` preserve their documented **22–23 September** review range as `found_from` and `found_on`; the page should display the range and sort by its latest endpoint. Their individual discovery days are not invented. Undated source tables and older research conclusions also need explicit historical retrieval/review evidence before adding chronological entries. This is a substantial dated backfill, not a claim that all undated past research is recoverable.

## Checks

JSON parses; IDs are unique; research dates descend; every row has an evidence link and qualification. All local person/detail targets exist. External person targets are exact WikiTree URLs for IDs attested in maintained findings or the creation ledger. Recent identity-sensitive rows and all non-baptism Findmypast collections were audited; representative baptism, OPR and civil rows were checked against their maintained source structures. No historical research, browser activity, live WikiTree edit or deployment was performed by this inventory task.

## Website integration

Published locally at `/latest-findings/`, with homepage and primary-navigation links. `tools/build_latest_findings.py` runs from both release finalization and the research-feed build. All 460 rows remain in the static table; JavaScript adds search, filters, sorting and 50-row pagination. The website change log remains separate.

The orchestrator passed 15 focused findings, navigation and release-readiness tests, including preservation of exactly one shared analytics tag after clean-URL normalization. Browser checks passed for search, empty results, type/assessment filters, both date orders, pagination, shareable URLs, date permalinks, review ranges and layouts at 1440, 390 and 320 px. The table scrolls within its container on narrow screens; no page overflow or console errors were observed. A screenshot is saved in `output/latest-findings-desktop-20260930.png`. Production upload remains pending.

Release checks and six packaged page/asset hashes pass for `www/glasgow-site-20260930-150054.tar.gz` (138,732,871 bytes; 138.73 decimal MB). The verification report is `output/latest-findings-verification-20260930.json`; the package also preserves the map above Alexander on the homepage.

## Profile links and relationship assessments — 30 September follow-up

The 53-row identity audit recovered existing profiles and compatible candidates, and created 30 consolidated public draft pages with 84 complete sourced subject handoffs. All 537 listed person entries now have a checked profile, candidate or draft link. Candidates are not rejected for missing corroboration alone; concrete conflicts remain grounds for exclusion. Nineteen OPR identity assessments were superseded in the maintained index and public Scottish study, preserving assessment history.

AGENTS.md, the project research skill and website-sync guidance now require updates to the dated findings ledger and public presentation after every coherent research batch, including subagent work. Named subjects require a checked profile/candidate or sourced draft. This is an ongoing research workflow, not a scheduled background process.

Assessment now includes “Relationships newly certain” and “Fathers newly certain”. One dated finding proves two formerly uncertain sibling relationships through the Prescott will/deed chain; zero documented father upgrades qualify. Prior confidence evidence is retained internally; public rows show the specific relationship, before/after confidence and cited proof. Existing certain relationships and mere corroborations do not count.

Passed 18 focused tests, scoped desktop/mobile checks and console-error checks. The final verification and replacement archive are recorded in output/latest-findings-profile-updates-verification-20260930.json and docs/public-catalogue-deployment.md. The earlier 15:00 and 16:10 bundles are superseded. Production upload remains pending.

## Relationship and profile restoration — 30 September follow-up

The preceding one-finding transition count was incomplete. Two historical batches are now added with recoverable research dates: David-3899’s father proved by Daniel’s will (17 July), and Peggy Hamilton’s parents/sisters identified from the census (19 August). The Prescott finding now includes the Samuel edges as well as Robert. Current ledger: 462 findings, three confidence-change batches and nine scoped transitions, including two father findings. This is a backfill of historical discoveries, not nine new records found on 30 September or an exhaustive count of every relationship ever researched.

Fresh public Open-profile captures verify the sibling biographies already live for Thomas, Daniel, Samuel and Robert. Current/replacement/diff panels were lost by the page hierarchy redesign and reopened amendments were suppressed by the completion gate. Both are repaired; completed comparisons retain no pending badge. 213 reviewed profile panels are restored. Five missing reciprocal sibling assertions now connect the Prescott group in HTML, dossier and network outputs without inventing shared parent proof. Robert and Samuel are publicly connected to Alexander-3904 as an uncertain research father hypothesis; their full sourced replacement drafts and actual pending WikiTree amendment flags are present. No live WikiTree edit was performed.

User correction is saved in AGENTS.md and the project skill: favour supported connections over orphaned profiles, preserve actual uncertainty, and assess mothers separately. Navigation/cohesion and full Free-space edition work is separately queued in docs/queued-site-work-2026-09-30.md at the owner’s request. Fifty-nine focused tests and scoped desktop/mobile checks pass. New archive/verification details are in output/relationship-profile-restoration-verification-20260930.json and docs/public-catalogue-deployment.md; production upload remains pending.
