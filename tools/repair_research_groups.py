#!/usr/bin/env python3
"""Curated evidence studies, independent of uncertain exported tree edges."""
from collections import Counter
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
SPACE = 'https://www.wikitree.com/wiki/Space:John_de_Glasgow_alias_Smith_/_John_Glasgow_of_Saltmarket%27'

# Explicit named anchors only: membership never expands through tree relationships.
GROUPS = [
    dict(id='research-saltmarket-succession', label='Saltmarket: the missing generation',
         members=['glasgow-1098', 'glasgow-1093'], years=(1506, 1564),
         place='Saltmarket and Bridgegait, Glasgow',
         description='Follow the same property from the older Saltmarket John to William and his proved son John. The title succession is strong evidence; the first father-son link remains unresolved.',
         question='Was William the son of the older Saltmarket John, and was that John also the man called alias Smith in 1506?',
         conclusion='William and Esbell Brade conveyed property to their son John in 1534. John inherited as William\'s heir in 1564. The older John-to-William succession occupies the same title position, but no inspected record calls William his son. The maintained pre-1500 free-space biography, rather than the stale John c.1475 profile, is the research destination.',
         boundary='A property-succession study with one proved father-son generation, not proof of every descendant attached beneath John c.1475.',
         next='Inspect the full BL/204 instrument and follow the four-shilling annual rent, widow\'s liferent and adjoining owners for an explicit heir or kinship clause.',
         evidence=[('Maintained Saltmarket biography', SPACE), ('William: evidence and family assessment', '/people/glasgow-1098.html')],
         sources=['surname-research/free-space-pages/John_Glasgow_of_Saltmarket.md', 'research/Glasgow-1098/findings.md']),
    dict(id='research-glasgow-fishers', label='The Glasgow fishers',
         members=['glasgow-1096', 'glasgow-3188', 'glasgow-1027', 'glasgow-3062', 'glasgow-1030'], years=(1551, 1619),
         place='Glasgow burgh and the Clyde-side property network',
         description='Robert, Ninian and their family emerge from burgess admissions, property deeds and testaments. John who married Jonet Mathie remains an identity question within this network.',
         question='Was John who married Jonet Mathie the living brother named by Ninian in 1613?',
         conclusion='Ninian\'s 1596 admission calls him Robert the fisher\'s second son. His testament names son Robert, sister Marion and a living brother John. Robert is confidently inferred to be Marion\'s and the record-defined brother John\'s father from the combined evidence. Glasgow-1030 represents that brother; identification with the 1618 Jonet Mathie husband remains probable. Robert the fisher\'s own father William remains probable and uncertain in the tree. John of Hirmenschelis, dead by 1577, cannot be the living brother.',
         boundary='The brother\'s inferred father is confident; continuity into the 1618 marriage household remains a separate identity question. These confidence levels do not extend through every attached generation.',
         next='Find an occupation, inherited property or parent statement carrying Ninian\'s brother into the 1618 marriage and 1619 baptism household.',
         evidence=[('Robert: craft and property evidence', '/people/glasgow-1096.html'), ('John and Jonet Mathie: competing parentage', '/people/glasgow-1030.html'), ('Isobella: the later Bridgegait fisher reference', '/people/glasgow-3916.html')],
         sources=['research/Glasgow-1096/findings.md', 'research/Glasgow-1030/findings.md', 'research/Glasgow-3916/findings.md']),
    dict(id='research-corsankell-household', label='Corsankell: James and his sons',
         members=['glasgow-1168', 'glasgow-3921', 'glasgow-3193'], years=(1559, 1571),
         place='Corsankell / Corsinkell, Stevenston, Ayrshire',
         description='The 1559-60 teind list and 1571 charter define James elder\'s household. Its connection to the Glasgow burgh family still needs a documentary bridge.',
         question='How did the Corsankell household connect to William\'s Glasgow burgh family?',
         conclusion='The 1571 NRS catalogue abstract GD39/5/59 names James elder\'s sons James and John. The record-defined John profile Glasgow-4061 has been merged into Glasgow-3193, the leading Kilwinning identity. The deed itself does not identify the Burrowland/Dalgarven tenant, so that continuity remains probable. William as James elder\'s father is still unproved; Campbell co-occupiers are not established wives or relatives.',
         boundary='A record-defined father-and-sons group. The city connection and the Kilwinning John\'s identity remain qualified despite the live merge.',
         next='Inspect the original 1571 deed and earlier estate succession for a predecessor, relative or link to the Glasgow property family.',
         evidence=[('James elder: household reconstruction', '/people/glasgow-1168.html'), ('1571 Corsinkell charter catalogue', 'https://catalogue.nrscotland.gov.uk/nrsonlinecatalogue/details.aspx?reference=GD39%2F5%2F59')],
         sources=['research/Glasgow-1168/findings.md']),
    dict(id='research-stevenston-estate-network', label='Stevenston: the estate network',
         members=['glasgow-3908', 'glasgow-3911', 'glasgow-1168', 'glasgow-1030'], years=(1549, 1618),
         place='Ardeer Nether, Brakpleuch, Dubbs and Corsankell',
         description='Matthew, Michael and the Corsankell Jameses occur in the same estate landscape. The Mathie and Glencairn connections offer leads into the city family, not a ready-made pedigree.',
         question='Can the Mathie-Glencairn records identify a kinship bridge between the Ayrshire tenants and Glasgow burgesses?',
         conclusion='Matthew at Ardeer Nether and Michael at Brakpleuch are distinct men in the 1559-60 teind list. A Michael in a 1549 Stevenston sasine is a probable match to the later tenant. City Mathy witnesses and later Glencairn households provide a social corridor; none establishes these Glasgows as siblings.',
         boundary='A tenancy and associate network, not a proven family. John-1030 is included for the later Mathie marriage connection only.',
         next='Trace the Glencairn estate and Mathie testamentary families for named Glasgow relatives or a documented holding transfer.',
         evidence=[('Matthew: Mathie-Glencairn research', '/people/glasgow-3908.html'), ('Michael: separate identity and estate records', '/people/glasgow-3911.html')],
         sources=['research/Glasgow-3908/findings.md', 'research/Glasgow-3911/findings.md']),
    dict(id='research-calder-testament-household', label='Calder: Andrew\'s actual household',
         members=['glasgow-3163', 'glasgow-3336', 'glasgow-3183', 'glasgow-3262'], years=(1597, 1624),
         place='Corstoun, parish of Caldercleir, sheriffdom of Edinburgh',
         description='Andrew\'s testament establishes Elizat Stevinsoun and four named children. Isobel and Jonet have qualified later identity joins; a separate 1609 Mid Calder Jonat is a further possible identity for the latter.',
         question='Who were Andrew\'s parents, and can estate, marriage or Menzeis records confirm his daughters\' later identities?',
         conclusion='Andrew\'s 1597/8 testament names wife Elizat Stevinsoun, son Robert and daughters Marion, Janet and Isobel. Isobel is probably the Edinburgh bride of tailor William Symountoun; Jonet is probably the 1624 Mid Calder bride of Martin Ramsy. Both documentary profiles were merged into those later identities on 27 September 2026, Andrew’s father links are confident for the record-defined daughters; their later bride identities remain probable and maternity remains separately uncertain. A different Jonat Glasgow had daughter Agnes Menzeis in Mid Calder in 1609 and could be the same Ramsy bride if her Menzeis marriage had ended; that continuity is still unproved.',
         boundary='The testament household is documented. The later Isobel and Jonet identifications are probable, and the 1609 Menzeis mother is a separate candidate, not an attached daughter. John of Hirmenschelis\'s second named child is Marjory, not an Andrew who could establish this man\'s parentage.',
         next='Follow the land reserved to Elizat until Robert came of age; inspect the 1609 baptism, 1624 marriage, David Menzeis records and Edinburgh craft archives for direct household identifiers.',
         evidence=[('Andrew: corrected testament and identities', '/people/glasgow-3163.html'), ('Isobel: testament and Edinburgh marriage', '/people/glasgow-3336.html'), ('Jonet: Ramsy and Menzeis comparison', '/people/glasgow-3183.html'), ('Jonat Menzeis: 1609 mother', '/people/glasgow-3262.html')],
         sources=['research/Glasgow-3163/findings.md', 'research/Glasgow-3336/findings.md', 'research/Glasgow-3183/findings.md', 'research/Glasgow-3262/findings.md']),
    dict(id='research-edinburgh-craft-marriages', label='Edinburgh and Leith: Glasgow women in craft households',
         members=['glasgow-3188', 'glasgow-3182', 'glasgow-3302', 'glasgow-3598', 'glasgow-3336'], years=(1607, 1620),
         place='Edinburgh and South Leith, Midlothian',
         description='Marriage and baptism entries place several Glasgow women among tailors and cordiners. The shared trades and locality point to research connections, while each woman must be identified from her own records.',
         question='Do craft incorporation, marriage-cautioner or testament records identify the fathers or earlier marriages of Barbara and Margaret Glasgow?',
         conclusion='Margaret Glasgow married cordiner William Hardie in 1611; one Barbara married George Johnstoun, also a cordiner, in 1616; another Barbara has a South Leith entry with John Wilson in 1611. The Edinburgh register also lists a cordiner William Hardie marrying in 1608, 1641 and 1643, but does not establish whether these entries concern Margaret\'s husband or namesakes. Ninian\'s son Robert was a cordiner, making his household a plausible context for the unattached women. Isobel, who married tailor William Symountoun in 1619, is now probably identified with Andrew of Corsoun\'s daughter; that proposed join remains qualified.',
         boundary='A craft and locality network, not proof that the Barbara entries refer to one woman or that Margaret and Barbara are Ninian\'s daughters.',
         next='Read the original 1611 South Leith entries, trace John Wilson after the marriage, and inspect Edinburgh tailoring and cordiner incorporation records for named fathers or cautioners. Compare the Hardie OPR marriages and testaments before treating the later William as Margaret\'s husband.',
         evidence=[('Barbara: South Leith identity comparison', '/people/glasgow-3182.html'), ('Margaret: Hardie marriage', '/people/glasgow-3598.html'), ('Isobel: Corsoun and Edinburgh evidence', '/people/glasgow-3336.html')],
         sources=['research/Glasgow-3182/findings.md', 'research/Glasgow-3302/findings.md', 'research/Glasgow-3598/findings.md', 'research/Glasgow-3336/findings.md']),
    dict(id='research-hirmenschelis-household', label='Hirmenschelis: John\'s testament family',
         members=['glasgow-3181'], years=(1563, 1577),
         place='Hirmenschelis / Hirdmanschiels, Calder district',
         description='John\'s testament names widow Margaret and children Katherine and Marjory. A separate Huchesoun confirmation strip supplied in the same PDF is an open archival and possible family-network lead.',
         question='Was the Hirmenschelis testator the John in the burgh protocols, and can the Huchesoun fragment help identify Margaret?',
         conclusion='Katherine and Marjory are John\'s named children; m[ar]iory follows the accepted human reading. Margaret\'s surname is read by the human contributor as Hochaine, possibly a phonetic Hutchin form, not a confirmed modern family identity. The index confirms Hirmenschelis and 4 May 1577 as the testament date. Andro Huchesoun\'s separate confirmation is only partially transcribed and establishes no Glasgow relationship.',
         boundary='The testament defines a household, not its link to the Glasgow burgh Johns. The associated fragment contains bairnis (children) and provisional Johne Huchesoun, but incomplete grammar prevents assigning their parentage or roles. Marjory is not evidence for an Andrew-3163 connection.',
         next='Ask NRS why strip 396A is linked to CC8/8/5 image 276 and identify its own testament entry. Complete the children clause, then compare people, places and property with John and Margaret without assuming a surname match proves kinship.',
         evidence=[('John: accepted names and associated fragment', '/research/transcriptions/john-1577/#associated-fragment'), ('John: profile and identity evidence', '/people/glasgow-3181.html')],
         sources=['research/Glasgow-3181/findings.md', 'research/transcriptions/associated-fragments/john-1577-hutcheson.json']),
    dict(id='research-kilbirnie-minister', label='Kilbirnie: the minister\'s origins',
         members=['glasgow-1073', 'glasgow-3375'], years=(1674, 1722),
         place='Kilbirnie and Kilwinning, Ayrshire',
         description='Rev. John\'s education and ministry are documented, but his earlier Ayrshire ancestry and a possible second John identity remain unsettled.',
         question='Was Rev. John the Kilwinning John married to Barbara Allison, and were the Georges of Bog and Bay part of his family or separate local households?',
         conclusion='University and Fasti records identify the minister\'s career, but name no parents. A FamilySearch-catalogued handwritten genealogy names George Glasgow of the Bog (Stevenson/Stevenston) and George Glasgow of the Bay (Kelvening/Kilwinning), while asking about their relationship to the minister. The note gives neither George a date or parentage; Glasgow-3120, stated born about 1660 in Kilwinning, is only a possible overlap with the Bay lead. The Corsankell-Stevenston-Kilwinning route remains a hypothesis, and John-3375\'s local household remains a duplicate candidate.',
         boundary='The minister and two possible local Glasgow bearers remain unconnected by proven descent. The retrospective manuscript and its AI transcript do not establish dates or identities; do not equate the Bay George with Glasgow-3120 or attach either George to the minister without contemporary evidence.',
         next='Verify the manuscript readings and chronology from its image, then seek contemporary parish, sasine or probate evidence for Bog/Stevenston and Bay/Kilwinning. Compare Glasgow-3120 only against independent records before changing attachments.',
         evidence=[('Rev. John: career, ancestry and identity problem', '/people/glasgow-1073.html'), ('FamilySearch manuscript: Georges of the Bog and Bay', 'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CSJ9-2YWB?view=fullText&keywords=Glasgow&searchForm=advanced&lang=en')],
         sources=['research/Glasgow-1073/findings.md', 'surname-research/pre-1700/familysearch-full-text-glasgow-scotland-1699-2026-09-22.md']),
    dict(id='research-calder-inveresk-james', label='Two places, one James?',
         members=['glasgow-991'], years=(1605, 1618),
         place='Mid Calder and Inveresk / Musselburgh',
         description='Two baptism sequences name a father James Glasgow. The question is whether they belong to one mobile household or two contemporaries.',
         question='Do the Mid Calder and Inveresk baptisms belong to the same James?',
         conclusion='Mid Calder indexes name father James in 1605, 1610 and 1616; Inveresk/Musselburgh indexes do so in 1609, 1614 and 1618. Andrew\'s testament does not name a son James, so it cannot establish this James\'s parentage. The attached children must not be split or moved on names alone.',
         boundary='An identity study spanning two record sequences, not proof of a single household or of two separate families.',
         next='Compare the original parish entries, occupations, witnesses and testaments for distinguishing family details.',
         evidence=[('James: baptism sequences and parentage correction', '/people/glasgow-991.html')],
         sources=['research/Glasgow-991/findings.md']),
]

