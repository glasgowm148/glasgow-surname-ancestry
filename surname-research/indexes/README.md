# Surname index contracts

This directory separates generated navigation from manually assessed topology.

- `profiles.json` is the generated machine-readable identity and cross-case map.
- `researched-profiles.md` is generated from case evidence indexes.
- `early-profiles.md` is generated from the workbook, case indexes, and the
  surname-wide early register. It has counted century and birthplace-area sections,
  plus a location/count/share and father-assessment matrix at the start of each
  century. Its compact person/father links rely on the enclosing area and lead to
  complete case findings.
- `early-irish-profiles.md` applies the same format through 1799 to profiles with
  an Irish birthplace, or an Irish death/residence where birthplace is missing.
  Known non-Irish birthplaces are excluded to avoid duplicating migration entries.
- `father-assessments.json` is the manually curated evidence-status layer used by
  both early-profile indexes; the generator never treats a WikiTree attachment as proof.
- `relationship-hypotheses.md` is manually maintained and must not be overwritten
  by the generator.

Father assessments use `confirmed`, `plausible`, `uncertain`, or `contradicted`.
Every upgrade to `confirmed` or `plausible` needs a concise basis and links to the
saved evidence analysis. Profiles without local parent captures remain `not
assessed`; this does not mean that no father is attached on live WikiTree.

Regenerate the generated files with:

```bash
.venv/bin/python src/surname_research_index.py
```

Generated links are navigation, not evidence. Dates and relationships inherited
from the workbook or WikiTree capture must be checked against original sources.
