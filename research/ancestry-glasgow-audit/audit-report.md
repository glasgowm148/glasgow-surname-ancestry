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

**Status: INCOMPLETE.** Workers are still saving the service, pension and medal-card indexes and the 1911, 1921 and 1939 English collections.
