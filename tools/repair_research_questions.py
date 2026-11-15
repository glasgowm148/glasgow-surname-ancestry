#!/usr/bin/env python3
"""Expose the maintained root research questions without rebuilding dossiers."""
from collections import Counter
from html import escape
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import evidence_labels  # noqa: E402

WEB = ROOT / 'www'
# Questions drawn from research/Glasgow-{951,822,591}/findings.md.
QUESTIONS = (
    ('glasgow-951', 'Alexander Glasgow', 'c.1811',
     'What evidence would identify Alexander of Lisnagaver’s mother and further test his assessed father?',
     'Existing assessment, 23 October 2026: John Glasgow, farmer (Glasgow-4090), is Alexander’s confidently assessed father at 90%, inferred from the combined family evidence rather than a direct parent statement for Alexander. John-867’s 1846 marriage names that father; Nancy’s 1892 probate citation and independently identified sibling households support the reconstruction. Maternal identity remains only possible. The held docket does not reproduce the petition, heir schedule or 1894 appraisal contents. The 15 November retrieval receipt records that those papers remain unrecovered, not that they are unavailable. No new parent assessment is made here.'),
    ('glasgow-822', 'John Glasgow', '1767',
     'What evidence would resolve John’s parentage beyond the strongly supported Bible-to-Inishrush identification?',
     'Existing review, 17 October 2026: the Bible John’s identity with the 1831 Inishrush householder (Glasgow-3927) is assessed at 94%. His selected father James Glasgow-1509 remains very uncertain at 18%, through correlated brotherhood and Adam-parentage hypotheses; an older Adam and Maria remain an alternative naming model. The held Bible and 1847 letter have been reviewed and supply no parent clause. The 27 October source hold calls for the exact 1803 probate reference and any surviving estate copy or substitute naming children. These are existing assessments, not new identity or parentage upgrades.'),
    ('glasgow-591', 'William Glasgow', 'c.1656',
     'Which Scottish William became the ancestor remembered in the Tyrone tradition?',
     'The Cavers Covenanter remains a compatible Scottish candidate, but migration, parentage and the William-to-John documentary line are unproved. The original 1725 Cavankilgreen memorial was read on 23 October 2026: it says the Glasgows collectively, with no personal forename to recover. All three held Quothquan testament images, CC14/5/9 images 24–26, were examined on 10 September; the latest full-page reread corrects Alexander Brown and John Neilson as executors and William Neilson of Biggar as cautioner, without a securely read kin clause. Glasgow-3912 was merged into Glasgow-1521; that survivor retains a working identification of the 1648 child with the 1673 testator. Neither this identity nor the testament establishes a Tyrone bridge.'),
)

