# Findmypast check for pre-1550 Glasgow records — 7 Oct 2026

Question: does Findmypast hold anything before 1550 that could resolve the 27 "uncertain" parent links among the 26 pre-1550 profiles (`research/pre-1550-parent-status-audit-2026-09-27.json`)? Those links include 1095→1098, 1098→1096/1097/1168/3915/3916, 1093→3163/3181, 1097→1156/3026, 1096→3613, 1168→3908, 3921→1495/1557/3179 and 3522→3917.

**Answer: no.** Findmypast has no record before 1550 that bears on these links.

## What was checked
- **The September 2026 surname audit** (`findmypast-glasgow-audit/audit-all-rows.csv`) was re-read for event years before 1550. It has 494 record IDs:
  - No indexed person record with Glasgow as a genuine surname. The nine name-bearing rows are "Royal Household Staff" entries already rejected as false surname hits.
  - 485 full-text book pages where the word appears. Most are English school and county registers.
  - The only Scottish books dated before 1550 are the *Rental Book of the Diocese of Glasgow* vol. I (Anguline ARA347, 1509–70: Simson protocols and rental, 328 hit pages), the *Register of the Collegiate Church of Crail* (ARA383), the *Red Book of Fife*, and *Candlemakers of Edinburgh 1517–1883*.
- **New exact-surname searches today**, before 1560, for Glasgw, Glasgu, Glasgou, Glesgw, Glesgow, Glasgo, Glascu, Glasco, Glascow, Glasgwe and Glasgoe. Every hit before 1560 was a full-text page of the same Rental Book volume (place-name uses: "Baronia de Glasgw", "at Glasgo", "Glasgw, the Archebischop of"). The rest were later records with no indexed date (OPR, Irish genealogical abstracts, English will indexes).
- **The Rental Book text itself.** Findmypast's own OCR of ARA347 pp. 1–356 was downloaded and scanned for every "Glas-/Gles-" form after a name. This covers the rental (1509–70) and its full personal and place indexes (pp. 240–261), plus the first part of the Simson protocols.
  - No person surnamed Glasgow appears.
  - The personal index runs Gybson → Henderson with no Glasgow entry.
  - The only personal use is a note signed "G. Glasgw." (the archbishop) on p. 124.
  - This independently confirms the earlier NLS full-text result recorded in Glasgow-1098 ("No Glasgow parent bridge").
- **Pages 357–559** (the rest of the Simson protocols and their index) were not fetched: Findmypast's daily transcript limit was reached. They were already searched in the NLS text.
- **The Crail, Fife and Candlemakers pages** (44 IDs in `tmp/fmp-studies/ids_otherbooks.txt`) were not fetched for the same reason. The four sample pages read show the word used as a place or in modern genealogies only.

## Where the pre-1550 leverage still lies (outside Findmypast)
The archival actions in `medieval-glasgow-bridge-1447-1534/report.md` §10 remain the route: GUA charters BL204/BL68/BL82, the St Andrew prebend original, NRS NP1/5 protocols, GCA B/10/1/3, and so on. One printed series is almost absent from the corpus: the *Acts of the Lords of Council in Civil Causes* (1478–1503) and *Acta Dominorum Concilii* (1501–54), which turn up in only one file. These record litigation among burgh families and sometimes name heirs. Neither is on Findmypast.

## Extension to 1550–1600 (same day)

**Indexed person records.** Findmypast has exactly five Glasgow-surname records dated 1550–1600. All five are already assigned to profiles (see `../findmypast-glasgow-pre1600.md`):

| Record | Profile |
| --- | --- |
| Robert, burial, Holkham, Norfolk, 23 Mar 1559 | Glasgow-4063 |
| John "in Hirmenschelis", Edinburgh testament, 4 May 1577 | Glasgow-3181 |
| Margaret, "sometime spouse to John Edstoun, in Croftmalloch", testament, 8 Nov 1580 | Glasgow-3613 |
| Ninian, Glasgow burgess "as second son to Robert G., fisher, burgess", 23 Oct 1596 | Glasgow-3188 |
| Andrew "in Corstoun, parish of Calder-Cleir", testament, 10 Jul 1598 | Glasgow-3163 |

A sixth row (`SCOT/BURGESS/0025937`, 3 Oct 1581) is "my lord Archbishop of [Glasgow]", a title rather than a surname.

New searches made today:
- Exact-surname searches on Glasgow, Glasgw, Glasgu, Glesgow, Glasgo, Glasco, Glascow, Glasgoe, Glasgou, Glascu and Glasgie, for 1550–1600.
- A variants-on Scotland search.
- Searches on year of birth 1564–1610 and year of death 1550–1610.

They added no new indexed person. The earliest Glasgow baptisms Findmypast indexes are the Mid Calder (Midlothian) series from 1605. The next testaments are Geillis 1603, Katherine 1605, Ninian 1607 and John 1610, all after the window.

