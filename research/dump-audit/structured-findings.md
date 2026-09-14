# Structured dump audit — public-safe findings

**Scope.** CSV/XLS/XLSX/TXT/ONT JSON, GEDCOM, old PHP/tree exports, GlasgowGit,
Resources, and the saved FTDNA project page under `dump/`.  Trees, the OneTree
exports, and DNA material were treated as derivative leads, never as proof.  No
living-person details, credentials, kit numbers, or raw DNA values are recorded
here.

## Coverage and result

| Material | Coverage | Result |
|---|---:|---|
| Archive inventory | 1,493 files | 79 exact copies already occur in maintained collections; repeated archive copies were not re-counted as evidence. |
| Spreadsheets | 12 `.xlsx` and 4 legacy `.xls` files | Six broad OneTree snapshots (1,378–1,465 people), one pre-1700 subset (232), two identical Kilwinning subsets (28 each), and three historical network-statistic workbooks. The `.xls` FamilySearch exports were inventoried but not parsed. The reviewed sheets are profile exports, not source records. |
| GEDCOM/tree-site/GlasgowGit | 8 GEDCOMs plus static PHP/JSON/HTML | Derivative and includes private/living data.  Historical deceased-person claims were sampled where they supplied a source or a conflicting narrative. `.rmtree`, `.rmbackup`, `.gramps`, and code-bearing site files were inventoried but not executed or parsed as evidence. |
| Testament/source images | 1577–1685 supplied material | Current originals/transcriptions and public pages already cover the identifiable Glasgow testament cases. |
| FTDNA saved HTML/CSV | project display and two exports | No new documentary citation; excluded from this handoff because it contains sensitive test data. |

**Conclusion: no new record-backed person or relationship is ready to add.**
The most useful work is to prevent old export prose from being reused as current
research.  The relevant site surfaces are the Name Study, early Scotland / early
Ireland studies, John of Saltmarket dossier, and the affected person dossiers.

## Confirmed duplicate documentary coverage

| Dump item | Record/source | Maintained outcome | Status / site surface |
|---|---|---|---|
| `dump/Wills & Testaments/Glasgow/1605_Katherine.pdf` | NRS CC9/7/4; Findmypast `SCOT/WILLS/057453`, Katherine Glasgow, spouse of Thomas Weir, Stevenston, 9 May 1605 | Original, transcription, identity and spouse conclusion already maintained in `research/Weir-4172/findings.md` and the 15th/16th-century Scotland study. | **Already integrated**; `/research/transcriptions/` and early-Scotland / Name Study surfaces. |
| `dump/Wills & Testaments/Glasgow/1613_Niniane.pdf` | NRS CC9/7/9; Findmypast `SCOT/WILLS/057459`, Ninian Glasgow, fisher and burgess, 8 May 1613 | Already transcribed and assigned to Glasgow-3188; its named kin clauses are current evidence. | **Already integrated**; `research/Glasgow-3188/findings.md`, `/research/transcriptions/ninian-1613/`. |
| `dump/Wills & Testaments/Glasgow/1637_John.pdf` | NRS CC9/7/27, Saltcoats/Ardrossan testament of John Glasgow | Already establishes the sailor, widow Isobell Gray, and lawful children Katherine and Agnes without asserting wider parentage. | **Already integrated**; `/research/transcriptions/saltcoats-1637/`, early-Scotland study. |
| `dump/Wills & Testaments/Glasgow/Lanark/1650_John/1650_Glasgow.pdf` and `.../1685_John_Lanark.pdf` | Lanark commissary estates | Existing audit distinguishes the separate 1650, 1662 and 1685 John Glasgow estates. | **Already integrated**; Glasgow-3296, Glasgow-3019 and Glasgow-3331 findings; do not combine. |
| `dump/Wills & Testaments/Edinburgh/1662_Archibald.pdf` and `.../1673_William.pdf` | Archibald at Leith; William at Quothquan | Maintained originals and walkthroughs already preserve these separate records. | **Already integrated**; `/research/transcriptions/archibald-1662/` and existing 1673 material. |

