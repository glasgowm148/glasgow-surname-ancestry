# Catalogue unconfirmed-identity deduplication audit — 6 September 2026

## Scope and result

All 69 entries formerly returned by **No confirmed WikiTree link** were
rechecked as person identities rather than record rows. The rebuilt queue has
56 unresolved identities: 43 creation-ready, 10 possible-profile HOLDs, one
identity HOLD and two unreviewed probate occurrences. Four pre-1500 subjects
now have confirmed individual WikiTree Space destinations and are excluded
from the unconfirmed filter.

The reduction from 69 to 56 is fully accounted for: five record people mapped
to existing profiles, four pre-1500 subjects linked to Space pages, and seven
separate record rows consolidated into three HOLD identities (four redundant
rows retired).

## Existing profiles recovered

| Retired catalogue identity | Existing profile | Identity basis |
| --- | --- | --- |
| `fmp-glasgow-17ba21591d7d`, Jon Glasgow, 6 Jul 1679 | [[Glasgow-1434]] | Exact date, Kilwinning and parents Jon Glasgow/Barbara Alason; Allison/Alason variant. |
| `fmp-glasgow-37cd5c63b64f`, Jon Glasgow, 16 Sep 1683 | [[Glasgow-1065]] | Exact date and Kilwinning; the profile already discusses the conflicting Jonet Young/Jean Gardiner index forms. |
| `fmp-glasgow-bacd8e7498f2`, Will Glasgow, 16 Apr 1706 | [[Glasgow-3408]] | Exact date, Irvine and father John; Isoabel Kert versus Isabell Kyle/Keil retained as an index/reading conflict. |
| `fmp-glasgow-27f929774fdc`, John Glasgow, 29 Mar 1731 | [[Glasgow-3006]] | Same parents, surgeon occupation, Puddockholm residence, parish and day; the original-register 1730 date controls over the FMP index year. |
| `fmp-glasgow-e9bdb7a1c978`, Margaret Glasgow, 21 Jan 1744 | [[Glasgow-3878]] | Same parents, surgeon occupation, Puddockholm and parish; the sourced 21 Aug 1743 register date controls and a second birth in the interval is impossible. |

Their record evidence is now in the corresponding `research/<WikiTree-ID>/findings.md`
files. Their generated new-person drafts were retired.

## Repeated records consolidated before identity counting

| Surviving HOLD | Records consolidated | Why it remains on HOLD |
| --- | --- | --- |
| `fmp-glasgow-7a66001e8cd6`, George Glasgow | CS143/24 and CS228/G/1/105, both 1724 | Compatible same-name Scottish proceedings, but the documents must establish whether one or two men were involved. |
| `fmp-glasgow-d086eba57157`, Thomas Glasgow | Dublin court proceedings of 1684, 1692 and 1701 | One continuing litigant is plausible; Thomas of Lifford cannot be the 1701 man, while [[Glasgow-3943]] remains only a candidate. |
| `fmp-glasgow-cc9a54fb3b86`, James Glasgow | Edinburgh apprenticeships of 1690 and 1696 | Same apprentice and weaver father; the first entry was scored out, coherently allowing re-apprenticeship, but the Lindsaylands family identity remains unresolved. |

The redundant standalone rows and drafts for the other four occurrences were
retired. Each surviving HOLD contains all records and the candidate analysis.
Five additional stale generated drafts that duplicated their already
consolidated Helen, Edward, George, James and Thomas handoffs were also removed;
each canonical surviving draft was checked to contain every source record.

## Confirmed pre-1500 WikiTree destinations

| Catalogue subject | Canonical individual Space page |
| --- | --- |
| Alexander de Glasgow, escheator | [[Space:Andrew_de_Glasgu]] |
| Alexander, son of Richard the messenger | [[Space:Alexander_son_of_Richard_messenger_of_Glasgow]] |
| Alexander, son of Richard the former constable | [[Space:Alexander_son_of_Richard_constable_of_Glasgow]] |
| John de Glasgow alias Smith | [[Space:John_de_Glasgow_alias_Smith_/_John_Glasgow_of_Saltmarket']] |

The two Richard-son pages were absent from the live site and were created from
the sourced local drafts. Both saves and public-page readbacks were verified.

## The 56 unresolved identities retained

Creation-ready (43):

`aedca3d838c1`, `ce7a886e0868`, `38a943ed5dc4`, `d8449b678fd3`,
`e0a45e457988`, `11135d44133e`, `1f9a4ce7f9bb`, `d96763598f21`,
`1acad1415f85`, `8d4bf08c43ec`, `120b52e4bd76`, `a2dbbb6de106`,
`015f1040785c`, `c5f9840e310b`, `5333ccc1e75f`, `c7dabfad5c23`,
`e37cff91091d`, `54571dfc429a`, `12395e3a9d9b`, `8534eaed42d0`,
`96dde749c693`, `b8c8c6842a85`, `cd18f5e7916d`,
`saltcoats-1637-katherine-glasgow`, `f9d3e4df7bbb`, `d3c5be859131`,
`10ad472195e9`, `5286617ad4ee`, `6cc997e45c40`, `984fa1db3c1a`,
`0840d67a902e`, `ba0ccce5c268`, `fba04c067c7c`, `fb417c9f3803`,
`57e604589b8e`, `16f49c884ed2`, `a8ea1428813a`, `c487f88da30e`,
`37b7f7e8fed2`, `033cb073721c`, `9bf49e7b9bd1`, `e47e0e47524a`,
`f325c7334f8a`.

Possible-existing-profile HOLDs (10):

`11443ace3ea2`, `a0b809464cc9`, `b741e434199b`, `cc9a54fb3b86`,
`baa0969903c8`, `saltcoats-1637-john-glasgow`, `26372d160744`,
`32d4ff293591`, `8b7fb215d258`, `d086eba57157`.

Identity HOLD (1): `7a66001e8cd6` (the consolidated George Glasgow court dossier).

Unreviewed (2): `record-james-glasgow-oritor-gentleman-1826-probate-occurrence`
and `record-james-glasgow-killycurragh-1836-probate-occurrence`.

## Durable catalogue rules applied

- A confirmed individual Space page counts as a WikiTree destination without
  being mislabelled as a person profile.
- Compatible repeated records are consolidated before queue totals are
  calculated.
- Exact dates, places, named relatives, occupations and residences control the
  duplicate comparison; conflicting index values are documented rather than
  turned into extra people.
- `OPEN`, `REOPEN` and `REOPENED` profile-maintenance rows are all parsed.
- Update priority follows genealogical impact: proved or corrected
  relationships first, then identity/conflation problems, material vital-data
  corrections, uncertain-link maintenance and source-only additions.
