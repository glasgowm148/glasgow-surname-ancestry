"""Materialize reviewed historical research cases omitted from mapped people.

The inclusion manifest supplies canonical destinations, never inferred identity
matches. Public profile metadata and the normal privacy filter remain required.
"""
import argparse
import json
import re
from copy import deepcopy
from html import escape

from bs4 import BeautifulSoup

try:
    import build_family_map as family
    import build_research_catalog as catalogue
    import evidence_labels
    from site_identity import page_title
    from catalogue_machine_data import build_machine_models, build_network
    from sync_catalogue_research import ROOT, WEB, read_json, write_json, refresh_person
    from queue_profile_amendments import reviewed_amendments
    from public_privacy import likely_living
except ModuleNotFoundError:  # Package imports used by focused checks.
    from tools import build_family_map as family, build_research_catalog as catalogue, evidence_labels
    from tools.site_identity import page_title
    from tools.catalogue_machine_data import build_machine_models, build_network
    from tools.sync_catalogue_research import ROOT, WEB, read_json, write_json, refresh_person
    from tools.queue_profile_amendments import reviewed_amendments
    from tools.public_privacy import likely_living

MANIFEST = ROOT / "data/wikitree/research-catalogue-cases.json"


def retain_case_context(fresh, previous):
    """Refresh evidence without discarding an existing reviewed family account.

    A small inclusion build lacks the full mapped family context. Relationship
    assessments are applied afterwards by the normal dossier resolver.
    """
    result = deepcopy(previous)
    for field in ("evidence", "claims"):
        rows = {item["id"]: deepcopy(item) for item in previous.get(field, [])}
        rows.update({item["id"]: deepcopy(item) for item in fresh.get(field, [])})
        result[field] = list(rows.values())
    summaries = {(item.get("title"), item.get("url")): deepcopy(item)
                 for item in previous.get("source_summary", [])}
    summaries.update({(item.get("title"), item.get("url")): deepcopy(item)
                      for item in fresh.get("source_summary", [])})
    result["source_summary"] = list(summaries.values())
    return result


def retain_catalogue_context(fresh, previous):
    """Keep mapped roots, locations and family fields during a case refresh."""
    result = {**fresh, **deepcopy(previous)}
    for field in ("source_qualities", "claim_statuses"):
        result[field] = catalogue._unique([
            *previous.get(field, []), *fresh.get(field, []),
        ])
    return result



def reviewed_inclusion_cases(cases, amendments, evidence, metadata):
    """Add reviewed canonical profile IDs without overriding exclusions/aliases.

    A prepared amendment establishes review scope, not a public identity. Both
    the actual profile capture and normal family metadata must support inclusion.
    The source manifest remains untouched; this union is rebuilt each run.
    """
    included = deepcopy(cases)
    for ident in amendments:
        previous = cases.get(ident, {})
        if previous.get("status") in {"internal", "withheld"}:
            continue
        if previous.get("status") == "covered" and previous.get("profile_id") != ident:
            continue
        if not catalogue.WIKITREE_ID.fullmatch(ident):
            continue
        capture = evidence.get("profiles", {}).get(ident) or {}
        fields = capture.get("profile_fields") or {}
        try:
            is_public = int(capture.get("privacy") or fields.get("Privacy") or 0) >= 50
        except (TypeError, ValueError):
            is_public = False
        meta = metadata.get(ident) or {}
        if (not capture or not is_public or not meta.get("full_name")
                or likely_living(capture, meta)
                or (fields.get("Name") and fields["Name"] != ident)):
            continue
        if previous.get("status") == "include":
            continue
        included[ident] = {
            **previous, "status": "include", "profile_id": ident,
            "reason": "Reviewed complete profile amendment with a public historical capture and family metadata.",
            "review_manifest": "research/queue-review-2026-10-17/catalogue-integration.json",
        }
    return included


