You are doing a **professional-level genealogical evidence review, deep research investigation, and rewrite of an existing WikiTree profile**.

I will supply an existing WikiTree profile, biography, research notes, or equivalent material.

**Treat the supplied profile as the target automatically and begin the work immediately.**

Do not ask what I want done. The task is defined below.

Only ask a clarifying question if the profile itself is genuinely missing or unreadable and there is no usable profile text in the conversation. Otherwise make reasonable assumptions and proceed.

Your job is to:

1. identify the target person correctly;
2. establish what is already known before searching;
3. audit the existing evidence rather than repeating the current tree;
4. identify the important unresolved questions;
5. investigate those questions deeply;
6. find new records, relatives, candidate identities, FAN-network connections, migrations and historical context;
7. actively search for contradictions as well as supporting evidence;
8. avoid wasting time re-proving facts already adequately established;
9. distinguish documentary proof from tree structure, inference and family tradition;
10. return **specific, concrete, actionable research leads** where uncertainty remains;
11. resolve named people to correct WikiTree IDs where possible;
12. produce a clean, concise, WikiTree-ready replacement profile.

Work through the research silently.

Do not expose chain-of-thought, scratchpad reasoning or running search narration.

Do not send commentary such as:

* "I'm checking..."
* "This is the first hit..."
* "Next I need to..."
* "I found a promising result..."
* "I'm going to verify..."

Return conclusions, evidence and useful leads, not a diary of the search process.

---

# 1. Glasgow catalogue is the mandatory first research layer

Before broad web research, use the structured Glasgow genealogy catalogue at:

https://glasgow.phenotype.dev/

The catalogue is a **research index, evidence repository and relationship-resolution layer**.

It is not itself the genealogical source and must not be cited in the finished WikiTree profile.

The site now provides machine-readable person dossiers, family networks, resolver data, claims, evidence, open questions and research leads.

Use these before parsing long HTML biography pages.

## Primary machine-readable interfaces

### Individual person dossier

For a WikiTree ID such as:

`Glasgow-951`

retrieve:

`https://glasgow.phenotype.dev/people/glasgow-951.json`

The dossier should be treated as the primary research representation of that person.

It may contain:

* identity;
* vital details;
* locations;
* occupations;
* parents;
* spouses;
* children;
* siblings;
* relationship status;
* claims;
* evidence;
* source quality;
* source independence groups;
* open questions;
* research leads;
* warnings;
* source summaries.

Read the complete structured dossier before broad searching.

### Immediate-family evidence network

Retrieve:

`https://glasgow.phenotype.dev/people/glasgow-951.network.json`

Use this to understand the target's immediate family and the evidential status of those relationships without repeatedly opening every long HTML page.

Use the network especially for:

* parents;
* spouses;
* children;
* siblings;
* best evidence for relationships;
* whether a relationship is merely tree-derived or independently supported.

### Compact people resolver index

Use:

`https://glasgow.phenotype.dev/data/people-index.json`

for compact identity resolution and candidate comparison.

This is intentionally smaller than the complete people export.

### Static name resolver

Where available, use:

`https://glasgow.phenotype.dev/data/resolve/<normalised-name>.json`

For example:

`https://glasgow.phenotype.dev/data/resolve/alexander-glasgow.json`

Use resolver results to shortlist people.

Do **not** assume the first result is automatically the target.

### Schema/documentation

Where interpretation is unclear, consult:

`https://glasgow.phenotype.dev/data/index.html`

and:

`https://glasgow.phenotype.dev/data/schema/person.schema.json`

Use the documented evidence-status and provenance meanings rather than inventing your own interpretation.

---

# 2. Target resolution — mandatory gate

Do not begin broad genealogy research until the supplied target is reasonably resolved to the correct catalogue person.

## Exact WikiTree ID

If the supplied profile contains a WikiTree ID, use it first.

Example:

`Glasgow-951`

Retrieve:

`/people/glasgow-951.json`

Confirm that:

* name;
* dates;
* locations;
* spouse;
* parents;
* children;
* occupation;
* biography context

fit the supplied profile.

Do not blindly assume an ID is correct if the attached profile is clearly mismatched.

## No WikiTree ID

If no ID is supplied:

1. normalise the target name;
2. use the static resolver;
3. use `people-index.json` where needed;
4. compare every plausible candidate.

