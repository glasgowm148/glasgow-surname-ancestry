# Glasgow OPR deaths and burials through 1700

Last updated: 10 September 2026.

## Current conclusion

All seven entries in the user-supplied Scotland’s People exact-surname search
have been accounted for. One record is already cited exactly, two are probable
matches, one existing citation needs its interpretation corrected, and three
entries remain unresolved. Four existing profiles have new notes/corrections
and complete replacement drafts queued. No new profile is ready to create.

| Indexed event | Existing profile / conclusion | Action |
| --- | --- | --- |
| Dirleton, 1 July 1688, 705/10/183 | Unnamed Glasgow; no secure identity | HOLD for original wording; do not invent a child |
| Linlithgow, 14 February 1670, 668/70/653 | Glasgow-3056 already cites it, but deceased forename is blank; JOHN GLASGOW appears in other details | Correct prose; retain populated date/location uncertain |
| Elizabeth, Polwarth, 16 March 1657, 754/10/30 | Probable Glasgow-3362, child recorded locally 17 August 1656 | Add qualified prose; no structured death |
| Janet, Polwarth, 25 December 1675, 754/10/113 | TOD / WILLIAM GLASGOW; no compatible live profile found | HOLD for name and kin term; no spouse attachment |
| Jon, Duddingston, 23 August 1641, 684/60/24 | Glasgow-1559 and Glasgow-3014 are competing candidates | Qualified research note in both; shared HOLD comparison |
| Robert, Duddingston, 17 January 1647, 684/60/47 | Exact existing citation in Glasgow-1156 | Confirming evidence only; no new queue action |
| Jon, Duddingston, 15 January 1638, 684/60/16 | Probable Glasgow-3014, child recorded four days earlier | Add qualified prose; no structured death |

## Source findings

The maintained source is
`surname-research/indexes/scotlandspeople-opr-deaths-to-1700.json`, transcribed
from the user's supplied result table on 10 September 2026. It preserves all
seven rows, blank ages, gender codes, other-details text and OPR locators.
Source portal: <https://www.scotlandspeople.gov.uk/>. Original images have not
been inspected; date and relationship interpretations remain qualified. The
seven-result total describes this search, not complete historical coverage.

Relevant public live WikiTree profiles were fetched on 10 September 2026.
Their biographies for Glasgow-1156, Glasgow-1559, Glasgow-3014, Glasgow-3056 and
Glasgow-3362 agree with the saved profile evidence. Raw verification is kept
internally in `.cache/opr-deaths-2026-09-10/live-profiles.json`. Complete drafts
retain prior substantive sources and citations.

Janet duplicate review covered all pages for Janet Tod (81 results), Janet
Todd (2,617 results) and Janet Glasgow (315 results), followed by 127 unique
date-compatible profile reads. No compatible Polwarth Janet/William household
was found. This negative search does not prove Janet lacks a WikiTree profile,
nor that Tod is necessarily her birth surname. Raw search material remains
internal because broad results may include living people.

## Website synchronization

The Scottish families account displays the seven-row evidence comparison and
next searches, with a Sources discovery link and safe JSON download. Person
findings, complete drafts and update flags are synchronized for Glasgow-3014,
Glasgow-1559, Glasgow-3056 and Glasgow-3362. The pending flags refer to proposed
WikiTree amendments; no live WikiTree edits or site deployment are made.

Durable paths: the source index above, each person's `findings.md` and complete
draft, `data/wikitree/profile-update-queue.json`, `surname-research/to-update.md`,
and `tools/publish_opr_death_review.py` (registered in unified repair).

Verification: targeted source-to-site sync reports four checked, none stale,
and no missing public cases. All four visible draft bodies contain clean
WikiTree markup and retain their existing substantive citations. The regional
table has seven rows and valid local profile links; desktop and mobile browser
checks passed. The disputed 1670 death is qualified in the visible header,
vitals, life event and public machine data while the imported snapshot remains
unchanged. Repeating the OPR publisher is idempotent.

## Priority actions

Read original OPR 684/60/16 and 60/24 to distinguish the two Duddingston Johns;
754/10/30 for Elizabeth's age or kinship; 668/70/653 for the unnamed deceased
and John's role; 754/10/113 for Janet's name and relation to William; and
705/10/183 for the Dirleton subject. Do not assign unresolved people, dates or
relationships from index column position alone.
