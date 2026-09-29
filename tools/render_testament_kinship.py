"""Publish manuscript name audits and the maintained early-family synthesis."""
from functools import lru_cache
from html import escape
import json
from pathlib import Path
import re
try:
    from tools.public_manuscript_previews import approved_preview
except ModuleNotFoundError:
    from public_manuscript_previews import approved_preview

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/transcriptions"
REPORT = DATA / "early-families-2026-09-10.json"
URL = "/research/transcriptions/early-families/"
LABELS = {"confirmed": "Confirmed / reconfirmed", "probable": "Probable",
          "unresolved": "Unresolved", "associated": "Associated research material",
          "excluded": "Rejected reading or match"}


def e(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    return escape(str(value or ""), quote=True)


@lru_cache(maxsize=1)
def audits():
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(DATA.glob("name-audit-2026-09-10-*.json"))]


def badge(status):
    status = status if status in LABELS else "unresolved"
    return f'<span class="tx-evidence-label tx-evidence-{status}">{LABELS[status]}</span>'


def findings_for(ident):
    return [item for audit in audits() for item in audit.get("findings", [])
            if item.get("case_id") == ident]


def render_name_audit(ident):
    findings = findings_for(ident)
    if not findings:
        return ""
    items = []
    for item in findings:
        fields = "".join(f'<div><dt>{label}</dt><dd>{e(item[key])}</dd></div>'
                         for key, label in (("previous", "Earlier reading / question"),
                                            ("basis", "Why this reading"),
                                            ("relationship_effect", "Effect on the family")) if item.get(key))
        items.append('<article class="tx-audit-item">' + badge(item.get("status"))
                     + f'<h3>{e(item.get("reading", "Unresolved reading"))}</h3>'
                     + f'<p class="tx-audit-location">{e(item.get("location"))}</p><dl>{fields}</dl></article>')
    return ('<section class="tx-name-audit" id="name-audit" aria-labelledby="name-audit-title">'
            '<header><p class="r-kicker">Second manuscript pass &middot; 10 September 2026</p>'
            '<h2 id="name-audit-title">The names, reconsidered</h2>'
            '<p>New readings and unchanged uncertainties are both recorded. A confirmed name or role '
            'does not by itself confirm a WikiTree identity or a relationship.</p></header>'
            '<details><summary>Read the name and relationship audit '
            f'<span>({len(findings)} findings, not a count of unique people)</span></summary>'
            + "".join(items) + '</details>'
            f'<p><a href="{URL}">See how the evidence fits the early families</a></p></section>')


def feature_link():
    if not REPORT.is_file():
        return ""
    return (f'<a class="tx-kinship-feature" href="{URL}"><span>'
            '<small>From handwriting to family history</small>'
            '<strong>Which early Glasgow families can we actually connect?</strong>'
            '<span>The secure lines, probable relatives and joins still missing a record.</span>'
            '</span><b aria-hidden="true">&rarr;</b></a>')


@lru_cache(maxsize=1)
def followup_reports():
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((DATA / "followup-2026-09-10").glob("*.json"))]


