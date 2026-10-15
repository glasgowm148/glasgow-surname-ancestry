# Glasgow ancestry programme

The research goal is to connect the oldest Glasgow branches into one extended
family, including explicitly graded working connections. The reported shared
Y-DNA origin guides the search; missing generations remain research questions.
Start with the earliest surviving records. Post-1850 work is secondary unless
it resolves an earlier branch connection.

The maintained goal, surname variants and specific early tests are in
`research/ancestry-connections/strategy.json`. The project research skill carries
this priority. `/onetree/progress/` presents the measurements, oldest family
heads, common-origin working model and specific connection investigations.

## Recompute

Run `make build-ancestry-progress` after synchronizing a connection batch's
public dossiers. The normal local rebuild includes this step after person-page
and shared-shell generation. The standalone build refreshes its own page,
downloads and Whole tree toolbar link; it does not deploy or alter WikiTree.

The inputs are the public surname index and resolved public person dossiers.
Raw export father fields are unsuitable: they can conflict with reviewed
relationship assertions. Alias IDs are consolidated. Only current paternal
links between eligible surname bearers enter the graph; maternal and spouse
links do not join paternal components. Competing fathers are held out rather
than joining mutually exclusive pedigrees. Cyclic links are flagged and excluded.

## Measures and cohort

- Separate paternal components, including singletons: lower means fewer gaps.
- Male heads with no included father and at least two surname-bearing children:
  lower means fewer unattached families. The queue also includes a head with one
  child and at least two descendants.
- Largest component as a share of the cohort: higher means greater coverage.
- Connected pairs: `100 × Σ n(n−1) / (N(N−1))`, where `n` is each component's
  size and `N` is the cohort size. A component join of sizes `a` and `b` connects
  `a × b` previously disconnected unordered pairs.

Each cutoff uses people dated by that year through a resolved birth, death or
explicit evidence date, plus eligible surname fathers reached by ancestry.
Estimated dates remain labelled. Lower-bound “after” dates cannot establish
eligibility. A known later birth blocks ancestor closure; a later death alone
does not. Unrelated undated subjects remain outside dated cohorts. Missing
documentary subjects, unavailable dossiers, ambiguity and dates are reported.

The working pedigree includes uncertain and unassessed current links. The
confidently marked view uses a restricted grade set over the **same cohort**.
These are public-model grades, not a claim that every underlying record has
received a new source audit. A conceptual shared-origin line counts as no
genealogical connection. Do not fabricate a parent to improve the score.

## Baseline and history

`baseline-2026-10-15.json` preserves the initial cohort IDs, metrics, method
version and input fingerprint. The builder creates it only with the initial
`--create-baseline` flag and never replaces it. `progress-history.json` adds a
snapshot only when the relevant public node/edge fingerprint changes.

Current totals and a comparison restricted to surviving baseline people are
both published. New and missing people are reported separately, so catalogue
growth cannot masquerade as a connection improvement. A changed denominator
must be considered when interpreting percentages. Method changes require an
explicitly documented new baseline rather than overwriting the old one.

The early comparison queue can include historical subjects represented by
full sourced study accounts rather than person dossiers. Such subjects remain
outside the numerical cohort until they have a public person model. No new
kinship discovery is claimed merely by adding an existing hypothesis here.
