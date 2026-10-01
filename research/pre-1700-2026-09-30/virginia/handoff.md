# Virginia father-proof search — 30 September 2026

## Current conclusion

**No qualifying new father proof.** Preserve all existing father links and their present certainty. Newly inspected deed occurrences below do not establish parentage. The earlier HTTP blocker for McIntosh's Norfolk wills 1710–1753 was overcome by the orchestrator's authenticated session. This agent independently inspected the exported record/index pages: a new 1729/30 Daneill Glasco witness occurrence, with no father clause. See `mcintosh1710-1753-assessment.md`.

Owned scope: `research/pre-1700-2026-09-30/virginia/`. No shared findings, website, WikiTree or browser edits. Read project research skill and website synchronization contract.

## Fresh WikiTree check

`live-profile-check.json` is a fresh unauthenticated `getPeople` response obtained 30 September 2026, with profile text and raw statuses. All five targets still have attached fathers:

| Profile | Attached father | Raw DataStatus.Father |
| --- | --- | --- |
| Glasgow-1526 | Glasgow-1157 (numeric 27923176) | empty string |
| Glasgow-1527 | Glasgow-1157 | empty string |
| Glasgow-397 | Glasgow-1157 | empty string |
| Glasgow-3519 | Glasgow-1157 | empty string |
| Glasgow-428 | Glasgow-1158 (numeric 27923184) | empty string |

These empty API flags must not be presented as newly resolved relationships. Glasgow-1158 itself has father Glasgow-1157 with raw status `20`; Glasgow-1157 has father numeric 29042221 with raw status `10`.

## Inspected collections and useful occurrences

