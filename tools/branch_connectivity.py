"""Paternal connectivity over resolved public genealogy dossiers.

No surname, platform ID or proposed ancestor is built into the graph algorithm.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from tools.documentary_ancestry import load_chronology, load_people, metric_node

CONFIDENT = frozenset(
    {"certain", "confident", "confirmed", "proved", "documented", "strongly_supported", "dna_confirmed"}
)
SUPPORTED = CONFIDENT | {'probable'}
MEASUREMENT_VIEWS = ('working', 'supported', 'confident')
METHOD_VERSION = 3
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
        for relation in (dossier.get("relationships") or {}).get("parents") or []:
            if str(relation.get("relationship", "")).casefold() != "father":
                continue
            status, status_basis = relationship_status(relation)
            if (
                status in EXCLUDED
                or relation.get("lifecycle") not in (None, "current")
                or relation.get("display") in {"historical", "superseded"}
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
            raise ValueError(f'Duplicate documentary ancestor: {person["id"]}')
        nodes[person['id']] = metric_node(person)
        aliases[person['id']] = person['id']
    shared_path = site_root / 'assets/research/relationship-assessments.json'
    if documentary and shared_path.exists():
        for assessment in json.loads(shared_path.read_text()):
            if not (assessment.get('working_selection') is True
                    and assessment.get('publication_status') == 'approved'
                    and assessment.get('status') in {'uncertain', 'probable'}
                    and assessment.get('allow_new_relationship') is True):
                continue
            views = assessment.get('perspectives') or {}
            child = next((p for p, v in views.items() if v.get('relationship') == 'father'), None)
            father = next((p for p, v in views.items() if v.get('relationship') != 'father'), None)
            if child in nodes and father in nodes and {child, father} & documentary_ids:
                raw.append(dict(child=child, father=father, status=assessment['status'],
                                basis=assessment.get('basis', ''), assertion_id=assessment['assertion_id']))
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
    quality["undated_people"] = sorted(i for i, n in nodes.items() if n["year"] is None)
    quality["outside_cohort_fathers"] = sorted(set(quality["outside_cohort_fathers"]))
    return nodes, sorted(edges, key=lambda e: (e["child"], e["father"])), quality


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
