# Audit of pre-1700 graph suggestions — 27 July 2026

This audit checks the proposed graph conclusions against the 22 July One-Tree
export, the current public WikiTree profiles and the sources exposed on those
profiles. Graph structure is treated as a finding aid, never as relationship
proof.

## Population and component counts

The stated selection rule reproduces exactly **365 profiles**, comprising
**289 Glasgow/Glasko/Glascoe surname profiles** and **76 connectors**.

The component totals do **not** reproduce under a direct-edge induced graph. If
only parent, child and spouse links whose two endpoints are among the 365
selected profiles are counted, the export gives:

| Measure | Submitted result | Reproduced result |
| --- | ---: | ---: |
| Components | 64 | **66** |
| Singletons | 47 | **49** |
| Dominant component | 258 | **256** |
| Glasgow bearers in dominant component | 206 | **206** |

All named smaller-component sizes reproduce exactly. The difference is two
profiles which the submitted method evidently connected to the core using a
different edge rule, probably through profiles outside the selected set or an
indirect relationship. The `64/47/258` figures should not be published without
the graph code or edge convention; use `66/49/256` for direct relationships
within the selected set.

The five asserted branches beneath Glasgow-1098 reproduce exactly when all
descendants are traversed but only pre-1700 Glasgow surname profiles are
counted: John-1093 **113**, Robert-1096 **45**, Archibald-1097 **34**,
James-1168 **11**, and Isobella-3916 **1**. These are topology counts, not
evidence that the five child attachments are valid. Only John-1093 is directly
proved as William-1098's son in the inspected records.

The statement that there are at least fourteen apparent parent-age conflicts
is plausible but method-dependent. Across the full export, a mechanical rule
of parent younger than 12 or older than 80 at a child's stated birth finds 15.
Several result from estimated or plainly incorrect profile dates and must be
resolved individually rather than treated as biological evidence.

## Proposed split-profile matches

| Pair | Verdict | Audit result |
| --- | --- | --- |
| Glasgow-1376 / Glasgow-2682 | **Reject as proposed** | Glasgow-1376's 1657 citation is Marion Glasgow's baptism with James named as father, not James's birth. Repair Glasgow-1376; do not merge it into the documented James-and-Isobell-Duffe family. |
| Glasgow-3077 / Glasgow-3337 | **Strong lead; hold merge** | The St Cuthbert sequence is coherent: James and Helen Clerk had Agnes in 1658; a James and Annapill/Anabell had children in 1661, 1663 and 1665. One widower is possible, but no death, second marriage or identifying record bridges the fathers. |
| Glasgow-1067 / Glasgow-3109 | **Strong lead; hold merge** | The 1676 Kilwinning baptism securely identifies Hew-1067. A Hugh and Jean Service had a family entry in 1696; Hugh and Mary Dean had a Kilmarnock child in 1699 and later Ayrshire children. A remarriage is feasible, but Jean's death and the marriages are not proved. |
| Glasgow-1054 / Glasgow-3184 | **Already resolved** | Glasgow-3184 now redirects to Glasgow-1054. No further merge action is required. |
| Glasgow-1084 / Glasgow-3015 | **Do not merge yet** | Glasgow-3015 is the Duddingston father of a child in 1638 with Helen Patoune. Glasgow-1084 is a 1616 Mid Calder child later associated with Issobell Porteous. A first-wife theory is possible, but no record links the two parish households. |

## Duplicate and conflation claims

| Profiles | Verdict | Required treatment |
| --- | --- | --- |
| Glasgow-1314 / Glasgow-3119 | **High-priority identity audit, not an automatic merge** | Glasgow-1314 has a sourced 7 July 1673 event and 1701 marriage to Margaret Aikman. Glasgow-3119 has a sourced 1705 marriage to Janet Graham, but no cited birth; its structured 1673 date conflicts with its biography's 1685. Obtain the original 1673 entry to test whether 7 and 20 July are birth and baptism of one child. The alleged 1703 son of Glasgow-3119 is itself only an inference from later children. |
| Glasgow-3103 / Glasgow-3368 | **Keep as two children pending burial evidence** | The profiles represent separate 1679 and 1680 baptisms to the same parents. Reuse of James normally indicates the elder died, rather than a duplicate index entry. The real unresolved problem is which child, if either, became Jean Dobie's husband and father of Peter in 1699. |
| Glasgow-3908 / Glasgow-3911 | **Confirmed distinct records** | The same 1559-60 teind source separately names Matthew at Ardeer Nether and Michael at Brakpleuch. Similar dates and consecutive profile creation are irrelevant. Do not merge. |
| Glasgow-1167 | **Real conflation; proposed remedy needs refinement** | The 1634 index records Euphame and father Johnne with surname Glasgow, but the Edinburgh sibling cluster and Fasti point toward Rev. John Glassford and Jonet Morriel. The same event is also claimed in Glasgow-1030's biography as a child of John Glasgow and Jonet Mathie. Inspect the original parish image; meanwhile remove the unsupported Mathie statement and unrelated 1850 occurrence, retain `Glasfoord` as an alternate surname, and do not attach the event to both families. |

## Proposed missing mothers

