# Evidence and confidence labels

One public vocabulary covers every surface. Internal keys (`proved`,
`strongly_supported`, study tones, `source_quality` values and so on) are
unchanged; only the words readers see are standardised.

- Source of truth: `tools/evidence_labels.py`
- JSON mirror: `www/assets/research/evidence-labels.json` (written by
  `tools/evidence_labels.py` and `tools/build_evidence_page.py`)
- Reader guide: `/evidence/` (`www/evidence/index.html`, built by
  `tools/build_evidence_page.py`; shell and `g-nav` rail copied unchanged from
  `/about/`)
- Shared CSS: `www/assets/research/evidence.css`, linked only from pages that
  use it
- Targeted repair of published pages: `tools/repair_evidence_labels.py`
  (idempotent; `[profile IDs]` limits it to named dossiers)

Rules:

1. A label never claims more than the evidence. "Documented" is used only for
   `proved`, meaning a cited record states the fact.
2. Marks copied from WikiTree start with "Tree-marked" so they are not read as
   this project's assessment. Tree links with no mark are "Unassessed tree link".
3. Text is always shown. Colours and glyphs (✓ ~ ? ! ✕ ↺ ◇ ○) are extra cues
   only. Each label is unique, so readers can distinguish them without colour.
4. When a dossier label is normalised, the curated qualifier is kept (for example
   "Probable; 1892 next-of-kin citation"). The canonical term is prefixed only
   when the text does not already start with it. The recorded state is never
   upgraded.

## Relationship and claim states

"Before" means the label shown before this change. `—` means the state does not
appear on that surface.

| Key | Catalogue results (`relationConfidence`) | Person dossiers | Atlas drawer | Canonical label | Meaning | Why changed |
|---|---|---|---|---|---|---|
| `proved` | Documented (teal dot) | Documented father/son/… (green, ✓) | — | **Documented** | A cited record states it, and the record has been checked as belonging to the person. | Unchanged; now reserved for this key only. |
| `strongly_supported` | Supported (teal dot, same as Documented) | "Strongly identified father/mother/…" (no specific style) | — | **Strongly supported** | Several independent, consistent records point to it; none states it outright. | "Supported" did not show that the evidence was indirect, and "Strongly identified" was a dossier-only variant. Now matches the study scale. |
| `probable` | Probable (gold dot) | Curated text; generic roles fell back to "Possible …" | — | **Probable** | The evidence favours it, but it is not proved. | The dossier fallback called probable links "Possible", understating them inconsistently. The label now follows the state. |
| `possible` | **Uncertain** (gold dot) | Possible …, or curated text such as "Open father hypothesis" | — | **Possible** | Consistent with the evidence so far. A lead, not a conclusion. | The catalogue used the same word as for the `uncertain` tree mark, so the two states could not be told apart. |
| `uncertain` | Uncertain (gold dot) | Curated text such as "Relationship unresolved" (gold, ?) | "uncertain" (raw key) | **Uncertain** | Flagged as uncertain by the research or the tree contributor. Treat it as unresolved. | Prefix added to curated dossier text ("Uncertain · Relationship unresolved"). |
| `disputed` | Disputed (gold dot) | (unstyled) | — | **Disputed** | Records or researchers disagree, and the conflict is not resolved. | Dossier styling added (!). |
| `contradicted` | Contradicted (pale dot) | Fell back to "Possible son" and similar | — | **Contradicted** | The records argue against the link. It is shown only to explain why it was rejected. | **Overstatement fixed:** rejected links were labelled "Possible". Now "Contradicted son link". |
| `superseded` | — | Superseded proposal (red-brown) | — | **Superseded** | An earlier proposal replaced by later research. | Unchanged. |
| `dna_confirmed` | DNA confirmed (teal dot) | — | "DNA-confirmed" (raw) | **Tree-marked DNA confirmed** | The WikiTree contributor marked the link as DNA-confirmed. This project has not checked it. | The old label read like a finding of this project. |
| `confident` | Confident (teal dot) | — | "confident" (raw) | **Tree-marked confident** | The contributor's judgement, not an assessment by this project. | As above. |
| `non_biological` | Non-biological (grey dot) | — | "non-biological" (raw) | **Tree-marked non-biological** | The tree marks an adoptive, step or other non-biological link. | Source made explicit. |
| `unmarked` / `unknown` | Unmarked (grey dot) | "Tree relationship", "Unassessed sibling link" or "Documented child" from curated text | Status hidden | **Unassessed tree link** (dossier: "Unassessed child link", and so on) | Copied from the tree with no certainty mark, and not assessed against records. | "Unmarked" and "Tree relationship" did not say the link was unassessed. The Atlas hid the status completely. A curated "Documented …" label on an unassessed row is now rewritten, so it cannot overstate. |