**Full-text book pages in the window, not yet read.** Today's transcript limit stopped these. Their IDs are queued in `tmp/fmp-studies/ids_1550-1600_books.txt`:
- *Register of Marriages for the Parish of Edinburgh 1595–1700* (SRS), pp. 282, 548, 563 and 738. The printed edition was already read in `../opr-marriages-to-1700/findings.md`, so these are expected to duplicate it.
- *Holyrood* marriages, pp. 24, 84, 88 and 107.
- *Roll of Fellows of the Royal College of Surgeons of Edinburgh 1581–1873*, pp. 55, 57, 60 and 69.
- An SGS volume (0110, 1555–1807) whose title is not yet identified, pp. 32, 35 and 61; its p. 32 matched the spelling "Glascu".
- The Crail register, *Red Book of Fife* and *Candlemakers of Edinburgh* pages.
- The rest of Rental Book vol. I (pp. 357–559).

**Conclusion.** For 1550–1600, Findmypast's indexed records add nothing beyond the five events the project already uses. Any remaining possibility is in the unread full-text pages above. The uncertain links among the pre-1600 profiles still depend on the protocol-book and archive work outside Findmypast.

## Correction to the 1550–1600 extension (same day)

The first extension used year-window searches that returned 1,600–2,300 results each. Findmypast caps paging at 500, so most matches went unseen. The check was redone by pulling each record category in full, with no truncation: Scotland, surname Glasgow, 1550–1600, both exact and with variants, plus all countries for wills, burials, guild, government, surveys, apprentices and family histories.

- **Indexed person records, complete list:**
  - The five already-assigned events (1559, 1577, 1580, 1596 and 1598), plus the 1581 archbishop title.
  - One new record not in the corpus: **Jhon Glascow, burial, Shustoke, Warwickshire, 1562** (`R_21667272899`). It is English, with no link to the Scottish network shown.
  - Scottish parish baptisms under any Glasgow spelling begin only in 1605–1609 (Mid Calder); none falls in 1550–1600.
- **Unread full-text pages (the real remaining frontier), 490 IDs** now in `tmp/fmp-studies/ids_1550-1600_books.txt`:
  - Scottish Genealogy Society parish-register volumes SGS 0042 (86 pages), 0093 (50), 0067 (27), 0058 (22), 0119 (7), 0028 (6), 0007 (6), 0110 (2), 0122 (2) and 0107 (1). Their titles are still unknown.
  - Edinburgh and Holyrood marriage registers (65 pages).
  - The Edinburgh surgeons' roll (17) and Edinburgh graduations (7).
  - The rest of Rental Book vol. I.
  - These need transcript access, blocked today by the daily limit.

## Full re-check to 1600: book titles identified and read (2026-10-07, later)

<!-- findmypast-studies-sweep-2026-10-07 pre1600-recheck -->

**What was wrong before.** The earlier passes knew only page IDs for the full-text books, not their titles. They also treated every page hit as possible evidence. Faceting the same searches by `DatasetTitle` named all 175 books. Most of them hit only because "Glasgow" appears as a **place** (city, see, university). The full list is in `tmp/fmp-studies/pre1600_titles.txt`.

**Books read in full from free archive.org copies.** Four parallel checks read the printed text of every pre-1600-relevant Scottish book:

| Book | Glasgow-surname people ≤1610 | New to corpus |
|---|---|---|
| *Extracts from the Records of the Burgh of Glasgow* I (1573–1642) | Stevin 1574, **Stevin 1589**, **Robert 1573–4** | 2 |
| *Burgesses & Guild Brethren of Glasgow 1573–1750* (SRS 43) | Ninian 1596 (son of Robert, fisher) | 0 |
| *Rental Book / Liber Protocollorum* (Bain & Rogers 1875), both vols | none: all place, see or archbishop uses | 0 |
| Macfarlane's *Genealogical Collections* (SHS 1900), both vols | none | 0 |
| *Catalogue of Edinburgh Graduates* (1858) | none ≤1610; Thomas Glasgow MA 1671 | 1 (post-1610) |
| *Register of the Collegiate Church of Crail* (1877) | none | 0 |
| *Collection of Epitaphs … chiefly in Scotland* (1834) | none | 0 |

**New items:**
- **Stevin Glasgw, water bailie of Glasgow, 4 Oct 1589.** Burgh Records I p.146: "The prouest, baillies, and counsall hes electit Stevin Glasgw watter baillie for this yeir". The project had him as water bailie only in 1585 ([[Glasgow-1093]]).
- **Robert Glasgw's tenement, burgh accounts 1573–4.** Burgh Records I p.463: the treasurer is discharged "as restand and nocht in vse of payment of Robert Glasgw tenement". This may be the Robert, fisher, whose second son Ninian became a burgess in 1596.
- After 1610:
  - Robert Glasgw, burgh officer, 11 Jun 1625 (Burgh Records I p.347).
  - Mr John Glasgow, minister at Kilbirnie, burgess and guild brother gratis, 1705 (Burgesses p.260; [[Glasgow-1073]]).
  - Thomas Glasgow, MA Edinburgh 1671 (Graduates p.100).
  - James Glasgow, burgess of Kirkcudbright, 1625 (`SCOT/BURGESS/0052718`), not in the corpus; transcript queued.
