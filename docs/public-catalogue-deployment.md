# Public catalogue deployment

The generated `www/` directory is the complete website root. No hosting credentials are stored in this repository. The owner confirmed the SSH deployment target on 2 October 2026: `root@23.88.104.255:/var/www/glasgow`, using the existing local SSH key. This is a real directory, not an atomic-release symlink; review the rsync dry-run and retain a private server backup before uploading.

The catalogue's maintained stylesheet is `tools/catalogue-light.css`. Both the catalogue builder and unified-site repair copy it to `www/people/catalogue.css`; a full catalogue build also restores the unified light `/catalogue/` shell. `tools/check_public_catalogue.py` flags a dark stylesheet or a reverted catalogue shell before release. Package a new archive after presentation changes so old CSS cache URLs and old bundles are not reused.

## Current live release — eighth Irish newspaper continuation, 5 October 2026

The catalogue now retains 421 newspaper pages: 420 surname records and one place-study page, with 264 distinct notice readings. The clip registry contains 488 approved excerpt images; 296 pre-1800 surname pages remain unchanged. Seven new Latest findings and 421 documentary newspaper targets are synchronized. The 1800–1850 ledger records 85 quoted query pairs, 1,677 retrieved entries, 1,660 readable primary previews and 145 distinct original pages checked. These are bounded query-workload counts, not unique people or archive-wide completeness.

Research commit: `c666bafc`. All 75 focused tests pass, with 17 affected tests rerun after the final corrections. Release gates and production smoke pass; asset stamping reports zero changes and the reviewed deploy has no deletions. The live probe compared all 182 changed public regular files against the previous UI release bundle and checked all 492 unique newspaper PNG URLs referenced by current source pages. All 666 unique paths returned HTTP 200 and matched local SHA-256. Proof: `artifacts/pre1850-continuation-20261005/eighth-batch-live-hashes.json` and `eighth-batch-live-hash-summary.json`. Chrome verifies the Anne family card's inline crop and candidate labels; screenshot: `artifacts/pre1850-continuation-20261005/phase-1850-root/eighth-live-jane-family-card.png`.

Verified bundle: `www/glasgow-site-20261005-184342.tar.gz`, 271,590,187 bytes (271.590 decimal MB); 80,587 payload members plus the embedded manifest. Every member matches the manifest and current local `www/`; gzip integrity passes. SHA-256: `290621008638d6d6979f21012661dfae3a61d3b6bb52e5d11f5187aaca3550e9`. Proof: `artifacts/pre1850-continuation-20261005/eighth-bundle-proof.json`. The pre-upload server backup `/var/backups/glasgow/20261005-eighth-newspaper/site-before.tar.gz` is 259,770,097 bytes and gzip-checked. No Git push or live WikiTree edit was performed.

## Previous live release — newspaper card presentation, 5 October 2026

This release clarifies each newspaper card's documentary target and separates source-based relationship tags from candidate hypotheses. The relationship filter restores all 20 readings across 21 pages; the combined Parents & children + 1772 filters to one reading across two pages, with Robert/Andrew targets and uncertainty badges intact. “Place not stated” renders without duplicated wording. Current catalogue totals remain 415 source pages (414 surname-reference pages and one place-study page); the 296 pre-1800 surname pages and the seventh release's research conclusions are unchanged.

Implementation commit: `019d2c04`. All 75 focused tests passed; release checks and production smoke passed. The deploy log records 576 changed regular paths. A read-only production check verified HTTP 200 and matching SHA-256 for all 1,060 unique paths: those 576 changed files plus all 484 newspaper excerpt PNGs referenced by the source routes. Evidence: `artifacts/newspaper-card-ui-20261005/live-hash-proof.json` and `live-hash-summary.json`. Chrome verifies the relationship-filter behavior and documentary target presentation; screenshots: `live-relationship-cards.png` and `live-parent-child-cards.png` in the same directory.

Verified bundle: `www/glasgow-site-20261005-172808.tar.gz`, 269,817,450 bytes (269.817 decimal MB); 80,577 payload members plus the embedded manifest. Every member matches the manifest and current local `www/`; gzip integrity passes. SHA-256: `75bf6e6d2ae783d7655b79d015a751981893d14ade646b6fdad45263dba2da22`. Proof: `artifacts/newspaper-card-ui-20261005/bundle-proof.json`. The pre-upload server backup `/var/backups/glasgow/20261005-newspaper-card-ui/site-before.tar.gz` is 259,612,312 bytes and gzip-checked; proof: `artifacts/newspaper-card-ui-20261005/backup-proof.json`. No Git push or live WikiTree edit was performed.

## Previous live release — seventh newspaper continuation, 5 October 2026

The live catalogue retains 415 source pages: 414 surname-reference pages and one place-study page. The maintained source library references 480 bounded newspaper excerpt PNGs, including one pending item. The 296 pre-1800 surname pages are unchanged. The 1800–1850 ledger records 85 quoted query pairs, 1,593 retrieved entries, 1,570 screened primary previews and 127 original-page reviews. These are bounded query-workload counts, not unique people or archive-wide completeness.

Research commit: `73dbae55`. All 67 focused tests pass. Release checks and production deploy smoke pass; the reviewed rsync output contains no deletions. A read-only production probe with the site's smoke-test User-Agent verified matching SHA-256 for all 480 referenced excerpt PNGs and all 104 changed regular files from the deployment output (563 unique paths; all returned HTTP 200). Evidence: `artifacts/pre1850-continuation-20261005/seventh-batch-live-hashes.json` and `seventh-batch-live-hash-summary.json`.

A temporary verification bundle generated from a hard-linked snapshot of `www/` is 269,646,404 bytes, with 80,576 payload members plus the embedded manifest. Every member matches that manifest and current local files; gzip integrity passes. SHA-256: `07a7594f50956c6fdf64618d33701ad094114a58e18f9ac4baef8db1b7ef819e`. Proof: `artifacts/pre1850-continuation-20261005/seventh-batch-release-proof.json`. The snapshot method left `www/` unchanged. The pre-upload backup is `/var/backups/glasgow/20261005-seventh-newspaper/site-before.tar.gz` (257,894,876 bytes; gzip-checked). A Chrome spot check confirms the James Glasgow merchant card shows its 278×34 excerpt, 11 merged issues, compatible candidate labels for Glasgow-3444 and Glasgow-3196, and original links; evidence: `artifacts/pre1850-continuation-20261005/phase-1850-root/seventh-live-james-merchant-card.png`. No Git push or live WikiTree edit was performed.

## Previous live release — sixth newspaper continuation, 5 October 2026

The live catalogue retained 397 source pages: 396 surname-reference pages and one place-study page, with 459 bounded PNG excerpts. The 296 pre-1800 surname pages were unchanged. Its 1800–1850 ledger recorded 85 queries, 1,190 retrieved entries, 1,167 screened primary previews and 97 original-page reviews; these are bounded workload counts, not unique people or archive-wide completeness.

Research commit: `182c7cb4`. All 64 focused tests passed. Release gates passed with zero asset-stamp changes and zero rsync deletions. All 729 checked live pages, data files and assets matched local SHA-256 using the smoke-test User-Agent. Evidence: `artifacts/pre1850-continuation-20261005/sixth-batch-live-hashes-verified.json` and `sixth-batch-live-hash-summary.json`.

Verified bundle: `www/glasgow-site-20261005-143933.tar.gz`, 267,939,730 bytes; 80,551 payload files plus the embedded manifest. Every payload matched the manifest and current local `www/`; gzip integrity passed. SHA-256: `06491d48374731b74eb9e1aebb1febc2dcd7f8f9cf978055c4ee82bc19cb49ce`. Proof: `artifacts/pre1850-continuation-20261005/sixth-batch-release-proof.json`. Private pre-upload backup: `/var/backups/glasgow/20261005-sixth-newspaper/site-before.tar.gz`, 257,230,132 bytes, gzip-checked. A Chrome spot check confirmed the Cookstown card’s original 283×312 excerpt, Glasgow-2058 possible and Glasgow-1968 weaker labels, and original link; screenshot: `artifacts/pre1850-continuation-20261005/phase-1850-root/sixth-live-cookstown-card.png`. No Git push or live WikiTree edit was performed.

## Previous live release — Glasco newspaper records, 5 October 2026

The live catalogue retains 393 source pages: 392 surname-reference pages and one place-study page, with 452 approved bounded PNG excerpts. All retained pages have saved clippings. The 296 pre-1800 surname pages are unchanged. This release adds 18 source pages and 20 excerpts: 13 personal-name page references, four repeated Glasco and Son watch-mark notices (one object/firm reference, not four people), and one Rev. J. Glasgow of Castledawson mention. Four new held documentary accounts and two existing accounts are consolidated, sourced and qualified; repeated notices retain one card reading with inline alternative issue excerpts. No profile identity or family certainty is inferred from the firm mark, publication location, initial-only entry or reprint.

Research commit: `197188cb`. All 62 focused tests, release totals, Atlas destinations, publication boundaries and asset versions pass. The reviewed rsync dry-run has zero deletions; deployment and production smoke pass. All 720 checked live pages/data/assets match local SHA-256 bytes, including all 452 approved excerpts. Proof: `artifacts/pre1850-continuation-20261005/fifth-batch-live-hashes.json`. Chrome confirms the live Owen card with its clipping, original link and unresolved identity. Local 390-pixel checks show no horizontal overflow and the temporary viewport override was reset. Evidence: `artifacts/pre1850-continuation-20261005/fifth-*` and `phase-1850-root/fifth-*`.

