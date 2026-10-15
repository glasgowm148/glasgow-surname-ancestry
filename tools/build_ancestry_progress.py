#!/usr/bin/env python3
"""Build the Glasgow ancestry goal, fixed-cohort baseline and early connection queue."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.branch_connectivity import load_public_nodes, summarize
from tools.documentary_ancestry import load_people
from tools.free_space_edition import shell_page
from tools.stamp_asset_versions import VERSIONED_ASSET, asset_path, content_hash

WORK = ROOT / "research/ancestry-connections"
WEB = ROOT / "www"
ROUTE = "/onetree/progress/"


def compact(summary):
    return {
        k: v for k, v in summary.items() if k not in {"cohort_ids", "family_roots", "unattached_multi_child_roots"}
    } | {
        "unattached_multi_child_roots": len(summary["unattached_multi_child_roots"]),
        "family_root_count": len(summary["family_roots"]),
    }


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def stamp(path):
    def replace(match):
        target = asset_path(WEB, path, match["url"])
        return (
            match[0]
            if target is None or not target.is_file()
            else (match["quote"] + match["url"] + "?v=" + content_hash(target) + match["quote"])
        )

    original = path.read_text()
    updated = VERSIONED_ASSET.sub(replace, original)
    if updated != original:
        path.write_text(updated)


def metrics_html(summary):
    values = [
        (f"{summary['component_count']:,}", "separate paternal branches"),
        (f"{len(summary['unattached_multi_child_roots']):,}", "unattached fathers with 2+ children"),
        (f"{summary['largest_component_percent']:.1f}%", "people in the largest branch"),
        (f"{summary['connected_pairs_percent']:.2f}%", "pairs connected through fathers"),
    ]
    return "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in values)


def root_rows(roots):
    return "".join(
        '<tr><td><a href="'
        + escape(r["url"], quote=True)
        + '">'
        + escape(r["name"])
        + "</a><small>"
        + escape(r["id"])
        + "</small></td><td>"
        + str(r["year"] or "Undated")
        + "<small>"
        + escape((r["year_basis"] or "ancestor of dated person") + " · " + (r["year_status"] or "unmarked"))
        + "</small></td><td>"
        + str(r["child_count"])
        + "</td><td>"
        + str(r["descendant_count"])
        + "</td></tr>"
        for r in roots
    )


def build(create_baseline=False):
    strategy = json.loads((WORK / "strategy.json").read_text())
    documentary = load_people(WORK / 'documentary-people.json')
    documentary_path = WORK / 'documentary-people.json'
    write_json(WEB / 'data/ancestry-documentary-people.json',
               json.loads(documentary_path.read_text()) if documentary_path.exists() else {'schema_version': 1, 'people': []})
    nodes, edges, quality = load_public_nodes(WEB, set(strategy["variants"]))
    cohorts = {}
    for cutoff in strategy["cutoffs"]:
        working = summarize(nodes, edges, cutoff)
        # Both grades use exactly the same people, so their percentages compare fairly.
        confident = summarize(nodes, edges, cutoff, "confident", cohort_ids=working["cohort_ids"])
        cohorts[str(cutoff)] = {"working": working, "confident": confident}
    primary = cohorts[str(strategy["primary_cutoff"])]
    fingerprint = hashlib.sha256(json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True).encode()).hexdigest()
    baseline_path = WORK / "baseline-2026-10-15.json"
    if not baseline_path.exists():
        if not create_baseline:
            raise ValueError("Initial baseline is missing; use --create-baseline once.")
        baseline = dict(
            schema_version=1,
            captured=strategy["reviewed"],
            method_version=2,
            cutoff=strategy["primary_cutoff"],
            input_fingerprint=fingerprint,
            cohort_ids=primary["working"]["cohort_ids"],
            metrics={view: compact(summary) for view, summary in primary.items()},
        )
        write_json(baseline_path, baseline)
    else:
        baseline = json.loads(baseline_path.read_text())
    fixed_ids = set(baseline["cohort_ids"]) & nodes.keys()
    fixed = {
        view: compact(summarize(nodes, edges, baseline["cutoff"], view, cohort_ids=fixed_ids))
        for view in ["working", "confident"]
    }
    history_path = WORK / "progress-history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else {"schema_version": 1, "snapshots": []}
    if not history["snapshots"] or history["snapshots"][-1]["input_fingerprint"] != fingerprint:
        history["snapshots"].append(
            dict(
                date=date.today().isoformat(),
                method_version=2,
                input_fingerprint=fingerprint,
                metrics={v: compact(s) for v, s in primary.items()},
                fixed_cohort=fixed,
            )
        )
        write_json(history_path, history)
    report = dict(
        schema_version=1,
        reviewed=history["snapshots"][-1]["date"],
        method_version=2,
        strategy=strategy,
        input_fingerprint=fingerprint,
        quality=quality,
        available_surname_people=sum(n.get("cohort_member") is not False for n in nodes.values()),
        documentary_ancestors=len(documentary),
        undated_surname_people=len(quality["undated_people"]),
        cohorts=cohorts,
        baseline=baseline,
        fixed_cohort=dict(
            metrics=fixed,
            missing_ids=sorted(set(baseline["cohort_ids"]) - nodes.keys()),
            added_ids=sorted(set(primary["working"]["cohort_ids"]) - set(baseline["cohort_ids"])),
        ),
        progress_history=history["snapshots"],
    )
    write_json(WEB / "data/ancestry-connectivity.json", report)
    write_json(WEB / "data/ancestry-connectivity-baseline.json", baseline)
    target = WEB / ROUTE.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    assets = WEB / "assets/research"
    for extension in ["css", "js"]:
        (assets / ("ancestry-progress." + extension)).write_text(
            (ROOT / "tools" / ("ancestry_progress." + extension)).read_text()
        )
    selected = primary["working"]
    roots = [
        r for r in selected["family_roots"] if r["year"] is not None and r["year"] <= strategy["early_priority_cutoff"]
    ]
    cards = []
    for case in strategy["early_connections"]:
        people = " · ".join(f'<a href="{escape(p["url"], quote=True)}">{escape(p["name"])}</a>' for p in case["people"])
        sources = " · ".join(
            f'<a href="{escape(s["url"], quote=True)}">{escape(s["label"])}</a>' for s in case["sources"]
        )
        cards.append(
            f'<article class="connection-case" id="{case["id"]}"><p class="eyebrow">{case["year"]} onwards · {escape(case["status"])}</p><h3>{escape(case["title"])}</h3><p>{people}</p><p>{escape(case["basis"])}</p><p><strong>Next discriminating record:</strong> {escape(case["next_test"])}</p><p class="source-line">{sources}<br>{escape("; ".join(case["record_references"]))}</p></article>'
        )
    cohort_rows = "".join(
        f"<tr><td>Through {cutoff}</td><td>{data['working']['population']:,}</td><td>{data['working']['component_count']:,}</td><td>{len(data['working']['unattached_multi_child_roots']):,}</td><td>{data['working']['connected_pairs_percent']:.2f}%</td></tr>"
        for cutoff, data in cohorts.items()
    )
    client = dict(
        cohorts={
            cutoff: {view: {k: v for k, v in value.items() if k != "cohort_ids"} for view, value in pair.items()}
            for cutoff, pair in cohorts.items()
        },
        primary_cutoff=strategy["primary_cutoff"],
        early_cutoff=strategy["early_priority_cutoff"],
    )
    payload = json.dumps(client, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    options = "".join(
        f'<option value="{c}"' + (" selected" if c == strategy["primary_cutoff"] else "") + f">Through {c}</option>"
        for c in strategy["cutoffs"]
    )
    main = f"""<main class="r-main ancestry-progress" id="main">