1. Charles Fleming McIntosh, *Brief Abstract of Lower Norfolk County and Norfolk County Wills, 1637–1710* (1914). Entire free Internet Archive OCR searched with case-insensitive `glas` and resulting name index checked. IA metadata labels the series 1637–1753, but this scan is **volume 1, ending at 1710**, not the later volume. Saved `mcintosh-wills-1637-1710.txt`, `mcintosh-metadata.json`, `gammon-1693-extract.txt`.
   - [IA volume](https://archive.org/details/briefabstractofl01mcin); [OCR](https://archive.org/download/briefabstractofl01mcin/briefabstractofl01mcin_djvu.txt).
   - Only relevant Glasco index entries: Daniel and Mary, printed p.149. Norfolk Book 5, folio 215, John Gamon will 4 October 1693, proved 15 March 1693/4. Identifies Daniel Glasco as son-in-law and Mary as Gamon's daughter, his wife. **Known in-law evidence; no father of Daniel or William. Independently recovered but does not count as new father proof.**
   - Daniell Duglas/Bridget Douglas, p.118, is a distinct named household; do not treat the `glas` substring as a Glasgow hit.

2. [NCGenWeb, Currituck Deed Book 3](https://www.ncgenweb.us/currituck/deeds/db03.html), transcription searched for `GLASCOE`, `GLASGOW`, `GLASCO`, `GLASGOE`. These two occurrences were not in maintained Glasgow-428 findings or live biographies:
   - **p.45, 5 January 1736/7:** Luke and Margaret White assign a deed to Daniel Glasgoe, acknowledged 5–6 July 1737. Identifies a contemporary Daniel and land transfer, no kinship or inheritance from a Glasgow father.
   - **pp.63–64, 2 October 1736, registered 6 April 1737:** William and Margrett Muncreef convey 160 acres to Isaac Davis, south of the Northwest River; a boundary adjoins **Daniel Glasgow Junr.** The designation distinguishes a younger Daniel but does not itself prove father and son, still less William-428's father. Do not assume this was Daniel-1158, whose current death estimate is 1712.
   - **p.83, 21 April 1738:** William and Susanna Glascoe's chapel-acre conveyance is already maintained; no father clause.
   - Book 3's introductory warning says early deeds were recopied, contains mixed dates and reports date discrepancies. Retain the transcribed old-style dates and check originals before exact identity/date changes.

3. [NCGenWeb Currituck Deed Book 2](https://www.ncgenweb.us/currituck/deeds/db02.html), reviewed accessible transcription including its recopied early deeds. Its Ann Glasco widow/heir entry (p.44, 19 April 1768) concerns Robert Overton's heirs; no named father for the assigned pre-1700 Glasgow targets. Do not promote an unnamed heir relationship into a father claim.

## Earlier access gaps (later Norfolk book recovered below)

- [FamilySearch, McIntosh Norfolk wills 1710–1753](https://www.familysearch.org/library/books/records/item/166084-brief-abstracts-of-norfolk-county-wills-1710-1753?offset=11), identifier **115233**, 343 pages, Allen County Public Library, labelled Available Online. [Viewer](https://www.familysearch.org/library/books/viewer/166084/?offset=11). HTTP catalogue and viewer requests both return **403 Forbidden**. Web-tool catalogue reads metadata; viewer exposes only the empty dynamic shell. No volume pages or index read. Internet Archive title/creator queries returned volume 1 only; no later-volume OCR found. Google Books API request returned 429. **Next actual source action: obtain this volume's name index/pages containing Glasco/Glascoe/Glasgow/Glascow.** No browser was opened, per user's computer-lag constraint.
- [Library of Virginia land-patent guide](https://lva-virginia.libguides.com/land-grants) returned **429 Too Many Requests** through web tool. The landing-page collection description was readable, but surname indexes/patent images were not searched.
- Direct NCGenWeb HTTP requests, including browser user-agent and alternate www host, return **406 Not Acceptable**. Web tool does read the public deed transcriptions, so this is **not** a blocker to the reviewed abstracts, only to saving the full direct response.
- [OCCGS Currituck mixed abstracts PDF](https://occgs.com/projects/rescue/locations/north%20carolina/CURRITUCK%20County-MISC.pdf), 88 PDF pages, direct HTTP **403**; web tool can expose OCR. It repeats the p.45 White–Daniel assignment. No new qualifying father clause found. The whole PDF was not exhaustively visually reviewed.
- Lancaster and Accomack original will/deed/court volumes were not searched; web-search misses are not collection searches. IA located [Nottingham's Accomack wills 1663–1800](https://archive.org/details/willsadministrat0000nott), but no original pages were obtained in this batch.

## Search terms

Web discovery: `Glascoe Norfolk will`, `Glasgow Glasco Daniel Virginia`, `Edward Glascoe`, `Thomas Glasgow 1650`, `Daniel Glasco`, `Robert Glasco will`, `Glasgow/Glascoe site:ncgenweb.us/currituck/deeds`, `Glasco Norfolk father`, `Glasgow Currituck father`, `Glasco Norfolk 1712`, `Daniel Glascoe son`, `Daniel Glasgow father 1653`, `Glasco deed 1710`, `Glascoe Norfolk land`, `Robert Glascock 1690`, and `Glasco/Glascoe/Glasgow site:usgwarchives.net/va`. These returned compiled trees, existing in-law records, or unrelated names, not father proof. IA exact title/creator searches are saved in `ia-search.json` and `mcintosh-all-search.json`.

## Website integration handoff

The orchestrator owns shared integration. If retaining the new deed leads, add the qualified 1736/7 Daniel occurrences and the later-probate access gap to **research/Glasgow-428/findings.md**, and to the relevant Daniel-1158/locality-family account if maintained. Synchronize the Glasgow-428 person dossier and Virginia/Currituck family study/open questions. Lead with **William's father remains unresolved**; date this research batch and label both deeds as residence/property evidence only. No new father should enter any structured network or update queue. This agent has not synchronized `www/`; local synchronization remains for the orchestrator, and live deployment is separately pending.

## Shared-login follow-up

The orchestrator reports a successful FamilySearch login in shared IAB browser 2. This agent attempted the authorized hidden Book166084 tab via CUA; the tool returned `Browser is not available: iab`. CUA inventory confirmed `browsers: []`. This agent has no callable browser backend besides CUA, and no tab was created. The successful login therefore does not yet remove this agent's page-access blocker. Requested a source download or index/page captures from the orchestrator's available IAB; no credentials inspected or re-entered, and no Chrome launched.

## Authenticated recovery — supersedes the Norfolk book access gap

The orchestrator searched Book166084 natively for `Glas` and supplied images 122 and 331. This agent preserved 16 source tiles, reconstructed and visually read both printed pages, and saved hash/IIIF provenance. Daneill Glasco witnessed Richard Johnson's will dated 26 February 1729/30, printed p.122. No father, child or kinship stated. The index p.331 reads “Glases, Daniell,122.” No certain profile identification; no father count. See `mcintosh1710-1753-assessment.md` for exact scope, date limitations and site integration.
