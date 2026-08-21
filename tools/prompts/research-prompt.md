You are doing a **professional-level genealogical evidence review, deep research investigation, and rewrite of an existing WikiTree profile**.

I have attached an existing WikiTree profile, biography, research notes, or equivalent material.

**Treat the attached/pasted profile as the target automatically and begin the work immediately.**

Do not ask me what I want done. The task is defined by this prompt.

Only ask a clarifying question if the profile itself is genuinely missing or unreadable and there is no usable profile text in the conversation. Otherwise make reasonable assumptions and proceed.

Your job is to:

1. research the person deeply;
2. audit and test the existing profile claims rather than repeating them;
3. find additional relevant records, relatives, candidate identities, migrations, associates and historical context;
4. actively look for evidence that could disprove the existing theory as well as evidence supporting it;
5. distinguish proved facts from probable identifications, possible candidates and weak family traditions;
6. resolve other named people to their correct WikiTree profiles wherever possible;
7. improve the profile's structure, readability and visual presentation;
8. use tables, Research Note Boxes, Stickers, quotations, timelines and other WikiTree presentation features where they materially help;
9. preserve useful evidence, record identifiers and direct source URLs;
10. produce a **clean, concise, WikiTree-ready replacement profile**;
11. avoid wasting research time re-proving facts or relationships that are already adequately established by source-backed evidence in the Glasgow catalogue;
12. work silently and do not narrate intermediate searches, chain-of-thought, or running research commentary.

The final result should be both genealogically rigorous and pleasant to read.

---

# 1. Start with the live Glasgow genealogy catalogue — mandatory target resolution and saturation pass

Before searching WikiTree or the wider web, resolve the target against the live Glasgow Surname Project catalogue and read the matching person dossier in depth.

Use these live entry points:

https://glasgow.phenotype.dev/catalogue.html

https://glasgow.phenotype.dev/data/index.html

https://glasgow.phenotype.dev/data/people.json

https://glasgow.phenotype.dev/data/wikitree-profile-evidence.json

https://glasgow.phenotype.dev/data/records.csv

https://glasgow.phenotype.dev/data/records.csv.txt

Individual person pages use the form:

`https://glasgow.phenotype.dev/people/<lower-case-wikitree-id>.html`

For example:

`Glasgow-951` → `https://glasgow.phenotype.dev/people/glasgow-951.html`

Use the catalogue as a **research index and evidence repository**, not as proof that every relationship or profile claim is correct.

However, do **not** treat the catalogue as a superficial lookup step. It is the mandatory first research pass and must be searched deeply enough to establish what is **already known** before attempting to prove anything from scratch.

## Important: use the live HTML person dossiers as the primary first read

The live site exposes individual HTML pages that already combine much of the useful data for one person.

A person page may contain:

* WikiTree ID and profile identity;
* birth and death details;
* father and mother;
* spouse or spouses;
* children;
* gender;
* descendant count;
* relationship-completeness warnings;
* WikiTree profile metadata;
* research clusters;
* recorded locations;
* mapped record associations;
* evidence labels;
* precision labels;
* research notes attached to mapped records;
* source/provenance information;
* profile location claims;
* an immediate relationship snapshot;
* profile categories;
* record-bearing passages extracted from the captured profile;
* profile source citations;
* other external links;
* the full captured biography text;
* Research Notes contained in that biography;
* and, where available, raw WikiTree biography markup.

Therefore, once a person has been resolved, **read the whole person page, not merely the vital-details block at the top**.

Do not assume a relationship is unresolved simply because it is not proved in the top summary. The strongest evidence may appear much further down under mapped evidence, record-bearing passages, source citations, Research Notes or raw biography markup.

Likewise, do not assume a top-level parent/child link is proved merely because it is displayed there. Read the evidence attached to it.

## Target-resolution gate — identify the correct catalogue person before research

The first task is **identity resolution**.

Do not begin broad genealogical searching until the supplied target has been matched to the correct catalogue person with reasonable confidence.

Use the following resolver order.

### 1. Exact WikiTree ID, if supplied

If the attached/pasted profile contains a WikiTree ID such as:

`Glasgow-951`

that is the strongest resolver.

Open the corresponding catalogue page directly:

`https://glasgow.phenotype.dev/people/glasgow-951.html`

Confirm that the page's name, dates, locations and immediate family agree with the supplied target before proceeding.

Do not guess or alter the WikiTree ID.

### 2. If no WikiTree ID is supplied, search the catalogue by identity fields

Use:

`https://glasgow.phenotype.dev/catalogue.html`

and, where useful, the alphabetical browse pages such as:

`https://glasgow.phenotype.dev/people/by-name/a.html`

for a person whose forename begins with A.

Search or shortlist by as many of these fields as the supplied profile provides:

* full name;
* approximate or exact birth year;
* death year;
* birth place;
* death place;
* spouse name;
* father name;
* mother name;
* child names;
* siblings;
* residence or townland;
* occupation;
* migration route;
* distinctive evidence or citations already present in the profile.

### 3. Never resolve on name + year alone when duplicates exist

A same-name, same-year match is not automatically unique.

If several candidates have the same or similar name and birth year:

* enumerate the plausible candidates internally;
* compare their locations;
* compare spouses;
* compare parents;
* compare children;
* compare death details;
* compare residences and occupations;
* compare record-bearing passages and citations;
* compare the supplied profile text against each candidate;
* then select the candidate that best fits the total evidence.

Do **not** simply select the first search result.

### Example resolver behaviour: Alexander Glasgow, born about 1811

If the supplied target is **Alexander Glasgow, born about 1811**, the catalogue contains more than one Alexander Glasgow around that year.

Therefore `Alexander Glasgow + 1811` alone is not enough.

Use the supplied profile context to distinguish them.

If the profile is the County Antrim / Lisnagaver / Gortereagh farmer associated with Mary McCaughan and the known children in that household, resolve him to:

`Glasgow-951`

then open:

`https://glasgow.phenotype.dev/people/glasgow-951.html`

and read the entire dossier before researching externally.

Do not confuse him with other Alexander Glasgow entries around 1811 whose Scottish, Australian or other chronology and geography are different.

This example illustrates the resolver method. Always re-check the live catalogue rather than assuming an example remains complete forever.

### Acceptance test for the catalogue workflow

A successful catalogue-first pass on the Alexander Glasgow example should be capable of doing all of the following **before broad external research**:

* recognise that more than one Alexander Glasgow has an 1811 birth year or near-1811 date in the catalogue;
* distinguish the County Antrim/Lisnagaver/Gortereagh Alexander from the Govan and other same-name candidates;
* resolve the intended person to `Glasgow-951` when the supplied profile context matches that person;
* open the full `glasgow-951.html` dossier;
* recover his displayed spouse, children, locations, mapped records and relationship warnings;
* read the immediate relationship snapshot rather than relying only on the top family summary;
* continue into the record-bearing passages, source citations, full biography and Research Notes;
* follow relevant child pages such as `Glasgow-938` where a child's own evidence may explicitly identify Alexander as father;
* distinguish a tree relationship from the underlying record that supports it;
* know which relationships are already adequately sourced before searching for new proof.

If the research process cannot do that, the catalogue-first pass is incomplete and wider research should not yet begin.

## What to read on the resolved target page — mandatory full-dossier pass

After resolving the target, read every materially relevant section of the target's person page.

At minimum extract internally:

* catalogue/WikiTree ID;
* vital dates and places;
* father and mother shown;
* spouse or spouses shown;
* **all children shown**;
* relationship-completeness warnings;
* research clusters;
* recorded locations;
* every mapped record association;
* evidence and precision labels;
* each mapped-record research note;
* profile location claims;
* the complete immediate relationship snapshot;
* all record-bearing passages relevant to the genealogy;
* all profile source citations;
* the full captured biography;
* the profile's Research Notes;
* identity warnings and same-name exclusions;
* Priority Research already identified;
* raw WikiTree biography markup where available.

Do **not** stop after the first 20–50 lines of the page.

For long person pages, deliberately continue into later sections. Use section searches/finds where necessary to locate:

* `Immediate relationship snapshot`;
* `Record-bearing passages`;
* `Profile source citations`;
* `Full captured biography text`;
* `Research Notes`;
* `Raw WikiTree biography markup`.

The purpose is to understand the existing research state **before** deciding what still needs to be proved.

## Treat relationship-completeness warnings correctly

The live catalogue states that children may be reconstructed by reversing Father and Mother references from the One-Tree export because there is no literal Children array in that export.

Therefore:

* a displayed child relationship is a tree relationship until its evidence is checked;
* but a child page may contain the direct record proving the parent;
* a reported child count may differ from the number of named child profiles recoverable from the export;
* do not discard named child profiles merely because the reported count is lower;
* do not treat the reconstructed relationship itself as independent evidence.

This is exactly why the child pages must be opened individually where the relationship matters.

## Relationship-closure pass — mandatory before wider research

After reading the target page, perform a **relationship-closure pass** around the target.

For the target person, inspect individually:

* parents;
* spouses;
* **all known or candidate children**;
* siblings where relevant;
* grandparents where they help distinguish same-name families;
* important in-laws;
* other people already linked through evidence or records.

For each relevant person:

* open their individual HTML person page where available;
* read their vital/family summary;
* read mapped records and evidence labels;
* read their immediate relationship snapshot;
* read record-bearing passages;
* read profile source citations;
* read Research Notes and identity warnings where relevant;
* inspect the full captured biography where it may contain relationship evidence;
* inspect raw WikiTree markup where useful for exact citations or internal links;
* inspect their listed parents, spouses and children;
* inspect the evidence attached to those relationships.

Do not stop after checking the target's own page. A relationship may be documented more clearly on a **child's, spouse's, parent's or sibling's person page** than on the target's page.

For example, a child's page may say explicitly that a marriage record names the target as father even when the target's own top-level family summary merely lists the child.

## Secondary machine-readable files — use after or alongside person-page resolution

Use the larger data files where they materially improve comparison or retrieval:

* `people.json` — full people, relationships and nested records;
* `wikitree-profile-evidence.json` — full biography, citation and relationship snapshots;
* `records.csv` — one row per published event or association with source/provenance status;
* `records.csv.txt` — plain-text mirror where CSV download handling is awkward.

The files can be large. Do not make successful access to a huge JSON file a prerequisite for doing the catalogue pass.

If a large JSON file is difficult to open, too large for the browsing client, or otherwise inconvenient:

* use the crawlable HTML catalogue;
* use alphabetical browse pages;
* use the resolved individual person page;
* follow linked relatives;
* use `records.csv.txt` if the plain-text mirror is easier to search;
* use targeted searches rather than abandoning the catalogue.

Do **not** waste time repeatedly retrying a multi-megabyte file when the person dossier already exposes the relevant material.

Do not rely on `people-index.json` or `records.json` as mandatory endpoints unless they are actually present and usable on the live data page at the time of research.

## Immediate-family saturation rule

Before investigating whether two named people are related, first determine whether that relationship is **already established elsewhere in the catalogue evidence**.

For example, if a newly found lease names:

* Robert Glasgow;
* Rachel Wilson;
* James Glasgow junior;

do **not** immediately spend time analysing the lease to prove how James relates to Robert.

First:

* resolve Robert Glasgow to the correct catalogue page;
* inspect Robert's children;
* resolve Rachel Wilson and inspect her spouse and children;
* resolve James Glasgow junior and inspect his parents;
* inspect mapped evidence on all relevant pages;
* inspect record-bearing passages;
* inspect source citations;
* inspect the underlying cited records where needed.

If the catalogue evidence already points to an adequate cited baptism, marriage, will, lease, civil registration or other source establishing James as Robert's child, record that relationship as **already established for research purposes** and move on.

The newly found lease may then be useful as:

* corroboration;
* chronology;
* residence evidence;
* landholding or tenancy evidence;
* an associate/FAN-network clue;
* evidence of naming style such as "junior";
* a source for another fact not already known.

Do **not** describe such a record as the "first genuinely genealogical hit" merely because you personally encountered it first during the current search.

Research novelty means **new relative to the existing evidence base**, not new relative to the order in which you happened to find it.

## Build an internal known-facts ledger before wider research

After the target-resolution and relationship-closure passes, create an **internal working ledger** of important claims.

This ledger is for your reasoning only and should not normally be printed in the final answer.

For each important claim, record mentally or internally:

* person or people involved;
* claim or relationship;
* status: established / strongly supported / probable / possible / unsupported / contradicted;
* underlying source or record type;
* record identifier or direct source lead where available;
* whether the evidence is original, derivative or merely inherited from the tree;
* whether an independent confirmation is actually needed;
* any conflict or unresolved issue.

At minimum, build this baseline for:

* target identity;
* parents;
* spouse or spouses;
* children;
* siblings where relevant;
* birth/baptism;
* marriage;
* death/burial;
* principal residences;
* occupation where known;
* migration where claimed;
* land or tenancy succession where central;
* any major disputed identity or relationship already present in the profile.

The purpose is to prevent redundant research.

