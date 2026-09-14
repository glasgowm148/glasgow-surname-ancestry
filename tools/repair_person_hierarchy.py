"""Render person dossiers as an evidence-led reading experience.

The catalogue builder and the unified-site repair both use this presentation
layer. Imported fields, scores and raw captures remain available in the
archive but do not compete with the maintained assessment.
"""
from __future__ import annotations

from collections import defaultdict
from html import escape
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

try:
    from publish_resolved_dossiers import publish
except ModuleNotFoundError:
    from tools.publish_resolved_dossiers import publish

try:
    from dossier_resolution import assessment_coverage, resolve_presentation
except ModuleNotFoundError:  # imported as tools.repair_person_hierarchy in tests
    from tools.dossier_resolution import assessment_coverage, resolve_presentation

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
PRESENTATION_VERSION = "25"
ASSET = f"/assets/repair/person-hierarchy.css?v={PRESENTATION_VERSION}"
_INDEX_CACHE: dict[str, dict] | None = None

CSS = r"""
.person-hierarchy .dossier-header{padding:12px 0 28px;border-bottom:1px solid var(--g-line,#cbd7c5)}
.person-hierarchy .dossier-header h1{max-width:18ch;margin:.15em 0 .08em}
.person-hierarchy .dossier-life{font:500 1.18rem/1.35 var(--g-serif,Georgia,serif);color:#536350;margin:.2rem 0}
.person-hierarchy .dossier-locality{font-size:1rem;color:#536350;margin:.4rem 0;max-width:72ch}
.person-hierarchy .dossier-meta{display:flex;gap:12px 20px;flex-wrap:wrap;color:#667466;font-size:.78rem}.person-hierarchy .dossier-meta a{font-weight:700}
.person-hierarchy .dossier-actions{display:flex;gap:9px;flex-wrap:wrap;margin:17px 0 0}.person-hierarchy .dossier-actions a{min-height:36px;display:inline-flex;align-items:center}
.person-hierarchy .dossier-nav{display:none;gap:8px;flex-wrap:wrap;margin:18px 0 0;padding:9px 0;position:sticky;top:0;z-index:4;background:color-mix(in srgb,var(--g-paper,#f8f8f0) 94%,transparent);border-bottom:1px solid var(--g-line,#cbd7c5)}
.person-hierarchy .dossier-nav a{padding:6px 9px;border:1px solid #c5d1c0;border-radius:5px;font-size:.78rem;text-decoration:none}
.person-hierarchy .dossier-layout{display:grid;grid-template-columns:minmax(180px,210px) minmax(0,1fr);gap:38px;align-items:start}.person-hierarchy .dossier-toc{position:sticky;top:61px;padding-top:34px}
.person-hierarchy .dossier-toc a{display:block;padding:7px 8px;border-left:2px solid transparent;font-size:.82rem;text-decoration:none}.person-hierarchy .dossier-toc a:hover,.person-hierarchy .dossier-toc a:focus-visible{border-left-color:#67845e;background:#edf2e8}
.person-hierarchy .dossier-reading{min-width:0;max-width:920px}.person-hierarchy .dossier-section{scroll-margin-top:78px;padding:34px 0;border-bottom:1px solid var(--g-line,#d4ddce)}
.person-hierarchy .dossier-section>h2{margin:0 0 14px;font:600 clamp(1.4rem,2.4vw,2rem)/1.2 var(--g-serif,Georgia,serif);color:#304b37}.person-hierarchy .dossier-section>h3{margin:26px 0 8px;font:600 1.06rem/1.3 var(--g-serif,Georgia,serif);color:#3c5c43}
.person-hierarchy .dossier-lede,.person-hierarchy .dossier-position{max-width:74ch;font-size:1.05rem;line-height:1.65}.person-hierarchy .dossier-facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:22px 0 0;border-top:1px solid #ccd6c8;border-bottom:1px solid #ccd6c8}
.person-hierarchy .dossier-fact{padding:12px 14px;border-right:1px solid #d8e0d3}.person-hierarchy .dossier-fact:last-child{border-right:0}.person-hierarchy .dossier-fact strong,.person-hierarchy .dossier-fact span{display:block}.person-hierarchy .dossier-fact strong{font:600 1rem var(--g-serif,Georgia,serif);color:#334d39}.person-hierarchy .dossier-fact span{font-size:.8rem;color:#657266;margin-top:4px}
.person-hierarchy .position-list{padding-left:20px;max-width:76ch}.person-hierarchy .position-list li{margin:7px 0}.person-hierarchy .status-label{display:inline-block;padding:2px 6px;border:1px solid #aab9a5;border-radius:4px;color:#536351;font-size:.68rem;font-weight:750;text-transform:uppercase;letter-spacing:.04em}.person-hierarchy .status-documented,.person-hierarchy .status-strongly-supported{border-color:#5f9174;color:#2d6848}.person-hierarchy .status-uncertain,.person-hierarchy .status-possible,.person-hierarchy .status-estimated{border-color:#b29b52;color:#765d16}.person-hierarchy .status-unassessed,.person-hierarchy .status-tree-derived{border-color:#a9b3ad;color:#65736a}.person-hierarchy .status-superseded{border-color:#b68181;color:#814545}
.person-hierarchy .relation-group{margin:24px 0}.person-hierarchy .relation-group h3{margin-top:0}.person-hierarchy .relation-table,.person-hierarchy .evidence-table,.person-hierarchy .source-table{width:100%;border-collapse:collapse;font-size:.88rem}.person-hierarchy .relation-table th,.person-hierarchy .relation-table td,.person-hierarchy .evidence-table th,.person-hierarchy .evidence-table td,.person-hierarchy .source-table th,.person-hierarchy .source-table td{padding:11px 12px;border-bottom:1px solid #d5ded1;text-align:left;vertical-align:top}.person-hierarchy .relation-table th,.person-hierarchy .evidence-table th,.person-hierarchy .source-table th{background:#edf2e8;color:#3e5943;font-size:.74rem;letter-spacing:.04em;text-transform:uppercase}.person-hierarchy .relation-table td:first-child{min-width:165px}.person-hierarchy .relation-table td:nth-child(2){min-width:135px}.person-hierarchy .relation-table td p,.person-hierarchy .evidence-table td p{margin:0 0 7px}.person-hierarchy .relation-note,.person-hierarchy .source-limit,.person-hierarchy .archive-note{color:#617064;font-size:.84rem}.person-hierarchy .relation-table tr[data-state="uncertain"],.person-hierarchy .relation-table tr[data-state="tree-derived"]{background:#fbfaf1}.person-hierarchy .relation-table tr[data-state="superseded"]{background:#faf5f3}
.person-hierarchy .question{margin:25px 0;padding:18px 20px;border-left:3px solid #78936e;background:#f5f7ef}.person-hierarchy .question h3{margin:0 0 9px;color:#304b37}.person-hierarchy .question p{max-width:76ch;line-height:1.6}.person-hierarchy .question .answer{font-size:1rem}.person-hierarchy .question .argument-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:15px}.person-hierarchy .argument-grid>div{padding-top:10px;border-top:1px solid #d0daca}.person-hierarchy .argument-grid strong{display:block;color:#536753;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px}
.person-hierarchy .evidence-table{margin-top:13px;background:#fff}.person-hierarchy .evidence-table th{font-size:.7rem}.person-hierarchy .evidence-table td:first-child{min-width:145px}.person-hierarchy .evidence-table td:nth-child(2),.person-hierarchy .evidence-table td:nth-child(3){min-width:210px}.person-hierarchy .evidence-table td:nth-child(4){min-width:180px}
.person-hierarchy .biography-content{max-width:76ch;font-size:1rem;line-height:1.65}.person-hierarchy .biography-content h3{margin:1.5em 0 .5em}.person-hierarchy .biography-table-wrap{max-width:100%;overflow-x:auto;margin:1.2em 0}.person-hierarchy .biography-content .biography-table{width:100%;border-collapse:collapse;background:#fffefa;color:#263b2d;font-size:.88rem}.person-hierarchy .biography-content .biography-table caption{caption-side:top;text-align:left;padding:0 0 8px;font-weight:700;color:#3e5943}.person-hierarchy .biography-content .biography-table tr{background:#fffefa;color:#263b2d}.person-hierarchy .biography-content .biography-table th,.person-hierarchy .biography-content .biography-table td{padding:10px 12px;border-bottom:1px solid #d5ded1;text-align:left;vertical-align:top;overflow-wrap:anywhere;background:#fffefa;color:#263b2d}.person-hierarchy .biography-content .biography-table th{background:#edf2e8;color:#3e5943;font-size:.76rem}
.person-hierarchy .timeline-group{margin:24px 0}.person-hierarchy .timeline-row{display:grid;grid-template-columns:110px minmax(0,1fr);gap:18px;padding:15px 0;border-top:1px solid #d7dfd3}.person-hierarchy .timeline-row time{font-weight:750;color:#60755c}.person-hierarchy .timeline-row h3{margin:0 0 4px;font-size:1rem}.person-hierarchy .timeline-row p{margin:4px 0;max-width:76ch}.person-hierarchy .timeline-row .timeline-role{color:#536953;font-size:.8rem;font-weight:700}.person-hierarchy .timeline-row .timeline-meta{color:#6b786c;font-size:.82rem}.person-hierarchy .timeline-row.is-context{background:linear-gradient(90deg,#fafaf4,transparent);padding-left:10px}
.person-hierarchy .task-list{display:grid;gap:11px;padding:0;list-style:none}.person-hierarchy .task{padding:14px 16px;border:1px solid #d1dccb;background:#fafbf6}.person-hierarchy .task-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.person-hierarchy .task-head strong{color:#304b37}.person-hierarchy .task p{margin:6px 0;max-width:77ch}.person-hierarchy .task-label{font-size:.72rem;color:#657463;text-transform:uppercase;letter-spacing:.04em}.person-hierarchy .research-log{font-size:.88rem}.person-hierarchy .research-log td:first-child{white-space:nowrap;font-weight:700;color:#5d705a}
.person-hierarchy .source-table td:first-child{min-width:190px}.person-hierarchy .source-table td:nth-child(2){min-width:110px}.person-hierarchy .source-table a{overflow-wrap:anywhere}.person-hierarchy .source-register{counter-reset:source;list-style:none;padding:0}.person-hierarchy .source-register>li{counter-increment:source;padding:14px 0 14px 35px;border-top:1px solid #d5ded1;position:relative}.person-hierarchy .source-register>li::before{content:counter(source);position:absolute;left:0;top:15px;color:#6f8468;font-weight:800}.person-hierarchy .source-register h3{margin:0 0 4px;font-size:1rem}.person-hierarchy .source-register p{margin:4px 0;max-width:76ch;font-size:.88rem}.person-hierarchy .source-claims{font-size:.8rem;color:#617064}.person-hierarchy .source-links{display:flex;flex-wrap:wrap;gap:5px 11px;margin-top:6px;font-size:.8rem}
.person-hierarchy .archive-original{margin-top:16px;background:#eef2e9}.person-hierarchy .archive-original summary{font-size:.82rem}.person-hierarchy .archive-copy h1,.person-hierarchy .archive-copy h2,.person-hierarchy .archive-copy h3{margin-top:1.2em}.person-hierarchy .archive-copy table{border-collapse:collapse;width:100%;font-size:.85rem}.person-hierarchy .archive-copy th,.person-hierarchy .archive-copy td{border:1px solid #d0dacb;padding:7px;text-align:left;vertical-align:top}.person-hierarchy .archive-copy th{background:#e8eee3}.person-hierarchy .dossier-archive{border-top:1px solid #bfcbb9;margin-top:34px;padding-top:10px}.person-hierarchy .dossier-archive>summary{font:600 1.05rem var(--g-serif,Georgia,serif);color:#3a5640}.person-hierarchy .dossier-archive .archive-body{padding:5px 0 18px}.person-hierarchy .dossier-archive details{margin:12px 0;background:#f5f7ef;border-color:#d2ddcc}.person-hierarchy .dossier-archive details summary{font-size:.88rem}.person-hierarchy .archive-copy{font-size:.87rem;line-height:1.6}.person-hierarchy .archive-copy pre,.person-hierarchy .archive-copy textarea{max-width:100%;overflow:auto;white-space:pre-wrap;font:12px/1.5 ui-monospace,monospace;background:#eef2e9;padding:12px;border:1px solid #d0dacb}.person-hierarchy .archive-json{font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:32rem;overflow:auto}.person-hierarchy .dossier-empty{padding:14px;background:#f5f7ef;color:#617064}.person-hierarchy a:focus-visible,.person-hierarchy summary:focus-visible{outline:3px solid #b68425;outline-offset:3px}
@media(max-width:900px){.person-hierarchy .dossier-nav{display:flex;position:static}.person-hierarchy .dossier-layout{display:block}.person-hierarchy .dossier-toc{display:none}.person-hierarchy .dossier-reading{max-width:none}}
@media(max-width:680px){.person-hierarchy .dossier-facts{grid-template-columns:repeat(2,minmax(0,1fr))}.person-hierarchy .dossier-fact:nth-child(2){border-right:0}.person-hierarchy .dossier-fact:nth-child(n+3){border-top:1px solid #d8e0d3}.person-hierarchy .question .argument-grid{grid-template-columns:1fr}.person-hierarchy .evidence-table,.person-hierarchy .source-table,.person-hierarchy .relation-table{display:block;overflow-x:auto}.person-hierarchy .evidence-table thead,.person-hierarchy .source-table thead,.person-hierarchy .relation-table thead{display:none}.person-hierarchy .evidence-table tr,.person-hierarchy .source-table tr,.person-hierarchy .relation-table tr{display:block;padding:10px 0;border-bottom:1px solid #d5ded1}.person-hierarchy .evidence-table td,.person-hierarchy .source-table td,.person-hierarchy .relation-table td{display:block;border:0;padding:5px 10px;min-width:0!important}.person-hierarchy .evidence-table td::before,.person-hierarchy .source-table td::before,.person-hierarchy .relation-table td::before,.person-hierarchy .biography-table td::before{display:block;color:#657463;font-size:.68rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin-bottom:2px}.person-hierarchy .relation-table td:nth-child(1)::before{content:'Person and dates'}.person-hierarchy .relation-table td:nth-child(2)::before{content:'Relationship'}.person-hierarchy .relation-table td:nth-child(3)::before{content:'Current assessment'}.person-hierarchy .relation-table td:nth-child(4)::before{content:'Why shown'}.person-hierarchy .evidence-table td:nth-child(1)::before{content:'Record'}.person-hierarchy .evidence-table td:nth-child(2)::before{content:'What it says'}.person-hierarchy .evidence-table td:nth-child(3)::before{content:'Why it matters'}.person-hierarchy .evidence-table td:nth-child(4)::before{content:'Limitation'}.person-hierarchy .source-table td:nth-child(1)::before{content:'Source'}.person-hierarchy .source-table td:nth-child(2)::before{content:'Record and repository'}.person-hierarchy .source-table td:nth-child(3)::before{content:'Supports'}.person-hierarchy .source-table td:nth-child(4)::before{content:'Limitations'}.person-hierarchy .biography-table{display:block;font-size:.9rem}.person-hierarchy .biography-table thead{display:none}.person-hierarchy .biography-table tr{display:block;padding:10px 0;border-bottom:1px solid #d5ded1}.person-hierarchy .biography-table td{display:block;border:0;padding:5px 10px;min-width:0!important}.person-hierarchy .biography-table td::before{content:attr(data-label)}.person-hierarchy .timeline-row{grid-template-columns:1fr;gap:4px}.person-hierarchy .timeline-row time{font-size:.83rem}.person-hierarchy .dossier-section{padding:27px 0}}
@media(max-width:380px){.person-hierarchy .dossier-facts{grid-template-columns:1fr}.person-hierarchy .dossier-fact{border-right:0!important}.person-hierarchy .dossier-fact+.dossier-fact{border-top:1px solid #d8e0d3}.person-hierarchy .dossier-actions a{width:100%;justify-content:center}}
.person-hierarchy .biography-content .biography-table th{overflow-wrap:normal;word-break:normal}
.person-hierarchy .reading-guide-intro{max-width:78ch;margin:18px 0 4px;padding:14px 16px;background:#f0f4eb;border-left:3px solid #6d9278}.person-hierarchy .reading-guide-intro p{margin:6px 0;line-height:1.55}.person-hierarchy .reading-guide-actions{display:flex;gap:8px;margin-top:12px}.person-hierarchy .reading-guide-actions[hidden]{display:none}.person-hierarchy .reading-guide-actions button{padding:7px 11px;border:1px solid #b8cbbd;border-radius:5px;background:#fffef9;color:#315a43;cursor:pointer}.person-hierarchy .reading-guide-actions button:focus-visible,.person-hierarchy summary:focus-visible{outline:3px solid #b68425;outline-offset:3px}.person-hierarchy .reading-group-title{margin:20px 0 3px;font:600 1.3rem/1.3 var(--g-serif,Georgia,serif);color:#304b37}.person-hierarchy .reading-group-purpose{margin:0 0 7px;color:#617064;font-size:.88rem}.person-hierarchy .biography-section:has(.biography-disclosure){padding:12px 0}.person-hierarchy .biography-section:has(.biography-disclosure)>h2{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}.person-hierarchy .biography-disclosure{margin:7px 0;border:1px solid #d3ddce;border-radius:7px;background:#fafbf6;overflow:hidden;scroll-margin-top:78px}.person-hierarchy .biography-disclosure>summary{padding:11px 16px}.person-hierarchy .biography-disclosure>summary>span{display:inline;font-weight:650}.person-hierarchy .biography-disclosure>summary small{display:block;margin:6px 0 0 18px;color:#617064;font-size:.82rem;line-height:1.5}.person-hierarchy .biography-disclosure>summary small span{display:block;font-weight:400;margin:2px 0}.person-hierarchy .biography-disclosure>summary small strong{font-weight:700}.person-hierarchy .biography-disclosure[open]>.biography-content{padding:0 16px 16px}
@media print{.person-hierarchy .biography-disclosure,.person-hierarchy details{display:block!important}.person-hierarchy details::details-content{content-visibility:visible!important}.person-hierarchy .biography-disclosure>summary,.person-hierarchy details>summary{list-style:none}.person-hierarchy .reading-guide-actions{display:none}}
.person-hierarchy .biography-figure{margin:24px 0;background:#fffefa;border:1px solid #d5ded1;border-radius:8px;overflow:hidden}.person-hierarchy .biography-figure>a{display:block}.person-hierarchy .biography-figure img{display:block;width:100%;height:auto}.person-hierarchy .biography-figure figcaption{padding:12px 16px;color:#536350;font-size:.85rem;line-height:1.5}.person-hierarchy .biography-figure figcaption p{margin:0}
@media(max-width:680px){.person-hierarchy .biography-content .biography-table caption{display:block;width:100%;box-sizing:border-box}}
@media(prefers-reduced-motion:reduce){.person-hierarchy *{scroll-behavior:auto!important;transition:none!important}}
/* Dossier-local refinement. Explicit layout defeats the older shell's
   generic flex header without changing navigation on other site pages. */
.person-hierarchy .dossier-header{display:block!important;padding:26px 30px!important;background:#faf9f3;border:1px solid #d9dfd0;border-top:4px solid #477b65;border-radius:0 0 10px 10px;box-shadow:none}
.person-hierarchy .experience-scope-help{display:none}.person-hierarchy .r-context-top{min-width:0;padding:10px 20px;gap:10px}.person-hierarchy .r-context-title{min-width:0;max-width:100%;flex-wrap:wrap}.person-hierarchy .r-context-controls{min-width:0;max-width:100%;flex-wrap:wrap}.person-hierarchy .r-context-clear{white-space:normal;max-width:100%}
.person-hierarchy .dossier-header .kicker{margin:0 0 10px;letter-spacing:.12em;font-size:11px;color:#657c60}
.person-hierarchy .dossier-header h1{margin:0 0 9px!important;font-size:clamp(2rem,4vw,3.15rem)!important;line-height:1.12;letter-spacing:normal;max-width:none}
.person-hierarchy .dossier-life{margin:0 0 6px!important;max-width:80ch;font:400 1.02rem/1.55 var(--g-serif,Georgia,serif);color:#4b6050}
.person-hierarchy .dossier-locality{margin:4px 0;font-size:1rem;color:#45634d}.person-hierarchy .dossier-meta{display:flex;flex-wrap:wrap;gap:5px 18px;font-size:.8rem;margin-top:8px}
.person-hierarchy .dossier-actions{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0!important}.person-hierarchy .dossier-actions a{display:inline-flex;align-items:center;min-height:40px;padding:8px 14px;border:1px solid #b8cbbd;border-radius:6px;text-decoration:none;font-size:.83rem;background:#fffef9;color:#315a43}
.person-hierarchy .dossier-actions a:first-child{background:#315a43;color:white;border-color:#315a43}.person-hierarchy .dossier-actions a:hover{box-shadow:0 0 0 2px #ccd9c9}
.person-hierarchy .dossier-section{padding:25px 0}.person-hierarchy .dossier-section>h2{font-size:1.5rem;margin-bottom:14px}.person-hierarchy .dossier-lede{margin:0;font-size:1rem;max-width:73ch}
.person-hierarchy .dossier-facts{grid-template-columns:repeat(2,minmax(0,1fr));background:#f0f3e9;border-radius:6px;margin-top:18px}.person-hierarchy .dossier-fact{padding:10px 13px;border:0}.person-hierarchy .dossier-fact strong{font:600 .75rem/1.4 inherit}.person-hierarchy .dossier-fact span{font-size:.83rem;line-height:1.5}
.person-hierarchy .relation-group,.person-hierarchy .section-details{margin:9px 0;border:1px solid #d3ddce;border-radius:7px;background:#fafbf6;overflow:hidden}
.person-hierarchy summary{cursor:pointer;min-height:44px;padding:12px 16px;font-size:.93rem;line-height:1.5;color:#315a43;list-style-position:inside}
.person-hierarchy summary::marker{color:#61816a}.person-hierarchy details[open]>summary{background:#eaf0e3;border-bottom:1px solid #d3ddce}
.person-hierarchy .relation-group>summary>span:first-child{font-weight:650}.person-hierarchy summary small{font-size:.77rem;color:#687c67;margin-left:5px}
.person-hierarchy .group-preview{display:block;font-size:.82rem;line-height:1.5;color:#617065;padding-left:18px;margin-top:3px;overflow-wrap:anywhere}
.person-hierarchy .relation-table{font-size:.88rem;table-layout:fixed}.person-hierarchy .relation-table th:first-child{width:24%}.person-hierarchy .relation-table th:nth-child(2){width:15%}.person-hierarchy .relation-table th:nth-child(3){width:21%}.person-hierarchy .relation-table td{min-width:0!important;overflow-wrap:anywhere}
.person-hierarchy .status-label{font-size:.76rem;line-height:1.4;text-transform:none;letter-spacing:normal;border:0;background:#edf0e9;padding:4px 7px;color:#526754}
.person-hierarchy .status-proved,.person-hierarchy .status-documented{color:#246444;background:#e2f0e5}.person-hierarchy .status-proved::before,.person-hierarchy .status-documented::before{content:'✓ ';font-weight:800}
.person-hierarchy .status-possible,.person-hierarchy .status-uncertain,.person-hierarchy .status-estimated{background:#f5edce;color:#78601e}.person-hierarchy .status-possible::before,.person-hierarchy .status-uncertain::before{content:'? ';font-weight:800}
.person-hierarchy .status-superseded{background:#f3e5df;color:#8c523f}.person-hierarchy .question{padding:16px 18px;margin:12px 0;background:#f8faf4;border:1px solid #d6dfd1;border-left:3px solid #6d9278;border-radius:5px}
.person-hierarchy .question h3{font-size:1.03rem;line-height:1.45;margin:0 0 7px}.person-hierarchy .question .answer{font-size:.94rem;margin:0 0 10px}.person-hierarchy .question-reasoning{font-size:.9rem}
.person-hierarchy .question-details{border:0;background:transparent;margin:8px 0 0}.person-hierarchy .question-details>summary{padding:8px 0;font-size:.82rem;color:#406953}.person-hierarchy .question-details[open]>summary{background:transparent}.person-hierarchy .disclosure-body{padding-top:8px;min-width:0}
.person-hierarchy .related-argument{font-size:.86rem;margin:8px 0}.person-hierarchy .evidence-table{table-layout:fixed;width:100%;font-size:.86rem}.person-hierarchy .evidence-table td{min-width:0!important;overflow-wrap:anywhere}.person-hierarchy .evidence-table th{letter-spacing:normal;text-transform:none;font-size:.78rem}
.person-hierarchy .record-detail{border:0;background:transparent;margin:4px 0}.person-hierarchy .record-detail>summary{padding:3px 0;min-height:32px;font-size:.8rem}.person-hierarchy .timeline-group{margin:0;padding:12px 16px}.person-hierarchy .timeline-group>h3{font-size:.92rem}.person-hierarchy .timeline-row{font-size:.9rem}.person-hierarchy .record-kind{font-size:.72rem;color:#7a6843}.person-hierarchy .timeline-row[data-group='Collateral records']{border-left:2px solid #c3ae79;padding-left:12px}
.person-hierarchy .section-details>h3,.person-hierarchy .section-details>ol,.person-hierarchy .section-details>.table-wrap{margin:16px}.person-hierarchy .task-list{counter-reset:none}.person-hierarchy .task-list>.task::before{content:none!important}.person-hierarchy .task-list>.task::marker{content:''}
.person-hierarchy .dossier-archive{background:#eef2e9;border:1px solid #ccd7c5;border-radius:6px;padding:0;margin:25px 0}.person-hierarchy .dossier-archive .archive-body{padding:10px 16px}.person-hierarchy .archive-copy{overflow-wrap:anywhere}.person-hierarchy [id]{scroll-margin-top:85px}
.person-hierarchy .copy-wikitree{padding:9px 14px;background:#315a43;color:white;border:0;border-radius:5px;margin-bottom:10px;cursor:pointer}.person-hierarchy .archive-copy textarea{display:block;width:100%;box-sizing:border-box}
@media(max-width:1100px){.person-hierarchy .dossier-layout{display:block}.person-hierarchy .dossier-toc{display:none}.person-hierarchy .dossier-nav{display:flex;position:static;flex-wrap:wrap;margin:14px 0;padding:0;background:transparent}.person-hierarchy .dossier-nav a{min-height:36px;display:flex;align-items:center}.person-hierarchy .dossier-reading{max-width:none}}
@media(min-width:1101px){.person-hierarchy .dossier-nav{display:none!important}}
@media(max-width:680px){.person-hierarchy .r-context-top{display:block!important;padding:12px 18px!important}.person-hierarchy .r-context-title{display:flex!important;max-width:100%!important;gap:4px 10px!important}.person-hierarchy .r-context-controls{display:flex!important;gap:8px;margin-top:9px;justify-content:flex-start;flex-wrap:wrap!important}.person-hierarchy .r-context-clear{flex:1 1 175px;font-size:12px!important}.person-hierarchy #r-context-scope{flex:0 1 115px}.person-hierarchy .r-context-title .experience-selection-id{font-size:11px}.person-hierarchy .r-context-title strong{font-size:15px!important}}
@media(max-width:680px){.person-hierarchy .dossier-header{padding:20px!important}.person-hierarchy .dossier-header h1{font-size:2.15rem!important}.person-hierarchy .question{padding:13px}.person-hierarchy .dossier-section{padding:20px 0}.person-hierarchy .evidence-table,.person-hierarchy .relation-table{table-layout:auto}.person-hierarchy .relation-table td:nth-child(4){padding-bottom:12px}.person-hierarchy .group-preview{padding-left:0}.person-hierarchy .dossier-facts{grid-template-columns:1fr}.person-hierarchy .dossier-fact{border:0!important}.person-hierarchy .dossier-fact+.dossier-fact{border-top:1px solid #dce3d5!important}.person-hierarchy .dossier-nav a{font-size:.8rem}.person-hierarchy .source-links{font-size:.82rem}.person-hierarchy .timeline-group{padding:8px 12px}}
/* Compact archival identity, ink-and-paper reading surface, distinct evidence states. */
.person-hierarchy summary{letter-spacing:normal!important;text-transform:none!important}.person-hierarchy .candidate-score{white-space:nowrap}.person-hierarchy .candidate-score small{display:block;white-space:normal;font:400 .65rem/1.3 var(--g-sans,Arial,sans-serif);margin-top:4px}.person-hierarchy .family-preview-person small{font-weight:400}
.person-hierarchy .dossier-header{background:#234a3e!important;border:0!important;border-radius:10px!important;padding:26px 30px!important;box-shadow:0 8px 24px #183f3010}
.person-hierarchy .dossier-header .kicker{color:#ddc791!important;font-size:.69rem!important;margin:0 0 8px!important}
.person-hierarchy .dossier-header h1{color:#fffaf0!important;font-size:2.65rem!important;letter-spacing:normal!important;line-height:1.12!important;margin:0 0 8px!important}
.person-hierarchy .dossier-life{color:#e6ebdd!important;font-size:1.02rem;max-width:76ch}
.person-hierarchy .dossier-locality{color:#e4d5b1!important;margin:7px 0;font-size:.94rem}.person-hierarchy .dossier-locality a{color:inherit;text-decoration:underline;text-decoration-color:#9eb9aa;text-underline-offset:3px}.person-hierarchy .dossier-locality a:hover{color:#fff}
.person-hierarchy .dossier-meta{color:#c2d4ca!important;font-size:.73rem}
.person-hierarchy .dossier-actions{margin-top:17px;gap:8px}.person-hierarchy .dossier-actions a{background:transparent!important;border:1px solid #86a89a!important;color:#f7f7ed!important;padding:7px 12px!important;font-size:.8rem!important;min-height:38px}
.person-hierarchy .dossier-actions a:first-child{background:#f4eddc!important;color:#244b3e!important;border-color:#f4eddc!important}.person-hierarchy .dossier-actions a:hover{background:#3c6656!important;color:white!important}
.person-hierarchy .dossier-layout{gap:32px;grid-template-columns:190px minmax(0,1fr)}.person-hierarchy .dossier-toc{counter-reset:contents}.person-hierarchy .dossier-toc a{counter-increment:contents;padding:9px 0;font-size:.82rem}.person-hierarchy .dossier-toc a::before{content:counter(contents,decimal-leading-zero);font:12px ui-monospace,monospace;color:#809586;margin-right:12px}
.person-hierarchy .dossier-section{padding:27px 0}.person-hierarchy .dossier-section>h2{font-size:1.6rem;margin-bottom:15px;letter-spacing:normal}.person-hierarchy .dossier-lede{font-size:1rem;line-height:1.65;margin:0}.person-hierarchy .dossier-facts{background:#eeeede;border-radius:6px;border:0;margin-top:18px}.person-hierarchy .dossier-fact{padding:11px 13px}.person-hierarchy .dossier-fact strong{font:700 .72rem/1.4 var(--g-sans,Arial,sans-serif);text-transform:uppercase;letter-spacing:.04em}.person-hierarchy .dossier-fact span{color:#435b4d;font-size:.82rem}
.person-hierarchy .relation-group{background:#fffefa;border:1px solid #ccd8cd;border-radius:8px;overflow:hidden;margin:10px 0}.person-hierarchy .relation-group>summary{padding:15px 17px;background:transparent}.person-hierarchy .relation-group>summary>span:first-child{font-size:1.02rem}.person-hierarchy .relation-group>summary>span:first-child>small{background:#e5edde;border-radius:12px;padding:2px 7px;margin-left:6px;font:12px/1.4 var(--g-sans,Arial,sans-serif)}
.person-hierarchy .group-preview{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;padding:0}.person-hierarchy .family-preview-person{display:inline-block;background:#f0f3e9;border-radius:5px;padding:6px 9px;font-size:.83rem;color:#304e3d;line-height:1.4}.person-hierarchy .family-preview-person small{display:block;font-size:.71rem;color:#647464;max-width:35ch}.person-hierarchy .confirmed-mark{color:#277451;font-weight:800}.person-hierarchy .relation-group[open]>summary{border-bottom:1px solid #dce4d5;background:#edf3e8}.person-hierarchy .relation-group[open] .group-preview{display:none}
.person-hierarchy .question{background:#fffefa;border:0;border-bottom:1px solid #d7dfd1;border-radius:0;padding:17px 18px;margin:0}.person-hierarchy .question h3{font:600 1.15rem/1.4 var(--g-serif,Georgia,serif);color:#244e40}.person-hierarchy .question .answer{font-size:.95rem}.person-hierarchy .question-details>summary{color:#41644d;font-weight:600}.person-hierarchy .question-details>summary:hover{color:#143e30;text-decoration:underline}
.person-hierarchy .comparison-note{font-size:.87rem;color:#586953;max-width:76ch}.person-hierarchy .parent-comparison>h3{font:600 1.05rem/1.4 var(--g-serif,Georgia,serif);margin:20px 0 8px}
.person-hierarchy .parent-candidate{background:#fffefa;border:1px solid #d5dfcf;border-radius:6px;margin:7px 0;overflow:hidden}.person-hierarchy .parent-candidate>summary{display:grid;grid-template-columns:minmax(0,1fr) 125px minmax(165px,210px);gap:10px;align-items:center;padding:13px 15px;position:relative;padding-left:32px}.person-hierarchy .parent-candidate>summary::before{content:'+';position:absolute;left:12px;color:#5e775e}.person-hierarchy .parent-candidate[open]>summary::before{content:'−'}.person-hierarchy .parent-candidate>summary::marker{content:''}.person-hierarchy .candidate-name{font-size:.89rem;font-weight:600;color:#2f4b3a}.person-hierarchy .candidate-verdict{font-size:.73rem;color:#7c6229}.person-hierarchy .candidate-score{font:600 .79rem ui-monospace,monospace;color:#61725a;text-align:right;overflow-wrap:anywhere}.person-hierarchy .parent-candidate[data-state='working']{border-left:4px solid #b79950;background:#fbf7e8}.person-hierarchy .parent-candidate[data-state='excluded'] .candidate-verdict,.person-hierarchy .parent-candidate[data-state='superseded'] .candidate-verdict{color:#944e3f}
.person-hierarchy .candidate-body{padding:0 17px 17px;font-size:.88rem;line-height:1.6}.person-hierarchy .candidate-arguments{display:grid;grid-template-columns:1fr 1fr;gap:22px}.person-hierarchy .candidate-arguments h4{font-size:.78rem;color:#476549;margin:8px 0}.person-hierarchy .candidate-arguments p{margin:0}.person-hierarchy .candidate-history{margin-top:13px;background:#edf1e8;border:1px solid #d4ddcc;border-radius:6px}.person-hierarchy .candidate-history>summary{padding:12px 15px;font-size:.88rem}.person-hierarchy .candidate-history .parent-candidate,.person-hierarchy .score-detail{margin:10px}.person-hierarchy .score-detail{padding:8px 12px;background:#fffefa;font-size:.85rem}.person-hierarchy .score-detail>summary{display:flex;flex-wrap:wrap;gap:8px 12px;padding:7px 0}.person-hierarchy .score-detail>summary strong{margin-left:auto}.person-hierarchy .score-detail>summary .relation-note{flex-basis:100%}.person-hierarchy .score-detail li{margin:7px 0}
.person-hierarchy .section-details{background:#edf1e8;border-radius:6px}.person-hierarchy .section-details>summary{padding:14px 16px}.person-hierarchy .dossier-nav a{background:#edf1e6;border:0;color:#31573f}.person-hierarchy .dossier-nav a:hover{background:#dfe9d7}
@media(max-width:1100px){.person-hierarchy .dossier-layout{display:block}}
@media(max-width:680px){.person-hierarchy .dossier-header{padding:20px!important}.person-hierarchy .dossier-header h1{font-size:2rem!important}.person-hierarchy .dossier-life{font-size:.94rem}.person-hierarchy .dossier-section{padding:22px 0}.person-hierarchy .dossier-facts{padding:2px 0}.person-hierarchy .dossier-fact{display:grid;grid-template-columns:75px minmax(0,1fr);gap:8px;padding:9px 12px}.person-hierarchy .dossier-fact span{margin:0}.person-hierarchy .parent-candidate>summary{grid-template-columns:1fr!important;padding:14px 14px 14px 34px!important;gap:5px}.person-hierarchy .parent-candidate>summary::before{top:15px}.person-hierarchy .candidate-name,.person-hierarchy .candidate-verdict,.person-hierarchy .candidate-score{grid-column:1!important;grid-row:auto!important;text-align:left!important}.person-hierarchy .candidate-score{width:fit-content;max-width:100%;margin-top:4px}.person-hierarchy .candidate-score small{max-width:100%}.person-hierarchy .candidate-arguments{grid-template-columns:1fr;gap:12px}.person-hierarchy .question{padding:16px}.person-hierarchy .group-preview{grid-template-columns:1fr;gap:6px}.person-hierarchy .r-view-tabs,.person-hierarchy .dossier-nav{flex-wrap:nowrap!important;overflow-x:auto;overscroll-behavior-inline:contain;scrollbar-width:none}.person-hierarchy .r-view-tabs::-webkit-scrollbar,.person-hierarchy .dossier-nav::-webkit-scrollbar{display:none}.person-hierarchy .r-view-tabs a,.person-hierarchy .dossier-nav a{flex:0 0 auto;white-space:nowrap}.person-hierarchy .dossier-nav{margin:10px 0 2px;padding:4px 0 7px;-webkit-mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 28px),transparent);mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 28px),transparent)}}
@media(min-width:681px){.person-hierarchy .dossier-header{display:grid!important;grid-template-columns:minmax(0,1fr) minmax(230px,320px);column-gap:36px}.person-hierarchy .dossier-header>.kicker,.person-hierarchy .dossier-header>h1,.person-hierarchy .dossier-header>.dossier-life,.person-hierarchy .dossier-header>.dossier-locality{grid-column:1}.person-hierarchy .dossier-meta{grid-column:2;grid-row:2;align-self:end}.person-hierarchy .dossier-actions{grid-column:2;grid-row:3/6;align-self:start;margin-top:12px!important}}
.person-hierarchy .group-preview{display:grid;width:100%;grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}.person-hierarchy .family-preview-person{display:block;min-width:0;border-left:3px solid #b89a55;background:#f6f2e7}.person-hierarchy .family-preview-person:has(.confirmed-mark){border-left-color:#2f805b;background:#e9f2e8}
.person-hierarchy .question{margin:10px 0;border:1px solid #d5dfd1;border-left:4px solid #759078;border-radius:8px;background:#fffefa}.person-hierarchy .question-details>summary{min-height:38px}
.person-hierarchy .parent-candidate>summary{grid-template-columns:minmax(0,1fr) auto minmax(100px,auto)}.person-hierarchy .candidate-identity{min-width:0}.person-hierarchy .candidate-identity small{display:block;margin-top:4px;color:#69786d;font-size:.72rem;line-height:1.4}.person-hierarchy .candidate-name{text-decoration-thickness:1px;text-underline-offset:3px}.person-hierarchy .candidate-score{min-width:96px;padding:7px 10px;border-radius:20px;background:#e8f1e7;text-align:center}.person-hierarchy .candidate-score strong,.person-hierarchy .candidate-score small{display:block}.person-hierarchy .candidate-score strong{font-size:.9rem;color:#315d43}.person-hierarchy .candidate-score small{font:600 .62rem/1.3 var(--g-sans,Arial,sans-serif);text-transform:uppercase;letter-spacing:.04em;color:#69806d}.person-hierarchy .candidate-verdict{padding:4px 8px;border-radius:12px;background:#f0ead8;color:#73591d;font-weight:700;text-align:center}.person-hierarchy .candidate-assessment{margin:2px 0 14px;color:#435347}.person-hierarchy .candidate-arguments>div{padding:13px 15px;border-radius:7px}.person-hierarchy .candidate-support{background:#edf6ed;border:1px solid #cfe2d0}.person-hierarchy .candidate-objection{background:#fff5df;border:1px solid #ead8aa}.person-hierarchy .candidate-arguments h4{margin:0 0 8px}.person-hierarchy .candidate-support h4{color:#276344}.person-hierarchy .candidate-objection h4{color:#805e16}.person-hierarchy .candidate-arguments ul{margin:0;padding-left:19px}.person-hierarchy .candidate-arguments li{margin:6px 0}.person-hierarchy .score-rationale{margin:13px 0 0;border-top:1px solid #d9e1d5}.person-hierarchy .score-rationale>summary{padding:10px 0 4px;color:#496453;font-weight:600}.person-hierarchy .score-rationale>div{display:grid;grid-template-columns:1fr 1fr;gap:18px}.person-hierarchy .score-rationale h5{margin:7px 0 2px;color:#647365;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}.person-hierarchy .score-rationale ul{margin:4px 0 8px;padding-left:18px}.person-hierarchy .parent-candidate[data-state='excluded']{border-left:4px solid #a85e4c;background:#fff9f5}.person-hierarchy .parent-candidate[data-state='excluded'] .candidate-score{background:#f3e7e2}.person-hierarchy .parent-candidate[data-state='excluded'] .candidate-score strong{color:#874635}
.person-hierarchy .section-details>summary,.person-hierarchy .dossier-archive>summary{display:flex;align-items:center;justify-content:space-between;gap:16px}.person-hierarchy .section-details>summary::after{content:'Open';flex:0 0 auto;padding:3px 8px;border:1px solid #b9c9b4;border-radius:12px;font:700 .66rem/1.4 var(--g-sans,Arial,sans-serif);text-transform:uppercase;letter-spacing:.04em}.person-hierarchy .section-details[open]>summary::after{content:'Close'}.person-hierarchy .section-details>summary span,.person-hierarchy .dossier-archive>summary span{min-width:0}.person-hierarchy .section-details>summary small,.person-hierarchy .dossier-archive>summary small{display:block;margin:3px 0 0;font:400 .74rem/1.45 var(--g-sans,Arial,sans-serif);color:#677568}.person-hierarchy .dossier-archive>summary{font:600 .95rem/1.4 var(--g-sans,Arial,sans-serif)}
@media(max-width:680px){.person-hierarchy .dossier-fact{grid-template-columns:90px minmax(0,1fr);gap:10px}.person-hierarchy .candidate-identity,.person-hierarchy .candidate-verdict,.person-hierarchy .candidate-score{grid-column:1!important}.person-hierarchy .candidate-verdict{width:fit-content}.person-hierarchy .score-rationale>div{grid-template-columns:1fr}}
@media(max-width:680px){.person-hierarchy .biography-content .biography-table{display:block;width:100%;font-size:.9rem}.person-hierarchy .biography-content .biography-table thead{display:none}.person-hierarchy .biography-content .biography-table tbody{display:block;width:100%}.person-hierarchy .biography-content .biography-table tr{display:block;width:100%;padding:10px 0;border-bottom:1px solid #d5ded1}.person-hierarchy .biography-content .biography-table td{display:block;border:0;padding:5px 10px;min-width:0!important}.person-hierarchy .biography-content .biography-table td::before{content:attr(data-label);display:block;color:#657463;font-size:.68rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin-bottom:2px}}
.person-hierarchy .record-excerpt{margin:25px 0;padding:16px;border:1px solid #c6d6c5;border-radius:7px;background:#f7f8f0;min-width:0}.person-hierarchy .record-excerpt>h3{margin:0 0 12px;font-size:1.05rem}.person-hierarchy .record-controls{display:flex;flex-wrap:wrap;gap:9px 18px;align-items:center;margin-bottom:12px;font-size:.8rem}.person-hierarchy .record-controls label{display:flex;align-items:center;gap:6px;cursor:pointer;min-height:36px}.person-hierarchy .record-controls input{width:18px;height:18px;accent-color:#315a43}.person-hierarchy .record-viewport{max-width:100%;overflow:auto;border:1px solid #d2d2c1;background:#eee9dc}.person-hierarchy .record-stage{position:relative;width:100%;line-height:0}.person-hierarchy .record-stage img{display:block;width:100%;height:auto;max-width:none}.person-hierarchy .record-guides-layer{display:block;position:absolute;inset:0;pointer-events:none}.person-hierarchy .record-highlight{display:none}.person-hierarchy .record-highlight.is-active{display:block}.person-hierarchy .record-controls select{max-width:100%;padding:7px;border:1px solid #9cab94;border-radius:4px;background:#fffefa;color:#304b37;font:inherit}.person-hierarchy .record-controls label:has(select){flex-wrap:wrap;min-width:0;max-width:100%}.person-hierarchy .record-excerpt:has(.record-enlarge:checked) .record-stage{width:max(100%,var(--record-width))}.person-hierarchy .record-highlight{position:absolute;border:2px solid #a85012;background:rgba(255,213,82,.12)}.person-hierarchy .record-highlight b{position:absolute;left:0;top:0;background:#8e3f0d;color:#fff;font:700 11px/15px Arial,sans-serif;padding:0 3px;transform:translateY(-100%)}.person-hierarchy .record-excerpt figcaption{font-size:.9rem;line-height:1.6}.person-hierarchy .record-excerpt h4{margin:15px 0 4px;font-size:.82rem;color:#35523d}.person-hierarchy .record-excerpt p{margin:6px 0}.person-hierarchy .record-provenance{font-size:.76rem;color:#617064}.person-hierarchy .record-legend{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:4px 18px;font-size:.78rem}.person-hierarchy .record-reading{border-left:3px solid #b6c8af;padding-left:12px}.person-hierarchy .record-viewport:focus-visible{outline:2px solid #315a43;outline-offset:3px}@media(max-width:680px){.person-hierarchy .record-excerpt{padding:10px}.person-hierarchy .record-controls{gap:4px 12px}.person-hierarchy .record-controls label{width:100%}}

"""


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.casefold()).strip("-") or "item"