# Additional main workstreams drawn from the maintained Name Study, Early
# Ireland and Saltmarket studies, under the early ancestry connection programme.
ADDITIONAL_QUESTIONS = (
    ('Donegal: Ramelton & Lifford', 'Archibald’s named eldest son',
     'What distinctive evidence would confirm the probable identification of Archibald’s named son with Thomas of Lifford/Raphoe?',
     'Betham GO MS 225 p.90/viewer image 97 explicitly names Thomas as eldest son of Archibald of Rathmalton. The 17 October 2026 assessment already prefers the Lifford/Raphoe man at 86%, probable. The literal son clause and the adult identity inference are separate conclusions. Held abstract images and Lifford purchase/litigation evidence do not supply a distinctive inherited-estate or family recital. A complete will has not been located in the checked local holdings; the limited will-book index search does not prove its absence or destruction. The live father field remains uncertain.',
     '/branches/research-irish-belfast-donegal/#ramelton'),
    ('Larne, Inishrush & South Carolina', 'Where Alexander’s paternal family joins',
     'Who was the father of John Glasgow, farmer (Alexander’s assessed father), and is the documented Kilwaughter family inside R-FT20271?',
     'Alexander’s existing 90% father assessment identifies the record-defined John Glasgow-4090; it does not establish John’s ancestry or identify the Desertoghill flax grower. John’s own upstream John-4179 hypothesis remains possible at 37%. Separately, the held public-safe SNP matrix leaves the Kilwaughter lines unresolved at FT20271 and its child branches. A verified male-line pedigree and actual SNP evidence are required; STR grouping and ancestor labels do not supply either missing connection.',
     '/people/glasgow-951.html#larne-reconstruction'),
    ('Hirmenschelis & the Huchesoun fragment', "Margaret's surname and the associated testament",
     'What do the unresolved Huchesoun clauses and strip’s archival placement establish about Margaret, if anything?',
     'The supplementary strip 396A, supplied under CC8/8/5 image 276, is held locally in the John 1577 PDF and page-three PNG. The 10 September partial reading identifies Andro Huchesoun’s confirmation and the word bairnis; Johne [Huchesoun?] and the clause grammar remain provisional. No Glasgow surname is securely read in the strip. Margaret’s proposed Hochaine/Hutchin surname and the PDF association are leads, not family proof. Complete the unresolved clauses and seek the strip’s own testament reference and mapping; the source image is not missing.',
     '/research/transcriptions/john-1577/#associated-fragment'),
    ('Ayrshire & St Vincent', 'The Montgreenan trust and family',
     'Which trust and household identities remain unresolved after the existing Montgreenan child identifications?',
     'John Glasgow-2952 and Anne Glasgow-2874 already have documented father assessments. Amelia Wilson-3789 is distinguished from John’s housekeeper Theobalds-120; her held 1867 death index names Robert Glasgow and Roselie Laborde, while identification with the trust’s Emilia remains qualified. Amelia’s existing father assessment retains its recorded confidence qualifications. Trust summaries, appeal findings and index evidence are held; the original trust and death images were not located in the checked case holdings. Maternity and inferred household relationships remain separate questions.',
     '/people/glasgow-1076.html'),
    ('Early Scottish records', 'The early burgh connection',
     'Do the Stirling, alias-Smith and Saltmarket records describe the same John, and how does William fit?',
     'The proposed identities remain possible; the Saltmarket-to-William succession is a separate probable connection. Neither establishes the entire exported early pedigree.',
     '/free-space/john-de-glasgow-alias-smith-john-glasgow-of-saltmarket-7ac174/'),
    ('Glasgow & Ayrshire', 'The burgh-to-Corsankell bridge',
     'What evidence would link the documented Corsankell household to William’s Glasgow burgh family?',
     'The 1571 GD39/5/59 abstract expressly names James elder’s sons James and John. The 12 November 2026 historical-account review supports Katherine Campbell as wife and probable mother, with the manuscript wording still uninspected. These household findings do not prove the upstream burgh connection: William-1098 remains James-1168’s possible father at 38%. The original 1571 deed and TD77/135 or GD103/2/22 material were not located in the checked case holdings; catalogue and historical-account evidence must not be described as original manuscript inspection.',
     '/branches/research-corsankell-household/'),
    ('Kilbirnie & Kilwinning', "The minister's identity and parents",
     'What evidence would connect the Kilwinning household to the documented Kilbirnie minister and identify his parents?',
     'The minister’s 1672 university class, 1674 graduation, 1688 ordination and 1721 death form a documented adult sequence. John-1604 remains the selected uncertain father; Robert-1078 remains an alternative. Identification with John-3375’s Barbara Alason household is unresolved. Addison’s printed p.6, checked on 12 November 2026, names the minister’s student son John and his April 1740 death; it does not identify the minister’s parents or select the 1713 or 1717 child. The held university extract and household evidence need a distinctive parent or identity bridge.',
     '/people/glasgow-1073.html'),
    ('Larne & Kilwaughter', 'The East Antrim bridge',
     'Can the seventeenth-century founder records be connected to the later secure Kilwaughter family?',
     'The 1764 Ballykeel lease expressly names James as Robert’s son, documenting Robert-1143 to James-1144. The bridge from the 1653/1669 bearers and the Scottish origin remain open. Compare NRS GD154/514–515, /525, /530 and /532 tenant originals; read PRONI T/828/15 before treating the Belfast captain’s 1686 will year as his death date.',
     '/branches/larne-kilwaughter/#larne-original-evidence'),
    ('Derryloran & Moneymore', 'Which household became which family?',
     'How do the 1740 and 1766 households map to the later named families?',
     'The records establish local occurrences, not all the inherited parent links. Conflicting attachments and place identifications need resolving; Kildress must not be folded into Derryloran without evidence.',
     '/branches/research-irish-derryloran/'),
    ('Early Scottish records', 'Five Glasgow entries (1601–1677)',
     'Which identities can be established for each of the five 1601–1677 source occurrences?',
     'The five occurrences are Agnes in the 1601 Milneburne sasine index, Margaret in the 1636 Byris of Kilwinning testament index, John in the 1643 Rashie/Kilbride testament index, James in the 1674 Didup inquest extract, and Hugh the preacher in the 1677 deed index. Agnes is probably Glasgow-3178. Margaret-1100’s separately identified 1610 baptism does not identify her with the 1636 testator. Hugh remains compatible with Glasgow-1603, Glasgow-1066 and Glasgow-3109; unsupported ages do not exclude them. Held index and extract readings do not replace the underlying instruments, which were not located in the checked case holdings. These are five occurrences, not necessarily five distinct people or five resolved identities.',
     'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CS3Q-47SZ-P?view=fullText&keywords=GLASGOW&searchForm=advanced&lang=en&groupId=M9QN-ZXH'),
    ('Documentary lines & Y-DNA', 'Where the paternal branches meet',
     'Where does a documented male Kilwaughter line sit among the tested paternal branches?',
     'A documented tester chain can connect the genetic comparison to a particular family. Shared SNPs can locate a branch, but cannot name the missing ancestor.',
     '/ydna/'),
)