def render_followups():
    reports = followup_reports()
    if not reports:
        return ""
    cards = []
    for report in reports:
        figures = []
        for figure in report.get("figures", []):
            if not isinstance(figure, dict):
                continue
            src = figure.get("src", "")
            if not isinstance(src, str) or not re.fullmatch(
                    r"/assets/research/testament-crops/[A-Za-z0-9._/-]+\.(?:jpg|jpeg|png|webp)", src):
                continue
            caption = e(figure.get("caption"))
            if approved_preview(src):
                alt = e(figure.get("alt"))
                figures.append(f'<figure class="tx-testament-figure"><img src="{e(src)}" alt="{alt}" '
                               'style="max-width:100%;height:auto"><figcaption>'
                               f'{caption}</figcaption></figure>')
            else:
                figures.append('<figure class="tx-testament-figure"><p class="tx-licensed-withheld">'
                               'Licensed scan withheld; consult cited source</p><figcaption>'
                               f'{caption}</figcaption></figure>')
        findings = []
        for finding in report.get("findings", []):
            label = ('<span class="tx-evidence-label tx-evidence-unresolved">'
                     'Does not establish the proposed connection</span>') if finding.get("status") == "excluded" else badge(finding.get("status"))
            source = finding.get("source_url")
            citation = (f'<a href="{e(source)}">{e(finding.get("source_reference", "Record or catalogue"))}</a>'
                        if source else e(finding.get("source_reference", "See the maintained case evidence")))
            kind = "Result of this search" if finding.get("new_this_pass") else "Established evidence rechecked"
            findings.append('<article class="tx-audit-item">' + label
                            + f'<p class="tx-audit-location">{kind}</p><h3>{e(finding["claim"])}</h3>'
                            + f'<p>{e(finding["basis"])}</p><p class="tx-audit-location">{citation}</p></article>')
        searches = "".join(f'<li><strong>{e(item["target"])}</strong><p>{e(item["result"])}</p></li>'
                           for item in report.get("searches", []))
        profiles = " &middot; ".join(f'<a href="https://www.wikitree.com/wiki/{e(ident)}">{e(ident)}</a>'
                                    for ident in report.get("profile_ids", []))
        cards.append(f'<article class="tx-name-audit" id="{e(report["id"])}">'
                     '<header><p class="r-kicker">Targeted record follow-up</p>'
                     f'<h2>{e(report["title"])}</h2><p>{e(report["question"])}</p></header>'
                     + badge(report.get("status")) + f'<p>{e(report["conclusion"])}</p>'
                     + "".join(figures)
                     + '<details><summary>Records, reasoning and search limits</summary>'
                     + "".join(findings) + '<h3>Search log</h3><ul>' + searches + '</ul></details>'
                     f'<aside class="tx-family-next"><h3>Next decisive record</h3><p>{e(report["next_record"])}</p></aside>'
                     + (f'<p class="tx-audit-location">Existing profile comparisons: {profiles}</p>' if profiles else "")
                     + '</article>')
    return ('<section class="tx-family-group" id="research-followup">'
            '<header><div><p class="r-kicker">Continuing the investigation &middot; 10 September 2026</p>'
            '<h2>Following the missing links</h2></div></header>'
            '<p class="tx-family-thesis">These searches test connections between the households, not the '
            'handwriting again. A newly located catalogue or a clearer research target is not a newly proved '
            'relative. Unavailable records are identified rather than counted as negative evidence.</p>'
            + "".join(cards) + '<p><a href="followup-research.json">Download the follow-up evidence and search logs</a></p></section>')


def source_refs(ids):
    return '<p class="tx-source-refs">' + " &middot; ".join(
        f'<a href="#source-{e(ident)}">{e(ident)}</a>' for ident in ids) + '</p>' if ids else ""