def person_href(value: str | None, profile_id: str | None = None) -> str:
    """Normalise internal links, especially from nested /people/ pages."""
    value = str(value or "").strip()
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/"):
        path = value
    elif value.startswith("people/"):
        path = "/" + value
    elif value.endswith(".html") and "/" not in value:
        path = "/people/" + value
    elif profile_id:
        path = f"/people/{profile_id.casefold()}.html"
    else:
        path = "/" + value
    return re.sub(r"^/people/(?:people/)+", "/people/", path)


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _profile_data(profile_id: str) -> tuple[dict, dict, dict]:
    global _INDEX_CACHE
    slug = profile_id.casefold()
    dossier = _load_json(WEB / "people" / f"{slug}.json", {})
    model = _load_json(WEB / "assets/research/people" / f"{slug}.json", {})
    if _INDEX_CACHE is None:
        _INDEX_CACHE = {row.get("id"): row for row in _load_json(WEB / "data/people-index.json", []) if row.get("id")}
    index = _INDEX_CACHE
    return dossier, model, index


def _editorial(profile_id: str) -> dict:
    dossier, model, _ = _profile_data(profile_id)
    authored = _load_json(ROOT / "research" / profile_id / "presentation.json", {})
    candidates = ROOT / "research" / profile_id / "parent_candidates.json"
    if candidates.exists():
        authored["parent_candidates"] = _load_json(candidates, [])
        assertions = {a["assertion_id"]: a for a in _relationship_assessments() if a.get("assertion_id")}
        for candidate in authored["parent_candidates"]:
            if not candidate.get("assertion_id"):
                continue
            assertion = assertions[candidate["assertion_id"]]
            candidate.update(state=assertion["hypothesis_status"], assessment=assertion["claim"],
                             objections=assertion["limitations"], source_ids=assertion["source_ids"])
    return resolve_presentation(profile_id, dossier, model, authored)


