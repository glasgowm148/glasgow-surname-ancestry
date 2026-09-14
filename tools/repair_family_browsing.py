#!/usr/bin/env python3
"""Regional, evidence-labelled entry cards for the Families & places index."""
from collections import Counter
from html import escape
from pathlib import Path
import json
import runpy
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
GROUP_DATA = runpy.run_path(str(ROOT / "tools/repair_research_groups.py"))
GROUPS = {item["id"]: item for item in GROUP_DATA["GROUPS"] + GROUP_DATA["IRISH_GROUPS"]}

REGIONS = (
    ("Ireland & Ulster", "/branches/early-ireland/", "826 people · 986 record associations"),
    ("Scotland", "/branches/scottish-families/", "1,207 people · 1,260 record associations"),
    ("United States & Canada", "/branches/north-american-families/", "2,241 people · 2,264 record associations"),
    ("Australia & New Zealand", "/branches/australasian-families/", "291 people · 291 record associations"),
    ("England & Wales", "/branches/english-welsh-families/", "93 people · 93 record associations"),
    ("Other places & unresolved locations", "/branches/other-family-places/", "2,371 people · 2,490 record associations"),
)

CSS = '''/* Families index: short regional entry points and evidence-led study cards. */
.family-region-nav{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}.family-region-nav a{padding:8px 11px;border:1px solid #cbd8c0;border-radius:999px;color:#36593e;background:#f6f8f1;font:600 11px var(--g-sans);text-decoration:none}.family-region-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,205px),1fr));gap:12px;margin:16px 0 34px}.family-region-card{display:block;min-height:112px;padding:17px;border:1px solid #cbd7c0;border-radius:9px;background:linear-gradient(135deg,#f8f8ef,#edf2e7);color:#284b36;text-decoration:none}.family-region-card span{display:block;color:#52634d;font:700 9px var(--g-sans);letter-spacing:.12em;text-transform:uppercase}.family-region-card h2{margin:8px 0 11px;font:500 22px/1.1 var(--g-serif)}.family-region-card small{color:#52664e;font:11px var(--g-sans)}.family-study-region{margin:38px 0}.family-study-region>header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;border-bottom:1px solid #d3ddca;padding-bottom:10px}.family-study-region h2{margin:0;font:500 30px/1.1 var(--g-serif);color:#294b37}.family-study-region header span{font:10px var(--g-sans);color:#52634d}.family-study-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:12px;margin-top:16px}.family-study-card{display:block;padding:15px;border:1px solid #d0dac7;border-radius:8px;background:#fcfcf8;color:#304c39;text-decoration:none}.family-study-card:hover,.family-study-card:focus-visible{border-color:#739168;outline:2px solid #b8cda9;outline-offset:2px}.family-study-status{display:inline-block;padding:3px 6px;border-radius:3px;background:#e5eedc;color:#42633e;font:700 9px var(--g-sans);letter-spacing:.06em;text-transform:uppercase}.family-study-card h3{margin:10px 0 6px;font:500 21px/1.15 var(--g-serif)}.family-study-where{display:block;color:#52634d;font:10px/1.4 var(--g-sans)}.family-study-question{margin:10px 0 0;color:#52634d;font:12px/1.5 var(--g-sans)}.family-study-question strong{color:#34543b}@media(max-width:700px){.family-region-grid{grid-template-columns:1fr}.family-study-region h2{font-size:26px}.family-study-region>header{align-items:flex-start;flex-direction:column;gap:4px}}\n'''


def status(group):
    boundary = group["boundary"].lower()
    if "reconstructed" in boundary:
        return "Reconstructed branch"
    if "network" in boundary or "locality" in boundary or "occurrence" in boundary or "trade cluster" in boundary:
        return "Locality / record cluster"
    if "documented" in boundary or "directly stated" in boundary or "testament household" in boundary:
        return "Documented household"
    return "Evidence-led study"


def study_card(entry, registry):
    group = GROUPS[entry["id"]]
    people = [registry[slug]["name"] for slug in entry["members"][:2] if slug in registry]
    key_people = ", ".join(people) if people else "Named local record subjects"
    return (f'<a class="family-study-card" href="{escape(entry["url"], quote=True)}">'
            f'<span class="family-study-status">{escape(status(group))}</span><h3>{escape(entry["label"])}</h3>'
            f'<span class="family-study-where">{escape(key_people)} · {entry["from"]}–{entry["to"]} · {escape(group["place"])}</span>'
            f'<p class="family-study-question"><strong>Open:</strong> {escape(entry["question"])}</p></a>')


def replace_section(text, section_id, heading, entries, registry):
    cards = "".join(study_card(entry, registry) for entry in entries)
    section = (f'<section id="{section_id}" class="family-study-region"><header><div><span class="r-kicker">Evidence-led study</span>'
               f'<h2>{heading}</h2></div><span>{len(entries)} studies</span></header><div class="family-study-grid">{cards}</div></section>')
    return re.sub(r'<section id="' + re.escape(section_id) + r'".*?</section>', section, text, count=1, flags=re.S)