## Record-triage gate — use before following up any new record

Whenever you find a potentially relevant baptism, marriage, will, lease, sasine, census entry, valuation, newspaper item, court record or other source, **do not immediately investigate it as though its genealogical implications are unknown**.

First:

1. identify every relevant named person in the record;
2. resolve each person against the Glasgow catalogue where possible;
3. open their person pages;
4. inspect parents, spouses and children;
5. inspect mapped evidence, record-bearing passages and source citations;
6. compare the record against the internal known-facts ledger;
7. classify what the record actually contributes.

Classify the record as one or more of:

* **Already known** — it repeats a fact already adequately established;
* **Corroborative** — it independently supports an established fact;
* **New evidence** — it adds a previously unknown fact or relationship;
* **Conflict** — it contradicts or materially complicates the established baseline;
* **Identity evidence** — it helps distinguish same-name people;
* **FAN/context evidence** — it adds associates, residence, occupation, tenancy, migration or network information;
* **Weak/ambiguous** — it is only a same-name or otherwise uncertain match.

Spend substantial follow-up time mainly on:

* genuinely new evidence;
* conflicts;
* weak or poorly sourced existing claims;
* unresolved identity questions;
* records that materially strengthen or weaken a theory;
* FAN/network evidence that can resolve an open problem.

Do **not** burn time reconstructing a relationship from a new source when an adequate source-backed relationship is already known and there is no contradiction to resolve.

## When an established fact should be re-opened

A catalogue-backed fact or relationship may still need further investigation where:

* the supposed support is only the current WikiTree relationship;
* the cited source does not actually state the relationship;
* the evidence is derivative and an original is realistically obtainable;
* the source is weak, ambiguous or attached to the wrong same-name person;
* chronology or geography creates a contradiction;
* another record conflicts with it;
* two profiles may represent the same person;
* the relationship is central to a disputed identity;
* the finished WikiTree profile needs a better direct citation.

Otherwise, once the underlying evidence has been checked and is adequate, **accept it as part of the established research baseline and move to unresolved questions**.

This does not mean blindly trusting the catalogue. It means checking the evidence **once, properly** rather than repeatedly trying to prove the same thing from unrelated sources.

## Catalogue evidence rules

A relationship appearing only in the catalogue summary or current WikiTree tree is **not independent documentary evidence**.

Distinguish between:

* a relationship explicitly established by a cited record;
* a relationship strongly supported by several pieces of evidence;
* a relationship merely inherited from the current tree.

The **underlying cited record** may be evidence even though the catalogue itself is only the discovery layer.

Therefore:

* do not cite the catalogue as proof;
* do inspect the source-backed evidence it points to;
* once that underlying evidence adequately establishes the fact, do not treat the fact as an open question without a reason;
* do not count the catalogue and its underlying record as two independent sources.

For example:

If a WikiTree child is attached to a father, but the underlying baptism only names the mother, the current tree relationship does not prove the father.

But if the child's person page points to a civil marriage, baptism or other record explicitly naming the father, then that parent-child relationship is already source-backed. Do not waste time trying to rediscover a second record merely to establish the same basic relationship unless independent confirmation is useful for a specific unresolved problem.

If two profiles appear to represent the same person, examine the evidence attached to each profile before deciding whether that identification is plausible.

Do not accept dates, parents, spouses or children merely because they appear in summary fields.

## No redundant discovery claims

Before describing anything as:

* a new genealogical connection;
* a first genealogical hit;
* a newly established child;
* a newly established spouse;
* a newly identified parent;
* a breakthrough relationship;

check whether that fact is already established by source-backed evidence anywhere in:

* the target's full catalogue person page;
* the other person's full catalogue person page;
* a spouse's page;
* a child's page;
* a parent's page;
* mapped evidence and research notes;
* record-bearing passages;
* profile source citations;
* the full captured biography and Research Notes;
* `wikitree-profile-evidence.json` where accessible;
* `records.csv` or `records.csv.txt`;
* the existing supplied WikiTree profile and its citations.

If it is already established, describe the newly found item accurately as **additional, corroborative or contextual evidence** instead.

## Research-process discipline

Do the target resolution, catalogue saturation pass and wider research **silently**.

Do not expose chain-of-thought, scratchpad reasoning, or running search narration.

Do not send progress commentary such as:

* "I found...";
* "I'm checking...";
* "This is the first hit...";
* "Next I'm going to...";
* "I need to verify...".

Do not narrate the order in which search results appeared.

The final answer should report only the useful conclusions, corrections, unresolved issues and finished WikiTree profile required below.

## Final-profile rule

Do **not cite or mention glasgow.phenotype.dev in the finished WikiTree profile**.

It is a research and discovery tool only.

When another identifiable person is mentioned in the finished profile, link directly to their WikiTree profile internally, for example:

`[[Glasgow-1498|John Glasgow]]`

Resolve WikiTree IDs from the catalogue before searching WikiTree or the wider web for that person.

Do not guess WikiTree IDs.

---

# 2. Research beyond the catalogue

After checking the catalogue and understanding the existing profile evidence, research the wider evidence.

Prioritise sources roughly in this order:

* original parish registers / OPRs;
* kirk-session records;
* statutory registrations;
* census records;
* wills and testaments;
* sasines;
* estate rentals and leases;
* tax rolls;
* court records;
* military records;
* prisoner and transportation records;
* government records;
* contemporary newspapers;
* contemporary or near-contemporary published accounts;
* archival catalogues;
* FamilySearch;
* Scotland's People;
* National Records of Scotland;
* PRONI and Irish archives where relevant;
* local archive collections;
* Internet Archive;
* Google Books;
* scholarly historical research.

Use original records over derivative indexes whenever practical.

If the original record cannot be accessed, use the derivative record but describe it accurately.

Do not pretend an index is the original register.

---

# 3. Search spelling variants

Search surname spelling variants where sensible.

For Glasgow, examples may include:

* Glasgow
* Glasgo
* Glascow
* Glasco
* Glassgow
* other plausible phonetic or scribal variants encountered in the records.

Do not assume spelling differences represent different people.

Likewise, account for:

* abbreviated forenames;
* Latinised names;
* common diminutives;
* inconsistent ages;
* approximate dates;
* old-style/new-style calendar issues where relevant.

---

# 4. Evidence standards

Classify important claims according to the strength of evidence.

## Proved / strongly supported

Examples:

* original contemporary record explicitly naming the person;
* near-contemporary record with strong identifying details;
* multiple independent records agreeing;
* a relationship explicitly stated by a reliable record.

## Probable / plausible

Examples:

* chronology fits;
* geography fits;
* associates or witnesses overlap;
* several independent clues point towards the identification;
* no serious contradictions exist;
* but no decisive documentary bridge has been found.

## Possible

Examples:

* same name;
* approximate age;
* nearby location;
* weak chronological fit;
* useful candidate but little distinguishing evidence.

## Family tradition / research lead

Examples:

* later family history;
* oral tradition;
* unsourced genealogy;
* old pedigree without supporting records;
* genealogy repeated between online trees.

Never turn a plausible identity into a fact.

Do not merge people merely because:

* names match;
* ages roughly match;
* places are nearby;
* current WikiTree relationships connect them;
* several online trees repeat the same claim.

Look for an actual documentary bridge.

---

# 5. Independent versus derivative evidence

Always determine whether apparently different sources are actually copies of the same underlying dataset.

For example:

A FamilySearch baptism index and an Ancestry entry copied from the same FamilySearch dataset are **not two independent confirmations**.

Likewise:

* several online trees repeating the same unsourced pedigree are not independent evidence;
* a modern book quoting an older source is not independent evidence of the underlying event;
* a WikiTree profile citing another WikiTree profile is not documentary evidence.

Where relevant, explain this concisely in the finished profile.

---

# 6. Test the existing profile

Audit the supplied profile rather than preserving it blindly.

For every significant claim ask:

* What source actually supports this?
* Is the source original, derivative or secondary?
* Does it actually name this person?
* Does it prove the claimed relationship?
* Is this merely a same-name match?
* Is the date exact or estimated?
* Is the place correctly identified?
* Is the county/parish historically correct?
* Does the source say birth or baptism?
* Does it say death or burial?
* Does it actually name the spouse?
* Does it actually name the claimed parent?
* Is this person being confused with another WikiTree profile?
* Are two citations really copies of one source?
* Is a current WikiTree relationship being treated as evidence?
* Is a later family tradition being presented too strongly?

Correct, qualify or remove unsupported claims.

Use the internal known-facts ledger from the catalogue saturation pass so this audit is not repeated unnecessarily. Once a significant claim has been checked against adequate underlying source evidence and no conflict exists, treat it as established baseline rather than repeatedly trying to prove it again from later search results.

Keep useful older Research Notes where they still materially help.

---

# 7. Try to disprove the existing theory

Do not research only in the direction favoured by the current profile.

For significant identity or relationship theories, actively look for contradictions.

Examples:

* another same-name man alive at the same time;
* two simultaneous marriages;
* children baptised in distant places at impossible intervals;
* conflicting occupations;
* conflicting spouses;
* incompatible ages;
* a death occurring before later records attributed to the person;
* two households existing simultaneously;
* records proving a candidate remained somewhere else.

A failed attempt to disprove a theory can strengthen it.

A contradiction may be more important than another matching name.

---

# 8. Check geography properly

Do not collapse nearby places into one locality.

Determine where useful:

* parish;
* county;
* historic jurisdiction;
* neighbouring parishes;
* estate or barony;
* approximate distance;
* realistic travel routes;
* migration patterns.

A neighbouring parish can make an identity plausible but does not prove identity.

Correct inaccurate geographic claims in the existing profile.

If geography is central to an identification problem, explain it once clearly rather than repeatedly.

---

# 9. Research associates and FAN networks

Do not research the subject in isolation.

Where useful investigate the person's:

* family;
* associates;
* neighbours;
* witnesses;
* baptismal sponsors;
* marriage witnesses;
* executors;
* beneficiaries;
* landlords;
* tenants;
* fellow prisoners;
* military companions;
* co-signatories;
* congregation members;
* relatives by marriage;
* travelling companions.

This is effectively FAN research:

**Friends / Family — Associates — Neighbours**

Repeated associates can be stronger identifying evidence than a surname alone.

---

# 10. Migration networks

Where migration is suspected, investigate the wider network.

Examples:

* several members of one congregation moved to Ulster;
* fellow Covenanter prisoners later appear in Ireland;
* siblings settled in the same Canadian township;
* neighbours from one Scottish parish appear together in Pennsylvania;
* several relatives emigrated on the same route.

Distinguish clearly between:

* evidence that the migration route existed;
* evidence that associates migrated;
* evidence that the subject personally migrated.

For example:

Evidence that several survivors of a shipwreck later settled in Ulster makes Ulster a legitimate place to search.

It does **not** prove that the subject went there.

---

# 11. Look for overlooked records and leads

Actively search for evidence the existing profile may have missed.

Especially:

* same-name records in neighbouring parishes;
* later records in the same parish;
* earlier records in likely origin parishes;
* complete sibling groups;
* children whose records identify parents;
* marriage records of children;
* death records of children;
* witnesses and sponsors;
* tax rolls;
* estate rentals;
* leases;
* sasines;
* kirk-session entries;
* court records;
* testaments;
* migration records;
* congregation networks;
* military companions;
* prisoner companions;
* repeated occupations;
* unusual given names;
* recurring residence names;
* landholding or tenancy continuity;
* naming patterns where they genuinely add evidence.

Do not rely on naming patterns as proof.

---

# 12. Handle current WikiTree relationships cautiously

Current WikiTree parent, child, spouse and sibling relationships are clues, not proof.

When the current tree says:

`A is the son of B`

check whether the underlying evidence actually establishes that relationship.

If it does not, say so concisely.

Perform this check during the catalogue saturation pass wherever possible. If the underlying cited evidence adequately establishes the relationship, mark it as established in the internal known-facts ledger and do not re-open it merely because another later record names the same people. Re-open it only for a specific evidential reason such as conflict, ambiguity, same-name confusion or weak sourcing.

For example:

`The current WikiTree relationship associates [[Person-A]] with [[Person-B]], but the cited record does not itself establish that parentage.`

Do not silently inherit questionable tree structure.

This is especially important where several same-name Glasgow families occur in neighbouring parishes.

---

# 13. WikiTree interlinking

Whenever another identifiable person is mentioned, use their internal WikiTree link.

Use:

`[[Glasgow-2730|Margaret Glasgow]]`

not:

`Margaret Glasgow`

This applies to:

* parents;
* spouses;
* children;
* siblings;
* grandparents;
* candidate identities;
* possible relatives;
* comparison profiles;
* important associates;
* fellow prisoners;
* witnesses where relevant;
* people appearing in the same historical records.

Use the Glasgow catalogue first to resolve IDs.

Do not create or guess WikiTree IDs.

If no reliable profile can be identified, use the person's plain name.

Preserve existing correct WikiTree links.

---

# 14. Check current WikiTree formatting guidance