Having one known wife and siblings with a mother is not proof of maternity.
Only one proposed addition currently has an exposed transcription that appears
capable of directly supporting it.

| Proposed link(s) | Verdict | Reason |
| --- | --- | --- |
| Brade-232 → Glasgow-1096, Glasgow-1097 | **Reject** | Protocol 1196 proves Esbell Brade as mother of John-1093 only. Robert and Archibald's parentage remains unproved. |
| Spreull-4 → Glasgow-3163, Glasgow-3181 | **Reject** | Jonet Spreull is directly mother of Stephen-1029. Andrew-3163's testament names no parents, and Glasgow-3181 is already affected by an identity conflation. |
| Rolland-239 → Glasgow-3188, Glasgow-1030 | **Reject** | Margaret Rolland is proved as Robert-1096's spouse, not as mother of either man. Ninian's mother is unnamed; John-1030's placement is reconstructed. |
| Newlands-647 → Glasgow-3026 | **Reject** | The 1551 protocol proves Isobell Newlands as Archibald-1097's spouse but names no children. Isabella-3026's parents are unproved. |
| Stewart-65226 → Glasgow-992 | **Probable/direct lead; verify full entry** | Stewart-65226 cites a High Kirk entry for a lawful son of George Glasgow and Margaret Steuart, with William Howie as witness. This likely belongs to William-992, but the profile transcription omits the child's name and date. Copy the full OPR entry before attaching. |
| Smith-374110 → Glasgow-1495 | **Reject** | Katherine-1495's testament calendar names her husband Thomas Weir but no parents. James-3921 is only an uncertain father candidate, so his wife cannot be inferred as mother. |
| Robertson-33965 → Glasgow-3019 | **Reject** | Bessie Robertson was wife of a John at Montfoid in 1610. Identity with Glasgow-3296 is unproved, and Glasgow-3019's placement beneath him is also unproved. |
| Porteous-912 → Glasgow-3107 | **Reject pending a birth record** | James-3107 is defined by his 1663 marriage and later children; no inspected record proves John-1084 as his father or Issobell Porteous as his mother. |
| Cunningham-22604 → Glasgow-3913 | **Reject** | Existing research explicitly leaves the Kilwaughter John's mother unknown; Jonet is possible only if the proposed full-brother reconstruction is correct. |
| Watt-5185 → Glasgow-3117, Glasgow-3106 | **Plausible but not direct** | James-3107 married Agnes Watt in 1663 and the Gordon child sequence follows, but the exposed baptism indexes name the father only. Use uncertain maternity at most. Glasgow-3117 also cites the wrong 1688 Alison event and needs repair first. |
| Dobie-449 → Glasgow-3102 | **Plausible; inspect original** | Jean Dobie's profile and Peter's profile cite the same 1699 baptism. The exposed citation does not show the parents, and the identity of the 1679/1680 father James is unresolved. |
| Adamson-3318 → Glasgow-1603 | **Reject** | Hugh-1603 and his placement under James-991 derive from an online tree. Christina Adamson's dates are also secondary. The apparent age advantage does not establish maternity. |
| Bie-55 → Glasgow-993 | **Reject** | Christina Bie's profile is a collaborative-tree reconstruction; Agnes's 1618 index names only father James in the exposed citation. Do not choose between two alleged wives from estimated ages. |

## “Probably not connected” claims

| Profiles | Verdict |
| --- | --- |
| Glasgow-3086 / Glasgow-3162 | **Valid separation.** They have distinct 3 June and 9 September 1688 Kilwinning entries and different named parents. |
| Glasgow-2867 / Glasgow-3407 | **No merge, but the submitted reason is invalid.** Glasgow-2867's spouse, children and parents are themselves unsupported; they cannot prove that the captain and Glasgow-3407 were separate. Keep apart because no identity bridge exists. |
| Glasgow-1434 / Glasgow-3018 | **Reclassify as an open identity lead.** Both could fit a Kilwinning-Stevenston-Irvine progression with successive wives, although a 1679 child would have been only about fourteen at the 1693 son's birth. The asserted duplicate-son barrier is not decisive because Glasgow-3018's skipper/bailie and family identifications are themselves reconstructed. Do not merge without burgh or parish continuity. |
| Glasgow-3296 component / core | **Valid hold.** The 1650 testament proves only sister Bessie; no parent or child bridge joins this component to the core. |

## Further suggestions produced by the audit

1. Repair record roles before graph analysis. Glasgow-1376 and Glasgow-3117
   currently use a child's event as if it described the profile person.
2. Inspect the original OPR images for the 1673 Alexander event, the 1634
   Euphame entry and the 1615-era lawful son of George and Margaret Steuart.
   Those three images can settle more than the broad component statistics.
3. Treat Glasgow-3103/3368 as a survival-identification problem, not a duplicate
   problem. Search burial and marriage entries before assigning Jean Dobie.
4. Search Irvine burgh and shipping records for continuity between the
   Kilwinning/Stevenston John-1434 and the later skipper/bailie material now on
   Glasgow-3018.
5. Do not bulk-add mothers. Record-by-record maternity review should begin with
   Stewart-65226/Glasgow-992, then Dobie-449/Glasgow-3102 and the Agnes Watt
   Gordon family.
