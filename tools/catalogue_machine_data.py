#!/usr/bin/env python3
"""Generate compact, provenance-aware machine interfaces for the catalogue."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

try:
    from project_paths import RESEARCH_DIR, SURNAME_RESEARCH_DIR
except ModuleNotFoundError:  # Imported as tools.catalogue_machine_data by tests.
    from tools.project_paths import RESEARCH_DIR, SURNAME_RESEARCH_DIR


SCHEMA_VERSION = "1.0"
SITE_URL = "https://glasgow.phenotype.dev"
WIKITREE_URL = "https://www.wikitree.com/wiki/"
WT_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
RELATIONSHIPS_PATH = SURNAME_RESEARCH_DIR / "indexes" / "relationship-hypotheses.md"
OCCUPATIONS = (
    "accountant", "architect", "blacksmith", "carpenter", "clerk", "doctor",
    "farmer", "fisher", "labourer", "lawyer", "merchant", "minister", "mason",
    "physician", "priest", "schoolmaster", "soldier", "teacher", "weaver",
)
GLASGOW_SURNAME_VARIANTS = frozenset({
    "glasgow", "glasco", "glascow", "glasgo", "glascoe", "glassco",
    "glassgow", "glasow", "glasoe", "glassgo", "glasko",
})


def _normal_match_text(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", str(value or "").casefold())
    return " ".join("glasgow" if token in GLASGOW_SURNAME_VARIANTS else token for token in tokens)


def _stable_id(prefix: str, *parts) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}-{sha1(payload.encode()).hexdigest()[:12]}"


def _unique(values) -> list:
    return list(dict.fromkeys(value for value in values if value not in (None, "", [])))


def _year(value: str):
    match = re.search(r"\b(1\d{3}|20\d{2})\b", value or "")
    return int(match.group()) if match else None


def _clean_markdown(value: str) -> str:
    value = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", value or "")
    return re.sub(r"[*_`]", "", value).strip()


def _citation_label(citation: str, url: str | None) -> str:
    """Keep a source-sized label when WikiTree table markup leaks into a citation."""
    citation = (citation or "").strip()
    if len(citation) <= 420 and "\n|-" not in citation:
        return citation
    if url and url in citation:
        url_start = citation.find(url)
        sentence_start = citation.rfind(". ", max(0, url_start - 700), url_start)
        start = sentence_start + 2 if sentence_start >= 0 else max(0, url_start - 300)
        sentence_end = citation.find(". ", url_start + len(url))
        end = sentence_end + 1 if sentence_end >= 0 else min(len(citation), url_start + len(url) + 220)
        label = citation[start:end]
    else:
        label = citation[:420]
    label = re.sub(r"https?://[^\s<>()\]]+", "", label)
    label = re.sub(r"\s+", " ", label).strip(" |()[]-.,")
    return label[:420].rstrip() + ("…" if len(label) > 420 else "")


def _canonical_status(value: str) -> str:
    text = (value or "").casefold()
    if re.search(r"\b(?:contradicted|excluded|rejected|impossible)\b", text):
        return "contradicted"
    if "disputed" in text:
        return "disputed"
    if re.search(r"\b(?:proved|proven|confirmed|documented)\b", text):
        return "proved"
    if "strong" in text:
        return "strongly_supported"
    if "high" in text:
        return "strongly_supported"
    if "probable" in text:
        return "probable"
    if re.search(r"\b(?:possible|plausible|working|open|low|moderate)\b", text):
        return "possible"
    return "unknown"


def _source_quality(citation: str, provenance: str = "") -> str:
    text = f"{citation} {provenance}".casefold()
    if "tree" in text or "profile provenance" in text:
        return "tree_only"
    if re.search(
        r"\b(?:original|manuscript|register image|will image|household images?|civil (?:marriage|birth|death|registration)|"
        r"marriage certificate|birth certificate|death certificate|census return|parish register)\b",
        text,
    ) or re.search(r"(?:census\.nationalarchives\.ie|civilrecords\.irishgenealogy\.ie)", text):
        return "original"
    if re.search(r"\b(?:index|transcript(?:ion)?s?|abstract|calendar|database|familysearch)\b", text):
        return "derivative"
    if re.search(r"\b(?:descendant account|published history|secondary)\b", text):
        return "secondary"
    return "unknown"


def _independence_group(url: str, title: str) -> str:
    if url:
        parsed = urlsplit(url)
        key = urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), parsed.path, "", ""))
    else:
        key = re.sub(r"\W+", "-", title.casefold()).strip("-")
    return _stable_id("SRC", key)


def _vital(value: str, place: str, note: str = "") -> dict:
    if not value and not place:
        return {"date": None, "place": None, "status": None}
    text = f"{value} {note}".casefold()
    if "estimated" in text or value.startswith("c. "):
        status = "estimated"
    elif value.startswith(("before ", "after ")) or "/" in value:
        status = "uncertain"
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        status = "exact"
    elif value:
        status = "uncertain"
    else:
        status = None
    return {"date": value or None, "place": place or None, "status": status}


def _relationship_assessments() -> list[dict]:
    if not RELATIONSHIPS_PATH.exists():
        return []
    rows = []
    for line in RELATIONSHIPS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or re.match(r"^\|\s*[-:]", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] == "Person A":
            continue
        ids_a, ids_b = WT_ID.findall(cells[0]), WT_ID.findall(cells[2])
        if not ids_a or not ids_b:
            continue
        source_link = re.search(r"\[([^]]+)]\((https?://[^)]+)\)", cells[4])
        rows.append({
            "person_a": ids_a[0], "person_b": ids_b[0],
            "relationship": _clean_markdown(cells[1]),
            "status_label": _clean_markdown(cells[3]),
            "status": _canonical_status(cells[3]),
            "basis": _clean_markdown(cells[4]),
            "source_title": _clean_markdown(source_link.group(1)) if source_link else None,
            "source_url": source_link.group(2) if source_link else None,
            "next_target": _clean_markdown(cells[5]),
            "provenance": "surname-research/indexes/relationship-hypotheses.md",
        })
    return rows


def _research_plans(public_ids: set[str]) -> dict[str, dict]:
    plans = {}
    for path in RESEARCH_DIR.glob("*/research_plan.json"):
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        profile_id = plan.get("case_id") or path.parent.name
        if profile_id in public_ids:
            plan["_provenance"] = str(path.relative_to(path.parents[2]))
            plans[profile_id] = plan
    return plans


def _assessment_roles(assessment: dict) -> tuple[str | None, str | None]:
    relation = assessment["relationship"].casefold()
    if re.search(r"\b(?:son|daughter|child) of\b", relation):
        return "parent", "child"
    if "father of" in relation:
        return "child", "father"
    if "mother of" in relation:
        return "child", "mother"
    if re.search(r"\b(?:brother|sister|sibling) of\b", relation):
        return "sibling", "sibling"
    if re.search(r"\b(?:husband|wife|spouse) of\b", relation):
        return "spouse", "spouse"
    return None, None


def _best_source(subject_ids: list[str], basis: str, people_by_id: dict[str, dict]) -> dict:
    sources = []
    terms = set(re.findall(r"\b(?:marriage|baptism|census|will|probate|lease|valuation|death|birth|\d{4})\b", basis.casefold()))
    for subject_id in subject_ids:
        person = people_by_id.get(subject_id, {})
        for capture in person.get("wikitree_evidence", []):
            for source in capture.get("sources", []):
                text = source.get("citation", "")
                url = (source.get("urls") or [""])[0]
                title = _citation_label(text, url)
                score = sum(term in title.casefold() for term in terms)
                if "original" in basis.casefold() and re.search(r"civil|image|original", title, re.I):
                    score += 2
                sources.append((score, title, url))
    if not sources:
        return {}
    score, title, url = max(sources, key=lambda item: (item[0], bool(item[2]), len(item[1])))
    if score <= 0:
        return {}
    return {"title": title, "repository": None, "reference": None, "url": url or None}


def _occupation_terms(person: dict) -> list[str]:
    text = " ".join(f"{row.get('association', '')} {row.get('note', '')}" for row in person.get("records", []))
    for capture in person.get("wikitree_evidence", []):
        for passage in capture.get("record_passages", []):
            for match in re.finditer(
                r"\b(?:was|worked as|employed as|recorded as|described as)\s+(?:an?\s+)?([A-Za-z -]{2,50})",
                passage, re.I,
            ):
                text += " " + match.group(1)
    return [occupation for occupation in OCCUPATIONS if re.search(rf"\b{re.escape(occupation)}s?\b", text, re.I)]


def _profile_assessment_flags(person: dict) -> dict[str, bool]:
    """Expose explicit profile cautions to automated relationship scoring.

    These deliberately narrow patterns identify profiles whose own current
    research narrative says that its displayed birth or attached family is
    not established.  They are cautions, not a general NLP proof engine.
    """
    text = " ".join(
        str(capture.get("biography_text") or "")
        for capture in person.get("wikitree_evidence", [])
    )
    text = re.sub(r"\s+", " ", text).casefold()
    structural_placeholder = bool(
        re.search(
            r"\b(?:research|structural) placeholder\b|"
            r"\bdoes not represent (?:an? )?(?:identified|documented) (?:man|woman|person)\b|"
            r"\bdoes not represent (?:an? )?(?:man|woman|person) identified in any surviving record\b",
            text,
        )
    )
    family_links_disclaimed = bool(
        re.search(
            r"\b(?:parentage|family)(?:.{0,90})\b(?:has|have) not been "
            r"(?:established|proved|identified)\b|"
            r"\bno documentary evidence(?:.{0,240})\blinks?\b(?:.{0,180})"
            r"\b(?:parents?|wife|spouse|children|family)\b|"
            r"\battached (?:parents?|family|spouse|children)(?:.{0,100})\bunsupported\b",
            text,
        )
    )
    birth_details_disclaimed = bool(
        re.search(
            r"\bbirth(?: date|place|, parentage|, family)*(?:.{0,100})"
            r"\b(?:has|have) not been (?:established|identified|proved)\b|"
            r"\b(?:birth date|birthplace) (?:is|remains) (?:unknown|unidentified)\b",
            text,
        )
    )
    source_texts = []
    for capture in person.get("wikitree_evidence", []):
        for source in capture.get("sources", []):
            if isinstance(source, dict):
                source_texts.append(
                    " ".join(str(source.get(key) or "") for key in ("citation", "title", "url"))
                )
            elif source:
                source_texts.append(str(source))
    meaningful_sources = [text.casefold() for text in source_texts if text.strip()]
    profile_sources_tree_only = bool(meaningful_sources) and all(
        re.search(r"ancestry\.[^ ]+/family-tree/|\bonline family tree\b|\buser-submitted tree\b", text)
        for text in meaningful_sources
    )
    return {
        "_structural_placeholder": structural_placeholder,
        "_family_links_disclaimed": family_links_disclaimed,
        "_birth_details_disclaimed": birth_details_disclaimed,
        "_profile_sources_tree_only": profile_sources_tree_only,
    }


def _profile_research_leads(person: dict, person_id: str) -> list[dict]:
    """Extract only actionable, concrete leads from captured public profile notes."""
    action = re.compile(
        r"\b(?:search|inspect|obtain|locate|trace|check|verify|consult|order|commission|re-examine|"
        r"needs? (?:checking|verification)|should be (?:obtained|checked|inspected|searched|verified|located|traced))\b",
        re.I,
    )
    archive_ref = re.compile(r"\b(?:(?:MIC|VAL|FIN|T)[./][A-Z0-9./-]+|(?:NRS|TNA|PRONI|GUA)\s+[A-Z0-9][A-Z0-9/.-]+)\b", re.I)
    url_pattern = re.compile(r"https?://[^\s<>()\]]+")
    leads = []
    for capture in person.get("wikitree_evidence", []):
        for passage in capture.get("record_passages", []):
            segments = re.split(r"(?<=[.!?])\s+|\s+[•*#]\s+", passage)
            for segment in segments:
                match = action.search(segment)
                if not match or re.search(r"\b(?:do not|should not|must not)\b", segment[max(0, match.start() - 30):match.end()], re.I):
                    continue
                if len(segment) > 700:
                    segment = segment[max(0, match.start() - 220):match.end() + 360]
                reference_match = archive_ref.search(segment)
                url_match = url_pattern.search(segment)
                record_type = _record_type(segment)
                years = [int(value) for value in re.findall(r"\b(1\d{3}|20\d{2})\b", segment)]
                if not reference_match and not url_match and (record_type == "research assessment" or not years):
                    continue
                reference = reference_match.group() if reference_match else None
                url = url_match.group().rstrip(".,;:") if url_match else None
                repository = None
                if reference and re.search(r"\bPRONI\b|^(?:MIC|VAL|FIN|T)[./]", reference, re.I):
                    repository = "PRONI"
                elif reference:
                    repository = reference.split()[0].upper()
                locations = _unique(
                    [location for location in person.get("recorded_in", []) if location.casefold() in segment.casefold()]
                    + re.findall(r"\bCounty [A-Z][A-Za-z]+\b", segment)
                )
                question = re.sub(r"\s+", " ", segment).strip(" #-*")
                lead_id = _stable_id("L", "profile-note", person_id, reference or url or question)
                leads.append({
                    "id": lead_id, "priority": 3, "status": "unsearched", "question": question,
                    "repository": repository, "collection": None, "reference": reference,
                    "record_type": record_type, "date_from": min(years) if years else None,
                    "date_to": max(years) if years else None, "locations": locations,
                    "people": [person_id], "name_variants": [],
                    "reason": "Concrete research action extracted from the public WikiTree profile notes.",
                    "would_support": None, "would_refute_or_complicate": None, "url": url,
                    "provenance": "wikitree_research_note_extraction",
                })
    return list({item["id"]: item for item in leads}.values())[:10]


def _relation_name(person_id: str, people_by_id: dict[str, dict]) -> str:
    return people_by_id.get(person_id, {}).get("name") or person_id


def _tree_relations(person: dict, people_by_id: dict[str, dict], public_ids: set[str]) -> list[dict]:
    relations = []
    groups = (
        ("father", "father", "wikitree_parent_field"),
        ("mother", "mother", "wikitree_parent_field"),
        ("spouses", "spouse", "wikitree_spouse_field"),
        ("children", "child", "reconstructed_parent_reference"),
    )
    for field, role, source in groups:
        for relation in person.get(field, []):
            relation_id = relation.get("id", "")
            if relation.get("withheld"):
                relations.append({"id": None, "name": "Living person (details withheld)", "relationship": role,
                                  "status": "unknown", "basis": "tree", "evidence_ids": [],
                                  "tree_relationship": True, "relationship_source": "privacy_redacted"})
                continue
            if not relation_id:
                continue
            related = people_by_id.get(relation_id, {})
            actual_role = role
            if role == "child":
                gender = related.get("gender", "")
                actual_role = "son" if gender == "Male" else "daughter" if gender == "Female" else "child"
            local = relation_id in public_ids
            tree_statuses = {
                "5": ("non_biological", "WikiTree: non-biological parent"),
                "10": ("uncertain", "WikiTree: uncertain parent"),
                "20": ("confident", "WikiTree: confident parent"),
                "30": ("dna_confirmed", "WikiTree: confirmed with DNA"),
            }
            tree_status, tree_status_label = tree_statuses.get(
                str(relation.get("data_status") or ""), ("unmarked", "WikiTree: relationship status unmarked")
            )
            relations.append({
                "id": relation_id, "name": relation.get("name") or _relation_name(relation_id, people_by_id),
                "relationship": actual_role, "status": "unknown", "status_label": "WikiTree tree relationship",
                "basis": "tree", "evidence_ids": [], "tree_relationship": True,
                "relationship_source": source, "tree_status": tree_status,
                "tree_status_label": tree_status_label,
                "url": f"/people/{related['catalogue_id']}.html" if local else None,
                "json_url": f"/people/{related['catalogue_id']}.json" if local else None,
                "network_url": f"/people/{related['catalogue_id']}.network.json" if local else None,
                "wikitree_url": WIKITREE_URL + relation_id,
            })
    # WikiTree relationship captures provide siblings without an expensive tree walk.
    for capture in person.get("wikitree_evidence", []):
        for sibling in capture.get("relations", {}).get("siblings", []):
            relation_id = sibling.get("id", "")
            if not relation_id or relation_id not in public_ids:
                continue
            related = people_by_id[relation_id]
            relations.append({
                "id": relation_id, "name": sibling.get("name") or related["name"], "relationship": "sibling",
                "status": "unknown", "status_label": "WikiTree relationship snapshot", "basis": "tree",
                "evidence_ids": [], "tree_relationship": True, "relationship_source": "wikitree_relation_snapshot",
                "url": f"/people/{related['catalogue_id']}.html", "json_url": f"/people/{related['catalogue_id']}.json",
                "network_url": f"/people/{related['catalogue_id']}.network.json", "wikitree_url": WIKITREE_URL + relation_id,
            })
    return list({(item.get("id"), item["relationship"]): item for item in relations}.values())


def _profile_source_evidence(person: dict) -> list[dict]:
    evidence = []
    for capture in person.get("wikitree_evidence", []):
        for item in capture.get("sources", []):
            citation = item.get("citation", "").strip()
            url = (item.get("urls") or [None])[0]
            title = _citation_label(citation, url)
            evidence_id = _stable_id("E", "citation", capture.get("profile_id"), url or citation)
            evidence.append({
                "id": evidence_id, "claim_ids": [], "record_type": "extracted citation", "date": None,
                "place": None, "subjects": [capture.get("profile_id")],
                "assertion": "Citation extracted from the WikiTree profile; its underlying record has not been interpreted here.",
                "evidence_status": "unassessed", "source_quality": _source_quality(title),
                "independence_group": _independence_group(url or "", title),
                "source": {"title": title, "repository": None, "reference": None, "url": url},
                "provenance": "wikitree_profile_citation",
            })
    return list({item["id"]: item for item in evidence}.values())


def _record_type(text: str) -> str:
    for value in ("civil marriage", "marriage", "baptism", "census", "will", "probate", "lease", "valuation", "birth", "death"):
        if value in text.casefold():
            return value
    return "research assessment"


def _assessment_claim(assessment: dict, people_by_id: dict[str, dict]) -> tuple[dict, dict]:
    a, b = assessment["person_a"], assessment["person_b"]
    claim_id = _stable_id("C", "relationship", a, assessment["relationship"], b)
    source = (
        {"title": assessment["source_title"], "repository": None, "reference": None,
         "url": assessment["source_url"]}
        if assessment.get("source_url") else
        _best_source([a, b], assessment["basis"], people_by_id)
    )
    evidence_id = _stable_id("E", "relationship-assessment", a, assessment["relationship"], b, assessment["basis"])
    evidence = {
        "id": evidence_id, "claim_ids": [claim_id], "record_type": _record_type(assessment["basis"]),
        "date": str(_year(assessment["basis"]) or "") or None, "place": None, "subjects": [a, b],
        "assertion": assessment["basis"],
        "evidence_status": "direct" if assessment["status"] == "proved" else "circumstantial",
        "source_quality": _source_quality(
            source.get("title", ""), f"{assessment['basis']} {assessment['status_label']}"
        ) if source else "unknown",
        "independence_group": _independence_group(source.get("url") or "", source.get("title") or assessment["basis"]),
        "source": source or {"title": "Controlled relationship assessment", "repository": None,
                             "reference": assessment["provenance"], "url": None},
        "provenance": assessment["provenance"],
    }
    claim = {
        "id": claim_id, "type": "relationship", "subject_ids": [a, b],
        "claim": f"{_relation_name(a, people_by_id)} was {assessment['relationship']} {_relation_name(b, people_by_id)}",
        "status": assessment["status"], "status_label": assessment["status_label"],
        "evidence_ids": [evidence_id], "notes": assessment["basis"], "provenance": assessment["provenance"],
    }
    return claim, evidence


def _person_id(person: dict) -> str:
    return next(iter(person.get("profile_ids", [])), None) or person["catalogue_id"]


def build_machine_models(public_people: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    """Return dossiers keyed by catalogue slug and a compact global index."""
    people_by_id = {profile_id: person for person in public_people for profile_id in person.get("profile_ids", [])}
    public_ids = set(people_by_id)
    assessments = [item for item in _relationship_assessments() if item["person_a"] in public_ids and item["person_b"] in public_ids]
    plans = _research_plans(public_ids)
    assessments_by_person = defaultdict(list)
    for assessment in assessments:
        assessments_by_person[assessment["person_a"]].append(assessment)
        assessments_by_person[assessment["person_b"]].append(assessment)

    dossiers = {}
    compact_index = []
    for person in public_people:
        person_id = _person_id(person)
        slug = person["catalogue_id"]
        claims, evidence = [], _profile_source_evidence(person)
        relations = _tree_relations(person, people_by_id, public_ids)
        relation_lookup = {(item.get("id"), item["relationship"]): item for item in relations}

        # Every mapped event remains an occurrence claim with honest provenance.
        for record in person.get("records", []):
            record_key = (
                person_id, record.get("year"), record.get("record_location"), record.get("association"),
                record.get("note"), record.get("source_url"),
            )
            claim_id = _stable_id("C", "mapped-record", *record_key)
            evidence_id = _stable_id("E", "mapped-record", *record_key)
            claims.append({
                "id": claim_id, "type": "recorded_occurrence", "subject_ids": [person_id],
                "claim": f"{person['name']} was recorded in {record.get('record_location') or 'an unspecified place'} ({record.get('year') or 'undated'}).",
                "status": _canonical_status(record.get("evidence", "")), "status_label": record.get("evidence") or "Unclassified",
                "evidence_ids": [evidence_id], "notes": record.get("association") or record.get("note"),
                "provenance": "mapped_record",
            })
            evidence.append({
                "id": evidence_id, "claim_ids": [claim_id], "record_type": record.get("association") or "mapped record",
                "date": record.get("year") or None, "place": record.get("record_location") or None,
                "subjects": [person_id], "assertion": record.get("note") or record.get("association") or "Mapped occurrence",
                "evidence_status": "direct" if _canonical_status(record.get("evidence", "")) == "proved" else "unassessed",
                "source_quality": _source_quality(
                    record.get("source_title", ""),
                    f'{record.get("source_type", "")} {record.get("source_status", "")}',
                ),
                "independence_group": _independence_group(record.get("source_url", ""), record.get("source_title", "")),
                "source": {"title": record.get("source_title"), "repository": None, "reference": record["record_id"],
                           "url": record.get("source_url")}, "provenance": record.get("source_type") or "mapped_record",
            })

        # Controlled assessments can upgrade a tree edge; they never arise from the tree itself.
        for assessment in assessments_by_person.get(person_id, []):
            claim, assessment_evidence = _assessment_claim(assessment, people_by_id)
            claims.append(claim)
            evidence.append(assessment_evidence)
            role_a, role_b = _assessment_roles(assessment)
            role = role_a if person_id == assessment["person_a"] else role_b
            other_id = assessment["person_b"] if person_id == assessment["person_a"] else assessment["person_a"]
            if not role:
                continue
            if role == "child":
                gender = people_by_id.get(other_id, {}).get("gender")
                role = "son" if gender == "Male" else "daughter" if gender == "Female" else "child"
            if role == "parent":
                gender = people_by_id.get(other_id, {}).get("gender")
                role = "father" if gender == "Male" else "mother" if gender == "Female" else "parent"
            edge = next((item for (rid, rrole), item in relation_lookup.items()
                         if rid == other_id and (rrole == role or {rrole, role} <= {"child", "son", "daughter"}
                                                   or {rrole, role} <= {"parent", "father", "mother"})), None)
            other = people_by_id[other_id]
            if edge is None:
                edge = {
                    "id": other_id, "name": other["name"], "relationship": role,
                    "tree_relationship": False, "relationship_source": "research_assessment",
                    "url": f"/people/{other['catalogue_id']}.html", "json_url": f"/people/{other['catalogue_id']}.json",
                    "network_url": f"/people/{other['catalogue_id']}.network.json", "wikitree_url": WIKITREE_URL + other_id,
                }
                relations.append(edge)
            edge.update({"status": assessment["status"], "status_label": assessment["status_label"],
                         "basis": "documentary" if assessment["status"] == "proved" else "research_assessment",
                         "evidence_ids": [assessment_evidence["id"]], "claim_id": claim["id"]})

        open_questions, research_leads = [], []
        plan = plans.get(person_id)
        if plan:
            for finding in plan.get("findings", []):
                claim_id = _stable_id("C", "research-finding", person_id, finding.get("claim"))
                evidence_ids = []
                for source_value in finding.get("sources", []):
                    evidence_id = _stable_id("E", "research-finding", person_id, finding.get("claim"), source_value)
                    evidence_ids.append(evidence_id)
                    evidence.append({
                        "id": evidence_id, "claim_ids": [claim_id], "record_type": _record_type(finding.get("claim", "")),
                        "date": None, "place": None, "subjects": _unique([person_id, *WT_ID.findall(finding.get("claim", ""))]),
                        "assertion": finding.get("reasoning"), "evidence_status": "circumstantial",
                        "source_quality": _source_quality(source_value),
                        "independence_group": _independence_group(source_value if source_value.startswith("http") else "", source_value),
                        "source": {"title": source_value, "repository": None, "reference": source_value if not source_value.startswith("http") else None,
                                   "url": source_value if source_value.startswith("http") else None},
                        "provenance": plan["_provenance"],
                    })
                claims.append({
                    "id": claim_id, "type": "research_finding", "subject_ids": _unique([person_id, *WT_ID.findall(finding.get("claim", ""))]),
                    "claim": finding.get("claim"), "status": _canonical_status(finding.get("confidence", "")),
                    "status_label": finding.get("confidence"), "evidence_ids": evidence_ids,
                    "notes": finding.get("reasoning"), "provenance": plan["_provenance"],
                })
            for question in plan.get("questions", []):
                if question.get("status") != "open":
                    continue
                question_id = _stable_id("Q", person_id, question.get("id"), question.get("question"))
                related_claims = [
                    claim["id"] for claim in claims
                    if person_id in claim.get("subject_ids", []) and claim["type"] == "relationship"
                    and (question.get("id") != "parents" or re.search(r"\b(?:son of|daughter of|child of|father|mother|parent)\b", claim.get("claim", ""), re.I))
                ]
                open_questions.append({
                    "id": question_id, "question": question.get("question"), "status": "unresolved",
                    "current_conclusion": question.get("answer") or None, "claim_ids": related_claims,
                    "evidence_for": _unique(eid for claim in claims if claim["id"] in related_claims for eid in claim.get("evidence_ids", [])),
                    "evidence_against": [],
                    "missing_bridge": (
                        "A contemporary record explicitly identifying the parent or parents."
                        if question.get("id") == "parents" else question.get("answer") or None
                    ), "lead_ids": [],
                    "provenance": plan["_provenance"],
                })
            for target in plan.get("targets", []):
                if target.get("status") in {"complete", "completed"} or target.get("kind") != "archive":
                    continue
                lead_id = _stable_id("L", person_id, target.get("id"), target.get("note"))
                target_text = f"{target.get('note', '')} {target.get('reason', '')}"
                year_values = [int(value) for value in re.findall(r"\b(1\d{3}|20\d{2})\b", target_text)]
                circa_match = re.search(r"\bcirca\s+(1\d{3}|20\d{2})\b", target_text, re.I)
                if circa_match:
                    target_year = int(circa_match.group(1))
                    date_from, date_to = target_year - 2, target_year + 2
                else:
                    date_from, date_to = (min(year_values), max(year_values)) if year_values else (None, None)
                repository = "PRONI" if re.search(r"\bPRONI\b|^(?:MIC|VAL|T)/", target.get("id", ""), re.I) else None
                research_leads.append({
                    "id": lead_id, "priority": target.get("generation", 0) + 1, "status": "unsearched",
                    "question": target.get("reason") or target.get("note"), "repository": repository,
                    "collection": target.get("note") or None, "reference": target.get("id") or None,
                    "record_type": _record_type(target.get("note", "")),
                    "date_from": date_from, "date_to": date_to,
                    "locations": _unique(re.findall(r"\b(?:Lisnagaver|Portglenone|Moneyleck|County [A-Za-z]+)\b", target.get("note", ""))),
                    "people": [person_id], "name_variants": [], "reason": target.get("reason") or None,
                    "would_support": target.get("note") or None, "would_refute_or_complicate": None,
                    "url": None, "provenance": plan["_provenance"],
                })
            for question in open_questions:
                question["lead_ids"] = [lead["id"] for lead in research_leads]

        existing_lead_keys = {
            (lead.get("reference"), lead.get("url"), lead.get("question")) for lead in research_leads
        }
        existing_references = {
            re.sub(r"[^a-z0-9]", "", lead["reference"].casefold())
            for lead in research_leads if lead.get("reference")
        }
        excluded_profile_references = {
            re.sub(r"[^a-z0-9]", "", str(reference).casefold())
            for reference in (plan or {}).get("excluded_profile_lead_references", [])
        }
        for lead in _profile_research_leads(person, person_id):
            key = (lead.get("reference"), lead.get("url"), lead.get("question"))
            reference_key = re.sub(r"[^a-z0-9]", "", (lead.get("reference") or "").casefold())
            if reference_key and reference_key in excluded_profile_references:
                continue
            if key not in existing_lead_keys and (not reference_key or reference_key not in existing_references):
                research_leads.append(lead)
                existing_lead_keys.add(key)
                if reference_key:
                    existing_references.add(reference_key)
        for question in open_questions:
            question["lead_ids"] = [lead["id"] for lead in research_leads]

        # Cross-link tree relations to claims, but retain unknown evidence status unless assessed.
        for relation in relations:
            if relation.get("claim_id") or not relation.get("id"):
                continue
            claim_id = _stable_id("C", "tree-relationship", person_id, relation["relationship"], relation["id"])
            claims.append({
                "id": claim_id, "type": "tree_relationship", "subject_ids": [person_id, relation["id"]],
                "claim": f"WikiTree currently connects {person['name']} and {relation['name']} as {relation['relationship']}.",
                "status": "unknown", "status_label": relation.get("status_label"), "evidence_ids": [],
                "notes": "Tree structure only; no documentary conclusion is implied.", "provenance": relation["relationship_source"],
            })
            relation["claim_id"] = claim_id

        evidence = list({item["id"]: item for item in evidence}.values())
        claims = list({item["id"]: item for item in claims}.values())
        source_summary = []
        for item in evidence:
            source = item.get("source") or {}
            if not source.get("title"):
                continue
            source_summary.append({"title": source.get("title"), "url": source.get("url"),
                                   "source_quality": item.get("source_quality"),
                                   "independence_group": item.get("independence_group"),
                                   "provenance": item.get("provenance")})
        source_summary = list({(item["title"], item.get("url")): item for item in source_summary}.values())
        aliases = _unique(
            value.strip() for info in person.get("profile_information", [])
            for value in re.split(r"[,;]", info.get("other_surnames", "")) if value.strip()
        )
        locations = _unique([person.get("birth_location"), person.get("death_location"), *person.get("recorded_in", [])])
        warnings = list(person.get("relationship_warnings", []))
        if len(evidence) > 100:
            warnings.append("This profile has more than 100 extracted evidence/source objects; use source_summary for quick review.")
        dossier = {
            "schema_version": SCHEMA_VERSION, "id": person_id,
            "alternate_ids": [profile_id for profile_id in person.get("profile_ids", []) if profile_id != person_id],
            "catalogue_id": slug, "name": person["name"],
            "canonical_url": f"{SITE_URL}/people/{slug}.html", "json_url": f"{SITE_URL}/people/{slug}.json",
            "network_url": f"{SITE_URL}/people/{slug}.network.json",
            "wikitree_url": WIKITREE_URL + person_id if WT_ID.fullmatch(person_id) else None,
            "vitals": {"birth": _vital(person.get("birth", ""), person.get("birth_location", ""), person.get("birth_note", "")),
                       "death": _vital(person.get("death", ""), person.get("death_location", ""), person.get("death_note", ""))},
            "identity": {"gender": person.get("gender") or None, "occupations": _occupation_terms(person),
                         "locations": locations, "aliases": aliases, "research_clusters": person.get("clusters", [])},
            "relationships": {
                "parents": [item for item in relations if item["relationship"] in {"father", "mother", "parent"}],
                "spouses": [item for item in relations if item["relationship"] == "spouse"],
                "children": [item for item in relations if item["relationship"] in {"child", "son", "daughter"}],
                "siblings": [item for item in relations if item["relationship"] == "sibling"],
            },
            "claims": claims, "evidence": evidence, "open_questions": open_questions,
            "research_leads": research_leads, "source_summary": source_summary, "warnings": warnings,
            "provenance": {"tree": "WikiTree One-Tree export", "mapped_records": "Glasgow Surname Project map dataset",
                           "profile_capture": "Public WikiTree profile evidence capture",
                           "relationship_assessments": "Controlled local relationship hypothesis register"},
        }
        dossiers[slug] = dossier
        father_ids = [item.get("id") for item in dossier["relationships"]["parents"] if item["relationship"] == "father" and item.get("id")]
        mother_ids = [item.get("id") for item in dossier["relationships"]["parents"] if item["relationship"] == "mother" and item.get("id")]
        dated_records = []
        for record in person.get("records", []):
            record_year = record.get("filter_year")
            if not isinstance(record_year, (int, float)) or not record.get("record_location"):
                continue
            dated_records.append({
                "year": round(record_year),
                "location": record.get("record_location"),
                "association": record.get("association") or record.get("note") or "mapped occurrence",
                "status": _canonical_status(record.get("evidence", "")),
                "latitude": record.get("latitude"), "longitude": record.get("longitude"),
                "precision": record.get("record_precision"),
                "source_quality": _source_quality(
                    record.get("source_title", ""),
                    f'{record.get("source_type", "")} {record.get("source_status", "")}',
                ),
            })
        compact_index.append({
            "schema_version": SCHEMA_VERSION, "id": person_id,
            "alternate_ids": dossier["alternate_ids"], "catalogue_id": slug, "name": person["name"],
            "gender": person.get("gender") or None,
            "birth_surnames": person.get("last_names_at_birth", []),
            "research_clusters": person.get("clusters", []),
            "birth_year": _year(person.get("birth", "")), "death_year": _year(person.get("death", "")),
            "_birth_expression": person.get("birth", ""),
            "birth_status": dossier["vitals"]["birth"].get("status"),
            "death_status": dossier["vitals"]["death"].get("status"),
            "birth_place": person.get("birth_location") or None, "death_place": person.get("death_location") or None,
            "locations": locations, "father_id": father_ids[0] if father_ids else None,
            "mother_id": mother_ids[0] if mother_ids else None,
            "parent_ids": _unique(item.get("id") for item in dossier["relationships"]["parents"]),
            "parent_names": _unique(item.get("name") for item in dossier["relationships"]["parents"]),
            "_parent_links": [{
                key: item.get(key) for key in (
                    "id", "name", "relationship", "status", "status_label", "tree_status", "tree_status_label"
                )
            } for item in dossier["relationships"]["parents"] if item.get("id") or item.get("name")],
            "spouse_ids": _unique(item.get("id") for item in dossier["relationships"]["spouses"]),
            "spouse_names": _unique(item.get("name") for item in dossier["relationships"]["spouses"]),
            "_spouse_links": [{
                key: item.get(key) for key in ("id", "name", "status", "status_label", "tree_status", "tree_status_label")
            } for item in dossier["relationships"]["spouses"] if item.get("id") or item.get("name")],
            "child_ids": _unique(item.get("id") for item in dossier["relationships"]["children"]),
            # Keep names parallel with child_ids; repeated given names can be genealogically significant.
            "child_names": [item.get("name") for item in dossier["relationships"]["children"] if item.get("id")],
            "_child_links": [{
                key: item.get(key) for key in ("id", "name", "status", "status_label", "tree_status", "tree_status_label")
            } for item in dossier["relationships"]["children"] if item.get("id") or item.get("name")],
            # Internal build field removed before the compact public index is written.
            "_sibling_ids": [item.get("id") for item in dossier["relationships"]["siblings"] if item.get("id")],
            "_sibling_links": [{
                key: item.get(key) for key in (
                    "id", "name", "status", "status_label", "tree_status", "tree_status_label",
                    "tree_relationship", "relationship_source",
                )
            } for item in dossier["relationships"]["siblings"] if item.get("id") or item.get("name")],
            "_dated_records": dated_records,
            "sibling_names": [item.get("name") for item in dossier["relationships"]["siblings"] if item.get("id")],
            "occupations": dossier["identity"]["occupations"],
            **_profile_assessment_flags(person),
            "html_url": f"/people/{slug}.html", "json_url": f"/people/{slug}.json",
            "network_url": f"/people/{slug}.network.json",
        })
    return dossiers, compact_index


def build_network(dossier: dict, dossiers_by_id: dict[str, dict]) -> dict:
    relationships = []
    evidence_by_id = {item["id"]: item for item in dossier["evidence"]}
    for group in ("parents", "spouses", "children", "siblings"):
        for relation in dossier["relationships"][group]:
            evidence = next((evidence_by_id[eid] for eid in relation.get("evidence_ids", []) if eid in evidence_by_id), None)
            item = {key: relation.get(key) for key in (
                "id", "name", "relationship", "status", "status_label", "basis", "tree_relationship",
                "tree_status", "tree_status_label", "relationship_source", "claim_id", "url", "json_url", "network_url")
            }
            if evidence:
                source = evidence.get("source") or {}
                item["best_evidence"] = {
                    "id": evidence["id"], "record_type": evidence.get("record_type"), "date": evidence.get("date"),
                    "assertion": evidence.get("assertion"), "source_url": source.get("url"),
                    "source_title": source.get("title"), "source_quality": evidence.get("source_quality"),
                    "independence_group": evidence.get("independence_group"),
                }
            relationships.append(item)
    return {
        "schema_version": SCHEMA_VERSION,
        "person": {"id": dossier["id"], "name": dossier["name"], "html_url": dossier["canonical_url"], "json_url": dossier["json_url"]},
        "depth": 1, "relationships": relationships,
    }


def resolver_candidates(index: list[dict], name: str, birth: int | None = None, location: str = "", spouse: str = "") -> list[dict]:
    """Explainable deterministic resolver used by generation and acceptance tests."""
    normal = _normal_match_text
    query_name, query_location, query_spouse = normal(name), normal(location), normal(spouse)
    candidates = []
    for person in index:
        candidate_name = normal(person["name"])
        if query_name not in candidate_name and candidate_name not in query_name:
            continue
        score, reasons, conflicts = (0.55 if candidate_name == query_name else 0.35), ["name match"], []
        if birth is not None:
            if person.get("birth_year") is None:
                conflicts.append("birth year unavailable")
            else:
                delta = abs(person["birth_year"] - birth)
                if delta == 0:
                    score += .25; reasons.append("birth year match")
                elif delta <= 5:
                    score += .12; reasons.append(f"birth year within {delta} years")
                else:
                    score -= min(.25, delta / 100); conflicts.append(f"birth year differs by {delta} years")
        if query_location:
            haystack = normal(" ".join(person.get("locations", [])))
            if query_location in haystack:
                score += .15; reasons.append("location match")
            else:
                score -= .08; conflicts.append("location differs")
        if query_spouse:
            haystack = normal(" ".join(person.get("spouse_names", [])))
            if query_spouse in haystack:
                score += .15; reasons.append("spouse match")
            else:
                score -= .05; conflicts.append("spouse not matched")
        candidates.append({**person, "score": round(max(0, min(1, score)), 2),
                           "match_reasons": reasons, "conflicts": conflicts})
    return sorted(candidates, key=lambda item: (-item["score"], item.get("birth_year") or 9999, item["id"]))


def write_machine_outputs(catalogue_dir: Path, data_dir: Path, dossiers: dict[str, dict], index: list[dict]) -> dict:
    dossiers_by_id = {dossier["id"]: dossier for dossier in dossiers.values()}
    for slug, dossier in dossiers.items():
        (catalogue_dir / f"{slug}.json").write_text(json.dumps(dossier, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        network = build_network(dossier, dossiers_by_id)
        (catalogue_dir / f"{slug}.network.json").write_text(json.dumps(network, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (data_dir / "people-index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    resolve_dir = data_dir / "resolve"
    # The parent generated-data directory is cleared at build start. Tolerate a
    # resolver directory recreated meanwhile by another catalogue process.
    resolve_dir.mkdir(exist_ok=True)
    by_name = defaultdict(list)
    name_aliases = defaultdict(set)
    for person in index:
        canonical_slug = re.sub(r"[^a-z0-9]+", "-", _normal_match_text(person["name"])).strip("-") or "other"
        original_slug = re.sub(r"[^a-z0-9]+", "-", person["name"].casefold()).strip("-") or "other"
        by_name[canonical_slug].append(person)
        name_aliases[canonical_slug].add(original_slug)
    for name_slug, members in by_name.items():
        query_name = members[0]["name"]
        payload = {"schema_version": SCHEMA_VERSION, "query": {"name": query_name},
                   "candidate_count": len(members), "candidates": resolver_candidates(index, query_name),
                   "scoring": "Exact/contained normalised name; clients may add birth, location and spouse using people-index fields."}
        for alias_slug in name_aliases[name_slug] | {name_slug}:
            (resolve_dir / f"{alias_slug}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"dossiers": len(dossiers), "resolver_names": len(by_name)}


def person_json_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{SITE_URL}/data/schema/person.schema.json",
        "title": "Glasgow Surname Project person dossier", "type": "object",
        "required": ["schema_version", "id", "name", "canonical_url", "vitals", "identity", "relationships", "claims", "evidence"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION}, "id": {"type": "string"}, "name": {"type": "string"},
            "canonical_url": {"type": "string", "format": "uri"},
            "relationships": {"type": "object", "required": ["parents", "spouses", "children", "siblings"]},
            "claims": {"type": "array", "items": {"type": "object", "required": ["id", "type", "status", "evidence_ids"]}},
            "evidence": {"type": "array", "items": {"type": "object", "required": ["id", "claim_ids", "source_quality", "provenance"]}},
            "open_questions": {"type": "array"}, "research_leads": {"type": "array"},
            "research_findings": {"type": "array"}, "similar_people": {"type": "array"},
            "potential_parentage": {"type": "object"},
        },
    }