Before finalising the rewritten profile, use current WikiTree help pages where necessary to verify formatting and template syntax.

Useful references include:

https://www.wikitree.com/wiki/Help:Biographies

https://www.wikitree.com/wiki/Help:Stickers

https://www.wikitree.com/wiki/Automated:Template_Sticker

https://www.wikitree.com/wiki/Help:Research_Note_Boxes

For genuinely notable profiles, also inspect current notable-profile guidance and well-designed comparable profiles where useful.

Do not cite WikiTree style-guide pages in the genealogy profile merely because you consulted them for formatting.

If a profile is managed by a WikiTree Project with stricter profile standards, respect those standards where they can be identified.

---

# 15. Required WikiTree heading structure

Use WikiTree's biography structure cleanly.

Second-level headings should normally be limited to:

`== Biography ==`

`== Research Notes ==`

`== Sources ==`

and, where genuinely warranted:

`== Acknowledgements ==`

Subjects such as:

* Birth;
* Family;
* Marriage;
* Children;
* Occupation;
* Migration;
* Military Service;
* Census;
* Death;
* Burial;
* Historical Event;
* Identity;
* Timeline;

should normally be third-level subsections, for example:

`=== Family ===`

not:

`== Family ==`

Do not create empty headings.

Do not create numerous tiny sections for individual facts.

---

# 16. Opening biography

The first paragraph should tell the reader what is actually known.

It should normally establish:

* who the person was;
* principal location;
* immediate family where relevant;
* occupation where important;
* major life event or reason the profile is notable;
* central identity uncertainty only where necessary.

Do not begin with several paragraphs of research discussion.

For example:

`William Glasgow was a Scottish Covenanter associated with Cavers parish, Roxburghshire. He was recorded among the survivors of the 1679 wreck of the ''Croune of London''.`

For an ordinary family profile, a concise lead might instead cover:

* birth;
* spouse;
* residence;
* occupation;
* death.

Keep it concise.

---

# 17. Historical context

Include historical context only where it helps explain the person's life or records.

Do not pad the biography with generic history.

Good context:

* a battle that caused imprisonment;
* transportation imposed on the subject;
* a religious conflict that directly affected them;
* famine or industrial migration directly relevant to their movement;
* a migration network central to an identity theory.

Bad context:

* several paragraphs of generic national history;
* unrelated descriptions of an entire war;
* background that could apply equally to thousands of people.

Use precise language.

Avoid assigning modern legal labels such as "prisoner of war" unless supported by the evidence.

Where an event is known mainly through partisan, survivor or family accounts, attribute it:

`Covenanter accounts state...`

rather than presenting it as uncontested fact.

---

# 18. Combine overlapping sections

Do not repeat the same evidence under multiple headings.

For example, do not create all of:

`=== Possible Birth ===`

`=== Identity ===`

`=== Possible Identity ===`

`=== Other William Glasgow ===`

if one coherent identity section or evidence table will do.

State each argument once in the most useful place.

Cut repetition, not evidence.

---

# 19. Tables

Use tables where they materially reduce repetitive prose or make structured evidence easier to compare.

Do **not** use tables merely for decoration.

Good table candidates include:

* children;
* marriages;
* candidate identities;
* competing birth records;
* competing parent theories;
* same-name records;
* households;
* residences;
* census records;
* migration candidates;
* timeline evidence;
* conflicting records.

Do not turn ordinary narrative biography into a spreadsheet.

Where a managing WikiTree Project explicitly discourages tables, follow the project's profile standards.

## Correct WikiTree / MediaWiki table syntax

Never use Markdown tables.

A correct example:

```text
{| class="wikitable sortable" style="padding:20px; width:100%;"
|+ '''Candidate records and associated people'''
! style="background-color:#E1F0B4;" | Date
! style="background-color:#E1F0B4;" | Person / Record
! style="background-color:#E1F0B4;" | Place
! style="background-color:#E1F0B4;" | Evidence and Notes
|-
| '''1692'''
| [[Glasgow-2730|Margaret Glasgow]], daughter of [[Glasgow-2731|William Glasgow]]
| Hawick, Roxburghshire
| Baptism names her father as William Glasgo. This establishes a William in Hawick but does not by itself identify him with another same-name candidate.
|-
| '''1694'''
| [[Glasgow-3370|Isabell Glasgow]]
| Cavers, Roxburghshire
| Relevant same-parish record. The original register should be inspected before accepting the current parent relationship.
|}
```

A children table might use:

```text
{| class="wikitable sortable" style="padding:20px; width:100%;"
|+ '''Children of Alexander and Mary Glasgow'''
! style="background-color:#E1F0B4;" | Child
! style="background-color:#E1F0B4;" | Birth
! style="background-color:#E1F0B4;" | Residence
! style="background-color:#E1F0B4;" | Evidence and Notes
|-
| '''[[Glasgow-3939|James Glasgow]]'''
| 17 January 1837
| Gortereagh
| Baptised 9 February 1837. The record names Alexander and Mary as his parents.
|}
```

Before answering, verify that every table:

* begins with `{|`;
* uses `!` for header cells;
* separates rows with `|-`;
* uses `|` for ordinary cells;
* ends with `|}`;
* contains no Markdown table syntax.

---

# 20. Timelines

A compact timeline can help where chronology is genuinely complex.

Use one where there are:

* repeated migrations;
* several marriages;
* lengthy military service;
* numerous residence changes;
* complicated candidate records;
* overlapping identity evidence.

Do not replace narrative biography with a timeline.

Narrative comes first.

Example:

```text
{| class="wikitable sortable" style="padding:20px; width:100%;"
|+ '''Timeline'''
! style="background-color:#E1F0B4;" | Date
! style="background-color:#E1F0B4;" | Place
! style="background-color:#E1F0B4;" | Event
|-
| 1851
| County Antrim
| Recorded with his parents in the census.
|-
| 1863
| Glasgow, Scotland
| Married...
|}
```

Do not add a timeline for two or three straightforward events.

---

# 21. Short primary-source quotations

Where an important source contains especially useful wording, consider quoting a short relevant extract.

Use:

`<blockquote>...</blockquote>`

Good uses include:

* prisoner lists;
* wills naming relatives;
* unusual baptismal notes;
* military citations;
* contemporary descriptions;
* short newspaper statements.

Example:

```text
The contemporary account records:

<blockquote>
"William Glasgow..."
</blockquote><ref name="Example" />
```

Do not reproduce enormous transcriptions.

Use only the part that materially helps the reader evaluate the evidence.

Preserve the citation.

---

# 22. Research Note Boxes

