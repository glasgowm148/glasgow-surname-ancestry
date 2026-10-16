#!/usr/bin/env python3
"""Build the standalone viewer from the catalogue's canonical public data."""

from __future__ import annotations

import argparse
import csv
from datetime import date
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PUBLIC_DIR = ROOT / "www" / "onetree" / "glasgow-one-tree-polished-3"
sys.path.insert(0, str(ROOT))

from tools.project_paths import merged_map_profiles  # noqa: E402
from tools.documentary_ancestry import load_chronology, load_people  # noqa: E402


WIKITREE = "https://www.wikitree.com/wiki/"
CATALOGUE = "https://glasgow.phenotype.dev/people/"
STATUS = {"5": "non-biological", "10": "uncertain", "20": "confident", "30": "DNA-confirmed"}
WORKING_ASSESSMENTS = ROOT / "research" / "relationship_assessments.json"
DOCUMENTARY_PEOPLE = ROOT / 'research/ancestry-connections/documentary-people.json'

REGIONS = [
    {"id": "principal", "label": "Principal pedigrees", "short": "Principal pedigrees", "title": "Principal pedigrees", "sub": "The largest recorded family branches", "color": "#506b58"},
    {"id": "branches", "label": "Documented branches", "short": "Documented branches", "title": "Other documented branches", "sub": "Recorded family fragments with a shared root profile", "color": "#69785f"},
    {"id": "small", "label": "Smaller families", "short": "Smaller families", "title": "Smaller documented families", "sub": "Separate small recorded family fragments", "color": "#7d8175"},
]

LOCATIONS = [
    {"id": "scotland", "label": "Scotland", "color": "#4f7458"},
    {"id": "ireland", "label": "Ireland / Ulster", "color": "#378076"},
    {"id": "america", "label": "United States", "color": "#517da5"},
    {"id": "canada", "label": "Canada", "color": "#687f91"},
    {"id": "oceania", "label": "Australia / New Zealand", "color": "#766c9d"},
    {"id": "england", "label": "England / Wales", "color": "#8b735b"},
    {"id": "other", "label": "Other / unknown", "color": "#85887f"},
]
LOCATION_BY_ID = {item["id"]: item for item in LOCATIONS}


def profile_name(profile: dict) -> str:
    return profile.get("LongName") or profile.get("BirthName") or " ".join(
        str(profile.get(key) or "") for key in ("Prefix", "FirstName", "MiddleName", "LastNameCurrent", "Suffix")
    ).strip() or profile.get("Name") or "Unknown"


def year_of(value: str) -> int | None:
    match = re.search(r"\b(1\d{3}|20\d{2})\b", value or "")
    return int(match.group()) if match else None


def location_for(text: str) -> str:
    text = (text or "").casefold()
    if re.search(r"canada|ontario|quebec|nova scotia|new brunswick|british columbia|newfoundland|\bb\.?c\.?\b", text):
        return "canada"
    if re.search(r"new zealand|australia|queensland|tasmania|new south wales|\bvictoria\b|oromahoe", text):
        return "oceania"
    if re.search(r"united states|\busa\b|\bamerica\b|alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|district of columbia|indian territory|\bs\.?\s*carolina\b|\bpa\b|\bmd\b|\bfla\b|\btn\b", text):
        return "america"
    if re.search(r"ireland|antrim|londonderry|\bderry\b|tyrone|donegal|belfast|ulster|leitrim|dublin|larne|armagh|laois|kilrea|kilwaughter|townland", text):
        return "ireland"
    if re.search(r"scotland|glasgow|lanark|ayr|lothian|edinburgh|renfrew|fife|roxburgh|peebles|stirling|paisley|inverness|aberdeen|perthshire|argyll|kirkurd|mid calder", text):
        return "scotland"
    if re.search(r"england|wales|london|yorkshire|norfolk|lancashire|\bkent\b|durham|northumberland|merseyside|cheshire|cornwall|devon|somerset|warwickshire|worcestershire", text):
        return "england"
    return "other"


