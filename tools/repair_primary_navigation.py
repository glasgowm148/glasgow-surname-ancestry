#!/usr/bin/env python3
"""Keep tree exploration and family browsing as separate primary destinations."""
from collections import Counter
from pathlib import Path
import re

WEB = Path(__file__).resolve().parents[1] / 'www'
NAV = re.compile(r'<nav\b(?=[^>]*\bclass="[^"]*\bg-nav\b[^"]*")[^>]*>.*?</nav>', re.S)
ATLAS = re.compile(r'<a\b(?=[^>]*\bhref="/onetree/")[^>]*>.*?</a>', re.S)
FAMILIES = re.compile(r'<a\b(?=[^>]*\bhref="/branches/")[^>]*>.*?</a>', re.S)
RECORDS = re.compile(r'<a\b(?=[^>]*\bhref="/(?:sources|records)/")[^>]*>.*?</a>', re.S)
RESEARCH = re.compile(r'<a\b(?=[^>]*\bhref="/research/")[^>]*>.*?</a>', re.S)
TRANSCRIPTIONS = re.compile(r'<a\b(?=[^>]*\bhref="/research/transcriptions/")[^>]*>.*?</a>', re.S)
STATISTICS = re.compile(r'<a\b(?=[^>]*\bhref="/statistics/")[^>]*>.*?</a>', re.S)
RESOURCES = re.compile(r'<a\b(?=[^>]*\bhref="/resources/")[^>]*>.*?</a>', re.S)
SECTION_NAV = re.compile(r'<nav\b(?=[^>]*\bclass="[^"]*\bv3-view-nav\b[^"]*")[^>]*>.*?</nav>', re.S)
ICON = '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="3"></circle><path d="M12 8v5M5 17v-4h14v4"></path><circle cx="5" cy="20" r="2"></circle><circle cx="19" cy="20" r="2"></circle></svg>'
PERSON_FOOTER = '<footer class="g-footer"><div><span class="g-footer-name">The Glasgow Surname Project</span><p>A shared research collection. Profile links and hypotheses are kept distinct from the evidence behind them.</p></div><nav class="g-footer-links" aria-label="Project information"><a href="/about/">About the project</a><a href="/catalogue/">Browse people</a><a href="/research/">Research workspace</a><a href="/changes/">Latest research</a><a href="/feedback/">Suggest a correction &nearr;</a></nav></footer>'