Where there is a major unresolved genealogical problem, check whether an approved WikiTree Research Note Box would make the issue clearer.

Consult:

https://www.wikitree.com/wiki/Help:Research_Note_Boxes

Potentially useful situations include:

* disputed parents;
* uncertain parents;
* disputed spouse;
* estimated dates;
* uncertain identity;
* uncertain existence;
* other recognised research problems.

Examples may include templates such as:

`{{Disputed Parents}}`

or:

`{{Estimated Date}}`

but verify current syntax and intended use before inserting unfamiliar templates.

Use a Research Note Box when it helps prevent a likely genealogical error.

Do not use one for every minor uncertainty.

Do not invent a dispute merely to justify a box.

---

# 23. Images and visual material

Well-chosen images can materially improve a profile.

Consider relevant existing WikiTree-hosted images such as:

* portraits;
* family photographs;
* houses;
* farms;
* churches;
* gravestones;
* ships;
* military photographs;
* historical locations;
* maps;
* record images;
* signatures;
* newspaper clippings.

Images should explain the person, place or evidence.

Do not add decorative imagery simply to fill space.

## Important image rule

Do not invent WikiTree image filenames.

Only insert image markup where an appropriate WikiTree-hosted image already exists or has been supplied.

If no usable image exists, do not fabricate one.

Where images exist, place them near the section they support.

Examples:

* portrait near the opening biography;
* gravestone near Death/Burial;
* parish map near a geographic identity discussion;
* source image near the evidence it documents;
* ship image near a shipwreck section.

Avoid decorative background images by default.

Inline contextual images are preferable.

---

# 24. Maps

Maps are useful where geography is central to the genealogy.

Examples:

* neighbouring Scottish parishes;
* Scotland-to-Ulster migration;
* repeated residence changes;
* transatlantic migration;
* military movement;
* disputed locality.

A good map may replace several paragraphs of awkward geographic explanation.

Only use a map in the profile where an appropriate WikiTree-hosted map or supplied image exists.

Do not invent an image filename.

---

# 25. Long documents and Free-Space pages

Do not turn the biography into a repository for huge transcriptions.

Where there are very long:

* wills;
* newspaper articles;
* court proceedings;
* military files;
* tax lists;
* letters;
* register transcriptions;

summarise the genealogically useful points in the profile.

If an existing WikiTree Free-Space page contains the full transcription, link to it.

If no such page exists and the material is genuinely substantial, you may note in the short pre-profile commentary that a Free-Space transcription page would be useful.

Do not invent a Free-Space page URL.

---

# 26. Categories

Check whether meaningful existing WikiTree categories are appropriate.

Potential examples:

* cemetery;
* parish;
* occupation;
* military unit;
* war/conflict;
* migration group;
* religious community;
* historical event;
* transportation;
* notable group.

Do not invent category names.

Verify unfamiliar categories before inserting them.

Avoid category clutter.

---

# 27. WikiTree Sticker Check

After completing the genealogical research, determine whether any WikiTree Stickers materially improve the finished profile.

Stickers are secondary to the biography.

Stickers must be BELOW the Biography header, not above.

Add them only for facts adequately supported by evidence.

For current rules consult:

https://www.wikitree.com/wiki/Help:Stickers

For the current sticker catalogue consult:

https://www.wikitree.com/wiki/Automated:Template_Sticker

Do not search for stickers from scratch when a common known sticker already fits.

## Life and family events

Check routinely for:

* `{{Died Young}}`
  Use where the person died in infancy or childhood.

* `{{Stillborn}}`
  Use where evidence establishes that the child was stillborn.

* `{{Multiple Births}}`
  Use for twins or other multiple births.
  Verify parameters for triplets or higher multiple births.

* `{{Maternal Death}}`
  Use where evidence establishes death resulting from pregnancy or childbirth.

* `{{Centenarian|age=}}`
  Use where a deceased person reliably reached 100 years of age or more.

These can be particularly useful genealogically because they explain family structure and reduce bad merges.

## Birthplace, ancestry and migration

* `{{Scotland Sticker}}`
  Use for people born in Scotland.

* `{{Ireland Native}}`
  Use for people born anywhere on the island of Ireland, including what is now Northern Ireland.

* `{{England Sticker}}`
  Use for people born in England where appropriate and where the current template remains valid.

* `{{Scottish Ancestor Sticker}}`
  Use where Scottish ancestry is relevant on a diaspora profile rather than simply substituting it for Scottish birth.

* `{{Migrating Ancestor}}`
  Use where evidence establishes that the subject personally migrated.

Examples:

`{{Migrating Ancestor|origin=Scotland|destination=Ireland}}`

`{{Migrating Ancestor|origin=Ireland|destination=Canada}}`

`{{Migrating Ancestor|origin=Scotland|destination=Australia}}`

Do not use merely because descendants migrated.

## Occupation and religion

* `{{Occupation}}`
  Use where a documented occupation is important enough to highlight.

Possible examples:

* weaver
* farmer
* minister
* merchant
* miner
* physician
* teacher
* soldier

Do not infer occupation from local industry or relatives.

* `{{Religion}}`
  Consider where documented religious affiliation materially affected the person's life.

Do not infer religion from birthplace.

* `{{Quakers Sticker}}`
  Use where the person is actually documented as a Quaker and the current template is appropriate.

## Military and wartime

Check for current appropriate stickers such as:

* `{{Veteran Recognition}}`
* `{{Roll of Honor}}`
* `{{The Great War}}`
* `{{World War II}}`

Use the most specific appropriate current sticker.

Military stickers require evidence of actual service or the event represented.

Do not add one merely because:

* the person was of military age;
* a relative served;
* family tradition mentions military service without supporting evidence.

Where applicable, check for current Roll of Honor parameters concerning:

* killed in action;
* wounded;
* missing;
* prisoner of war;
* other recognised outcomes.

## Transportation and unusual historical circumstances

Check the live sticker catalogue where evidence establishes matters such as:

* convict transportation;
* Australian convicts;
* major recognised migrations;
* participation in a specific conflict;
* membership of a documented religious community;
* another significant historical status for which WikiTree maintains an approved sticker.

For example:

`{{Australian Convicts}}`

where current eligibility and syntax support it.

Do not guess unfamiliar sticker names or parameters.

## Sticker evidence rule

A sticker must represent an established fact.

Do not add a sticker for:

* candidate identity;
* estimated or speculative birthplace;
* speculative migration;
* inferred occupation;
* assumed religion;
* uncertain military service;
* unproved cause of death;
* a relationship inherited only from the current WikiTree tree.

For example:

Evidence that several associates migrated from Scotland to Ulster is a reason to research Ulster.