def page_shell(person, dossier, findings, links):
    # A fresh record account starts without captured relatives. Render the same
    # approved relationships that the subsequent machine-data resolver applies.
    try:
        from publish_resolved_dossiers import resolve
    except ModuleNotFoundError:
        from tools.publish_resolved_dossiers import resolve
    shared = ROOT / "research/relationship_assessments.json"
    registry = WEB / "assets/research/assessments.json"
    dossier = resolve(dossier,
                      read_json(registry).get("assessments", []) if registry.exists() else [],
                      read_json(shared) if shared.exists() else [])
    # Reuse only the current site's shared shell, removing all subject content.
    soup = BeautifulSoup((WEB / "people/glasgow-1521.html").read_text(), "html.parser")
    ident, slug, name = dossier["id"], person["catalogue_id"], person["name"]
    destination = catalogue.WIKITREE_URL + ident if person["profile_ids"] else person["records"][0]["source_url"]
    destination_label = "View on WikiTree" if person["profile_ids"] else "View the baptism source"
    soup.body["data-g-path"] = f"/people/{slug}.html"
    soup.body["data-r-person"] = ident
    soup.body["data-g-person"] = json.dumps({"id":ident, "name":name, "life":f"{person['birth']} – {person['death']}", "url":f"/people/{slug}.html", "tree":False})
    soup.title.string = page_title(name)
    description = soup.select_one('meta[name="description"]')
    if description is None:
        description = soup.new_tag("meta", attrs={"name": "description"})
        soup.head.append(description)
    description["content"] = "Sources, conclusions and unresolved questions for " + name + "."
    for node in soup.select('link[rel="canonical"], link[rel="alternate"]'):
        suffix = ".json" if node.get("type") == "application/json" else ".html"
        node["href"] = f"{catalogue.SITE_URL}/people/{slug}{suffix}"
    for node in soup.select('script[type="application/ld+json"]'):
        node.string = json.dumps({"@context":"https://schema.org", "@type":"Person", "name":name,
                                  "url":f"{catalogue.SITE_URL}/people/{slug}.html", "sameAs":destination})
    main = soup.select_one("main.v3-dossier"); main.clear()
    for crumb in soup.select(".g-breadcrumb"):
        for child in crumb.find_all(["span", "strong"]):
            if "William Glasgow" in child.get_text():
                child.string = name
    family_rows = []
    for label, key in (("Parents", "parents"), ("Spouses", "spouses"), ("Children", "children"), ("Siblings", "siblings")):
        relatives = dossier["relationships"].get(key, [])
        if not relatives:
            continue
        values = []
        for relative in relatives:
            rid = relative.get("id", "")
            if not rid:
                continue
            href = relative.get("url") or (f'/people/{links[rid]}.html' if rid in links else catalogue.WIKITREE_URL + rid)
            state = relative.get("status") or relative.get("tree_status") or "unmarked"
            shown = relative.get("tree_status_label") or relative.get("status_label")
            status = evidence_labels.normalise_status_label(state, shown) if shown else evidence_labels.label(state)
            rating = relative.get('probability') or {}
            if key == 'spouses' and rating.get('value') is not None:
                status += f" · {round(rating['value'] * 100)}%"
            values.append(f'<li><a href="{escape(href, quote=True)}">{escape(relative.get("name") or rid)}</a> · {escape(status)}</li>')
        if values:
            family_rows.append(f'<h3>{label}</h3><ul>{"".join(values)}</ul>')
    family_html = "".join(family_rows) or "<p>No family attachments are available in this public capture. See the case findings for documentary relationships and candidates.</p>"
    family_html += f'<p class="evidence-guide-link"><a href="{evidence_labels.GUIDE_URL}">{evidence_labels.GUIDE_LABEL}</a></p>'
    content = f'''<header class="v3-person-header"><span class="r-kicker">Person dossier · {ident}</span>
<div class="v3-title-line"><div><h1>{escape(name)}</h1><p>{escape(person['birth'] or 'Birth unrecorded')} – {escape(person['death'] or 'Death unrecorded')}</p>
<div class="profile-wikitree-actions"><span>{'WikiTree destination' if person['profile_ids'] else 'WikiTree identity unresolved'}</span><a href="{escape(destination, quote=True)}">{destination_label} <small>{ident} ↗</small></a></div></div></div></header>
<div class="v3-person-opening"><div id="person-summary"><section class="v3-person-understanding" id="overview"><span class="r-kicker">The research account</span>
<dl class="v3-vitals"><div><dt>Birth</dt><dd>{escape(person['birth'] or 'Not recorded')}<span>{escape(person['birth_location'] or 'Place not recorded')}</span></dd></div><div><dt>Death</dt><dd>{escape(person['death'] or 'Not recorded')}<span>{escape(person['death_location'] or 'Place not recorded')}</span></dd></div></dl>
<div class="v3-inline-links"><a href="#research">Read the full research →</a></div></section></div>
<section class="v3-person-family" id="family"><h2>The family</h2>{family_html}<p class="v3-family-note">Recorded attachments are distinguished from documentary proof in the research assessment.</p></section></div>
<section class="r-section" id="research"><span id="research-stack"></span><h2>The research behind the story</h2></section>
<section class="r-section" id="research-tools"><h2>Research tools and original material</h2><div class="r-actions"><a href="/people/{slug}.json">Structured person data</a><a href="{escape(destination, quote=True)}">{destination_label}</a></div></section>'''
    main.append(BeautifulSoup(content, "html.parser"))
    # Remove the template's subject-specific breadcrumb text outside the main.
    for node in soup.find_all(string=lambda text: text and "William Glasgow" in text):
        if node.find_parent("main") is None and node.find_parent("script") is None:
            node.replace_with(str(node).replace("William Glasgow", name))
    update = dossier.get("wikitree_update")
    if update:
        update = {**update, "profile_url": update.get("profile_url") or catalogue.WIKITREE_URL + ident}
    return refresh_person(soup, findings, update, links)