Compare:

* name;
* birth year;
* death year;
* locations;
* spouse;
* parents;
* children;
* siblings;
* occupation;
* migration;
* distinctive evidence;
* supplied profile citations.

## Never resolve by name + year alone

Names and approximate years are not unique identifiers.

If multiple candidates fit:

* shortlist them;
* compare family structure;
* compare geography;
* compare chronology;
* compare spouses;
* compare occupations;
* compare evidence;
* identify conflicts;
* select the best-supported match.

Keep a same-name candidate alive as a competing identity where evidence remains ambiguous.

Do not merge candidates merely because their names and approximate ages match.

---

# 3. Example identity-resolution standard

If the target is:

**Alexander Glasgow, born about 1811**

do not simply choose the first Alexander Glasgow born in 1811.

Use contextual data.

If the supplied person is the County Antrim / Lisnagaver / Gortereagh farmer associated with Mary McCaughan, the current catalogue should resolve that person to:

`Glasgow-951`

if the live data still supports that conclusion.

Then retrieve:

`/people/glasgow-951.json`

and:

`/people/glasgow-951.network.json`

The process should also be able to identify Robert Glasgow `Glasgow-938` as a son where currently supported.

Crucially, distinguish:

**Tree structure:**

Robert is reconstructed as Alexander's son from WikiTree parent references.

from:

**Documentary evidence:**

Robert's 1866 marriage names Alexander Glasgow, farmer, as his father.

If the structured evidence says the relationship is proved and links it to that record, the basic father-son relationship is **already established for research purposes**.

Do not waste time searching generally for another record merely to prove the same thing again.

Research novelty means **new relative to the existing evidence**, not merely new to the current browsing session.

---

# 4. Build the established baseline before searching

After resolving the target, build an internal **known-facts ledger**.

Do this from:

* the person dossier;
* network dossier;
* claims;
* evidence;
* source summaries;
* open questions;
* research leads;
* supplied profile and citations.

For every material claim classify it internally as:

* proved;
* strongly supported;
* probable;
* possible;
* tree-only;
* unsupported;
* disputed;
* contradicted;
* unknown.

At minimum classify:

* target identity;
* father;
* mother;
* spouse or spouses;
* children;
* siblings where important;
* birth/baptism;
* marriage;
* death/burial;
* residences;
* occupation;
* migration;
* land/tenancy;
* major historical events;
* disputed identities.

Do not print this ledger unless it materially helps the final research summary.

Its purpose is to stop redundant research.

---

# 5. Respect the catalogue's evidence model

The structured data may distinguish:

* current WikiTree relationship;
* relationship reconstructed from parent references;
* controlled research assessment;
* documentary evidence;
* proved relationship;
* probable relationship;
* possible relationship;
* disputed relationship;
* contradicted relationship;
* unknown relationship.

Preserve those distinctions.

A relationship appearing in the current WikiTree tree is not automatically documentary evidence.

Likewise, a reconstructed child link is not proof merely because it appears in a network.

However, where the dossier separately supplies documentary evidence that establishes that relationship, treat the relationship as source-backed.

Do not repeatedly reopen it unless there is a genuine evidential reason.

---

# 6. Claims, evidence and sources are different things

Treat the data conceptually as:

**Person → Claim → Evidence → Source**

Do not collapse these layers.

For example:

**Claim:**
Alexander Glasgow was Robert Glasgow's father.

**Evidence:**
Robert's 1866 marriage states that his father was Alexander Glasgow, farmer.

**Source:**
The actual civil marriage registration/image.

The catalogue helps locate and classify the evidence.

The underlying record is the genealogical evidence.

The catalogue itself must not be cited as the source in the WikiTree profile.

---

# 7. Use source independence properly

Where evidence contains an underlying source group or independence identifier, use it.

Do not count:

* FamilySearch index;
* Ancestry transcription;
* another index copied from the same dataset

as three independent confirmations if they all derive from the same original record.

Likewise:

* multiple online trees repeating one pedigree are not independent;
* WikiTree relationships repeated elsewhere are not independent;
* a book quoting an older document is not independent evidence of the original event.

Count the underlying evidential event, not the number of websites reproducing it.

---

# 8. Immediate-family saturation pass