# The maintained Early Ireland overview distinguishes locality evidence from
# proposed descent. These small studies retain that distinction in navigation.
IRISH_GROUPS = [
    dict(id='research-irish-cross-derry', label='Cross and Derry: a reconstructed cluster', members=['glasgow-2917', 'glasgow-1732', 'glasgow-1654'], years=(1686, 1844), place='Cross, Killycurragh and Ballynasollus, Derry/Tyrone', description='A Scottish baptism is documented; the later Irish association and attached descent remain reconstructed.', question='Can Irish records bridge Charles Glasgow from the Scottish baptism to the Cross families?', conclusion='The named local subgroups are useful research leads, not a documented chain from Charles.', boundary='A locality and identity study. No displayed father-son link is accepted from the Scottish baptism.', next='Seek Irish parish, lease, probate or land records naming Charles or the first Cross household.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-tamlaght', label="Tamlaght O'Crilly: the Hugh households", members=['glasgow-548', 'glasgow-3931', 'glasgow-540', 'glasgow-591'], years=(1740, 1772), place="Tamlaght O'Crilly and Inishrush, County Londonderry", description='Two 1740 Hugh Glasgow households and a 1772 occurrence are documented; their identities and kinship are unresolved.', question='Which, if any, later Glasgow family belongs to each documented Hugh household?', conclusion='The returns establish household occurrences, not descent from the traditional William or a secure profile identity.', boundary='Contemporary locality evidence with unresolved identities and no proved relationship between the two Hughs.', next='Find lease, church, probate or estate material with age, occupation, household or relatives.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-east-antrim', label='East Antrim: Larne to Kilwaughter', members=['glasgow-1078', 'glasgow-1081', 'glasgow-3913', 'glasgow-1143', 'glasgow-1499', 'glasgow-1504', 'glasgow-1505', 'glasgow-1022'], years=(1653, 1772), place='Larne, Glenarm and Kilwaughter, County Antrim', description='Early adults and households are documented in east Antrim; a complete founding family and links to later branches are not proved.', question='Can the early Larne, Glenarm and Kilwaughter occurrences be connected by a record-defined household?', conclusion='The 20 December 1764 Ballykeel lease, memorial 159661, explicitly names James as Robert’s son, documenting Robert-1143 to James-1144; the continuation to Archibald is supported by concordant records. Archibald’s missing boy fits Tennessee Robert, the possible father of James J. The older Larne ropemaker is separately a candidate for Adam of Inishrush’s father; the joining generations remain hypotheses.', boundary='Documentary locality cluster, not a founding couple or complete descent.', next='Compare NRS GD154/514–515 (c. 1653), /525 (c. 1690), /530 (November 1692) and /532 (1693–1708) tenant and rental originals, and read PRONI T/828/15 for named relatives and date qualifications.', evidence=[('Larne and American family reconstruction', '/people/glasgow-951.html#larne-reconstruction'), ('Larne and Kilwaughter family study', '/branches/larne-kilwaughter/'), ('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-moneymore', label='Moneymore: a labelled tree under review', members=['glasgow-1026', 'glasgow-1492', 'glasgow-2425', 'glasgow-2426'], years=(1671, 1735), place='Moneymore / Derryloran, County Tyrone', description='A Scottish baptism is cited for the earliest profile, but no Irish record yet supports the claimed migration or attached Moneymore descent.', question='Can Irish evidence identify William Walter Glasgow or reconcile the competing attached fathers?', conclusion='The Moneymore-labelled tree remains reconstructed; the stated County Galway locality is inconsistent with the Ulster setting.', boundary='A profile and locality reconciliation study, not a confirmed Irish lineage.', next='Find Irish records for William, spouse and children and resolve the competing father attachments.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-derryloran', label='Derryloran and Cookstown: four 1740 households', members=['glasgow-2988', 'glasgow-2915', 'glasgow-1970'], years=(1740, 1760), place='Derryloran and Cookstown, County Tyrone', description='Two James and two William Glasgow households form a documented 1740 parish cluster beneath later Cookstown research.', question='Can later Cookstown profiles be matched to a specific 1740 householder?', conclusion='The four household occurrences are firm locality evidence; relationships and profile identities remain unknown.', boundary='A documentary parish cluster, not proof of a shared father or Moneymore descent.', next='Follow each householder in church, lease, tax, probate and estate records.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-cork-new-zealand', label='Cork to New Zealand: an independent migration', members=['glasgow-971'], years=(1792, 1873), place='County Cork and New Zealand', description='A later migration family is documented independently of the Ulster clusters.', question='Is there any documentary bridge from this Cork family to an earlier Glasgow branch?', conclusion='No evidence currently joins the Cork–New Zealand family to the Ulster locality clusters.', boundary='A separate migration family; broad surname or Y-DNA affinity does not supply the missing connection.', next='Trace the Barony-to-Cork move and earliest Cork records before testing wider links.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-broughshane', label='Broughshane, Racavan and Clough', members=['glasgow-1657'], years=(1766, 1850), place='Broughshane, Racavan and Clough, County Antrim', description='A record-supported later Antrim household whose connection to other Irish clusters is unresolved.', question='Can the later Broughshane family be placed beside, rather than inside, another Antrim cluster?', conclusion='The household is a valid local study; no relationship to Kilwaughter, Glenleslie or Bann Valley is established.', boundary='A later Antrim family, not an inferred branch of another locality group.', next='Follow original parish, lease and probate records for parents, holdings and collateral kin.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-belfast-donegal', label='Belfast and Donegal: separate documentary occurrences', members=['glasgow-3172', 'glasgow-3556', 'glasgow-3001'], years=(1667, 1728), place='Belfast, Raphoe and Killybegs', description='Belfast maritime, Raphoe deed and Killybegs account records establish separate surname occurrences.', question='Do any contemporary records connect the Belfast and Donegal people to one another or to Antrim?', conclusion='No father-son or collateral relationship has been found; the settings remain separate research clusters.', boundary='Documentary occurrences in distinct places, not a reconstructed Irish founder family.', next='Inspect the Belfast will and maritime records, Raphoe deeds and Killybegs accounts for named associates or kin.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-dublin-watchmakers', label='Dublin Glasco watchmakers', members=['glasgow-1241', 'glasco-143', 'glasco-144', 'glasco-173'], years=(1750, 1783), place='Christchurch Lane and Ormond Quay, Dublin', description='A distinct documented trade cluster links Glasco watchmakers by occupation and address, not yet by stated relationship.', question='Can a primary record connect the Dublin watchmakers and distinguish the competing Thomas profiles?', conclusion='The records support a documentary trade cluster; they do not establish serial marriages or a proved chain to the Scottish baptism.', boundary='A Dublin occupation-and-address study, separate from Ulster until a relationship record appears.', next='Inspect wills, parish registers, guild material and trade records for explicit family language.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-kilclone-meath', label='Kilclone, County Meath: the Glasco memorial family', members=[], years=(1738, 1754), place='Kilclone, County Meath', description='A memorial directly names Patrick Glasco as father of James, Richard and William, while leaving their wider connections open.', question='Can further Meath evidence identify the Kilclone family without merging it into Dublin, Rathdowney or Ulster?', conclusion='The memorial proves a small sibling group and their father; no record connects it to another Glasgow/Glasco cluster.', boundary='A directly stated local family, deliberately kept separate from other Irish branches.', next='Seek estate, tax, probate and later parish material for the named Kilclone household.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-inishrush-collateral', label='Inishrush, Dunaghy and Drumragh collateral leads', members=['glasgow-822', 'glasgow-3902', 'glasgow-1623', 'glasgow-3927'], years=(1767, 1851), place='Inishrush, Dunaghy, Drumragh and Rasharkin', description='Documented family-register, census, tithe and marriage clues identify collateral research leads alongside, not within, Lisnagaver.', question='Can Inishrush, Dunaghy and Drumragh records establish a documented bridge to the later Rasharkin households?', conclusion='James of Larne, born about 1737, could father Adam about 1758; his reported 1762 marriage leaves Adam’s mother unresolved. Older Alexander as Adam’s brother fits better than as Adam and Rose’s son. The older Adam–Maria naming model and earlier local Hugh households remain alternatives.', boundary='Collateral locality research. It does not prove kinship with Lisnagaver, Bann Valley or the Hugh tradition.', next='Trace church, lease and succession records for the named households and distinguish the two Ballybogey Jameses.', evidence=[('Larne and American family reconstruction', '/people/glasgow-951.html#larne-reconstruction'), ('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland'), ('Lisnagaver and Rasharkin family study', '/branches/lisnagaver-rasharkin/')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-bann-valley-killoquin', label='Bann Valley and Killoquin: Daniel and Thomas', members=['glasgow-3904', 'glasgow-3896', 'glasgow-987', 'glasgow-951', 'glasgow-938'], years=(1778, 1871), place='Kilrea, Killoquin, Lisnagaver and Gortereghy', description='Daniel and Thomas Glasgow are proved brothers; the older parent generation and Alexander’s proposed sibling place remain qualified.', question='Can estate and church records resolve the older Alexander-and-Rosanna generation and Alexander’s relationship to Daniel and Thomas?', conclusion='Daniel and Thomas are securely brothers. The Larne reconstruction compares descent through their proposed father older Alexander with a separate younger-James route to Alexander-951. The first preserves the Thomas-parent testimony; neither yet supplies Alexander-951’s father statement.', boundary='A partly proved local family core, not evidence that it descends from East Antrim or another Irish cluster.', next='Inspect Killoquin rent rolls, estate accounts, valuation revisions and the first Lisnagaver leases.', evidence=[('Larne and American family reconstruction', '/people/glasgow-951.html#larne-reconstruction'), ('Lisnagaver and Rasharkin family study', '/branches/lisnagaver-rasharkin/'), ('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
    dict(id='research-irish-desertoghill-garvagh', label='Desertoghill and Garvagh: a 1796 occurrence', members=[], years=(1796, 1796), place='Desertoghill and Garvagh, County Londonderry', description='A 1796 flax-grower entry records John Glasgow at Desertoghill; parentage and descendants are not yet known.', question='Can a church, lease, probate or estate record identify John Glasgow’s household at Desertoghill?', conclusion='The flax list proves a late-eighteenth-century locality occurrence, not a relationship to Tamlaght, Inishrush or another Derry group.', boundary='One documented local occurrence, deliberately kept separate from named family clusters.', next='Trace the Desertoghill and Garvagh tenant, church and probate records for household detail.', evidence=[('Early Ireland branch overview', 'https://www.wikitree.com/wiki/Space:Glasgow_Branches_in_Early_Ireland')], sources=['surname-research/free-space-pages/Glasgow_Branches_In_Early_Ireland.md'], irish=True),
]


def insert_after_page_header(text, content):
    pattern = r'(<main\b[^>]*>(?:(?!</main>|<header\b).)*<header\b[^>]*>.*?</header>)'
    updated, count = re.subn(pattern, lambda match: match[1] + content, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Research page header not found inside main')
    return updated


def father_audit_section(audit):
    """Expose the maintained early Glasgow father audit, including unresolved leads."""
    rows = []
    for item in audit['results']:
        father = item.get('father')
        father_text = (f'<a href="https://www.wikitree.com/wiki/{escape(father)}">{escape(father)}</a>'
                       if father else 'No father attached')
        source = (f'<p><strong>Source evidence:</strong> {escape(item["source_summary"])}</p>'
                  if item.get('source_summary') else '')
        rows.append(f'<details><summary>{escape(item["name"])} · {escape(item["id"])} — '
                    f'{escape(item["outcome"])}</summary><p><strong>Father:</strong> {father_text}</p>'
                    f'<p>{escape(item["assessment"])}</p>{source}'
                    f'<p><strong>Next question:</strong> {escape(item["next_question"])}</p>'
                    f'<p><a href="{escape(item["findings"], quote=True)}">Read the profile evidence</a></p></details>')
    counts = audit['counts']
    followup = ''
    if audit.get('followup_batch'):
        followup = ('<p>The follow-up search located a probable 1582 Bridgegait reference to '
                    '<a href="/people/herbison-475.html">Archibald Herbertsoun, fisher</a>. '
                    'It was added to <a href="/people/glasgow-3916.html">Isobella’s live profile</a> '
                    'and source account. The remaining father arguments still leave an identity '
                    'or family degree unresolved; this batch added no confident father link. '
                    'The original Morton, Torphichen and Ayr sasine succession records remain '
                    'priority archival sources; publicly available indexes do not supply their full text.</p>')
    return (f'<!-- early-father-audit:start --><section class="experience-topic" id="early-father-audit">'
            f'<span class="r-kicker">Father audit · 28 September 2026</span>'
            f'<h2>Early Glasgow profiles: fathers and remaining leads</h2>'
            f'<p>{escape(audit["scope"])}</p><p><strong>{audit["cohort_total"]} profiles:</strong> '
            f'{counts["confident"]} confident father links · {counts["uncertain"]} uncertain · '
            f'{counts["father_missing"]} missing fathers · {counts["unmarked"]} unmarked links.</p>'
            f'<p>{escape(audit["method"])}</p><p>One father relationship was upgraded on live WikiTree; '
            f'no new father was attached. The brother John’s father is confidently inferred from '
            f'Ninian’s <a href="https://archive.org/details/scottishrecordso43scotuoft/page/24/mode/2up">1596 admission</a> '
            f'and <a href="/research/transcriptions/ninian-1613/">1613 testament</a>; his later marriage identity '
            f'remains probable.</p>' + followup + '<details><summary>Review the 31 assessed profiles and next searches</summary>'
            + ''.join(rows) + '</details></section><!-- early-father-audit:end -->')


def repair():
    changed = Counter()
    def write(path, text):
        file = WEB / path
        if not file.exists() or file.read_text() != text:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
            changed['research_groups'] += 1

    registry = {p['slug']: p for p in json.loads((WEB / 'assets/research/registry.json').read_text())}
    records = json.loads((WEB / 'assets/research/record-index.json').read_text())
    branch_path = WEB / 'assets/research/branches.json'
    branches = [b for b in json.loads(branch_path.read_text()) if not b.get('curatedResearch')]
    template = (WEB / 'branches/family-glasgow-1095/index.html').read_text()
    entries = []
    for group in GROUPS + IRISH_GROUPS:
        members = [slug for slug in group['members'] if slug in registry]
        countries = dict(Counter(registry[slug].get('country') or 'other' for slug in members))
        entry = dict(id=group['id'], label=group['label'], description=group['description'],
                     kind='research', curatedResearch=True, root='', rootId='',
                     anchorIds=[registry[slug].get('id', slug) for slug in members],
                     members=members, count=len(members), countries=countries,
                     record_count=sum(r.get('p') in members for r in records),
                     review_count=sum(bool(registry[slug].get('reviewed')) for slug in members),
                     url='/branches/' + group['id'] + '/', topic_ids=['early-ireland' if group.get('irish') else 'scottish-families'],
                     evidence_sources=group['sources'], question=group['question'])
        entry.update({'from': group['years'][0], 'to': group['years'][1]})
        entries.append(entry)
        people = ''.join('<a href="/people/' + escape(slug) + '.html"><span><strong>' +
                         escape(registry[slug]['name']) + '</strong><br><small>' +
                         escape(registry[slug].get('id', slug)) + '</small></span><span>View evidence</span></a>'
                         for slug in members)
        links = ''.join('<li><a href="' + escape(url, quote=True) + '">' + escape(label) + '</a></li>'
                        for label, url in group['evidence'])
        regional_link = '<a href="/branches/#irish-research-studies">Early Ireland research groups</a>' if group.get('irish') else '<a href="/branches/scottish-families/">Scottish families</a><a href="/branches/family-glasgow-1095/#research-studies">Within the John c.1475 tree umbrella</a>'
        content = f'''<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">Evidence-led research group</span><h1>{escape(group['label'])}</h1><p class="r-lead">{escape(group['description'])}</p><p class="r-caption">{escape(group['place'])} &middot; {group['years'][0]}-{group['years'][1]}</p></header>
<nav class="experience-branch-nav" aria-label="Research group navigation"><div class="r-actions"><a href="/branches/#research-studies">All research groups</a>{regional_link}<a href="/research/#open-questions">Open research questions</a></div></nav>
<section class="experience-topic"><span class="r-kicker">The open question</span><h2>{escape(group['question'])}</h2><p>{escape(group['conclusion'])}</p></section>
<div class="r-grid2"><section><h2>People to investigate</h2><p class="r-caption">Named anchors and candidates, not an automatic descendant list.</p><div class="r-linklist">{people}</div></section><section><h2>What connects this group?</h2><p>{escape(group['boundary'])}</p><h3>What would move it forward?</h3><p>{escape(group['next'])}</p><h3>Read the evidence</h3><ul>{links}</ul></section></div></main>'''
        page = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: content, template, count=1, flags=re.S)
        page = re.sub(r'<title>.*?</title>', '<title>' + escape(group['label']) + ' | Glasgow surname archive</title>', page, count=1, flags=re.S)
        page = page.replace('data-g-path="/branches/family-glasgow-1095/index.html"', 'data-g-path="/branches/' + group['id'] + '/index.html"')
        # Curated studies are deliberately smaller than the inherited John c.1475
        # template. Their branch context must remain the named anchors above.
        page = page.replace('data-r-branch="family-glasgow-1095"', 'data-r-branch="' + group['id'] + '"')
        page = page.replace('<strong>John Glasgow · c. 1475</strong>', '<strong>' + escape(group['label']) + '</strong>')
        write('branches/' + group['id'] + '/index.html', page)
    write('assets/research/branches.json', json.dumps(branches + entries, ensure_ascii=False, separators=(',', ':')) + '\n')

    cards = ''.join('<a class="experience-topic" href="' + entry['url'] + '"><span class="r-kicker">Research group</span><h3>' + escape(entry['label']) + '</h3><p>' + escape(entry['question']) + '</p><small>Evidence and unresolved links</small></a>' for entry in entries)
    section = '<!-- curated-research-groups:start --><section id="research-studies"><span class="r-kicker">Beyond the exported tree</span><h2>Research groups within the early Scottish branches</h2><p class="r-lead">The John c.1475 tree contains several documented households joined by uncertain links. Start with the evidence for each group, rather than assuming every attached generation is proved.</p><div class="experience-topic-grid">' + cards + '</div></section><!-- curated-research-groups:end -->'
    irish_cards = ''.join(
        '<a class="experience-topic" href="' + escape(branch['url'], quote=True) +
        '"><span class="r-kicker">Local research study</span><h3>' +
        escape(branch['label']) + '</h3><p>' + escape(branch['description']) +
        '</p><small>People, evidence and unresolved links</small></a>'
        for branch in branches + [entry for entry in entries if entry.get('topic_ids') == ['early-ireland']]
        if branch['id'] in ('lisnagaver-rasharkin', 'larne-kilwaughter') or branch.get('topic_ids') == ['early-ireland']
    )
    irish_section = (
        '<!-- curated-irish-groups:start --><section id="irish-research-studies">'
        '<span class="r-kicker">Households and local records</span>'
        '<h2>Research groups within the early Irish branches</h2>'
        '<div class="experience-topic-grid">' + irish_cards +
        '</div></section><!-- curated-irish-groups:end -->'
    )
    for relative in ('branches/family-glasgow-1095/index.html',):
        text = (WEB / relative).read_text()
        text = re.sub(r'<!-- curated-research-groups:start -->.*?<!-- curated-research-groups:end -->', '', text, flags=re.S)
        text = re.sub(r'<!-- curated-irish-groups:start -->.*?<!-- curated-irish-groups:end -->', '', text, flags=re.S)
        sections = section
        text = insert_after_page_header(text, sections)
        write(relative, text)
    relative = 'branches/scottish-families/index.html'
    text = (WEB / relative).read_text()
    marker = '<!-- curated-scottish-studies -->'
    text = re.sub(r'<!-- curated-scottish-studies --><nav\b[^>]*>.*?</nav>', '', text, flags=re.S)
    navigation = marker + f'<nav class="experience-branch-nav" aria-label="Scottish research studies"><p>Look inside uncertain tree connections</p><div class="r-actions"><a href="/branches/#research-studies">{len(GROUPS)} evidence-led Scottish research groups</a><a href="/research/#open-questions">The main open research questions</a></div></nav>'
    text = insert_after_page_header(text, navigation)
    audit_path = ROOT / 'research/pre-1600-glasgow-father-evidence-audit-2026-09-28.json'
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        text = re.sub(r'<!-- early-father-audit:start -->.*?<!-- early-father-audit:end -->', '', text, flags=re.S)
        text = insert_after_page_header(text, father_audit_section(audit))
        write('assets/research/early-father-audit.json', json.dumps(audit, ensure_ascii=False, separators=(',', ':')) + '\n')
    write(relative, text)
    return changed


if __name__ == '__main__':
    print(dict(repair()))
