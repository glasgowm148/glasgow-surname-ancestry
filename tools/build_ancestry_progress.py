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
from tools.branch_connectivity import CONFIDENT, SUPPORTED, EXCLUDED, MEASUREMENT_VIEWS, METHOD_VERSION, load_public_nodes, summarize, paternal_link_impacts, relationship_status, is_named_father_name
from tools.documentary_ancestry import load_people
from tools.free_space_edition import shell_page
from tools.stamp_asset_versions import VERSIONED_ASSET, asset_path, content_hash

WORK = ROOT / "research/ancestry-connections"
WEB = ROOT / "www"
ROUTE = "/onetree/progress/"
LINK_VIEWS = {
    'working': {'label': 'Working pedigree, including uncertain links',
                'description': 'Counts working parents, including uncertain and ungraded links. Competing fathers and cyclic links remain excluded.'},
    'supported': {'label': 'Probable or stronger',
                  'description': 'Counts probable, strongly supported and confidently marked links. Probable parentage remains inferred. These percentages measure connectivity, not the probability that a pedigree is correct.',
                  'included_grades': sorted(SUPPORTED)},
    'confident': {'label': 'Confidently marked links',
                  'description': 'Counts confidently marked and strongly supported links. A saved certainty flag does not mean every source has been independently re-audited.',
                  'included_grades': sorted(CONFIDENT)},
}


def pending_father_changes(catalogue):
    """Reuse the catalogue's explicit amendments, keyed to the selected pair."""
    return {(str(change.get('subject_id') or row.get('id') or row['map_key']).casefold(),
             str(change.get('relative_id')).casefold(), change.get('assertion_id')): change
            for row in catalogue if row.get('needs_wikitree_update')
            for change in row.get('wikitree_update_relationship_changes') or []
            if change.get('relationship') == 'father' and change.get('relative_id')}


def confidence_grade(state):
    # An ungraded named parent is not an absent (Unknown) father.
    for key in ('status', 'assessment_status', 'tree_status'):
        status = state.get(key)
        if status in {'proved', 'confident', 'strongly_supported', 'certain', 'dna_confirmed'}:
            return 'confident'
        if status in {'probable', 'possible', 'uncertain'}:
            return status
    return None


def individual_finding_rows(nodes, edges, assessments, cohorts, baseline_ids, identity_hold_ids=(), father_changes=None):
    """Explicit saved pair assessments only; never infer an old numeric rating."""
    def percent(state):
        value = state.get('probability_percent', state.get('percent'))
        if value is None:
            probability = state.get('probability') or {}
            value = probability.get('value')
            if type(value) in (int, float):
                value *= 100
        return round(value, 8) if type(value) in (int, float) and 0 <= value <= 100 else None

    def person(ident):
        node = nodes[ident]
        result = dict(id=ident, name=node['name'], url=node['url'])
        if re.fullmatch(r'(?!record-)[A-Za-z][A-Za-z0-9_]*-\d+', ident):
            result['wikitree_url'] = 'https://www.wikitree.com/wiki/' + ident
        return result

    def saved_state(state):
        if state is None:
            return None
        # Keep prior assessment/flag/date evidence without duplicating the
        # complete assertion, perspectives and its history for every table row.
        return {key: value for key, value in state.items() if key not in
                {'assessment_history', 'perspectives', 'analysis_links'}}

    rows = []
    for edge in edges:
        assertion = assessments.get(edge.get('assertion_id'))
        if not assertion or assertion.get('publication_status') != 'approved':
            continue
        current = edge.get('confidence_percent')
        if type(current) not in (int, float):
            continue
        child, father = edge['child'], edge['father']
        amendment = (father_changes or {}).get((child.casefold(), father.casefold(), assertion['assertion_id']), {})
        # The selected edge is authoritative; alternate hypotheses stay out.
        states = list(assertion.get('assessment_history') or []) + [assertion]
        previous = (assertion.get('provenance') or {}).get('prior_assessment')
        if not isinstance(previous, dict):
            previous = None
        if not previous and amendment.get('previous_status_provenance'):
            previous = dict(status=amendment.get('previous_status') or amendment.get('before'),
                            source_basis=amendment['previous_status_provenance'])
        structural_recorded = False
        for index, state in enumerate(states):
            historical_father = state.get('relative_id') or state.get('prior_selected_father')
            if index != len(states)-1 and historical_father and historical_father != father:
                previous = state
                continue
            value = current if index == len(states)-1 else percent(state)
            if value is None:
                previous = state
                continue
            # An assessed alternative supplies the prior pair percentage, but
            # was never a selected father finding in the measured pedigree.
            if index != len(states)-1 and (state.get('lifecycle') == 'alternative'
                                          or state.get('display') == 'alternative'):
                previous = {**state, 'probability_percent': value}
                continue
            prior_father = (previous or {}).get('relative_id') or (previous or {}).get('prior_selected_father')
            changed_father = bool(prior_father and prior_father != father)
            before = None if changed_father else percent(previous or {})
            probability = state.get('probability') or {}
            provenance = assertion.get('provenance') or {}
            newly_selected = (index == len(states)-1
                              and provenance.get('new_father_attachment') is True
                              and (previous or {}).get('working_selection') is False)
            new = newly_selected or (before is None and (
                changed_father or bool(provenance.get('new_local_documentary_person'))
                or provenance.get('new_father_attachment') is True))
            before_grade = confidence_grade(previous or {})
            after_grade = confidence_grade(state)
            structural = (not structural_recorded and amendment.get('action') in {'add', 'replace'})
            if structural:
                new = True
            if before == value and before_grade == after_grade and not newly_selected and not structural:
                previous = state
                continue
            review_date = state.get('assessment_date') or state.get('reviewed') or probability.get('reviewed')
            research_event = None
            if structural or (new and provenance.get('new_father_attachment') is True):
                structural_recorded = True
                if not provenance.get('new_local_documentary_person'):
                    replacement = amendment.get('action') == 'replace' or changed_father
                    prior = dict(status=amendment.get('previous_status'))
                    research_event = dict(
                        type='father_replacement' if replacement else 'father_attachment',
                        date=provenance.get('new_father_attachment_reviewed') or review_date,
                        before_grade=(confidence_grade(prior) or before_grade) if replacement else 'unknown',
                        after_grade=after_grade,
                        catalogue_action=amendment.get('action'),
                        previous_father_id=amendment.get('previous_relative_id') or prior_father,
                    )
            elif not new and (before is not None or (before_grade and after_grade and before_grade != after_grade)):
                research_event = dict(type='confidence_change', date=review_date,
                                      before_grade=before_grade, after_grade=after_grade)
            rows.append(dict(
                assertion_id=assertion['assertion_id'], child=person(child), father=person(father),
                date=review_date, research_event=research_event,
                saved_order=len(rows), kind='new' if new else 'change' if before is not None else 'first',
                before_percent=before, after_percent=value,
                previous_assessment=saved_state(previous), assessment_status=state.get('status') or state.get('assessment_status'),
                source_ids=state.get('source_ids') or probability.get('source_ids') or [],
                reason=state.get('change_reason') or state.get('reason') or state.get('source_basis') or probability.get('basis') or state.get('basis') or '',
                limitations=state.get('limitations') or state.get('record_scope') or state.get('scope') or '',
                identity_hold=child in identity_hold_ids or father in identity_hold_ids,
                catalogue_father_action=amendment.get('action'),
                cohorts=[str(cutoff) for cutoff, views in cohorts.items() if child in views['working']['cohort_ids']],
                baseline=child in baseline_ids,
            ))
            previous = {**state, 'probability_percent': value}
    # Python's stable sort retains saved source order within each exact date.
    return sorted(rows, key=lambda row: (row['research_event'] or {}).get('date') or row['date'] or '', reverse=True)