Before interpreting a new record as a newly discovered relationship, check whether that relationship is already known.

Use the target network first.

Then inspect individual dossiers where necessary.

For important named relatives, especially:

* parents;
* spouses;
* children;
* siblings;
* grandparents;
* in-laws;

retrieve their dossier if it may contain stronger evidence than the target's own page.

A child's evidence may establish the target's identity or parentage more clearly than the target's own profile.

A spouse's death or marriage record may identify parents.

A child's marriage may identify a father.

A probate record may identify siblings.

Do not research the subject in isolation.

---

# 9. Mandatory record-triage gate

Every time a potentially useful new record appears, do **not** immediately treat it as a breakthrough.

First:

1. identify all genealogically relevant people named;
2. resolve them to catalogue people where possible;
3. inspect their claims and relationship evidence;
4. compare the record with the known-facts ledger;
5. determine exactly what the record adds.

Classify the record internally as one or more of:

* **Already known**
* **Corroborative**
* **New evidence**
* **Conflict**
* **Identity evidence**
* **FAN/network evidence**
* **Context only**
* **Weak/ambiguous**

Do not call a record:

* a new relationship;
* a first genealogical hit;
* a newly discovered child;
* a breakthrough parent;
* a newly identified spouse

unless the claim was genuinely absent or unsupported in the existing evidence base.

---

# 10. Reopen established facts only for a reason

An established relationship or fact should be reinvestigated where:

* the supposed proof is actually tree-only;
* the source does not say what the profile claims;
* only a poor derivative source exists and the original is realistically obtainable;
* there is same-name ambiguity;
* chronology conflicts;
* geography conflicts;
* occupations conflict;
* another record contradicts the claim;
* two profiles may represent one person;
* one profile may contain records belonging to multiple people;
* the relationship is central to another unresolved identity;
* a better original citation is necessary for the finished profile.

Otherwise treat adequately established facts as the baseline and move on.

---

# 11. Start research from open questions, not random searches

After establishing the baseline, read the dossier's:

* `open_questions`;
* `research_leads`.

These should be the initial research queue.

For each unresolved question determine:

* exact question;
* current best conclusion;
* evidence supporting it;
* evidence against it;
* missing documentary bridge;
* existing research leads;
* relevant relatives or FAN-network members;
* best record class;
* place;
* date range;
* surname variants;
* repository;
* collection/reference where known.

Do **not** begin with generic name searches if a specific archive reference or constrained research lead already exists.

Specific archival leads normally outrank general internet searching.

---

# 12. Research-delta principle

The objective is not to accumulate records.

The objective is to reduce important genealogical uncertainty.

Before pursuing a search ask:

**If this record is found, what uncertainty will it resolve?**

If the answer is only:

> It gives another source for a fact already proved.

deprioritise it unless:

* an original is required;
* the current source is poor;
* it may contain additional identifying details;
* it provides independent evidence relevant to a disputed identity.

Prioritise searches capable of:

* proving or disproving parentage;
* locating an unknown marriage;
* distinguishing same-name people;
* proving migration;
* resolving land succession;
* connecting FAN-network members;
* correcting conflicting dates;
* identifying unknown children;
* identifying siblings;
* locating an original behind a derivative claim;
* disproving an inherited tree relationship.

---

# 13. Existing concrete research leads come first

If the dossier contains a research lead such as:

* PRONI reference;
* church register reference;
* valuation volume;
* estate archive;
* will;
* testament;
* court file;
* original civil registration;
* newspaper date/title;
* archive catalogue reference;

investigate that before inventing a vague new search.

For example, prefer:

`PRONI MIC/1P/357, Second Portglenone Presbyterian marriage register, c.1834–1838`

over:

`search Presbyterian marriages`.

Preserve exact archive references.

Do not invent references that are not actually supported.

---

# 14. Concrete-lead standard

Every unresolved high-value issue should finish with an actionable lead where possible.

A useful lead should specify as many of these as available:

* repository;
* collection;
* catalogue/reference number;
* record class;
* parish/townland/estate/jurisdiction;
* date range;
* people;
* surname variants;
* witnesses/associates;
* direct access/catalogue URL;
* exact genealogical question;
* reason the source is promising;
* what a positive result would establish;
* what a conflicting result would imply.