# Status, what would resolve each question and the record to request or
# inspect. Every entry restates the maintained research cited above (or the
# person's presentation.json research tasks); an empty value is published as
# "Not yet identified" rather than filled with a guess.
QUESTION_ACTIONS = {
    'Archibald’s named eldest son': ('Open · son-to-Lifford identity already probable',
                    'A distinctive estate, relative or associate linking the named 1673 son to the Lifford adult.',
                    'Held Betham abstract images and limited NAI PRCT/1/1 index captures; full will or decisive PRONI family recital not located in checked local holdings.'),
    'glasgow-951': ('Open · father assessed at 90%; maternity unresolved',
                    'A mother-naming record or estate schedule testing the existing family inference.',
                    'Held Nancy docket and 15 November retrieval receipt; petition, heir schedule and appraisal contents unrecovered, not shown to be unavailable.'),
    'glasgow-822': ('Open · identity assessed at 94%; parents uncertain',
                    'A parent or kin clause distinguishing the selected James hypothesis from the alternative family.',
                    'Held Bible and letter already reviewed; exact 1803 probate locator and any surviving estate copy or substitute naming children.'),
    'glasgow-591': ('Open · Scottish identity unproved',
                    'A migration or father–son bridge; resolve the held testament’s gutter, appointment and account clauses without treating administrative roles as kin.',
                    'Held CC14/5/9 images 24–26, all examined in the latest 10 September reread, research/transcriptions/originals-2026-09-10-reread/william-1673.json. Compare the current Glasgow-1521 account, into which Glasgow-3912 was merged. Trace the neighbouring Glasgow holding in the 1725 Cavankilgreen deed through estate succession; no personal forename is omitted.'),
    'Where Alexander’s paternal family joins': ('Open · upstream pedigree and SNP placement separate',
                    'A named parent bridge above John-4090, separately from a documented male-line pedigree and actual Kilwaughter SNP placement.',
                    'Held John-4090 family evidence and the public-safe SNP matrix; no resolving parent clause or Kilwaughter SNP result in that reviewed evidence.'),
    'Margaret\'s surname and the associated testament': ('Open · source held; clauses partly read',
                    'The complete kin clause and the archive’s explanation of how strip 396A maps to image 276.',
                    'Held testaments/Edinburgh/1577_John/1577_John.pdf, page 3, and 1577_John_p3.png; complete reading and strip identification remain unresolved.'),
    'The Montgreenan trust and family': ('Open · children identified; trust and household details qualified',
                    'The exact Emilia clause, maternal wording and independent household links.',
                    'SC6/44/4 and original 1867 Amelia Wilson death entry, 576/2/47; summaries and index evidence held, original images not located in checked case holdings.'),
    'The early burgh connection': ('Open · proposed identities possible', '', ''),
    'The burgh-to-Corsankell bridge': ('Open · household documented; upstream bridge uncertain',
                    'A property transfer, predecessor or family clause linking the burgh and Corsankell accounts.',
                    'GD39/5/59 and earlier estate succession; official abstract and historical-account evidence held, manuscript originals not located in checked case holdings.'),
    'The minister\'s identity and parents': ('Open · adult ministry documented; household and parents uncertain',
                    'A distinctive identity or parent clause joining the Kilwinning household to the minister.',
                    'Held university extract and parish-family evidence; compare John-3375’s household without treating the student son’s name as a parent statement.'),
    'The East Antrim bridge': ('Open · Robert-1143 to James-1144 documented',
                    '',
                    'NRS GD154/514–515, /525, /530 and /532 tenant originals; PRONI T/828/15.'),
    'Which household became which family?': ('Open', '', ''),
    'Five Glasgow entries (1601–1677)': ('Open · individual source identities remain qualified',
                    'Record-specific spouses, relatives, residences or title recitals distinguishing compatible profiles.',
                    'RS11/1 Agnes sasines; CC9/7/27 Margaret and CC9/7/28 John testaments; 1674 Didup inquest; RD3/42 p.148 Hugh deed. Index/extract evidence held; underlying instruments not located in checked case holdings.'),
    'Where the paternal branches meet': ('Open',
                    'A documented tester chain connecting the genetic comparison to a particular family.', ''),
}


