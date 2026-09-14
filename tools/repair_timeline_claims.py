"""Maintained, public-safe calibration of the Timeline's illustrative narratives.

Genetic measurements are preserved. Historical scenarios are not biographies.
Context: maintained FT4811 study (research/free-space-pages/pages/051-r-ft4811.wiki),
whose competing Normandy/Borders explanations are hypotheses, not a pedigree.
"""
from bs4 import BeautifulSoup

HISTORY = {
    'R-S20045': ('A narrow surviving branch, not an identified disaster', [
        'The long interval and few sampled descendant branches are compatible with a paternal-line bottleneck. They do not establish how many men lived in the original population, nor whether war, climate, migration or uneven modern sampling explains the pattern.',
        'Iron Age communities around the North Sea experienced environmental and economic change. An ancestral association with bog-iron working, the Cimbrian migrations or a particular catastrophe is an untested historical scenario. No identified S20045 ancient individual connects this family to those events.',
    ]),
    'R-BY139800': ('North Sea life and the Roman frontier', [
        'Jutland, the Elbe region and the Roman frontier supply possible historical settings for this period. Archaeological finds illuminate regional exchange, warfare and iron production; they do not identify the occupation or home of this paternal ancestor.',
        'The earlier project scenario proposed a Jastorf-community origin, bog-iron specialists, survival through the Cimbrian migrations and later frontier service. These are separate propositions requiring evidence, not consequences of the SNP date. Roman objects found in northern Europe cannot prove that this particular family traded with Rome.',
    ]),
    'R-S14827': ('Several possible routes across the North Sea', [
        'The estimated branching period overlaps major changes in northern Europe. Anglo-Saxon settlement, continental coastal movements and later Norse migration are historical routes worth comparing with the distribution of tested lines.',
        'A Normandy route through the Saxon Shore or the Bessin is one project hypothesis, not an established journey. A common-ancestor estimate earlier than Rollo does not exclude later migration by descendants, and cannot prove membership of a Continental Saxon aristocracy. Ancient DNA and independently linked pedigrees are needed to distinguish these scenarios.',
    ]),
    'R-FT4811': ('A shared paternal root; the medieval route is open', [
        'Modern tested branches connect Glasgow, Duffield, Churnside, Brown and Wright research lines at this upstream level. Shared descent does not identify the common ancestor, his occupation, feudal allegiance or place of arrival in Britain.',
        'The maintained project study contains two working explanations: a Normandy-to-Derbyshire route involving Ferrers or Vipont networks, and a lowland Scots or Borders origin suggested by later family geography. Neither is a documented father-to-son bridge. A date compatible with the Norman period is not evidence that the ancestor crossed in 1066.',
        'The later surnames and ancestral locations are research leads. Claims of professional soldiers, three brothers divided between lordships, or descent from one named Norman invader exceed the current evidence. Documentary work on each tester pedigree and additional independently placed tests can discriminate between the models.',
    ]),
    'R-FT32941': ('The Duffield connection: evidence and proposed bridge', [
        'Modern Duffield and Glasgow test results provide a paternal connection at this level. They do not by themselves place the common ancestor at Duffield Castle, identify Roger de Duffeld as a carrier, or establish an elder Duffield brother and younger Glasgow cleric.',
        'Duffield and Ferrers estates, and recruitment between England and Scotland, offer a possible medieval context. The proposed roles of steward, forester, soldier or cleric remain hypotheses. The existence of a castle or a documented office does not assign that office to an SNP ancestor.',
        'John of Huntingdon and the medieval de Glasgu record bearers below are documentary subjects to investigate separately. Their recorded careers are distinct from the unproved proposal that they connect Duffield descendants to later Glasgow families. No named medieval man is genetically identified here.',
    ]),
    'R-FT25406': ('The Glasgow name: records beside genetics', [
        'FT25406 groups tested Glasgow/Glasgo paternal lines in the surname era. Its age estimate supports comparison with late-medieval records, but cannot identify a particular fifteenth-century carrier or validate the missing generations in a paper pedigree.',
        'The maintained records identify clerics, royal servants and later burgh figures. John Glasgow alias Smith is a documentary research subject near this period; the alias and property evidence should be interpreted in their own records. A royal-armourer role is not established by his surname, and DNA does not assign him to FT25406.',
        'The earlier "Iron Guild" narrative proposed continuous inherited metalworking from Iron Age Jutland through Ferrers estates to Scottish burghs. That continuity is unsupported: a shared Y chromosome carries no occupational history. Medieval trades and burgh networks remain useful research context, not proof of a 3,000-year hereditary caste.',
    ]),
    'R-FT20271': ('Scotland, Ulster and the Atlantic: test each family route', [
        'The Scottish, Irish and North American ancestral locations reported by testers make migration across these regions relevant context. Scottish Presbyterian settlement, religious conflict and Atlantic migration affected many families; they do not establish the motive or route of every Glasgow line.',
        'The SNP does not prove a Plantation arrival, persecution during the Killing Times, or travel along the Great Wagon Road. Each such claim needs records for the specific person. Ulster settlement and later American movements may belong to different generations and branches.',
        'The linked research profiles and the genetic panel distinguish documentary anchors, reported tester pedigrees and provisional placements. Resolve those pedigrees independently rather than treating the whole FT20271 group as one documented migration story.',
    ]),
}