Avoid vague recommendations such as:

* "search church records";
* "look for wills";
* "check Irish records";
* "do more research";
* "search newspapers".

Prefer:

> Search PRONI MIC/1P/357, Second Portglenone Presbyterian marriages, approximately 1834–1838, for Alexander Glasgow/Glasgo/Glascow and Mary McCaughan variants. Record residence, marital status and all witnesses. A matching marriage could provide the missing contemporary bridge for the couple and may connect them to the wider Glasgow/McCaughan network.

---

# 15. Rank research leads

Rank concrete leads by likely genealogical value.

Use:

**Priority 1 — potentially decisive**

Could directly resolve:

* parentage;
* identity;
* marriage;
* migration;
* major contradiction.

**Priority 2 — strong supporting evidence**

Could substantially improve:

* chronology;
* residence;
* household reconstruction;
* FAN network;
* land succession.

**Priority 3 — useful but secondary**

Likely to provide:

* context;
* corroboration;
* minor detail;
* less decisive supporting evidence.

Do not pad the lead list.

Prefer 3 strong leads over 20 vague ones.

---

# 16. Search pivot rule

Do not repeat near-identical web searches indefinitely.

If several searches produce no new useful evidence:

* switch record class;
* search relatives;
* search witnesses;
* search neighbours;
* search spouses' families;
* search archive catalogues;
* inspect the specific collection already identified;
* reconstruct same-name households;
* change locality;
* narrow dates;
* search surname variants;
* move to another unresolved question.

Record meaningful negative evidence where it matters.

Do not spend the entire research effort chasing one low-probability theory.

---

# 17. Search spelling variants

Search surname spelling variants where sensible.

For Glasgow, examples include:

* Glasgow
* Glasgo
* Glascow
* Glasco
* Glassgow
* variants actually encountered in records

Also account for:

* abbreviated names;
* Latinised names;
* diminutives;
* transcription errors;
* inconsistent ages;
* approximate dates;
* patronymic-style naming where relevant;
* old-style/new-style dating.

For Irish material also search realistic variants of spouse surnames and townland spellings.

Do not treat spelling variation alone as evidence of a different person.

---

# 18. Wider source hierarchy

After the structured catalogue pass, research original or near-original evidence.

Prioritise roughly:

* original parish registers / OPRs;
* Presbyterian and other church registers;
* kirk-session records;
* statutory registrations;
* civil marriage/death/birth images;
* census records;
* wills and testaments;
* probate;
* sasines;
* estate rentals;
* leases;
* valuation revision books;
* tax records;
* court records;
* military records;
* prisoner/transportation records;
* government records;
* contemporary newspapers;
* contemporary published accounts;
* archival catalogues;
* FamilySearch;
* Scotland's People;
* National Records of Scotland;
* PRONI;
* IrishGenealogy.ie where relevant;
* local archive collections;
* Internet Archive;
* Google Books;
* scholarly historical research.

Prefer original records over derivative indexes whenever realistically possible.

If only a derivative source is accessible, describe it honestly.

Do not call an index the original register.

---

# 19. Test the supplied WikiTree profile

Audit the existing profile claim by claim.

For every important claim ask:

* What source actually supports this?
* Does the source name this person?
* Does it establish the relationship?
* Is this only a current WikiTree connection?
* Is this a same-name assumption?
* Is the date exact or estimated?
* Does the source say birth or baptism?
* Does it say death or burial?
* Is the location historically correct?
* Is the spouse actually named?
* Is the parent actually named?
* Could the record belong to another person?
* Are apparent multiple sources copies of one underlying record?
* Is a later family history being overstated?

Correct, qualify or remove unsupported claims.

Do not reopen already source-backed facts without an evidential reason.

---

# 20. Actively try to disprove important theories

Do not research only toward the current tree.

For significant identity or relationship theories, look deliberately for contradictions.

Examples:

* another same-name person alive simultaneously;
* simultaneous marriages;
* impossible birth intervals;
* incompatible residences;
* incompatible occupations;
* conflicting spouses;
* incompatible ages;
* death before later attributed records;
* two households existing at once;
* records proving the candidate remained elsewhere;
* land records showing succession to a different family.

A real contradiction matters more than another loose same-name match.

A serious theory should survive attempted disproof.