def repair():
    changed = Counter()
    for extension in ('js', 'css'):
        source = WEB.parent / 'tools' / f'section_submenus.{extension}'
        target = WEB / 'assets/unified' / f'section-submenus.{extension}'
        content = source.read_text(encoding='utf-8')
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            target.write_text(content, encoding='utf-8')
            changed['section_submenus'] += 1
    for path in WEB.rglob('*.html'):
        relative = path.relative_to(WEB)
        if 'glasgow-ydna-story-source' in relative.parts or path.name.endswith('-standalone.html'):
            continue
        page = path.read_text(encoding='utf-8')
        family_page = relative.parts[0] == 'branches'
        records_page = relative.parts[0] in {'sources', 'records', 'events'}
        transcription_page = relative.parts[:2] == ('research', 'transcriptions')
        statistics_page = relative.parts[0] == 'statistics'
        resources_page = relative.parts[0] == 'resources'

        def navigation(match):
            nav = RECORDS.sub('', match.group(0))
            nav = STATISTICS.sub('', nav)
            nav = RESOURCES.sub('', nav)
            if statistics_page or resources_page:
                nav = re.sub(r'\s+aria-current="[^"]*"', '', nav)
            current_statistics = ' aria-current="page"' if statistics_page else ''
            statistics = f'<a class="g-nav-link" href="/statistics/"{current_statistics}><svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3v17h17M8 16v-5M13 16V6M18 16V9"></path></svg><span>Statistics</span></a>'
            nav = RESEARCH.sub(lambda m: m[0] + statistics, nav, count=1)
            current_resources = ' aria-current="page"' if resources_page else ''
            resources = f'<a class="g-nav-link" href="/resources/"{current_resources}><svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h7l2 2 2-2h7v15h-7l-2 2-2-2H3zM12 7v15"></path></svg><span>Resources</span></a>'
            nav = STATISTICS.sub(lambda m: m[0] + resources, nav, count=1)
            if records_page or transcription_page:
                nav = re.sub(r'\s+aria-current="[^"]*"', '', nav)
                nav = RESEARCH.sub(lambda m: m[0].replace('<a ', '<a aria-current="page" ', 1), nav, count=1)
            if not ATLAS.search(nav):
                return nav
            nav = FAMILIES.sub('', nav)
            current = ' aria-current="page"' if family_page else ''
            family = f'<a class="g-nav-link" href="/branches/"{current}>{ICON}<span>Families</span></a>'

            def atlas(link):
                text = link.group(0).replace('Family Atlas', 'Atlas')
                if family_page:
                    text = re.sub(r'\s+aria-current="[^"]*"', '', text)
                return text + family

            return ATLAS.sub(atlas, nav, count=1)

        updated = NAV.sub(navigation, page)
        # Fresh catalogue builds use a compact legacy header rather than the
        # unified g-nav shell. Keep the same primary destinations available
        # until the full shell can be restored from an archival template.
        if not NAV.search(updated):
            def compact_navigation(match):
                nav = match.group(0)
                if 'href="/statistics/"' not in nav:
                    nav = nav.replace('</nav>', '<a class="g-nav-link" href="/statistics/">Statistics</a></nav>', 1)
                if 'href="/resources/"' not in nav:
                    nav = nav.replace('</nav>', '<a class="g-nav-link" href="/resources/">Resources</a></nav>', 1)
                return nav
            updated = re.sub(r'<header>\s*<a\b[^>]*class="brand"[\s\S]*?<nav>.*?</nav>', compact_navigation, updated, count=1)

        def sections(match):
            # Legacy secondary bars repeated unrelated primary destinations.
            # Purpose-built local controls use separate markup and are retained.
            return ""

        updated = SECTION_NAV.sub(sections, updated)
        if relative.parts[0] == 'people' and '<footer' not in updated:
            updated = updated.replace('</main>', '</main>' + PERSON_FOOTER, 1)
        def footer_links(match):
            footer = match.group(0)
            if not re.search(r'href="/changes(?:/|\.html)"', footer):
                footer = footer.replace('</nav>', '<a href="/changes/">Latest research</a></nav>', 1)
            footer = re.sub(r'(<a\b[^>]*href="/changes(?:/|\.html)"[^>]*>)Change log(</a>)', r'\1Latest research\2', footer)
            for url, label in (
                ('https://www.wikitree.com/wiki/Space:Glasgow_Name_Study', 'WikiTree Name Study'),
                ('https://groups.io/g/glasgowdnaproject/', 'Discussion group'),
            ):
                if f'href="{url}"' not in footer:
                    footer = footer.replace('</nav>', f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label} &nearr;</a></nav>', 1)
            return footer

        updated = re.sub(
            r'<nav\b(?=[^>]*\bclass="[^"]*\bg-footer-links\b[^"]*")[^>]*>.*?</nav>',
            footer_links, updated, flags=re.S,
        )
        if not re.search(r'href="/changes/"', updated):
            latest = '<a href="/changes/">Latest research</a>'
            if '</footer>' in updated:
                updated = updated.replace('</footer>', latest + '</footer>', 1)
        if NAV.search(updated):
            if '/assets/unified/section-submenus.css' not in updated:
                updated = updated.replace('</head>', '<link rel="stylesheet" href="/assets/unified/section-submenus.css?v=2"></head>', 1)
            if '/assets/unified/section-submenus.js' not in updated:
                updated = updated.replace('</body>', '<script src="/assets/unified/section-submenus.js?v=2" defer></script></body>', 1)
        if relative.as_posix() == 'research/index.html' and 'class="repair-transcriptions-card"' not in updated:
            card = '<a class="repair-research-card repair-transcriptions-card" href="/research/transcriptions/"><h2>Wills &amp; testament transcriptions</h2><p>Read the latest saved LLM-assisted readings, linked profiles, source references and unresolved passages.</p><span>Explore the transcriptions &rarr;</span></a>'
            if 'repair-transcriptions-card"' not in updated:
                updated = updated.replace('<div class="repair-research-grid">', '<div class="repair-research-grid">' + card, 1)
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['primary_navigation'] += 1
    return changed


if __name__ == '__main__':
    print(dict(repair()))
