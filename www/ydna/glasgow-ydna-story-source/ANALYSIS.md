> Earlier-edition analysis retained for continuity. For the delivered narrative edition, see NARRATIVE_NOTES.md, data-integrity-report.json and story-test-report.json.

# Analytical revision notes

## Basis and boundaries

The kit-level analysis uses the supplied 982-line Y-DNA page. Sections 1–6 refer to lines in `reference/original-upload.html`. The Origins extension also uses the 2,153-line timeline supplied afterwards, preserved as `reference/supplied-timeline.html`; section 7 refers to that file. These are claims in supplied research pages, not independently inspected underlying sequence files or documentary records.

New work consists of the matrix consistency audit, analytical corrections, and a source-labelled historical synthesis. External primary/custodian documentation supports methods and selected historical settings; it does not supply new genetic results or prove the proposed medieval pedigree.

## 1. Counts, identities and measurement labels

The original static header says nine reported roots, but its data array contains eight root groups (lines 333–337 and 863–872). The rebuilt counts derive from the data. Seventeen Y-111 reference matches, nine Big Y reference matches, and seven core FT20271-side Big Y kits including the reference are different populations, not competing totals.

The Henry root combines an unnumbered FT25406 Big Y result with numbered Y-111 kit 325862 (lines 393–400). They are now separate selectable tests. A reported pedigree is not a licence to impute one tester's SNP result to another.

All 64 available stored pair distances are retained, including the 325862–B835762 value explicitly present in the source's placement table but absent from its original comparison object. Missing pairs remain “Not supplied”. They are not zero and are not inherently genetically incomparable. The additional unnumbered William-root mention remains an identity-reconciliation issue rather than a silently assigned test.

Standard-panel allele-step distance, extended Big Y STR mismatches, directional variant-state differences, and model-adjusted distance are shown separately. A “3 / 650” extended comparison is not the same measurement as three allele steps on Y-111. Swapping the two comparison selections now swaps the directional counts and their labels.

## 2. Eight minimum-spanning trees, not one unique lineage

**New computation from the matrix at source lines 560–569.** The complete seven-kit graph has 21 undirected pair distances. All triangle inequalities pass. Exhaustive enumeration gives **eight labelled minimum-spanning trees**, each with total edge weight **15**.

All eight contain these three edges:

- B696189–B580327: 5.
- B580327–1002232: 3.
- 200475–999763: 0.

The alternatives arise in attaching 1002232, 959947 and 478604 to either of the two identical Y-111 endpoint profiles, 200475 and 999763. Each attachment offers a tied choice, giving 2 × 2 × 2 = 8 labelled trees. These are not eight biologically established genealogies. Collapsing identical haplotypes would change the graph and its count.

The network view therefore lets the reader inspect all alternatives and states that its vertices are modern tested profiles, its edges are similarity links, and its positions are not dates. The reconstructed Robert-family pedigree is shown separately.

## 3. The endpoint matrix is not exactly tree-additive

**New mathematical check.** For an exact non-negative additive tree metric, the largest two of the three pair-sums for any four vertices must agree. The supplied matrix fails this four-point condition in **four of 35 quartets**.

For W = B696189, A = B580327, J = 1002232 and R = 200475:

```
d(W,A) + d(J,R) = 5 + 5 = 10
d(W,J) + d(A,R) = 6 + 6 = 12
d(W,R) + d(A,J) = 7 + 3 = 10
```

The largest two sums are 12 and 10. Consequently, no single exact additive tree reproduces every supplied endpoint distance. All four failing quartets involve W, A, J and one of the closely related Robert-family kits; these are not four independent biological observations.

This does not refute a paternal genealogy. Observed STR endpoint distances can lose information about mutation paths. Nor does this calculation prove SAPP's selected ancestral DYS576 state or identify a specific recurrence. It shows why a shortest network should not be presented as a uniquely recovered historical tree.

## 4. FT6135: the inheritance test is incomplete

The original page correctly defines “not displayed” as distinct from ancestral, but elsewhere says FT6135 fails the three-son inheritance test (lines 502–515 and 734). The two claims do not follow from the same evidence.