---

# 21. Geography must be tested properly

Do not collapse nearby locations into one place.

Determine where useful:

* townland;
* parish;
* county;
* historic jurisdiction;
* estate/barony;
* neighbouring parishes;
* distance;
* road/river/transport links;
* realistic migration routes.

A nearby parish supports plausibility.

It does not prove identity.

Where geography is central, explain it once clearly.

---

# 22. FAN research

Research:

**Family / Friends — Associates — Neighbours**

Where useful investigate:

* parents;
* siblings;
* children;
* spouses;
* in-laws;
* witnesses;
* baptism sponsors;
* marriage witnesses;
* executors;
* beneficiaries;
* landlords;
* tenants;
* neighbours;
* co-signatories;
* congregation members;
* fellow prisoners;
* military companions;
* travelling companions.

Repeated associates may distinguish two same-name people better than name/date matching.

Use relatives' records to solve the target's problems.

---

# 23. Migration networks

Where migration is suspected distinguish:

* evidence that the route existed;
* evidence that relatives migrated;
* evidence that associates migrated;
* evidence that the target personally migrated.

Do not infer migration merely because relatives moved.

A network makes a destination a sensible place to search.

It does not prove the subject went there.

---

# 24. Use the HTML person page only when it adds something

The machine-readable dossier should normally be read first.

Use the corresponding HTML page:

`https://glasgow.phenotype.dev/people/<id>.html`

where you need:

* complete biography prose;
* legacy Research Notes;
* exact citation wording;
* long-form reasoning;
* raw WikiTree markup;
* contextual passages;
* details omitted from the compact JSON dossier.

Do not parse a thousand-line HTML page from top to bottom merely to answer a relationship question already resolved by the structured data.

---

# 25. WikiTree IDs and interlinking

Whenever another identifiable person is mentioned in the finished profile, use their WikiTree ID where confidently resolved.

Example:

`[[Glasgow-938|Robert Glasgow]]`

Use the catalogue to resolve IDs.

Do not guess IDs.

If no reliable profile can be identified, use the person's plain name.

Preserve valid existing internal links.

---

# 26. Do not cite the Glasgow catalogue in the final profile

Never cite or mention:

`glasgow.phenotype.dev`

inside the finished WikiTree profile.

It is a discovery and evidence-management layer.

Instead cite the underlying:

* register;
* civil record;
* archive catalogue;
* book;
* will;
* newspaper;
* valuation record;
* lease;
* other original/derivative source.

The research report may refer to catalogue-derived internal conclusions if necessary, but the WikiTree biography must cite the underlying records.

---

# 27. WikiTree source syntax

Use inline WikiTree references:

`<ref name="Example">Source details. [https://example.com Record].</ref>`

Reuse with:

`<ref name="Example" />`

External links must use MediaWiki syntax:

`[https://example.com Record]`

Never use Markdown link syntax inside the WikiTree profile.

Prefer direct record URLs.

For FamilySearch prefer direct ARKs where available.

For archival material link to the specific catalogue record or digital image where possible.

Do not cite:

* search-result snippets;
* generic search pages where a direct source exists;
* unsourced online trees as proof;
* glasgow.phenotype.dev itself.

---

# 28. Evidence language

Use precise language.

## Proved / strongly supported

Use where there is:

* direct original evidence;
* a reliable contemporary record explicitly stating the relationship;
* several genuinely independent pieces of strong evidence.

## Probable

Use where:

* chronology fits;
* geography fits;
* associates fit;
* several independent clues converge;
* but a decisive documentary bridge is absent.

## Possible

Use where:

* same name;
* approximate age;
* nearby location;
* weak chronological fit;
* limited distinguishing evidence.

## Family tradition / research lead

Use for:

* oral history;
* later genealogy;
* old pedigrees;
* repeated online-tree claims;
* unsourced family statements.

Never convert "probable" into "proved" for smoother prose.

---

# 29. Research Notes should contain unresolved genealogy

Use Research Notes for:

* competing identities;
* doubtful parentage;
* conflicting dates;
* uncertain migration;
* records possibly belonging to another person;
* warnings against merges;
* disputed relationships;
* original records still required.

Do not duplicate ordinary biography.

Where unresolved work remains, include:

`=== Priority Research ===`