def relation(row: dict, role: str, raw: dict, catalogue_by_id: dict[str, dict], public_ids: set[str]) -> list[dict]:
    status = STATUS.get(str((raw.get("DataStatus") or {}).get(role.title()) or ""), "unmarked")
    result = []
    for item in row.get(role, []) or []:
        profile_id = item.get("id") or ""
        if item.get("withheld"):
            result.append({"id": "", "name": "Private parent", "role": role, "status": status, "withheld": True})
            continue
        if not profile_id and not item.get("name"):
            continue
        result.append({
            "id": profile_id, "name": item.get("name") or profile_id, "role": role, "status": status,
            "inModel": profile_id in public_ids,
        })
    return result


def external_relations(items: list[dict], role: str, catalogue_by_id: dict[str, dict], public_ids: set[str]) -> list[dict]:
    result = []
    for item in items or []:
        profile_id = item.get("id") or ""
        if item.get("withheld"):
            result.append({"id": "", "name": f"Private {role}", "role": role, "withheld": True})
            continue
        result.append({
            "id": profile_id, "name": item.get("name") or profile_id or f"Unnamed {role}", "role": role,
            "inModel": profile_id in public_ids,
            "marriageDate": item.get("marriage_date") or "", "marriageLocation": item.get("marriage_location") or "",
        })
    return result


def apply_working_hypotheses(people: list[dict], assessments: list[dict], parent_aliases: dict | None = None) -> int:
    """Overlay explicitly selected uncertain father links onto the local model."""
    by_id = {person["id"]: person for person in people}
    parent_aliases = parent_aliases or {}
    selected = []
    selected_children = set()
    for assessment in assessments:
        if not (assessment.get("working_selection") is True
                and assessment.get("publication_status") == "approved"
                and assessment.get("status") == "uncertain"
                and assessment.get("allow_new_relationship") is True):
            continue
        perspectives = assessment.get("perspectives") or {}
        child = next((pid for pid, view in perspectives.items() if view.get("relationship") == "father"), None)
        father = next((pid for pid, view in perspectives.items() if view.get("relationship") != "father"), None)
        if not child or not father or child == father:
            raise ValueError(f"Working hypothesis {assessment.get('assertion_id', '<unknown>')} must define father and child perspectives")
        if child not in by_id or father not in by_id:
            raise ValueError(f"Working hypothesis {assessment.get('assertion_id', '<unknown>')} has an endpoint outside the public model")
        existing = [row for row in by_id[child]["parents"] if row.get("role") == "father"]
        resolution = assessment.get('parent_alias_resolution') or {}
        prior_alias = resolution.get('original_id')
        aliases = [row for row in existing if row.get('id') not in by_id
                   and (parent_aliases.get(row.get('id')) == father or
                        (not row.get('id') and not row.get('withheld')
                         and row.get('name') == 'Parent outside current One-Tree export'
                         and resolution.get('canonical_id') == father
                         and parent_aliases.get(prior_alias) == father))]
        if existing and any(row.get('id') != father and row not in aliases for row in existing):
            raise ValueError(f"Working hypothesis {assessment.get('assertion_id', '<unknown>')} conflicts with existing father of {child}")
        if not existing or aliases:
            if child in selected_children:
                raise ValueError(f"Working hypotheses conflict: multiple selected fathers for {child}")
            selected_children.add(child)
            selected.append((child, father, assessment, aliases))
    edges = {person["id"]: next((row["id"] for row in person["parents"] if row.get("role") == "father"), None)
             for person in people}
    for child, father, assessment, aliases in selected:
        edges[child] = father
        seen, node = set(), child
        while node:
            if node in seen:
                raise ValueError(f"Working hypothesis {assessment.get('assertion_id', '<unknown>')} introduces a paternal cycle")
            seen.add(node)
            node = edges.get(node)
    for child, father, assessment, aliases in selected:
        if aliases:
            by_id[child]['parentAliasResolutions'] = [dict(original=row.copy(), canonical_id=father,
                original_profile_id=row.get('id') or assessment['parent_alias_resolution']['original_id'],
                source='saved_wikitree_redirect') for row in aliases]
            by_id[child]['parents'] = [row for row in by_id[child]['parents'] if row not in aliases
                                      and not (row.get('role') == 'father' and row.get('id') == father)]
        by_id[child]["parents"].append({
            "id": father, "name": by_id[father]["name"], "role": "father", "status": "uncertain",
            "inModel": True, "reason": assessment.get("basis") or "", "source": "local_working_hypothesis",
            "assertion_id": assessment.get("assertion_id"), "analysis_links": assessment.get("analysis_links") or [],
            "hypothesis": True,
        })
        children = by_id[father].setdefault('childrenRecorded', [])
        previous = next((row for row in children if row.get('id') == child), {})
        children[:] = [row for row in children if row.get('id') != child]
        children.append({**previous, 'id': child, 'name': by_id[child]['name'], 'role': 'child',
                         'inModel': True, 'status': 'uncertain', 'hypothesis': True,
                         'source': 'local_working_hypothesis', 'assertion_id': assessment.get('assertion_id'),
                         'reason': assessment.get('basis') or ''})
    return len(selected)