The supplied states are: derived displayed in 959947 and 200475; no displayed result in the two James M. descendants. Those omissions remain **unknown**. A positive/reference/no-call evidence table and scenario selector replace the premature negative inference.

Derived calls in both James M. kits would support inheritance at or above Robert under the reported pedigrees and a simple mutation model. Reliable reference calls in both would contradict a simple single-origin/no-reversion account across all three branches—but would not logically exclude Robert carrying the derived state followed by reversion on the James branch. Mixed or inadequate calls require further review.

The exact placement of FTE32242 on the Robert-to-James M. edge is similarly distinguished from the directly reported modern positives. Two positive son-lines support James M. as a carrier, conditional on correct pedigrees and calls; exact edge localisation also needs reliable collateral non-carrier evidence. “Basal assignment” is not substituted for a fully audited set of negative genotypes.

## 5. SAPP is another analysis of the same data

The source says the SAPP run had no SNP or genealogy constraints (lines 604–609). Its recovery of DYS714=27 and the Robert-family motif is useful processing consistency, but not an independent genetic replication. The wording now makes that dependency explicit.

SAPP's documentation describes 67% date ranges, 28-year generations and rounding to 50 years. Those ranges are separated from the source's stated 95% SNP timeline intervals. The supplied model scores are not converted into probabilities of a historical pedigree.

The c.1850 Robert-family node conflicts with the reported 1749-born ancestor; zero-generation nodes among identical STR profiles cannot establish their historical order. These are model limitations to inspect, not evidence that the documented ancestor lived at the model's date.

A further source conflict is exposed: the marker narrative attributes DYS511=11 to B696189 (line 584), while the SAPP diagram labels DYS451 10→11 (line 662). The disputed marker is not silently reconciled or used to reconstruct a supposedly complete profile.

## 6. Raw-file, YFull and documentary claims remain attributed

The uploaded page describes several VCF calls and a BED coverage check; those files were not attached. The revision labels them source-reported rather than claiming a new raw-data verification. A position lying in a quality BED interval is not, by itself, a reference genotype. The unspecified genome assembly remains unspecified.

The C→G call at 26534797 is kept distinct from the named C→A FT124483 mutation. Rounded Block Tree private-variant averages are not treated as independent validation of exact per-kit counts.

The YFull section remains a dated account of the source's August 2026 review. Another interpretation of the same sample can audit a calling/tree pipeline; it is not another sampled paternal line. Public tree placements were not refreshed or silently substituted for the supplied snapshot.

The original estate-based exclusion of a proposed father and census-based pedigree bridges are retained as reported research claims, not newly proved documentary findings. Next-evidence priorities now change with the research goal, with the source's original ranking retained for comparison.

## 7. Historical context restored: FT4811 and the FTA30932 collateral line

The additional timeline makes the deeper relationship explicit. Its FT4811 section (lines 1562–1580) places FTA30932 (Churnside/Brown) beside the FT32941 path (Duffield and the Glasgow descendants). The previous explorer said the joining node was not supplied. That is superseded by the new source; the app now uses **FT4811** in the branch map, pair comparison logic, match interpretation and historical view.

The main Glasgow path is FT4811 → FT32941 / FTA35069 → FT25406 → FT20271. It does **not** pass through FTA30932. A reported basal Wright branch is retained separately. The additional FTC49014 node is put between S14827 and FT4811 as described in the timeline (1668–1674), rather than following the file’s out-of-order visual placement. This remains a source-reported connection rather than a fresh live-tree verification.

### The arrival model

The timeline explicitly proposes Norman divergence around 1066–1150 (1589–1645). That is now presented as the project’s leading arrival hypothesis, rather than discarded because the exact migrant is unnamed. Its rationale combines the reported FT4811 common-ancestor age, the later paternal-root geography and a plausible Anglo-Norman setting.

FT4811’s reported TMRCA is 1044 CE with a 697–1313 interval (1565–1569). These are **common-ancestor estimates**, not a crossing date. The 1066–1150 working historical window is drawn separately and never called a genetic confidence interval. The FTDNA Time Tree documentation explicitly dates ancestors/branching and describes the origin flags as self-reported paternal origins. A split around 379 CE does not exclude a descendant migrating around 900 or 1066.

