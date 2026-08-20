# Glasgow surname reconstruction

Start here for surname-wide research. The working goal is to group every known
Glasgow family and occurrence, infer the smallest defensible connections between
clusters, and then seek records capable of proving or rejecting each connection.

Shared Y-DNA supports a project-wide hypothesis that the documentary Glasgow
paternal lines descend from a common male ancestor around 1500. It does not, by
itself, distinguish a father from an uncle, brother, cousin, or more distant
collateral. Every structural relationship still needs documentary or suitably
specific genetic evidence.

## Navigation

| Resource | Use |
| --- | --- |
| [Early profiles](indexes/early-profiles.md) | Generated index of profiles dated through 1700; the 1500s are isolated as the highest-priority bridge period. |
| [Early Irish profiles](indexes/early-irish-profiles.md) | Generated Irish cohort through 1799, grouped by century and recorded county with father-assessment counts. |
| [Researched profiles](indexes/researched-profiles.md) | Generated links from each active case to its findings, WikiTree queue, brief, and captured relatives. |
| [Relationship hypotheses](indexes/relationship-hypotheses.md) | Manual register of proposed edges, alternatives, confidence, and the next record needed. |
| [Location/family clusters](clusters/README.md) | Canonical human dashboard of significant conclusions and WikiTree transfer status. |
| [Pre-1700 evidence](pre-1700/evidence-register.md) | Occurrence-level early records, duplicate audits, exclusions, and unresolved identities. |
| [New profiles](new-people/) | Unresolved Glasgow profile drafts, named `year_country_preciselocation_name.md`; completed drafts move to `research/<WikiTree-ID>/`. |
| [Surname workbook](../data/reference/glasgow-one-tree.xlsx) | Current search snapshot of the broader WikiTree population; useful for discovery, never proof. |

## Information model

- **Occurrence:** one name in one record, retained even before it can be assigned.
- **Person:** a deduplicated individual supported by one or more occurrences.
- **Household:** co-residents explicitly stated by a source.
- **Cluster:** people grouped by place, associates, occupation, chronology, or
  migration for research; cluster membership is not kinship proof.
- **Relationship hypothesis:** a proposed edge with competing topologies and a
  stated proof target.
- **Proved relationship:** an edge supported by a direct record or a documented,
  conflict-free proof argument.

## Research cycle

1. Search the workbook and generated indexes before creating or merging a person.
2. Capture every Glasgow and relevant associate found in a source, not just the
   person who prompted the search.
3. Assign occurrences to a person only when the identity evidence is sufficient.
4. Group people geographically and chronologically; record all plausible
   topologies rather than forcing a single tree.
5. Prioritise testaments, wills, retours, sasines, rentals, deeds, court records,
   burgess records, kirk-session material, and migration records that name kin.
6. Update the individual case, cluster dashboard, early register when applicable,
   and relationship-hypothesis register.
7. Regenerate the machine-derived navigation:

```bash
.venv/bin/python src/surname_research_index.py
```

The exporter performs step 7 automatically after a case under `research/` is
rebuilt.