def has_named_father(dossier):
    """A retained named father, independent of his confidence or graph eligibility."""
    for relation in (dossier.get('relationships') or {}).get('parents') or []:
        status, _ = relationship_status(relation)
        if (str(relation.get('relationship', '')).casefold() != 'father'
                or not relation.get('id') or status in EXCLUDED
                or relation.get('lifecycle') not in (None, 'current')
                or relation.get('display') in {'alternative', 'historical', 'superseded'}
                or relation.get('publication_status') in {'withheld', 'blocked', 'rejected'}):
            continue
        if not is_named_father_name(relation.get('name')):
            continue
        return True
    return False


def father_listing_counts(cohort_ids, listings):
    values = [listings.get(ident) for ident in cohort_ids]
    return dict(unknown_count=values.count(False), named_count=values.count(True),
                unavailable_count=values.count(None), population=len(values))


def named_father_review_counts(cohort_ids, retained_fathers):
    """Current exact-rating coverage, independent of surname-graph eligibility."""
    cohort = set(cohort_ids)
    selected = {row['child']: row for row in retained_fathers
                if row['child'] in cohort and is_named_father_name(row.get('father_name'))}
    rated = sum(type(row.get('confidence_percent')) in (int, float)
                and 0 < row['confidence_percent'] < 100 for row in selected.values())
    total = len(selected)
    return dict(named_count=total, rated_count=rated, unrated_count=total - rated,
                coverage_percent=100 * rated / total if total else None)


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


def comparison_rows(cohort, selected='working'):
    rows = []
    for view in MEASUREMENT_VIEWS:
        summary = cohort[view]
        label = escape(LINK_VIEWS[view]['label'])
        if view == selected:
            label = '<strong>' + label + '</strong>'
        rows.append(f"<tr><th scope='row'>{label}</th><td>{summary['component_count']:,}</td>"
                    f"<td>{summary['largest_component_size']:,}</td><td>{summary['connected_pairs_percent']:.2f}%</td></tr>")
    return ''.join(rows)


