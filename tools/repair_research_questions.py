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
     'Probable father (evaluation of 23 September 2026): John Glasgow, farmer, named in John-867’s 1846 marriage. Nancy Glasgow’s 1892 Plattsburgh probate citation serves Alexander’s children as heirs, in the same class as her named niece and nephew. Every sibling branch with a recorded birth surname is Glasgow, which points to a shared father. No record names Alexander’s father directly. Nancy’s probate petition and heir schedule are the decisive test, and his mother is unknown. The Larne reconstruction remains the wider-origin question.'),
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
    ('Larne, Inishrush & South Carolina', 'Where Alexander’s paternal family joins',
     'Was James of Larne Adam’s father, and was Tennessee Robert Archibald’s missing son?',
     'The two family reconstructions fit without making Robert the Irish men’s father. Compare the Larne 1762 marriage and William’s 1815 will with Archibald’s 1818 adult-heir receipts; each can name a missing connection. John Glasgow, farmer, is Alexander’s probable father, and his Desertoghill identity is unproved. Neither missing names nor a whole-haplogroup age settles the Larne joining generation.',
     '/people/glasgow-951.html#larne-reconstruction'),
    ('Hirmenschelis & the Huchesoun fragment', 'Margaret\'s surname and the associated testament',
     'Why was Andro Huchesoun\'s confirmation included with John Glasgow\'s record, and could it help identify Margaret?',
     'The supplementary strip is now partially transcribed: it names Andro Huchesoun, children, and provisionally Johne Huchesoun. The complete kin clause is unresolved. Margaret\'s proposed Hochaine/Hutchin surname makes this a research lead, not a proved relationship; the archive must explain how strip 396A maps to image 276.',
     '/research/transcriptions/john-1577/#associated-fragment'),
    ('Ayrshire & St Vincent', 'The Montgreenan trust and family',
     'Which existing child profiles match the people named in Robert Glasgow’s trust and succession papers?',
     'UCL’s published archival research reports children John and Emilia and identifies Anne as his natural daughter. This challenges the older childlessness account. The original trust, distinct Emilia/Amelia identities and suggested relationships in the enslaved household still need examination.',
     '/people/glasgow-1076.html'),
    ('Early Scottish records', 'The early burgh connection',
     'Do the Stirling, alias-Smith and Saltmarket records describe the same John, and how does William fit?',
     'The proposed identities remain possible; the Saltmarket-to-William succession is a separate probable connection. Neither establishes the entire exported early pedigree.',
     "https://www.wikitree.com/wiki/Space:John%20de%20Glasgow%20alias%20Smith%20/%20John%20Glasgow%20of%20Saltmarket'"),
    ('Glasgow & Ayrshire', 'The burgh-to-Corsankell bridge',
     'How do the documented Corsankell households connect to the Glasgow burgh family?',
     'The proposed identification of Robert of Kilbride with the burgh fisher is an important test. Property succession and associates must establish the exact bridge; nearby Calder records do not establish it.',
     'https://www.wikitree.com/wiki/Space:Glasgow%20Name%20Study'),
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
     '/branches/larne-kilwaughter/#larne-original-evidence'),
    ('Early Scottish records', 'Five Glasgow entries (1601–1677)',
     'Can the five FamilySearch index and court-record occurrences from 1601–1677 be traced to identifiable people?',
     'The 1932 Ayrshire sasine index names Agnes Glasgow, spouse of John Logan/Logane, in Milneburne, Stevenston, recorded 29 June 1601; she is probably Glasgow-3178, but the underlying RS11/1 entry needs checking. Grant’s Glasgow testament index lists “Margaret, in Byris of Kilwinning,” dated 8 November 1636. Glasgow-1100 is chronologically possible, but the index gives no spouse or kin, and the date is not a proved death date. The same index lists “John, in Rashie” (AI transcript: Rashlic), parish of Kilbride, dated 17 April 1643. A 1674 Hunterston papers extract names “James Glasgow in Didup” in an inquest list, and the 1677 Register of Deeds index lists “Hugh Glasgow, preacher of the gospel.” These are five source-level occurrences, not necessarily five people. Several existing James profiles remain possible; Hugh may overlap with Glasgow-1603, Hew-1066 or Glasgow-3109. John is not Glasgow-4061; a raw Findmypast John Glasgow 1643 candidate may be the same testament, and the separate John in Bog of Steivinstoun entry dated 6 November 1685 is already recorded. Follow-up FamilySearch place filters for Ireland (17 cards), England (58), the United States, Wales and Canada (no results) found no new image-verified pre-1700 bearer. Promising Irish court, English probate, church, muster and guild items were FamilySearch Center/affiliate-library restricted; an accessible 1875 Irish deed transcription mentions James Glasgow at Glenarm but is not an early record.',
     'https://www.familysearch.org/ark:/61903/3:1:3Q9M-CS3Q-47SZ-P?view=fullText&keywords=GLASGOW&searchForm=advanced&lang=en&groupId=M9QN-ZXH'),
    ('Documentary lines & Y-DNA', 'Where the paternal branches meet',
     'Where does a documented male Kilwaughter line sit among the tested paternal branches?',
     'A documented tester chain can connect the genetic comparison to a particular family. Shared SNPs can locate a branch, but cannot name the missing ancestor.',
     'https://www.wikitree.com/wiki/Space:Glasgow%20Name%20Study'),
)