def apply_reviewed_parent_replacements(people: list[dict], assessments: list[dict]) -> list[str]:
    """Apply sourced role corrections, retaining the previous parent display."""
    by_id = {p['id']: p for p in people}
    approved = {a.get('assertion_id'): a for a in assessments if a.get('publication_status') == 'approved'}
    proposals = []
    for assessment in approved.values():
        replacement = assessment.get('tree_parent_replacement')
        if not replacement:
            continue
        child, father, previous = (replacement.get(k) for k in ('child', 'father', 'previous_parent'))
        correction = approved.get(replacement.get('role_correction_assertion'), {})
        if (child not in by_id or father not in by_id or previous == father
                or assessment.get('status') not in {'proved', 'strongly_supported', 'confident'}
                or not assessment.get('source_ids')
                or assessment.get('perspectives', {}).get(child, {}).get('relationship') != 'father'
                or correction.get('role_correction', {}).get(child, {}).get('to') != 'sibling'
                or previous not in correction.get('people', []) or not correction.get('source_ids')):
            raise ValueError('Parent replacement requires an approved father and sourced sibling-role correction')
        old = [r for r in by_id[child]['parents'] if r.get('role') == 'father']
        if any(r.get('id') not in {previous, father} for r in old):
            raise ValueError('Parent replacement conflicts with another attached father: ' + child)
        proposals.append((child, father, assessment, old))
    edges = {p['id']: next((r['id'] for r in p['parents'] if r.get('role') == 'father'), None) for p in people}
    edges.update({child: father for child, father, _, _ in proposals})
    for child, _, _, _ in proposals:
        seen, node = set(), child
        while node:
            if node in seen:
                raise ValueError('Parent replacement introduces a paternal cycle: ' + child)
            seen.add(node); node = edges.get(node)
    changed = set()
    for child, father, assessment, old in proposals:
        person = by_id[child]
        person['priorParentRoles'] = old
        person['parents'] = [r for r in person['parents'] if r.get('role') != 'father'] + [dict(
            id=father, name=by_id[father]['name'], role='father', status=assessment['status'], inModel=True,
            source='approved_research_parent_replacement', assertion_id=assessment['assertion_id'],
            reason=assessment['basis'], analysis_links=assessment.get('analysis_links', []))]
        person['note'] = (person.get('note', '') + ' ' + assessment['tree_parent_replacement']['reason']).strip()
        previous = assessment['tree_parent_replacement']['previous_parent']
        if previous in by_id:
            old_children = by_id[previous].get('childrenRecorded', [])
            by_id[previous]['priorChildRoles'] = [r for r in old_children if r.get('id') == child]
            by_id[previous]['childrenRecorded'] = [r for r in old_children if r.get('id') != child]
            changed.add(previous)
        current_children = [r for r in by_id[father].get('childrenRecorded', []) if r.get('id') != child]
        current_children.append(dict(id=child, name=person['name'], role='child', inModel=True,
            status=assessment['status'], reason=assessment['basis'], assertion_id=assessment['assertion_id']))
        by_id[father]['childrenRecorded'] = current_children
        changed.update([child, father])
    return sorted(changed)