def build(create_baseline=False):
    strategy = json.loads((WORK / "strategy.json").read_text())
    documentary = load_people(WORK / 'documentary-people.json')
    documentary_path = WORK / 'documentary-people.json'
    write_json(WEB / 'data/ancestry-documentary-people.json',
               json.loads(documentary_path.read_text()) if documentary_path.exists() else {'schema_version': 1, 'people': []})
    retained_fathers = []
    nodes, edges, quality = load_public_nodes(WEB, set(strategy["variants"]), retained_fathers=retained_fathers)
    listings = {}
    identity_hold_ids = set()
    for ident, node in nodes.items():
        # Read the public account, including named fathers excluded from the
        # surname graph. Confidence-threshold roots are not missing fathers.
        path = WEB / str(node['url']).split('#')[0].lstrip('/')
        if path.suffix == '.html' and path.with_suffix('.json').is_file():
            dossier = json.loads(path.with_suffix('.json').read_text())
            listings[ident] = has_named_father(dossier)
            if dossier.get('creation_status') == 'identity_hold':
                identity_hold_ids.add(ident)
    cohorts = {}
    for cutoff in strategy["cutoffs"]:
        working = summarize(nodes, edges, cutoff)
        # Every threshold uses exactly the same people, including isolated profiles.
        cohorts[str(cutoff)] = {'working': working, **{
            view: summarize(nodes, edges, cutoff, view, cohort_ids=working['cohort_ids'])
            for view in MEASUREMENT_VIEWS if view != 'working'}}
        for summary in cohorts[str(cutoff)].values():
            summary['father_listing'] = father_listing_counts(working['cohort_ids'], listings)
    primary = cohorts[str(strategy["primary_cutoff"])]
    assessments = {a.get('assertion_id'): a for a in json.loads((ROOT / 'research/relationship_assessments.json').read_text())}
    cases = {c.get('assertion_id'): c for c in strategy['early_connections'] if c.get('assertion_id')}
    # Reuse the per-pair next questions already reviewed with the ratings.
    rating_tests = {}
    for path in sorted(WORK.glob('father-coverage-review*.json')):
        for rating in json.loads(path.read_text()).get('ratings', []):
            if rating.get('next_test'):
                rating_tests[rating.get('assertion_id')] = rating['next_test']
    priorities = []
    for impact in paternal_link_impacts(nodes, edges, strategy['primary_cutoff'], primary['working']['cohort_ids']):
        if impact['status'] in CONFIDENT:
            continue
        child, father = impact['child'], impact['father']
        assessment = assessments.get(impact.get('assertion_id'), {})
        case = cases.get(impact.get('assertion_id'), {})
        priorities.append({**{k: impact[k] for k in ('child', 'father', 'status', 'child_side', 'parent_side', 'cross_pairs', 'confident_child_side', 'confident_parent_side', 'confident_pair_gain', 'confident_component_reduction')},
                           'confidence_percent': impact.get('confidence_percent'),
                           'child_name': nodes[child]['name'], 'father_name': nodes[father]['name'],
                           'child_url': nodes[child]['url'], 'father_url': nodes[father]['url'],
                           'year': nodes[child].get('year'),
                           'analysis_url': next((l['href'] for l in assessment.get('analysis_links', []) if l.get('href')), nodes[child]['url']),
                           'next_test': case.get('next_test') or assessment.get('next_test') or rating_tests.get(impact.get('assertion_id')) or 'Read the family evidence and next question.',
                           'last_review': case.get('last_test') or assessment.get('last_test', '')})
    priorities.sort(key=lambda r: (-r['cross_pairs'], r['child'], r['father']))
    fingerprint = hashlib.sha256(json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True).encode()).hexdigest()
    baseline_path = WORK / "baseline-2026-10-15.json"
    if not baseline_path.exists():
        if not create_baseline:
            raise ValueError("Initial baseline is missing; use --create-baseline once.")
        baseline = dict(
            schema_version=1,
            captured=strategy["reviewed"],
            method_version=METHOD_VERSION,
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
        for view in MEASUREMENT_VIEWS
    }
    for summary in fixed.values():
        summary['father_listing'] = father_listing_counts(fixed_ids, listings)
    history_path = WORK / "progress-history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else {"schema_version": 1, "snapshots": []}
    previous_version = history['snapshots'][-1].get('method_version') if history['snapshots'] else None
    new_view = bool(history['snapshots']) and any(
        view not in history['snapshots'][-1]['metrics'] for view in MEASUREMENT_VIEWS)
    new_measurement = bool(history['snapshots']) and 'individual_confidence' not in history['snapshots'][-1].get('fixed_cohort', {}).get('working', {})
    new_unknown_measurement = bool(history['snapshots']) and 'father_listing' not in history['snapshots'][-1].get('fixed_cohort', {}).get('working', {})
    listing_changed = bool(history['snapshots']) and (fixed['working']['father_listing'] != history['snapshots'][-1].get('fixed_cohort', {}).get('working', {}).get('father_listing') or any(
        pair['working']['father_listing'] != history['snapshots'][-1].get('cohorts', {}).get(cutoff, {}).get('working', {}).get('father_listing')
        for cutoff, pair in cohorts.items()))
    if not history["snapshots"] or history["snapshots"][-1]["input_fingerprint"] != fingerprint or previous_version != METHOD_VERSION or new_view or new_measurement or listing_changed or history['snapshots'][-1]['date'] != date.today().isoformat():
        correction = previous_version is not None and previous_version != METHOD_VERSION
        history["snapshots"].append(
            dict(
                date=date.today().isoformat(),
                method_version=METHOD_VERSION,
                **(dict(event_type='method_correction', previous_method_version=previous_version,
                        genealogical_connections_added=0,
                        note='Retained primary fathers now take precedence over unselected alternatives. Existing links restored by this method correction are not new research findings or evidence upgrades.')
                   if correction else {}),
                **(dict(event_type='additional_confidence_view', genealogical_connections_added=0,
                        note='Probable-or-stronger connectivity is measured separately. Existing assessments, prior measurements and the original baseline are unchanged.')
                   if new_view and not correction and history['snapshots'][-1]['input_fingerprint'] == fingerprint else {}),
                input_fingerprint=fingerprint,
                **(dict(event_type='unknown_father_measurement_added', genealogical_connections_added=0,
                        note='Unknown fathers are now counted from retained public parent listings, separately from confidence in named links. Earlier unknown-father counts were not recorded and are not reconstructed.')
                   if new_unknown_measurement and not correction and history['snapshots'][-1]['input_fingerprint'] == fingerprint else {}),
                **(dict(event_type='individual_confidence_measurement_added', genealogical_connections_added=0,
                        note='Exact reviewed father percentages and coverage are now recorded. Relationships and confidence grades are unchanged; earlier measurements are not reconstructed.')
                   if new_measurement and not correction and not new_view else {}),
                metrics={v: compact(s) for v, s in primary.items()},
                fixed_cohort=fixed,
            )
        )
        write_json(history_path, history)
    # Record dated cutoff measurements from now on; never reconstruct old dates
    # using today's pedigree. Older snapshots retain their fixed-cohort history.
    cutoff_history = {
        str(cutoff): {view: compact(summary) for view, summary in pair.items()}
        for cutoff, pair in cohorts.items()
    }
    if history['snapshots'][-1].get('cohorts') != cutoff_history:
        history['snapshots'][-1]['cohorts'] = cutoff_history
        write_json(history_path, history)
    catalogue = json.loads((WEB / 'data/catalogue-search-index.json').read_text())
    individual_findings = individual_finding_rows(nodes, edges, assessments, cohorts, set(baseline['cohort_ids']),
                                                 identity_hold_ids, pending_father_changes(catalogue))
    current_named_father_coverage = dict(
        cohorts={cutoff: named_father_review_counts(pair['working']['cohort_ids'], retained_fathers)
                 for cutoff, pair in cohorts.items()},
        fixed=named_father_review_counts(fixed_ids, retained_fathers),
    )
    report = dict(
        current_named_father_coverage=current_named_father_coverage,
        schema_version=1,
        reviewed=history["snapshots"][-1]["date"],
        method_version=METHOD_VERSION,
        link_views=LINK_VIEWS,
        strategy=strategy,
        input_fingerprint=fingerprint,
        quality=quality,
        available_surname_people=sum(n.get("cohort_member") is not False for n in nodes.values()),
        documentary_ancestors=len(documentary),
        documentary_identity_selections=[{'person_id': p['id'], **p['identity_selection']}
                                         for p in documentary if (p.get('identity_selection') or {}).get('selected') is True],
        undated_surname_people=len(quality["undated_people"]),
        cohorts=cohorts,
        research_priorities=priorities,
        research_priority_method='Working pairs count all retained profile pairs dependent on this link. Confident-pair gain counts only pairs joined by upgrading this one link, with every other assessment unchanged. Hypothetical gains overlap; do not sum them. A high gain is not evidence or a reason to raise confidence.',
        baseline=baseline,
        fixed_cohort=dict(
            metrics=fixed,
            missing_ids=sorted(set(baseline["cohort_ids"]) - nodes.keys()),
            added_ids=sorted(set(primary["working"]["cohort_ids"]) - set(baseline["cohort_ids"])),
            confident_baseline_comparable=baseline.get('method_version') == METHOD_VERSION,
            supported_baseline_available='supported' in baseline.get('metrics', {}),
        ),
        progress_history=history["snapshots"],
        individual_findings=individual_findings,
        individual_confidence_method='Arithmetic mean of reviewed individual percentages for selected eligible father–child links; unrated links have no percentage. Review coverage is measured separately. Not a whole-pedigree probability.',
        unknown_father_method='Counts cohort people with no retained named father in their public account, including unnamed placeholders and only unselected alternatives. A named father remains named regardless of confidence or surname-graph eligibility. Missing public accounts are reported separately. This counts people, while confidence series count eligible father links. Older unknown-father counts were not recorded and are not reconstructed.',
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
    snapshot = history["snapshots"][-1]
    reconciliation_note = (
        '<p role="note"><strong>Publication repair:</strong> ' + escape(snapshot['note']) + '</p>'
        if snapshot.get('event_type') == 'publication_reconciliation' else ''
    )
    publication_html = ''
    confidence_note = ''
    publication_path = max(WORK.glob('tree-publication-review-*.json'), default=None)
    if publication_path is not None:
        publication = json.loads(publication_path.read_text())
        write_json(WEB / 'data/ancestry-tree-publication-review.json', publication)
        checked = publication['models']['main']
        flag_count = publication['next_metric_check']['saved_confident_tree_flags_not_used_by_current_metric']
        confidence_note = (f'<p role="note"><strong>Confidence-only calculation under review:</strong> '
                           f'The {publication["reviewed"]} review found {flag_count:,} saved confident WikiTree flags omitted from this calculation. '
                           'The working figures are unaffected; correcting this will not count as new research evidence.</p>')
        publication_summary = publication.get('publication_summary') or (
            f'The main viewer now includes {len(checked["added_historical_profiles"]):,} historical profiles that were absent '
            f'and synchronizes {checked["changed_father_fields"]:,} father fields. These reproduce existing published conclusions; '
            'the connectivity figures do not increase. Competing fathers remain unresolved, and existing uncertainty grades are retained.')
        publication_html = (f'<section aria-labelledby="tree-publication-title"><h2 id="tree-publication-title">Whole tree publication check</h2>'
                            f'<p>Checked {publication["reviewed"]}: both viewers reproduce the published paternal relationships for '
                            f'{checked["checked_historical_profiles"]:,} profiles through {publication["cutoff"]}, including '
                            f'{checked["matched_paternal_edges"]:,} paternal links and the named documentary connector.</p>'
                            f'<p>{escape(publication_summary)}</p>'
                            '<p><a href="/data/ancestry-tree-publication-review.json">Read the profile-by-profile publication audit</a></p></section>')
        if publication.get('method_version') != report['method_version'] or publication['next_metric_check'].get('status') != 'OPEN':
            confidence_note = ''
        if publication.get('input_fingerprint') != report['input_fingerprint']:
            publication_html = (f'<section aria-labelledby="tree-publication-title"><h2 id="tree-publication-title">Whole tree publication check</h2>'
                                f'<p>The last recorded review was {publication["reviewed"]}. The research graph has changed since; refresh its publication audit.</p>'
                                '<p><a href="/data/ancestry-tree-publication-review.json">Read the previous review</a></p></section>')
    method_review_path = max(WORK.glob('confidence-method-review-*.json'), default=None)
    if method_review_path is not None:
        method_review = json.loads(method_review_path.read_text())
        write_json(WEB / 'data/ancestry-confidence-method-review.json', method_review)
        if method_review['method_version'] == METHOD_VERSION:
            counted = method_review['dispositions']['counted in confident graph']
            confidence_note = (f'<section aria-labelledby="confidence-method-title"><h2 id="confidence-method-title">Confidence calculation corrected</h2>'
                               f'<p>Method {METHOD_VERSION}, {method_review["reviewed"]}: {counted:,} eligible saved confident WikiTree flags are now counted. '
                               'Explicit uncertain or possible research assessments still take priority over a tree flag. '
                               'This corrects classification; it adds no parentage claims or evidence upgrades and leaves working connectivity unchanged.</p>'
                               '<p>The original baseline is preserved. Its method-2 confidence figures are not directly comparable with method 3; '
                               'the working baseline remains comparable. <a href="/data/ancestry-confidence-method-review.json">Read the flag-by-flag audit and before/after measurements</a>.</p></section>')
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
        current_named_father_coverage=current_named_father_coverage,
        cohorts={
            cutoff: {view: {k: v for k, v in value.items() if k != "cohort_ids"} for view, value in pair.items()}
            for cutoff, pair in cohorts.items()
        },
        primary_cutoff=strategy["primary_cutoff"],
        early_cutoff=strategy["early_priority_cutoff"],
        views=LINK_VIEWS,
        history_method_version=METHOD_VERSION,
        history_baseline=dict(cutoff=baseline['cutoff'], population=len(baseline['cohort_ids'])),
        progress_history=[
            {key: row[key] for key in ('date', 'method_version', 'fixed_cohort', 'cohorts') if key in row}
            for row in history['snapshots']
        ],
        research_priorities=priorities,
        individual_findings=individual_findings,
    )
    payload = json.dumps(client, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    options = "".join(
        f'<option value="{c}"' + (" selected" if c == strategy["primary_cutoff"] else "") + f">Through {c}</option>"
        for c in strategy["cutoffs"]
    )
    view_options = ''.join(f'<option value="{view}">{escape(LINK_VIEWS[view]["label"])}</option>'
                           for view in MEASUREMENT_VIEWS)
    named_coverage = current_named_father_coverage['cohorts'][str(strategy['primary_cutoff'])]
    named_coverage_text = (f"{named_coverage['rated_count']:,} of {named_coverage['named_count']:,} retained named fathers individually rated; "
                           f"{named_coverage['unrated_count']:,} ungraded. "
                           + (f"{named_coverage['coverage_percent']:.1f}% coverage." if named_coverage['coverage_percent'] is not None
                              else "No retained named fathers."))
    main = f"""<main class="r-main ancestry-progress" id="main">
<header class="r-page-head"><span class="r-kicker">Glasgow ancestry programme · {report["reviewed"]}</span><h1>Ancestry research progress</h1><p class="lead">Track stronger father–child connections and fewer separate branches as the research develops.</p><p class="progress-actions"><a href="/onetree/#view=all">Explore the whole tree →</a><a href="/branches/early-scottish-records/">Early Scottish evidence</a><a href="#uncertain-connections">Largest uncertain connections</a><a href="#early-connections">First connections to investigate</a></p></header>
<section aria-labelledby="connectivity-title"><h2 id="connectivity-title">How connected is the family?</h2><div class="progress-controls"><label>Historical cohort <select id="progress-cutoff">{options}</select></label><label>Links counted <select id="progress-view">{view_options}</select></label></div><p id="link-view-note" aria-live="polite">{escape(LINK_VIEWS['working']['description'])}</p><div class="connectivity-stats" id="connectivity-stats">{metrics_html(selected)}</div><p id="cohort-detail" aria-live="polite">{selected["population"]:,} public surname bearers; {selected["edge_count"]:,} father–child links. All views use the same people.</p><p id="named-father-coverage" aria-live="polite">{escape(named_coverage_text)}</p><p class="source-line">Current rating coverage includes every retained selected named father, including fathers outside the surname graph. Alternatives and unnamed fathers are excluded. Historical graph-link series below retain their original scope.</p><div class="progress-table-wrap"><table><caption>Compare the same people at each link threshold</caption><thead><tr><th>Links counted</th><th>Branches</th><th>People in largest branch</th><th>Connected pairs</th></tr></thead><tbody id="threshold-comparison">{comparison_rows(primary)}</tbody></table></div><p>Probable assessments can strengthen the middle measure while the confidently marked measure stays separate. The original baseline has no probable-or-stronger measurement; this series starts with the current review. An unmarked link is a review gap rather than a disproof.</p><p>{escape(strategy["metrics"]["target"])}</p><p>Smaller branch and unattached-father counts mean fewer gaps; larger connected-pair and largest-branch percentages mean more of the family is joined. A tentative connection remains tentative.</p></section>
{reconciliation_note}
{confidence_note}
{publication_html}
<section id="uncertain-connections" aria-labelledby="uncertain-connections-title"><h2 id="uncertain-connections-title">Which uncertain connections would help most?</h2><p>Father links for the cohort through {strategy['primary_cutoff']}. Coverage is measured above; this queue focuses research on the larger remaining uncertainties. Compare the whole working branch with the immediate gain from making just one link confident. Every other uncertain link stays uncertain.</p><div id="priority-uncertainty-summary" class="priority-uncertainty-summary"></div><div class="progress-controls"><label>Rank connections by <select id="priority-order"><option value="confident">Immediate gain in confident pairs</option><option value="working">Pairs depending on the working connection</option></select></label><label class="inline-check"><input type="checkbox" id="priority-early">Only children dated by 1650</label></div><p id="priority-count" aria-live="polite"></p><div class="progress-table-wrap" tabindex="0" role="region" aria-label="Research priority table; scroll horizontally on small screens"><table class="research-priority-table"><caption>Potential research yield · fixed cohort through {strategy['primary_cutoff']}</caption><thead><tr><th>Proposed father → child</th><th>Current confidence</th><th>Child-side people</th><th>Working pairs depending on link</th><th>Confident pairs gained if upgraded alone</th><th>Next useful evidence test</th></tr></thead><tbody id="priority-rows"></tbody></table></div><p>These counts concern retained profile accounts, including unresolved identity questions. Named documentary ancestors can connect them but do not increase the person counts. Potential gains overlap and must not be added. Ranking measures impact; it does not measure whether an upgrade is attainable. <a href="/data/ancestry-connectivity.json">Download all priorities and the method</a>.</p><noscript><p>Enable JavaScript to rank the queue, or use the download above. The source-backed early cases follow below.</p></noscript></section>
<section aria-labelledby="working-map-title"><h2 id="working-map-title">One family, with the missing joins visible</h2><p>The shared-origin model gathers the branches below one ancestral lineage. Dotted lines mean an unknown route through generations; they are research targets and do not change the measured pedigree.</p><div id="working-origin-map" class="working-origin-map"></div><noscript><p>The earliest branch heads and their descendants appear in the table below. Each belongs to the shared-origin working model; the intervening generations remain open.</p></noscript></section>
<section id="early-connections" aria-labelledby="early-connections-title"><h2 id="early-connections-title">Start with the earliest connections</h2><p>These comparisons are already supported as research hypotheses. They are arranged by the oldest record involved. Resolve the missing identity, kinship or title-transfer step, then extend the connection to its supported siblings.</p>{"".join(cards)}</section>
<section aria-labelledby="family-heads-title"><h2 id="family-heads-title">Unattached family heads</h2><p>Work upwards from families rather than collecting isolated later records. Heads with one child but two or more surname descendants are included in this queue too.</p><div class="progress-controls"><label class="inline-check"><input type="checkbox" id="early-heads" checked>Prioritise heads dated by 1650</label><label>Find a family <input id="head-search" type="search" placeholder="Name or profile ID"></label></div><p id="head-count" aria-live="polite">{len(roots)} early family heads</p><div class="progress-table-wrap"><table><thead><tr><th>Family head</th><th>Earliest cohort year</th><th>Children</th><th>Descendants</th></tr></thead><tbody id="family-head-rows">{root_rows(roots)}</tbody></table></div></section>
<section aria-labelledby="cohorts-title"><h2 id="cohorts-title">Track the earlier generations separately</h2><p>The working pedigree at each cutoff. Estimated vital dates remain estimates. Undated fathers of included people enter by ancestry; unrelated undated entries stay outside the dated cohorts.</p><div class="progress-table-wrap"><table><thead><tr><th>Cutoff</th><th>People</th><th>Branches</th><th>Unattached fathers, 2+ children</th><th>Connected pairs</th></tr></thead><tbody>{cohort_rows}</tbody></table></div></section>
<section aria-labelledby="baseline-title"><h2 id="baseline-title">Track the same baseline people</h2><p>Initial baseline: {baseline["captured"]}, through {baseline["cutoff"]}, {len(baseline["cohort_ids"]):,} people. On those same surviving baseline people, the working connected-pair score is {fixed["working"]["connected_pairs_percent"]:.2f}% (initially {baseline["metrics"]["working"]["connected_pairs_percent"]:.2f}%). New cohort people: {len(report["fixed_cohort"]["added_ids"])}; missing baseline people: {len(report["fixed_cohort"]["missing_ids"])}.</p><p>A connection between two components joins every cross-branch pair. The score is 100 × Σ n(n−1) ÷ N(N−1), where n is each paternal component's size and N is the cohort. The common-origin model stays outside the measurements.</p><p>Confidence grades come from the current resolved public dossiers. A confidently marked tree link is not a claim that every underlying source has been independently re-audited. Women born with the surname count; their fathers can join the paternal family, while spouses and maternal paths cannot.</p><p>Coverage: {report["available_surname_people"]:,} public surname profiles and {report["documentary_ancestors"]} separately listed documentary ancestors available; {report["undated_surname_people"]:,} have no usable structured date before ancestry closure; {len(quality["missing_dossiers"])} dossiers unavailable; {len(quality["multiple_fathers"])} competing-father cases held out; {len(quality["cycles"])} paternal cycles flagged. Cyclic edges are excluded from the score. Named documentary ancestors with complete public research accounts can connect these profiles. They are listed separately as connectors and never increase the profile denominator. An unnamed conceptual ancestor cannot connect branches in this measure.</p><p>{escape(strategy["later_records"])}</p><p class="progress-actions"><a href="/data/ancestry-connectivity.json">Current measurements and research queue (JSON)</a><a href="/data/ancestry-connectivity-baseline.json">Fixed initial baseline (JSON)</a></p></section>
<script type="application/json" id="ancestry-progress-data">{payload}</script></main>"""
    history_html = f'''<section id="progress-history" class="progress-history" aria-labelledby="history-title">
<h2 id="history-title">Research findings over time</h2>
<p>Track changes supported by new evidence or a revised assessment, including decreases. A first percentage counts when it changes a saved earlier confidence grade. Initial indexing and unchanged grades are review coverage. <a href="#individual-findings">See whose assessment changed ↓</a></p>
<div class="progress-controls"><label>History cohort <select id="history-cohort"><option value="fixed">Fixed baseline · {len(baseline['cohort_ids']):,} people through {baseline['cutoff']}</option><option value="selected">Selected historical cohort</option></select></label></div>
<div id="uncertainty-history" class="research-findings-trend" aria-labelledby="research-history-title">
<h3 id="research-history-title">Confidence changes from research</h3>
<p id="research-history-scope" class="source-line"></p>
<div id="research-history-summary" class="history-changes" aria-live="polite"></div>
<p>Net movement from recorded findings · positive means more links in that grade; negative means fewer.</p>
<div id="research-history-legend" class="research-grade-legend"></div><div id="research-history-chart"></div>
<p id="research-history-exclusions" class="source-line"></p><p id="research-catalogue-reconciliation" class="source-line"></p>
<p class="source-line">A change within a grade still counts as an improved or lowered rating above, even when its line stays level. Each date combines the findings recorded that day; the baseline does not invent an earlier date or percentage.</p>
<details><summary>View dated research changes</summary><div class="progress-table-wrap"><table><caption>Grade columns show cumulative net change; review columns count that date’s findings.</caption><thead><tr><th scope="col">Date</th><th scope="col">Confident</th><th scope="col">Probable</th><th scope="col">Possible</th><th scope="col">Uncertain</th><th scope="col">Unknown</th><th scope="col">Ratings improved</th><th scope="col">Ratings lowered</th><th scope="col">New fathers</th><th scope="col">Replacements</th></tr></thead><tbody id="research-history-rows"></tbody></table></div></details>
<h3>Current counts</h3><div id="research-current-counts" class="research-grade-legend"></div><p class="source-line">Unknown means no named father is retained. The other grades count named father links. These current totals are separate from research gains.</p>
</div>
<details id="catalogue-history"><summary>Catalogue and review coverage history · includes first-time grading</summary><p>These older snapshot charts also change when people are indexed, first assessed or reconciled. They measure catalogue coverage and connectivity, and are not used to count research improvements above.</p>
<p id="history-scope" class="source-line"></p>
<div id="catalogue-uncertainty-history" class="uncertainty-trend" aria-labelledby="uncertainty-history-title">
<h3 id="uncertainty-history-title">How many fathers remain unknown or uncertain?</h3>
<p>Unknown means no named father is retained, including an unnamed placeholder or only unselected candidates. Below confident counts named father links graded probable, possible, uncertain or unmarked. Unknown counts people; the other series count father links. <a href="#family-heads-title">Explore unattached family heads</a>.</p>
<div id="uncertainty-totals" class="uncertainty-totals" aria-live="polite"></div><div id="uncertainty-breakdown" class="uncertainty-breakdown"></div>
<p class="uncertainty-legend"><span>━ Named fathers below confident</span><span>┄ Uncertain grade only</span><span>● Unknown father</span></p><div id="uncertainty-trend-chart"></div>
<p class="source-line">Lower is better. Counts follow the history cohort selected above, using each day's last comparable measurement. Changes include regrading existing fathers, review coverage and changes to the people or links included; they are not all new family connections. Unknown-father history starts with its first saved count; earlier missing measurements stay blank.</p>
<details><summary>View uncertainty counts by date</summary><div class="progress-table-wrap"><table><thead><tr><th scope="col">Date</th><th scope="col">All below confident</th><th scope="col">Share of father links</th><th scope="col">Unknown father</th><th scope="col">Uncertain</th><th scope="col">Possible</th><th scope="col">Probable</th><th scope="col">Unmarked</th></tr></thead><tbody id="uncertainty-trend-rows"></tbody></table></div></details>
</div>
<h3>Confident connections and other measures</h3><p>Green tracks confident father links; blue includes probable links. Change the measure to explore confidence or branch connectivity.</p><div class="progress-controls"><label>Measure <select id="history-metric"><option value="edge_count">Father–child links</option><option value="reviewed_confidence_percent">Mean reviewed father confidence (%)</option><option value="assessed_links_percent">Graph-link coverage (%)</option><option value="largest_component_size">People in largest branch</option><option value="connected_pairs_percent">Connected pairs (%)</option><option value="component_count">Separate paternal components</option></select></label></div><fieldset class="history-legend" id="history-confidence-levels"><legend>Confidence levels shown</legend><label class="history-confident"><input id="history-confident" type="checkbox" checked> Confident</label><label class="history-supported"><input id="history-supported" type="checkbox" checked> Probable or stronger</label><label class="history-working"><input id="history-working" type="checkbox"> Working, including uncertain</label></fieldset><div id="history-changes" class="history-changes" aria-live="polite"></div><div id="history-chart"></div><p id="history-note" class="source-line"></p>
<details><summary>View snapshot data</summary><div class="progress-table-wrap"><table><caption id="history-table-caption">Daily measurements</caption><thead id="history-table-head"></thead><tbody id="history-table-body"></tbody></table></div></details>
<noscript><p>Enable JavaScript to explore the chart, or <a href="/data/ancestry-connectivity.json">read the dated measurements</a>.</p></noscript>
<div class="confidence-trend">
<h3>Graph-link review coverage and recorded mean confidence</h3><p id="confidence-trend-summary" aria-live="polite"></p>
<div id="confidence-trend-chart"></div>
<p class="source-line">Every changed saved review is shown, including changes within the same day. Reviews are evenly spaced; recording times were not retained. The mean covers individually assessed fathers, so review coverage and new or revised links can move it up or down. It is not a probability for the whole tree. Earlier unrecorded percentages are not reconstructed.</p>
<details><summary>View exact confidence review data</summary><div class="progress-table-wrap"><table><thead><tr><th scope="col">Saved review</th><th scope="col">Mean confidence</th><th scope="col">Rated father links</th><th scope="col">Review coverage</th></tr></thead><tbody id="confidence-trend-rows"></tbody></table></div></details>
</div>
</details>
<div id="individual-findings" aria-labelledby="individual-findings-title"><h3 id="individual-findings-title">Individual findings</h3><p>Follow each selected father’s assessment, with the child’s biography and WikiTree profile. Percentage changes use saved individual estimates, including decreases and changes within a confidence band. First percentages that change a saved earlier confidence grade count as findings; unchanged initial assessments remain review coverage. New and replacement recommendations are reconciled with the catalogue. Dates are recorded review dates; same-day entries retain saved order.</p><div class="progress-controls"><label>Findings <select id="findings-kind"><option value="research">Research changes and father recommendations</option><option value="change">Confidence changes (percentages or grades)</option><option value="first">First individual ratings</option><option value="new">New / replacement fathers</option><option value="all">All findings</option></select></label><label class="inline-check"><input type="checkbox" id="findings-all-cohorts">Include beyond the selected history cohort</label></div><p id="findings-count" aria-live="polite"></p><div class="progress-table-wrap" tabindex="0" role="region" aria-label="Individual father findings"><table><thead><tr><th scope="col">Review date</th><th scope="col">Child and father</th><th scope="col">Individual assessment</th><th scope="col">Evidence and reason</th></tr></thead><tbody id="findings-rows"></tbody></table></div></div>
</section>'''
    main = main.replace('<section aria-labelledby="connectivity-title">', history_html + '<section aria-labelledby="connectivity-title">', 1)
    main = main.replace('<section aria-labelledby="baseline-title">', '<section aria-labelledby="baseline-title"><details><summary>Research objective and shared-origin hypothesis</summary><p>' + escape(strategy['objective']) + '</p><p>' + escape(strategy['common_origin']) + '</p></details>', 1)
    main = main.replace('<a href="#early-connections">', '<a href="#progress-history">Progress chart</a><a href="#individual-findings">Individual findings</a><a href="#early-connections">', 1)
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