Verified bundle: `www/glasgow-site-20261005-123755.tar.gz`, **267,264,682 bytes (267.264682 decimal MB)**; 80,544 public files and 80,545 rootless members. Every archive and local file matches the embedded manifest; gzip integrity passes. SHA-256: `fe57e7e01a10249875b94b5aacd4d06ac12f5e7ac3c1665574f211441ce867e2`. Private pre-upload server backup: `/var/backups/glasgow/20261005-fifth-newspaper/site-before.tar.gz`, 253,589,445 bytes, gzip-tested. No Git push or live WikiTree edit was performed.

At that release point, the 1800–1850 ledger recorded 61 query pairs, 1,595 provider-reported result entries, 974 retrieved entries and 951 screened first previews (59.6% of that logged result workload). Forty-one queries had reached End and twenty remained partial; alternate highlights still required review. These historical workload totals are not unique page/person counts or a measure of all surviving archive mentions. Search work continued in the sixth release above; the additional audits and coverage review were integrated into the current ledger. The pre-1800 displayed-query pass remains complete, with no pre-1800 pending review rows.

## Previous live release — Irish 1800–1850 continuation, 5 October 2026

The live catalogue retains 375 pages: 374 surname pages and one place-study page, with 432 approved bounded PNG excerpts. The 296 confirmed pre-1800 surname pages are unchanged. This release adds qualified Irish 1800–1850 evidence. The 1841 Belfast notice for Rev. A. J. Glasgow leaves the second initial unresolved: Adam Dickie Glasgow remains possible, with conflicting contemporary initials; James McClure Glasgow has a concrete Bombay chronology conflict. The repeated 1849 Cookstown Russian Company notice for John Glasgow remains qualified (profile 2058). Issue-specific James Glasgow corrections preserve the distinctions among the underlying notices. These are documentary assessments, not established identity or relationship claims.

Research commit: `86ecf007`. All 61 focused tests pass; release totals, Atlas destinations, publication boundaries and asset versions also pass. The reviewed dry-run has zero deletions and production smoke passes. All 694 checked live files match local bytes; the fourth-batch live hash record is `artifacts/pre1850-continuation-20261005/fourth-batch-live-hashes.json`. The live 1849 card was checked in Chrome. Evidence: `artifacts/pre1850-continuation-20261005/fourth-batch-*`. The previous downloadable bundle remains unchanged. No Git push or live WikiTree edit was performed.

Inline follow-up `4b9fa946` displays every approved alternative issue excerpt as a lazy-loaded figure inside its merged card’s disclosure, with issue metadata and original links. The single consolidated reading is preserved. All 42 source-collection tests pass; production preflight and smoke pass, with zero upload deletions. All 38 changed source pages match live bytes, and the expanded 1849 card was visually verified with its three images loaded. Evidence: `artifacts/pre1850-continuation-20261005/inline-alternatives-*`. A narrow-screen supplementary-image sizing improvement follows the continuing research batch.

## Previous live release — Pre-1800 priority closure, 5 October 2026

The live catalogue retains 296 pre-1800 surname pages, grouped into 155 distinct readings; every confirmed pre-1800 page has a saved clipping. Across all years, 373 retained pages display 429 approved bounded PNG excerpts. The recorded Irish broad/name/abbreviation priority queries, selected worldwide name audits and refreshed Glascow tail are closed for their displayed result sets. This is documented query closure, not proof of every surviving or unindexed newspaper mention. The 1800–1850 Irish extension follows.

Twenty-six George Glasgow original pages are integrated into four qualified documentary subjects: Manchester patent, Glasgow merchant/Nethermains property, Royal Artillery reports and the separate unassigned 1774 appointment. Private-sale, adjournment and judicial-sale notices retain distinct terms; damaged margins remain visible and qualified. The complete 1795 War Office notice announces an army-major appointment. Existing-profile identities, cross-record continuity and family links remain qualified; no live WikiTree save or relationship upgrade occurred. Sources/year/country pages, subjects, five affected candidate dossiers/comparisons, Latest findings and the held queue are synchronized.

Research commit: `4599242a`. All 61 focused tests pass, as do release totals, Atlas destinations, publication boundaries and asset versions. The reviewed SSH upload has zero deletions and production smoke passes. All 682 checked live files match local bytes, including every approved excerpt and affected profile readers/data. The live 1795 army-major card was visually checked in Chrome. Evidence: `artifacts/pre1850-continuation-20261005/third-batch-*`.

The previous downloadable bundle represents the preceding release; a fresh complete bundle follows continuing research batches. The retained server rollback remains `/var/backups/glasgow/20261005-pre1800-sprint/site-before.tar.gz`. No Git push was performed.

## Previous live release — Newspaper families and notices, 5 October 2026

The live collection retains 270 pre-1800 surname pages, grouped into 144 distinct readings. Across all years, 347 retained pages display 403 approved bounded PNG excerpts. Every confirmed pre-1800 page has a saved clipping. Sources and year/country pages, consolidated subjects, 14 affected candidate dossiers/comparisons, Latest findings and the held queue are synchronized. New documentary families name Robert as son of Andrew, miller at Calder (1772), and James as son of David in the Kelso militia ballot (1798). Profile assignments remain possible; no live WikiTree save or relationship certainty upgrade occurred. The three new Robert contexts remain separate. Sixteen 1782 tannery issues and three distinct 1785 issues form two reading groups; Leith merchant notices and a rescued 1798 Secretary chest paragraph are integrated.

Research commit: `b17052cb`. All 61 focused tests pass; release totals, Atlas destinations, publication boundaries and asset versions pass. The reviewed upload contains zero deletions and production smoke passes. All 643 checked live files match local bytes, including every approved excerpt, affected profile readers/data and newspaper country/year pages. The live Calder family card and clipping were checked in Chrome; proof is saved under `artifacts/pre1850-continuation-20261005/second-batch-*`. George and refreshed Glascow pre-1800 closure results are still being integrated before the 1800–1850 phase.

This batch was uploaded directly to the authorized SSH target. The previous downloadable bundle represents the preceding release; a fresh complete bundle follows the continuing research batches. The retained server rollback backup remains `/var/backups/glasgow/20261005-pre1800-sprint/site-before.tar.gz`. No Git push was performed.

## Previous live release — Newspaper continuation, 5 October 2026

The collection now retains 246 pre-1800 surname pages, grouped into 137 distinct readings. Across all years, 323 retained pages display 377 approved bounded PNG excerpts. Sources, year/country routes, consolidated subjects, 15 candidate dossiers, Latest findings and the held queue are synchronized. New evidence includes the 1758 vessel William’s unnamed Glasgow master, William Allen Glasgow’s 1795 engineer commission, earlier Samuel Old Bailey reports, 1774–1777 West Calder tenancy notices, two North Carolina secretary proclamations and repeated Wilmington tannery advertisements. Duplicate Samuel regiment accounts are consolidated, their incoming anchor preserved, and the mistaken assignment to Captain Murray’s company withdrawn. Candidate identifications remain qualified; no live WikiTree save or relationship upgrade occurred.

Research commit: `896148d8`. All 61 focused tests pass; release totals, Atlas destinations, publication boundaries and asset versions pass. The reviewed upload has zero deletions; production smoke passes. All 600 checked live files match local bytes, including every 377 excerpt, affected profile readers/data and newspaper country/year pages. The new officer card was visually checked in Chrome. Evidence: `artifacts/pre1850-continuation-20261005/first-batch-*`. Pre-1800 variant and alternate-hit checks continue; the 1800–1850 extension remains outstanding. Displayed provider totals, retrieved cards and actually read previews are recorded separately.

This batch was uploaded directly using the existing authorized SSH target. The previous verified downloadable bundle below represents the preceding release; a fresh complete bundle will be prepared after the continuing research batches. The retained server rollback backup remains `/var/backups/glasgow/20261005-pre1800-sprint/site-before.tar.gz`. No Git push was performed.

## Previous live release — Pre-1800 newspaper sprint, 5 October 2026

The pre-1800 personal-surname collection has increased from 39 to 225 retained original page URLs, grouped into 130 distinct notice readings. Reprints and duplicate archive scans retain their original links and excerpts without being counted as independent events or corroboration. Across all years, 302 retained pages display 355 visually approved bounded PNG excerpts, including supplementary headings and context. The all-years presentation has 202 distinct readings. All retained pages have an inline excerpt; original links remain available for fuller context.

Sources, country/year routes, complete consolidated documentary subjects, candidate dossiers/comparisons, Latest findings and the held work queue are synchronized. Thirty-five American pages formerly outside a country route now appear in the United States index and year pages. Candidate cards distinguish confirmed surname readings from probable or possible personal identifications and preserve uncertain dates. New subjects include James of Marsh Creek, John of Millrig and the Huntingdon County township list, and Andrew signing the 1779 Leith notice. North Carolina allegations, the published response and reproduced conveyance/affidavit are attributed; no conviction, authenticated transaction or family relationship follows. Postal addressees need not still be alive. Vessel William never supplies a captain’s forename. Northern Star issue ranges explain the reviewed advertisement-date differences without silently changing either date. No live WikiTree save or family certainty upgrade occurred.