def _upsert_selected(rows, supplied, key):
    """Replace selected identities in place; retain unrelated rows and order."""
    replacements = {key(row): row for row in supplied}
    result, seen = [], set()
    for row in rows:
        ident = key(row)
        if ident not in replacements:
            result.append(row)
        elif ident not in seen:
            result.append(replacements[ident])
            seen.add(ident)
    result.extend(row for ident, row in replacements.items() if ident not in seen)
    return result


def publish_context(people, dossiers):
    """Expose the same cases to the site's shared person context and search."""
    registry_path = WEB / "assets/research/registry.json"
    registry = read_json(registry_path)
    supplied = {p["catalogue_id"] for p in people}
    registry = [r for r in registry if r["slug"] not in supplied]
    searches = []
    for person in people:
        slug = person["catalogue_id"]
        d = dossiers[slug]; ident = d["id"]
        years = [int(y) for y in re.findall(r"\b\d{4}\b", person["birth"]+" "+person["death"])]
        life = f"{person['birth'] or 'Not recorded'} – {person['death'] or 'Not recorded'}"
        registry.append({"id":ident,"selection_id":ident,"slug":slug,"name":person["name"],"url":f"/people/{slug}.html","life":life,
                         "birth":person["birth"] or None,"death":person["death"] or None,"birthPlace":person["birth_location"],"deathPlace":person["death_location"],
                         "country":"other","deathCountry":"other","reviewed":None,"override":False,"atlas":False,"branches":[],
                         "spouses":[r["name"] for r in d["relationships"]["spouses"]],"parentNames":[r["name"] for r in d["relationships"]["parents"]],
                         "childNames":[r["name"] for r in d["relationships"]["children"]],"gender":person["gender"],"from":min(years) if years else None,"to":max(years) if years else None,"records":0,"composite":False})
        model = {"schema_version":"3.0","build":"research-case-sync","id":ident,"catalogue_id":slug,"name":person["name"],"url":f"/people/{slug}.html",
                 "source_json":f"/people/{slug}.json","vitals":deepcopy(d["vitals"]),"original_vitals":deepcopy(d["vitals"]),"relationships":d["relationships"],
                 "identity":d["identity"],"review":None,"override":None,"open_questions":d["open_questions"],"events":[],"research_events":[],"dna":[],"record_ids":[],
                 "atlas":False,"branches":[],"evidence_count":len(d["evidence"]),"claims_count":len(d["claims"]),"selection_id":ident,"composite_entry":False,
                 "mentions":[],"family_events":[],"unresolved_events":[],"evidence_documents":[],"source_documents":[]}
        for value in model["vitals"].values():
            value.update(display_date=value.get("date"),country="other",basis="imported_vital")
        write_json(WEB / f"assets/research/people/{slug}.json", model)
        searches.append({"id":ident,"name":person["name"],"url":f"/people/{slug}.html","kind":"person","icon":"person","life":life,
                         "place":person["birth_location"] or person["death_location"],"meta":f"{life} · {ident}","tree":False,
                         "search":" ".join([person["name"],ident,person["birth_location"],person["death_location"]])})
    write_json(registry_path, registry)
    packed_path = WEB / "assets/v3/registry-packed.json"
    packed = read_json(packed_path)
    packed["rows"] = [[r.get(key) for key in packed["fields"]] for r in registry]
    write_json(packed_path, packed)
    for relative in ("assets/research/search-people.json", "assets/research/search-index.json"):
        path = WEB / relative
        rows = read_json(path)
        if isinstance(rows, list):
            rows = _upsert_selected(rows, searches, lambda row: row.get("id"))
            write_json(path, rows)
    for relative in ("assets/v3/search-people.json", "assets/v3/people-quick.json"):
        path = WEB / relative
        rows = read_json(path)
        supplied = [[row["id"], row["name"], row["url"], row["meta"], row["search"]]
                    if "search-people" in relative else
                    [row["id"], row["name"], row["life"], row["place"], row["url"].split("/")[-1][:-5]]
                    for row in searches]
        rows = _upsert_selected(rows, supplied, lambda row: row[0])
        write_json(path, rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh explicitly requested reviewed cases, preserving their prepared amendments")
    parser.add_argument("profiles", nargs="*", help="Limit materialization and shared context updates to these reviewed profile IDs")
    parser.add_argument("--profiles", dest="requested_profiles", nargs="+", help="Reviewed canonical profile IDs to materialize")
    args = parser.parse_args()
    args.profiles.extend(args.requested_profiles or [])
    if args.refresh and not args.profiles:
        raise ValueError("--refresh requires explicit reviewed profile IDs")
    manifest = read_json(MANIFEST)
    cases = manifest["cases"]
    amendments = reviewed_amendments(ROOT)
    evidence = catalogue._load_wikitree_evidence()
    seed_ids = {c["profile_id"] for c in cases.values() if c["status"] == "include"}
    seed_ids.update(amendments)
    if args.profiles:
        requested = set(args.profiles)
        seed_ids = {ident for ident in seed_ids if ident in requested}
        seed_ids.update(c["profile_id"] for key, c in cases.items()
                        if key in requested and c["status"] == "include")
    mapped_records = family.load_records() if args.refresh else []
    if mapped_records:
        family.apply_catalogue_profile_links(mapped_records)
    metadata = family.profile_metadata(mapped_records, seed_ids)
    cases = reviewed_inclusion_cases(cases, amendments, evidence, metadata)
    if args.profiles:
        requested = set(args.profiles)
        cases = {key: case for key, case in cases.items()
                 if key in requested or case.get("profile_id") in requested}
        eligible = {case.get("profile_id", key) for key, case in cases.items()
                    if case.get("status") in {"include", "include_record"}}
        if requested - eligible:
            raise ValueError("Profiles require reviewed inclusion: " + ", ".join(sorted(requested - eligible)))
    wanted = {c["profile_id"] for c in cases.values() if c["status"] == "include"}
    documentary = [c["record"] for c in cases.values() if c["status"] == "include_record"]
    selected_records = [row for row in mapped_records
                        if wanted.intersection(catalogue._ids(row.get("profile_id", "")))]
    edges = family.relationship_edges(mapped_records) if mapped_records else []
    _, descendant_counts, _ = family.root_metadata(mapped_records, edges)
    people = catalogue._build_people(selected_records + documentary, metadata, edges,
                                     descendant_counts, evidence, profile_seed_ids=wanted)
    people = [p for p in people if not p["likely_living"]]
    available = {p["profile_ids"][0] for p in people if p["profile_ids"]}
    if wanted - available:
        raise ValueError("Missing public historical metadata: " + ", ".join(sorted(wanted - available)))
    dossiers, index = build_machine_models(people)
    public_index = read_json(WEB / "data/people-index.json")
    search = read_json(WEB / "data/catalogue-search-index.json")
    existing = {r["id"] for r in search}
    links = {p["id"]: p.get("slug", p["id"].lower()) for p in public_index}
    links.update({p["id"]: p["catalogue_id"] for p in index})
    created = []
    created_people = []
    for person in people:
        slug = person["catalogue_id"]
        ident = person["profile_ids"][0] if person["profile_ids"] else slug
        if slug in existing and not args.refresh:
            continue
        capture = evidence["profiles"].get(ident, {})
        if person["profile_ids"] and int(capture.get("privacy") or capture.get("profile_fields", {}).get("Privacy") or 0) < 50:
            raise ValueError("No public capture for " + ident)
        dossier = dossiers[slug]
        previous_row = next((row for row in search if row["id"] == slug), {})
        previous_dossier_path = WEB / f"people/{slug}.json"
        if args.refresh and previous_dossier_path.exists():
            previous_dossier = read_json(previous_dossier_path)
            dossier = retain_case_context(dossier, previous_dossier)
            dossiers[slug] = dossier
            person["name"] = dossier["name"]
            next(item for item in index if item["id"] == ident)["name"] = dossier["name"]
        source_ids = [key for key, value in cases.items() if value.get("profile_id") == ident and value["status"] in {"include", "include_record"}]
        findings = catalogue._load_research_findings(list(dict.fromkeys([ident, *source_ids])))
        dossier["research_findings"] = findings
        dossier["similar_people"] = []
        dossier["potential_parentage"] = {}
        dossier["provenance"]["research_findings"] = (
            "Maintained research case files; inclusion reviewed in research-catalogue-cases.json "
            "or the durable catalogue-integration.json profile amendment review."
        )
        write_json(WEB / f"people/{slug}.json", dossier)
        write_json(WEB / f"people/{slug}.network.json", build_network(dossier, {d["id"]:d for d in dossiers.values()}))
        (WEB / f"people/{slug}.html").write_text(page_shell(person, dossier, findings, links), encoding="utf-8")
        public_index = [row for row in public_index
                        if row.get("catalogue_id") != slug and row.get("id") != ident]
        public_index.append(next(p for p in index if p["id"] == ident))
        row = {key: deepcopy(person[key]) for key in ("map_key", "name", "profile_ids", "first_names", "last_names_at_birth", "last_names_current", "suffixes", "has_suffix", "gender", "birth", "birth_note", "birth_location", "birth_location_note", "death", "death_location", "spouses", "father", "mother", "children", "cluster", "clusters", "descendants", "evidence", "recorded_in", "regions")}
        row.update(id=slug, locations=catalogue._unique([person["birth_location"], person["death_location"]]), location_aliases=[], location_groups=[], family_root=None, family_roots=[],
                   date_years=[int(y) for y in re.findall(r"\b\d{4}\b", person["birth"] + " " + person["death"])],
                   birth_year=None, death_year=None, missing_father=not person["father"], missing_mother=not person["mother"],
                   missing_vital_location=not person["birth_location"] or not person["death_location"], estimated_location=bool(person["birth_location_note"]),
                   has_profile=True, wikitree_free_space_url="", profile_disposition="", has_wikitree_destination=True, missing_profile=False,
                   profile_work_status="existing_profile", profile_work_candidate_count=0, needs_wikitree_update=False, wikitree_update_significance=0, wikitree_update_summary="",
                   has_original_record=any(e.get("source_quality")=="original" for e in dossier["evidence"]), has_open_questions=bool(dossier["open_questions"]),
                   uncertain_identity=False, source_qualities=catalogue._unique(e.get("source_quality") for e in dossier["evidence"]),
                   claim_statuses=catalogue._unique(c.get("status") for c in dossier["claims"]), record_types=[], record_count=0, woman_married_glasgow=False, evidence_terms=[])
        for kind in ("birth", "death"):
            match = re.search(r"\b(\d{4})\b", person[kind])
            row[kind + "_year"] = int(match.group(1)) if match else None
        if not person["profile_ids"]:
            row.update(has_profile=False, has_wikitree_destination=False, missing_profile=True,
                       profile_work_status="identity_hold", uncertain_identity=True,
                       evidence=["Historical baptism; WikiTree identity unresolved"], record_count=len(person["records"]))
        if previous_row:
            row = retain_catalogue_context(row, previous_row)
            search = [value for value in search if value["id"] != slug]
        search.append(row)
        created.append(ident)
        created_people.append(person)
    write_json(WEB / "data/people-index.json", public_index)
    write_json(WEB / "data/catalogue-search-index.json", search)
    (WEB / "data/people-index.js").write_text("window.glasgowPeopleIndex=" + json.dumps(search, ensure_ascii=False, separators=(",", ":")) + ";\n")
    combined = read_json(WEB / "data/people.json")
    if args.refresh:
        replaced = {p["catalogue_id"] for p in created_people}
        combined["people"] = [p for p in combined["people"] if p["catalogue_id"] not in replaced]
    known = {p["catalogue_id"] for p in combined["people"]}
    combined["people"].extend(p for p in people if p["catalogue_id"] not in known)
    combined["count"] = len(combined["people"])
    write_json(WEB / "data/people.json", combined)
    if created_people:
        publish_context(created_people, dossiers)
    print(json.dumps({"created": created}, indent=2))


if __name__ == "__main__":
    main()