def _refresh_reviewed_parentage(profile_ids=None) -> None:
    """Refresh reviewed scores from the rich source model, not the public index."""
    requested = {value.casefold() for value in profile_ids} if profile_ids else None
    subjects = [
        path.parent.name for path in (ROOT / "research").glob("*/parent_candidates.json")
        if requested is None or path.parent.name.casefold() in requested
    ]
    if not subjects:
        return
    try:
        from tools.build_family_map import (
            apply_catalogue_profile_links, load_records, profile_metadata,
            relationship_edges, root_metadata,
        )
        from tools.build_research_catalog import (
            _build_people, _load_profile_updates, _load_wikitree_evidence,
            _potential_parentage, _similar_people, catalogue_profile_update_ids,
            catalogue_research_case_ids,
        )
        from tools.catalogue_machine_data import build_machine_models
    except ModuleNotFoundError:
        from build_family_map import (
            apply_catalogue_profile_links, load_records, profile_metadata,
            relationship_edges, root_metadata,
        )
        from build_research_catalog import (
            _build_people, _load_profile_updates, _load_wikitree_evidence,
            _potential_parentage, _similar_people, catalogue_profile_update_ids,
            catalogue_research_case_ids,
        )
        from catalogue_machine_data import build_machine_models
    records = load_records()
    apply_catalogue_profile_links(records)
    edges = relationship_edges(records)
    _, descendant_counts, _ = root_metadata(records, edges)
    wikitree_evidence = _load_wikitree_evidence()
    profile_updates = _load_profile_updates(wikitree_evidence)
    profiles = profile_metadata(records, catalogue_profile_update_ids())
    people = _build_people(
        records, profiles, edges, descendant_counts, wikitree_evidence,
        profile_seed_ids=set(profile_updates) | catalogue_research_case_ids(),
    )
    _, rich_index = build_machine_models(
        [person for person in people if not person["likely_living"]]
    )
    subject_ids = set(subjects)
    refreshed = _potential_parentage(
        rich_index, _similar_people(rich_index), requested_subject_ids=subject_ids,
    )
    for profile_id in subjects:
        path = WEB / "people" / f"{profile_id.casefold()}.json"
        dossier = _load_json(path, {})
        if dossier and profile_id in refreshed and dossier.get("potential_parentage") != refreshed[profile_id]:
            dossier["potential_parentage"] = refreshed[profile_id]
            path.write_text(json.dumps(dossier, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def _canonical_records() -> list[dict]:
    return _load_json(ROOT / "research" / "canonical_records.json", [])


def _canonical_record_rows(profile_id: str) -> list[dict]:
    """Return explicitly shared record identities mapped to this profile."""
    wanted = profile_id.casefold()
    rows = []
    for record in _canonical_records():
        profiles = record.get("profiles") or {}
        profile_key = next((key for key in profiles if str(key).casefold() == wanted), None)
        if profile_key:
            row = {key: value for key, value in record.items() if key not in {"profiles", "record_assessments"}}
            context = profiles.get(profile_key)
            if isinstance(context, dict) and context:
                row["_profile_context"] = context
            rows.append(row)
    return rows


def _record_rows(profile_id: str) -> list[dict]:
    path = ROOT / "research" / profile_id / "records_mentions.json"
    if path.exists():
        rows = _load_json(path, {}).get("records", [])
    else:
        editorial = _load_json(ROOT / "research" / profile_id / "presentation.json", {})
        if editorial.get("record_rows"):
            rows = editorial["record_rows"]
        else:
            model = _load_json(WEB / "assets/research/people" / f"{profile_id.casefold()}.json", {})
            rows = []
            for record_id in model.get("record_ids", []):
                row = _load_json(WEB / "assets/research/records" / f"{record_id}.json", {})
                if row:
                    rows.append(row)
    # Share the recorded facts AND the viewing person's role. A local copy
    # must not shadow a canonical correction or another person's context.
    canonical = {_record_id(row): row for row in _canonical_record_rows(profile_id)}
    merged = [{**row, **canonical.pop(_record_id(row), {})} for row in rows]
    return merged + list(canonical.values())


def _status_class(value: str | None) -> str:
    return _safe_slug(str(value or "unassessed"))


def _a(href: str, label: str, external: bool = False) -> str:
    attrs = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a href="{escape(href, quote=True)}"{attrs}>{escape(label)}</a>'


def _link_text(href: str, label: str) -> str:
    return _a(href, label, href.startswith("http"))


def _record_id(row: dict) -> str:
    """Return the maintained record identity, never the shared web URL."""
    explicit = str(row.get("record_id") or "").strip()
    if explicit:
        return explicit
    basis = "|".join(str(row.get(k) or "") for k in ("date", "association", "place"))
    return "record-" + hashlib.sha1(basis.encode()).hexdigest()[:12]


def _public_record_note(row: dict) -> str:
    note = str(row.get("note") or "")
    if "One-Tree export profile fields" in note:
        return "The profile snapshot records this fact, but it is not an independent historical record; the linked historical evidence is assessed separately."
    return note


def _record_source_map(rows: list[dict]) -> tuple[dict[str, str], list[dict]]:
    """Build a source register per record, not per URL.

    Several distinct entries can legitimately share a transcription or search
    page.  Their stable record IDs keep baptism entries, valuation volumes and
    the will/marriage identity bridge separate while retaining the common URL.
    """
    sources, by_record = [], {}
    for row in rows:
        record_id = _record_id(row)
        if record_id in by_record:
            continue
        key = "source-" + _safe_slug(record_id)
        by_record[record_id] = key
        url = str(row.get("source_url") or "").strip()
        sources.append({
            "key": key,
            "record_id": record_id,
            "title": row.get("association") or row.get("source_title") or "Source record",
            "date": row.get("date") or row.get("year") or "",
            "place": row.get("place") or row.get("record_location") or "",
            "url": url,
            "status": row.get("status") or "Source association",
            "note": _public_record_note(row) or "The cited page should be checked against the underlying record.",
            "private": bool(row.get("private") or any(token in str(row.get("association") or "").casefold() for token in ("correspondence", "email", "private"))),
        })
    return by_record, sources


def _record_by_keys(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for row in rows:
        if row.get("record_id"):
            out[str(row["record_id"])] = row
        text = f"{row.get('association','')} {row.get('date','')}".casefold()
        if "1834" in text and "tithe" in text: out.setdefault("tithe-1834", row)
        if "1837" in text and "bapt" in text: out.setdefault("baptism-james-1837", row)
        if "1838" in text and ("unnamed" in text or "child" in text): out.setdefault("baptism-unnamed-1838", row)
        if "1844" in text and "bapt" in text: out.setdefault("baptism-james-1843", row)
        if "1851" in text and "census" in text: out.setdefault("census-1851", row)
        if "valuation" in text and "struck" in text: out.setdefault("valuation-1879-1888", row)
        elif "valuation" in text: out.setdefault("valuation-1863-1878", row)
        if "1866" in text and "marriage" in text: out.setdefault("marriage-robert-1866", row)
        if "1871" in text and "marriage" in text and "mary" in text: out.setdefault("marriage-mary-1871", row)
        if "1876" in text and "marriage" in text: out.setdefault("marriage-ann-1876", row)
        if "1888" in text and "death" in text: out.setdefault("death-alexander-1888", row)
        if "daniel glasgow will" in text: out.setdefault("will-daniel-1871", row)
        if "daniel neely glasgow" in text and "marriage" in text: out.setdefault("marriage-daniel-neely-1888", row)
        if "correspondence" in text or "autosomal" in text or ("thomas" in text and "descendant" in text): out.setdefault("correspondence-thomas-2020", row)
    return out


def _record_link(row: dict | None, source_by_record: dict[str, str]) -> str:
    if not row: return ""
    url = str(row.get("source_url") or "")
    links = []
    record_id = _record_id(row)
    if record_id in source_by_record: links.append(_a(f"#{source_by_record[record_id]}", "Source register"))
    if url: links.append(_a(url, "Open record", True))
    if row.get("related_url"): links.append(_a(person_href(row["related_url"]), "Related person"))
    return " · ".join(links)


def _format_date_value(value) -> str:
    value = str(value or "").strip()
    if value.casefold() in {"unknown", "not recorded", "not established", "n/a", "none"}:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        from datetime import date as _date
        return _date.fromisoformat(value).strftime("%-d %B %Y")
    qualified = re.fullmatch(r"(before|after|about|circa|c\.)\s+(\d{4}-\d{2}-\d{2})", value, re.I)
    if qualified:
        from datetime import date as _date
        return f"{qualified.group(1)} {_date.fromisoformat(qualified.group(2)).strftime('%-d %B %Y')}"
    return value


def _date_sort_key(value, fallback=None) -> tuple:
    """Sort ranges/decades by their stated start; boundaries by stated date.

    Missing month/day sort at the beginning of that year/month. Qualifiers
    break otherwise equal keys (before, exact, approximate/range, after).
    Undated records sort last. No date or conversion is inferred for display.
    """
    text = str(value or fallback or "").strip()
    years = [int(item) for item in re.findall(r"(?<!\d)(\d{4})(?!\d)", text)]
    if not years:
        return (9999, 0, 0, 9, text.casefold())
    lowered = text.casefold()
    iso = re.search(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})", text)
    month = day = 0
    if iso:
        month, day = int(iso[2]), int(iso[3])
    else:
        from calendar import month_name
        for number, name in enumerate(month_name):
            if number and re.search(rf"\b{name}\b", text, re.I):
                month = number
                match = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+{name}\b", text, re.I)
                if match: day = int(match[1])
                break
    qualifier = 0 if lowered.startswith("before") else 3 if lowered.startswith("after") else 2 if lowered.startswith(("c.", "circa", "about")) or len(years) > 1 else 1
    return (years[0], month, day, qualifier, text.casefold())


def _record_context(row: dict) -> dict:
    context = row.get("_profile_context")
    return context if isinstance(context, dict) else {}


def _event_matches_record(event: dict, row: dict) -> bool:
    event_url = str(event.get("source_url") or "").strip()
    row_url = str(row.get("source_url") or "").strip()
    if event_url and row_url and event_url == row_url:
        return True
    event_ids = {str(event.get("id") or ""), str(event.get("evidence_id") or "")}
    if _record_id(row) in event_ids:
        return True
    # Some imported death events retain no source URL, while the canonical
    # record does.  Match only the same death year and place rather than
    # collapsing unrelated same-name events.
    if str(event.get("event_type") or "").casefold() == "death" and _record_id(row).startswith("death-"):
        event_years = _date_sort_key(event.get("date"), event.get("year"))[:2]
        row_years = _date_sort_key(row.get("date"), row.get("year"))[:2]
        event_place = str(event.get("place") or "").casefold()
        row_place = str(row.get("place") or row.get("record_location") or "").casefold()
        return event_years[0] == row_years[0] and (not event_place or not row_place or event_place in row_place or row_place in event_place)
    return False


def _matching_record(event: dict, rows: list[dict]) -> dict | None:
    return next((row for row in rows if _event_matches_record(event, row)), None)


def _default_timeline_group(row: dict) -> str:
    text = " ".join(str(row.get(key) or "") for key in ("record_id", "association", "role", "status")).casefold()
    if any(token in text for token in ("collateral", "family network", "descendant", "family continuation", "elder-family", "will-daniel", "marriage-daniel-neely")):
        return "Collateral records"
    return "Records mentioning this person"


def _timeline_role(row: dict, context: dict) -> str:
    return str(context.get("role") or row.get("timeline_role") or row.get("role") or row.get("status") or "Record association")


def _role_label(relation: dict, group: str, state: str) -> str:
    """Use a relationship label that fits the opened person's perspective."""
    if relation.get('lifecycle') == 'current' and relation.get('status_label'):
        return relation['status_label']
    role = str(relation.get("relationship") or "").casefold()
    if relation.get("hypothesis_status") == "open":
        return relation.get("status_label") or ("Open father hypothesis" if role == "father" else "Open relationship hypothesis")
    if state == "superseded":
        return "Superseded proposal"
    if state in {"unknown", "unmarked", "unassessed"}:
        if group == "parents" or role in {"father", "mother", "parent"}:
            return "Unassessed parent"
        if group == "children" or role in {"son", "daughter", "child"}:
            return "Unassessed child"
        if group == "spouses" or role in {"spouse", "partner"}:
            return "Tree relationship"
        if group == "siblings" or role == "sibling":
            return "Unassessed sibling link"
        return "Relationship not assessed"
    if group == "parents" or role in {"father", "mother", "parent"}:
        if role == "father":
            return "Documented father" if state == "proved" else "Strongly identified father" if state == "strongly_supported" else "Possible father"
        if role == "mother":
            return "Documented mother" if state == "proved" else "Strongly identified mother" if state == "strongly_supported" else "Possible mother"
        return "Documented parent" if state == "proved" else "Strongly identified parent" if state == "strongly_supported" else "Possible parent"
    if group == "children" or role in {"son", "daughter", "child"}:
        if role == "daughter":
            return "Documented daughter" if state == "proved" else "Strongly identified daughter" if state == "strongly_supported" else "Possible daughter"
        if role == "son":
            return "Documented son" if state == "proved" else "Strongly identified son" if state == "strongly_supported" else "Possible son"
        return "Documented child" if state == "proved" else "Strongly identified child" if state == "strongly_supported" else "Possible child"
    if group == "spouses" or role in {"spouse", "partner"}:
        return "Documented spouse" if state == "proved" else "Tree relationship"
    if group == "siblings" or role == "sibling":
        return "Documented sibling" if state == "proved" else "Unassessed sibling link"
    return relation.get("status_label") or state.replace("_", " ").title()


def _current_vitals(profile_id: str, dossier: dict, model: dict, editorial: dict | None = None) -> dict:
    # Publication resolves research first; display overrides cannot decide facts.
    return dossier.get("vitals") or {}


def _family_dates(relation: dict, index: dict) -> str:
    rid = str(relation.get("id") or "")
    if not rid:
        return "Dates not established"
    dossier, model, _ = _profile_data(rid)
    values = []
    for kind in ("birth", "death"):
        item = _current_vitals(rid, dossier, model).get(kind) or {}
        value = item.get("display_date") or item.get("date")
        formatted = _format_date_value(value) if value else ""
        values.append((formatted + (f" ({item['qualifier']})" if item.get("qualifier") else "")) if formatted else "date not established")
    if any(v != "date not established" for v in values):
        qualifier = (_current_vitals(rid, dossier, model).get("birth") or {}).get("qualifier")
        if qualifier and values[0].endswith(f" ({qualifier})") and values[1].endswith(f" ({qualifier})"):
            values[0] = values[0].removesuffix(f" ({qualifier})")
        return "–".join(values)
    return "Dates not established"


def _reverse_relation(profile_id: str, relation: dict, group: str) -> dict | None:
    """Use a reviewed reverse edge when the opened dossier has only a tree edge."""
    rid = relation.get("id")
    if not rid:
        return None
    reverse_group = {"parents": "children", "children": "parents", "spouses": "spouses", "siblings": "siblings"}.get(group)
    if not reverse_group:
        return None
    target_dossier, target_model, _ = _profile_data(rid)
    current = str(profile_id).casefold()
    for candidate in (target_dossier.get("relationships", {}).get(reverse_group, []) or target_model.get("relationships", {}).get(reverse_group, [])):
        if str(candidate.get("id") or "").casefold() != current:
            continue
        state = candidate.get("status") or ""
        if state in {"proved", "strongly_supported", "possible", "superseded"} and (candidate.get("basis") != "tree"):
            return candidate
    return None


def _relationship_assessments() -> list[dict]:
    return _load_json(ROOT / "research" / "relationship_assessments.json", [])


def _shared_relationship_assessment(profile_id: str, relation: dict) -> dict | None:
    dossier, _, _ = _profile_data(profile_id)
    return next((row for rows in dossier.get("relationships", {}).values() for row in rows
                 if row.get("id") == relation.get("id") and row.get("lifecycle") == "current"), None)


def _assessed_relation(profile_id: str, relation: dict, group: str) -> dict:
    return _shared_relationship_assessment(profile_id, relation) or relation


def _relation_reason(editorial: dict, relation: dict, group: str) -> str:
    rid = relation.get("id") or ""
    if relation.get("reason"):
        return str(relation["reason"])
    configured = (editorial.get("family_reasons") or {}).get(rid)
    if configured:
        return configured
    state = relation.get("status") or relation.get("tree_status") or "unassessed"
    if relation.get("tree_relationship") and state in {"unknown", "unmarked", "unassessed"}:
        return "The family tree retains this link, but the available records have not been assessed as establishing this relationship."
    if relation.get("basis") == "research_assessment":
        return "The maintained research assesses this relationship; the linked record and qualification explain what is established."
    return "The relationship is retained in the family model, but its documentary basis has not been resolved."


def _family_html(profile_id: str, dossier: dict, model: dict, index: dict, editorial: dict, source_by_record: dict[str, str]) -> str:
    relations = dossier.get("relationships", {})
    lookup = {str(r.get("id")): r for group in ("parents", "spouses", "children", "siblings") for r in relations.get(group, []) if r.get("id")}
    display = editorial.get("family_display") or {}
    groups = []
    if display.get("groups"):
        for configured in display["groups"]:
            values = []
            for item in configured.get("items", []):
                if isinstance(item, str):
                    if item in lookup:
                        values.append(lookup[item])
                elif isinstance(item, dict):
                    values.append(item)
            groups.append((configured.get("key") or "family", configured.get("title") or "Family", values))
    else:
        groups = [("spouses", "Partner", relations.get("spouses", [])), ("children", "Children", relations.get("children", [])), ("parents", "Parents", relations.get("parents", [])), ("siblings", "Collateral relatives", relations.get("siblings", []))]
    out = []
    for key, title, values in groups:
        if not values:
            continue
        if key == "children":
            def child_sort(item):
                rid = item.get("id") if isinstance(item, dict) else ""
                _, child_model, _ = _profile_data(str(rid)) if rid else ({}, {}, {})
                vital = (child_model.get("vitals") or {}).get("birth") or {}
                raw = vital.get("date") or vital.get("display_date") or ""
                return (*_date_sort_key(raw), str(item.get("name") if isinstance(item, dict) else item))
            values = sorted(values, key=child_sort)
        rendered = []
        for original in values:
            relation = _assessed_relation(profile_id, original, key)
            rid = relation.get("id") or ""
            href = person_href(relation.get("url"), rid) if rid else ""
            name = relation.get("name") or rid or "Unnamed person"
            person = _link_text(href, name) if href else escape(name)
            state = relation.get("status") or relation.get("tree_status") or "unassessed"
            label = _role_label(relation, key, state)
            if relation.get("display") == "alternative" and state in {"unknown", "unassessed"}:
                label = "Earlier tree proposal; not established"
            if relation.get("display") == "proposed":
                label = relation.get("status_label") or "Uncertain working hypothesis"
            relationship = relation.get("relationship") or ("parent" if key == "parents" else "child" if key == "children" else "partner")
            reason = _relation_reason(editorial, relation, key)
            source_links = []
            source_ids = list((editorial.get("family_sources") or {}).get(rid, []))
            source_ids.extend(relation.get("source_ids") or relation.get("evidence_ids") or [])
            for source_id in dict.fromkeys(source_ids):
                if source_id in source_by_record:
                    source_links.append(_a(f"#{source_by_record[source_id]}", "Supporting record"))
            source_links.extend(_a(link["href"], link["label"]) for link in relation.get("analysis_links", []))
            link_html = f'<div class="source-links">{" · ".join(source_links)}</div>' if source_links else ""
            claim_attr = f' data-claim-id="{escape(relation["claim_id"])}"' if relation.get("assertion_id") else ""
            rendered.append(f'<tr data-state="{escape(_status_class(state))}"{claim_attr}><td>{person}<br><span class="relation-note">{escape(_family_dates(relation, index))}</span></td><td>{escape(relationship)}</td><td><span class="status-label status-{escape(_status_class(state))}">{escape(label)}</span></td><td>{escape(reason)}{link_html}</td></tr>')
        previews = []
        for item in values:
            relation = _assessed_relation(profile_id, item, key)
            confirmed = relation.get("status") == "proved"
            name = str(item.get("name") or item.get("id") or "Unnamed")
            dates = _family_dates(relation, index)
            mark = '<span class="confirmed-mark" aria-label="Documented relationship">✓</span> ' if confirmed else ''
            previews.append(f'<span class="family-preview-person">{mark}{escape(name)}<small>{escape(dates)}</small></span>')
        out.append(f'<details class="relation-group"><summary><span>{escape(title)} <small>{len(values)}</small></span><span class="group-preview">{"".join(previews)}</span></summary><div class="table-wrap"><table class="relation-table"><thead><tr><th>Person and dates</th><th>Relationship</th><th>Current assessment</th><th>Why this relationship is shown</th></tr></thead><tbody>{"".join(rendered)}</tbody></table></div></details>')
    scope = editorial.get("family_scope_note")
    return (f'<p class="family-scope">{escape(scope)}</p>' if scope else "") + "".join(out)


def _parent_comparison_html(editorial: dict, dossier: dict) -> str:
    # This section deliberately compares identified possible fathers only.
    # Record-defined unnamed men and proposed mothers remain in the research
    # account, where they can be discussed without pretending they are scored
    # profile candidates.
    candidates = [item for item in (editorial.get("parent_candidates") or []) if item.get("father_profile_id")]
    automated = (dossier.get("potential_parentage") or {}).get("candidates") or []
    if not candidates:
        return ""
    scores = {item["id"]: item for item in automated}
    labels = {"working": "Working hypothesis", "open": "Open lead", "weak": "Weak lead", "excluded": "Excluded"}
    state_order = {"working": 0, "open": 1, "weak": 2, "uncertain": 3, "excluded": 4}

    def bullet_list(value) -> str:
        values = value if isinstance(value, list) else [value] if value else []
        return '<ul>' + ''.join(f'<li>{escape(str(part))}</li>' for part in values) + '</ul>'

    groups = []
    for title, states in (("Current candidates", {"working", "open", "weak", "uncertain"}), ("Excluded candidates", {"excluded"})):
        entries = []
        for item in sorted(candidates, key=lambda row: (state_order.get(row.get("state") or "uncertain", 9), -int((scores.get(row.get("father_profile_id")) or {}).get("score") or 0))):
            state = item.get("state") or "uncertain"
            if state not in states:
                continue
            cid = _safe_slug(item.get("id") or item["candidate"])
            profile_id = item["father_profile_id"]
            score = scores.get(profile_id) or {}
            score_text = f'{score.get("score", "—")}/100'
            score_hint = item.get("score_note") or "Stored individual research score; not a probability"
            pd, _, _ = _profile_data(profile_id)
            birth = (pd.get("vitals") or {}).get("birth") or {}
            birth_value = _format_date_value(birth.get("display_date") or birth.get("date")) or "not yet established"
            birth_place = birth.get("place") or "place not established"
            birth_prefix = "Birth" if birth.get("status") in {"exact", "proved"} else "Estimated birth"
            wiki = pd.get("wikitree_url") or f'https://www.wikitree.com/wiki/{profile_id}'
            local = person_href(None, profile_id)
            links = [_a(link["href"], link["label"]) for link in item.get("source_links", [])]
            links.insert(0, _a(local, "Local evidence dossier"))
            source_path = item.get("source_path") or ""
            source_parts = source_path.split("/")
            if len(source_parts) > 2 and source_parts[0] == "research":
                research_dossier, _, _ = _profile_data(source_parts[1])
                for finding in research_dossier.get("research_findings", []):
                    if finding.get("source_path", "").lstrip("/") == source_path:
                        sections = finding.get("sections") or []
                        if sections:
                            anchor = _research_note_anchor(source_path, sections[0].get("title") or "Research note")
                            links.append(_a(person_href(None, source_parts[1]) + "#" + anchor, "Maintained research account"))
                        break
            if not links and item.get("link"):
                links.append(_a(item["link"], "Detailed analysis"))
            reason_list = bullet_list(score.get("reasons") or [])
            conflict_list = bullet_list(score.get("conflicts") or [])
            score_detail = f'<details class="score-rationale"><summary>Why the research tool gave this score</summary><div><h5>Factors</h5>{reason_list}<h5>Conflicts and deductions</h5>{conflict_list}</div></details>' if score else ""
            verdict = item.get("verdict_label") or labels.get(state, "Uncertain lead")
            entries.append(f'<details class="parent-candidate" id="candidate-{cid}" data-state="{escape(state)}" data-score-profile="{escape(profile_id)}"><summary><span class="candidate-identity"><a class="candidate-name" href="{escape(wiki)}" target="_blank" rel="noopener">{escape(item["candidate"])}</a><small>{escape(profile_id)} · {escape(birth_prefix)}: {escape(birth_value)} · {escape(birth_place)}</small></span><span class="candidate-verdict">{escape(verdict)}</span><span class="candidate-score" title="{escape(score_hint)}"><strong>{escape(score_text)}</strong><small>research score</small></span></summary><div class="candidate-body"><p class="candidate-assessment">{escape(item.get("assessment") or "")}</p><div class="candidate-arguments"><div class="candidate-support"><h4><span aria-hidden="true">✓</span> Supporting evidence</h4>{bullet_list(item.get("supports"))}</div><div class="candidate-objection"><h4><span aria-hidden="true">!</span> Objections and gaps</h4>{bullet_list(item.get("objections"))}</div></div>{score_detail}<div class="source-links">{" · ".join(links)}</div></div></details>')
        if entries:
            content = f'<h3>{title}</h3>' + "".join(entries)
            groups.append(content if title == "Current candidates" else f'<details class="candidate-history"><summary>{title} · {len(entries)}</summary>{"".join(entries)}</details>')
    return '<p class="comparison-note">This is a father-only comparison of identified WikiTree profiles. Every candidate has an estimated or recorded birth and an individual stored research score. Scores rank leads; they are not probabilities or proof of parentage.</p><div class="parent-comparison">' + "".join(groups) + '</div>'


def _evidence_questions(editorial: dict, rows: list[dict], source_by_record: dict[str, str]) -> str:
    questions = editorial.get("evidence_questions") or []
    by_key = _record_by_keys(rows)
    interpretations = editorial.get("record_evidence") or {}
    out = []
    for question in questions:
        qid = str(question.get("id") or _safe_slug(question.get("title")))
        q_interpretations = interpretations.get(qid) or {}
        evidence_rows = []
        for key in question.get("records", []):
            row = by_key.get(key)
            interpretation = q_interpretations.get(key)
            if not row or not interpretation:
                continue
            title = row.get("association") or row.get("source_title") or "Record"
            facts = interpretation.get("recorded_statement")
            relevance = interpretation.get("relevance")
            limitation = interpretation.get("limitation")
            if not facts or not relevance or not limitation:
                continue
            link = _record_link(row, source_by_record)
            record_html = f'<strong>{escape(title)}</strong><br><span class="relation-note">{escape(str(row.get("date") or row.get("year") or "Undated"))} · {escape(str(row.get("place") or row.get("record_location") or "Place not stated"))}</span>'
            if link: record_html += f'<div class="source-links">{link}</div>'
            anchor = f' id="record-{escape(_safe_slug(_record_id(row)))}-{escape(_safe_slug(qid))}"'
            evidence_rows.append(f'<tr{anchor}><td>{record_html}</td><td>{escape(facts)}</td><td>{escape(relevance)}</td><td>{escape(limitation)}</td></tr>')
        table = '<table class="evidence-table"><thead><tr><th>Record</th><th>What it says</th><th>Why it matters</th><th>Limitation</th></tr></thead><tbody>' + "".join(evidence_rows) + '</tbody></table>' if evidence_rows else ''
        extras = _a("#parent-candidates", "Compare possible fathers and their stored scores") if qid == "parents" and editorial.get("parent_candidates") else ""
        dna = editorial.get("dna_summary") or {}
        dna_block = f'<div class="dna-summary"><h4>DNA findings</h4><p><strong>Autosomal lead.</strong> {escape(dna.get("autosomal") or "")}</p><p><strong>Y-DNA findings.</strong> {escape(dna.get("y_dna") or "")}</p><p class="relation-note"><strong>Limitation.</strong> {escape(dna.get("limitation") or "")}</p></div>' if qid == "dna" and dna else ""
        reference_links = []
        for reference in question.get("record_references", []):
            rid = _safe_slug(reference["record_id"])
            target_qid = _safe_slug(reference["question_id"])
            record = by_key.get(reference["record_id"], {})
            reference_links.append(f'<span id="record-{rid}-{escape(qid)}">{_a(f"#record-{rid}-{target_qid}", record.get("association") or reference["record_id"])}</span>')
        related = question.get("related_question") or {}
        related_html = f'<p class="related-argument">{_a(related["href"], related["label"])}</p>' if related else ""
        reason = f'<p class="question-reasoning">{escape(question.get("reasoning") or "")}</p>' if question.get("reasoning") else ""
        # A canonical multi-record proof stays visible once. Supporting rows,
        # transcripts and secondary questions open on demand.
        visible_reason = reason if question.get("id") in (editorial.get("visible_arguments") or []) else ""
        detail_reason = "" if visible_reason else reason
        limits = ''.join(f'<p><strong>{label}</strong> {escape(question[key])}</p>' for key, label in (("limitation", "Limitations."), ("missing", "Next evidence.")) if question.get(key))
        references = '<p class="source-links">' + " · ".join(reference_links) + '</p>' if reference_links else ""
        record_count = len(evidence_rows)
        record_label = f" · {record_count} {'record' if record_count == 1 else 'records'}" if evidence_rows else ""
        out.append(f'<article class="question" id="question-{escape(qid)}"><h3>{escape(question.get("title") or "Research question")}</h3><p class="answer">{escape(question.get("answer") or "")}</p>{visible_reason}{related_html}{references}<details class="question-details"><summary>Evidence and qualifications{record_label}</summary><div class="disclosure-body">{detail_reason}{table}{extras}{dna_block}{limits}</div></details></article>')
    return "".join(out) or '<p class="dossier-empty">No maintained question-and-argument layer is available for this dossier.</p>'


def _timeline_html(profile_id: str, model: dict, rows: list[dict], source_by_record: dict[str, str]) -> str:
    groups = defaultdict(list)
    consumed = set()
    editorial = _editorial(profile_id)

    def add(group: str, *, date, year, record_id, title, role, place, note, url):
        groups[group].append({
            "date": _format_date_value(date) or "Undated",
            "sort_date": date or year,
            "year": year,
            "record_id": record_id,
            "title": title,
            "role": role,
            "place": place,
            "note": note,
            "url": url,
            "group": group,
        })

    for event in model.get("events", []):
        if event.get("research") or event.get("kind") == "research":
            continue
        if event.get("id") in (editorial.get("archive_event_ids") or []):
            continue
        event = dict(event)
        kind = event.get("event_type")
        qualifier = (editorial.get("vital_qualifiers") or {}).get(kind)
        if qualifier:
            event["note"] = " · ".join(filter(None, (event.get("note"), qualifier)))
        if kind == "death" and re.match(r"(?:before|after)\b", str(event.get("date") or ""), re.I):
            event["label"] = "Death boundary (not a recorded death)"
        matched = _matching_record(event, rows)
        event_type = str(event.get("event_type") or "").casefold()
        if matched and event_type in {"birth", "death", "marriage"}:
            record_id = _record_id(matched)
            consumed.add(record_id)
            context = _record_context(matched)
            add(
                context.get("timeline_group") or "Life events",
                date=event.get("date") or matched.get("date") or matched.get("year"),
                year=event.get("year") or matched.get("year"),
                record_id=record_id,
                title=matched.get("association") or event.get("label") or event_type or "Recorded event",
                role=event.get("role") or context.get("role") or "Subject",
                place=event.get("place") or matched.get("place") or matched.get("record_location") or "",
                note=matched.get("note") or event.get("note") or "",
                url=matched.get("source_url") or event.get("source_url") or "",
            )
            continue
        if matched and event.get("source_url") and str(event.get("source_url")) == str(matched.get("source_url")):
            continue
        add(
            "Life events" if event.get("kind") == "personal" else "Collateral records",
            date=event.get("date") or event.get("raw_date") or event.get("year"),
            year=event.get("year") or 9999,
            record_id=event.get("evidence_id") or "",
            title=event.get("label") or event.get("event_type") or "Recorded event",
            role=event.get("role") or "Subject",
            place=event.get("place") or "",
            note=event.get("note") or "",
            url=event.get("source_url") or "",
        )
    modern = []
    for row in rows:
        record_id = _record_id(row)
        if record_id in consumed:
            continue
        if record_id.startswith("correspondence"):
            modern.append(row)
            continue
        context = _record_context(row)
        group = context.get("timeline_group") or _default_timeline_group(row)
        add(
            group,
            date=row.get("date") or row.get("year"),
            year=row.get("year") or 9999,
            record_id=record_id,
            title=row.get("association") or "Recorded association",
            role=_timeline_role(row, context),
            place=row.get("place") or row.get("record_location") or "",
            note=_public_record_note(row),
            url=row.get("source_url") or "",
        )
    for values in groups.values():
        values.sort(key=lambda e: (*_date_sort_key(e.get("sort_date"), e.get("year")), str(e["title"]).casefold(), str(e["record_id"])))
    def group_html(title: str, items: list[dict]) -> str:
        if not items:
            return ""
        rendered = []
        for event in items:
            links = []
            if event.get("record_id") and event["record_id"] in source_by_record:
                links.append(_a(f'#{source_by_record[event["record_id"]]}', "Source register"))
            if event.get("url"):
                links.append(_a(event["url"], "Open record", True))
            note = f'<details class="record-detail"><summary>Record detail</summary><p>{escape(str(event["note"]))}</p></details>' if event.get("note") else ""
            link_html = f'<div class="source-links">{" · ".join(links)}</div>' if links else ""
            anchor = f' id="timeline-{escape(_safe_slug(event.get("record_id") or event.get("title")))}"' if event.get("record_id") else ""
            place_html = f'<p class="timeline-meta">{escape(str(event["place"]))}</p>' if event.get("place") else ""
            rendered.append(f'<div class="timeline-row" data-group="{escape(event["group"])}"{anchor}><time>{escape(str(event["date"]))}</time><div><h3>{escape(str(event["title"]))}</h3><p class="timeline-role">{escape(str(event["role"]))}</p><span class="record-kind">{escape(event["group"])}</span>{place_html}{note}{link_html}</div></div>')
        return f'<div class="timeline-group"><h3>{escape(title)}</h3>{"".join(rendered)}</div>'
    historical = sorted((event for group in groups.values() for event in group), key=lambda e: (*_date_sort_key(e.get("sort_date"), e.get("year")), str(e["title"]).casefold(), str(e["record_id"])))
    # Modern activity remains in the research/evidence/source account, never
    # appended to the life chronology.
    return group_html("Historical chronology", historical)


def _research_html(editorial: dict) -> str:
    tasks = editorial.get("research_tasks") or []
    task_html = []
    for task in tasks:
        scope = task.get("scope") or ("DNA" if "DNA" in str(task.get("what")) or "kit" in str(task.get("what")) else "Documentary")
        status_meta = f' · {task.get("status_date")}' if task.get("status_date") else ""
        superseded = f'<p class="relation-note"><span class="task-label">Superseding result</span> {escape(task.get("superseded_by"))}</p>' if task.get("superseded_by") else ""
        task_html.append(f'<li class="task"><div class="task-head"><strong>{escape(str(task.get("priority") or ""))}. {escape(task.get("what") or "Research task")}</strong><span class="task-label">{escape(scope)}</span><span class="status-label status-{escape(_status_class(task.get("status")))}">{escape(str(task.get("status") or "Status not recorded"))}{escape(status_meta)}</span></div><p><span class="task-label">Question tested</span> {escape(task.get("tests") or "Not specified.")}</p><p><span class="task-label">What would matter</span> {escape(task.get("matters") or "Not specified.")}</p>{superseded}{f'<p class="relation-note"><span class="task-label">Provenance</span> {escape(task.get("provenance"))}</p>' if task.get("provenance") else ""}</li>')
    logs = editorial.get("completed_searches") or []
    log_html = "".join(f'<tr><td>{escape(str(item.get("date") or "Undated"))}</td><td>{escape(item.get("scope") or item.get("search") or "Search")}</td><td>{escape(item.get("result") or "")}</td><td>{escape(item.get("limitation") or "")}</td></tr>' for item in logs)
    task_block = f'<ol class="task-list">{"".join(task_html)}</ol>' if task_html else '<p class="dossier-empty">No active task is recorded.</p>'
    log_block = f'<div class="table-wrap"><table class="source-table research-log"><thead><tr><th>Date</th><th>Scope</th><th>Result</th><th>Limitation</th></tr></thead><tbody>{log_html}</tbody></table></div>' if log_html else '<p class="dossier-empty">No completed search log is recorded.</p>'
    completed_block = f'<h3>Completed searches and review log</h3>{log_block}' if log_html else ""
    return f'<h3>Active research priorities</h3>{task_block}{completed_block}'


def _sources_html(rows: list[dict], sources: list[dict], source_by_record: dict[str, str], editorial: dict) -> str:
    if not sources: return '<p class="dossier-empty">No external source URL is available in the public source register.</p>'
    claims = defaultdict(list)
    for question in editorial.get("evidence_questions") or []:
        qid = question.get("id")
        for record_id in question.get("records", []):
            if record_id in source_by_record:
                claims[source_by_record[record_id]].append(f"record-{_safe_slug(record_id)}-{_safe_slug(qid)}")
    rendered = []
    for source in sources:
        used_links = []
        for claim in dict.fromkeys(claims.get(source["key"], [])):
            used_links.append(_a(f"#{claim}", "Claim: " + claim.removeprefix("record-")))
        origin = _a(source["url"], "Open cited record or transcription", True) if source["url"] else ('<span class="source-claims">Correspondence summary; raw message withheld</span>' if source.get("private") else '<span class="source-claims">Public image or transcription link not available</span>')
        timeline_href = f"#timeline-{_safe_slug(source['record_id'])}"
        timeline_link = "" if str(source["record_id"]).startswith("correspondence") else f' · {_a(timeline_href, "Back to chronology")}'
        claims_html = f' · <span class="source-claims">Used by: {" · ".join(used_links)}</span>' if used_links else ""
        meta = " · ".join(str(value) for value in (source["date"], source["place"], source["status"]) if value)
        rendered.append(f'<li id="{escape(source["key"])}"><h3>{escape(source["title"])}</h3><p>{escape(meta)}</p><p>{escape(source["note"])}</p><div class="source-links">{origin}{timeline_link}{claims_html}</div></li>')
    return '<ol class="source-register">' + "".join(rendered) + '</ol><p class="relation-note">Each entry is a separately identified record. Shared URLs may represent one transcription or search page containing more than one record; they are not independent confirmations.</p>'


_MARKDOWN = MarkdownIt("commonmark").enable("table")
_MARKDOWN_TAGS = {"a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4", "h5", "hr", "li", "ol", "p", "pre", "strong", "table", "tbody", "td", "th", "thead", "tr", "ul"}
_MARKDOWN_ATTRS = {"a": {"href", "title"}}


def _safe_markdown_html(markdown_text: str, base_url: str) -> str:
    """Parse Markdown and sanitise the resulting HTML without touching URLs."""
    readable = re.sub(r"<ref(?:\s+[^>]*)?>(.*?)</ref>", r"\1", markdown_text or "", flags=re.I | re.S)
    readable = re.sub(r"\[\[([A-Za-z]+-[0-9]+)\|([^\]]+)\]\]", lambda m: f"[{m.group(2)}](/people/{m.group(1).casefold()}.html)", readable)
    readable = re.sub(r"\[\[([A-Za-z]+-[0-9]+)\]\]", lambda m: f"[{m.group(1)}](/people/{m.group(1).casefold()}.html)", readable)
    rendered = _MARKDOWN.render(readable)
    soup = BeautifulSoup(rendered, "html.parser")
    for tag in list(soup.find_all(True)):
        if tag.name not in _MARKDOWN_TAGS:
            if tag.name in {"script", "style", "iframe", "object", "embed", "form"}:
                tag.decompose()
            else:
                tag.unwrap()
            continue
        allowed = _MARKDOWN_ATTRS.get(tag.name, set())
        for attribute in list(tag.attrs):
            if attribute not in allowed:
                del tag.attrs[attribute]
        if tag.name == "a":
            href = str(tag.get("href") or "")
            if href.lower().startswith(("javascript:", "data:", "vbscript:")):
                tag.unwrap()
            else:
                tag["href"] = href if href.startswith("#") else urljoin(base_url, href)
    return str(soup)


def _biography_figure_html(profile_id: str, figure: dict) -> str:
    """Publish a maintained local illustration and give it an accessible caption."""
    filename = str(figure.get("file") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:svg|png|jpg|webp)", filename):
        return ""
    source = ROOT / "research" / profile_id / "figures" / filename
    if not source.is_file():
        return ""
    destination = WEB / "assets/research/figures" / profile_id.casefold() / filename
    payload = source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.read_bytes() != payload:
        destination.write_bytes(payload)
    href = "/" + destination.relative_to(WEB).as_posix()
    mobile = str(figure.get("mobile_file") or "")
    mobile_source = ""
    if re.fullmatch(r"[A-Za-z0-9_-]+\.(?:svg|png|jpg|webp)", mobile):
        mobile_path = source.parent / mobile
        if mobile_path.is_file():
            mobile_destination = destination.parent / mobile
            mobile_bytes = mobile_path.read_bytes()
            if not mobile_destination.exists() or mobile_destination.read_bytes() != mobile_bytes:
                mobile_destination.write_bytes(mobile_bytes)
            mobile_href = "/" + mobile_destination.relative_to(WEB).as_posix()
            mobile_source = f'<source media="(max-width:680px)" srcset="{mobile_href}">'
    caption = _safe_markdown_html(str(figure.get("caption") or ""), f"/research/{profile_id}/")
    alt = escape(str(figure.get("alt") or figure.get("title") or "Evidence diagram"), quote=True)
    return f'<figure class="biography-figure"><a href="{href}" aria-label="Open illustration at full size"><picture>{mobile_source}<img src="{href}" alt="{alt}" loading="lazy"></picture></a><figcaption>{caption}</figcaption></figure>'


def _record_excerpt_html(profile_id: str, excerpt_id: str) -> str:
    """Render reviewed source pixels with optional, removable reading guides."""
    directory = ROOT / "research" / profile_id / "record-excerpts"
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return ""
    manifest = json.loads(manifest_path.read_text())
    entries = manifest.get("excerpts", []) if isinstance(manifest, dict) else manifest
    item = next((entry for entry in entries if entry.get("id") == excerpt_id), None)
    if not item:
        return ""
    filename = str(item.get("file") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp)", filename):
        return ""
    source = directory / filename
    if not source.is_file():
        return ""
    width, height = int(item.get("width") or 0), int(item.get("height") or 0)
    if width <= 0 or height <= 0:
        return ""
    destination = WEB / "assets/research/record-excerpts" / profile_id.casefold() / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = source.read_bytes()
    if not destination.is_file() or destination.read_bytes() != payload:
        destination.write_bytes(payload)
    href = "/" + destination.relative_to(WEB).as_posix()
    ident = "excerpt-" + _safe_slug(excerpt_id)
    boxes, legend = [], []
    for number, box in enumerate(item.get("highlights") or [], 1):
        x, y, w, h = (float(box.get(key) or 0) for key in ("x", "y", "width", "height"))
        if not (0 <= x < width and 0 <= y < height and w > 0 and h > 0 and x + w <= width and y + h <= height):
            continue
        label = escape(str(box.get("label") or "Reading guide"))
        boxes.append(f'<span class="record-highlight" data-guide="{number}" style="left:{100*x/width:.4f}%;top:{100*y/height:.4f}%;width:{100*w/width:.4f}%;height:{100*h/height:.4f}%"><b>{number}</b></span>')
        legend.append(f'<option value="{number}">{number}. {label}</option>')
    title = escape(str(item.get("title") or "Original record excerpt"))
    alt = escape(str(item.get("alt") or item.get("title") or "Original record excerpt"), quote=True)
    body = []
    for key, label in (("transcription", "Reading"), ("analysis", "Why it matters"), ("uncertainties", "Limits of this excerpt")):
        if item.get(key):
            body.append(f'<div class="record-{key}"><h4>{label}</h4>{_safe_markdown_html(str(item[key]), f"/research/{profile_id}/")}</div>')
    attribution = " · ".join(str(item.get(key) or "") for key in ("archive", "record_reference") if item.get(key))
    source_url = str(item.get("source_url") or "")
    origin = _a(source_url, "Full original record", True) if source_url.startswith(("https://", "http://")) else ""
    guide_control = f'<label>Reading guide <select data-record-guide aria-label="Reading guide" aria-controls="{ident}-image"><option value="">Original — no guide</option>{"".join(legend)}</select></label>' if boxes else ""
    context_link = ""
    context_file = str(item.get("context_file") or "")
    if re.fullmatch(r"[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp)", context_file) and (directory / context_file).is_file():
        context_destination = destination.parent / context_file
        context_destination.write_bytes((directory / context_file).read_bytes())
        context_link = " · " + _a("/" + context_destination.relative_to(WEB).as_posix(), "Wider record excerpt")
    return f'<figure class="record-excerpt" id="{ident}" style="--record-width:{min(width, 1600)}px"><h3>{title}</h3><div class="record-controls">{guide_control}<label><input class="record-enlarge" type="checkbox" aria-controls="{ident}-image"> Enlarge excerpt</label>{_a(href, "Open image at full size")}</div><div class="record-viewport" tabindex="0" aria-label="Scrollable original record excerpt"><div class="record-stage" id="{ident}-image"><img src="{href}" alt="{alt}" width="{width}" height="{height}" loading="lazy"><div class="record-guides-layer" aria-hidden="true">{"".join(boxes)}</div></div></div><figcaption><p class="record-provenance">{escape(attribution)} · {origin}{context_link}. Original pixels; reading guides are removable.</p>{"".join(body)}</figcaption></figure>'


def _biography_sections_html(profile_id: str, editorial: dict, used_ids: set[str]) -> list[tuple[str, str, str, dict]]:
    """Render authored narrative sections as part of the current dossier view."""
    rendered_sections = []
    for number, item in enumerate(editorial.get("biography_sections") or [], start=1):
        if not isinstance(item, dict) or not str(item.get("markdown") or "").strip():
            continue
        for attachment in item.get("downloads") or []:
            filename = str(attachment.get("file") or "")
            public_file = str(attachment.get("public_file") or filename)
            if not all(re.fullmatch(r"[A-Za-z0-9_-]+\.(?:json|csv)", name) for name in (filename, public_file)):
                continue
            source = ROOT / "research" / profile_id / filename
            if source.is_file():
                destination = WEB / "assets/research" / public_file
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
        title = str(item.get("title") or "Biography")
        requested_id = _safe_slug(str(item.get("id") or title or f"biography-{number}"))
        if not re.match(r"[a-z]", requested_id):
            requested_id = "section-" + requested_id
        section_id = requested_id
        suffix = 2
        while section_id in used_ids:
            section_id = f"{requested_id}-{suffix}"
            suffix += 1
        used_ids.add(section_id)
        soup = BeautifulSoup(
            _safe_markdown_html(str(item["markdown"]), f"/research/{profile_id}/"), "html.parser"
        )
        for figure in item.get("figures") or []:
            if not isinstance(figure, dict):
                continue
            marker = "{{figure:" + str(figure.get("file") or "") + "}}"
            placeholder = next((p for p in soup.find_all("p") if p.get_text().strip() == marker), None)
            rendered = BeautifulSoup(_biography_figure_html(profile_id, figure), "html.parser")
            if placeholder is not None:
                placeholder.replace_with(rendered)
            elif rendered.contents:
                soup.append(rendered)
        for excerpt_id in item.get("record_excerpts") or []:
            marker = "{{record:" + str(excerpt_id) + "}}"
            placeholder = next((p for p in soup.find_all("p") if p.get_text().strip() == marker), None)
            rendered = BeautifulSoup(_record_excerpt_html(profile_id, str(excerpt_id)), "html.parser")
            if placeholder is not None:
                placeholder.replace_with(rendered)
            elif rendered.contents:
                soup.append(rendered)
        for table in soup.select("table"):
            table["class"] = list(dict.fromkeys((table.get("class") or []) + ["biography-table"]))
            headers = [header.get_text(" ", strip=True) for header in table.select("thead th")]
            for header in table.select("thead th"):
                header["scope"] = "col"
            if not table.select_one("caption"):
                caption = soup.new_tag("caption")
                caption.string = f"{title} table"
                table.insert(0, caption)
            for row in table.select("tbody tr"):
                for index, cell in enumerate(row.select(":scope > td")):
                    if index < len(headers):
                        cell["data-label"] = headers[index]
            wrapper = soup.new_tag("div", attrs={"class": "biography-table-wrap"})
            table.wrap(wrapper)
        rendered_sections.append((section_id, title, str(soup), item.get("reading_summary") or {}))
    return rendered_sections


def _research_note_anchor(path: str, title: str) -> str:
    return "research-note-" + hashlib.sha256((path.lstrip("/") + "|" + title).encode()).hexdigest()[:12]


def _archive_html(profile_id: str, dossier: dict, editorial: dict, supplements: str = "") -> str:
    findings, blocks = dossier.get("research_findings") or [], []
    superseded = editorial.get("superseded_interpretations") or []
    for finding in findings:
        source_path = finding.get("source_path") or f"/research/{profile_id}/findings.md"
        source_path = "/" + source_path.lstrip("/")
        base_url = source_path if source_path.endswith("/") else source_path.rsplit("/", 1)[0] + "/"
        for section in finding.get("sections", []):
            title = section.get("title") or "Research note"
            markdown_text = section.get("markdown") or ""
            if not markdown_text.strip():
                continue
            category = section.get("category") or "research note"
            rendered = _safe_markdown_html(markdown_text, base_url)
            anchor = _research_note_anchor(source_path, title)
            blocks.append(f'<details id="{anchor}"><summary>{escape(category.title())}: {escape(title)}</summary><div class="archive-copy">{rendered}<details class="archive-original"><summary>Original Markdown</summary><pre>{escape(markdown_text)}</pre></details></div></details>')
    update = dossier.get("wikitree_update") or {}; draft = update.get("draft_wikitext") or ""
    automated = dossier.get("potential_parentage") or {}
    reviewed_candidates = {c["score_profile_id"]: c for c in editorial.get("parent_candidates", []) if c.get("score_profile_id")}
    candidates = []
    for candidate in automated.get("candidates") or []:
        reviewed = reviewed_candidates.get(candidate.get("id"))
        verdict = f' · Reviewed: {reviewed["assessment"]}' if reviewed else ''
        candidates.append(f'{candidate.get("name") or candidate.get("id")}: {candidate.get("score", "—")}/100 · Stored classification: {candidate.get("classification") or "automated lead"}{verdict}')
    raw_json = json.dumps({key: dossier.get(key) for key in ("id", "vitals", "relationships", "claims", "research_assessments", "shared_relationship_assertions", "relationship_history")}, ensure_ascii=False, indent=2)
    parts = ['<p class="archive-note">This material is retained for audit and future research. It is not a second current conclusion. Imported values, automated comparisons and raw exports do not override the reviewed presentation above.</p>']
    if supplements:
        parts.append(supplements)
    editorial_corrections = editorial.get("editorial_corrections") or []
    if editorial_corrections:
        corrections = []
        for item in editorial_corrections:
            anchor = "editorial-correction-" + _safe_slug(item.get("id") or item.get("label") or "issue")
            corrections.append(f'<article id="{escape(anchor)}"><p><strong>{escape(item.get("label") or "Editorial correction")}</strong>: {escape(item.get("correction") or "")}</p><p class="relation-note">{escape(item.get("source") or "Source not stated")}</p></article>')
        parts.append('<details><summary>Editorial corrections</summary><div class="archive-body">' + "".join(corrections) + '</div></details>')
    if superseded:
        correction_blocks = []
        for item in superseded:
            anchor = "correction-" + _safe_slug(item.get("id") or item.get("label") or "issue")
            rejected = item.get("rejected_claim") or item.get("claim") or "The earlier interpretation"
            operative = item.get("operative_correction") or item.get("correction") or "The correction remains operative."
            unaffected = item.get("unaffected") or "Other findings are not changed by this correction."
            correction_blocks.append(f'<article id="{escape(anchor)}"><p><strong>{escape(item.get("label") or "Correction")}</strong></p><p><span class="task-label">Rejected interpretation</span> {escape(rejected)}</p><p><span class="task-label">Operative correction</span> {escape(operative)}</p><p><span class="task-label">Unaffected</span> {escape(unaffected)}</p><p class="relation-note">{escape(item.get("source") or "Source not stated")}</p></article>')
        parts.append('<details><summary>Resolved corrections and editorial issues</summary><div class="archive-body">' + "".join(correction_blocks) + '</div></details>')
    if blocks: parts.append('<details><summary>Research notes and earlier assessments</summary><div class="archive-body">' + "".join(blocks) + '</div></details>')
    if candidates: parts.append('<details><summary>Automated parent comparison (research aid, not a recommendation)</summary><div class="archive-copy"><p>Stored scores are preserved for audit only. They are not probabilities or genealogical evidence, and a reviewed exclusion remains excluded.</p><ul>' + "".join(f'<li>{escape(line)}</li>' for line in candidates) + '</ul></div></details>')
    if draft: parts.append(f'<details><summary>Prepared WikiTree copy/export</summary><div class="archive-copy"><button class="copy-wikitree" data-copy-wikitree="wikitree-export">Copy WikiTree text</button><textarea id="wikitree-export" aria-label="Original WikiTree export" rows="24" readonly>{escape(draft)}</textarea></div></details>')
    slug = str(dossier.get("catalogue_id") or profile_id).casefold()
    parts.append(f'<details><summary>Structured dossier and technical data</summary><div class="archive-copy"><p><a href="/people/{escape(slug)}.json">Machine-readable dossier</a> · <a href="/people/{escape(slug)}.network.json">Family network</a></p><pre class="archive-json">{escape(raw_json)}</pre></div></details>')
    return '<details id="archive-tools" class="dossier-archive"><summary><span>Archive and research tools<small>Earlier assessments, imports, comparisons and exports</small></span></summary><div class="archive-body">' + "".join(parts) + '</div></details>'


def render_person_dossier(profile_id: str) -> str:
    dossier, model, index = _profile_data(profile_id)
    if not dossier:
        return ""
    editorial = _editorial(dossier.get("id") or profile_id)
    authored = editorial.get("reading_mode") == "authored" and bool(editorial.get("biography_sections"))
    guide = editorial.get("reading_guide")
    section_ids = [str(item.get("id") or "") for item in editorial.get("biography_sections") or []]
    groups = (guide or {}).get("groups") if isinstance(guide, dict) else None
    valid_groups = isinstance(groups, list) and all(isinstance(group, dict) and isinstance(group.get("id"), str) and isinstance(group.get("title"), str) and isinstance(group.get("purpose"), str) and isinstance(group.get("section_ids"), list) and all(isinstance(sid, str) for sid in group.get("section_ids")) for group in groups)
    covered = [sid for group in groups for sid in group["section_ids"]] if valid_groups else []
    valid_summaries = all(isinstance(item.get("reading_summary"), dict) and all(isinstance(item["reading_summary"].get(key), str) and item["reading_summary"].get(key) for key in ("question", "finding", "purpose")) for item in editorial.get("biography_sections") or [])
    valid_guide = isinstance(guide, dict) and guide.get("mode") == "summary-disclosures" and isinstance(guide.get("hypothesis"), str) and isinstance(guide.get("current_answer"), str) and bool(guide["hypothesis"]) and bool(guide["current_answer"]) and valid_groups and len({group["id"] for group in groups}) == len(groups) and len(covered) == len(section_ids) and len(set(covered)) == len(covered) and set(covered) == set(section_ids) and valid_summaries
    if not valid_guide:
        guide = None
    rows = _record_rows(dossier.get("id") or profile_id)
    source_by_record, sources = _record_source_map(rows)
    name = dossier.get("name") or model.get("name") or profile_id
    vitals = dossier.get("vitals") or {}
    model_vitals = _current_vitals(profile_id, dossier, model, editorial)

    def date_label(kind):
        item = model_vitals.get(kind) or vitals.get(kind) or {}
        value = item.get("display_date") or item.get("date")
        formatted = _format_date_value(value) or "Date not established"
        return formatted + (f" ({item['qualifier']})" if item.get("qualifier") else "")

    birth = date_label("birth"); death = date_label("death")
    birth_place = (model_vitals.get("birth") or vitals.get("birth") or {}).get("place")
    death_place = (model_vitals.get("death") or vitals.get("death") or {}).get("place")
    assessment_date = editorial.get("assessment_date") or ""
    wiki = dossier.get("wikitree_url") or ""
    opening = editorial.get("opening") or ""
    position = editorial.get("position") or {"answer": "No maintained assessment is recorded.", "points": []}
    def fact_value(date_value, place_value):
        return date_value + (f" · {place_value}" if place_value else "")
    fact_entries = [("Birth", fact_value(birth, birth_place)), ("Death", fact_value(death, death_place))]
    if editorial.get("name_variants"):
        fact_entries.append(("Recorded names", "; ".join(str(value) for value in editorial["name_variants"])))
    if editorial.get("principal_locality") or birth_place or death_place:
        fact_entries.append(("Locality", editorial.get("principal_locality") or birth_place or death_place))
    if assessment_date:
        fact_entries.append(("Assessment", str(assessment_date)))
    facts = ''.join(f'<div class="dossier-fact"><strong>{escape(label)}</strong><span>{escape(str(value))}</span></div>' for label, value in fact_entries if value)
    slug = str(dossier.get("catalogue_id") or profile_id).casefold()
    family_anchor = _safe_slug(editorial.get("family_section") or "family") if authored else "family"
    actions = ([ _a(wiki, "View on WikiTree", True) ] if wiki else []) + [_a(f"/people/{slug}.html#{family_anchor}", "Explore family"), _a("#archive-tools", "Research/export tools")]
    family_body = _family_html(dossier.get("id") or profile_id, dossier, model, index, editorial, source_by_record)
    parent_body = _parent_comparison_html(editorial, dossier)
    evidence_body = _evidence_questions(editorial, rows, source_by_record)
    timeline_body = _timeline_html(dossier.get("id") or profile_id, model, rows, source_by_record)
    research_body = _research_html(editorial)
    sources_body = _sources_html(rows, sources, source_by_record, editorial)
    has_family = "relation-table" in family_body
    has_evidence = bool(editorial.get("evidence_questions"))
    has_timeline = bool(timeline_body)
    has_research = bool(editorial.get("research_tasks") or editorial.get("completed_searches"))
    has_sources = bool(sources)
    resolution = editorial.get("resolution") or {}
    state_note = ""
    if resolution.get("state") == "unmapped":
        state_note = '<p class="relation-note assessment-state">Research is available, but no publication-safe conclusion has yet been resolved.</p>'
    elif resolution.get("state") == "conflict":
        state_note = '<p class="relation-note assessment-state">Assessment status: maintained research conflicts; the issue is intentionally unresolved.</p>'
    elif resolution.get("state") == "none":
        state_note = '<p class="relation-note assessment-state">Assessment status: no maintained assessment is present in the published research model.</p>'
    section_nav = '<a href="#overview">Overview</a>'
    toc_nav = '<a href="#overview">Overview</a>'
    summary = opening or str(position.get("answer") or "")
    guide_html = ""
    if guide:
        guide_html = '<div class="reading-guide-intro"><p>Choose a question below; open its full evidence.</p><p><strong>Main hypothesis:</strong> ' + escape(str(guide.get("hypothesis") or "")) + '</p><p><strong>Current answer:</strong> ' + escape(str(guide.get("current_answer") or "")) + '</p><div class="reading-guide-actions" data-reading-controls hidden><button type="button" data-reading-expand>Expand all</button><button type="button" data-reading-collapse>Collapse all</button></div><noscript><p>JavaScript is disabled; open linked sections manually to reveal their evidence.</p></noscript></div>'
    sections = ['<section id="overview" class="dossier-section"><h2>Current position</h2><p class="dossier-lede">' + escape(summary) + '</p>' + guide_html + state_note + f'<div class="dossier-facts">{facts}</div></section>']
    biography_sections = _biography_sections_html(
        dossier.get("id") or profile_id, editorial,
        {"overview", "family", "evidence", "parent-candidates", "timeline", "research", "sources", "archive-tools"},
    )
    nav_titles = {item.get("id"): item.get("nav_title") for item in editorial.get("biography_sections", [])}
    group_by_section = {sid: group for group in (guide or {}).get("groups", []) for sid in group.get("section_ids", [])}
    emitted_groups = set()
    for section_id, title, body, reading_summary in biography_sections:
        nav_title = nav_titles.get(section_id) or title
        section_nav += f'<a href="#{escape(section_id)}">{escape(nav_title)}</a>'
        toc_nav += f'<a href="#{escape(section_id)}">{escape(nav_title)}</a>'
        group = group_by_section.get(section_id)
        group_html = ""
        if group and group.get("id") not in emitted_groups:
            emitted_groups.add(group.get("id")); group_html = f'<h3 class="reading-group-title" id="reading-group-{escape(str(group.get("id")))}">{escape(str(group.get("title") or ""))}</h3><p class="reading-group-purpose">{escape(str(group.get("purpose") or ""))}</p>'
        if guide and reading_summary:
            rs = ''.join(f'<span class="reading-summary-{key}"><strong>{label}:</strong> {escape(str(reading_summary.get(key) or ""))}</span>' for key, label in (("question", "Question"), ("finding", "Finding"), ("purpose", "Purpose")) if reading_summary.get(key))
            content = f'<details class="biography-disclosure"><summary><span>{escape(title)}</span><small>{rs}</small></summary><div class="biography-content">{body}</div></details>'
        else:
            content = f'<div class="biography-content">{body}</div>'
        sections.append(f'<section id="{escape(section_id)}" class="dossier-section biography-section">{group_html}<h2>{escape(title)}</h2>{content}</section>')
    supplements = []
    if authored:
        # Preserve existing deep links and unique supporting material without
        # presenting the former summaries as a second current account.
        for ident, title, body in (
            ("family", "Relationship register and imported attachments", family_body),
            ("evidence", "Earlier evidence summaries and record associations", evidence_body),
            ("parent-candidates", "Detailed candidate research and score audit", parent_body),
            ("timeline", "Full documentary index, including collateral records", timeline_body),
            ("research", "Search history and the wider research register", research_body),
        ):
            if body:
                supplements.append(f'<details id="{ident}" class="supporting-register"><summary>{title}</summary><div class="archive-copy">{body}</div></details>')
        has_family = has_evidence = has_timeline = has_research = False
        parent_body = ""
    if has_family:
        section_nav += '<a href="#family">Family</a>'; toc_nav += '<a href="#family">Family and relationships</a>'
        sections.append(f'<section id="family" class="dossier-section"><h2>Family and relationships</h2>{family_body}</section>')
    if has_evidence:
        section_nav += '<a href="#evidence">Evidence</a>'; toc_nav += '<a href="#evidence">Evidence and reasoning</a>'
        sections.append(f'<section id="evidence" class="dossier-section"><h2>Evidence and reasoning</h2>{evidence_body}</section>')
    if parent_body:
        section_nav += '<a href="#parent-candidates">Possible father</a>'; toc_nav += '<a href="#parent-candidates">Possible father</a>'
        sections.append(f'<section id="parent-candidates" class="dossier-section"><h2>Possible father</h2>{parent_body}</section>')
    if has_timeline:
        section_nav += '<a href="#timeline">Timeline</a>'; toc_nav += '<a href="#timeline">Life and records</a>'
        sections.append(f'<section id="timeline" class="dossier-section"><h2>Life and records</h2><details class="section-details"><summary><span>Explore the dated records<small>Chronology, roles and locations</small></span></summary>{timeline_body}</details></section>')
    if has_research:
        section_nav += '<a href="#research">Research</a>'; toc_nav += '<a href="#research">Research still needed</a>'
        sections.append(f'<section id="research" class="dossier-section"><h2>Research still needed</h2><details class="section-details"><summary><span>Research priorities and completed searches<small>Open questions, searches and next evidence</small></span></summary>{research_body}</details></section>')
    if has_sources:
        section_nav += '<a href="#sources">Sources</a>'; toc_nav += '<a href="#sources">Sources</a>'
        sections.append(f'<section id="sources" class="dossier-section"><h2>Sources</h2><details class="section-details"><summary><span>Browse {len(sources)} source records<small>Citations, provenance and limitations</small></span></summary>{sources_body}</details></section>')
    section_nav += '<a href="#archive-tools">Archive and tools</a>'; toc_nav += '<a href="#archive-tools">Archive and tools</a>'
    locality = editorial.get("principal_locality") or birth_place or death_place or ""
    life = " – ".join(value for value in (str(birth), str(death)) if value != "Date not established") or "Dates not established"
    qualifier = (model_vitals.get("birth") or {}).get("qualifier")
    if qualifier and birth.endswith(f" ({qualifier})") and death.endswith(f" ({qualifier})"):
        life = birth.removesuffix(f" ({qualifier})") + " – " + death
    script = '''<script>(function(){var printing=false;function openHash(){var id;try{id=decodeURIComponent(location.hash.slice(1));}catch(e){return;}var target=document.getElementById(id);if(!target)return;for(var node=target;node;node=node.parentElement){if(node.tagName==="DETAILS")node.open=true;}if(target.matches(".dossier-section")){var d=target.querySelector(":scope > .biography-disclosure");if(d)d.open=true;}requestAnimationFrame(function(){target.scrollIntoView({block:"start"});});}function all(open){document.querySelectorAll(".dossier-reading details").forEach(function(d){d.open=open;});}function printOpen(){if(printing)return;printing=true;document.querySelectorAll(".person-dossier-readable[data-dossier-presentation] .dossier-reading details").forEach(function(d){d.dataset.printWasOpen=d.open?"1":"0";d.open=true;});}function printRestore(){if(!printing)return;document.querySelectorAll(".person-dossier-readable[data-dossier-presentation] .dossier-reading details").forEach(function(d){d.open=d.dataset.printWasOpen==="1";d.removeAttribute("data-print-was-open");});printing=false;}function init(){openHash();var c=document.querySelector("[data-reading-controls]");if(c){c.hidden=false;c.querySelector("[data-reading-expand]").onclick=function(){all(true)};c.querySelector("[data-reading-collapse]").onclick=function(){all(false)}}}if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();window.addEventListener("hashchange",openHash);window.addEventListener("beforeprint",printOpen);window.addEventListener("afterprint",printRestore);})();</script>'''
    locality_href = editorial.get("principal_locality_href") or ""
    locality_value = _a(locality_href, str(locality)) if locality and locality_href else escape(str(locality))
    locality_html = f'<p class="dossier-locality">{locality_value}</p>' if locality else ""
    assessment_meta = f'<span>Research assessment: <time>{escape(str(assessment_date))}</time></span>' if assessment_date else ""
    return f'''<nav class="crumb"><a href="/catalogue/">People catalogue</a> / {escape(name)}</nav><article class="person-dossier-readable" data-dossier-presentation="{PRESENTATION_VERSION}"><header class="dossier-header"><p class="kicker">Person dossier · {escape(profile_id)}</p><h1>{escape(name)}</h1><p class="dossier-life">{escape(life)}</p>{locality_html}<div class="dossier-meta">{assessment_meta}</div><div class="dossier-actions">{"".join(actions)}</div></header><nav class="dossier-nav" aria-label="On this page">{section_nav}</nav><div class="dossier-layout"><aside class="dossier-toc" aria-label="Dossier contents">{toc_nav}</aside><div class="dossier-reading">{"".join(sections)}{_archive_html(profile_id, dossier, editorial, "".join(supplements))}</div></div></article>{script}'''


def _replace_main(text: str, profile_id: str) -> str:
    soup = BeautifulSoup(text, "html.parser"); main = soup.select_one("main.v3-dossier") or soup.select_one("main.person-dossier") or soup.select_one("main")
    if not main: return text
    rendered = render_person_dossier(profile_id)
    if not rendered: return text
    replacement = BeautifulSoup(rendered, "html.parser"); main.clear()
    for child in list(replacement.contents): main.append(child)
    main["class"] = list(dict.fromkeys((main.get("class") or []) + ["person-hierarchy", "person-dossier-readable"]))
    soup.body["class"] = list(dict.fromkeys((soup.body.get("class") or []) + ["person-hierarchy"]))
    soup.body["data-r-person"] = profile_id
    soup.body["data-g-path"] = f"/people/{profile_id.casefold()}.html"
    name_node = replacement.select_one("h1")
    name = name_node.get_text(" ", strip=True) if name_node else profile_id
    bar_label = soup.select_one(".g-bar .g-crumbs strong")
    if bar_label:
        bar_label.string = name
    for link in soup.select(".g-nav-link[aria-current]"):
        del link["aria-current"]
    people_link = soup.select_one('.g-nav-link[href="/catalogue/"]')
    if people_link:
        people_link["aria-current"] = "page"
    soup.body["data-g-person"] = json.dumps({
        "id": profile_id,
        "name": name,
        "url": f"/people/{profile_id.casefold()}.html",
        "tree": not profile_id.casefold().startswith("record-"),
    })
    for old_asset in soup.select('link[href^="/assets/repair/person-hierarchy.css"]'):
        old_asset.decompose()
    soup.head.append(soup.new_tag("link", rel="stylesheet", href=ASSET))
    return str(soup)


def revise(text: str, profile_id_hint: str = ""):
    match = re.search(r'data-r-person=["\']([^"\']+)', text)
    if "main" not in text: return text, False
    profile_id = match.group(1) if match else profile_id_hint
    if not profile_id: return text, False
    if not (WEB / "people" / f"{profile_id.casefold()}.json").exists(): return text, False
    updated = _replace_main(text, profile_id)
    return updated, updated != text


def repair(profile_ids=None):
    global _INDEX_CACHE
    publish(WEB)
    _refresh_reviewed_parentage(profile_ids)
    _INDEX_CACHE = None
    counts = {"person_hierarchy": 0}; asset = WEB / "assets/repair/person-hierarchy.css"; asset.parent.mkdir(parents=True, exist_ok=True)
    if not asset.exists() or asset.read_text(encoding="utf-8") != CSS: asset.write_text(CSS, encoding="utf-8")
    for path in sorted((WEB / "people").glob("*.html")):
        if profile_ids and path.stem not in {value.casefold() for value in profile_ids}:
            continue
        text = path.read_text(encoding="utf-8")
        dossier = _load_json(path.with_suffix(".json"), {})
        profile_id_hint = str(dossier.get("id") or "")
        updated, _ = revise(text, profile_id_hint)
        if updated != text: path.write_text(updated, encoding="utf-8"); counts["person_hierarchy"] += 1
        # This is the same resolved account the HTML uses, not another
        # hand-maintained summary. Keep imports and original notes untouched.
        match = re.search(r'data-r-person=["\']([^"\']+)', updated)
        if match:
            profile_id = match[1]
            json_path = path.with_suffix(".json")
            dossier = _load_json(json_path, {})
            if dossier:
                presentation = _editorial(profile_id)
                payload = {"version": PRESENTATION_VERSION, **presentation, "record_associations": _record_rows(profile_id)}
                _, model, _ = _profile_data(profile_id)
                payload["vitals"] = _current_vitals(profile_id, dossier, model, presentation)
                payload["relationships"] = {group: [_assessed_relation(profile_id, row, group) for row in rows] for group, rows in (dossier.get("relationships") or {}).items() if isinstance(rows, list)}
                if dossier.get("presentation") != payload:
                    dossier["presentation"] = payload
                    json_path.write_text(json.dumps(dossier, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return counts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", nargs="*", help="Optional WikiTree IDs for a targeted rebuild")
    print(repair(parser.parse_args().profiles))