- **Index false positives resolved.** The Findmypast burgess-index entries for 1581, 1633 "Patrick" and 1662 "Andrew" are archbishops: Montgomery, Patrick Lindsay and Andrew Fairfoul. "My lady Glasgow" in 1608 is the archbishop's wife. None is a surname bearer.

**Citation problem found.** [[Glasgow-1096]]'s research brief and live biography quote "lands of the late William Glasgow on the south … James Young" as *Liber Protocollorum* vol. II p.87. In fact:
- That page is protocols 112–113 of 1505.
- Vol. II ends in 1513 and does not mention Young.
- The clause almost certainly comes from Renwick's *Abstracts of Protocols of the Town Clerks of Glasgow* (archive.org `abstractsprotoc08robegoog`), which the same file mislabels "Liber protocollorum Vol. II, Record 1058".

Separately, [[Glasgow-1093]] cites the 1555 Zowng/Crownare entry as vol. 2 p.160; it is vol. I p.160.

**Queued page IDs triaged.** The SGS volumes in the 490-ID queue are mostly 19th-century Edinburgh cemetery inscriptions that matched the loose year filter:
- 0042 Grange
- 0093 Rosebank
- 0067 Newington
- 0028 East Preston St
- 0122 Broughton Place
- 0058 probably Liberton

These are dropped. The remaining real frontier, in priority order, is `tmp/fmp-studies/ids_pre1600_priority.txt` (519 IDs):
1. Kirkcudbright burgess 1625.
2. Four undated Glasgow entries in the GPC *Transatlantic Migration Indexes* (`US/GPC/02500460`, `02448029`, `02448030`, `00633657`), possibly from Dobson's *Scots-Irish Links 1575–1725*.
3. *Scots in Prussia* vols 3, 5, 6 (SGS 0107, 0109, 0110). Vol 6 is the matriculation lists from 1555, and its p.32 matched "Glascu".
4. Dobson, *Scots-Irish Links 1575–1725*, Pts 1–5 (~350 pages).
5. *Red Book of Scotland* I (97 pages).
6. *Historic Families of Fife* (30).
7. *Transatlantic Voyages 1600–1699* (47).
8. Edinburgh and Holyrood marriages and the surgeons' roll.

These are not free online, and the transcript limit still blocks them.

**Conclusion.** Every Findmypast index and every freely readable book up to 1600 has now been checked. The only additions to the pre-1600 Glasgow network are Stevin's 1589 water-bailie election and Robert's 1573–4 tenement. Anything else would have to come from the paywalled books queued above.

## Second pass to 1610 (2026-10-07, night)

<!-- findmypast-studies-sweep-2026-10-07 pre1600-pass2 -->

**Why another pass was needed.** Findmypast's "Scotland, Published Family Histories" collection (303 books with Glasgow hits, all Internet Archive scans) has no title or year field. Every year-filtered and title-faceted search above therefore skipped it. Exact searches for about 25 spellings (Glasgw, Glasgu, Glesgow, Glascoo …) also turned up hits that variant matching had missed. Beyond Findmypast, the main printed record series had never been checked systematically for completeness. Thirteen parallel readers then went through the free archive.org texts. Section files are in `tmp/fmp-studies/a_sections/p2_*.md`. Novelty was re-checked against a corpus rebuilt tonight.