The review contains 518 pages: 301 retained surname pages, one place-study page, 68 city/vessel exclusions and 148 later readings pending. William, James and John quoted “Glafgow” result cards were screened to their displayed ends, with promising originals inspected and retained. Unresolved originals, preview-only dismissals, Thomas pagination gaps, broader Glascow results, unqueried spellings and incomplete holdings prevent an exhaustive pre-1800 or worldwide claim. The local agent setting is ten, while this session provides four total slots including the orchestrator; three low-intensity workers were reused. Earlier failed external launches receive no coverage credit. Working tabs were closed when their tasks finished.

Research commits span `c0601e10` through `b7d83f5f`, with the final batch in `b7d83f5f` and preceding release in `4d6d8ff6`; catalogue analytics restoration is `5b8b3115`. All 61 focused tests pass. Release totals, Atlas destinations, publication boundaries, asset versions, production smoke and catalogue probes pass. The first upload stopped at the publication boundary because a later rebuild removed three required catalogue analytics tags; they were restored before the successful retry. The reviewed dry-run has zero deletions. All 567 checked live pages/data/assets match local bytes, including every 355 approved excerpt image, affected profile readers/data and all newspaper country/year indexes. Desktop excerpt/candidate reading was visually checked in Chrome. Evidence: `artifacts/pre1800-sprint-20261005/thirteenth-batch-*`, `current-live-hashes.json`, `final-counts.json` and `thirteenth-batch-live-card.png`.

Verified current bundle: `www/glasgow-site-20261005-062432.tar.gz`, **240,031,200 bytes (240.031200 decimal MB)**; 80,423 public files and 80,424 rootless members. Every archive file matches its embedded manifest and current local bytes; gzip integrity passes. SHA-256: `9390488322fb368b970e525db294ade8f7f7b8c662416e06275e672330c4d524`. This supersedes the 00:11 bundle below. Eighteen superseded generated packages and one failed temporary archive were removed locally to recover space; maintained evidence and the current rollback backup remain intact.

The prior site is retained in the gzip-tested private server backup `/var/backups/glasgow/20261005-pre1800-sprint/site-before.tar.gz` (175,889,249 bytes). Uploads preserve host ownership and hosting configuration. No Git push was performed.

## Previous live release — Complete retained clippings and merged notices, 5 October 2026

All 116 retained newspaper pages now have approved saved excerpts: 143 primary-manifest excerpts, including 39 pre-1800 pages. The presentation groups 27 repeated card rows into 89 distinct maintained notice readings, preserving every issue date, original page link, excerpt and deep-link anchor. Supplementary passages remain inline in expandable details. Cards show clickable profile candidates, recorded life dates, curated confidence, the person's role and the evidence basis. Supplementary media and readings align side by side on desktop and stack without horizontal overflow on mobile. Pending leads and city/vessel exclusions remain separately qualified.

Two newly inspected pre-1800 records are integrated: Nicholas Glasco in the 1746 Southwark prisoners report has a consolidated sourced public draft; the 1765 death notice names an unnamed wife of Philip Glasco junior, a probable earlier wife for compatible candidate Glasgow-3932 before the 1768 Teresa Plunkett marriage. It does not identify her as Teresa or prove Philip's parents. The 1875 Evening Telegraph age for Daniel of Kilrea is corrected to 75; the News-Letter's conflicting 73 remains recorded. The 1858 uncle quotation supplies no forename, and the 1802/1806 licence headings are corrected. A deceased Benjamin comparison is explicitly excluded from the July 1870 record. Six affected profile dossiers/comparisons, Sources, consolidated subject accounts, Latest findings and the held queue are synchronized. No live WikiTree save or relationship upgrade occurred.

The review contains 328 catalogued pages: 180 inspected, comprising 115 surname pages, one place-study page and 64 exclusions; 148 readings remain pending. These selective searches do not establish exhaustive pre-1800 or worldwide newspaper coverage. The local agent configuration was raised to ten, but the separate ten-worker launch failed before any research; no search coverage is credited to it. The current chat's built-in delegation remains capped at four slots including the orchestrator.

Implementation commits: `8c956f7f` and `8b8633c6`. All 34 focused tests pass, as do release totals, Atlas destinations, publication boundaries, asset versions, production smoke and catalogue probes. All 231 checked live pages/data/assets, including all 143 primary-manifest excerpt images and the Sources stylesheet/script, match local bytes. Desktop/mobile clipping, supplementary-excerpt and repeated-notice filter checks pass. Final rsync dry-run: no changes. Verification and live screenshots: `artifacts/remaining-clippings-20261004/`.

Verified final bundle: `www/glasgow-site-20261005-001143.tar.gz`, **185,918,646 bytes (185.918646 decimal MB)**; 80,158 public files and 80,159 rootless members. Every archive file matches the embedded manifest and current local bytes; gzip integrity passes. SHA-256: `5b0a95a0dd9088863432258cd1784bad9113b7f20d389b1ec59e3f3057cfc142`. This supersedes the intermediate 00:03 bundle, which predates the card alignment correction.

The prior live site is retained in the gzip-tested private server backup `/var/backups/glasgow/20261005-000315-complete-newspaper-clips/site-before.tar.gz` (156,848,600 bytes). Both reviewed uploads contain no deletions and preserve host ownership and hosting configuration. No Git push was performed. Chrome has four tabs; only the final live Sources tab remains controlled by this research session.

## Previous live release — Pre-1800 newspaper clippings, 4 October 2026

All 37 currently retained pre-1800 newspaper pages now display 40 approved inline excerpts, including the separate December 1792 cargo advertisement and larger Kildress reading supplements. The full reviewed collection has 90 pages with 93 excerpts, up from 55 pages. Twenty-four retained later pages still need an excerpt. Pending search leads and city/vessel exclusions have separate explanatory messages. Each pre-1800 crop was visually checked and every approved source/public image hash and year-page image passed the preservation audit.

The newly inspected 20 September 1768 original names Philip Glasco the younger and Teresa Plunkett, corroborating compatible candidate Glasgow-3932 without proving his father. The John Glasgow Nottingham store notice is corrected to the end of September; the 1 August 1792 Oporto notice itself is dated 23 July. The Derby Mercury March/April conflict and the January 1796 issue/advertisement date conflict remain visible. Candidate dossiers, subject accounts, Sources, Latest findings and the held queue are synchronized. No live WikiTree save or relationship upgrade occurred.

The review contains 326 catalogued pages: 178 inspected, including 113 surname pages, one place-study page and 64 exclusions; 148 await reading. The pre-1800 log has 156 query records. All 51 catalogue-led Irish name forms and the 16 abbreviation queries are recorded, but worldwide Glascow loading stopped at 180 of 306 results and further highlights remain unread. These counts do not establish exhaustive newspaper coverage.

Implementation commit: `71688860`. All 26 focused tests, release totals, Atlas destinations, publication boundaries and asset versions pass. Production smoke and catalogue probes pass. All 100 checked live pages/data/assets, including all 93 primary-manifest excerpt images, match local bytes. The live year filter and Philip marriage clipping were visually checked in Chrome. Final rsync dry-run: no changes. Evidence and screenshot: `artifacts/pre1800-root-20261004/`.

Verified bundle: `www/glasgow-site-20261004-225627.tar.gz`, **166,851,637 bytes (166.851637 decimal MB)**; 80,106 public files and 80,107 rootless members. Every archive file matches the embedded manifest and current local bytes; gzip integrity passes. SHA-256: `087d54f014b7c5ddc5fb92b7bb246ccd04703209529cd53edb1619bc06f13384`.

The prior live site is retained in the gzip-tested private server backup `/var/backups/glasgow/20261004-pre1800-clippings/site-before.tar.gz` (152,538,968 bytes). The reviewed upload has no deletions and preserves host ownership and hosting configuration. No Git push was performed. Agent-created tabs were closed after their jobs; the final Chrome inventory has four tabs. The project skill now requires prompt cleanup while allowing multiple active working tabs.

## Previous live release — Newspaper continuation, 4 October 2026

Six further original surname notices from 1811–1850 and their approved inline clippings are deployed: senior Royal Artillery George (1811/1819), George Mark (1825), Edward George (1825), Benjamin's surgery degree report (1825), and John the Cookstown tea/coffee agent (1850). The degree report remains explicitly in conflict with the university index's 1826 entry. Military identities and family connections remain qualified. Eight candidate dossiers, five consolidated subject accounts, Sources year pages, Latest findings and the held queue are synchronized. No WikiTree save or relationship upgrade occurred.

The newspaper review contains 325 catalogued pages: 168 inspected, including 112 surname pages, one place-study page and 55 exclusions; 157 await reading. The live saved-clipping filter returns 55 of 113 retained pages. The 1800–1850 coverage log records 59 distinct quoted queries, 758 retrieved result entries, 735 readable first previews and 45 newly resolved original pages across the continuing search. Larger result sets and unqueried names remain incomplete; these totals do not claim exhaustive coverage.

Implementation commits: `2143cc9b` and `609c7601`. The first upload preflight rejected three serialized analytics tags; those tags were restored to the canonical form and the complete publication-boundary audit passed before upload. All 47 focused tests, release totals, Atlas destinations and asset versions pass. Production smoke/catalogue probes pass, all 25 sampled live pages/data/assets match local bytes, and the final rsync dry-run reports no changes. The live degree card and clipping filter were checked in Chrome; desktop and local mobile reading have no horizontal overflow. Evidence: `artifacts/newspapers-degree-military-20261004/`.