def repair_montgreenan():
    """Keep the Scottish family guide aligned with the maintained estate case."""
    path = WEB / "branches/scottish-families/index.html"
    before = text = path.read_text(encoding="utf-8")
    section = '''<section id="montgreenan-family"><h2>Montgreenan and St Vincent</h2>
<p><a href="/people/glasgow-1076.html">Robert Glasgow of Montgreenan (Glasgow-1076)</a> connects the Ayrshire estate to plantation wealth extracted from enslaved labour on St Vincent. His family account also needs to distinguish estate succession from paternal descent.</p>
<p>UCL's published account of his 1803 trust names children John and Emilia, and its succession research identifies Anne as his natural daughter and heir. The older statement that he died without issue cannot be repeated without qualification. The Robertson successor took the Glasgow name through Anne's marriage; that surname condition does not establish a Glasgow paternal line. <a href="https://wwwdepts-live.ucl.ac.uk/lbs/person/view/2146643739">UCL's trust research</a> and <a href="https://wwwdepts-live.ucl.ac.uk/lbs/person/view/27300">succession account</a> provide the archival references.</p>
<p><strong>Original-record review pending.</strong> Compare SC6/44/4 and SC6/44/4/1 with the existing child profiles, then inspect the St Vincent registers T71/493, pages 591–592, and T71/495, page 54. The Emilia/Amelia identity and the proposed family relationships of the enslaved household remain unresolved.</p></section>'''
    text = re.sub(r'<section id="montgreenan-family">.*?</section>', '', text, flags=re.S)
    anchor = '<section><h2>Explore the connected families</h2>'
    if anchor not in text:
        raise ValueError("Scottish family guide insertion point missing")
    text = text.replace(anchor, section + anchor, 1)
    if text != before:
        path.write_text(text, encoding="utf-8")
        return Counter(montgreenan_family=1)
    return Counter()


def repair():
    changed = Counter()
    registry = {item["slug"]: item for item in json.loads((WEB / "assets/research/registry.json").read_text())}
    entries = [item for item in json.loads((WEB / "assets/research/branches.json").read_text()) if item.get("curatedResearch")]
    scottish = [item for item in entries if not GROUPS[item["id"]].get("irish")]
    irish = [item for item in entries if GROUPS[item["id"]].get("irish")]
    regions = ''.join(f'<a class="family-region-card" href="{url}"><span>Browse region</span><h2>{label}</h2><small>{count}</small></a>' for label, url, count in REGIONS)
    region_section = '<section id="experience-regions"><span class="r-kicker">Browse by place</span><h2>Start with a region</h2><div class="family-region-grid">' + regions + '</div></section>'
    path = WEB / "branches/index.html"
    text = path.read_text()
    text = re.sub(r'<section id="experience-regions">.*?</section>', region_section, text, count=1, flags=re.S)
    text = replace_section(text, "research-studies", "Scottish research studies", scottish, registry)
    text = replace_section(text, "irish-research-studies", "Ireland & Ulster research studies", irish, registry)
    text = re.sub(r'<nav class="family-region-nav"[^>]*>.*?</nav>', '', text, flags=re.S)
    nav = '<nav class="family-region-nav" aria-label="Browse family studies"><a href="#experience-regions">Regions</a><a href="#research-studies">Scotland studies</a><a href="#irish-research-studies">Ireland &amp; Ulster studies</a><a href="#r-branch-results">Find a family</a></nav>'
    text = re.sub(r'(<main\b[^>]*>\s*<header\b[^>]*>.*?</header>)', r'\1' + nav, text, count=1, flags=re.S)
    text = re.sub(r'(<p id="r-branch-count" role="status">.*?</p>)(?:<div id="r-branch-pages"[^>]*></div>)?', r'\1<div id="r-branch-pages" class="r-pager" aria-label="Family results pages"></div>', text, count=1, flags=re.S)
    stylesheet = '<link rel="stylesheet" href="/assets/research/family-browsing.css?v=2">'
    text = re.sub(r'<link rel="stylesheet" href="/assets/research/family-browsing\.css\?v=\d+">', stylesheet, text, count=1)
    if stylesheet not in text:
        text = text.replace('</head>', stylesheet + '</head>', 1)
    text = re.sub(r'src="/assets/research/views\.js\?v=[^"]+"', 'src="/assets/research/views.js?v=3.1-family-pagination-1"', text, count=1)
    if text != path.read_text():
        path.write_text(text)
        changed["family_browsing"] += 1
    css_path = WEB / "assets/research/family-browsing.css"
    if not css_path.exists() or css_path.read_text() != CSS:
        css_path.write_text(CSS)
        changed["family_browsing"] += 1
    changed.update(repair_montgreenan())
    return changed


if __name__ == "__main__":
    print(dict(repair()))