# Status, what would resolve each question and the record to request or
# inspect. Every entry restates the maintained research cited above (or the
# person's presentation.json research tasks); an empty value is published as
# "Not yet identified" rather than filled with a guess.
QUESTION_ACTIONS = {
    'glasgow-951': ('Open · probable father, not proved',
                    'A probate petition or heir schedule stating each cited person’s relationship to Nancy Glasgow.',
                    'Clinton County Surrogate’s Court probate file for Nancy Glasgow (d. 1891): petition and affidavit/schedule of heirs and next of kin.'),
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
    'The Montgreenan trust and family': ('Open',
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


def question_actions(key):
    """Render status, resolution and record target; never invent a missing value."""
    status, resolve, record = QUESTION_ACTIONS.get(key, ('Open', '', ''))
    unknown = f'<span class="question-unknown">{escape(evidence_labels.NOT_YET_IDENTIFIED)}</span>'
    rows = ''.join(
        f'<div><dt>{escape(evidence_labels.QUESTION_FIELDS[field])}</dt><dd>{escape(value) if value else unknown}</dd></div>'
        for field, value in (('resolve', resolve), ('record', record))
    )
    return (f'<p class="repair-question-status"><span class="question-status question-open">{escape(status)}</span></p>'
            f'<dl class="question-actions">{rows}</dl>')


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
        f'<div class="repair-question-trail-actions">{question_actions(trail_slug)}</div>'
        for trail_slug, trail_name, trail_date, trail_question, _ in trails
    )
    def render_study(region, title, question, context, url):
        sources = STUDY_SOURCES.get(title, ())
        action = 'Open FamilySearch index &rarr;' if url.startswith('https://www.familysearch.org/') else 'Read the maintained research &rarr;'
        source_markup = (
            '<p class="repair-question-sources"><strong>Sources:</strong> '
            + ' · '.join(f'<a href="{escape(source_url, quote=True)}">{escape(label)}</a>' for label, source_url in sources)
            + '</p>' if sources else ''
        )
        return (
            f'<article class="repair-question-study"><span class="r-kicker">{escape(region)}</span>'
            f'<h3><a href="{escape(url, quote=True)}">{escape(title)}</a></h3>'
            f'<p class="repair-question-prompt">{escape(question)}</p>{question_actions(title)}<p>{escape(context)}</p>{source_markup}'
            f'<a class="repair-question-arrow" href="{escape(url, quote=True)}">{action}</a></article>'
        )

    wider_markup = ''.join(render_study(*study) for study in ADDITIONAL_QUESTIONS)
    section = (
        '<section id="open-questions" aria-labelledby="open-questions-title">'
        '<div class="repair-question-lead"><span class="r-kicker">The roots we are researching</span>'
        '<h2 id="open-questions-title">Main open<br>research questions</h2>'
        '<p class="repair-question-intro">The main open questions across the maintained family studies and free-space research. Proposed identities and family links remain separate from documented relationships.</p>'
        f'<a class="repair-question-focus" href="/people/{slug}.html"><span class="r-kicker">{escape(date)} &middot; The nearest question</span>'
        f'<h3>{escape(name)}</h3><p>{escape(question)}</p><span>Follow the evidence &rarr;</span></a>'
        f'<div class="repair-question-focus-actions">{question_actions(slug)}</div>'
        f'<p class="evidence-guide-link"><a href="{evidence_labels.GUIDE_URL}">{evidence_labels.GUIDE_LABEL}</a>'
        '<span> What the status labels mean.</span></p></div>'
        '<div class="repair-question-trails"><div class="repair-question-trails-head"><span>Other roots under review</span><p>Each trail records what is known and what remains unproved.</p></div>'
        f'{trails_markup}</div><div class="repair-question-wider">'
        '<div class="repair-question-wider-head"><h3>Beyond the nearest roots</h3>'
        '<p>Identity, parentage and the missing links between documented households.</p>'
        '<a class="r-button" href="/branches/#research-studies">Explore the evidence-led research groups &rarr;</a></div>'
        f'<div class="repair-question-study-grid">{wider_markup}</div></div></section>'
    )
    path = WEB / 'research/index.html'
    before = page = path.read_text(encoding='utf-8')
    if 'id="open-questions"' in page:
        page = re.sub(r'<section\b(?=[^>]*\bid="open-questions")[^>]*>.*?</section>', lambda _: section, page, count=1, flags=re.S)
    else:
        page = page.replace('</header><div class="repair-research-grid">', '</header>' + section + '<div class="repair-research-grid">', 1)
    style = '''<style id="open-questions-style">
#open-questions{scroll-margin-top:100px;display:grid;grid-template-columns:1.15fr 1fr;gap:44px;margin:28px 0 42px;padding:37px 38px;background:#e7ebdd;border:1px solid #d6ddc8}
#open-questions h2{font:500 36px/1.13 var(--g-serif);letter-spacing:-.025em;margin:8px 0 14px;color:#30452d}
#open-questions h3{font:500 25px/1.15 var(--g-serif);letter-spacing:-.015em;margin:7px 0;color:#30452d}
.repair-question-intro{max-width:510px;margin:0 0 24px;color:#53634a;font:15px/1.58 var(--g-sans)}
.repair-question-focus{display:block;max-width:510px;padding:18px 0 2px;border-top:1px solid #bac8a6;color:inherit;text-decoration:none}
.repair-question-focus>p{margin:0 0 13px;color:#40523c;font:16px/1.5 var(--g-serif)}
.repair-question-focus>span:last-child,.repair-question-arrow{font:700 10px/1.3 var(--g-sans);letter-spacing:.08em;text-transform:uppercase;color:#496844}
.repair-question-trails{border-left:1px solid #bac8a6;padding-left:26px}
.repair-question-trails-head{padding:2px 0 14px;border-bottom:1px solid #cbd5bf}
.repair-question-trails-head>span{font:700 10px/1.3 var(--g-sans);letter-spacing:.11em;text-transform:uppercase;color:#496844}
.repair-question-trails-head p{margin:6px 0 0;color:#66745c;font:12px/1.45 var(--g-sans)}
.repair-question-trail{display:block;padding:20px 0 18px;border-bottom:1px solid #cbd5bf;color:inherit;text-decoration:none}
.repair-question-trail p{max-width:400px;margin:0 0 13px;color:#40523c;font:15px/1.45 var(--g-serif)}
.repair-question-focus:hover h3,.repair-question-trail:hover h3{text-decoration:underline;text-decoration-color:#758b69;text-underline-offset:4px}
.repair-question-wider{grid-column:1/-1;border-top:1px solid #bac8a6;padding-top:26px;min-width:0}
.repair-question-wider-head{margin-bottom:24px}.repair-question-wider-head p{color:#53634a;max-width:680px}
.repair-question-study-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px 40px}
.repair-question-study{border-top:1px solid #cbd5bf;padding-top:20px;min-width:0}
.repair-question-study h3 a{color:inherit;text-decoration:none}.repair-question-study h3 a:hover{text-decoration:underline}
.repair-question-study>p{font:14px/1.6 var(--g-sans);color:#53634a;max-width:510px}
.repair-question-study>p.repair-question-prompt{font:18px/1.4 var(--g-serif);color:#30452d}
.repair-question-study>a{display:inline-block;margin:7px 0 12px;text-underline-offset:4px}
@media(max-width:720px){.repair-question-study-grid{grid-template-columns:1fr;gap:18px}.repair-question-wider{padding-top:20px}}
@media(max-width:720px){#open-questions{grid-template-columns:1fr;gap:23px;margin:18px -1px 32px;padding:24px 22px}#open-questions h2{font-size:32px}.repair-question-trails{border-left:0;border-top:1px solid #bac8a6;padding:18px 0 0}.repair-question-focus{max-width:none}.repair-question-trail{padding:17px 0}.repair-question-trail h3{font-size:23px}}
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
