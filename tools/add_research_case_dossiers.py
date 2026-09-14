"""Materialize reviewed historical research cases omitted from mapped people.

The inclusion manifest supplies canonical destinations, never inferred identity
matches. Public profile metadata and the normal privacy filter remain required.
"""
import json
import re
from copy import deepcopy
from html import escape

from bs4 import BeautifulSoup

import build_family_map as family
import build_research_catalog as catalogue
from catalogue_machine_data import build_machine_models, build_network
from sync_catalogue_research import ROOT, WEB, read_json, write_json, refresh_person

MANIFEST = ROOT / "data/wikitree/research-catalogue-cases.json"


def page_shell(person, dossier, findings, links):
    # Reuse only the current site's shared shell, removing all subject content.
    soup = BeautifulSoup((WEB / "people/glasgow-3912.html").read_text(), "html.parser")
    ident, slug, name = dossier["id"], person["catalogue_id"], person["name"]
    destination = catalogue.WIKITREE_URL + ident if person["profile_ids"] else person["records"][0]["source_url"]
    destination_label = "View on WikiTree" if person["profile_ids"] else "View the baptism source"
    soup.body["data-g-path"] = f"/people/{slug}.html"
    soup.body["data-r-person"] = ident
    soup.body["data-g-person"] = json.dumps({"id":ident, "name":name, "life":f"{person['birth']} – {person['death']}", "url":f"/people/{slug}.html", "tree":False})
    soup.title.string = name + " · Glasgow surname archive"
    soup.select_one('meta[name="description"]')["content"] = "Sources, conclusions and unresolved questions for " + name + "."
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
    for label, key in (("Parents", "parents"), ("Spouses", "spouses"), ("Children", "children")):
        relatives = dossier["relationships"][key]
        if not relatives:
            continue
        values = []
        for relative in relatives:
            rid = relative.get("id", "")
            if not rid:
                continue
            href = f'people/{links[rid]}.html' if rid in links else catalogue.WIKITREE_URL + rid
            status = relative.get("tree_status_label") or relative.get("status_label") or "Recorded attachment; see assessment"
            values.append(f'<li><a href="{escape(href, quote=True)}">{escape(relative.get("name") or rid)}</a> · {escape(status)}</li>')
        if values:
            family_rows.append(f'<h3>{label}</h3><ul>{"".join(values)}</ul>')
    family_html = "".join(family_rows) or "<p>No family attachments are available in this public capture. See the case findings for documentary relationships and candidates.</p>"
    content = f'''<header class="v3-person-header"><span class="r-kicker">Person dossier · {ident}</span>
<div class="v3-title-line"><div><h1>{escape(name)}</h1><p>{escape(person['birth'] or 'Birth unrecorded')} – {escape(person['death'] or 'Death unrecorded')}</p>
<div class="profile-wikitree-actions"><span>{'WikiTree destination' if person['profile_ids'] else 'WikiTree identity unresolved'}</span><a href="{escape(destination, quote=True)}">{destination_label} <small>{ident} ↗</small></a></div></div></div></header>
<div class="v3-person-opening"><div id="person-summary"><section class="v3-person-understanding" id="overview"><span class="r-kicker">The research account</span>
<dl class="v3-vitals"><div><dt>Birth</dt><dd>{escape(person['birth'] or 'Not recorded')}<span>{escape(person['birth_location'] or 'Place not recorded')}</span></dd></div><div><dt>Death</dt><dd>{escape(person['death'] or 'Not recorded')}<span>{escape(person['death_location'] or 'Place not recorded')}</span></dd></div></dl>
<div class="v3-inline-links"><a href="#research">Read the full research →</a></div></section></div>
<section class="v3-person-family" id="family"><h2>The family</h2>{family_html}<p class="v3-family-note">Recorded attachments are distinguished from documentary proof in the research assessment.</p></section></div>
<section class="r-section" id="research"><span id="research-stack"></span><h2>The research behind the story</h2></section>
<section class="r-section" id="research-tools"><h2>Research tools and original material</h2><div class="r-actions"><a href="people/{slug}.json">Structured person data</a><a href="{escape(destination, quote=True)}">{destination_label}</a></div></section>'''
    main.append(BeautifulSoup(content, "html.parser"))
    # Remove the template's subject-specific breadcrumb text outside the main.
    for node in soup.find_all(string=lambda text: text and "William Glasgow" in text):
        if node.find_parent("main") is None and node.find_parent("script") is None:
            node.replace_with(str(node).replace("William Glasgow", name))
    return refresh_person(soup, findings, None, links)


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
            known = {r.get("id") for r in rows}
            rows.extend(r for r in searches if r["id"] not in known)
            write_json(path, rows)
    for relative in ("assets/v3/search-people.json", "assets/v3/people-quick.json"):
        path = WEB / relative; rows = read_json(path); known = {r[0] for r in rows}
        for row in searches:
            if row["id"] in known:
                continue
            rows.append([row["id"], row["name"], row["url"], row["meta"], row["search"]]
                        if "search-people" in relative else
                        [row["id"], row["name"], row["life"], row["place"], row["url"].split("/")[-1][:-5]])
        write_json(path, rows)


def main():
    manifest = read_json(MANIFEST)
    cases = manifest["cases"]
    wanted = {c["profile_id"] for c in cases.values() if c["status"] == "include"}
    metadata = family.profile_metadata([], wanted)
    evidence = catalogue._load_wikitree_evidence()
    documentary = [c["record"] for c in cases.values() if c["status"] == "include_record"]
    people = catalogue._build_people(documentary, metadata, [], {}, evidence, profile_seed_ids=wanted)
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
    for person in people:
        slug = person["catalogue_id"]
        ident = person["profile_ids"][0] if person["profile_ids"] else slug
        if slug in existing:
            continue
        capture = evidence["profiles"].get(ident, {})
        if person["profile_ids"] and int(capture.get("privacy") or capture.get("profile_fields", {}).get("Privacy") or 0) < 50:
            raise ValueError("No public capture for " + ident)
        dossier = dossiers[slug]
        source_ids = [key for key, value in cases.items() if value.get("profile_id") == ident and value["status"] in {"include", "include_record"}]
        findings = catalogue._load_research_findings(list(dict.fromkeys([ident, *source_ids])))
        dossier["research_findings"] = findings
        dossier["similar_people"] = []
        dossier["potential_parentage"] = {}
        dossier["provenance"]["research_findings"] = "Maintained research case files; inclusion reviewed in research-catalogue-cases.json"
        write_json(WEB / f"people/{slug}.json", dossier)
        write_json(WEB / f"people/{slug}.network.json", build_network(dossier, {d["id"]:d for d in dossiers.values()}))
        (WEB / f"people/{slug}.html").write_text(page_shell(person, dossier, findings, links), encoding="utf-8")
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
        search.append(row)
        created.append(ident)
    write_json(WEB / "data/people-index.json", public_index)
    write_json(WEB / "data/catalogue-search-index.json", search)
    (WEB / "data/people-index.js").write_text("window.glasgowPeopleIndex=" + json.dumps(search, ensure_ascii=False, separators=(",", ":")) + ";\n")
    combined = read_json(WEB / "data/people.json")
    known = {p["catalogue_id"] for p in combined["people"]}
    combined["people"].extend(p for p in people if p["catalogue_id"] not in known)
    combined["count"] = len(combined["people"])
    write_json(WEB / "data/people.json", combined)
    publish_context(people, dossiers)
    print(json.dumps({"created": created}, indent=2))


if __name__ == "__main__":
    main()