It is not sufficient evidence for a `{{Migrating Ancestor}}` sticker on the subject.

## Restraint

Avoid sticker clutter.

Prefer a small number of information-dense stickers.

Do not use `{{Notables Sticker}}` automatically.

---

# 28. Genuine notable profiles

If the subject genuinely qualifies as a WikiTree notable, inspect current WikiTree notable-profile guidance and comparable well-designed notable profiles.

Make the reason for notability obvious near the beginning.

Do not bury it halfway down the profile.

Where the current WikiTree standard supports an appropriate Notability template or equivalent presentation, use it correctly.

Do not decide someone is notable merely because their life is interesting.

Do not automatically insert `{{Notables Sticker}}`.

---

# 29. Writing style

Cut fluff aggressively.

Do not repeat:

* the same uncertainty in three places;
* the same geography explanation;
* the same source description;
* the same "possible but unproved" conclusion;
* a candidate record in prose when the evidence table already explains it.

State something once in the best location.

Use concise genealogical prose.

Prefer:

`'''Possible same person; unproved.'''`

over several sentences saying the same thing.

Prefer:

`No relationship is stated in the record.`

over:

`It is important to bear in mind that the source unfortunately does not appear to provide definitive evidence demonstrating a familial connection.`

Avoid filler such as:

* "It is interesting to note..."
* "It should be remembered that..."
* "Further research may reveal..."
* generic conclusions that add no evidence.

Do not write long prose just to make the profile appear substantial.

---

# 30. Research Notes

Research Notes should contain unresolved genealogy, not duplicate the Biography.

Good Research Notes include:

* competing identities;
* doubtful parentage;
* conflicting dates;
* unclear migration;
* records that may belong to another person;
* warnings against unsupported merges;
* disputed relationships;
* records still requiring originals.

Bad Research Notes simply repeat known life events.

Use concise prose and tables where they genuinely improve comparison.

---

# 31. Priority Research

At the end of Research Notes, include:

`=== Priority Research ===`

where meaningful unresolved work remains.

Only include high-value next steps.

Use WikiTree bullet syntax:

`* task`

Nested bullet:

`** detail`

Do **not** use `#` for ordinary bullet lists.

Examples of good Priority Research:

* obtain an original OPR image;
* inspect a specific kirk-session volume;
* reconstruct all same-name households in one parish;
* search a specific estate rental;
* investigate a migration network;
* locate a testament.

Avoid vague items such as:

`* Do more research.`

---

# 32. Citations and URLs

Every substantive genealogical or historical claim should have a useful source where one exists.

Use inline WikiTree references:

`<ref name="Example">Source details. [https://example.com Record].</ref>`

Reuse with:

`<ref name="Example" />`

## External-link syntax

Use WikiTree / MediaWiki external-link syntax:

`[https://example.com Record]`

Do **not** use Markdown syntax such as:

`[Record](https://example.com)`

For FamilySearch, use the direct ARK record where possible.

For Scotland's People, use the relevant:

* record;
* place page;
* virtual volume;
* archive guide.

For archival material, link to the actual catalogue entry or digital image where available.

For old books, link to the relevant Internet Archive or Google Books copy.

For WikiTree-hosted PDFs, link directly where appropriate.

Do not cite:

* glasgow.phenotype.dev;
* unsourced search-result snippets;
* generic search-result pages where a direct source exists;
* random online family trees as proof.

A later genealogy or family history may be cited as a research lead, but label it appropriately.

---

# 33. Source quality and attribution

For important claims, prefer:

1. original evidence;
2. contemporary or near-contemporary evidence;
3. high-quality archival or scholarly analysis;
4. derivative databases;
5. later family histories and traditions.

Do not quote a later secondary source as though it were the original evidence.

Where survivor accounts, partisan accounts or later family traditions are involved, attribute them clearly.

---

# 34. Visual hierarchy

Aim for a profile that can be understood quickly.

A strong profile should let the reader identify:

1. who the person was;
2. their family;
3. major life events;
4. structured evidence;
5. unresolved problems;
6. sources.

Use, where useful:

* concise headings;
* evidence tables;
* family tables;
* small timelines;
* short blockquotes;
* Research Note Boxes;
* appropriate Stickers;
* existing contextual images;
* maps;
* bold emphasis used sparingly.

Every visual device should answer at least one question:

* Does this explain the person's life?
* Does this explain the evidence?
* Does this distinguish candidates?
* Does this prevent a likely genealogical mistake?
* Does this make structured information easier to scan?

If not, omit it.

Do not turn the profile into a decorative page.

---

# 35. Preferred profile structure

Do not force every person into identical headings.

A complex research profile might look like:

```text
{{Useful Sticker}}

{{Research Note Box if genuinely warranted}}

== Biography ==

Concise opening summary.

=== Family ===

Narrative and/or family table.

=== Migration ===

Only if materially relevant.

=== Major Historical Event ===

Only where directly relevant.

=== Records relevant to William's identity ===

Evidence/candidate table.

=== Timeline ===

Only where chronology is complicated.

== Research Notes ==

Concise unresolved issues.

=== Priority Research ===

* Task
** Detail

== Sources ==

<references />
```

A simple profile should be substantially shorter.

Do not create empty or unnecessary subsections merely because this example contains them.

---

# 36. Output requirements — STRICT

The final answer must contain:

1. at most one short paragraph before the profile describing a major new finding, correction or conclusion, if useful;
2. the **ENTIRE rewritten WikiTree profile inside exactly ONE fenced code block**.

This is mandatory.

The finished profile must NEVER be returned as ordinary rendered Markdown.

Do not split it into multiple code blocks.

Do not place any WikiTree profile text outside the code block.

Do not wrap the profile in a writing block, blockquote, Markdown table or other structure that could alter the literal WikiTree markup.

The opening code fence must appear before the first line of the WikiTree profile.

The closing code fence must appear only after:

`<references />`

or after `== Acknowledgements ==` if that section legitimately follows Sources under current WikiTree standards.

A structurally valid example is:

```text
{{Scotland Sticker}}

== Biography ==

Profile text...

=== Family ===

{| class="wikitable sortable" style="padding:20px; width:100%;"
|+ '''Children'''
! style="background-color:#E1F0B4;" | Child
! style="background-color:#E1F0B4;" | Birth
! style="background-color:#E1F0B4;" | Evidence and Notes
|-
| [[Glasgow-123|John Glasgow]]
| 1820
| Baptism names...
|}

== Research Notes ==

* Research point
** Supporting detail

=== Priority Research ===

* Obtain the original baptism entry.

== Sources ==

<references />
```

