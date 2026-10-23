"""Paternal connectivity over resolved public genealogy dossiers.

No surname, platform ID or proposed ancestor is built into the graph algorithm.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from tools.documentary_ancestry import load_chronology, load_people, metric_node
from tools.relationship_probability import confidence_band

CONFIDENT = frozenset(
    {"certain", "confident", "confirmed", "proved", "documented", "strongly_supported", "dna_confirmed"}
)
SUPPORTED = CONFIDENT | {'probable'}
MEASUREMENT_VIEWS = ('working', 'supported', 'confident')
METHOD_VERSION = 4
EXCLUDED = frozenset(
    {
        "rejected",
        "disproved",
        "contradicted",
        "non_biological",
        "non-biological",
        "superseded",
        "historical",
        "excluded",
    }
)


def _year(value):
    """Conservative upper year for an event, retaining estimates as estimates."""
    if not isinstance(value, str) or re.search(r"\b(after|aft)\b|^\s*>", value, re.I):
        return None
    years = [int(y) for y in re.findall(r"(?<!\d)(\d{4})(?!\d)", value)]
    years = [y for y in years if 1000 <= y <= 2100]
    return max(years) if years else None


def _dated(dossier):
    candidates = []
    vitals = dossier.get("vitals") or {}
    for kind in ("birth", "death"):
        event = vitals.get(kind) or {}
        year = _year(event.get("date"))
        if year is not None:
            status = event.get("status") or (
                "estimated" if re.search(r"circa|\bc\.|estimat|about", event.get("date", ""), re.I) else "unmarked"
            )
            candidates.append((year, kind, status))
    evidence_years = [_year(e.get("date")) for e in dossier.get("evidence") or []]
    evidence_years = [y for y in evidence_years if y is not None]
    candidates += [(y, "dated evidence", "record date") for y in evidence_years]
    selected = min(candidates, default=(None, None, "undated"), key=lambda x: x[0])
    return selected, min(evidence_years, default=None)


def _cycles(edges):
    parent = {e["child"]: e["father"] for e in edges}
    done, cycles = set(), []
    for start in parent:
        path, position, current = [], {}, start
        while current in parent and current not in done:
            if current in position:
                cycles.append(sorted(path[position[current] :]))
                break
            position[current] = len(path)
            path.append(current)
            current = parent[current]
        done.update(path)
    return sorted(cycles)


def relationship_status(relation: dict) -> tuple[str, str]:
    """Use an explicit research assessment before a saved WikiTree flag.

    Public tree links have a generic unknown assessment and a separate
    tree_status. An explicit uncertain/possible assessment still takes priority.
    """
    normalize = lambda value: re.sub(r'[\s-]+', '_', str(value or '').strip().casefold())
    status = normalize(relation.get('status')) or 'unassessed'
    if status in {'unknown', 'unassessed'} and relation.get('tree_status'):
        return normalize(relation['tree_status']), 'saved_wikitree_flag'
    return status, 'resolved_dossier_assessment'


def load_public_nodes(site_root: Path, variants: set[str]):
    site_root = Path(site_root)
    index = json.loads((site_root / "data/people-index.json").read_text())
    allowed = {x.casefold() for x in variants}
    nodes, aliases, raw, paths = {}, {}, [], {}
    pending_documentary_accounts = {}
    quality = {
        "missing_dossiers": [],
        "multiple_fathers": [],
        "outside_cohort_fathers": [],
        "undated_people": [],
        "cycles": [],
    }
    for row in index:
        if not any(str(s).casefold() in allowed for s in row.get("birth_surnames") or []):
            continue
        relative = urlsplit(row.get("json_url") or "").path
        if not re.fullmatch(r"/people/[A-Za-z0-9_-]+\.json", relative):
            quality["missing_dossiers"].append(str(row.get("id")))
            continue
        if relative in paths:
            aliases[str(row["id"])] = paths[relative]
            continue
        try:
            dossier = json.loads((site_root / relative.lstrip("/")).read_text())
        except (OSError, ValueError):
            quality["missing_dossiers"].append(str(row.get("id")))
            continue
        ident = str(dossier.get("id") or row["id"])
        paths[relative] = ident
        for alias in [row["id"], ident, *(dossier.get("alternate_ids") or []), *(row.get("alternate_ids") or [])]:
            if isinstance(alias, str):
                aliases[alias] = ident
        if ident in nodes:
            continue
        (year, basis, status), first_record = _dated(dossier)
        vitals = dossier.get("vitals") or {}
        birth = vitals.get("birth") or {}
        death = vitals.get("death") or {}
        nodes[ident] = dict(
            id=ident,
            name=dossier.get("name") or row.get("name") or ident,
            url=row.get("html_url") or f"/people/{ident.casefold()}.html",
            gender=(dossier.get("identity") or {}).get("gender") or row.get("gender") or "",
            birth_year=_year(birth.get("date")),
            death_year=_year(death.get("date")),
            birth_status=birth.get("status"),
            year=year,
            year_basis=basis,
            year_status=status,
            first_record_year=first_record,
        )
        historical = dossier.get('historical_basis') or {}
        latest_birth = historical.get('latest_birth_year')
        source = urlsplit(historical.get('source_url') or '')
        if (re.fullmatch(r'record-[a-z0-9]+(?:-[a-z0-9]+)*', ident)
                and row.get('html_url') == f'/people/{ident}.html'
                and relative == f'/people/{ident}.json'
                and dossier.get('pending_profile_creation') is True
                and dossier.get('creation_status') in {'identity_hold', 'hold_source_verification'}
                and (dossier.get('wikitree_update') or {}).get('new_profile') is True
                and not any(item.get(key) for item in (row, dossier)
                            for key in ('wikitree_url', 'profile_ids', 'profile_id', 'linked_identity'))
                and not any(item.get(key) for item in (row, dossier)
                            for key in ('private', 'living', 'likely_living'))
                and type(latest_birth) is int and latest_birth < date.today().year - 120
                and source.scheme in {'http', 'https'} and source.netloc):
            pending_documentary_accounts[ident] = dossier['creation_status']
        for relation in (dossier.get("relationships") or {}).get("parents") or []:
            if str(relation.get("relationship", "")).casefold() != "father":
                continue
            status, status_basis = relationship_status(relation)
            if (
                status in EXCLUDED
                or relation.get("lifecycle") not in (None, "current")
                or relation.get("display") in {"alternative", "historical", "superseded"}
                or relation.get("publication_status") in {"withheld", "blocked", "rejected"}
            ):
                continue
            if relation.get("id"):
                raw.append(
                    dict(
                        child=ident,
                        father=str(relation["id"]),
                        status=status,
                        basis=relation.get("reason") or relation.get("basis") or "",
                        assertion_id=relation.get("assertion_id"),
                        assessment_status=relation.get('status') or 'unassessed',
                        tree_status=relation.get('tree_status'),
                        status_basis=status_basis,
                        selection_priority=(
                            3 if relation.get('publication_status') == 'approved'
                            and relation.get('working_selection') is True else
                            2 if relation.get('publication_status') == 'approved'
                            and relation.get('display') == 'current' else
                            1 if relation.get('tree_relationship') is True else 0
                        ),
                    )
                )
    documentary = load_people(site_root / 'data/ancestry-documentary-people.json')
    for revision in load_chronology(site_root / 'data/ancestry-documentary-people.json'):
        if revision['id'] in nodes:
            nodes[revision['id']].update({k: revision[k] for k in
                ('year', 'year_basis', 'year_status', 'birth_year', 'death_year', 'first_record_year') if k in revision})
    documentary_ids = {p['id'] for p in documentary}
    for person in documentary:
        if person['id'] in nodes:
            if (person['id'] not in pending_documentary_accounts
                    or any(person.get(key) for key in ('private', 'living', 'likely_living'))
                    or person['url'] != f'/people/{person["id"]}.html'):
                raise ValueError(f'Duplicate documentary ancestor: {person["id"]}')
            if pending_documentary_accounts[person['id']] == 'identity_hold':
                nodes[person['id']].update(metric_node(person))
            # Source verification does not change an existing public account's
            # cohort membership. Adding its tree presentation must not shrink
            # the measured population or count a second person.
        else:
            nodes[person['id']] = metric_node(person)
        aliases[person['id']] = person['id']
    shared_path = site_root / 'assets/research/relationship-assessments.json'
    if documentary and shared_path.exists():
        for assessment in json.loads(shared_path.read_text()):
            if not (assessment.get('working_selection') is True
                    and assessment.get('publication_status') == 'approved'
                    and assessment.get('display') not in {'alternative', 'historical', 'superseded'}
                    and assessment.get('lifecycle') in (None, 'current')
                    and assessment.get('status') in {'uncertain', 'probable'}
                    and assessment.get('allow_new_relationship') is True):
                continue
            views = assessment.get('perspectives') or {}
            child = next((p for p, v in views.items() if v.get('relationship') == 'father'), None)
            father = next((p for p, v in views.items() if v.get('relationship') != 'father'), None)
            if child in nodes and father in nodes and {child, father} & documentary_ids:
                raw.append(dict(child=child, father=father, status=assessment['status'],
                                basis=assessment.get('basis', ''), assertion_id=assessment['assertion_id'],
                                selection_priority=3))
    # Select the public working father, never the most confident hypothesis.
    # Resolve aliases before testing uniqueness, including fathers outside the
    # surname cohort. Conflicting selections at the same priority stay ambiguous.
    candidates = defaultdict(list)
    for edge in raw:
        edge['father'] = aliases.get(edge['father'], edge['father'])
        candidates[edge['child']].append(edge)
    raw = []
    for child_edges in candidates.values():
        priority = max(edge['selection_priority'] for edge in child_edges)
        for edge in child_edges:
            selected = edge.pop('selection_priority') == priority
            if selected:
                raw.append(edge)
    by_child = defaultdict(dict)
    all_fathers = defaultdict(set)
    for edge in raw:
        edge["father"] = aliases.get(edge["father"], edge["father"])
        all_fathers[edge["child"]].add(edge["father"])
        if edge["father"] not in nodes:
            quality["outside_cohort_fathers"].append(edge["child"])
            continue
        existing = by_child[edge["child"]].get(edge["father"])
        if not existing or edge["status"] in CONFIDENT:
            by_child[edge["child"]][edge["father"]] = edge
    edges = []
    for child, fathers in sorted(by_child.items()):
        if len(all_fathers[child]) != 1:
            quality["multiple_fathers"].append(child)
        else:
            edges.extend(fathers.values())
    quality["cycles"] = _cycles(edges)
    # Reuse public pair-specific estimates; certainty flags supply no percentage.
    estimate_path = site_root / 'assets/research/relationship-probabilities.json'
    estimates = {}
    if estimate_path.exists():
        for estimate in json.loads(estimate_path.read_text()).get('estimates', []):
            if estimate.get('relationship') == 'father':
                child = aliases.get(estimate['subject_id'], estimate['subject_id'])
                father = aliases.get(estimate['relative_id'], estimate['relative_id'])
                estimates[(child, father)] = estimate
    for edge in edges:
        estimate = estimates.get((edge['child'], edge['father']))
        if (estimate and type(estimate.get('percent')) in (int, float)
                and 0 < estimate['percent'] < 100 and estimate.get('basis')
                and confidence_band(edge['status']) != 'unrated'
                and confidence_band(estimate.get('assessment_status')) == confidence_band(edge['status'])
                and (not estimate.get('assertion_id') or not edge.get('assertion_id')
                     or estimate['assertion_id'] == edge['assertion_id'])):
            edge['confidence_percent'] = estimate['percent']
    quality["undated_people"] = sorted(i for i, n in nodes.items() if n["year"] is None)
    quality["outside_cohort_fathers"] = sorted(set(quality["outside_cohort_fathers"]))
    return nodes, sorted(edges, key=lambda e: (e["child"], e["father"])), quality


def paternal_link_impacts(nodes, edges, cutoff, cohort_ids):
    """Measure working dependency and the gain from upgrading one selected link.

    The latter joins only the two existing confident components. Other uncertain
    links stay uncertain. Documentary connectors never enter the person counts.
    These are hypothetical research yields, not evidence or expected probabilities.
    """
    cohort = set(cohort_ids) & nodes.keys()
    eligible = set(cohort)
    parents = {e['child']: e['father'] for e in edges}
    stack = list(cohort)
    while stack:
        father = parents.get(stack.pop())
        if father in nodes and father not in eligible and not (
                nodes[father].get('birth_year') is not None and nodes[father]['birth_year'] > cutoff):
            eligible.add(father)
            stack.append(father)
    selected = [e for e in edges if {e['child'], e['father']} <= eligible]
    strong = [e for e in selected if e['status'] in CONFIDENT]
    strong_cycles = {n for cycle in _cycles(strong) for n in cycle}
    strong = [e for e in strong if not {e['child'], e['father']} <= strong_cycles]
    cyclic = {n for cycle in _cycles(selected) for n in cycle}
    selected = [e for e in selected if not {e['child'], e['father']} <= cyclic]
    working, confident = defaultdict(set), defaultdict(set)
    for edge in selected:
        child, father = edge['child'], edge['father']
        working[child].add(father)
        working[father].add(child)
    # Each threshold excludes its own cycles, as summarize does. A cycle in
    # the working graph need not exist after uncertain edges are filtered.
    for edge in strong:
        child, father = edge['child'], edge['father']
        confident[child].add(father)
        confident[father].add(child)

    def reachable(graph, start, cut=None):
        seen, pending = {start}, [start]
        while pending:
            node = pending.pop()
            for other in graph[node]:
                if (cut and {node, other} == cut) or other in seen:
                    continue
                seen.add(other)
                pending.append(other)
        return seen

    component, sizes = {}, {}
    for node in sorted(eligible):
        if node in component:
            continue
        members = reachable(confident, node)
        for member in members:
            component[member] = node
        sizes[node] = len(members & cohort)
    rows = []
    for edge in selected:
        child, father = edge['child'], edge['father']
        child_side = reachable(working, child, {child, father})
        father_side = reachable(working, father, {child, father})
        if child_side & father_side:
            continue
        n, m = len(child_side & cohort), len(father_side & cohort)
        c, f = component[child], component[father]
        a, b = sizes[c], sizes[f]
        rows.append({**edge, 'child_side': n, 'parent_side': m, 'cross_pairs': n * m,
                     'confident_child_side': a, 'confident_parent_side': b,
                     'confident_pair_gain': a * b if c != f else 0,
                     'confident_component_reduction': int(c != f and a > 0 and b > 0)})
    return rows


def summarize(nodes, edges, cutoff, view="working", cohort_ids=None):
    if view not in MEASUREMENT_VIEWS:
        raise ValueError("view must be working, supported or confident")
    grades = SUPPORTED if view == 'supported' else CONFIDENT
    eligible_edges = [e for e in edges if view == "working" or e["status"] in grades]
    future = set()
    if cohort_ids is None:
        cohort = {i for i, n in nodes.items() if n.get('cohort_member') is not False
                  and n.get("year") is not None and n["year"] <= cutoff}
    else:
        cohort = set(cohort_ids) & nodes.keys()
    # Named record ancestors can connect measured profiles without changing
    # the denominator. Fixed cohorts also traverse newly documented ancestors.
    graph_nodes = set(cohort)
    by_child = {e['child']: e['father'] for e in eligible_edges}
    stack = list(cohort)
    while stack:
        father = by_child.get(stack.pop())
        if father not in nodes or father in graph_nodes:
            continue
        if nodes[father].get('birth_year') is not None and nodes[father]['birth_year'] > cutoff:
            future.add(father)
            continue
        graph_nodes.add(father)
        if cohort_ids is None and nodes[father].get('cohort_member') is not False:
            cohort.add(father)
        stack.append(father)
    selected = [e for e in eligible_edges if e["child"] in graph_nodes and e["father"] in graph_nodes]
    cycles = _cycles(selected)
    cycle_nodes = {i for cycle in cycles for i in cycle}
    selected = [e for e in selected if not (e["child"] in cycle_nodes and e["father"] in cycle_nodes)]
    parents = {e["child"]: e["father"] for e in selected}
    adjacency, children = defaultdict(set), defaultdict(set)
    for edge in selected:
        a, b = edge["child"], edge["father"]
        adjacency[a].add(b)
        adjacency[b].add(a)
        children[b].add(a)
    unseen, components, sizes = set(graph_nodes), [], {}
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        component, stack = {start}, [start]
        while stack:
            for item in adjacency[stack.pop()]:
                if item in unseen:
                    unseen.remove(item)
                    component.add(item)
                    stack.append(item)
        measured = component & cohort
        if measured:
            components.append(measured)
        sizes.update(dict.fromkeys(component, len(measured)))
    roots = []
    for ident in sorted(graph_nodes):
        node = nodes[ident]
        if node.get("gender", "").casefold() not in {"male", "m"} or ident in parents:
            continue
        descendants, stack = set(), list(children[ident])
        while stack:
            item = stack.pop()
            if item not in descendants:
                descendants.add(item)
                stack.extend(children[item])
        if len(children[ident]) >= 2 or len(descendants) >= 2:
            roots.append(
                {
                    **{
                        k: node.get(k)
                        for k in ("id", "name", "url", "year", "year_basis", "year_status", "first_record_year")
                    },
                    "child_count": len(children[ident]),
                    "descendant_count": len(descendants & cohort),
                    "component_size": sizes[ident],
                }
            )
    roots.sort(key=lambda r: (r["year"] is None, r["year"] or 9999, -r["descendant_count"], r["id"]))
    population = len(cohort)
    largest = max(map(len, components), default=0)
    pair_count = sum(len(c) * (len(c) - 1) for c in components)
    confidence = [e['confidence_percent'] for e in selected
                  if type(e.get('confidence_percent')) in (int, float)
                  and 0 < e['confidence_percent'] < 100]
    result = dict(
        cohort_ids=sorted(cohort),
        population=population,
        edge_count=len(selected),
        component_count=len(components),
        largest_component_size=largest,
        largest_component_percent=100 * largest / population if population else 0,
        connected_pairs_percent=100 * pair_count / (population * (population - 1)) if population > 1 else 0,
        unattached_multi_child_roots=[r for r in roots if r["child_count"] >= 2],
        family_roots=roots,
        edge_status_counts=dict(sorted(Counter(e["status"] for e in selected).items())),
        individual_confidence=dict(
            rated_edge_count=len(confidence),
            unrated_edge_count=len(selected) - len(confidence),
            rated_edges_percent=100 * len(confidence) / len(selected) if selected else 0,
            mean_percent=sum(confidence) / len(confidence) if confidence else None,
        ),
        quality=dict(
            cycles=cycles,
            cycle_edges_excluded=sum(len(c) for c in cycles),
            later_born_ancestors_excluded=sorted(future),
            undated_ancestors=[i for i in sorted(cohort) if nodes[i].get("year") is None],
        ),
    )
    if graph_nodes - cohort:
        result['connector_ids'] = sorted(graph_nodes - cohort)
    return result