Verified bundle: `www/glasgow-site-20261004-202017.tar.gz`, **162,550,262 bytes (162.550262 decimal MB)**; 80,067 public files and 80,068 rootless members. Every archive and local file matches its embedded manifest; gzip integrity passes. SHA-256: `6df5a9a42f03e5006bf01599117a83f9b740dbfd10053ab2b79982d90fb161e1`. This supersedes the 18:54 census package and the intermediate 20:14 package, which predates the analytics repair.

The prior live site is retained in the gzip-tested private server backup `/var/backups/glasgow/20261004-newspaper-degree-military/site-before.tar.gz` (151,735,157 bytes). The reviewed upload has no deletions and preserves host ownership and hosting configuration. No Git push was performed.

## Previous live release — Census coverage, 4 October 2026

The census collection correction is deployed. Citation access/review dates, archive identifiers and emigrants' birthplaces had left valid references outside their enumeration-year groups or under the wrong country. All 2,668 collected census references are preserved; 2,531 now have supported year groups, up from 791. The remaining 137 have visible unresolved-year routes. Shared citations retain each explicitly supported census year. Hash-pinned citation reviews handle a small set of ambiguous titles; census substitutes retain their proper record names. This release adds no new original-image readings or identity/relationship conclusions.

Irish year pages now contain: 1831 — 5 references / 8 linked people; 1851 — 25 / 76; 1901 — 92 / 193; 1911 — 73 / 157. Scottish 1841 increases from 4 to 24 references and 1851 from 6 to 23. Census cards show named, searchable public people and separate reference/person totals. These are catalogue associations, including spouses and relatives, rather than unique households, verified surname enumerations or a complete archive search.

Implementation commits: `614d2e20` and `55df3365`. Verified bundle: `www/glasgow-site-20261004-185428.tar.gz`, **161,744,890 bytes (161.744890 decimal MB)**. All 80,058 local public files match the embedded manifest; the archive has 80,059 rootless members and passes gzip integrity. SHA-256: `a1cffd8316ce3023b0114f58845cf140f223166a15a55ffe7f321382f8dd0627`.

All 33 focused tests, JavaScript syntax, release totals, Atlas destinations, publication boundaries and asset versions pass. Production smoke/catalogue probes pass; all 18 sampled pages/assets match the local release byte for byte. Browser checks confirm the live 1851 totals, named-person search, pagination and mobile filter controls with no horizontal overflow at 390 pixels. The temporary viewport override was reset. The newspaper saved-clipping filter still returns 49 of 107 retained pages. No browser errors were recorded. Final rsync dry-run: no changes.

The previous Sources release is retained in the gzip-tested private server backup `/var/backups/glasgow/20261004-census-sources/site-before.tar.gz` (151,328,763 bytes). Reviewed deletions remove only obsolete collection pages; every source reference and individual reader remains. Deployment preserves host ownership and existing hosting configuration. Verification, before/after counts and screenshots: `artifacts/census-sources-live-20261004/`. No Git push was performed.

## Previous live release — Sources library, 4 October 2026

The organised Sources library is deployed at `https://glasgow.phenotype.dev/sources/`. It preserves all 15,656 collected reference items, with 470 collection pages grouped by record type, country and year or period. Coverage guides explain surviving holdings, losses and record limitations, with original repository links. The newspaper collection includes 49 inline excerpts beside reviewed notices and a gallery of 16 distinct supplied clippings; three gallery items remain explicitly pending exact original image links. These counts overlap; 53 distinct approved clipping images are published.

Implementation commit: `eed58953`. Verified release: `www/glasgow-site-20261004-172236.tar.gz`, **161,343,337 bytes (161.343337 decimal MB)**. All 80,033 public files match the local tree and embedded manifest; the archive contains 80,034 rootless members and passes gzip integrity. SHA-256: `84e1d8760c2357fdd1acd54be78d4e9b3ece6da0856ce8d438b9ac694c194cb4`.

The prepared release passed 22 focused tests and desktop/mobile source checks. Deployment reran release totals, Atlas destinations, publication boundaries and asset-version checks, then uploaded with `tools/deploy_site.py --execute --no-stamp` to preserve the settled release. Production smoke and catalogue probes pass. All 70 sampled served pages/assets, including every one of the 53 clipping images, match local SHA-256 hashes. Browser checks confirm the Sources overview, 1851 Irish Census collection and original links, clipping gallery, desktop/mobile name/year/clipping filters, and the old family-page newspaper anchor redirect. At 390 pixels, controls and the loaded clipping fit without horizontal overflow; the temporary viewport override was reset. No browser errors were recorded.

The previous served tree is retained in the gzip-tested private backup `/var/backups/glasgow/20261004-sources-library/site-before.tar.gz` (140,230,921 bytes). The reviewed rsync upload preserves server ownership and had no deletions. The final rsync dry-run reports no changes. Hosting configuration is unchanged. Verification logs and screenshots: `artifacts/sources-live-deploy-20261004/`. This is a completed production deployment; Git pushes remain the owner's responsibility.

## Previous live release — Search filters, 4 October 2026

The search filter menus are repaired and deployed to `https://glasgow.phenotype.dev/catalogue/`. The toolbar's horizontal scrolling clipped every descendant menu to a 40-pixel strip and scrolled the buttons out of view when a field received focus. Filter buttons now wrap with visible overflow; complete panels, including Gender and exact-name spelling, remain accessible. The maintained rule is in `tools/catalogue-light.css`. This release also publishes the research updates already prepared locally through 4 October and supersedes the earlier packages and pending-publication notes below.

Verified release: `www/glasgow-site-20261004-013540.tar.gz`, **150,335,474 bytes (150.335474 decimal MB)**. All 79,493 public files match both the local tree and embedded manifest; the archive contains 79,494 rootless members and passes gzip integrity. SHA-256: `6555fa2291077e4f0a6fd8f756eb466a414de4aba3de9dafed43994793024b6c`.

Validation passed: 14 focused unit tests; catalogue checks; release totals, Atlas destinations, publication boundaries and asset versions; local and live smoke checks. Browser checks opened all seven menus locally at desktop, tablet and mobile widths, and on production at 1200 and 390 pixels. A 320 × 568 production check confirms the lower Name controls scroll within the sheet and remain clickable. Every visible control passed pointer-access checks, with no horizontal page overflow or browser errors. Female filtering returns the expected 2,637 people. Six served pages/assets match local SHA-256 hashes; the CSS URL uses `v=b459b98b00` with immutable caching. The final rsync dry-run reports no changes.

The previous served tree is retained in the gzip-tested private backup `/var/backups/glasgow/20261004-search-filters/site-before.tar.gz`. The reviewed rsync upload preserves host ownership and had no deletions. Evidence and desktop/mobile screenshots: `artifacts/search-filter-fix-20261004/`. The completed changes are committed locally; the owner handles Git pushes.

## Previous live release — 2 October 2026

All findings from the delegated site audit are fixed and deployed to `https://glasgow.phenotype.dev/`. The maintained changes are listed in `docs/site-reader-audit.md`; implementation commit: `1160fe1f`. No Git push or live WikiTree edit was performed.

Verified release: `www/glasgow-site-20261002-135909.tar.gz`, **148,779,924 bytes (148.78 decimal MB)**. Its 79,457 public files all match the local tree and embedded manifest; there are 79,458 rootless archive members. Gzip integrity passes. SHA-256: `1be3acb66a69f97856c4caf407d9b066a2f79aa0b5356a74abf434555f0cdc03`. This supersedes the earlier packages and pending-publication notes below.

Validation passed:

- 73 focused unit tests, 16 navigation/smoke tests, scoped Ruff and JavaScript syntax checks; deployment and smoke tests also passed after their final adjustments.
- 733 generated-content checks, release totals, Atlas destinations, publication boundaries and asset versions.
- 27 local browser cases at 320/390/1440 px, including serious/critical accessibility gates; maximum CLS 0.0921 and blocking time 139 ms. The catalogue update badge now has 6.87:1 contrast.
- 26 journey checks at 1440/390 px both locally and on production. Five reader routes also passed desktop/mobile visual review. All 85 Free-space reading bodies retain their prior content.
- Live smoke and catalogue probes; 20 sampled live pages/assets match the local release byte for byte. A final rsync dry-run reports no remaining changes.

The original Nginx vhost and complete served tree were backed up under `/var/backups/glasgow/20261002-site-audit/` (`nginx.conf` and gzip-tested `site-before.tar.gz`). That private server backup is retained for rollback. Uploads preserve the server's file ownership rather than copying Mac user/group IDs; obsolete public export remnants and macOS metadata are removed by the reviewed release exclusions.

Nginx now includes `/etc/nginx/conf.d/glasgow-cache-map.conf` in its HTTP context and `/etc/nginx/snippets/glasgow-cache-headers.conf` in this site's existing vhost. `nginx -t` and reload succeeded. Public Cloudflare responses confirm revalidation for HTML/unversioned data, one-year immutable caching for versioned assets and hash-named payloads, `no-store` on a missing versioned asset, and retained immutable policy on a conditional 304. Existing routing and TLS configuration are preserved.