MISSING_CONNECTIONS = {
    'glasgow-951': 'John-4090 is already Alexander’s confidently assessed father at 90%, by inference. Maternal identity and further estate evidence remain unresolved.',
    'glasgow-822': 'The Bible-to-Inishrush identity is strongly supported at 94%; the missing parent clause must test the uncertain ancestry separately.',
    'glasgow-591': 'The Scottish candidate still needs a Tyrone bridge. The held testament was examined across all three images but retains unresolved clauses; Glasgow-1521’s child/testator identity remains working. The collective 1725 Glasgow clause has no personal forename to recover.',
    'Archibald’s named eldest son': 'Thomas is explicitly the testator’s son; his probable identity with the Lifford adult still needs a distinctive bridge.',
    'Where Alexander’s paternal family joins': 'John-4090’s upstream ancestry and the Kilwaughter line’s SNP placement remain independent gaps.',
    "Margaret's surname and the associated testament": 'The source strip is held. Its complete wording and connection to John’s record remain unresolved; neither identifies Margaret yet.',
    'The Montgreenan trust and family': 'Existing child identifications must be retained; the trust’s Emilia wording, maternity and household relationships remain qualified.',
    'The early burgh connection': 'The same-name Johns may be different men. Their identities and William’s place in the family need separate tests.',
    'The burgh-to-Corsankell bridge': 'The household relationships do not establish the possible William-to-James burgh bridge.',
    "The minister's identity and parents": 'The minister’s adult sequence is documented; identification with the Kilwinning household and his parents remain uncertain.',
    'The East Antrim bridge': 'Robert’s relationship to James is documented in 1764. The missing generations back to the seventeenth-century bearers and Scotland remain open.',
    'Which household became which family?': 'The earlier records name local households. They do not yet establish how those households connect to the later families.',
    'Five Glasgow entries (1601–1677)': 'The 1610 Margaret baptism does not settle the distinct 1636 testament identity. Each of the five source occurrences needs its own comparison.',
    'Where the paternal branches meet': 'The DNA comparison needs a documented father-to-son chain connecting a tested line to a named family.',
}


