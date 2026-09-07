# Findmypast Glasgow HOLD identity resolution — 6 September 2026

## Current conclusion

The earlier 1650–1750 integration treated 145 source groups as possible new
people on HOLD. A consolidation-first review now yields **117 assignments to
existing WikiTree profiles**, **44 distinct people ready for a new profile**,
and **16 irreducibly unresolved source identities on HOLD**. The scoped audit
now contains 177 documentary identities rather than 182 because repeated
William Glasgow, Edward Glasgow and Helen Glasgow rows were consolidated.

The exhaustive source-group decisions, profile IDs, handoff paths and notes
are in `catalogue-integration-plan-1650-1750.json`; the human decisions are in
`catalogue-integration-overrides.json`.

## Consolidated record groups

| Result | Records consolidated | Basis | Certainty |
| --- | --- | --- | --- |
| One William Glasgow of Cavers/Ormistoun | `GBPR/COVENANT/028558`, `028559`, `028560` | The 1679 deposition names a Cavers man serving at Ormistoun; the survivor list places William under Cavers; the 1684 list again identifies an Ormistoun servant. | High, but later relationships unknown |
| One Edward Glasgow of St Clement Danes | `GBOR/WESTMINSTER_RATEBOO/9492920/3`, `9494667/3`, `9497118/3` | Two indexes are the same house 6/folio 3 assessment; the third is the adjacent house 7/folio 4 assessment in the same parish and year. | High for the duplicated row; moderate-high for the adjacent holding |
| One Helen Glasgow of Linlithgow | `SCOT/OPR/BAP/0476082`, `0501646` | Both point to page 231, year 1668, the same child and John Glasgow/Agnes Easton or Daston; one supplies the 22 December date. | Very high |

## Existing-profile assignments

The 117 assignments use one or more of these bridges: exact date and parish;
exact parents and parish; a separately stated birth date matching the profile;
or an adult occupational trail already described on the profile. Minor
spelling forms and birth-versus-baptism differences were not treated as new
people. Important examples include:

- David, born 12 May and baptised 23 May 1742 at Livingston, belongs to
  `Glasgow-1228`, not `Glasgow-1218`.
- Robert Glasgow's 1672 apprenticeship and 1684 merchant-burgess admission
  both belong to `Glasgow-1374` because both name Robert Mein/Meane as master.
- Five Edinburgh records of James Glasgow acting as a weaver master between
  1656 and 1693 belong to the established weaver and burgess `Glasgow-1150`;
  the apprentices and their fathers are associates, not new Glasgow parents.
- The 1699 youngest-son apprenticeship belongs to `Glasgow-3285`; his age,
  Edinburgh setting and father James the weaver agree.
- The Cavers shipwreck-survivor John belongs to `Glasgow-1498`, whose profile
  already describes the event.
- The 1666 Edinburgh cordiner-burgess entry belongs to `Glasgow-3938`; the
  occupation, wife Euphame and her father Andrew Lorimer identify him.

## New-profile-ready people

Forty-four consolidated identities have a transcript-supported person, date
or bounded event period, place or contextual setting, and no compatible
WikiTree profile after review. Each has one draft even when several source
rows support the person. These are **creation recommendations**, not claims
that a WikiTree profile has been created. The complete list and drafts appear
under `new_person:READY` in `catalogue-integration-plan-1650-1750.json` and the
generated catalogue queue.

## Remaining HOLD identities