The first post-upload smoke run stopped solely because its expected heading still said “The family atlas”; the maintained page correctly says “The family tree”. The check was corrected and passes. No content rollback or additional upload was needed.

Evidence: `output/playwright/site-fixes-20261002/`, especially `bundle-verification.json`, `quality-local-final.json`, `journeys-live.log`, `http-live.json`, `smoke-live-final.log`, `catalogue-live.log`, `deploy-readback.log` and `nginx-install.log`. These are scoped verification results, not a new review of historical evidence or production field-performance measurements.

## Release

1. If source data changed, rebuild with `.venv/bin/python tools/build_family_map.py`. For presentation-only changes, preserve the existing generated datasets.
2. Apply maintained presentation repairs: `.venv/bin/python tools/repair_unified_site.py`. This also runs the read-only migration audit; keep the local `www_old/` migration reference available.
3. Test: `.venv/bin/python -m unittest discover -s tests -v`.
4. Check generated entry points: `.venv/bin/python tools/check_public_catalogue.py`. Run the desktop/mobile checks in `docs/site-experience-checks.md`, including family pagination and research-feed identity details.
5. Review the release changes and keep the previous hosted website bundle available for rollback. Upload only the contents of `www/` to the document root for `glasgow.phenotype.dev`, not the repository or private research directories. Prefer an atomic directory switch where the host supports it.
6. Probe production: `.venv/bin/python tools/check_public_catalogue.py --base-url https://glasgow.phenotype.dev/`. Repeat key browser flows against production and check changed stylesheet/script versions.

Preparing local files or passing local checks is not a production deployment. The host upload remains a separate authorized manual step.

After any targeted data or page update, run `.venv/bin/python -m tools.publish_research_release` before packaging. This resolves approved structured assessments while retaining imported provenance, renders source evidence into static HTML, and refreshes the small indexes and `/data/manifest.json`. The unified presentation repair also runs this finalization step. The manifest's build fingerprint and assembly timestamp describe the exported data; its research date is independently derived from dated findings and reviews. Full `people.json` remains explicitly labelled as an imported snapshot. Free-space summary inputs live in `research/free-space-pages/public-study-summaries.json` and are published by `tools/build_free_space_site.py`.

For server reuploads, place the finished bundle at `www/glasgow-site-YYYYMMDD-HHMMSS.tar.gz`. Assemble it outside `www/` first, excluding earlier `glasgow-site-*.tar.gz` bundles and macOS metadata, then move the verified archive into `www/`. Put the website contents directly at archive root so extraction updates the server's document root without adding a nested `www/` directory. Report the exact byte size and decimal MB; label binary MiB explicitly.

## Deployment helpers

`tools/stamp_asset_versions.py --check` finds stale local CSS/JS `?v=` values; run `--write` only after the generated HTML is settled. `tools/deploy_site.py --bundle` creates and verifies the conventional archive. For SSH deployment, set `GLASGOW_DEPLOY_TARGET=user@host:/absolute/document-root` (or use `--target`): the default is an itemised rsync dry-run, and `--execute` is required to upload. `--atomic` uploads to `<document-root>.releases/<timestamp>` and switches the document-root symlink, so the host must permit that symlink arrangement; `--rollback --execute` switches to the preceding release. Every executed deploy runs `tools/smoke_test_site.py` against `--base-url` (defaulting to production). Run the smoke checker directly against a local server when preparing a release: `.venv/bin/python tools/smoke_test_site.py http://127.0.0.1:8765`.

## Pending presentation release

- All requested site tasks completed locally on 30 September 2026. Retains 462 findings, three newly-certain batches covering nine relationship transitions, reciprocal Prescott brother links, Robert/Samuel pending WikiTree amendments and 213 restored comparison panels. Removed redundant Filters/latest-findings submenus; Family Tree now orders Whole tree, Branch cards, Timeline, Y-DNA; oversized timeline panels start collapsed and deep links expand their targets. Submenus have stable first-paint markup and same-page anchors preserve the document. Changes/Feedback appear under About and use the shared shell. Cohesion migration also repairs 1,265 place and 102 public people/group readers; audit has zero unexplained public reader gaps. Free-space is now a complete categorized, importance-sorted second edition of 85 unique studies, including two explicitly blank original captures, with citations, full local drafts and conflict-preserving WikiTree reconciliation. Three principal-page metadata checks succeeded; WikiTree raw text returned HTTP 202 empty, so current live bodies are not asserted. Passed 69 focused tests, the timeline disclosure check, scoped desktop/mobile browser checks, and release validation.
  Latest verified upload bundle: `www/glasgow-site-20260930-182547.tar.gz`, 141,897,269 bytes (141.90 decimal MB), 79,136 rootless members. All 86 Free-space HTML pages are present; 20 affected page/asset hashes match both local files and the archive manifest. SHA-256: `c4dcc815c0ecd8ac62fef7add11bb9ed8a6ec61c0e023ed5691aa0b7b60e5b87`. Verification: `output/site-task-completion-verification-20260930.json`. Supersedes the 17:33 bundle. No live WikiTree saves or production deployment performed. The previously deferred queue is completed locally; see `docs/queued-site-work-2026-09-30.md` and `docs/free-space-edition.md`.

- Branch area popups repaired on 30 September 2026. Regional headings now show the area name and recorded people count on separate lines, avoiding concatenated rank/name/count text. The shared directory popup remains compatible; narrow-screen width is constrained. Audited all seven interactive branch maps and all 56 area popups; verified actual pointer hover and mobile390 layout with no console errors. Eight focused tests passed. Maintained JS/CSS and public assets are synchronized; 4,802 page asset versions updated.
  Previous upload bundle (superseded above): `www/glasgow-site-20260930-173313.tar.gz`, 140,389,867 bytes (140.39 decimal MB), 79,051 rootless archive members. Release checks and gzip integrity pass; all seven affected map pages plus both assets match the archive manifest and local hashes. SHA-256: `e3fbe5ac5616bccce18b599c802e3f3754448441e940cabb866ffe6ae3891fc0`. Verification: `output/branch-popup-audit-20260930.json`. Supersedes the 17:25 bundle and includes the completed research/profile batch. Production upload remains pending; the redesign queue was subsequently completed in the release above.

- Previous research/profile batch completed on 30 September 2026. Latest findings now contains 462 entries, including three newly-certain finding batches covering nine relationship transitions; two batches include father evidence. Historical discoveries retain their original dates. This is a backfill of recoverable dated history, not an exhaustive claim. The four Prescott brothers have reciprocal sourced sibling links; Robert and Samuel have explicitly uncertain father hypotheses and complete pending WikiTree amendments. Current captured biography, complete replacement draft and diff panels are restored on 213 reviewed profiles. Passed 59 focused tests and scoped desktop/mobile browser checks. No live WikiTree edits or production upload performed.
  Previous upload bundle (superseded above): `www/glasgow-site-20260930-172518.tar.gz`, 140,387,466 bytes (140.39 decimal MB), 79,051 rootless archive members. Release checks and gzip integrity pass; 15 affected page/asset hashes match local files and the archive manifest. SHA-256: `eaeadc520dd8208f277669355f5a92f75ed6a7500d476b0b92aac133029dca75`. Verification: `output/relationship-profile-restoration-verification-20260930.json`. Supersedes the 16:24 bundle and earlier archives. Later navigation/design and Free-space second-edition work was subsequently completed in the release above.

- Latest findings added on 30 September 2026 at `/latest-findings/`, with homepage and primary-navigation links. Its table contains 460 sourced discoveries and corrections dated 21 July–30 September, newest first, with evidence limits, search, filters and pagination. All rows remain available without JavaScript. Passed 15 focused tests and desktop/mobile browser checks at 1440, 390 and 320 px. The maintained ledger and build workflow preserve future updates.
  Profile follow-up: all 537 listed people now link to checked profiles, compatible candidates or sourced drafts; 30 consolidated pages cover 84 subject handoffs. Nineteen OPR identity assessments were reconciled. The project agent and research skill require findings updates after every coherent batch. Assessment offers “Relationships newly certain” and “Fathers newly certain”: one dated finding establishes two sibling upgrades; no father upgrade qualifies. Passed 18 focused tests and scoped desktop/mobile checks.
  Previous upload bundle (superseded above): `www/glasgow-site-20260930-162417.tar.gz`, 138,868,165 bytes (138.87 decimal MB). Release totals, Atlas destinations, publication boundaries, asset versions and gzip integrity pass; 79,047 archived files include the release manifest. Nine affected page/asset hashes match current local files and the manifest. SHA-256: `257f6f25c32ff0e054a4aa625520dde42608c5eeb8ee78eb99b4dff73f67778c`. Verification: `output/latest-findings-profile-updates-verification-20260930.json`. Supersedes the 14:05, 15:00 and 16:10 bundles; production upload remains pending.

- Homepage study map restored above Alexander's example on 30 September 2026. Tree restoration and navigation repairs preserve the Whole tree label, its first position and the loaded tree heading. Passed 10 focused tests and 34 desktop/mobile browser checks at 1440, 390 and 320 px. Production upload remains pending.
  The earlier `www/glasgow-site-20260930-140559.tar.gz` is superseded by the Latest findings bundle above, which also preserves these repairs and the saved 30 September research findings.

