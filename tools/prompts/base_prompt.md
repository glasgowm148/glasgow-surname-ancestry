Use **https://glasgow.phenotype.dev/** as the first research layer before broader genealogy searching.

The site is a structured research catalogue, evidence repository, and relationship-resolution layer. It is **not itself the underlying genealogical source**. Use it to understand what is already known, what evidence supports it, and what remains unresolved.

## 1. Resolve the target person first

If a WikiTree ID is known, use it directly.

For example, for `Glasgow-951` retrieve:

`https://glasgow.phenotype.dev/people/glasgow-951.json`

Confirm that the dossier matches the supplied person using several identifying features, such as:

* name
* dates
* locations
* spouse
* parents
* children
* occupation
* biography context

Do not assume an ID is correct if the details conflict.

If no WikiTree ID is known, first use the name resolver:

`https://glasgow.phenotype.dev/data/resolve/<normalised-name>.json`

Example:

`https://glasgow.phenotype.dev/data/resolve/alexander-glasgow.json`

If necessary, also use:

`https://glasgow.phenotype.dev/data/people-index.json`

Compare all plausible candidates using family structure, dates, geography, occupations, migration and distinctive evidence. Never resolve someone from name and approximate year alone.

## 2. Read the person JSON dossier before broad searching

Treat:

`/people/<wikitree-id>.json`

as the primary research representation of the person.

Inspect the complete dossier, especially:

* identity and vital details
* locations and occupations
* parents, spouses, children and siblings
* relationship status
* claims
* evidence
* source quality
* source-independence groups
* open questions
* research leads
* warnings
* source summaries

Establish what is already known before doing new research.

## 3. Inspect the immediate-family evidence network

Retrieve:

`/people/<wikitree-id>.network.json`

Use this to understand immediate family relationships and their evidential status.

Pay particular attention to:

* parents
* spouses
* children
* siblings
* best evidence for each relationship
* whether the relationship is tree-derived or independently supported

If an important relative may have stronger evidence, retrieve that relative's own JSON dossier. A child's marriage, spouse's death record, probate record, etc. may establish facts about the target more clearly than the target's own page.

## 4. Respect the evidence model

Do not treat a relationship appearing in the tree as documentary proof.

Distinguish between:

* current WikiTree relationship
* relationship reconstructed from tree references
* controlled research assessment
* documentary evidence
* proved relationship
* probable relationship
* possible relationship
* disputed relationship
* contradicted relationship
* unknown relationship

Also keep these layers separate:

**Person → Claim → Evidence → Source**

For example:

* Claim: A was B's father.
* Evidence: B's marriage record names A as father.
* Source: the actual marriage registration.

The catalogue describes and organises that evidence. The underlying record is the genealogical source.

## 5. Avoid redundant research

Before searching externally, establish a baseline from the dossier and network.

Do not spend time re-proving facts already supported by adequate documentary evidence unless there is a reason to reopen them, such as:

* tree-only evidence
* same-name ambiguity
* conflicting dates or places
* contradictory records
* weak derivative sourcing
* possible conflation of two people
* a need to locate the original source

Before calling any newly found record a discovery, check the catalogue to see whether the relationship or fact is already known.

## 6. Use open questions and research leads as the research queue

After reading the dossier, inspect:

* `open_questions`
* `research_leads`

Start there rather than with generic web searches.

Prefer specific existing leads — archive references, church registers, valuation books, wills, civil registrations, newspapers, etc. — over vague name searches.

Preserve exact repository, collection and reference details supplied by the catalogue.

## 7. Resolve named relatives and candidates through the catalogue

When another person becomes important to the research:

1. resolve them using the static resolver or `people-index.json`;
2. retrieve their person dossier;
3. inspect their relationship evidence and claims;
4. compare them against the target's network.

Do not assume the first resolver result is correct and do not guess WikiTree IDs.

## 8. Use source independence correctly

If the structured evidence identifies an underlying source group or independence group, respect it.

Several websites or indexes derived from the same original record count as one underlying piece of evidence, not several independent confirmations.

Likewise, repeated online trees are not independent documentary evidence.

## 9. Use the HTML page only when needed

Normally use the JSON dossier first.

Retrieve:

`https://glasgow.phenotype.dev/people/<id>.html`

only when you need material not adequately represented in the structured JSON, such as:

* full biography prose
* legacy Research Notes
* exact citation wording
* long-form reasoning
* raw WikiTree markup
* contextual passages

Do not parse the full HTML page just to answer a question already resolved by the structured dossier.

## 10. Consult the schema when meanings are unclear

Use:

`https://glasgow.phenotype.dev/data/index.html`

and:

`https://glasgow.phenotype.dev/data/schema/person.schema.json`

when you need to interpret fields, evidence statuses or provenance.

Follow the catalogue's documented meanings rather than inventing your own.

## 11. Do not cite the catalogue as genealogical evidence

`glasgow.phenotype.dev` is a discovery, indexing and evidence-management layer.

When using its findings in genealogy work, follow through to and cite the underlying source wherever possible — for example:

* parish or church register
* civil registration
* census
* will or probate record
* valuation or land record
* archive catalogue/item
* newspaper
* published contemporary source

Do not present the Glasgow catalogue itself as proof of the genealogical claim.