## Superseded export claims — do not re-import

| Exact export location | Claim to suppress | Current evidence-led conclusion | Action / affected surfaces |
|---|---|---|---|
| `dump/GlasgowGit/glasgow-name-study.md:57-60`, `origins-timeline.md:36`, and `people/john-1475.md:160-177` | The 1506 alias-Smith John was likely related to the Stirling witness, was the 1507–13 cleric, and founded the main burgh line; the Kilwinning teind was his holding. | The 1506 BL/204 catalogue proves only John de Glasgow alias Smith and Sir Allan Smith's joint acquisition.  The 1527 Saltmarket John is William Glasgow's **probable** father by title succession; alias-Smith is only a possible earlier occurrence.  No source links either to the 1475 witness, cleric, or teind holder. | **HOLD, high confidence that the old claims are unsupported.** Keep current qualification on `surname-research/free-space-pages/John_Glasgow_of_Saltmarket.md` and its public dossier; no person profile for the pre-1500 subject. |
| `dump/GlasgowGit/glasgow-name-study.md:73,82,88` | Cunninghame associations establish a family-wide Reformation/political alliance, supported by DNA and Kilwinning memorials. | Teind and estate material document people and places, not a continuous family or political allegiance.  Individual later marriages are distinct evidence. | **HOLD.** Name Study / early-Scotland overview must retain the current evidence boundary. |
| `dump/GlasgowGit/glasgow-name-study.md:142-153` | William Glasgow (c.1656) reached Tyrone with Derry-relief forces and founded the Tyrone–Melanchthon line. | The Cavers/Ormiston Covenanter record is a candidate only.  It does not give an Irish destination or identify Glasgow-591; DNA participant labels cannot bridge the paper pedigree. | **HOLD, high confidence the asserted migration is unproved.** Early-Ireland study, Glasgow-591 dossier, and Y-DNA narrative must retain this distinction. |
| `dump/GlasgowGit/glasgow-name-study.md:9-11,82` | Deep Y-DNA and medieval/Norman stories identify the surname's founders or a continuous pedigree. | The reviewed corpus expressly says no named medieval bearer is connected to the sixteenth-century burgh family; genetic clustering describes paternal relatedness, not a historical individual or route. | **HOLD.** Name Study and `/ydna/` must not revive these as historical facts. |

## Export rows checked, not new evidence

The April 2025 OneTree spreadsheet (`dump/Glasgow_2025-04-04_15-55-58.xlsx`,
`TableData`) contains 1,463 exported profiles: 2 in 1401–1500, 19 in 1501–1600,
and 125 in 1601–1700.  The special pre-1700 export
`dump/Glasgow_2025-03-18_01-12-38.xlsx`, `TableData`, contains 232 profiles.
These date/place/parent fields have no attached record provenance. Sampling the
historical rows found the same people and old attachments already audited in the
current corpus; the export was not treated as a complete record-by-record
audit. It produces no create/update candidate.

The two Kilwinning spreadsheets are duplicate 28-profile exports.  Their
place-linked group is already covered by the maintained Kilwinning and
Corsinkell work; do not infer kinship from shared locality or duplicate export
membership.

## Next record work

1. Obtain and inspect the complete BL/204 instrument (1506) before changing
   the alias-Smith/Saltmarket identity or any relationship.
2. Seek direct Scottish/Irish evidence for the proposed William Glasgow
   migration before connecting Glasgow-591 to the Cavers prisoner or Tyrone
   family.
3. Treat unproven older exported parents, dates and places as **HOLD** until an
   original record supports the particular person and relationship.

## Integration handoff

No main-source or site mutation was made by this audit.  The current public
surfaces already contain the documentary findings; the orchestrator should only
check that any remaining old Name Study / Y-DNA presentation does not reproduce
the four superseded export narratives above.  Local publication status is
unchanged; no deployment occurred.