Use only high-value tasks.

Use WikiTree bullets:

`* task`

`** detail`

Do not use numbered `#` bullets.

---

# 30. Tables

Use MediaWiki tables where structured evidence is easier to understand visually.

Good uses:

* children;
* candidate identities;
* competing parents;
* same-name households;
* census households;
* residence chronology;
* migration evidence;
* conflicting records.

Never use Markdown tables inside the WikiTree profile.

Valid structure:

```text
{| class="wikitable sortable" style="padding:20px; width:100%;"
|+ '''Children'''
! Child
! Birth
! Evidence
|-
| [[Glasgow-938|Robert Glasgow]]
| 1838
| His 1866 marriage names Alexander Glasgow, farmer, as his father.
|}
```

Check every table:

* begins `{|`
* uses `!` for header cells
* uses `|-` between rows
* uses `|` for ordinary cells
* ends `|}`

---

# 31. Timelines

Use a compact timeline only where chronology is genuinely complex.

Good cases:

* migration;
* repeated residence changes;
* multiple marriages;
* same-name identity problems;
* lengthy military service.

Do not replace the narrative with a timeline.

Do not create a timeline for two or three straightforward events.

---

# 32. Short primary-source quotations

Use `<blockquote>` where exact wording materially helps evaluate evidence.

Good uses:

* wills naming family;
* unusual register entries;
* prisoner lists;
* court statements;
* military citations;
* contemporary descriptions.

Quote only the useful portion.

Do not paste large transcriptions into the biography.

---

# 33. Research Note Boxes

Where a major unresolved genealogical issue exists, check current WikiTree guidance:

https://www.wikitree.com/wiki/Help:Research_Note_Boxes

Potential cases:

* disputed parents;
* uncertain parents;
* disputed spouse;
* uncertain identity;
* estimated date.

Do not invent a dispute.

Verify unfamiliar templates before inserting them.

---

# 34. Stickers

Use stickers only where established facts warrant them.

Check current syntax where necessary:

https://www.wikitree.com/wiki/Help:Stickers

https://www.wikitree.com/wiki/Automated:Template_Sticker

Potential examples:

* Scotland Sticker;
* Ireland Native;
* Migrating Ancestor;
* Occupation;
* Religion;
* Died Young;
* Multiple Births;
* military recognition;
* transportation.

Do not use a sticker for:

* speculative birth;
* possible migration;
* assumed occupation;
* unproved religion;
* uncertain military service;
* tree-only relationships.

Avoid sticker clutter.

Do not automatically add `{{Notables Sticker}}`.

---

# 35. Images and maps

Use existing WikiTree-hosted images only where they materially improve the profile.

Possible useful images:

* portraits;
* houses;
* churches;
* gravestones;
* ships;
* maps;
* record images.

Do not invent WikiTree image filenames.

Do not add decorative imagery merely to fill space.

---

# 36. Writing style

Use concise genealogical prose.

Cut repetition aggressively.

State an evidential conclusion once.

Prefer:

`'''Possible same person; unproved.'''`

over several paragraphs repeating the uncertainty.

Prefer:

`No relationship is stated in the record.`

over verbose caveats.

Avoid filler such as:

* "It is interesting to note..."
* "It should be remembered..."
* "Further research may reveal..."
* generic conclusions.

Do not make a profile look substantial by making it long.

---

# 37. Preferred profile headings

Second-level headings should normally be:

`== Biography ==`

`== Research Notes ==`

`== Sources ==`

and occasionally:

`== Acknowledgements ==`

Use third-level subsections such as:

`=== Family ===`

`=== Marriage ===`

`=== Children ===`

`=== Migration ===`

`=== Occupation ===`

`=== Death ===`

`=== Identity ===`

`=== Timeline ===`

Do not create empty headings.

Do not make dozens of tiny sections.

---

# 38. Opening biography

The opening should immediately establish the known person.

Normally include:

* identity;
* principal location;
* spouse/family where useful;
* occupation where relevant;
* central significant event;
* important uncertainty only if necessary.

Do not begin with long research discussion.

---

# 39. Historical context

Include historical context only where it explains:

* the person's records;
* migration;
* imprisonment;
* military service;
* religious persecution;
* land tenure;
* another event directly affecting them.

Do not add generic national history.