# The people and studies each question is about. People are the profiles the
# maintained question text or its research names; studies are the written
# studies that list them or that the question links. Only existing pages are
# linked (see subjects_html).
QUESTION_SUBJECTS = {
    'glasgow-951': (('glasgow-951', 'glasgow-867'), ('lisnagaver-rasharkin',)),
    'glasgow-822': (('glasgow-822', 'glasgow-3902', 'glasgow-1509'), ('research-irish-inishrush-collateral',)),
    'glasgow-591': (('glasgow-591',), ('research-irish-tamlaght',)),
    'Archibald’s named eldest son': (('glasgow-1101',), ('research-irish-belfast-donegal',)),
    'Where Alexander’s paternal family joins': (('glasgow-951', 'glasgow-1499', 'glasgow-1509', 'glasgow-1505'), ('larne-kilwaughter', 'lisnagaver-rasharkin')),
    "Margaret's surname and the associated testament": (('glasgow-3181',), ('research-hirmenschelis-household',)),
    'The Montgreenan trust and family': (('glasgow-1076', 'glasgow-2952', 'glasgow-2874', 'theobalds-120'), ()),
    'The early burgh connection': (('glasgow-1093', 'glasgow-1098'), ('research-saltmarket-succession',)),
    'The burgh-to-Corsankell bridge': (('glasgow-1168',), ('research-corsankell-household', 'research-glasgow-fishers')),
    "The minister's identity and parents": (('glasgow-1073', 'glasgow-3120'), ('research-kilbirnie-minister',)),
    'The East Antrim bridge': (('glasgow-1143', 'glasgow-1144'), ('larne-kilwaughter', 'research-irish-east-antrim')),
    'Which household became which family?': ((), ('research-irish-derryloran', 'research-irish-moneymore')),
    'Five Glasgow entries (1601–1677)': (('glasgow-3178', 'glasgow-1100'), ('early-scottish-records',)),
    'Where the paternal branches meet': ((), ('larne-kilwaughter',)),
}
_SUBJECT_NAMES = None


def _subject_names(web=None):
    """Person and study names from the published registry and study list."""
    global _SUBJECT_NAMES
    if _SUBJECT_NAMES is None:
        import json
        web = web or WEB
        people, studies = {}, {}
        try:
            people = {row['slug']: row.get('name') or row['slug'] for row in json.loads((web / 'assets/research/registry.json').read_text(encoding='utf-8'))}
            studies = {row['id']: row.get('label') or row['id'] for row in json.loads((web / 'assets/research/branches.json').read_text(encoding='utf-8'))}
        except (OSError, ValueError, KeyError, TypeError):
            pass
        _SUBJECT_NAMES = people, studies
    return _SUBJECT_NAMES


def subjects_html(key, web=None):
    """'People' and 'Study' links for a question; empty when none exists."""
    web = web or WEB
    slugs, study_ids = QUESTION_SUBJECTS.get(key, ((), ()))
    people, studies = _subject_names(web)
    person_links = [f'<a href="/people/{escape(slug, quote=True)}.html">{escape(people[slug])}</a>'
                    for slug in slugs if slug in people and (web / 'people' / f'{slug}.html').is_file()]
    study_links = [f'<a href="/branches/{escape(sid, quote=True)}/">{escape(studies[sid])}</a>'
                   for sid in study_ids if sid in studies and (web / 'branches' / sid / 'index.html').is_file()]
    parts = []
    if person_links:
        parts.append('<span><strong>People:</strong> ' + ' · '.join(person_links) + '</span>')
    if study_links:
        parts.append('<span><strong>' + ('Study' if len(study_links) == 1 else 'Studies') + ':</strong> ' + ' · '.join(study_links) + '</span>')
    return f'<p class="repair-question-subjects">{" ".join(parts)}</p>' if parts else ''


def question_actions(key, context_html=''):
    """Render status, resolution and record target; never invent a missing value."""
    status, resolve, record = QUESTION_ACTIONS.get(key, ('Open', '', ''))
    unknown = f'<span class="question-unknown">{escape(evidence_labels.NOT_YET_IDENTIFIED)}</span>'
    rows = ''.join(
        f'<div><dt>{escape(evidence_labels.QUESTION_FIELDS[field])}</dt><dd>{escape(value) if value else unknown}</dd></div>'
        for field, value in (('resolve', resolve), ('record', record))
    )
    missing = MISSING_CONNECTIONS.get(key, '')
    # The status (already "Open · <qualifier>") links to the guide's entry on question statuses.
    return (f'<p class="repair-question-status"><span class="question-status question-open">'
            f'<a class="ev-label-link" href="{evidence_labels.GUIDE_URL}#open-questions-guide">{escape(status)}</a></span></p>'
            f'<p class="repair-question-missing">{escape(missing)}</p>{subjects_html(key)}'
            f'<details class="repair-question-details"><summary>Evidence and next records to check</summary>'
            f'{context_html}<dl class="question-actions">{rows}</dl></details>')