DNA_PROSE = {
    'A-PR2921': ['Y-chromosomal ancestry connects living paternal lines through shared ancestors. It does not identify those ancestors\' occupations, social roles or individual biographies.'],
    'R-S20045': ['The sampled tree has a long, sparsely branching interval. A population bottleneck is one possible explanation, but missing or unevenly sampled descendant lines can also affect its shape. The date and modern tree cannot identify a specific ancient disaster.'],
    'R-BY139800': ['This genetic branch is placed between older North Sea-associated nodes and later descendants. Its estimated age is a genetic inference; Jutland settlement, ironworking and contact with Rome are possible historical settings rather than established family events.'],
    'R-S14827': ['S14827 joins several sampled paternal branches. Their dates and later distribution provide clues for comparing migration scenarios, but neither proves an Anglo-Saxon, Norse, Norman or Saxon Shore identity for the common ancestor.'],
    'R-FT4811': ['FT4811 is an upstream shared paternal root for the tested research lines shown below. The common-ancestor estimate is statistical, not a dated migration or a named medieval pedigree. Later family geography motivates competing Borders and Normandy hypotheses; it does not establish feudal allegiances or a division between identified sons.'],
    'R-FT32941': ['Modern Duffield and Glasgow test results connect at this upstream node. The shared mutation does not locate its first carrier at Duffield Castle or establish descent from a named medieval cleric. Later surname distributions motivate a proposed Duffield-to-Glasgow bridge that remains unproved.'],
}

def calibrate(page):
    soup = BeautifulSoup(page, 'html.parser')
    for row in soup.select('.timeline-row'):
        identifier = row.get('id')
        for card in row.select('.card'):
            historical = 'card-hist' in card.get('class', [])
            body = card.select_one('.card-body') or card
            if historical and identifier in HISTORY:
                title, paragraphs = HISTORY[identifier]
                links = {a.get('href'): a.get_text(' ', strip=True) for a in card.select('a[href]')}
                body.clear()
                for text in paragraphs:
                    paragraph = soup.new_tag('p'); paragraph.string = text; body.append(paragraph)
                if links:
                    refs = soup.new_tag('p', attrs={'class':'timeline-document-links'})
                    label = soup.new_tag('strong'); label.string = 'Related research and records: '; refs.append(label)
                    for href, name in links.items():
                        link = soup.new_tag('a', href=href); link.string = name; refs.append(link)
                    body.append(refs)
                heading = card.select_one('.hist-title')
                if heading: heading.string = title
            if not historical and identifier in DNA_PROSE:
                for paragraph in body.find_all('p', recursive=False): paragraph.decompose()
                for text in reversed(DNA_PROSE[identifier]):
                    paragraph = soup.new_tag('p'); paragraph.string = text; body.insert(0, paragraph)
            for old in card.select('.timeline-evidence-status'): old.decompose()
            status = soup.new_tag('div', attrs={'class':'timeline-evidence-status'})
            strong = soup.new_tag('strong')
            strong.string = 'Historical context / hypothesis' if historical else 'Genetic evidence / inference'
            status.append(strong)
            status.append('Regional history is not a biography of this ancestor. Proposed routes, roles and identities require independent documentary or ancient-DNA evidence.' if historical else 'SNP relationships and estimated dates describe paternal ancestry. Geographic and surname interpretations do not identify a named historical carrier.')
            body.insert(0, status)
            label = card.select_one('.context-label')
            if label: label.string = 'Historical context' if historical else 'Genetic evidence & inference'
        if identifier == 'R-FT32941':
            for description in row.select('.sis-desc'):
                description.string = 'A Duffield-labelled research branch. Association with Roger de Duffeld or a specific castle is not a genetically demonstrated medieval pedigree.'
            name = row.select_one('.snp-name')
            if name: name.string = 'Duffield / Glasgow connection'
    for identifier in ('R-FTA30932', 'R-FTE32242'):
        for marker in soup.select('.sis-id'):
            if marker.get_text(strip=True) == identifier:
                branch = marker.find_parent(class_='sis-row')
                if branch:
                    branch['id'] = identifier
                    branch['class'] = list(dict.fromkeys(branch.get('class', []) + ['timeline-snp-anchor']))
                break
    return str(soup)