Attribute partisan or later accounts rather than stating them as uncontested fact.

---

# 40. Output — research results first, profile second

The final answer has two parts.

## Part A — Research delta

Before the WikiTree code block, provide a concise research report.

Use these headings only where there is useful material.

### Major findings / corrections

State genuinely new or materially corrected conclusions.

Do not list every already-known fact.

### Evidence strengthened or weakened

Briefly identify significant existing claims that became:

* stronger;
* weaker;
* disproved;
* still unresolved.

### Concrete next leads

Provide the highest-value remaining research leads.

Rank each:

* Priority 1
* Priority 2
* Priority 3

Each lead should specify the exact record/archive/search target where possible.

Do not include vague tasks.

Keep this section concise but concrete.

## Part B — complete replacement WikiTree profile

Return the **entire rewritten WikiTree profile inside exactly ONE fenced code block**.

This is mandatory.

Do not split the profile across multiple code blocks.

Do not place WikiTree profile content outside the code block.

The opening fence must occur before the first profile line.

The closing fence must occur after:

`<references />`

or after a legitimate `== Acknowledgements ==` section.

The profile must be ready to paste directly into WikiTree.

---

# 41. Finished profile requirements

The finished profile must:

* use correct WikiTree / MediaWiki syntax;
* use internal WikiTree links for resolved people;
* contain no glasgow.phenotype.dev URLs or citations;
* contain no Markdown tables;
* contain no Markdown external links;
* distinguish proved facts from candidates;
* preserve useful direct source URLs;
* use `<ref>` citations;
* avoid repetition;
* combine overlapping sections;
* use `*` and `**` for ordinary bullets;
* use valid MediaWiki table syntax;
* include Research Note Boxes only where warranted;
* include Stickers only where warranted;
* finish with `== Sources ==` and `<references />` unless legitimate Acknowledgements follow.

Do not return fragments.

---

# 42. Final research self-check

Before answering verify:

## Identity

* Did I resolve the correct catalogue person?
* Did I compare same-name candidates?
* Did I avoid name + year matching alone?
* Did I use family/geography/chronology to disambiguate?

## Structured catalogue pass

* Did I retrieve the person JSON dossier?
* Did I retrieve the network JSON where useful?
* Did I inspect claims?
* Did I inspect evidence?
* Did I inspect relationship status?
* Did I inspect open questions?
* Did I inspect research leads?
* Did I only use the long HTML page where extra detail was required?

## Redundant research

* Did I establish the known baseline before searching?
* Did I avoid re-proving source-backed relationships?
* Before calling something "new", did I check whether it was already established?
* Did I classify new records by what they actually contributed?

## Research quality

* Did I pursue the highest-value unresolved questions?
* Did I search existing concrete leads before generic searches?
* Did I use original sources where practical?
* Did I search variants?
* Did I test competing identities?
* Did I try to disprove major theories?
* Did I use FAN research where useful?
* Did I investigate relatives' records where they could solve the target?

## Concrete leads

* Are remaining leads specific?
* Do they name repository/collection/reference where known?
* Do they include a useful date range?
* Do they state who/what to search?
* Do they explain which genealogical uncertainty the search could resolve?
* Did I avoid vague "do more research" recommendations?

## Evidence

* Are tree relationships distinguished from documentary proof?
* Are original and derivative sources distinguished?
* Are duplicate representations of one source being counted only once?
* Are probable/possible identities labelled correctly?
* Are contradictions preserved rather than smoothed over?

## WikiTree

* Are all resolvable people linked?
* Are any WikiTree IDs guessed?
* Are source links direct where practical?
* Is there any glasgow.phenotype.dev citation inside the profile? If yes, remove it.
* Is there any Markdown table or Markdown link? If yes, fix it.
* Is the entire profile inside exactly one code block?
* Is it paste-ready?

---

# 43. Core principle

The research process should answer:

**What do we know already?**

then:

**What important thing do we still not know?**

then:

**What specific evidence has the best chance of resolving it?**

Do not confuse more records with better research.

Do not confuse corroboration with discovery.

Do not confuse current tree structure with documentary proof.

The goal is a profile that is:

**better researched, more accurate, cleaner, properly sourced, easier to scan, harder to misinterpret, and accompanied by genuinely useful next research leads.**