| Stable ID | Evidence cluster | Why it must remain one HOLD question | Next decisive test |
| --- | --- | --- | --- |
| `fmp-glasgow-26372d160744` | Margaret, born 1740, Edrom, father James | `Glasgow-1607` has the same year and father in nearby Kelso, but no exact date or mother bridge. | Inspect OPR 738/4 p.24 and the source behind `Glasgow-1607`. |
| `fmp-glasgow-27f929774fdc` | John, baptised 29 Mar 1731, Kilbirnie, surgeon Robert/Margaret Allan | `Glasgow-3006` has the same parents, parish and day in 1730; this may be a year error or a reused child name. | Compare both OPR images/pages 79 and 83 and seek a burial. |
| `fmp-glasgow-32d4ff293591` | Mary, born 7 Apr 1744, Kilmarnock, Hugh/Margaret Giffen | Unsourced `Glasgow-369`, about 1742 Scotland, remains compatible. | Establish or exclude `Glasgow-369` through its later family records. |
| `fmp-glasgow-37cd5c63b64f` | Jon, baptised 16 Sep 1683, Kilwinning, George/Jonet Young | Another same-day John record, assigned to `Glasgow-1065`, names George/Jean Gardiner. | Inspect the original page to resolve duplicate indexing versus two families. |
| `fmp-glasgow-46aec084bb6e` | Thomas in a Dublin Exchequer bill, 1684 | The bill-book index lacks parties, residence and title; several Thomas profiles remain possible. | Inspect Equity Exchequer Bill Book vol.5 p.102. |
| `fmp-glasgow-4f5b960fe01d` | George v Stevenson and others, 1724 | A second 1724 George action may concern the same man, but neither abstract identifies him. | Inspect CS228/G/1/105 and compare CS143/24. |
| `fmp-glasgow-59dea07d1fbb` | James, Edinburgh apothecary apprentice, 1696, son of James the weaver | The father is identifiable, but two 1679/1680 same-name sons survive as profiles and the earlier name may have been reused. | Find burial/survival evidence and the original apprenticeship entry. |
| `fmp-glasgow-7a66001e8cd6` | George Glasgow and Robert Crawford title deeds, 1724 | Same unresolved two-action problem as the other George record. | Inspect CS143/24 and compare CS228/G/1/105. |
| `fmp-glasgow-8a1040c5d545` | Thomas Glasgow, Esquire, Dublin Exchequer bill, 1701 | The title is compatible with `Glasgow-3556`, but the index exposes no property, parties or residence. | Inspect Equity Exchequer Bill Book vol.12 p.121. |
| `fmp-glasgow-8b7fb215d258` | Thomas admitted Edinburgh burgess gratis, 1660 | No occupation, relative or prior apprenticeship distinguishes four live candidates. | Inspect the council act and guild entry for identifying context. |
| `fmp-glasgow-a0b809464cc9` | Hugh, sailor at Irvine then London, enrolled 3 Feb 1733 | Several Irvine/Kilwinning Hughs have compatible ages and no voyage or relative bridge. | Inspect the underlying seafarer entry and London/Irvine maritime records. |
| `fmp-glasgow-b741e434199b` | James of Saltoun, surgeon of the *Swift* of Sheerness, 1733 | The occupation distinguishes the record bearer but has not yet been joined to any of many James profiles. | Trace the ship, naval/pay records and Saltoun residence. |
| `fmp-glasgow-baa0969903c8` | John at Antigua, 10 Mar 1707/08, in an emigrant-ministers list | `Glasgow-3161` is only an age-compatible candidate and has no Antigua or ministry bridge. | Inspect Money Book 19 p.200 and church/appointment records. |
| `fmp-glasgow-cc9a54fb3b86` | James, Edinburgh cordiner/tanner apprentice, 1690, son of deceased James the weaver of Lindsayland | Several James profiles fit; the deceased-father wording distinguishes him from the 1696 apprentice but not from those profiles. | Inspect the original apprenticeship and Lindsayland records. |
| `fmp-glasgow-d086eba57157` | Thomas in a Dublin Chancery bill, 1692 | Chronology overlaps `Glasgow-3556`, but no parties, property or title are exposed. | Inspect Chancery Bill Book vol.11 p.36. |
| `fmp-glasgow-e9bdb7a1c978` | Margaret, baptised 21 Jan 1744, Kilbirnie, surgeon Robert/Margaret Allan | `Glasgow-3878` has the same parents and parish but an August 1743 date; the five-month interval makes a second birth impossible and points to a record/date problem. | Compare the OPR entries/images before merging or creating. |

## Decision rule retained

HOLD means that no profile should be created or merged yet. A source row is
evidence, not a person. A new profile is READY only after compatible facts are
clustered and every surviving WikiTree candidate is excluded; otherwise the
facts stay in one consolidated evidence handoff.
