# Ancestry Glasgow record audit

Coverage ledger for Glasgow-surname entries saved from Ancestry's free-access collections (Remembrance offer, 4–11 November 2026). The captures themselves are private and stay outside the repository; licensed document images are neither copied nor published. Reviewed entries are recorded as canonical records (`research/canonical_records.json`, record IDs `ancestry-<collection>-<record>`), each citing its Ancestry record URL and The National Archives reference.

## Rules applied

- **Publication scope.** An entry becomes a canonical record only when its subject has a sourced birth bound before 1906 (more than 120 years ago), or is exactly identified with a public catalogue profile that has a recorded death. Bounds come from an indexed birth date or age, or from a recorded role: a soldier's parent on a dated document (the soldier at least 14, the parent at least 12 at his birth), a spouse with an indexed marriage date (lawful minimum marriage age then 12), or a soldier on a dated document (at least 14). A 1914–1920 collection span alone does not bound a soldier's birth before 1906. Everyone else is a scope HOLD: counted here, never named.
- **Relatives on the same document.** In a published entry, other people on the document are named only when they meet the same rule; the rest are counted, not named.
- **Identity.** An entry is linked to a catalogue profile only when combined evidence identifies the person (for example, exact birth dates plus named spouse and children). Name and approximate date alone are not identity evidence; such entries stay unmatched Glasgow-surname records with no profile role. Companion index entries for one person on one document share a `documentary_group` and are not independent corroboration.
- **Source level.** Every entry is an inspected Ancestry index transcript. The original WO 363, WO 364, WO 372 and census images have not been inspected.

## Batch 1 — 4 November 2026

**WO 363 service records (Ancestry collection 1219):** 56 index entries captured; 36 recorded as canonical records, 2 linked to existing profiles and 34 unmatched; 20 scope HOLDs (18 born after 1905, 2 with no birth bound). **WO 372 medal index cards (collection 1262):** 2 captured, both scope HOLDs (only the 1914–1920 span, no birth bound before 1906).

**Match.** Two entries on one attestation identify the family of [Robert Glasgow-1110](/people/glasgow-1110.html), of the Camlachie/Rasharkin branch. His daughters' indexed birth dates (14 October 1912 and 3 July 1916, Glasgow) equal [Jessie Rodie Glasgow-1111](/people/glasgow-1111.html) and [Elizabeth Brownlie Glasgow-1112](/people/glasgow-1112.html) exactly, and the indexed wife, Elizabeth Macpherson, matches their catalogue mother. Both daughters have recorded deaths, so the entries are kept as canonical records with qualified roles. They are held out of the public record index, whose ingester accepts only births before 1906. The soldier's own entry and service details are not yet captured.

**Unmatched.** No catalogue profile is identified with the other 34 entries. Scottish fathers on 1915–1917 documents (Glasgow East, Shettleston, Stirling, Prestonpans and Leadhills) have only name-level candidates. Robert Glasgow-938 died in 1902 and is excluded as the 1915 Prestonpans father.

## Batch 2 — 4 November 2026

**WO 363 (collection 1219):** 12 more entries captured (68 in all); 11 more canonical records (47 in all, 45 unmatched). **WO 372 medal index cards (collection 1262):** 14 captured, all scope HOLDs. **1911 England census (collection 2352, RG 14):** 49 entries captured; 45 recorded as canonical records, 2 linked and 43 unmatched; 4 scope HOLDs (aged under 6 in 1911). Household members are named only when their indexed age puts their birth before 1906. Three entries index the surname as "Elargow", a probable misreading of Glasgow; they are recorded with that literal reading and no identity.

**Matches.** [Mary Janet Glasgow-639](/people/glasgow-639.html), 60 and single, heads a household at 8 Severn Street, Leicester, with her sister [Ann Isabella (Glasgow) Williams-640](/people/glasgow-640.html), 56: a match on full name, birthplace, ages and the named sister. [William Glasgow-1003](/people/glasgow-1003.html), 35, single and born Kendal, boards at 14 Nairne Street, Burnley, where his family had earlier lived: a probable match, with no named relative in the household. No vital or relationship changes follow.

## Batch 3 — 4 November 2026

Running totals after this batch: **303 canonical records** from 507 captured entries.

- **WO 363 (1219):** 75 captured; 52 recorded.
- **WO 372 medal cards (1262):** 21 captured, all HOLD.
- **1911 census (2352):** 135 captured; 115 recorded, 9 with profile roles.
- **1921 census (63150):** 2 captured; 1 recorded.
- **1939 Register (61596):** 58 captured; 28 recorded. There were 30 HOLDs: 22 born after 1905, 7 whose indexed surname is not Glasgow (for example Robertson-Glasgan or a household member's own surname) and 1 with no date. Closed 1939 entries are counted, never named.
- **Search-result rows only (source level "index"):**
  - Belfast News-Letter notices (2193): 190 rows; 91 recorded, 99 HOLDs (76 rows with no dated event, 23 events after the bound).
  - 1926 Irish Free State census (63564): 20 rows; 11 recorded.
  - Irish National Army census 1922 (62515): 2 rows; 1 recorded.
  - Ireland's Memorial Records (1633): 4 rows; 4 recorded.

Relatives named in a search row are published only when the row's date bounds them too.

**Matches.**
- **Irish death confirmations.** Index rows confirm the recorded death dates of 22 existing profiles: the Cookstown, Belfast, Portadown and Newry families, and three Belfast or Partick soldiers in Ireland's Memorial Records. These are confirmations only, with no date changes. Mary Elizabeth Glasgow's 1874 Belfast notice is held as a candidate comparison for Glasgow-1403.
- **1911 households.** [Robert James Glasgow-2672](/people/glasgow-2672.html) and [Roberta-2673](/people/glasgow-2673.html) at Bootle are matched, with a son Marius outside the catalogue. [John Mawson Glasgow-999](/people/glasgow-999.html) at Huncoat is matched. [William Glasgow-2060](/people/glasgow-2060.html) at Bolton is a probable match. William "Elargow" of Rock Ferry is a candidate comparison for Glasgow-2675.

## Batch 4 — 4 November 2026

Running totals after this batch: **1,049 canonical records** from 1,623 captured entries. New in this batch:
- **WO 364 pension records (1114):** 22 of 41 recorded.
- **Medal cards:** all 42 still HOLD.
- **1911 census:** 336 of 414 recorded.
- **1921 census:** 7 of 20 recorded.
- **1939 Register:** 154 of 298 recorded.
- **Ireland civil birth index (2573):** 333 of 446 recorded.
- **Scottish probate calendar (60558):** 22 of 49 recorded.
- **Scottish rolls of honour (62490):** 2 recorded.
- **Ireland Cemetery Collection (70947):** 5 HOLDs; four are post-1905 deaths.

A soldier's child with an indexed birth year before 1860 is treated as an index error and HOLD, not as evidence of an early birth.

**Matches.**
- **Robert Glasgow-1110:** his WO 364 pension record also lists his daughters.
- **Irish births:** the birth index confirms 67 profiles' births and probably 36 more; 6 registrations remain candidate comparisons only.
- **Households:** Edwin Glasgow-2671 at Newcastle, and the Swailes-Glasgow family at Low Fell, Gateshead.
- **1939 Register:** Arthur Graham Glasgow-670 at Southampton and Henry Glasgow-4318 at Poole, both probable.
- **Scottish probate:** four estates, for Ninian-3297, Alexander-2702, Wilhelmina Husband-862 and Robert Forsyth-442.

**Status: INCOMPLETE.** Workers are still saving the service, pension and medal-card indexes and the 1911, 1921 and 1939 English collections.