def render_family_report(fresh):
    if not REPORT.is_file():
        return ""
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    nav = "".join(f'<a href="#{e(group["id"])}">{e(group["short_title"])}</a>' for group in report["groups"])
    sections = []
    for number, group in enumerate(report["groups"], 1):
        rows = []
        for edge in group.get("relationships", []):
            rows.append('<article class="tx-relationship">' + badge(edge["status"])
                        + f'<h3>{e(edge["people"])}</h3><p>{e(edge["evidence"])}</p>'
                        + (f'<p class="tx-relationship-limit">{e(edge["limit"])}</p>' if edge.get("limit") else "")
                        + source_refs(edge.get("sources", [])) + '</article>')
        cases = "".join(f'<a href="/research/transcriptions/{e(ident)}/#name-audit">'
                        f'{e(fresh.get(ident, {}).get("title", ident))}</a>' for ident in group.get("cases", []))
        profiles = "".join(f'<a href="https://www.wikitree.com/wiki/{e(ident)}">{e(label)} ({e(ident)})</a>'
                           for ident, label in group.get("profiles", []))
        sections.append(f'<section class="tx-family-group" id="{e(group["id"])}">'
                        f'<header><span class="tx-family-number">{number:02d}</span><div>'
                        f'<p class="r-kicker">{e(group["period"])}</p><h2>{e(group["title"])}</h2></div></header>'
                        f'<p class="tx-family-thesis">{e(group["conclusion"])}</p>'
                        '<div class="tx-relationship-grid">' + "".join(rows) + '</div>'
                        f'<aside class="tx-family-next"><h3>The next decisive record</h3><p>{e(group["next_record"])}</p></aside>'
                        + (f'<nav class="tx-family-links" aria-label="{e(group["short_title"])} manuscripts">{cases}</nav>' if cases else "")
                        + (f'<details class="tx-family-profiles"><summary>Profile identities being compared</summary><div>{profiles}</div></details>' if profiles else "")
                        + '</section>')
    scope = sorted({ident for audit in audits() for ident in audit.get("scope", [])})
    audit_links = "".join(f'<li><a href="/research/transcriptions/{e(ident)}/#name-audit">'
                          f'{e(fresh.get(ident, {}).get("title", ident))}</a>'
                          f'<span>{len(findings_for(ident))} findings</span></li>' for ident in scope)
    sources = "".join(f'<li id="source-{e(source["id"])}"><strong>{e(source["id"])}. </strong>'
                      f'<a href="{e(source["url"])}">{e(source["title"])}</a>'
                      f'<p>{e(source["detail"])}</p><small>{e(source["access"])}</small></li>'
                      for source in report["sources"])
    priorities = "".join(f'<li><strong>{e(item["title"])}</strong><p>{e(item["why"])}</p></li>'
                         for item in report["priorities"])
    limitations = "".join(f'<li>{e(item)}</li>' for item in report["limitations"])
    return ('<main class="tx-main tx-kinship" id="main"><nav class="tx-breadcrumb" aria-label="Research trail">'
            '<a href="/research/">Research</a><span>/</span><a href="/research/transcriptions/">Transcriptions</a></nav>'
            '<header class="tx-hero tx-kinship-hero"><p class="r-kicker">Evidence synthesis &middot; 10 September 2026</p>'
            f'<h1>{e(report["title"])}</h1><p>{e(report["intro"])}</p>'
            '<div class="tx-evidence-legend">' + "".join(badge(status) for status in LABELS) + '</div></header>'
            '<aside class="tx-kinship-answer"><h2>The short answer</h2>'
            f'<p>{e(report["answer"])}</p></aside>'
            '<nav class="tx-family-nav" aria-label="Family groups">'
            + ('<a href="#research-followup">Latest record searches</a>' if followup_reports() else "")
            + nav + '</nav>' + render_followups() + "".join(sections)
            + '<section class="tx-family-priorities"><p class="r-kicker">Research with a specific target</p>'
            '<h2>Which records could change the tree?</h2><ol>' + priorities + '</ol></section>'
            '<section class="tx-audit-directory" id="all-name-audits"><p class="r-kicker">Back to the handwriting</p>'
            f'<h2>{len(scope)} cases reconsidered</h2><p>The audit includes creditors, witnesses, executors and '
            'unresolved names, not just people already placed in the family tree. Findings include reconfirmations; '
            'they are not all newly discovered people.</p><ul>' + audit_links + '</ul>'
            '<p><a href="name-audit.json">Download the full name audit (JSON)</a> &middot; '
            '<a href="research-notes.md">Read the research handoff (Markdown)</a></p></section>'
            '<section class="tx-kinship-limits"><h2>What this pass does not establish</h2><ul>' + limitations + '</ul></section>'
            '<section class="tx-kinship-sources"><h2>Records behind the reconstruction</h2><ol>' + sources + '</ol></section>'
            '<p class="tx-back"><a href="/research/transcriptions/">Back to the manuscript collection</a></p></main>')


def publish_family_report(write, shell, template, fresh, output):
    body = render_family_report(fresh)
    if body:
        write(output / "early-families/index.html", shell(template, body, "Reconstructing the early Glasgow families", URL + "index.html"))
        write(output / "early-families/name-audit.json", json.dumps(audits(), indent=2, ensure_ascii=False) + "\n")
        if followup_reports():
            write(output / "early-families/followup-research.json", json.dumps(followup_reports(), indent=2, ensure_ascii=False) + "\n")
        notes = DATA / "early-families-2026-09-10.md"
        if notes.is_file():
            write(output / "early-families/research-notes.md", notes.read_text(encoding="utf-8"))
