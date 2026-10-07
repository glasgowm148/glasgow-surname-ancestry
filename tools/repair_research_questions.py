#!/usr/bin/env python3
"""Expose the maintained root research questions without rebuilding dossiers."""
from collections import Counter
from html import escape
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import evidence_labels  # noqa: E402

WEB = ROOT / 'www'
# Questions drawn from research/Glasgow-{951,822,591}/findings.md.
QUESTIONS = (
    ('glasgow-951', 'Alexander Glasgow', 'c.1811',
     'Who were Alexander of Lisnagaver\'s parents?',
     'Probable father (reviewed 29 September 2026): John Glasgow, farmer, named in John-867’s 1846 marriage. Nancy Glasgow’s 1892 Plattsburgh probate citation serves Alexander’s children as heirs, in the same class as her named niece and nephew. Every sibling branch with a recorded birth surname is Glasgow, which points to a shared father. No record names Alexander’s father directly. The new death notice gives Nancy about 75, conflicting with her will’s age. Glenleslie’s Nancy died in 1847 and is a different woman. Independent sibling parent statements, the Scottish Mary Thomson–Sneddon candidate and the docketed 1894 appraisal offer further tests; the petition remains valuable. His mother is unknown. The Larne reconstruction remains the wider-origin question.'),
    ('glasgow-822', 'John Glasgow', '1767',
     'Can the Bible John be identified with the Inishrush householder, and who were his parents?',
     'The 1831 identity is probable. John’s possible brotherhood with Adam makes the Larne James-1509 hypothesis testable alongside older Adam and Maria from the naming pattern. His nine-child Bible weakens direct fatherhood of Alexander, not collateral kinship.'),
    ('glasgow-591', 'William Glasgow', 'c.1656',
     'Which Scottish William became the ancestor remembered in the Tyrone tradition?',
     'The Cavers Covenanter is the leading identified candidate, but his migration, parentage and the William-to-John documentary line remain unproved. A broader Y-DNA cluster does not establish this individual connection.'),
)