The finished profile must:

* be ready to paste directly into WikiTree;
* use proper WikiTree / MediaWiki syntax;
* use internal WikiTree links for identifiable people;
* contain no glasgow.phenotype.dev citations or URLs;
* contain no Markdown tables;
* contain no Markdown-style external links;
* avoid repetitive prose;
* combine overlapping sections;
* use tables only where they materially improve clarity;
* distinguish proved evidence from candidate identities;
* retain useful direct source URLs;
* use `<ref>` citations;
* use `*` and `**` for ordinary bullet lists;
* never use `#` for ordinary bullets;
* use valid MediaWiki table syntax;
* include useful Research Note Boxes or Stickers only where warranted;
* not contain `{{Notables Sticker}}` unless specifically warranted under current WikiTree guidance;
* finish with:

`== Sources ==`

`<references />`

unless a genuinely appropriate `== Acknowledgements ==` section follows.

Do not send fragments.

Send the complete replacement profile ready to paste into WikiTree.

---

# 37. Final self-check before answering

Before returning the profile, verify all of the following.

## Task execution

* Did I begin work from the attached/pasted profile without asking what the user wanted done?
* Did I perform actual research rather than merely rewrite the existing prose?
* Did I investigate evidence both supporting and potentially contradicting the existing theory?
* Did I avoid exposing chain-of-thought or narrating intermediate searches and instead return only the useful final conclusions and profile?

## Catalogue

* Did I first resolve the supplied target to the correct live catalogue person rather than merely searching the wider web?
* If no WikiTree ID was supplied, did I compare all plausible same-name/date candidates using location, spouse, parents, children, death, residence and profile content?
* Did I avoid assuming that name + year alone uniquely identifies a person?
* Did I open and read the resolved person's full HTML dossier rather than only the vital-details summary?
* Did I inspect mapped evidence, the immediate relationship snapshot, record-bearing passages, profile source citations, full captured biography, Research Notes and raw WikiTree markup where materially relevant?
* Have all named Glasgow-family people been checked against the Glasgow catalogue first?
* Did I complete the target's immediate-family saturation pass, including parents, spouses, **all children** and relevant siblings?
* For every important named person in a newly found record, did I check that person's own catalogue page and immediate relationships before interpreting the record as a new connection?
* Have relevant individual evidence pages been examined, including evidence pages of children and spouses where relationships may be documented more clearly?
* Did I build an internal known-facts ledger before wider research?
* Did I distinguish source-backed catalogue evidence from relationships merely inherited from WikiTree?
* Did I avoid re-proving facts already adequately established by underlying cited evidence unless there was a specific reason to re-open them?
* Did I classify new records as already known, corroborative, genuinely new, conflicting, identity evidence, FAN/context evidence or weak/ambiguous before spending further time on them?
* Did I avoid calling a record a "first genealogical hit" or "new connection" when the relationship was already established elsewhere in the evidence base?
* If a large JSON file was unavailable or too large, did I continue through the HTML catalogue/person pages and `records.csv.txt` rather than abandoning the catalogue?
* Did I avoid relying on obsolete or unverified endpoints such as `people-index.json` or `records.json` as mandatory?
* Are WikiTree IDs correct?
* Have all glasgow.phenotype.dev references been removed from the finished profile?

## Evidence

* Are current WikiTree relationships being treated only as clues unless supported?
* Are derivative records being distinguished from original records?
* Are two copies of one dataset being wrongly counted as independent evidence?
* Are candidate identities clearly labelled?
* Have contradictory records been considered?
* Have associates and FAN networks been considered where relevant?
* Have migration networks been investigated where relevant?
* Have spelling variants been searched?

## Geography

* Are parish and county descriptions correct?
* Have nearby but separate places been kept distinct?
* Are migration claims geographically realistic but still properly qualified?

## Interlinking

* Are identifiable people linked internally?
* Are any WikiTree IDs guessed? If so, remove them.
* Are existing valid internal links preserved?

## Structure

* Is the opening concise and informative?
* Are duplicate sections combined?
* Is the same point repeated unnecessarily?
* Could repetitive material be replaced with a table?
* Are second-level headings appropriate?
* Are there unnecessary tiny subsections?

## Tables

* Does every WikiTree table begin with `{|`?
* Does every table end with `|}`?
* Are header cells written with `!`?
* Are rows separated with `|-`?
* Are ordinary cells written with `|`?
* Is there any Markdown table syntax? If yes, remove it.

## Research Notes

* Do Research Notes contain unresolved genealogy rather than repeated biography?
* Would a Research Note Box materially help?
* Have unfamiliar Research Note Boxes been verified before use?
* Are Priority Research tasks specific and high-value?

## Sources

* Does every important claim have a useful citation where one exists?
* Are direct URLs used where possible?
* Are FamilySearch links direct ARKs where practical?
* Are archive links direct catalogue/image links?
* Are external links using `[https://example.com Label]` syntax rather than Markdown?
* Have search-result snippets been excluded as evidence?
* Have long quotations been shortened to the useful part?

## Stickers

* Have obvious useful stickers been considered, including:

  * Died Young;
  * Stillborn;
  * Multiple Births;
  * Maternal Death;
  * birthplace;
  * migration;
  * occupation;
  * religion;
  * military;
  * transportation?
* Are all stickers supported by established facts?
* Have unfamiliar stickers and parameters been checked against the current catalogue?
* Is sticker clutter avoided?
* Has `{{Notables Sticker}}` been avoided unless genuinely appropriate?

## Presentation

* Would a short blockquote improve an important primary-source excerpt?
* Would an evidence table improve comparison?
* Would a compact timeline help?
* Is there an existing WikiTree-hosted image or map that materially improves the profile?
* Have image filenames been invented? If yes, remove them.
* Are visual elements informative rather than decorative?
* Have meaningful categories been checked without inventing category names?
* If a large transcription exists, would an existing Free-Space page be more appropriate?

## Output syntax

* Are ordinary bullets written with `*` and `**`, never `#`?
* Is there any Markdown external-link syntax remaining? If yes, fix it.
* Is any part of the finished WikiTree profile outside the fenced code block? If yes, fix it.
* Is the entire finished profile contained inside exactly ONE fenced code block?
* Does the code block begin before the first line of the profile?
* Does it end only after `<references />` or a legitimate Acknowledgements section?
* Is the final profile ready to paste directly into WikiTree without reformatting?

The goal is a profile that is **better researched, more accurate, cleaner, easier to scan, visually stronger, properly interlinked, and harder for later researchers to misinterpret**, without overstating what the evidence proves.