STUDY_SOURCES = {
    'Five Glasgow entries (1601–1677)': (
        ('FamilySearch Ayrshire sasine index, item #007830795, image 74',
         'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CS3Q-47SZ-P?view=fullText&keywords=GLASGOW&searchForm=advanced&lang=en&groupId=M9QN-ZXH'),
        ('National Records of Scotland, Ayr register RS11/1',
         'https://catalogue.nrscotland.gov.uk/nrsonlinecatalogue/browsetreeview.aspx?reference=RS11'),
        ('FamilySearch Hunterston papers, item #007764588, image 105',
         'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CSM7-J962-6?view=fullText&keywords=Glasgow&searchForm=advanced&lang=en&groupId=M9QY-96Q'),
        ('FamilySearch will index, item #007960708, image 112',
         'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CS8K-D98V?view=index&keywords=Glasgow&searchForm=advanced&lang=en&groupId=M97N-2NT'),
        ('Independent scan of Grant, printed p. 196',
         'https://www.electricscotland.com/history/records/scottishrecordso07scotuoft.pdf#page=206'),
        ('FamilySearch land-record index, item #007830797, image 48',
         'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CS39-S9V2-4?view=fullText&keywords=HUGH+Glasgow&searchForm=simple&lang=en&groupId=M9QN-ZQ3'),
        ('Scottish Record Society publication catalogue',
         'https://www.scottishrecordsociety.org.uk/publications/old-series/'),
        ('FamilySearch Ireland full-text query (17 result cards)',
         'https://www.familysearch.org/en/search/full-text/results?count=100&q.anyDate.to=1699&q.anyPlace=Ireland&q.fullName=Glasgow&c.recordPlace2=on&f.recordPlace1=9%2CIreland&c.recordPlace1=on&f.recordPlace0=9'),
        ('FamilySearch England full-text query (58 result cards)',
         'https://www.familysearch.org/en/search/full-text/results?count=100&q.anyDate.to=1699&q.anyPlace=England&q.fullName=Glasgow&c.recordPlace2=on&f.recordPlace1=9%2CEngland&c.recordPlace1=on&f.recordPlace0=9'),
        ('FamilySearch Irish deed transcription, image 20 (1873–1875 false lead)',
         'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CSK3-33XZ-V?view=fullText&keywords=Glasgow%2CIreland&searchForm=advanced&lang=en'),
    ),
}


