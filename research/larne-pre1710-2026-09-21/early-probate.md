# Early probate — focused search, 21 September 2026

**Result: no new pre-1710 record text or kinship proof recovered.** Current relationships remain unchanged.

## Chosen lead

James Glasgow of Belfast’s 1686 will extract, PRONI **T828/15**, described by [NLI MS_UR_012684](https://sources.nli.ie/Record/MS_UR_012684). This is the surviving pre-1710 probate lead in the maintained Larne notes most likely to name kin. The 1727 Kilwater James index explicitly warns that its original and further information did not survive. The present attempt therefore sought a digitised substitute for the 1686 extract in the **Virtual Record Treasury of Ireland**, rather than retrying the previously inaccessible NLI catalogue.

## Actual new access result

The [Virtual Treasury](https://virtualtreasury.ie/) public application exposes a working anonymous search endpoint, `https://by2022-prod.adaptcentre.ie/IR_REST_V2/webapi/doc_search`. Its JavaScript uses a JSON POST with `indexDBName: beyond_2022`, `kwList`, `kwSearchFieldList`, `kwOperList`, `totalElementsInt`, and `pageNumberInt`. No authentication was needed or used.

Exact-phrase searches (operator `EXACT`, all fields unless noted):

| Query | Returned items | Assessment |
| --- | ---: | --- |
| James Glasgow | 8 | Later Holmes will abstract/adjacent items sharing page OCR; two 1766 census sources; a 1752 Gazette; Vicars index. No 1686 Belfast extract. |
| James Glasgo | 0 | Search result only; not an exhaustive variant audit. |
| James Glasco | 0 | Same limitation. |
| T828/15, reference code | 0 | No matching catalogue record returned. |
| T/828/15, reference code | 0 | No matching catalogue record returned. |
| Nicholson Papers | 0 | No matching phrase returned. |
| Connor wills | 4 | Deputy Keeper report records, not the sought extract. |

[Reproducible public search route](https://virtualtreasury.ie/search-results?kwList=James%20Glasgow&kwSearchFieldList=all&kwOperList=EXACT&totalElementsInt=20&pageNumberInt=0). The web-text tool could not render this search route, but its public backing search returned structured results successfully.

**Newness:** this establishes a previously unused, accessible archive search route and bounded negative results. It does not establish that T828/15 is absent from all digitisation, or that no substitute survives. No beneficiary, executor, probate date or death date has been read. The 1686 will date still cannot by itself exclude identity with a later James.

A useful access side result is that the previously blocked IMC volume III is indexed with images/transcriptions in VRTI, including [IMC 1954/RoD/3/1800/237](https://virtualtreasury.ie/item/IMC-1954-RoD-3-1800-237), Alexander Holmes’s 1799 will. That is an already-known later record, not new pre-1710 evidence. Adjacent abstract records also match because their shared page OCR contains the Holmes text: do not misattribute its James Glasgow passage to those other testators. No new image reading was claimed here.

## Affected profiles and public integration

Direct targets: Glasgow-1081 and collateral Captain Glasgow-3172; downstream hypotheses Glasgow-1502 → Glasgow-1143/1499 remain unproved. Glasgow-1509’s later ropemaker evidence does not bridge these early generations. Root may add the VRTI search result to the Larne open-source questions; no family-status upgrade or live edit is supported. This handoff is deliberately not a new public conclusion.