- Catalogue cells now show their individual status colours: green for supported or tree-marked certain, yellow for uncertain/estimated/bounded dates, red for disputed/contradicted, and grey for unassessed. Birth/death date and place flags remain independent; missing values stay neutral. Includes relationship cells, accessible status text and tooltips; the colour legend was removed at the owner’s request. Passed seven focused regressions, catalogue validation and scoped desktop/mobile/grouped browser checks. Production upload remains pending.

- Reader wording and navigation revised on 29 September 2026: plain genealogy terms, direct Records & sources navigation, clearer homepage reading routes and retained earlier research notes and bookmarks. Passed 29 focused regressions, 146 desktop/mobile browser checks and 733 generated-content checks; asset versions are current. See `docs/site-reader-audit.md`. Production upload remains pending.

- Source library redesigned on 28 September 2026: responsive search panel, compact source rows and a reviewed-collections sidebar that preserves all five published notices. `tools/repair_sources_page.py` maintains the layout and runs during release finalization. Passed 34 focused browser checks (including mobile, scoped search, no-JavaScript listing and failed-worker recovery) and 5 combined sources/records regressions. Production upload remains pending.
- Records loading and presentation repaired on 28 September 2026. Generation and targeted repair attach the records script and stylesheet by path regardless of prior asset versions. Search now has pagination, sorting, scoped links and failed-request retry; the page has a responsive filter panel and compact record rows. Passed 3 focused generator regressions and 48 browser checks, including 1440, 390 and 320 px layouts and HTTP-failure recovery. These are scoped checks, not a full-site release audit. Production upload remains pending.
- Family search renders 24 results per page with accessible previous/next controls, a result range, and page reset when filters change. Curated regional studies remain visible separately.
- Latest research cards identify their subject with a profile identifier, qualified dates and recorded places. These catalogue fields help distinguish namesakes; the linked case remains authoritative where recorded fields are disputed.
- The preceding presentation batch passed nine focused regression tests, 56 desktop/mobile browser checks and the full migration audit. Those results predate the pagination and feed-identity changes; rerun the release checks above before publishing this batch.
- No production upload has been performed for this release preparation.

`health.json` exposes the generation date, public people/record/place counts, source-link backlog and core generation checks. The status page presents the same information for readers.

The original Google Analytics tag (`G-JB207MGBMX`) is restored at the project owner's request. `tools/site_analytics.py` adds exactly one tag to full HTML pages and deduplicates its managed and legacy forms. Run `.venv/bin/python tools/site_analytics.py --check` to check coverage and duplicates. Public privacy and publication boundaries are described in `docs/privacy-policy.md` and `/privacy/`.

Release preparation rejects private identifiers, raw captures, withheld DNA and unapproved licensed assets, inconsistent totals and broken Atlas destinations. Historical transcription assets explicitly approved in `research/transcriptions/public-preview-approvals.json` are restored and retained only when their exact paths and hashes match that manifest and their preserved originals. Asset stamping cannot bypass these gates. Bundles include `release-manifest.json` with each public file's byte count and SHA-256 hash; Python sources, credentials, private directories, escaped symlinks and earlier bundles are excluded. Old bundles are retained outside the public root in `artifacts/site-releases/`.

The full previously curated `/ydna/` study is approved in `research/ydna-publication-approval.json`. Its renderer preserves the historical narrative, diagrams, comparisons, matrices, SNP summaries, tools and exports inside the shared site shell. Release checks compare the embedded study and documentary-line data against the exact approved retained inputs; this exception does not authorize raw sequence files or additional tester records.

The owner also restored Alexander Glasgow's full DNA section, separate matrix exports and six record excerpts, all Atlas tester annotations and controls, and the two supplied Y-DNA reference pages. `research/publication-restoration-approval.json` records the exact retained research sources, including the complete Atlas markup and data recovered from the pre-audit archive. The manuscript asset manifest includes the six dossier excerpts. Builds and release gates preserve these publications while retaining the living-person, restricted-capture and raw-sequence checks.

Executed rsync releases delete excluded files from the public destination as well as obsolete pages, so old public archives and source files cannot survive through exclusion protection. Atomic switching refuses an existing real directory and requires a release directory; establish the host's document-root symlink arrangement separately. Retain rollback bundles outside the served document root.

The supplied `_headers` and `.htaccess` configure basic security headers where supported. Production must be checked for the actual header response, HTTPS and publication boundaries after upload; local files alone do not establish host configuration. Remove private or unapproved assets and old bundles from the host/CDN during an authorized release, retaining the explicitly restored research paths.

Zero-result searches dispatch a local `catalogue:zero-results` browser event; no custom analytics event is configured for it.

After each release, verify the people, records, places and comparison views on a narrow mobile viewport and a desktop viewport. Keep the previous website bundle available on the host for rollback.

## Periodic profile discovery

Run the live audit periodically to find WikiTree profiles created from catalogue drafts:

```bash
.venv/bin/python tools/audit_missing_wikitree_profiles.py --apply-new-draft-matches
```

Automatic linking is deliberately narrow: the previous audit must have found no candidate, exactly one new candidate must appear, and it must match the draft's vital year plus the chronology/place score. Ambiguous results remain candidates for review. The saved link is applied on the next normal catalogue build.

## Prepared local release — 30 September 2026, 19:27

`www/glasgow-site-20260930-192738.tar.gz` supersedes the earlier 18:25 package
for server upload. It is 142,859,653 bytes (142.86 decimal MB), with 79,153
rootless archive members. SHA-256:
`4bd7c5dd6098eab4be99bc84b5234402a45de7eaa1ad67c1f8043e6a86246c32`.
Release totals, Atlas destinations, publication boundaries and content-hash
asset versions passed. Streaming gzip verification read the complete archive
and compared 22 selected final pages/assets against both local files and
`release-manifest.json`.

This package includes the restored side-by-side profile diff on 210 profiles,
filtered catalogue Map view, branch maps before long panels with click-away
previews, and a central 140-item held/pending research queue. The historical
audit backfills 29 dated findings: 38 documented relationship changes across
32 finding batches (14 uncertain/unknown to certain and 24 previously ungraded
to certain; 31 father changes). Already confident links without a recoverable
prior grade remain excluded. The ledger now contains 491 findings.

Passed 36 focused Python tests, the executable Map model fixture and scoped
desktop/mobile browser checks; the two queue tests were rerun after the jump
link correction. Evidence and screenshots are recorded in
`output/catalogue-research-ui-verification-20260930.json`. Research workflow
instructions and automatic release synchronization maintain the audit, queue
and findings views. No production deployment or live WikiTree save occurred
in this batch; hosted pages remain pending manual upload and live verification.

## Manual-amendment comparison repair — 30 September 2026

The renderer now preserves side-by-side comparisons on manual amendments, including manager-blocked replacement drafts. Glasgow-548, Glasgow-567 and Glasgow-822 were rebuilt with both full biographies retained. Seven focused tests and desktop/mobile browser checks passed. The corrected upload bundle supersedes the 21:20 package: `www/glasgow-site-20260930-214345.tar.gz`, 143876515 bytes (143.88 decimal MB). SHA-256: `2082e09d21203e83aab9ee217a43093da1916c27d320528879a6d33f7ef35bb2`. Release gates, gzip integrity and all three repaired-page manifest/local hashes passed. No production upload was performed. Verification: `output/manual-profile-diff-verification-20260930.json`.

## Prepared local release — 30 September 2026, 23:30

`www/glasgow-site-20260930-233047.tar.gz` supersedes the 23:08 archive. It is 144,084,352 bytes (144.08 decimal MB), SHA-256 `d6ccd2dc66cce444e2bcf2ef65ce1121b1cf41eb55a8e421ea7b84e16fea8c35`. All 216 profile comparison panels start collapsed and offer a default Changes only filter, retaining complete readable/copyable text. Glasgow-548’s draft now preserves its full captured family account, adds record-limit notes and qualifies the traditional marriage without removing the story, migration context, conflicting dates or namesake links. Nine focused tests, scoped desktop/mobile interaction checks, release totals, Atlas destinations, publication boundary, gzip integrity and seven selected archive/current-file hashes pass. Research inputs, profile pages, queue, manifest and local index are synchronized. No WikiTree save or production upload performed. Verification: `output/profile-diff-controls-verification-20260930.json`.

## Eleven-profile preservation audit — 30 September 2026

All eleven pending WikiTree biographies were checked against fresh anonymous public captures and reconciled passage by passage. Restored family facts, context, quotations, estimates, dated search history and source limitations; retained supported corrections and competing death indications. All 180 complete existing reference bodies, source URLs and profile links remain. SHA256 review fingerprints invalidate changed captures or replacement drafts. The maintained drafts, queue/register, public people pages/data, research manifest and local index are synchronized. Individual kit-level comparisons are withheld from public summaries; broad historical conclusions remain. Ten focused tests and scoped browser checks pass. No live WikiTree save or production upload occurred.

New upload bundle: `www/glasgow-site-20261001-000224.tar.gz`, 144,115,274 bytes (144.12 decimal MB), SHA-256 `4c7da9be4d1eebf2a4fa69e03ae97911035844a78bacb7478169421f19ba39a9`. Release totals, Atlas destinations, publication boundary, content-hash asset versions, complete gzip stream and 26 selected manifest/local-file hashes pass. Supersedes the 23:30 package. Audit: `research/profile-preservation-audit-2026-09-30/audit.md`; verification: `output/profile-preservation-verification-20260930.json`.