**What was read:**
- **Renwick's Glasgow protocols:** all 11 volumes.
- **National registers:** *RMS* I–VI; *RSS* I; *RPC* II–VIII; Pitcairn's *Criminal Trials*; *Exchequer Rolls* (indexes); Treasurer's Accounts (indexes of the volumes online).
- **Church and university:** *Fasti* (with Wodrow's 1567/1574 registers and the *Booke of the Universall Kirk*); *Munimenta Universitatis Glasguensis*; the Edinburgh graduates to 1640; King's and Marischal colleges; St Andrews (search-inside only).
- **Burgh records:**
  - Edinburgh burgh extracts 1403–1589.
  - Nine Scottish Record Society (SRS) protocol books.
  - *Registrum Episcopatus Glasguensis* and *Liber Collegii Nostre Domine*.
  - Lanark, Irvine, Ayr and Paisley burgh records.
  - All ten volumes of the Ayrshire & Galloway Collections.
- **Ireland and England:** Irish fiants, Erck, Hill's *Plantation*, *Calendar of State Papers* (Ireland and Scotland volumes online), the Border Papers, the Montgomery and Hamilton manuscripts, and the free 1622–31 Ulster muster transcriptions.
- **Family histories:** about 60 volumes, among them the Fraser family books (Pollok, Lennox, Colquhoun, Keir, Menteith, Montgomeries, Buccleuch, Elphinstone, Annandale, Douglas), Paterson's *Ayr and Wigton*, Hunter's *Biggar*, the Somervilles, Michel's *Écossais en France* and the Waus correspondence.

**New records up to 1610:**

| Who | Record | Source |
|---|---|---|
| Stephen Glasgow ([[Glasgow-1029]]) | Water bailie elected **4 Oct 1589** (settles the open date); occupier of two rood-lands in Crapnestok 1582-3; landholder on the north side of the Trongate 1585; about 15 witness appearances 1582–91 | Burgh Records I p.146; Renwick VIII 2466, IX 2774 and others |
| Stephen Glasgow | Privy Council, Sept 1592: Spreull of Ladymure is cautioner in 500 merks that he will not intercommune with the rebel Matheu Hereot | *RPC* V p.566 |
| Stephen Glasgow | College rental c.1580–90: two acres in Provansyd feued to "Margret Graham spowse to Stevin Glasgw"; his tenement | *Munimenta* I pp.172, 180 |
| "Stephen Glasco" | 1578: received restitution of herrings as procurator for the robbed Edinburgh owners. Identity with Stephen not proved | *CSP Scotland* IX p.513 |
| Robert Glasgw (1096, or Robert fisher) | Landholder 1560; witness 1562–69; **tacksman of Burrowfeild 30 Oct 1575**; "sometime" lands on the Bridgegait 1583; unpaid tenement 1573–4 | Renwick II 545, IV 1048, VIII 2509 and others; Burgh Records I p.463 |
| q. John Glasgw ([[Glasgow-1093]]) | Boundary entries 1560, 1564, 1576, 1587, 1588 | Renwick III 786, VIII 2314, X 3063, 3093 |
| q. William Glasgu | Dead by 16 Sep 1600, lands on the north side of the Briggate | Renwick XI 3700 |
| **William Glasgow in Granton (Cramond)** and **Jeane Fairlie, his spouse** | 1602–03: warded in the Edinburgh tolbooth on Mr Johne Russell's charge of burning his house of Wester Granton; certified by Cramond kirk; awarded 10s. a day in aliment. A new couple, not in the project | *RPC* VI pp.382, 388, 738, 775 (checked against the archive.org text) |
| George Glasgow, merchant ([[Glasgow-1099]]?) | 13 Aug 1606: cautioner in £200 for James Lichtbody | *RPC* VII p.648 |

**New records after 1610:**
- Robert Glasgw, burgh officer, 1625 (Burgh Records I p.347).
- Andrew Glasgow, bursar, 1630 (later deleted); Archibaldus Glasgow, matriculated 23 Mar 1631 ([[Glasgow-1101]]) (*Munimenta* III pp.257, 83).
- Robert Glasgow, writer in Ayr, 1687–88 (*Charters of Ayr* p.211).
- Mr John Glasgow, Glasgow burgess 1705 ([[Glasgow-1073]]).
- Jane Thompson, wife of Rev. Adam Glasgow ([[Glasgow-1781]]), in *Fultons of Lisburn* p.35.

**English Findmypast leads not in the corpus:**
- Glascoe at Berwick, 1597.
- Navestock, 1566.
- Walsall, 1582.
- Great Yarmouth, 1595.
- Jhon Glascow buried at Shustoke, 1562.
- John Glascoo baptised in Essex, 1564 (`R_875725910`).

**Corrections to the earlier sections of this file:**
- The 1589 water-bailie entry belongs to Stephen ([[Glasgow-1029]]), where its date had been an open question. It does not belong to [[Glasgow-1093]].
- Thomas Glasgow, MA Edinburgh 1670/71, is already [[Glasgow-3413]].

**Citation errors found** (noted in each profile's findings):
- [[Glasgow-1093]] and Graham-38221: "vol. 6" should be IX 2838, 2903, 2916 and XI 3533.
- [[Glasgow-1100]]: vol. IX is Hegate's; 2921 and 2932 should be 2903 and 2916; 3453 should be 3492.
- [[Glasgow-3163]]: vol. VIII 2867 and 2893 should be IX 2903 and 2916.
- [[Glasgow-1096]]: 1058 is in vol. IV.
- [[Glasgow-1098]]: the Howe protocols are in vol. VI.
- Protocol 307 is dated 5 Aug 1556.
- Stephen's university incorporation is under 22 Oct, not 24 Oct.
- *RMS* IV 739 is probably p.165.
- Alan-3023's year is 1494 or 1495.
- [[Glasgow-1495]]'s "grandson" claim is not supported by *Fasti*.
- *Registrum Episcopatus* no. 315 (1377) is Danielston's lay foundation, not an episcopal charter.

**Checked and empty.** None of these has a Glasgow surname up to 1610:
- *Fasti* and the Reformation registers.
- *RMS* and *RSS* I (apart from the three people already known: William 1526, Elizabeth 1552 and Robert 1580).
- Edinburgh burgh extracts and the SRS protocol books.
- Lanark, Irvine, Ayr and Paisley.
- Irish fiants and Ulster sources.
- All the family histories.

The pre-1610 Glasgow-surname evidence is concentrated in Glasgow burgh itself.

**Still unread:**
- *RPC* I (1545–69).
- *RSS* II–VIII (1529–84).
- Treasurer's Accounts II, VI and IX–XIII.
- Edinburgh burgh extracts vol. 5 (1589–1603).
- *Ayr Burgh Accounts 1534–1624*.
- Kirkcudbright council records.
- *Thirds of Benefices*.
- Hunter's *Men and Arms* (the 1630 Down/Antrim muster).
- The unpublished Glasgow protocols of 1600–05 in Glasgow City Archives.
- The Findmypast transcript queue (`ids_pre1600_priority.txt`).

## Third pass to 1610 (2026-10-08)

<!-- findmypast-studies-sweep-2026-10-07 pre1600-pass3 -->

Nine more readers covered:
- Glasgow trades and civic records (about 20 books).
- Edinburgh testaments, apprentices and marriages.
- Charter calendars and HMC reports.
- West Lothian and Calder.
- The 239 Findmypast family histories not yet read (101 volumes read after triage).
- Ulster inquisitions, Pynnar, Carew, CSP Ireland 1611–25, the Belfast Town Book and Carrickfergus.
- English printed registers (about 1,630 volumes scanned) and FreeREG.
- The full body text of *Fasti* ii and iv–viii.
- RPC I–VIII body text, RPS to 1612, Exchequer Rolls XVI and Treasurer II.

Sections: `tmp/fmp-studies/a_sections/p3_*.md`.

**New up to 1610:**

| Who | Record | Source |
|---|---|---|
| **Michael Glasgow, mason, Glasgow** | On the masons' roll c.1600; quarter master on 22 Sep 1601; fined on 27 Dec 1604 "for working at the Castle without leave of the said Andrew" [Boyd, deacon]. Not in the project (the earliest Michael known was 1679) | *Sketch of the Incorporation of Masons* (1879) pp.56, 58, 71 (archive.org `cu31924030291862`; checked) |
| **George Glasgw in Mureistoun** (Murieston, Mid Calder) | On the roll of Calder-Comitis tenants called to the wappinschaw of 4 Aug 1586 | *Analecta Scotica* I p.399; McCall, *Mid-Calder* pp.15–16 |
| George Glasgow, merchant ([[Glasgow-1099]]?) | First Dean of Guild roll, 14 Feb 1605; "George Glasgowis hous in Briggait" in the crafts' hospital rental (copied 1609 and 1614) | Crawfurd, *Trades' House* pp.49–51; *Merchants House* p.90; Lumsden, *Trades House Records* pp.24, 57 |
| "Dene Hendry off Glasgow", canon of Jedburgh | Witness, 13 Jul 1464. Probably a toponymic byname, like the "de Glasgu" clerics | *Rutherfurds of that Ilk*, app. XXIII |
| Adam Glasgow, quarrier | "payment to, 407", in the index only; the page itself has not been seen | *Treasurer's Accounts* IX (1546–51) index p.536 |
| Eliz. Glascoe | Buried 22 Sep 1582, Walsall St Matthew (Staffordshire) | Walsall register transcript p.155; FreeREG |
| Lucie Glascoe | Buried 1597, Berwick-upon-Tweed (index only) | NBI `BMD/NBI/07403544` |

**Weak or later items:**
- "David Grames man Glasgo", 1502 (*Treasurer's Accounts* II p.144): surname or place, unclear.
- Robert Glasgow, paid by the crafts' hospital 1635–37.
- Margaret (1611), Barbara (1616) and Isobel (1619) Glasgow, marriages in Edinburgh (known).
- Rev. Robert Glasgow of Invertiel (born Manchester 1846; *Fasti* v 101) and his family, including son Robert, killed 25 Apr 1915 at Gallipoli.
- Rev. James Glasgow of Coylton's widow Margaret Macfarlane Maitland (*Fasti* viii 214).
- Robert Glasgow of Kilbirnie (1720) as maternal grandfather of James Smith at Todhills.
- "Mr Glasgow of Montgreenan" bought Holehouse in 1818.
- Jane Glasgow married Wm. Hughes of St Paul, Minnesota.

**English leads resolved:**
- Navestock 1566 is Glasier.
- Great Yarmouth 1595 is Glaskon.
- Shustoke 1562 is Glascotte (WikiTree Glascotte-1).
- Essex 1564 "Glascoo" is Glascock.
- Unresolved Findmypast hits: Staffordshire (Anguline ARA223, 1571, "Glascoe"), Yorkshire (ARA202, 1599, "Glascow") and Roman Catholic records (ARA394, 1590, "Glasco", possibly Glascock).

**Corrections:**
- Margaret's testament is 8 Nov 1580, not 1578 as the 2026-09-28 audits say.
- The 1577 Hirmenschelis testator is John.
- The Belfast 1669/70 James Glasco entry may be on p.270.

**Checked and empty up to 1610:**
- RPC I (1545–69) and RPS to 1612.
- *Fasti* (all volumes now in full).
- Ulster sources to 1660.
- Charter calendars: Laing, Yester (to 1503), Paisley, Crosraguel, Ayr Friars, Kelso, and the HMC indexes reached.
- Glasgow Cordiners and Hammermen books.
- Glasgow histories (McUre, Gibson, Renwick & Lindsay, the Regality Club, Charters & Documents vol I pt 1).
- Canongate marriages.

**Still unreachable:**
- Edinburgh burgh extracts 1589–1626.
- RSS II–VIII; Treasurer's Accounts VI and IX–XIII (snippet view only).
- HMC 3rd–5th Reports.
- Yester Writs 1503–1625.
- The Calder baron-court book 1586–1601 (manuscript, Boswell of Auchinleck papers).
- The Irish Patent Rolls of James I.
- Thirds of Benefices (lending copy only).
- The Findmypast transcript queue, still blocked by the daily limit on 8 Oct.


## Fourth pass to 1610 (2026-10-15)

<!-- findmypast-studies-sweep-2026-10-07 pre1600-pass4 -->

**Sources covered:**
- **Findmypast transcript queue:** 503 of 534 pages fetched on 14 Oct before the daily limit hit again.
- **Archive catalogues:**
  - NRS: all 2,393 dated records to 1640, each details page opened.
  - Archives Hub, Glasgow City Archives and Glasgow University Archives.
  - NLS manuscripts.
  - TNA Discovery API.
  - PRONI and NAI.
- **HathiTrust full-text search** of the whole collection: about 360 phrase searches.
- **Medieval:** PoMS, Bain's *Calendar of Documents* I–V, *Rotuli Scotiae*.
- **Other burgh records:** Stirling, Aberdeen, Peebles, Dumbarton, Dundee, Perth, Inverness, Dumfries, Rutherglen, Renfrew.
- **Church records:** kirk sessions and presbyteries (St Andrews, Aberdeen, Lanark presbytery) and the club miscellanies in full.
- **Journals:** about 1,000 volumes (PSAS, TGAS, *Scottish Antiquary*, SHR and others).

Sections: `tmp/fmp-studies/a_sections/p4_*.md`.

**New up to 1610:**

| Who | Record | Source |
|---|---|---|
| **Alexander Glasgw, Coldingham area** | Creditor for seven bolls of oats in the testament of Williame Auchincraw in Flemingtoun, confirmed 20 Dec 1571: "Item to Alexander Glasgw sevin bollis aittis" | Thomson, *Coldingham: Parish and Priory* (1908) app. XXVII (from Edinburgh Testaments, probably NRS CC8/8/2) |
| **Jhone Glasgw, barony of Carnwath** (next to Libberton/Quothquan) | The phrase "Jhone Glasgw" appears on 2 pages. HathiTrust is search-only, so the context is unseen | Dickinson (ed.), *Court Book of the Barony of Carnwath 1523–1542* (SHS 3rd ser. 29, 1937). Needs reading by hand |
| John Glesgw, Stirling (known person) | New charter: witness to William Murray's grant of half the Dow Croft, 8 Aug 1475 | NRS B66/25/43 (original at Stirling Council Archives) |
| **Maurice de Glasco**, Pentland | 1304: Edward I lodged in his houses; paid 5s. for damage to his corn | Bain, *CDS* IV p.476 |
| Adam de Glasgou/Glascou, Berwick (known Adam de Glasgeu?) | Juror 1315 (*CDS* III no. 461); he "and his ancestors" were seised of half a carucate in Bondington under Alexander III | *Rot. Scot.* I 268b |
| Master John de Glasgow (known) | Primary texts checked: Oxford safe-conduct 18 Feb 1379/80 (*Rot. Scot.* II 20b); canon of Moray, 5 Jul 1406 (II 178b); *CDS* IV no. 780 (1408, index only) | |

**Later (Ulster and Ayr):**
- From Dobson's *Scots-Irish Links*:
  - James Glasgow in the barony of Glenarm, 1650s [NAS GD154/512, 525].
  - John Glasgow, witness, Kilwaughter, 1691 [GD154/528/1].
  - Glenarm–Ayr/Irvine voyages of 1673 and 1682.
  - Captain James's Ayr arrivals of 1667 and 1673.
  - Margaret Glasgow, wife of George Craig, merchant in Irvine (Coleraine sasines 1711/1715, GD1/693/19–20).
- John Glasgow, whipman, 1642.
- Undated Prerogative index entries: Mary Glasgow of Mowillan and William Glasgow of Larne.

**Corrections:**
- **Strike "James Glasgow, burgess of Kirkcudbright, 1625"** from the earlier sections. The transcript reads "ArcheBischop of, ad F & B": this is Archbishop James Law (checked in the transcript).
- The four undated GPC index records are from Dobson's *Scots in the West Indies* (Robert of Montgreenan, known) and from *Nova Scotia Immigrants* (unnamed). None is from *Scots-Irish Links*.
- PoMS person 14528 merges two different men.

**Checked and empty up to 1610:**
- *Scots in Prussia* (no "Glascu" student; only "Dioc. Glascu.").
- *Red Book of Scotland* I, *Fife families*, the surgeons' roll, *Candlemakers*, *Transatlantic Voyages*.
- The other burghs listed above.
- St Andrews, Aberdeen and Lanark church records; the miscellanies; the journals.
- PRONI, NAI and TNA (place uses only).

**Next actions:**
- Read the Carnwath court book (NLS Digital / SHS).
- Order NRS CC8/8/2 (Auchincraw testament).
- NRS GD154 and the E71/E72 port books.
- Check the Northumberland Archives EP/38/1 (Berwick burials, Lucie Glascoe 1597) and Norfolk PD 26/16(S) registers.
- Read the Irish Patent Rolls of James I page by page (Google Books XD5JAAAAcAAJ).
- Remaining Findmypast queue: `tmp/fmp-studies/ids_queue_r5.txt` (the Irish abstracts with the correct `/1` IDs, Fife pages, Edinburgh graduates pages).

## Expansion to 1650 (2026-10-15)

<!-- findmypast-studies-sweep-2026-10-07 to1650-pass5 -->

**What was searched:**
- **Findmypast indexes:** every exact Glasgow spelling (21 forms), 1600–1650, split by dataset. About 4,500 rows: 3,445 book pages and 398 named records. Of the named records, 173 are dated ≤1650 and 46 are undated. 25 transcripts were fetched.
- **Ten readers on printed and online sources:**
  - The retours (both volumes in full).
  - *RMS* VII–IX; *RPC* 1st ser. IX–XIV and 2nd ser. I–VIII; RPS 1610–51.
  - 1641 Depositions; Pender's 1659 census; CSP Ireland 1625–60; Adair, Reid and Seymour.
  - Glasgow burgh records I–II; the burgess roll; Trades House; *Munimenta*.
  - SSNE; Scots in Poland and Germany; General Assembly and Commission records; the Kirkcudbright war committee; Terry's army papers.
  - The NRS, Archives Hub and NLS catalogues for 1610–50.
  - HathiTrust phrase searches; the SRO printed sasine indexes (full view); the Edinburgh burgh extracts 1589–1655.
  - 37 regional volumes re-scanned for 1610–50.

Sections: `tmp/fmp-studies/a_sections/p5_*.md`.

**New records, 1610–1650:**

| Who | Record | Source | Profile |
|---|---|---|---|
| William Glascoe/Glascow m. Catherine Fraith/Fraser | 10 Jul 1610, South Leith | OPR 692/2/9 (SCOT/OPR/MAR/1447177/1) | [[Glasgow-3075]] |
| James Glasgow, weaver in Quothquan | Defender in Symentoun's complaint (acts of 1607–08, heard 1612) | *RPC* IX p.342 | [[Glasgow-3910]] |
| An elder named only as "Glasgow", Stevenston kirk | 28 Jan 1613, at Mr John Bell's institution | Broun protocol book no. XXXII, *Ayr & Galloway Coll.* pp.191–2 | [[Glasgow-3178]] (context) |
| **Robert Glasgow, tanner, Glasgow** | 1623: listed as having left the trade over the tanning patent | *RPC* XIII p.246 | [[Glasgow-1027]]? |
| Robert Glasgw, town officer | **11 Jun 1625** (not 1675 as the corpus has it) | Burgh Records I p.347 | [[Glasgow-1027]] (re-date) |
| James Glasgow, tailor, Fisherrow, and **Christina Bye**; son Alexander and his wife Janet Clerk; Edward Glasgow | Sasines 1624–25 | SRO sasine index no. 38 pp.187–8 | [[Glasgow-1148]], [[Glasgow-1557]] (candidate) |
| Archibald Glasgow, student | Witness to the Blackfriars contract, 6 Jun 1635 | *Charters & Docs* I pt 2 p.363 | [[Glasgow-1101]] |
| "Archbold Glascow, clerk" | 9 Dec 1639, Ireland | Crossle abstracts (NAI doc 849) | [[Glasgow-1101]]? |
| **Issobell Glasgow**, daughter of Wm Glasgow and Issobella Miral | Baptised 26 Nov 1639, Haddington. No Haddington Glasgow was known before | OPR 709/1 p.208 | none |
| Alexander Glasgow, tailor, Fisherrow | Sasine headword 1637–43 | SRO index no. 42 | [[Glasgow-1148]] |
| Robert Glasgow, cordiner, West Port, and **Eupham Lorimer** | Sasine 1 Mar 1644 | SRO index no. 44 | [[Glasgow-3938]] |
| Alexander (Fisherrow), Edward, James (weaver) | Sasines 1646–47 | SRO index no. 44 | [[Glasgow-1148]] |
| Archibald Glasgow, Leith, and **Margaret Hilstoun** | Sasine 14 Aug 1647 | SRO index no. 44 | [[Glasgow-3078]] |
| Walter Glasgow, son of William, Leithford | Buried 4 Jun 1647, Kirknewton | OPR 689/20 | [[Glasgow-2453]] |
| Mr Archibald Glasgow, minister | Deposed winter 1647–48 (Derry/Lagan); Faughanvale £50 in 1655; under scrutiny 1658; Taughboyne 1661 | Adair p.140; Reid II pp.59–60, 559; Seymour pp.155, 169, 199–200 | [[Glasgow-1101]] (cleric candidate; formerly misfiled under Thomas) |

**Corrections and conflicts:**
- The Robert town-officer item is dated 1625, not 1675.
- Janet Clerk is Alexander's wife, not James's.
- The ministry entries were misfiled under Thomas (Glasgow-3556). They concern Archibald (Glasgow-1101 candidate); the separate 1657 catalogue reference has not been inspected and cannot yet be equated with the 1647/48 deposition.
- The Findmypast/SGS baptism readings conflict with the maintained accounts: Walter (1554), 1647 versus the supplied ScotlandsPeople/FamilySearch 1649; Margaret (3112), 1649 versus FamilySearch 1646. Earlier attribution of the SGS dates to ScotlandsPeople was incorrect.
- Glasgow-1167’s biography still names the former minister attachment, but the live structured father is the Edinburgh slater Glassfuird-2. The index reads Johnne Glasgow; preserve the August correction pending the original.
- The attachment of William-1556 to 3075 is doubtful.
- Robert-3938's 1652 marriage needs re-checking.

**Known: about 150.** These include about 146 Findmypast index rows already in the project, Archibald's 1647 retour, the Edinburgh marriages 1611–49, the Glasgow burgess and *Munimenta* entries, and Robert of Larne (1653 depositions).

**Checked and empty for 1610–1650:**
- *RMS* VII–IX (VII–VIII in full, IX index only).
- *RPC* to 1660 and RPS to 1651.
- The retours (apart from Archibald 1647).
- Glasgow burgh records II.
- Edinburgh extracts 1589–1655.
- 1641 Depositions (apart from Robert of Larne).
- Pender's 1659 census.
- CSP Ireland to 1660.
- SSNE and the Scots in Poland and Germany.
- General Assembly records.
- Terry.
- The witchcraft calendar (place uses only).
- The catalogues.
- English: one unclear 1619 Newcastle infant "Glasko"; the rest are Glascock or unproven.

**Still to read:**
- The Carnwath court book ("Jhone Glasgw", 1523–42; search-only, needs NLS or a library copy).
- *Knights of St John* ("Wilyame Glasgow", with Torphichen).
- SRO sasine index no. 42 entries.
- The Stevenston elder's forename (page image).
- The Crossle 1639 image.
- *Thirds of Benefices*.
- *Men and Arms*.
- Civil Survey III.

## Authenticated Findmypast follow-up — 15 October 2026

The saved, user-created Findmypast session provided subscription transcript access. A fresh exact-spelling and variants sweep covered Scottish parish records, apprentices, burgess entries, wills/probate, and the Irish Archbold Glascow abstracts. Exact Glasgow parish partitions were fully retrieved (262 baptism rows, 83 marriage rows, 21 burial rows); these provider totals include later/undated synthetic lifespan matches and are not counts of early people. Broader baptism and Ireland variants searches reached 500 rows and remain incomplete. The initial unsupported “wills & testaments” category received no coverage credit and was repeated with “wills & probate”. Exact filters and retrieval counts are retained in `followup-2026-10-15-search-log.json`.

No newly indexed, explicitly dated 1600–1650 Glasgow-surname ID was found beyond the previous named-record sweep. Re-opened transcripts add **Issobell’s birth on 24 November 1639** to her known Haddington baptism of 26 November, father Wm Glasgow and mother Issobella Miral, OPR 709/1 p.208. Her parents and compatible profile candidates are kept together in a sourced public household account.

Important corrections: the dated Crossle IDs both refer to the same image/document849; the undated SmithVII entry is document501 on another image, not an established duplicate. The 1625 Kirkcudbright James is indexed “Archbishop of”, a title hit. The Walter1647 and Margaret1649 dates are Findmypast/SGS readings, not ScotlandsPeople readings. Thomas3556’s cleric section was moved to Archibald1101; Katherine1495’s Edward lead now belongs with Edward1557. ChristinaBie-55 is a compatible existing candidate for the sasine index’s ChristinaBye. No family certainty upgrade, new live profile, or live WikiTree edit resulted.

Original Crossle images, disputed parish pages and sasine instruments remain uninspected. Earlier library-only targets, transcript queues and search-only volumes remain access gaps, not negative searches. The local site accounts retain these limits.
