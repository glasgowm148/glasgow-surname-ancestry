#!/usr/bin/env python3
"""Build the public statistics page from the maintained catalogue pane."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'


def repair():
    catalogue = (WEB / 'catalogue/index.html').read_text(encoding='utf-8')
    shell = (WEB / 'research/index.html').read_text(encoding='utf-8')
    block = re.search(
        r'<section class="catalogue-statistics" id="statistics">(.*?)</section></details><section class="catalogue-browse"',
        catalogue, re.S)
    if not block:
        raise RuntimeError('Could not locate the maintained catalogue statistics pane')
    statistics = block.group(1)
    summary = re.search(r'<div class="statistics-summary">.*?</div>(?=\s*<details\b)', statistics, re.S)
    detail = re.search(
        r'<details id="statistics-detail">.*?<div class="statistics-grid">(.*)</div><p class="statistics-caution">(.*?)</p></details>',
        statistics, re.S)
    if not summary or not detail:
        raise RuntimeError('Could not locate the maintained statistics summary or detail panels')
    panels, caution = detail.groups()
    panels = re.sub(r'href="(people/|places/)', r'href="/\1', panels)
    panels = panels.replace('/catalogue.html?', '/catalogue/?')
    main = '''<main class="r-main statistics-page" id="main"><header class="v3-page-head statistics-page-head"><span class="r-kicker">The collection, at a glance</span><h1>Statistics from the<br>public historical catalogue.</h1><p>Counts are drawn from the maintained catalogue snapshot. They describe records and documented associations, not a proved single family tree.</p></header><section class="statistics-page-summary" aria-label="Catalogue summary">''' + summary.group(0) + '''</section><section class="statistics-page-panels" aria-labelledby="statistics-detail-title"><div class="statistics-page-intro"><span class="r-kicker">Patterns in the collection</span><h2 id="statistics-detail-title">Places, names, branches and movement</h2><p>Each panel remains linked back to the relevant catalogue or place view.</p></div><div class="statistics-grid">''' + panels + '''</div><p class="statistics-caution">''' + caution + '''</p></section></main>'''
    shell = re.sub(r'<title>.*?</title>', '<title>Catalogue statistics · Glasgow surname archive</title>', shell, count=1, flags=re.S)
    shell = re.sub(r'<meta content="The Glasgow surname archive:[^"]*" name="description">', '<meta content="Statistics from the public historical catalogue: places, names, branches and recorded movement." name="description">', shell, count=1)
    shell = shell.replace('data-g-path="/research/index.html"', 'data-g-path="/statistics/index.html"')
    shell = shell.replace('<strong>Research</strong>', '<strong>Statistics</strong>', 1)
    shell = re.sub(r'<nav class="v3-view-nav" aria-label="Section views">.*?</nav>', '', shell, count=1, flags=re.S)
    shell = re.sub(r'<main class="r-main" id="main">.*?</main>', main, shell, count=1, flags=re.S)
    shell = shell.replace('</head>', '<link rel="stylesheet" href="/assets/repair/statistics.css?v=2"></head>', 1)
    output = WEB / 'statistics/index.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    before = output.read_text(encoding='utf-8') if output.exists() else None
    if before != shell:
        output.write_text(shell, encoding='utf-8')
        return {'statistics_page': 1}
    return {}


if __name__ == '__main__':
    print(repair())