### Catalogue label map (orchestrator to apply in `tools/catalogue_search.js`)

```js
const labels={proved:'Documented',strongly_supported:'Strongly supported',probable:'Probable',possible:'Possible',disputed:'Disputed',contradicted:'Contradicted',dna_confirmed:'Tree-marked DNA confirmed',confident:'Tree-marked confident',uncertain:'Uncertain',non_biological:'Tree-marked non-biological',unmarked:'Unassessed tree link'};
```

The keys, the `allowed` set, the tree fallback and the documented-tree filter
(`proved`, `strongly_supported`, `dna_confirmed`) do not change. Add a
`/evidence/` link ("Read the full evidence guide") to the end of
`section.catalogue-legend`. The generator `_catalogue_legend_html()` in
`tools/build_research_catalog.py` already emits it.

## Study-page scale (`tools/build_study_pages.py`, `/branches/<study>/`)

| Tone key | Before | Canonical | Style (unchanged) |
|---|---|---|---|
| `proved` | Proved | **Documented** | solid dark green |
| `supported` | Strongly supported | **Strongly supported** | solid light green |
| `hypothesis` | Hypothesis | **Working hypothesis** | dashed orange |
| `unresolved` | Unresolved | **Unresolved** | dotted grey |

"Proved" was the only place this word appeared, and it claimed more than the
dossier term for the same key. "Working hypothesis" makes it clear that the
link is being tested and is not a finding.

## Record quality (`source_quality`)

| Key | Label | Notes |
|---|---|---|
| `original` | Original record | Image or original register inspected |
| `derivative` | Index or transcription | Open to copying errors |
| `secondary` | Secondary source | Its own claims need sources |
| `tree_only` | Tree/profile only | A lead, not evidence |
| `unknown` | Unclassified | Do not assume an original |

`_evidence_badge()` in `build_research_catalog.py` takes its default labels
from this table.

## Catalogue legend ("How to read the evidence")

Before: Documented ("Supported by a cited record"), Probable ("Supported, but
not conclusively proved"), Profile lead, Estimated, and the cluster warning. The
generator now uses the canonical meanings for Documented, Strongly supported,
Probable, Possible and Unassessed tree link, adds Profile lead and Estimated,
keeps the cluster warning (`CLUSTER_NOTE`) and links to `/evidence/`. The
published `www/catalogue*.html` files are owned by the orchestrator and have
not been changed.

## Open research questions

Every published open question shows its status and two fields:
**What would resolve this** and **Record to request or inspect**. If the
maintained research does not state a value, the page shows
**Not yet identified**. No value is guessed.

- `/research/#open-questions`: `QUESTION_ACTIONS` in
  `tools/repair_research_questions.py`, with one entry for each item in
  `QUESTIONS` and `ADDITIONAL_QUESTIONS`
- Dossier "Active research priorities": `_research_html()` in
  `tools/repair_person_hierarchy.py`, using presentation research tasks. The
  status comes from the task status. The two fields come from the task's
  explicit resolution and record text; if that text is missing, the page shows
  "Not yet identified".