## Performance release — 1 October 2026

Upload bundle: `www/glasgow-site-20261001-111836.tar.gz`, 149,273,265 bytes (149.27 decimal MB), SHA-256 `821b186d65e26e30e5024c0902e24c5344294a99628de6d458f238a7dcbbfb04`. This supersedes all earlier bundles. All 79,443 archived files match the internal manifest; 16 critical page/asset/data hashes also match current local files. Gzip integrity, release totals, Atlas destinations and publication boundaries pass. Browser gates pass at 320/390/1440 px; 35 focused tests and 80 search parity cases pass. See `docs/site-experience-checks.md` for budgets, retained source data and existing full-suite limitations.

Superseded local bundles (23 files) were moved intact to ignored `archive/site-releases/`, outside the public website tree. Their relocation ledger is `archive/site-releases/moved-20261001.json`; historical bundle names in earlier notes refer to this retained location. During the owner’s authorized server upload, remove superseded tarballs from the host/CDN as described above.

No production deployment or Git push was performed. Production caching still requires the host to honour the supplied `.htaccess` or `_headers` configuration and must be checked after upload. Verification: `artifacts/site-performance-release-verification.json` and `artifacts/site-quality-report.json`.

## Full-suite repair release — 1 October 2026

Latest verified upload bundle: `www/glasgow-site-20261001-121650.tar.gz`, 149,136,681 bytes (149.14 decimal MB). SHA-256: `8f105cf1c446769e34c335a502b5d9827f7eb7e750b0f21fd2338ca908187a9c`. All 79,443 public files match the internal release manifest; eight affected pages/assets also match current local files. Verification: `artifacts/site-suite-release-verification.json`. Superseded bundles are preserved outside the public root in `archive/site-releases/`.

The final full suite runs 406 tests with zero failures/errors; six archived-migration checks require the unavailable `www_old` reference and remain skipped. Lint, data validation, dependency checks, all 18 browser gates, release totals, Atlas destinations and publication boundaries pass. This release includes corrected date qualifications, refreshed map/comparison data, accurate work-queue counts, retained merge redirects and the smaller identity resolver index. No push, live profile edit or production deployment was performed.

## Production verification — 1 October 2026

After the owner reported the upload, read-only checks against
`https://glasgow.phenotype.dev/` confirmed all 16 sampled pages, scripts,
stylesheets, packed datasets and source fragments match the local release
byte for byte after gzip decoding. The public catalogue checker and release
smoke checker pass. All sampled requests return 200 over HTTPS; three
conditional requests return 304. Versioned asset URLs work.

Browser checks covered 320, 390 and 1440 px. Search returned the expected
385 Alexander matches, with 50 on the first page; initial search readiness
was 530–771 ms in fresh, unthrottled browser contexts. Filters, findings
pagination (including without JavaScript), source deep links, the filtered
map and merged-profile redirects work. The newly added Gray candidates
compare successfully. The copy handler passes all 167,286 characters of
Alexander's revised biography to the Clipboard API with the same SHA256 as
the maintained draft. That check intercepted the API argument rather than
altering the owner's operating-system clipboard.

The initial 18-page browser run passed all checks except one 320 px tree
layout-shift measurement of 0.106 (limit 0.10). Three isolated repeat runs
measured 0.068, so retain this as an intermittent concern rather than claim
the original run was fully green. No horizontal overflow or JavaScript
page errors were observed. Additional records, places, comparisons and
filtered-map checks passed at 390 and 1440 px apart from the comparison
button's contrast finding below.

Remaining work:

- The host omits `Cache-Control` on all 16 samples, including versioned
  assets and hash-named fragments. Gzip and conditional revalidation work,
  and Cloudflare serves some cache hits, but the supplied `.htaccess` and
  `_headers` policies are not visible in live responses. Configure the
  origin/CDN to revalidate HTML and unversioned data, and serve content-hash
  asset URLs with `public, max-age=31536000, immutable`; verify actual
  responses after applying the rules.
- `#compare-submit` fails WCAG text contrast at both tested widths. Its
  text colour needs correction in the maintained stylesheet and a new
  verified release before the owner uploads it.

Evidence: `artifacts/site-live-release-http-20261001.json`,
`artifacts/site-live-quality-20261001.json`,
`artifacts/site-live-tree-cls-20261001.json`,
`artifacts/site-live-secondary-20261001.json`, and screenshots under
`output/playwright/site-live-*-20261001.png`. These are lab observations,
not production field measurements. No host configuration, site content,
Git push or WikiTree edit was performed during verification.

## Applying caching on an Nginx origin

Uploading `.htaccess` or `_headers` does not configure Nginx. Two maintained
includes are available in `deploy/nginx/`: `cache-map.conf` goes inside the
existing `http {}` context; `cache-headers.conf` goes beside the existing
`add_header` directives in this site's serving `server {}` or `location {}`
block. Keep the current document root, TLS settings and routing intact.

The policy revalidates HTML and unversioned files, gives one-year immutable
caching to content-hash CSS/JS/JSON/CSV query URLs and hash-named catalogue
details/source fragments, and sends `no-store` for errors. A hash query does
not make HTML immutable. Conditional 304 responses retain their cache policy.