The explorer keeps earlier Anglo-Saxon-period arrival, Norse-era migration and longer British residence as alternatives. It does not pretend to have calculated posterior odds. The central narrative is the project’s preferred model, not a claim that genetics alone distinguishes it from earlier settlement.

### Geographic and named-person distinctions

The Churnside match screen names Jamaica. The timeline adds a Berwickshire ancestry lead and a profile for Alexander Churnside. Both are shown, with their different evidential roles. Brown’s Virginia/Kentucky root is not converted into a proven Border pedigree. A nineteenth-century London Wright anchor is not used as an eleventh-century birthplace.

The timeline’s Roger de Duffeld, John of Huntingdon, John/Adam/Andrew de Glasgu and John Glasgow alias Smith are retained as specific documentary targets (1744–1786 and 1863–1871). Their proposed roles in the genetic story are stated explicitly. The app neither deletes these useful hypotheses nor presents them as an established father-to-son chain.

The official Derbyshire monument record independently supports a de Ferrers castle setting around 1080. The Edinburgh council source supplies twelfth-century burgh context. Neither establishes the genotype, occupation or parentage of the proposed family.

### Date and causal claims needing care

The supplied FT32941 row repeats FT4811’s exact 1044 / 697–1313 estimate (1710–1715). This is preserved and labelled, not treated as an independently calibrated simultaneous event. FTA30932’s c.1120 label has no supplied confidence range; it is drawn as a date-only marker. FTC49014’s approximate 500 CE date is treated similarly.

FT25406’s common ancestor need not be the first person to use the surname. FT20271’s 1583 estimate does not date a particular Plantation migration. FTE32242’s placement remains conditioned on the modern son-line pedigrees; the timeline’s rough 1850 label is not used to override that existing analysis.

Continental Saxon settlement in Normandy, Ferrers/Vipont retinues, catastrophe explanations for a long thin branch and the “Iron Guild” are retained in an explicit hypothesis section. They are not promoted into events demonstrated by the DNA. The source’s contradictory statements about ancient DNA and IN21748 (1388–1394) are noted rather than silently reconciled.

### Actionable tests without a medieval skeleton

The added research goal prioritises (1) independently sourced collateral pedigrees/geography, (2) a current full FT4811/FTC49014 tree and age refresh, (3) dated charter/property/witness relationships in the Derbyshire–Glasgow bridge, and (4) well-resolved basal cousin sampling. A specific medieval migrant or suitable ancient sample would be informative but is not required to improve the model.

## Method references

- FTDNA, *Understanding Y-DNA Genetic Distance*: https://help.familytreedna.com/hc/en-us/articles/6019925167631-Understanding-Y-DNA-Genetic-Distance
- FTDNA, *Big Y Block Tree Guide*: https://help.familytreedna.com/hc/en-us/articles/4402392809359-Big-Y-Block-Tree-Guide
- FTDNA, *Big Y Matching — Matches Guide*: https://help.familytreedna.com/hc/en-us/articles/4402696079887-Big-Y-Matching-Matches-Guide
- SAPP, *Outputs*: https://www.jdvsite.com/outputs/
- SAPP, *FAQ*: https://www.jdvsite.com/faq/
- Azimi et al., *The maximum four point condition matrix of a tree*: https://arxiv.org/abs/2308.08237

The page's Sources & audit view contains the fuller source manifest. `verify_matrix.py` reproduces the new numerical audit without third-party dependencies.

## Additional origins sources

- Supplied project timeline, preserved locally as `reference/supplied-timeline.html`; public counterpart: https://glasgow.phenotype.dev/timeline
- FTDNA, *Understanding the Discover Time Tree*: https://help.familytreedna.com/hc/en-us/articles/6463909777295-Understanding-the-Y-DNA-Discover-Time-Tree
- Derbyshire Historic Environment Record, *Duffield Castle, MDR4704*: https://her.derbyshire.gov.uk/Monument/MDR4704
- City of Edinburgh Council, *Edinburgh 900 / early royal burghs*: https://www.edinburgh.gov.uk/900

Specific live Discover clade pages were not retrievable during this revision. No claim of fresh verification is made for the project’s node dates, medieval-person identifications or private account assignments.