def generate_model(catalogue_path: Path, prior: dict) -> dict:
    payload = json.loads(catalogue_path.read_text(encoding="utf-8"))
    rows = payload["people"]
    profiles, exports = merged_map_profiles()

    # Prefer each profile's own dossier over a combined comparison entry.
    catalogue_by_id: dict[str, dict] = {}
    for row in sorted(rows, key=lambda item: (len(item.get("profile_ids", [])) != 1, item.get("catalogue_id", ""))):
        for profile_id in row.get("profile_ids", []):
            catalogue_by_id.setdefault(profile_id, row)
    public_ids = set(catalogue_by_id) & set(profiles)

    people = []
    for profile_id in sorted(public_ids, key=str.casefold):
        raw = profiles[profile_id]
        row = catalogue_by_id[profile_id]
        fathers = relation(row, "father", raw, catalogue_by_id, public_ids)
        mothers = relation(row, "mother", raw, catalogue_by_id, public_ids)
        birth_date, death_date = raw.get("BirthDate") or "", raw.get("DeathDate") or ""
        birth_status = str((raw.get("DataStatus") or {}).get("BirthDate") or "")
        birthplace = raw.get("CorrectedBirthLocation") or raw.get("BirthLocation") or row.get("birth_location") or ""
        deathplace = raw.get("CorrectedDeathLocation") or raw.get("DeathLocation") or row.get("death_location") or ""
        birth_location_id, death_location_id = location_for(birthplace), location_for(deathplace)
        location_id = birth_location_id if birth_location_id != "other" else death_location_id
        if location_id == "other":
            location_id = location_for(row.get("cluster") or "")
        location = LOCATION_BY_ID[location_id]
        people.append({
            "id": profile_id, "name": profile_name(raw), "born": year_of(birth_date), "died": year_of(death_date),
            "birthDisplay": row.get("birth") or "", "deathDisplay": row.get("death") or "",
            "birthplace": birthplace, "deathplace": deathplace,
            "sex": raw.get("Gender") or row.get("gender") or "", "parents": fathers + mothers,
            "partners": external_relations(row.get("spouses", []), "spouse", catalogue_by_id, public_ids),
            "childrenRecorded": external_relations(row.get("children", []), "child", catalogue_by_id, public_ids),
            "note": "; ".join(row.get("relationship_warnings", [])), "kind": "person",
            "first": raw.get("FirstName") or raw.get("RealName") or "", "surname": raw.get("LastNameAtBirth") or "",
            "currentSurname": raw.get("LastNameCurrent") or "",
            "bornApprox": birth_status not in ("", "certain") or bool(birth_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth_date)),
            "year": year_of(birth_date) or year_of(death_date) or 1850,
            "catalogueId": row["catalogue_id"], "locationRegion": location_id,
            "locationLabel": location["label"], "locationColor": location["color"],
            "birthLocationRegion": birth_location_id, "deathLocationRegion": death_location_id,
            "cluster": row.get("cluster") or "",
        })

    documentary = load_people(DOCUMENTARY_PEOPLE)
    for revision in load_chronology(DOCUMENTARY_PEOPLE):
        for person in people:
            if person['id'] == revision['id']:
                display = revision.get('tree_display') or {}
                person.update({k: display[k] for k in ('born', 'died', 'year', 'birthDisplay', 'deathDisplay', 'lifeLabel', 'deathplace', 'deathLocationRegion') if k in display})
                person['note'] = (person.get('note', '') + ' ' + revision['reason']).strip()
    for person in documentary:
        if person['id'] in public_ids:
            raise ValueError(f'Duplicate documentary ancestor: {person["id"]}')
        place = LOCATION_BY_ID['scotland']
        people.append(dict(id=person['id'], name=person['name'], kind='person',
                           born=None, died=None, birthDisplay='', deathDisplay='',
                           birthplace='', deathplace='', sex=person.get('gender', ''),
                           parents=[], partners=[], childrenRecorded=[],
                           note=person['summary'], first=person['name'].split()[0],
                           birthSurname='Glasgow', currentSurname='Glasgow', bornApprox=False,
                           year=person['first_record_year'], catalogueId=person['id'],
                           locationRegion='scotland', locationLabel=place['label'], locationColor=place['color'],
                           birthLocationRegion='other', deathLocationRegion='other',
                           cluster=person.get('record_place', ''), documentary=True,
                           recordUrl=person['url'], catalogueUrl=person['url'], wikitreeUrl=person.get('wikitree_url', ''),
                           recordPeriod=person['record_period'], recordPlace=person.get('record_place', ''), sourceIds=person['source_ids'],
                           identitySelection=person.get('identity_selection'), recordGroups=person.get('record_groups', [])))
    try:
        assessments = json.loads(WORKING_ASSESSMENTS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        assessments = []
    aliases_path = ROOT / 'data/wikitree/live-profile-overrides.json'
    parent_aliases = json.loads(aliases_path.read_text()).get('redirects', {}) if aliases_path.exists() else {}
    reviewed_parent_ids = apply_reviewed_parent_replacements(people, assessments)
    hypotheses = apply_working_hypotheses(people, assessments, parent_aliases)

    # One real parent drives the drawing. Both remain in the relationship list.
    chosen: dict[str, dict] = {}
    for person in people:
        options = [r for r in person["parents"] if r.get("inModel") and r.get("status") != "non-biological"]
        evidence_rank = {"DNA-confirmed": 0, "confident": 1, "unmarked": 2, "uncertain": 3}
        options.sort(key=lambda item: (not item.get("hypothesis", False), evidence_rank.get(item["status"], 2), item["role"] != "father", item["id"]))
        if options:
            chosen[person["id"]] = options[0]

    # Break malformed source cycles without inventing a replacement link.
    while True:
        cycle = None
        for start in chosen:
            order, seen, node = [], {}, start
            while node in chosen:
                if node in seen:
                    cycle = order[seen[node]:]
                    break
                seen[node] = len(order)
                order.append(node)
                node = chosen[node]["id"]
            if cycle:
                break
        if not cycle:
            break
        chosen.pop(max(cycle), None)

    people_by_id = {person["id"]: person for person in people}
    chosen_children: dict[str, list[str]] = {person["id"]: [] for person in people}
    for child_id, picked in chosen.items():
        chosen_children[picked["id"]].append(child_id)

    subtree: dict[str, int] = {}
    def count_subtree(profile_id: str) -> int:
        subtree[profile_id] = 1 + sum(count_subtree(child) for child in chosen_children[profile_id])
        return subtree[profile_id]

    component_roots = [person["id"] for person in people if person["id"] not in chosen]
    for root_id in component_roots:
        count_subtree(root_id)

    # Family sections are real pedigree roots. Very large pedigrees are split only
    # at meaningful recorded child branches so the sidebar stays navigable.
    major_roots = {profile_id for profile_id in component_roots if subtree[profile_id] >= 8}
    anchors = set(major_roots)
    def add_branch_anchors(profile_id: str) -> None:
        cursor = profile_id
        while subtree[cursor] > 220:
            substantial = [child for child in chosen_children[cursor] if subtree[child] >= 20]
            if len(substantial) >= 2:
                anchors.update(substantial)
                for child in substantial:
                    if subtree[child] > 220:
                        add_branch_anchors(child)
                return
            large = [child for child in chosen_children[cursor] if subtree[child] > 220]
            if len(large) != 1:
                return
            cursor = large[0]

    for root_id in sorted(major_roots):
        add_branch_anchors(root_id)

    def branch_label(profile_id: str) -> str:
        name = re.sub(r"\s+", " ", people_by_id[profile_id]["name"]).strip()
        return f"{name} line"

    sections = []
    for profile_id in sorted(anchors, key=lambda item: (-subtree[item], people_by_id[item]["year"], item)):
        person = people_by_id[profile_id]
        life = ('Recorded ' + person['recordPeriod']) if person.get('documentary') else (person.get('lifeLabel') or "–".join(str(value) if value else "?" for value in (person["born"], person["died"])))
        place = person["birthplace"] or person["deathplace"] or person.get('recordPlace') or "place not recorded"
        tier = "principal" if subtree[profile_id] >= 220 else "branches"
        sections.append({
            "id": profile_id, "label": branch_label(profile_id),
            "sub": f"{life} · {place} · {subtree[profile_id]:,} profiles",
            "region": tier, "color": next(region["color"] for region in REGIONS if region["id"] == tier),
        })
    sections.append({
        "id": "@smaller-families", "label": "Smaller documented families",
        "sub": "Separate recorded fragments; no shared ancestor is asserted",
        "region": "small", "color": LOCATION_BY_ID["other"]["color"],
    })

    for person in people:
        picked = chosen.get(person["id"])
        if picked:
            person["edge"] = {
                "parent": picked["id"], "type": "hypothesis" if picked.get("hypothesis") else "recorded", "semantic": "parent", "role": picked["role"],
                "status": picked["status"],
            }
        else:
            parent = "@root" if person["id"] in major_roots else "@smaller-families"
            person["edge"] = {
                "parent": parent, "type": "group", "semantic": "collection",
            }

    group_nodes = [{
        "id": "@root", "name": "Glasgow research collection", "kind": "group", "born": None, "died": None,
        "birthplace": "", "deathplace": "", "parents": [], "partners": [], "childrenRecorded": [],
        "note": "A visual collection root, not a person or shared ancestor.", "year": 1200,
    }]
    small_section = sections[-1]
    group_nodes.append({
        "id": small_section["id"], "name": small_section["label"], "kind": "group", "born": None, "died": None,
        "birthplace": "", "deathplace": "", "parents": [], "partners": [], "childrenRecorded": [],
        "note": small_section["sub"], "year": 1250, "locationRegion": "other",
        "locationLabel": LOCATION_BY_ID["other"]["label"], "locationColor": LOCATION_BY_ID["other"]["color"],
        "edge": {"parent": "@root", "type": "group", "semantic": "collection"},
    })

    # Tester-level annotations require separate publication approval.  Keep the
    # public atlas model deliberately empty even when a prior local model had
    # those annotations, so a normal source build cannot restore them.
    dna: list[dict[str, object]] = []
    parent_relationships = sum(len(person["parents"]) for person in people)
    spouse_relationships = sum(len(person["partners"]) for person in people) // 2
    recorded_edges = sum(not person.get("edge", {}).get("type") == "hypothesis" for person in people)
    return {
        "meta": {
            "title": "Glasgow profiles · recorded families and selected working hypotheses", "date": date.today().isoformat(), "people": len(people),
            "groups": len(sections), "recorded": recorded_edges, "parentRelationships": parent_relationships,
            "partners": spouse_relationships, "hypotheses": hypotheses, "withheld": payload.get("withheld_likely_living_count", 0),
            "coverage": f"Generated from the public catalogue dated {payload.get('generated', '')}; {len(people)-len(documentary):,} public WikiTree profiles and {len(documentary)} named documentary ancestors are included.",
            "documentaryPeople": len(documentary),
            "identityHypotheses": sum((p.get('identity_selection') or {}).get('selected') is True for p in documentary),
            "reviewedParentReplacementIds": reviewed_parent_ids,
            "method": "Current family fields come from the public catalogue, alongside named documentary ancestors with complete sourced accounts. Documentary record periods are not birth dates. Selected working hypotheses remain marked uncertain and counted separately. One parent drives the drawing; collection nodes do not assert common ancestry.",
            "sources": [{"title": "Glasgow research catalogue", "url": "https://glasgow.phenotype.dev/"}, {"title": "Public catalogue people data", "url": "https://glasgow.phenotype.dev/data/people.json"}, {"title": "Public Y-DNA explorer", "url": "https://glasgow.phenotype.dev/ydna/"}],
            "sourceExports": [path.name for path in exports], "catalogueGenerated": payload.get("generated", ""),
            "version": "4.2", "uiUpdated": date.today().isoformat(),
            "visualMethod": "Recorded family branches determine the layout. Family-local location blooms use petal area for country counts and order petals along the leading recorded migration route; zoom replaces blooms with real pedigree generations. Profile colour uses birthplace country when resolved, then death place or catalogue cluster as a fallback. No geography layer changes or invents a relationship.",
            "dnaCoverage": "Individual Y-DNA annotations are withheld pending publication approval. See the public Y-DNA summary.",
        },
        "root": "@root", "people": group_nodes + people, "sections": sections, "regions": REGIONS,
        "locations": LOCATIONS, "landmarks": ["@root", *[section["id"] for section in sections]], "dna": dna,
    }


def validate(model: dict) -> dict:
    people = {person["id"]: person for person in model["people"]}
    if len(people) != len(model["people"]) or model["root"] not in people:
        raise ValueError("The model must have unique IDs and a root.")
    for person in people.values():
        seen, node = set(), person["id"]
        while node != model["root"]:
            if node in seen:
                raise ValueError(f"Cycle detected at {node}")
            seen.add(node)
            parent = people[node].get("edge", {}).get("parent")
            if parent not in people:
                raise ValueError(f"Missing attachment for {node}: {parent}")
            edge = people[node]["edge"]
            if edge["type"] in {"recorded", "hypothesis"} and not any(
                relation.get("id") == parent and relation.get("role") == edge.get("role")
                for relation in people[node].get("parents", [])
            ):
                raise ValueError(f"Recorded display edge is not a structured parent link: {node} -> {parent}")
            node = parent
    real = [person for person in people.values() if person.get("kind") == "person"]
    for person in real:
        if not re.fullmatch(r"[a-z0-9_-]+", person.get("catalogueId", "")):
            raise ValueError(f"Bad catalogue ID for {person['id']}")
        if not person.get("locationColor") or not person.get("locationLabel"):
            raise ValueError(f"Missing location encoding for {person['id']}")
    return {
        "people": len(real), "group_nodes": len(people) - len(real),
        "recorded_display_parent_links": sum(p.get("edge", {}).get("type") == "recorded" for p in real),
        "structured_parent_relationships": sum(len(p.get("parents", [])) for p in real),
        "structured_spouse_mentions": sum(len(p.get("partners", [])) for p in real),
        "hypothesis_edges": sum(p.get("edge", {}).get("type") == "hypothesis" for p in real),
        "missing_attachments": 0, "cycles": 0, "bad_links": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue-data", type=Path, default=ROOT / "www" / "data" / "people.json")
    parser.add_argument("--model", type=Path, default=PUBLIC_DIR / "model.json")
    parser.add_argument("--template", type=Path, default=HERE / "template.html")
    parser.add_argument("--output", type=Path, default=PUBLIC_DIR / "index.html")
    parser.add_argument("--qa", type=Path, default=PUBLIC_DIR / "qa-summary.json")
    parser.add_argument("--ids", type=Path, default=PUBLIC_DIR / "wikitree-ids.csv")
    args = parser.parse_args()
    try:
        prior = json.loads(args.model.read_text(encoding="utf-8")) if args.model.exists() else {}
        model = generate_model(args.catalogue_data, prior)
        if args.model.resolve() == (PUBLIC_DIR / 'model.json').resolve():
            # Retain only the owner's explicitly approved, hash-pinned publication.
            from tools.approved_restorations import entries, restored_model, source
            approved = entries().get('onetree/glasgow-one-tree-polished-3/model.json')
            if approved and approved['kind'] == 'atlas-model':
                model = restored_model(model, json.loads(source(approved)))
        checks = validate(model)
        template = args.template.read_text(encoding="utf-8")
        if template.count("__MODEL__") != 1:
            raise ValueError("Template needs exactly one __MODEL__ placeholder.")
        args.model.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        data = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
        args.output.write_text(template.replace("__MODEL__", data), encoding="utf-8")
        args.qa.write_text(json.dumps({"generated": date.today().isoformat(), **checks}, indent=2) + "\n", encoding="utf-8")
        with args.ids.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["WikiTree ID", "Name", "WikiTree URL", "Catalogue URL"])
            for person in sorted((p for p in model["people"] if p.get("kind") == "person" and not p.get('documentary')), key=lambda p: p["id"].casefold()):
                writer.writerow([person["id"], person["name"], WIKITREE + person["id"], CATALOGUE + person["catalogueId"] + "/"])
        if args.model.resolve() == (PUBLIC_DIR / 'model.json').resolve():
            from tools.sync_ancestry_atlas import sync
            sync(ROOT / 'www', model)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Build failed: {exc}\n")
    print(f"Built {args.output} with {checks['people']:,} profiles and {model['meta']['hypotheses']:,} selected working hypothesis parent edges.")


if __name__ == "__main__":
    main()