<header class="r-page-head"><span class="r-kicker">Glasgow ancestry programme · {report["reviewed"]}</span><h1>Connect the oldest branches.</h1><p class="lead">{escape(strategy["objective"])}</p><p>{escape(strategy["common_origin"])}</p><p class="progress-actions"><a href="/onetree/#view=all">Explore the whole tree →</a><a href="/branches/early-scottish-records/">Early Scottish evidence</a><a href="#early-connections">First connections to investigate</a></p></header>
<section aria-labelledby="connectivity-title"><h2 id="connectivity-title">How connected is the family?</h2><div class="progress-controls"><label>Historical cohort <select id="progress-cutoff">{options}</select></label><label>Links counted <select id="progress-view"><option value="working">Working pedigree, including uncertain links</option><option value="confident">Confidently marked links</option></select></label></div><div class="connectivity-stats" id="connectivity-stats">{metrics_html(selected)}</div><p id="cohort-detail" aria-live="polite">{selected["population"]:,} public surname bearers; {selected["edge_count"]:,} father–child links. Both views use the same people.</p><p>{escape(strategy["metrics"]["target"])}</p><p>Smaller branch and unattached-father counts mean fewer gaps; larger connected-pair and largest-branch percentages mean more of the family is joined. A tentative connection remains tentative.</p></section>
<section aria-labelledby="working-map-title"><h2 id="working-map-title">One family, with the missing joins visible</h2><p>The shared-origin model gathers the branches below one ancestral lineage. Dotted lines mean an unknown route through generations; they are research targets and do not change the measured pedigree.</p><div id="working-origin-map" class="working-origin-map"></div><noscript><p>The earliest branch heads and their descendants appear in the table below. Each belongs to the shared-origin working model; the intervening generations remain open.</p></noscript></section>
<section id="early-connections" aria-labelledby="early-connections-title"><h2 id="early-connections-title">Start with the earliest connections</h2><p>These comparisons are already supported as research hypotheses. They are arranged by the oldest record involved. Resolve the missing identity, kinship or title-transfer step, then extend the connection to its supported siblings.</p>{"".join(cards)}</section>
<section aria-labelledby="family-heads-title"><h2 id="family-heads-title">Unattached family heads</h2><p>Work upwards from families rather than collecting isolated later records. Heads with one child but two or more surname descendants are included in this queue too.</p><div class="progress-controls"><label class="inline-check"><input type="checkbox" id="early-heads" checked>Prioritise heads dated by 1650</label><label>Find a family <input id="head-search" type="search" placeholder="Name or profile ID"></label></div><p id="head-count" aria-live="polite">{len(roots)} early family heads</p><div class="progress-table-wrap"><table><thead><tr><th>Family head</th><th>Earliest cohort year</th><th>Children</th><th>Descendants</th></tr></thead><tbody id="family-head-rows">{root_rows(roots)}</tbody></table></div></section>
<section aria-labelledby="cohorts-title"><h2 id="cohorts-title">Track the earlier generations separately</h2><p>The working pedigree at each cutoff. Estimated vital dates remain estimates. Undated fathers of included people enter by ancestry; unrelated undated entries stay outside the dated cohorts.</p><div class="progress-table-wrap"><table><thead><tr><th>Cutoff</th><th>People</th><th>Branches</th><th>Unattached fathers, 2+ children</th><th>Connected pairs</th></tr></thead><tbody>{cohort_rows}</tbody></table></div></section>
<section aria-labelledby="baseline-title"><h2 id="baseline-title">Track the same baseline people</h2><p>Initial baseline: {baseline["captured"]}, through {baseline["cutoff"]}, {len(baseline["cohort_ids"]):,} people. On those same surviving baseline people, the working connected-pair score is {fixed["working"]["connected_pairs_percent"]:.2f}% (initially {baseline["metrics"]["working"]["connected_pairs_percent"]:.2f}%). New cohort people: {len(report["fixed_cohort"]["added_ids"])}; missing baseline people: {len(report["fixed_cohort"]["missing_ids"])}.</p><p>A connection between two components joins every cross-branch pair. The score is 100 × Σ n(n−1) ÷ N(N−1), where n is each paternal component's size and N is the cohort. The common-origin model stays outside the measurements.</p><p>Confidence grades come from the current resolved public dossiers. A confidently marked tree link is not a claim that every underlying source has been independently re-audited. Women born with the surname count; their fathers can join the paternal family, while spouses and maternal paths cannot.</p><p>Coverage: {report["available_surname_people"]:,} public surname profiles and {report["documentary_ancestors"]} separately listed documentary ancestors available; {report["undated_surname_people"]:,} have no usable structured date before ancestry closure; {len(quality["missing_dossiers"])} dossiers unavailable; {len(quality["multiple_fathers"])} competing-father cases held out; {len(quality["cycles"])} paternal cycles flagged. Cyclic edges are excluded from the score. Named documentary ancestors with complete public research accounts can connect these profiles. They are listed separately as connectors and never increase the profile denominator. An unnamed conceptual ancestor cannot connect branches in this measure.</p><p>{escape(strategy["later_records"])}</p><p class="progress-actions"><a href="/data/ancestry-connectivity.json">Current measurements and research queue (JSON)</a><a href="/data/ancestry-connectivity-baseline.json">Fixed initial baseline (JSON)</a></p></section>
<script type="application/json" id="ancestry-progress-data">{payload}</script></main>"""
    page = shell_page((WEB / "about/index.html").read_text(), main, "Glasgow ancestry progress", ROUTE + "index.html")
    page = page.replace(
        "</head>", '<link rel="stylesheet" href="/assets/research/ancestry-progress.css?v=current"></head>'
    )
    page = page.replace(
        "</body>", '<script defer src="/assets/research/ancestry-progress.js?v=current"></script></body>'
    )
    target.write_text(page)
    stamp(target)
    # This is a durable, targeted integration into the existing Whole tree tools.
    atlas = WEB / "onetree/index.html"
    original = atlas.read_text()
    if 'href="/onetree/progress/"' not in original:
        updated = re.sub(
            r'(<div[^>]+class="v3-atlas-tools"[^>]*>)',
            r'\1<a href="/onetree/progress/">Ancestry progress</a>',
            original,
            count=1,
        )
        if updated == original:
            raise ValueError("Whole tree toolbar was not found")
        atlas.write_text(updated)
    print(
        json.dumps(
            dict(
                population=selected["population"],
                branches=selected["component_count"],
                multi_child_roots=len(selected["unattached_multi_child_roots"]),
                connected_pairs_percent=selected["connected_pairs_percent"],
                early_family_heads=len(roots),
                baseline=baseline["captured"],
            )
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-baseline", action="store_true", help="Create, never replace, the first baseline")
    build(parser.parse_args().create_baseline)