def repair():
    changed = Counter()
    programme_path = ROOT / 'research/ancestry-connections/strategy.json'
    programme = ''
    if programme_path.exists():
        strategy = json.loads(programme_path.read_text())
        programme = (
            '<article class="repair-question-focus"><span class="r-kicker">Main research goal · earliest branches first</span>'
            '<h3><a href="/latest-findings/#research-progress">Connect the Glasgow surname family</a></h3>'
            f'<p>{escape(strategy["objective"])}</p>'
            '<p>Begin with the medieval Johns, Alan and the Saltmarket succession. '
            'Track separate paternal branches and unattached family heads; preserve the evidence grade of tentative joins.</p>'
            '<a class="repair-question-arrow" href="/latest-findings/#early-connections">'
            'See the baseline and oldest connection tests &rarr;</a></article>'
        )
    lead, *trails = QUESTIONS
    slug, name, date, question, context = lead
    trails_markup = ''.join(
        f'<a class="repair-question-trail" href="/people/{trail_slug}.html">'
        f'<span class="r-kicker">{escape(trail_date)} &middot; Open question</span>'
        f'<h3>{escape(trail_name)}</h3><p>{escape(trail_question)}</p>'
        f'<span class="repair-question-arrow" aria-hidden="true">Read the evidence &rarr;</span></a>'
        f'<div class="repair-question-trail-actions">{question_actions(trail_slug, "<p>" + escape(trail_context) + "</p>")}</div>'
        for trail_slug, trail_name, trail_date, trail_question, trail_context in trails
    )
    def render_study(region, title, question, context, url):
        sources = STUDY_SOURCES.get(title, ())
        action = ('Open FamilySearch index &rarr;' if url.startswith('https://www.familysearch.org/')
                  else 'Read the study &rarr;' if url.startswith('/branches/')
                  else 'Read the person’s page &rarr;' if url.startswith('/people/')
                  else 'Read the transcription &rarr;' if url.startswith('/research/transcriptions/')
                  else 'Read the Y-DNA story &rarr;' if url.startswith('/ydna/')
                  else 'Read the research notes &rarr;')
        source_markup = (
            '<p class="repair-question-sources"><strong>Sources:</strong> '
            + ' · '.join(f'<a href="{escape(source_url, quote=True)}">{escape(label)}</a>' for label, source_url in sources)
            + '</p>' if sources else ''
        )
        return (
            f'<article class="repair-question-study"><span class="r-kicker">{escape(region)}</span>'
            f'<h3><a href="{escape(url, quote=True)}">{escape(title)}</a></h3>'
            f'<p class="repair-question-prompt">{escape(question)}</p>{question_actions(title, "<p>" + escape(context) + "</p>" + source_markup)}'
            f'<a class="repair-question-arrow" href="{escape(url, quote=True)}">{action}</a></article>'
        )

    wider_markup = ''.join(render_study(*study) for study in ADDITIONAL_QUESTIONS)
    section = (
        '<section id="open-questions" aria-labelledby="open-questions-title">'
        '<div class="repair-question-lead"><span class="r-kicker">Unresolved family history</span>'
        '<h2 id="open-questions-title">Open questions</h2>'
        '<p class="repair-question-intro">Read what we know about each family, why a relationship is still uncertain and which record could help resolve it.</p>'
        f'{programme}'
        f'<a class="repair-question-focus" href="/people/{slug}.html"><span class="r-kicker">{escape(date)} &middot; Featured question</span>'
        f'<h3>{escape(name)}</h3><p>{escape(question)}</p><span>Follow the evidence &rarr;</span></a>'
        f'<div class="repair-question-focus-actions">{question_actions(slug, "<p>" + escape(context) + "</p>")}</div>'
        f'<p class="evidence-guide-link"><a href="{evidence_labels.GUIDE_URL}">{evidence_labels.GUIDE_LABEL}</a>'
        '<span> What the status labels mean.</span></p></div>'
        '<div class="repair-question-trails"><div class="repair-question-trails-head"><span>Other ancestors being researched</span><p>Each study explains what is known and what still needs proof.</p></div>'
        f'{trails_markup}</div><div class="repair-question-wider">'
        '<div class="repair-question-wider-head"><h3>More family questions</h3>'
        '<p>Identity, parentage and the missing links between documented households.</p>'
        '<a class="r-button" href="/branches/#research-studies">Browse family studies &rarr;</a></div>'
        f'<div class="repair-question-study-grid">{wider_markup}</div></div></section>'
    )
    path = WEB / 'research/index.html'
    before = page = path.read_text(encoding='utf-8')
    if 'id="open-questions"' in page:
        page = re.sub(r'<section\b(?=[^>]*\bid="open-questions")[^>]*>.*?</section>', lambda _: section, page, count=1, flags=re.S)
    else:
        page = page.replace('</header><div class="repair-research-grid">', '</header>' + section + '<div class="repair-research-grid">', 1)
    style = '''<style id="open-questions-style">
#open-questions{scroll-margin-top:100px;display:grid;grid-template-columns:1.15fr 1fr;gap:24px;margin:28px 0 42px;padding:0;background:transparent;border:0}
#open-questions h2{font:500 36px/1.13 var(--g-serif);letter-spacing:-.025em;margin:8px 0 14px;color:#30452d}
#open-questions h3{font:500 25px/1.15 var(--g-serif);letter-spacing:-.015em;margin:7px 0;color:#30452d}
.repair-question-lead,.repair-question-trails,.repair-question-wider{align-self:start;background:#e7ebdd;border:1px solid #d6ddc8;padding:30px 32px;min-width:0}
.repair-question-intro{max-width:510px;margin:0 0 24px;color:#53634a;font:15px/1.58 var(--g-sans)}
.repair-question-focus{display:block;max-width:510px;padding:18px 0 2px;border-top:1px solid #bac8a6;color:inherit;text-decoration:none}
.repair-question-focus>p{margin:0 0 13px;color:#40523c;font:16px/1.5 var(--g-serif)}
.repair-question-focus>span:last-child,.repair-question-arrow{font:700 10px/1.3 var(--g-sans);letter-spacing:.08em;text-transform:uppercase;color:#496844}
.repair-question-trails{display:grid;align-content:start;gap:0}
.repair-question-trails-head{padding:2px 0 14px;border-bottom:1px solid #cbd5bf}
.repair-question-trails-head>span{font:700 10px/1.3 var(--g-sans);letter-spacing:.11em;text-transform:uppercase;color:#496844}
.repair-question-trails-head p{margin:6px 0 0;color:#66745c;font:12px/1.45 var(--g-sans)}
.repair-question-trail{display:block;margin-top:16px;padding:18px 20px 14px;background:#f8faf4;border:1px solid #cbd5bf;border-bottom:0;color:inherit;text-decoration:none}
.repair-question-trail p{max-width:400px;margin:0 0 13px;color:#40523c;font:15px/1.45 var(--g-serif)}
.repair-question-trail-actions{padding:0 20px 17px;background:#f8faf4;border:1px solid #cbd5bf;border-top:0}
.repair-question-focus:hover h3,.repair-question-trail:hover h3{text-decoration:underline;text-decoration-color:#758b69;text-underline-offset:4px}
.repair-question-wider{grid-column:1/-1}
.repair-question-wider-head{margin-bottom:24px}.repair-question-wider-head p{color:#53634a;max-width:680px}
.repair-question-study-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.repair-question-study{background:#f8faf4;border:1px solid #cbd5bf;padding:20px;min-width:0}
.repair-question-study h3 a{color:inherit;text-decoration:none}.repair-question-study h3 a:hover{text-decoration:underline}
.repair-question-study>p{font:14px/1.6 var(--g-sans);color:#53634a;max-width:510px}
.repair-question-study>p.repair-question-prompt{font:18px/1.4 var(--g-serif);color:#30452d}
.repair-question-study>a{display:inline-block;margin:7px 0 12px;text-underline-offset:4px}
.repair-question-subjects{margin:0 0 10px;font:13px/1.55 var(--g-sans);color:#53634a}.repair-question-subjects>span{display:block}.repair-question-subjects a{color:#496844;text-underline-offset:3px}
@media(max-width:720px){.repair-question-study-grid{grid-template-columns:1fr;gap:18px}.repair-question-wider{padding-top:20px}}
@media(max-width:720px){#open-questions{grid-template-columns:1fr;gap:16px;margin:18px -1px 32px}#open-questions h2{font-size:32px}.repair-question-lead,.repair-question-trails,.repair-question-wider{padding:24px 22px}.repair-question-focus{max-width:none}.repair-question-trail{padding:17px 18px 13px}.repair-question-trail-actions{padding:0 18px 16px}.repair-question-trail h3{font-size:23px}}
</style>'''
    if 'id="open-questions-style"' in page:
        page = re.sub(r'<style id="open-questions-style">.*?</style>', style, page, count=1, flags=re.S)
    else:
        page = page.replace('</head>', style + '</head>', 1)
    if page != before:
        path.write_text(page, encoding='utf-8')
        changed['research_questions'] += 1

    path = WEB / 'index.html'
    before = page = path.read_text(encoding='utf-8')
    button = '<a class="r-button primary" href="/research/#open-questions">Explore the main research questions &rarr;</a>'

    def feature(match):
        content = match.group(0)
        if 'Inside the research' not in content or '/research/#open-questions' in content:
            return content
        return content.replace('<div class="r-actions">', '<div class="r-actions">' + button, 1).replace('class="r-button primary" href="/people/glasgow-951.html"', 'class="r-button" href="/people/glasgow-951.html"', 1)

    page = re.sub(r'<section class="v3-feature">.*?</section>', feature, page, flags=re.S)
    if page != before:
        path.write_text(page, encoding='utf-8')
        changed['research_questions'] += 1
    return changed


if __name__ == '__main__':
    print(dict(repair()))