Nginx replaces inherited `add_header` directives when a child block defines
its own. Preserve all current security headers and apply the cache include
at the effective serving level; an asset location with its own headers will
otherwise bypass a server-level include. Disable conflicting `expires` or
duplicate `Cache-Control` directives at that same level. This follows the
[Nginx header](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
and [map](https://nginx.org/en/docs/http/ngx_http_map_module.html) documentation.

Run `nginx -t` before reloading the configured host. The project provides
`.venv/bin/python tools/check_nginx_cache.py` to test these exact includes
in an isolated local Nginx process, including immutable/revalidation rules,
invalid versions, unhashed fragments, 404 responses and conditional 304s.
It does not edit or reload the host's existing server configuration.

After the owner supplies the host connection and configuration location,
apply the matching host policy and check actual production responses.
Cloudflare cache rules must respect the origin policy; existing cached
responses may require a targeted purge of the changed URLs. A successful
local Nginx test does not confirm live caching. Apache and compatible static
hosts should use the bundled `.htaccess` and `_headers` instead.

## Follow-up fixes prepared — 1 October 2026, 13:55

New upload bundle: `www/glasgow-site-20261001-135520.tar.gz`, 149,133,900
bytes (149.13 decimal MB; 142.23 MiB). SHA256:
`95be56399f4edb92277c4190c2652d42f6a0cb526b72a9ea93ffe0c51fccf941`.
All 79,443 public files match the internal manifest; ten critical pages,
stylesheets and host-policy files also match the final local files. Gzip,
release totals, Atlas destinations, publication boundaries and asset
versions pass. The superseded 12:16 bundle is retained intact in
`archive/site-releases/`, with `moved-20261001-followup.json` recording it.

The Compare button now has white text on its green background. The tree
reserves the Menu label's width and omits the empty location-picker space
before that picker moves into Filters & tools; all ten location controls
remain visible there. Empty place/comparison containers reserve space to
prevent the footer jumping when their cards load. Maintained styles and
public assets are synchronized; generated URLs use the new content hashes.

All 27 final browser cases pass at 320/390/1440 px, including actual Gray
comparisons, accessibility, overflow and performance limits. Maximum CLS
is 0.0921 and blocking time 146 ms; tree CLS is 0.0326/0.0761/0.0283 at the
three widths. Eleven focused Python tests and all nine self-contained
browser fixture cases pass. The real isolated Nginx verification passes
eleven cache/status cases plus a conditional 304. The wider genealogy
suite was not rerun for these style/configuration changes.

The owner subsequently uploaded the site fixes; verification follows below. Live
cache headers remain unresolved: there is no confirmed connection to this
site's origin, and the available Cloudflare dashboard is signed out.
The Nginx includes above are ready to apply if the origin uses Nginx;
the owner's hosting details are required before changing production.
No production upload, host change, Git push or WikiTree edit was performed.

Verification: `artifacts/site-followup-release-verification-20261001.json`,
`artifacts/site-followup-quality-20261001.json` and
`output/playwright/site-quality-compare-mobile.png`.

## Follow-up production verification — 1 October 2026, 14:49 UTC

After the owner's upload, all five sampled pages/stylesheets return HTTP
200 with gzip and match the current local release after decompression.
All nine browser cases pass for the tree, places and an actual Gray
comparison at 320/390/1440 px. No page errors, serious/critical accessibility
violations or horizontal overflow were observed; maximum CLS is 0.0341
and blocking time 194 ms. These are scoped lab measurements.

All five responses still omit `Cache-Control`. Applying and verifying the
appropriate origin/CDN policy remains the next priority; hosting details
are still required. No host configuration or Git push was performed.

Evidence: `artifacts/site-followup-live-http-20261001.json` and
`artifacts/site-followup-live-browser-20261001.json`.

## Free-space library redesign — 1 October 2026

The library now has three starting routes, a topic sidebar with selected states, compact study rows, year-aware search and 12-study pagination with shareable URLs. Mobile layouts and printing preserve access to all matching studies. All 85 reading bodies, citations, comparisons and complete drafts match the previous bundle unchanged. Six focused tests and 92 browser checks pass at 320/390/1440 px; the legacy parity test is skipped because `www_old` is unavailable. Local entry-point, publication-boundary, release-total and asset-version checks pass. Shared generated changes are limited to cache versions.

Verified upload bundle: `www/glasgow-site-20261001-215445.tar.gz`, 148,098,794 bytes (148.10 decimal MB), 79,444 rootless members. All 86 Free-space HTML pages and both assets match local files and the embedded release manifest; gzip integrity passes. SHA-256: `097a7d5edca652eeef0e845e0313446697d1c01c505f231b2926d2db90d101c0`. Verification: `output/playwright/free-space-release-verification.json`. Supersedes the 13:55 package. Production upload remains pending.

## Free-space collection-led redesign — 1 October 2026

The opening view now features the name-study overview, four reading routes and six subject collections. Principal studies retain their existing public conclusions and qualifications, with related reading and complete topic lists. Search opens the paginated full study list; previous bookmarks, no-JavaScript access and full matching-result printing remain supported. Desktop, tablet and mobile compositions have been visually checked. Eleven focused tests and 180 browser checks pass, including WCAG serious/critical checks in both browsing views. All 85 reading bodies match the prior bundle unchanged. Research data and publication approvals are retained; this presentation-only release uses the targeted library builder, content-hash stamping and read-only release checks.

Verified upload bundle: `www/glasgow-site-20261001-223450.tar.gz`, 148,103,738 bytes (148.10 decimal MB), 79,444 rootless members. All 86 Free-space HTML pages and both assets match local files and the embedded release manifest; gzip integrity, release totals, publication boundaries and asset versions pass. SHA-256: `99c2f961a0ca28699f7dd694d7bab93932ef5d7cd566730ee93ff5a7c6da5d63`. Verification: `output/playwright/free-space-collections-release-verification.json`. Supersedes the 21:54 package. Production upload remains pending.

## Prepared local newspaper research release — 3 October 2026

The expanded search inspected 28 candidate pages and retained nine surname pages plus one separately labelled place-study page. Seven person accounts, the Montgreenan name-study account, Lisnagaver/Rasharkin and Larne/Kilwaughter studies, Sources and six Latest findings entries are synchronized locally. The public newspaper catalogue now has 50 pages: ten surname pages including the earlier 1740 record, one place-study page and 39 excluded early place/vessel hits. This is a curated catalogue, not an exhaustive search. Identity and date conflicts remain explicit; no live WikiTree save occurred.

Verified upload archive: `www/glasgow-site-20261003-134628.tar.gz`, **150,228,451 bytes (150.23 decimal MB)**. SHA-256: `d092d5c3f5eb2893bd809091b798e3e9e12896fc74fbf64597cb22549ae35f96`. All 79,473 public archive files match the embedded manifest; 22 affected page/data hashes also match current local files. Release totals, Atlas destinations, publication boundaries and asset versions pass. Twenty-nine focused tests and scoped desktop/mobile browser checks pass. Verification: `output/newspaper-study-expansion-20261003.json`. Supersedes the 2 October 22:54 local newspaper package. **No production upload was performed; the live release remains the one documented above.**

## Prepared local Lisnagaver–Rasharkin newspaper release — 3 October 2026

The locality expansion searched 81 query/date combinations, oldest first, and read selected hit passages in 54 result pages; broad result sets remain sampled. Two retained Belfast pages repeat one death notice for Daniel Glasgow of Kilrea, dated 16 October 1871: Church Street residence, age 73 versus 75 in the civil register. Daniel’s profile, the Lisnagaver–Rasharkin study, newspaper review, Latest findings and pending WikiTree amendment are synchronized locally. The amendment preserves the complete captured biography and adds only one sourced paragraph. The public newspaper catalogue has 52 curated pages (12 surname pages, one place-study page and 39 early exclusions).

Verified upload archive: `www/glasgow-site-20261003-235723.tar.gz`, **150,321,204 bytes (150.32 decimal MB)**. SHA-256: `73f6c6ebd65ef6dbe75e52636190d9978be36a8e8ee2e433c253912f4b8594c1`. All 79,478 public files match the archive manifest; eight affected page/data hashes match local files. Release totals, destinations, publication boundaries and asset versions pass. Verification: `output/newspaper-local-expansion-20261003.json`. Private originals: `artifacts/newspapers-lisnagaver-rasharkin-20261003.zip` (7,716,684 bytes), two scan hashes verified. **Local package only; no live WikiTree save or production upload.**

## Prepared local William Glasgow newspaper release — 4 October 2026

Eighteen additional surname pages, eight dated findings, nine complete HOLD evidence drafts and six complete source-preserving profile proposals are synchronized into the newspaper review, Derryloran/Cookstown study, people, Latest findings and held/pending queue. The mill case distinguishes two Williams; its singular Robert father clause remains unassigned. A current July 1870 action strongly separates Drapersfield Benjamin from Benjamin-2059. No parents for John-2058 or relationship upgrade are established. Northern Ireland: 100 result entries loaded, 98 unique pages, 71 saved snippets reviewed; the separate 134-entry Ireland-country set remains incompletely read. These counts are not full-page transcription counts.

Verified local upload archive: `www/glasgow-site-20261004-011343.tar.gz`, **150,336,671 bytes (150.34 decimal MB)**. SHA-256: `604e8ed664457bf7c52b273c8ff0cb7e12068f9834d70f34e197f366a220ee6d`. All 79,493 archive files match its manifest; 20 affected files match local hashes. Release totals, destinations, publication boundaries and asset versions pass; desktop/mobile reading and complete comparisons checked. Verification: `output/newspaper-william-identities-20261004.json`. Private originals: `artifacts/newspapers-william-glasgow-20261004.zip`, **7,679,471 bytes (7.68 decimal MB)**; 20 captures, 71 snippets, two inspected civil PDFs, CRC and hashes verified. **Local package only; no live WikiTree save or production upload.**

## Prepared local pre-1900 newspaper coverage release — 4 October 2026

Five new surname pages and the corrected 1858 mill testimony are integrated into the catalogue, family drafts, Latest findings and pending amendments. Benjamin's testimony expressly names his late father Robert; the existing-profile identity remains held. The infant John George notice and inspected gravestone support adding George to Glasgow-2542 and marking his existing father-2059 connection Confident; this proposal is unsaved. The cross-column Richard/city match is withdrawn. The catalogue records 230 pages: 82 inspected (35 surname, one place study, 46 exclusions), with 148 pending full passage/identity review. All 157 Northern Ireland Benjamin result pages and 166 snippets were captured and screened; worldwide coverage remains incomplete.

Verified upload archive: `www/glasgow-site-20261004-033240.tar.gz`, **150,756,244 bytes (150.756244 decimal MB)**. SHA-256: `65ab737fc17076e85e81faf140b2b44312b145fd1c2a438f5e864d13cd8f513f`. All 79,498 public files match the embedded manifest and current local hashes; gzip integrity, release totals, destinations, publication boundaries and asset versions pass. Nine focused findings tests and desktop/mobile family-draft checks pass. Verification: `artifacts/newspapers-pre1900-20261004/site-bundle-verification.json`. Private originals: `artifacts/newspapers-pre1900-20261004.zip`, **14,780,865 bytes (14.780865 decimal MB)**, 279 capture/metadata/derived files, CRC and all manifest hashes verified. This package supersedes the 01:13 newspaper package. **Local package only; no live WikiTree save or production upload.**

## Prepared local newspaper follow-up release — 4 October 2026

The original 6 January 1892 death notice names Jane Graham as Robert Glasgow's wife and associates the couple with Rasharkin. Both existing profile accounts, the Lisnagaver study, Latest findings and the source review are synchronized locally; this supports an existing marriage, with no parent upgrade. Three further original passages are resolved as city/vessel exclusions, and nine early Margaret result pages are saved as pending readings. The catalogue now has 243 unique pages: 86 inspected (36 surname, one place study, 49 exclusions) and 157 pending passage/identity reviews. The worldwide scan remains incomplete; exact-name early retrieval bounds are explicitly 1600–1749.

The release check blocked a completed profile comparison containing a withheld identifier. The comparison builder now applies the existing public privacy policy before rendering; historical paragraphs and private originals are preserved. Older generated mirrors were repaired. Synchronization checks now inspect complete public lazy fragments and report no stale or missing cases for Graham-21720/Glasgow-938. Nine findings tests, fourteen study tests and fifteen comparison/privacy/fragment checks pass.

Verified upload archive: `www/glasgow-site-20261004-043907.tar.gz`, **151,272,769 bytes (151.272769 decimal MB)**. SHA-256: `ac003cfa5fbd8c754ea1630618a9e63f9c39fb9e9b09fb54b6bf18e7c8a1bc9b`. All 79,498 public files match the embedded manifest and current local hashes; 79,499 rootless members. Gzip integrity, release totals, destinations, publication boundaries (zero failures) and asset versions pass. Verification: `artifacts/newspapers-pre1900-20261004/site-followup-bundle-verification.json`. Desktop/mobile study reading checked. Private originals: `artifacts/newspapers-pre1900-20261004-followup.zip`, **20,239,107 bytes (20.239107 decimal MB)**, 298 capture/metadata/derived files, CRC and all manifest hashes verified. This package supersedes the 03:32 newspaper package. **Local package only; no live WikiTree save, production upload or Git push.**
