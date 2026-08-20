You are tidying, restructuring and visually improving an existing WikiTree profile.

This is an **editorial cleanup task, not a genealogical research task**.

I have attached an existing WikiTree profile or biography.

Your job is to:

1. preserve the substantive genealogical information already present;
2. remove repetition and unnecessary prose;
3. improve structure, readability and visual hierarchy;
4. turn repetitive groups of records, children, candidates, households, etc. into proper WikiTree tables where useful;
5. interlink people mentioned in the profile to their existing WikiTree profiles;
6. add a small number of appropriate WikiTree Stickers where the existing evidence clearly supports them;
7. use useful WikiTree presentation features such as Research Note Boxes, quotations, images, maps, categories and timelines where they materially improve the profile;
8. preserve useful source citations and URLs;
9. return the entire cleaned profile ready to paste directly into WikiTree.

Do **not** perform new genealogical research.

Do **not** search the wider web for new records, relationships or biographical facts.

Do **not** introduce new genealogical claims merely because they seem plausible.

# 1. Permitted lookup: Glasgow genealogy catalogue

The primary lookup tool for this cleanup task is the Glasgow surname catalogue:

https://glasgow.phenotype.dev/data/people-index.json

https://glasgow.phenotype.dev/data/people.json

https://glasgow.phenotype.dev/data/wikitree-profile-evidence.json

https://glasgow.phenotype.dev/data/records.json

Use this catalogue primarily to identify the correct existing WikiTree profiles for people already mentioned in the supplied profile.

## How to use it

Start with:

https://glasgow.phenotype.dev/data/people-index.json

Use it to resolve names to likely WikiTree IDs.

Where necessary:

* follow the person's individual HTML page;
* inspect enough identifying information to distinguish people with the same name;
* compare dates, places, spouse, parents or children already stated in the supplied profile;
* inspect the person's evidence section where necessary to distinguish similarly named profiles;
* use `people.json`, `wikitree-profile-evidence.json` or `records.json` only where needed to distinguish candidates.

The goal is primarily to convert names such as:

`John Glasgow`

into:

`[[Glasgow-1498|John Glasgow]]`

where the identity is sufficiently clear.

Do not guess WikiTree IDs.

If two catalogue profiles could plausibly represent the person mentioned and the supplied profile does not provide enough information to distinguish them, leave the name unlinked rather than choosing arbitrarily.

## Important catalogue rule

Do not cite or mention `glasgow.phenotype.dev` in the finished WikiTree profile.

It is an editorial lookup tool only.

Do not use relationships shown in the catalogue as new genealogical evidence.

For example, if the supplied profile merely says:

`John Glasgow`

and the catalogue shows a John Glasgow attached to particular parents, do not add those parents unless they were already stated in the supplied profile.

Do not expand the biography with new catalogue-derived facts.

The catalogue may resolve **who an existing mention refers to**; it should not become a source of new biography content during this cleanup task.

# 2. No new genealogical research

Do not search for new genealogical evidence on:

* Google;
* FamilySearch;
* Scotland's People;
* Ancestry;
* National Records of Scotland;
* PRONI;
* Internet Archive;
* Google Books;
* newspapers;
* archive catalogues;
* other genealogy sites;
* unrelated WikiTree profiles.

Do not verify or disprove the existing genealogy.

Do not turn this into an identity investigation.

If the supplied profile contains an uncertain statement such as:

`William may have been the same person as...`

preserve the uncertainty.

Do not strengthen it to:

`William was the same person as...`

Likewise, do not weaken an explicitly sourced fact merely because you have not independently researched it.

Your job is to tidy and present the evidence already supplied.

# 3. Preserve evidence and meaning

Do not remove useful genealogical information merely to shorten the profile.

Preserve:

* dates;
* places;
* relationships;
* candidate identities;
* conflicting records;
* migration information;
* occupations;
* religious affiliations where relevant;
* military information;
* historical events directly relevant to the person;
* research warnings;
* useful explanations of uncertainty;
* source references;
* URLs;
* WikiTree profile IDs;
* archive references;
* record identifiers.

Cut repetition, not information.

If the same point appears:

* in the Biography;
* again in a subsection;
* again under Identity;
* again under Research Notes;

state it once in the best location.

# 4. Follow WikiTree biography structure

The profile should normally use these second-level sections only:

`== Biography ==`

`== Research Notes ==`

`== Sources ==`

and, only where genuinely needed:

`== Acknowledgements ==`

Subjects such as:

* Birth;
* Family;
* Marriage;
* Children;
* Occupation;
* Military Service;
* Migration;
* Census;
* Death;
* Burial;
* Historical Event;
* Timeline;
* Identity;

should normally be third-level subsections beneath `== Biography ==` or `== Research Notes ==`.

For example:

`=== Family ===`

not:

`== Family ==`

Keep the heading hierarchy clean and consistent.

# 5. Improve the opening biography

The first paragraph should quickly establish:

* who the person was;
* where they were principally associated;
* the strongest known life events;
* their occupation or significance where relevant;
* any major unresolved identity issue only if it is central to understanding the profile.

Avoid opening with several paragraphs of research discussion.

Prefer:

`William Glasgow was a Scottish Covenanter associated with Cavers parish, Roxburghshire. He was recorded among the survivors of the 1679 wreck of the ''Croune of London''.`

rather than making the reader work through several paragraphs before learning who the person was.

For an ordinary family profile, the opening might instead summarise:

* birth;
* spouse;
* principal residence;
* occupation;
* death.

Keep the lead concise.

# 6. Combine overlapping sections

Look for sections that cover substantially the same issue.

Common examples:

`=== Identity ===`

`=== Possible Identity ===`

`=== Possible Birth ===`

`=== Other William Glasgow ===`

`=== Research Notes ===`

These should usually be consolidated.

Use a small number of meaningful sections.

A typical structure might be:

`== Biography ==`

`=== Family ===`

`=== Migration ===`

`=== Occupation ===`

`=== Records relevant to identity ===`

`== Research Notes ==`

`=== Priority Research ===`

`== Sources ==`

Do not force this exact structure where it does not suit the profile.

# 7. Use tables where they materially improve clarity

Use tables for structured evidence.

Good table candidates include:

* children;
* marriages;
* siblings;
* candidate identities;
* same-name records;
* residences;
* census households;
* baptism records;
* migration candidates;
* conflicting birth or death records;
* multiple possible parents;
* repeated records from the same register;
* structured timelines.

Do not create a table merely for decoration.

Do not turn ordinary narrative biography into a spreadsheet.

If prose already explains a sequence clearly, leave it as prose.

## WikiTree table syntax

Tables must use literal MediaWiki/WikiTree syntax.

Never use Markdown tables.

Example:

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
| Relevant same-parish record. Existing uncertainty about her parentage should remain explicit.
|}
```

Another useful format:

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
|-
| [[Glasgow-938|Robert Glasgow]]
| About 1840 or 1841
| County Antrim
| Recorded as their ten-year-old son in 1851.
|}
```

Before answering, check that every table:

* begins with `{|`;
* uses `!` for header cells;
* separates rows with `|-`;
* uses `|` for ordinary cells;
* ends with `|}`;
* contains no Markdown table syntax.

# 8. Timelines

A timeline can be useful where chronology is genuinely complicated.

Do not replace the biography with a timeline.

Narrative biography comes first.

A compact timeline may follow where it helps the reader understand:

* repeated migration;
* military service;
* several marriages;
* residence changes;
* overlapping candidate records;
* a long sequence of documented events.

Prefer a table such as:

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

Do not create a timeline for a person with only two or three straightforward life events.

# 9. Interlink people consistently

Whenever an identifiable person is mentioned, use their internal WikiTree link.

Use:

`[[Glasgow-1498|John Glasgow]]`

rather than:

`John Glasgow`

This applies to:

* parents;
* spouses;
* children;
* siblings;
* grandparents;
* candidate identities;
* possible relatives;
* people compared in Research Notes;
* witnesses or associates where they are important and an existing profile can be confidently identified.

Use the Glasgow catalogue to resolve IDs.

Do not guess WikiTree IDs.

If no reliable profile can be identified, use the person's plain name.

Do not add a genealogical relationship merely because the catalogue shows one.

# 10. Names already containing WikiTree links

Preserve existing correct internal links.

If the supplied profile says:

`[[Glasgow-2730|Margaret Glasgow]]`

do not replace it with a plain name.

If the display name is awkward, it may be cleaned while preserving the ID.

For example:

`[[Glasgow-2730|Margaret]]`

may sometimes read better where the surname is already obvious.

Do not change the underlying WikiTree ID unless the supplied link is clearly referring to a different named person and the catalogue resolves the intended profile unambiguously.

# 11. Research Notes

Research Notes should contain unresolved genealogical problems, not duplicate the biography.

Good Research Notes include:

* competing identities;
* doubtful parentage;
* conflicting dates;
* unclear migration;
* records that may concern the same person;
* warnings against unsupported merges;
* uncertain spouses;
* uncertain children;
* unexplained gaps;
* specific records that still need checking.

Bad Research Notes merely repeat known life events.

Prefer concise statements.

For example:

`The 1658 Polwarth baptism is chronologically plausible but no existing evidence in this profile connects the child to Cavers.`

rather than several paragraphs restating the baptism and shipwreck.

# 12. Research Note Boxes

Where the supplied profile contains a significant unresolved genealogical issue, consider whether an official WikiTree Research Note Box would make the warning clearer.

Useful cases include:

* disputed parents;
* uncertain parents;
* disputed spouse;
* estimated dates;
* uncertain identity;
* uncertain existence;
* other formally recognised research problems.

Only add a Research Note Box when:

* the issue is already established in the supplied profile;
* the box materially helps prevent a bad merge, bad parent attachment or other likely error;
* the exact template syntax is known.

Examples of useful known boxes include:

`{{Disputed Parents}}`

and, where appropriate:

`{{Estimated Date}}`

Do not guess Research Note Box names.

Do not create a new dispute merely to justify a box.

Do not use a Research Note Box for minor uncertainty that can be handled with one sentence in Research Notes.

# 13. Priority Research

If the supplied profile already contains research tasks, consolidate them under:

`=== Priority Research ===`

Use WikiTree bullet syntax:

`* first task`

and nested bullets:

`** detail`

Never use `#` for ordinary bullet lists.

Do not invent a large new research programme.

You may reword and organise research tasks already implicit or explicit in the supplied profile.

For example, if the profile says several times that an original baptism should be checked, reduce that to one clear Priority Research item.

# 14. Sources and citations

Preserve meaningful existing `<ref>` citations and direct source URLs.

Use:

`<ref name="Example">...</ref>`

and reuse with:

`<ref name="Example" />`

Where identical sources are cited multiple times under slightly different reference names, consolidate them where safe.

Do not remove a useful source simply because the prose citing it has been shortened.

Do not invent source details.

Do not change a derivative source into an original source.

Do not imply that two copies of the same underlying dataset are independent evidence.

If the profile already explains this distinction, preserve it concisely.

Finish with:

`== Sources ==`

`<references />`

Avoid adding a redundant manual list of every URL after `<references />` unless the supplied profile has a genuine reason to retain one.

## External-link syntax

Use WikiTree / MediaWiki external-link syntax:

`[https://example.com Record]`

Do not use Markdown external-link syntax:

`[Record](https://example.com)`

When preserving an existing source URL, convert Markdown-style links to
WikiTree / MediaWiki syntax where necessary.

Examples:

Correct:
`<ref name="Birth">FamilySearch, baptism record. [https://www.familysearch.org/ark:/61903/1:1:XXXX-XXX FamilySearch record].</ref>`

Incorrect:
`<ref name="Birth">FamilySearch, baptism record. [FamilySearch record](https://www.familysearch.org/ark:/61903/1:1:XXXX-XXX).</ref>`

# 15. Short source quotations

Where an existing source contains a particularly important piece of wording, consider using a short quotation rather than repeatedly paraphrasing it.

Use:

`<blockquote>...</blockquote>`

only where the quotation materially helps the reader understand the evidence.

Good examples include:

* a prisoner list entry;
* a will naming relatives;
* a contemporary description;
* an unusual baptismal note;
* a military citation;
* a short newspaper statement.

Do not reproduce long source transcriptions in the main biography.

Keep quotations short and directly relevant.

Always preserve the citation.

For example:

```text
The contemporary list records:

<blockquote>
"William Glasgow..."
</blockquote><ref name="Example" />
```

Do not use blockquotes merely for decorative effect.

# 16. Images, maps and document images

Where the supplied profile already contains suitable WikiTree images, maps or document images, position them sensibly within the biography.

Useful visual material includes:

* portraits;
* family photographs;
* houses or farms;
* churches;
* gravestones;
* ships;
* military units;
* historical locations;
* parish or migration maps;
* original record images;
* signatures;
* newspaper clippings.

Images should explain the person, place or evidence.

Do not add decorative imagery merely to fill space.

Where appropriate, place a relevant image near the section it supports.

Examples:

* portrait near the opening biography;
* gravestone near Death/Burial;
* migration map near Migration;
* church image near Baptism/Marriage;
* source image near the evidence it documents.

If the supplied profile includes valid image markup, preserve and improve its placement where useful.

Do not invent image filenames.

Do not claim an image exists unless it is already available in the supplied profile/material.

Avoid decorative background images by default.

Inline contextual images are preferable.

# 17. Maps

Maps are particularly useful where geography is important to the genealogy.

Consider an existing map where it helps explain:

* neighbouring parishes;
* migration routes;
* repeated moves;
* disputed locality;
* military movement;
* immigration/emigration.

A map may replace several paragraphs of clumsy geographic explanation.

Do not create or invent a map during this cleanup-only task unless one has already been supplied.

If the profile already includes one, position it near the relevant section and make the surrounding prose concise.

# 18. Large transcriptions and Free-Space pages

Do not let the biography become a dumping ground for enormous source transcriptions.

If the supplied profile contains very long:

* wills;
* newspaper articles;
* military records;
* court cases;
* tax lists;
* letters;
* register transcriptions;

condense the main biography to the genealogically useful information.

If an existing WikiTree Free-Space page containing the full material is already linked, retain that link.

Do not create a new Free-Space page during this cleanup task unless explicitly asked.

Where no Free-Space page exists, preserve important material but avoid deleting unique evidence merely for neatness.

# 19. Categories

Preserve useful existing WikiTree categories.

Examples may include:

* birth or residence location;
* cemetery;
* occupation;
* military unit;
* conflict;
* migration;
* religious group;
* historical event;
* notable grouping.

Do not invent category names.

Do not search WikiTree for new categories during this cleanup-only task.

If existing categories are duplicated, malformed or obviously misplaced in the body of the biography, tidy their placement without changing their substantive meaning.

# 20. Stickers

Add a small number of useful WikiTree Stickers where facts already contained in the supplied profile clearly justify them.

Do not research new facts merely to qualify somebody for a sticker.

Stickers must represent established information already present in the profile.

Stickers must be BELOW the Biography header, not above

Avoid sticker clutter.

## Life and family events

Check routinely for:

* `{{Died Young}}`
  Use where the profile establishes death in infancy or childhood.

* `{{Stillborn}}`
  Use where the profile establishes that the child was stillborn.

* `{{Multiple Births}}`
  Use for twins or other documented multiple births.

* `{{Maternal Death}}`
  Use where the existing profile establishes death due to pregnancy or childbirth.

* `{{Centenarian|age=}}`
  Use where the documented age at death was 100 or more.

These can be especially useful genealogically because they help explain family structure and reduce the risk of later researchers incorrectly merging or reassigning children.

## Origin and migration

* `{{Scotland Sticker}}`
  Use where the profile establishes birth in Scotland.

* `{{Ireland Native}}`
  Use where the profile establishes birth on the island of Ireland, including what is now Northern Ireland.

* `{{Scottish Ancestor Sticker}}`
  Use where appropriate for a diaspora profile with relevant Scottish ancestry.

* `{{Migrating Ancestor}}`
  Use only where the supplied profile establishes that the person personally migrated.

Examples:

`{{Migrating Ancestor|origin=Scotland|destination=Ireland}}`

`{{Migrating Ancestor|origin=Ireland|destination=Canada}}`

Do not add a migration sticker merely because:

* their parents migrated;
* their children migrated;
* associates migrated;
* a migration is only a research theory.

## Occupation and religion

* `{{Occupation}}`
  Use where an occupation is explicitly documented and important enough to highlight.

* `{{Religion}}`
  Use where religious affiliation is explicitly established and materially relevant.

* `{{Quakers Sticker}}`
  Use where the person is explicitly documented as a Quaker and the specific sticker is appropriate.

Do not infer occupation or religion.

## Military and special circumstances

Where the supplied profile already establishes relevant service or status, consider known appropriate stickers such as:

* `{{Veteran Recognition}}`
* `{{Roll of Honor}}`
* `{{The Great War}}`
* `{{World War II}}`
* `{{Australian Convicts}}`

Do not guess unfamiliar parameters.

If exact syntax is not already known from this prompt or the supplied profile, omit the sticker rather than performing new wider research.

## Sticker evidence rule

Do not add any sticker for:

* candidate identity;
* speculative birthplace;
* uncertain migration;
* inferred occupation;
* assumed religion;
* uncertain military service;
* unproved cause of death;
* a relationship that exists only because the current WikiTree tree says so.

Do not automatically add `{{Notables Sticker}}`.

# 21. Genuine notable profiles

If the supplied profile is clearly a genuine WikiTree notable, make the reason for notability obvious near the beginning.

Do not write several paragraphs before explaining why the person is notable.

A concise lead works better.

If an existing current Notability template is already present and appropriate, preserve it.

Do not automatically insert `{{Notables Sticker}}`.

Do not decide during this cleanup task that an ordinary person should become a notable.

# 22. Historical prose

Retain historical context only where it directly explains the person's biography.

Shorten generic history.

For example, if a person was a Covenanter prisoner, retain enough context to explain:

* why they were imprisoned;
* why they were transported;
* what happened to the ship.

Do not turn the profile into a general essay about the Covenanters.

Likewise, if a person migrated during:

* the Plantation of Ulster;
* industrial expansion;
* famine;
* wartime evacuation;
* convict transportation;

retain only the context directly useful for understanding that person's records.

# 23. Visual hierarchy

Aim for a profile that can be scanned quickly.

A good profile should make it easy to identify:

1. who the person was;
2. their immediate family;
3. their major life events;
4. structured evidence;
5. unresolved problems;
6. sources.

Use:

* concise headings;
* tables;
* occasional bold emphasis;
* short blockquotes;
* useful stickers;
* Research Note Boxes;
* contextual images;
* compact timelines;

where these genuinely improve comprehension.

Do not combine all of them merely because they are available.

Every visual element should answer one of these questions:

* Does this explain the person's life?
* Does this explain the evidence?
* Does this help distinguish people?
* Does this prevent a likely genealogical mistake?
* Does this make structured information easier to scan?

If not, omit it.

# 24. Tone and wording

Use concise genealogical prose.

Avoid:

* filler;
* repeated caveats;
* over-formal academic language;
* dramatic storytelling unsupported by sources;
* speculative statements presented as facts;
* long introductions before the actual biographical facts.

Prefer:

`'''Possible same person; unproved.'''`

over a paragraph that says essentially the same thing.

Prefer:

`No relationship is stated in the record.`

over:

`It is important to bear in mind that the source unfortunately does not appear to provide definitive evidence demonstrating a familial connection.`

Do not make the prose artificially grand because the person is historically interesting.

# 25. Do not alter genealogical conclusions without reason

This is a cleanup task.

If the existing profile concludes:

`These two people may be the same person, but the identification is unproved.`

retain that conclusion unless the supplied text itself contains an obvious internal contradiction that can be fixed editorially.

Do not decide that two profiles should be merged.

Do not sever relationships.

Do not add new parents, spouses or children.

Do not reinterpret a record beyond what the supplied profile already says.

# 26. Correct obvious structural problems

You may safely fix:

* duplicate sections;
* repeated sentences;
* broken headings;
* inconsistent apostrophes;
* malformed WikiTree links;
* malformed `<ref>` reuse;
* broken WikiTree table markup;
* bullet lists incorrectly using `#`;
* excessive blank lines;
* inconsistent date formatting;
* unnecessarily verbose source descriptions;
* prose that would be clearer as a table;
* plain names that can confidently be converted to internal WikiTree links;
* badly positioned existing images;
* redundant visual elements;
* repeated source descriptions;
* oversized quotations that can safely be shortened without losing genealogical information.

Do not silently "correct" historical spellings inside quoted or transcribed records.

# 27. Preferred finished structure

Do not force every profile into exactly the same shape, but a strong finished profile may look like:

```text
{{Useful Sticker}}

{{Research Note Box if genuinely warranted}}

== Biography ==

Concise opening summary.

=== Family ===

Narrative or family table.

=== Migration ===

Concise migration account if relevant.

=== Occupation ===

Only if useful.

=== Major Historical Event ===

Only if directly relevant.

=== Records relevant to identity ===

Candidate/evidence table if needed.

=== Timeline ===

Compact chronology table only if genuinely useful.

== Research Notes ==

Concise unresolved issues.

=== Priority Research ===

* Task
** Detail

== Sources ==

<references />
```

Do not create empty headings.

Do not create a subsection merely because it appears in this example.

# 28. Output requirements — STRICT

The final response must contain:

1. optionally, one very short paragraph stating what was tidied or structurally changed;
2. the **ENTIRE cleaned WikiTree profile inside exactly ONE fenced code block**.

This is mandatory.

Do not send any part of the finished profile as rendered Markdown.

Do not split the profile across several code blocks.

The code block must begin before the first line of the WikiTree profile and end only after the final line.

For example:

```text
{{Scotland Sticker}}

== Biography ==

Biography...

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

* Issue still unresolved.
* Another issue.

== Sources ==

<references />
```

The finished profile must:

* be ready to paste directly into WikiTree;
* contain valid WikiTree / MediaWiki syntax;
* use internal WikiTree links where identities can be confidently resolved;
* contain no `glasgow.phenotype.dev` citations or URLs;
* contain no Markdown tables;
* use `*` and `**` for bullet lists, not `#`;
* avoid repetitive prose;
* consolidate overlapping sections;
* use tables where they materially improve clarity;
* preserve useful existing evidence and source URLs;
* avoid introducing new research conclusions;
* use only evidence already contained in the supplied profile;
* use visual elements only where useful;
* finish with:

`== Sources ==`

`<references />`

# 29. Final self-check

Before answering, verify:

## Research boundary

* Did I avoid wider genealogical research?
* Did I use the Glasgow catalogue only to resolve existing person mentions and WikiTree IDs?
* Did I avoid adding new relationships or biographical claims from the catalogue?

## Interlinking

* Have identifiable people been interlinked where possible?
* Are all WikiTree IDs confidently resolved rather than guessed?
* Did I preserve correct existing internal links?

## Structure

* Have duplicate sections been combined?
* Are second-level headings limited appropriately?
* Has repetitive prose been removed without losing information?
* Could any remaining repetitive material work better as a table?
* Have I avoided unnecessary tiny subsections?

## Tables

* Are all tables valid MediaWiki syntax?
* Does every table begin with `{|`?
* Does every table end with `|}`?
* Are rows separated with `|-`?
* Are there any Markdown tables? If yes, replace them.

## Research Notes

* Are existing uncertainties still clearly expressed?
* Are Research Notes focused on unresolved genealogy rather than repeating Biography?
* Would a Research Note Box materially help with a major existing dispute?
* Have I avoided inventing a dispute or unfamiliar box?

## Sources

* Have I preserved useful citations and URLs?
* Have repeated `<ref>` definitions been consolidated where safe?
* Have I avoided inventing source details?
* Is any long quotation unnecessarily bloating the biography?
* Are all external links using `[https://example.com Label]` WikiTree syntax?
* Is there any Markdown external-link syntax such as `[Label](https://example.com)` remaining? If yes, convert it.

## Stickers

* Have I checked obvious useful life-event stickers such as:
  * Died Young;
  * Stillborn;
  * Multiple Births;
  * Maternal Death?
* Have I considered birthplace, migration, occupation, religion and military stickers where already supported?
* Have I avoided unsupported or decorative stickers?
* Have I avoided automatically adding `{{Notables Sticker}}`?

## Presentation

* Would an existing image, map or document image improve the relevant section?
* Have I positioned existing visuals sensibly?
* Would a short blockquote communicate an important source better?
* Would a compact timeline genuinely help?
* Is every visual element doing useful work rather than decorating the page?
* Have I preserved useful existing categories?
* Have I avoided decorative clutter?

## Syntax

* Are bullets written with `*` and `**`, never `#`?
* Have all `glasgow.phenotype.dev` references been removed from the finished profile?
* Is the entire finished profile contained inside exactly ONE code block?
* Is any profile text outside that code block? If yes, fix it.
* Does the profile finish with `== Sources ==` and `<references />`?

The goal is a profile that is **cleaner, shorter, easier to scan and harder to misinterpret**, without changing the underlying genealogy.
