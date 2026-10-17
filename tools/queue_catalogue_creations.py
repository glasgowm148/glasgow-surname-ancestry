#!/usr/bin/env python3
"""Integrate reviewed new-person drafts into the maintained People catalogue.

The review manifest owns identity decisions. These helpers neither search for
profiles nor infer vital dates from documentary occurrence years.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_research_catalog as catalogue
from catalogue_machine_data import build_machine_models, build_network, compact_resolver_row

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("research/queue-review-2026-10-17/catalogue-integration.json")


def _read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else deepcopy(default)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def reviewed_people(root=ROOT):
    """Return validated public historical subjects; fail before any writes."""
    root = Path(root).resolve()
    payload = _read(root / MANIFEST, {})
    entries = payload.get("new_people", [])
    seen = set()
    for entry in entries:
        slug = entry.get("catalogue_id", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError(f"Invalid or repeated canonical catalogue ID: {slug}")
        seen.add(slug)
        for field in ("subject_id", "name", "assessment", "draft_path", "draft_wikitext"):
            if not entry.get(field):
                raise ValueError(f"{slug}: missing {field}")
        for field in ("first_names", "last_names_at_birth", "last_names_current"):
            if not isinstance(entry.get(field), list):
                raise ValueError(f"{slug}: explicit {field} list required")
        if not entry["first_names"]:
            raise ValueError(f"{slug}: a reviewed given name is required")
        if entry.get("likely_living") or entry.get("living") or entry.get("private"):
            raise ValueError(f"{slug}: non-public or living subject")
        draft = entry["draft_wikitext"]
        surname = next(iter(entry["last_names_at_birth"]), "")
        if not catalogue._is_complete_profile_draft(draft, subject_surname=surname):
            raise ValueError(f"{slug}: complete sourced WikiTree draft required")
        draft_path = (root / entry["draft_path"]).resolve()
        if root not in draft_path.parents:
            raise ValueError(f"{slug}: draft path must stay within the project")
        if not draft_path.exists() or draft not in draft_path.read_text(encoding="utf-8"):
            raise ValueError(f"{slug}: maintained draft does not contain reviewed text")
        if not catalogue._is_external_public_url(entry.get("source_subject_url", "")):
            raise ValueError(f"{slug}: original public subject source required")
        records = entry.get("records") or []
        if not records:
            raise ValueError(f"{slug}: reviewed source records required")
        for record in records:
            if not record.get("source_title") or not catalogue._is_external_public_url(record.get("source_url", "")):
                raise ValueError(f"{slug}: every record needs a public source citation")
            if record["source_url"] not in draft:
                raise ValueError(f"{slug}: source record missing from complete draft")
            if record.get("profile_id"):
                raise ValueError(f"{slug}: new-person record already links a profile")
        status = entry.get("creation_status") or "creation_ready"
        if status not in {"creation_ready", "hold_source_verification", "identity_hold"}:
            raise ValueError(f"{slug}: unsupported creation status {status}")
        historical = " ".join(str(entry.get(key) or "") for key in ("birth", "death"))
        historical += " " + " ".join(str(r.get("year") or "") for r in records)
        basis = entry.get("historical_basis") or {}
        latest_birth = basis.get("latest_birth_year")
        age_proven = (isinstance(latest_birth, int) and latest_birth < date.today().year - 120
                      and catalogue._is_external_public_url(basis.get("source_url", "")))
        if not age_proven and not any(int(year) <= 1900 for year in re.findall(r"\b(1\d{3})\b", historical)):
            raise ValueError(f"{slug}: public historical status is not established")
    return entries


def reviewed_records(root=ROOT):
    """Standard builder rows, grouped under the reviewed canonical identity."""
    rows = []
    for entry in reviewed_people(root):
        for source in entry["records"]:
            row = deepcopy(source)
            # The catalogue's canonical supplement convention is record-<id>.
            row.update(person=entry["name"], profile_id="",
                       supplement_id=entry["catalogue_id"].removeprefix("record-"))
            if not entry.get("birth"):
                row["birth_status"] = "unknown"
            rows.append(row)
    return rows


def reviewed_audits(root=ROOT):
    return {entry["catalogue_id"]: {
        "recommended_action": "create_new_profile" if entry.get("creation_status", "creation_ready") == "creation_ready" else "hold",
        "identity_status": "distinct_documentary_person" if entry.get("creation_status", "creation_ready") == "creation_ready" else "hold_source_verification",
        "identity_note": entry["assessment"], "draft_path": entry["draft_path"],
        "review_method": "Reviewed documentary identity and duplicate assessment",
        "reviewed_at": entry.get("reviewed_at") or "2026-10-17", "candidates": [],
    } for entry in reviewed_people(root)}


def decorate_person(person, entry):
    """Apply reviewed fields after _build_people, including deliberately unknowns."""
    if person.get("profile_ids"):
        raise ValueError(f"{entry['catalogue_id']}: refusing to replace an existing-profile identity")
    ready = entry.get("creation_status", "creation_ready") == "creation_ready"
    person.update(catalogue_id=entry["catalogue_id"], name=entry["name"],
                  pending_profile_creation=True, creation_ready=ready,
                  creation_status=entry.get("creation_status", "creation_ready"),
                  profile_work_status="creation_ready" if ready else "identity_hold", profile_work_candidate_count=0,
                  has_wikitree_destination=False, wikitree_free_space_url="", profile_disposition="",
                  missing_profile=True, needs_wikitree_update=True,
                  creation_subject_id=entry["subject_id"], creation_assessment=entry["assessment"],
                  creation_draft_path=entry["draft_path"], creation_draft_wikitext=entry["draft_wikitext"],
                  creation_source_url=entry["source_subject_url"],
                  creation_historical_basis=deepcopy(entry.get("historical_basis") or {}))
    for key in ("first_names", "last_names_at_birth", "last_names_current"):
        person[key] = deepcopy(entry[key])
    for key in ("gender", "birth", "birth_note", "birth_location", "birth_location_note", "death", "death_location"):
        person[key] = entry.get(key) or ""
    person["_birth_estimate_suppressed"] = not bool(person["birth"])
    person["likely_living"] = False  # reviewed_people enforces historical evidence.
    return person


def creation_update(person):
    """Queue entry for a new profile, distinct from a replacement biography."""
    if not person.get("pending_profile_creation") or person.get("profile_ids"):
        return None
    return {
        "profile_id": person["catalogue_id"], "catalogue_id": person["catalogue_id"],
        "action": "create_new_profile", "new_profile": True, "pending": True,
        "creation_ready": bool(person.get("creation_ready")),
        "creation_status": person.get("creation_status") or "creation_ready",
        "significance": 65 if person.get("creation_ready") else 50,
        "summary": (f"Create the reviewed, sourced profile for {person['name']}." if person.get("creation_ready")
                    else f"Review the draft for {person['name']}; verify the source before creation."),
        "profile_url": person.get("creation_source_url") or "",
        "draft_path": person.get("creation_draft_path") or "",
        "proposed_wikitext": person.get("creation_draft_wikitext") or "",
        "draft_wikitext": person.get("creation_draft_wikitext") or "",
        "remote_wikitext": "", "remote_captured_at": "", "remote_revision": "",
        "assessment": person.get("creation_assessment") or "",
    }


def creation_panel(update):
    """Full creation text without a fictitious captured/current biography."""
    draft = update.get("proposed_wikitext") or update.get("draft_wikitext") or ""
    title = "Create a new WikiTree profile" if update.get("creation_ready", True) else "New profile draft — source verification on HOLD"
    return f'''<section id="wikitree-update" class="profile-update-panel profile-creation-panel">
<div class="candidate-section-heading"><div><p class="kicker">Needs updated on WikiTree</p><h2>{escape(title)}</h2></div><p>Significance {int(update.get('significance') or 0)}/100</p></div>
<p class="lede">{escape(update.get('summary') or '')}</p><p>No existing WikiTree biography is linked to this documentary person. The text below is the complete reviewed creation draft.</p>
<p>{escape(update.get('assessment') or '')}</p>
<details class="profile-draft-panel"><summary>Complete paste-ready WikiTree creation draft</summary>
<textarea id="profile-update-draft" class="profile-draft" rows="28" readonly>{escape(draft)}</textarea>
<div class="actions"><button id="copy-profile-update" class="button" type="button">Copy complete profile</button><a class="button secondary" href="{escape(update.get('profile_url') or '', quote=True)}">Inspect the original source</a></div>
<p id="profile-update-status" class="form-status" aria-live="polite"></p></details></section>'''


def _search_row(person, dossier):
    row = {key: deepcopy(person[key]) for key in (
        "map_key", "name", "profile_ids", "first_names", "last_names_at_birth", "last_names_current", "suffixes", "has_suffix",
        "gender", "birth", "birth_note", "birth_location", "birth_location_note", "death", "death_location", "spouses", "father", "mother",
        "children", "cluster", "clusters", "descendants", "evidence", "recorded_in", "regions")}
    update = creation_update(person)
    years = lambda value: [int(y) for y in re.findall(r"\b(\d{4})\b", value)]
    birth_years, death_years = years(person["birth"]), years(person["death"])
    qualities = catalogue._unique(e.get("source_quality") for e in dossier["evidence"])
    row.update(id=person["catalogue_id"], locations=catalogue._unique([person["birth_location"], person["death_location"], *person["recorded_in"]]),
               location_aliases=[], location_groups=[], family_root=None, family_roots=[],
               date_years=sorted(set(birth_years + death_years + [int(r["filter_year"]) for r in person["records"] if isinstance(r.get("filter_year"), (int, float))])),
               birth_year=birth_years[0] if birth_years else None, death_year=death_years[0] if death_years else None,
               missing_father=not person["father"], missing_mother=not person["mother"], missing_vital_location=not person["birth_location"] or not person["death_location"],
               estimated_location=bool(person["birth_location_note"]), has_profile=False, wikitree_free_space_url="", profile_disposition="",
               has_wikitree_destination=False, missing_profile=True, creation_ready=person["creation_ready"], pending_profile_creation=True,
               creation_status=person["creation_status"], profile_work_status=person["profile_work_status"], profile_work_candidate_count=0, needs_wikitree_update=True,
               wikitree_update_significance=update["significance"], wikitree_update_summary=update["summary"], wikitree_update_relationship_changes=[],
               has_original_record="original" in qualities, has_open_questions=bool(dossier["open_questions"]), uncertain_identity=False,
               source_qualities=qualities, claim_statuses=catalogue._unique(c.get("status") for c in dossier["claims"]),
               record_types=catalogue._catalogue_record_types(person), record_count=len(person["records"]), woman_married_glasgow=False, evidence_terms=[])
    return row


@contextmanager
def _root_paths(root):
    """Keep existing renderers root-aware without leaking patched module paths."""
    import add_research_case_dossiers as cases
    import sync_catalogue_research as sync
    assignments = [(cases, "ROOT", root), (cases, "WEB", root / "www"),
                   (sync, "ROOT", root), (sync, "WEB", root / "www"),
                   # The shell already has its new subject content. A renderer
                   # refresh here could replace it with a stale previous dossier.
                   (sync, "revise", lambda text: (text, False)),
                   (catalogue, "PROJECT_ROOT", root)]
    old = [(module, key, getattr(module, key)) for module, key, _ in assignments]
    try:
        for module, key, value in assignments:
            setattr(module, key, value)
        yield cases
    finally:
        for module, key, value in old:
            setattr(module, key, value)


def _merge(existing, supplied, key):
    identities = {row[key] for row in supplied}
    return [row for row in existing if row[key] not in identities] + supplied


def apply_creations(root=ROOT):
    """Materialize reviewed identities in the actual catalogue and person pages."""
    from bs4 import BeautifulSoup
    root = Path(root).resolve()
    entries = reviewed_people(root)
    if not entries:
        return {"integrated": [], "count": 0}
    people = []
    all_records = reviewed_records(root)
    for entry in entries:
        records = [row for row in all_records if row["supplement_id"] == entry["catalogue_id"].removeprefix("record-")]
        built = catalogue._build_people(records, {}, [], {}, {"profiles": {}})
        if len(built) != 1:
            raise ValueError(f"{entry['catalogue_id']}: source rows did not consolidate to one person")
        people.append(decorate_person(built[0], entry))
    web = root / "www"
    combined = _read(web / "data/people.json", {"people": []})
    for person in people:
        for old in combined["people"]:
            if old.get("catalogue_id") == person["catalogue_id"] and old.get("profile_ids"):
                raise ValueError(f"{person['catalogue_id']}: existing-profile canonical ID collision")
    dossiers, resolver = build_machine_models(people)
    searches = []
    public_index = _read(web / "data/people-index.json", [])
    links = {p["id"]: p.get("catalogue_id") or p.get("slug") or p["id"].lower() for p in public_index}
    links.update({d["id"]: slug for slug, d in dossiers.items()})
    audits = reviewed_audits(root)
    with _root_paths(root) as cases:
        for person in people:
            slug = person["catalogue_id"]
            dossier = dossiers[slug]
            update = creation_update(person)
            findings = [{"profile_id": person["creation_subject_id"], "updated": audits[slug]["reviewed_at"], "sections": [
                {"title": "Current conclusion", "category": "conclusion", "markdown": person["creation_assessment"]},
                {"title": "Source findings", "category": "sources", "markdown": "\n\n".join(
                    f"[{r['source_title']}]({r['source_url']}) — {r.get('year') or 'Undated'}; {r.get('record_location') or 'place not established'}. {r.get('association') or ''} {r.get('note') or ''}" for r in person["records"])}]}]
            dossier.update(research_findings=findings, profile_work=audits[slug], pending_profile_creation=True,
                           creation_ready=person["creation_ready"], creation_status=person["creation_status"], wikitree_update=update, similar_people=[], potential_parentage={})
            dossier["provenance"]["research_findings"] = str(MANIFEST)
            if person["creation_historical_basis"]:
                dossier["historical_basis"] = deepcopy(person["creation_historical_basis"])
            _write(web / f"people/{slug}.json", dossier)
            _write(web / f"people/{slug}.network.json", build_network(dossier, {d["id"]: d for d in dossiers.values()}))
            soup = BeautifulSoup(cases.page_shell(person, dossier, findings, links), "html.parser")
            soup.select_one("#research-tools").insert(0, BeautifulSoup(creation_panel(update), "html.parser"))
            destination = soup.select_one(".profile-wikitree-actions")
            if destination:
                destination.clear()
                destination.append(BeautifulSoup(f'<span>{"New WikiTree profile to create" if person["creation_ready"] else "New profile draft — source verification on HOLD"}</span><a href="{escape(person["creation_source_url"], quote=True)}">Inspect the original source</a>', "html.parser"))
            for link in soup.select('a[href]'):
                if link.get_text(" ", strip=True) == "View the baptism source":
                    link.string = "Inspect the original source"
            soup.body.append(soup.new_tag("script", src=f"/people/profile-update.js?v={catalogue.CATALOGUE_ASSET_VERSION}", defer=True))
            (web / f"people/{slug}.html").write_text(str(soup), encoding="utf-8")
            searches.append(_search_row(person, dossier))
        # Context assets belong to complete sites; tiny build fixtures may omit them.
        if (web / "assets/research/registry.json").exists():
            cases.publish_context(people, dossiers)
    combined["people"] = _merge(combined["people"], people, "catalogue_id")
    combined["count"] = len(combined["people"])
    _write(web / "data/people.json", combined)
    search = _merge(_read(web / "data/catalogue-search-index.json", []), searches, "id")
    _write(web / "data/catalogue-search-index.json", search)
    _write(web / "data/people-index.json", _merge(public_index, [compact_resolver_row(row) for row in resolver], "catalogue_id"))
    (web / "data/people-index.js").write_text("window.glasgowPeopleIndex=" + json.dumps(search, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    return {"integrated": [p["catalogue_id"] for p in people], "count": len(people)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(apply_creations(args.root), indent=2))