# Additional main workstreams drawn from the maintained Name Study, Early
# Ireland and Saltmarket free-space research, rather than tree connectivity.
ADDITIONAL_QUESTIONS = (
    ('Donegal: Ramelton & Lifford', 'Archibald’s named eldest son',
     'Is the Thomas named in Archibald’s April 1673 will the later Lifford/Raphoe man?',
     'Betham GO MS 225 p. 90/image 97 explicitly names Thomas Glasgow as eldest son of Archibald of Rathmalton. The son-to-Lifford identity is strongly probable, but the abstract gives no residence or estate. The new Lifford purchase transcript and shared Hamill title-group context strengthen the regional setting without proving inheritance or parentage. The live father field remains uncertain.',
     '/branches/research-irish-belfast-donegal/#ramelton'),
    ('Larne, Inishrush & South Carolina', 'Where Alexander’s paternal family joins',
     'Who was the father of John Glasgow, farmer (Alexander’s probable father), and is the documented Kilwaughter family inside R-FT20271?',
     'No record names John farmer’s father. The Larne candidates (Hugh-1499 through John-4179, James-1509, William-1505) and a County Londonderry origin are all unresolved. A Big Y-700 test of a documented Kilwaughter line would show, if the tester’s pedigree is right, whether that family is in FT20271 at all. Tennessee Robert as Archibald’s son and as James J’s father remain the two unproved American links.',
     '/people/glasgow-951.html#larne-reconstruction'),
    ('Hirmenschelis & the Huchesoun fragment', 'Margaret\'s surname and the associated testament',
     'Why was Andro Huchesoun\'s confirmation included with John Glasgow\'s record, and could it help identify Margaret?',
     'The supplementary strip is now partially transcribed: it names Andro Huchesoun, children, and provisionally Johne Huchesoun. The complete kin clause is unresolved. Margaret\'s proposed Hochaine/Hutchin surname makes this a research lead, not a proved relationship; the archive must explain how strip 396A maps to image 276.',
     '/research/transcriptions/john-1577/#associated-fragment'),
    ('Ayrshire & St Vincent', 'The Montgreenan trust and family',
     'Which existing child profiles match the people named in Robert Glasgow’s trust and succession papers?',
     'The current profiles John Glasgow-2952 and Anne Glasgow-2874 represent the named Montgreenan son and Robertson wife. Amelia Wilson-3789 is John’s sister and is distinct from his housekeeper Theobalds-120. The trust’s Emilia identification remains qualified; original trust, maternal claims and inferred household relationships still need examination.',
     '/people/glasgow-1076.html'),
    ('Early Scottish records', 'The early burgh connection',
     'Do the Stirling, alias-Smith and Saltmarket records describe the same John, and how does William fit?',
     'The proposed identities remain possible; the Saltmarket-to-William succession is a separate probable connection. Neither establishes the entire exported early pedigree.',
     '/free-space/john-de-glasgow-alias-smith-john-glasgow-of-saltmarket-7ac174/'),
    ('Glasgow & Ayrshire', 'The burgh-to-Corsankell bridge',
     'How do the documented Corsankell households connect to the Glasgow burgh family?',
     'The proposed identification of Robert of Kilbride with the burgh fisher is an important test. Property succession and associates must establish the exact bridge; nearby Calder records do not establish it.',
     '/branches/research-corsankell-household/'),
    ('Kilbirnie & Kilwinning', 'The minister\'s identity and parents',
     'Is the Kilwinning John the minister of Kilbirnie, and who were his parents?',
     'A FamilySearch-catalogued handwritten genealogy names undated Georges of the Bog in Stevenson/Stevenston and the Bay in Kelvening/Kilwinning while asking about their connection to the minister. The Bay George might overlap the unsourced Glasgow-3120 profile, but the note does not identify either man or prove a pre-1700 date. The minister\'s identity and parentage still require contemporary parish, marriage and church records.',
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
     'Can the five FamilySearch index and court-record occurrences from 1601–1677 be traced to identifiable people?',
     'The 1932 Ayrshire sasine index names Agnes Glasgow, spouse of John Logan/Logane, in Milneburne, Stevenston, recorded 29 June 1601; she is probably Glasgow-3178, but the underlying RS11/1 entry needs checking. Grant’s Glasgow testament index lists “Margaret, in Byris of Kilwinning,” dated 8 November 1636. Glasgow-1100 is chronologically possible, but the index gives no spouse or kin, and the date is not a proved death date. The same index lists “John, in Rashie” (AI transcript: Rashlic), parish of Kilbride, dated 17 April 1643. A 1674 Hunterston papers extract names “James Glasgow in Didup” in an inquest list, and the 1677 Register of Deeds index lists “Hugh Glasgow, preacher of the gospel.” These are five source-level occurrences, not necessarily five people. Several existing James profiles remain possible; Hugh may overlap with Glasgow-1603, Hew-1066 or Glasgow-3109. John is not Glasgow-4061; a raw Findmypast John Glasgow 1643 candidate may be the same testament, and the separate John in Bog of Steivinstoun entry dated 6 November 1685 is already recorded. Follow-up FamilySearch place filters for Ireland (17 cards), England (58), the United States, Wales and Canada (no results) found no new image-verified pre-1700 bearer. Promising Irish court, English probate, church, muster and guild items were FamilySearch Center/affiliate-library restricted; an accessible 1875 Irish deed transcription mentions James Glasgow at Glenarm but is not an early record.',
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
    'Archibald’s named eldest son': ('Open · father clause found, identity strongly probable',
                    'A distinctive estate, relative or associate linking the named 1673 son to the Lifford adult.',
                    'NAI PRCT/1/1, microfilm MFGS/41/1 (accessible; G index and Glas* transcript matches checked without locating the particular will); PRONI deed recitals and Cairns/M’Auley collateral records.'),
    'glasgow-951': ('Open · probable father, not proved',
                    'A relationship-bearing estate schedule or independent parent statement in a reconstructed sibling branch.',
                    'Nancy’s probate petition/heir schedule and 1894 appraisal; Mary Thomson–Sneddon’s family and Ann Glasgow McClelland’s own death.'),
    'glasgow-822': ('Open · 1831 identity probable',
                    'A kin term, transfer, residence or family admission linking the two Inishrush households.',
                    'Drimbolg congregation admissions and session records for John and Adam Glasgow.'),
    'glasgow-591': ('Open · leading candidate unproved',
                    'A migration or father–son record for William.',
                    'The original 1725 Cavankilgreen memorial; the 1673 Quothquan testament, NRS CC14/5/9.'),
    'Where Alexander’s paternal family joins': ('Open',
                    'A named missing connection in the Larne marriage, William’s will or Archibald’s receipts.',
                    'The Larne 1762 marriage; William’s 1815 will; Archibald’s 1818 adult-heir receipts.'),
    'Margaret\'s surname and the associated testament': ('Open · kin clause partly transcribed',
                    'The complete kin clause, and the archive’s explanation of how strip 396A maps to image 276.',
                    'The supplementary strip 396A with Andro Huchesoun’s confirmation (image 276).'),
    'The Montgreenan trust and family': ('Partly resolved · John and Anne linked',
                    '',
                    'Robert Glasgow’s original trust and succession papers.'),
    'The early burgh connection': ('Open · proposed identities possible', '', ''),
    'The burgh-to-Corsankell bridge': ('Open',
                    'Property succession and associates that establish the exact bridge.', ''),
    'The minister\'s identity and parents': ('Open',
                    '',
                    'Contemporary parish, marriage and church records for the minister.'),
    'The East Antrim bridge': ('Open · Robert-1143 to James-1144 documented',
                    '',
                    'NRS GD154/514–515, /525, /530 and /532 tenant originals; PRONI T/828/15.'),
    'Which household became which family?': ('Open', '', ''),
    'Five Glasgow entries (1601–1677)': ('Open · source-level occurrences only',
                    '',
                    'The underlying Ayr register entry, NRS RS11/1, for Agnes Glasgow (1601).'),
    'Where the paternal branches meet': ('Open',
                    'A documented tester chain connecting the genetic comparison to a particular family.', ''),
}


MISSING_CONNECTIONS = {
    'glasgow-951': 'John Glasgow, farmer, is Alexander’s probable father. A separate family record is needed to test that inference; his mother remains unknown.',
    'glasgow-822': 'The missing link is between the Bible family and the recorded Inishrush households, before working back to John’s parents.',
    'glasgow-591': 'The Scottish candidate needs a recorded connection to the Tyrone family. The migration and father–son line are still unproved.',
    'Archibald’s named eldest son': 'The will names Archibald’s son Thomas. The remaining question is whether he is the later Thomas at Lifford.',
    'Where Alexander’s paternal family joins': 'The missing connections are between the Larne, Inishrush and South Carolina families; the matching reconstructions need named family evidence.',
    "Margaret's surname and the associated testament": 'The remaining passage may help identify Margaret, but neither its complete family wording nor its connection to John’s record is settled.',
    'The Montgreenan trust and family': 'John and Anne are linked. Other people named in the trust, including Emilia, still need their identities and family connections checked.',
    'The early burgh connection': 'The same-name Johns may be different men. Their identities and William’s place in the family need separate tests.',
    'The burgh-to-Corsankell bridge': 'Both households have their own evidence. The missing link is a record connecting the Glasgow burgh family to Corsankell.',
    "The minister's identity and parents": 'The Kilwinning man’s identification as the Kilbirnie minister and his parents are still unresolved.',
    'The East Antrim bridge': 'Robert’s relationship to James is documented in 1764. The missing generations back to the seventeenth-century bearers and Scotland remain open.',
    'Which household became which family?': 'The earlier records name local households. They do not yet establish how those households connect to the later families.',
    'Five Glasgow entries (1601–1677)': 'Five record occurrences need individual identity checks. They are not necessarily five distinct people or established matches to existing profiles.',
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
