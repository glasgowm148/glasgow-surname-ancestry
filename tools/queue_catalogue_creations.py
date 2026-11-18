#!/usr/bin/env python3
"""Integrate reviewed new-person drafts into the maintained People catalogue.

The review manifest owns identity decisions. These helpers neither search for
profiles nor infer vital dates from documentary occurrence years.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from collections import Counter
from copy import deepcopy
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_research_catalog as catalogue
from catalogue_machine_data import build_machine_models, build_network, compact_resolver_row, _wikitree_profile_url
try:
    from relationship_update_changes import catalogue_changes, normalise_change
except ModuleNotFoundError:
    from tools.relationship_update_changes import catalogue_changes, normalise_change

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("research/queue-review-2026-10-17/catalogue-integration.json")


def _read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else deepcopy(default)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def creation_routes(web, slugs, restored_aliases=None):
    """Register reviewed local people in the existing shared route map."""
    path = web / 'assets/unified/routes.js'
    if not path.exists():
        return None
    text = path.read_text(encoding='utf-8')
    prefix = 'window.GlasgowRoutes='
    if not text.startswith(prefix):
        raise ValueError('Unsupported unified route schema')
    routes, end = json.JSONDecoder().raw_decode(text[len(prefix):])
    for slug in slugs:
        if slug in routes and routes[slug] != slug and (restored_aliases or {}).get(slug) != routes[slug]:
            raise ValueError(f'{slug}: reviewed creation conflicts with an existing route alias')
        routes[slug] = slug
    return prefix + json.dumps(routes, ensure_ascii=False, separators=(',', ':')) + text[len(prefix) + end:]


def publish_creation_aliases(root, entries):
    """Keep explicit source-subject URLs pointing to their canonical cases."""
    from tools.publish_retired_record_redirects import redirect_page
    web = Path(root) / 'www'
    active = {row['catalogue_id'] for row in _read(web / 'data/people.json', {'people': []})['people']}
    entries = list(entries)
    selected = {entry['catalogue_id'] for entry in entries}
    # Other maintained builders also publish canonical record accounts.
    # Their pre-prefix URL follows the same explicit catalogue-ID convention.
    entries += [{'catalogue_id': ident, 'subject_id': ident.removeprefix('record-')}
                for ident in sorted(active - selected) if ident.startswith('record-')]
    aliases = {}
    for entry in entries:
        current = entry['catalogue_id']
        for old in {str(entry.get('subject_id') or '').casefold(), current.removeprefix('record-')}:
            if (old == current or old in active or current not in active
                    or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', old)
                    or not (web / 'people' / (current + '.html')).is_file()):
                continue
            if old in aliases and aliases[old] != current:
                raise ValueError('Conflicting source-subject alias: ' + old)
            aliases[old] = current
    changed = 0
    for old, current in aliases.items():
        path = web / 'people' / (old + '.html')
        content = redirect_page(old, current)
        if not path.exists() or path.read_text() != content:
            path.write_text(content)
            changed += 1
    return changed


def native_creation_merges(root):
    """Read reversible workbench identity decisions; never infer a merge from names."""
    root = Path(root)
    if not (root / "genealogy.toml").is_file():
        return {}, {}
    from genealogy.store import open_project
    from tools.workbench_legacy_views import Views
    with open_project(root, readonly=True) as project:
        view = Views(project.store)
        merges = {old: new for old, new in view._merged_public.items()
                  if old != new and old.startswith("record-")}
        reasons = {}
        rows = project.store.all("SELECT id,kind,survivor_id,reason,moved_json FROM entity_merge")
        undone = {row["reason"].split("undo ", 1)[1].split(":", 1)[0]
                  for row in rows if row["kind"] == "split" and str(row["reason"] or "").startswith("undo ")}
        active = {row["id"]: row for row in rows if row["kind"] == "merge" and row["id"] not in undone}
        for row in active.values():
            target = view.person(row["survivor_id"])
            if target:
                reason = row["reason"]
                try:
                    structured = json.loads(reason)
                    if isinstance(structured, dict) and isinstance(structured.get("basis"), str):
                        reason = structured["basis"]
                except (TypeError, ValueError):
                    pass
                reasons.setdefault(target, []).append(reason)

        # Older reviewed links kept the catalogue prefix only in the link
        # receipt. Retire that route when its exact subject alias was moved
        # by the same active native merge to the stated WikiTree profile.
        path = root / "data/wikitree/catalogue-profile-links.json"
        for slug, link in _read(path, {}).get("entries", {}).items():
            if not slug.startswith("record-") or not isinstance(link, dict):
                continue
            merge = active.get(link.get("native_merge_id"))
            if not merge or view.person(merge["survivor_id"]) != link.get("profile_id"):
                continue
            subject = slug.removeprefix("record-")
            if view._merged_public.get(subject) != link["profile_id"]:
                continue
            for item in json.loads(merge["moved_json"] or "{}").get("rows", []):
                if item.get("table") != "external_id":
                    continue
                alias = project.store.one(
                    "SELECT value,system FROM external_id WHERE id=?", (item["key"].get("id"),)
                )
                if not alias or alias["system"] != "glasgow-local" or alias["value"] != subject:
                    continue
                if slug in merges and merges[slug] != link["profile_id"]:
                    raise ValueError(f"{slug}: current merge conflicts with the reviewed catalogue link")
                merges[slug] = link["profile_id"]
                break
    return merges, reasons


def _project_creation_merges(entries, merges, reasons):
    """Consolidate validated accounts without changing their maintained source drafts."""
    by_id = {entry["catalogue_id"]: deepcopy(entry) for entry in entries}
    grouped = {}
    for entry in entries:
        old = entry["catalogue_id"]
        target = merges.get(old, old)
        if target not in by_id:
            if old in merges and not target.startswith("record-"):
                continue  # The native decision retired this draft into an existing profile.
            if old in merges:
                raise ValueError(f"{old}: native merge survivor {target} has no reviewed creation account")
            continue
        grouped.setdefault(target, []).append(entry)
    result = []
    for target, sources in grouped.items():
        survivor = by_id[target]
        if len(sources) == 1:
            result.append(survivor)
            continue
        sources = sorted(sources, key=lambda entry: entry["catalogue_id"] != target)
        survivor["merged_source_accounts"] = deepcopy(sources)
        survivor["retired_catalogue_ids"] = [entry["catalogue_id"] for entry in sources if entry["catalogue_id"] != target]
        survivor["records"] = []
        survivor["candidates"] = []
        record_keys = set()
        concrete_values = {}
        for entry in sources:
            for row in entry.get("records", []):
                # The retained account is first: its interpretation wins, while
                # every original role/note stays in merged_source_accounts.
                key = (row.get("source_url"), row.get("attribution_scope", "subject"))
                if not key[0]:
                    raise ValueError(f"{target}: native merge record needs source_url")
                values = concrete_values.setdefault(key, {})
                for field in ("year", "filter_year", "record_location", "region"):
                    value = row.get(field)
                    if value is None or isinstance(value, str) and not value.strip():
                        continue
                    normal = value.strip() if isinstance(value, str) else value
                    # Numeric year strings and JSON numbers express the same
                    # scalar; other wording differences require review.
                    if field in ("year", "filter_year") and re.fullmatch(r"-?\d+(?:\.\d+)?", str(normal)):
                        normal = float(normal)
                    if field in values and values[field] != normal:
                        raise ValueError(f"{target}: native merge has conflicting record {field} "
                                         f"for {key[0]} ({key[1]})")
                    values[field] = normal
                if key not in record_keys:
                    survivor["records"].append(deepcopy(row))
                    record_keys.add(key)
            for row in entry.get("candidates", []):
                if row not in survivor["candidates"]:
                    survivor["candidates"].append(deepcopy(row))
        for field in ("birth", "death", "birth_location", "death_location", "gender"):
            values = {entry[field] for entry in sources if entry.get(field)}
            if len(values) > 1:
                raise ValueError(f"{target}: native merge has conflicting {field}")
            if not survivor.get(field) and values:
                survivor[field] = next(iter(values))
        local_ids = {entry["catalogue_id"].casefold() for entry in sources}
        survivor["candidates"] = [candidate for candidate in survivor["candidates"]
            if str(candidate.get("profile_id") or candidate.get("catalogue_id") or candidate.get("id") or "").casefold()
            not in local_ids]
        statuses = {entry.get("creation_status", "creation_ready") for entry in sources}
        survivor["creation_status"] = ("identity_hold" if "identity_hold" in statuses else
                                      "hold_source_verification" if "hold_source_verification" in statuses else "creation_ready")
        survivor["assessment"] = "\n\n".join(
            ["Identity consolidation: " + "; ".join(dict.fromkeys(reasons.get(target, []))) ] +
            [entry["assessment"] for entry in sources])
        additions = []
        for index, entry in enumerate(sources[1:], 1):
            draft = entry["draft_wikitext"]
            ref_prefix = "merged" + str(index) + "-"
            while ref_prefix in survivor["draft_wikitext"] or any(ref_prefix in text for text in additions):
                ref_prefix = "m" + ref_prefix
            # Namespace both named definitions and reuses, including unquoted names.
            draft = re.sub(r"""(<ref\b[^>]*?\bname\s*=\s*)(?:"([^"<>]+)"|'([^'<>]+)'|([^\s>/]+))""",
                           lambda match: match[1] + '"' + ref_prefix + next(value for value in match.groups()[1:] if value is not None) + '"', draft, flags=re.I)
            draft = re.sub(r"(?m)^\[\[Category:.*?\]\]\s*", "", draft)
            draft = re.sub(r"<references\s*/\s*>", "", draft, flags=re.I)
            draft = re.sub(r"(?m)^(==+)(.*?)\1\s*$", lambda m: "=" + m[1] + m[2] + m[1] + "=", draft)
            additions.append("=== Additional source account: " + entry["name"] + " ===\n" + draft.strip())
        insertion = "\n\n".join(additions) + "\n\n"
        survivor["draft_wikitext"] = re.sub(r"(?mi)^==\s*Sources\s*==\s*$", lambda m: insertion + m[0],
                                               survivor["draft_wikitext"], count=1)
        result.append(survivor)
    return result


def reviewed_people(root=ROOT, catalogue_ids=None, *, merge_state=None):
    """Return validated public historical subjects; fail before any writes."""
    root = Path(root).resolve()
    payload = _read(root / MANIFEST, {})
    entries = payload.get("new_people", [])
    merges, reasons = native_creation_merges(root) if merge_state is None else merge_state
    if catalogue_ids is not None:
        requested = list(catalogue_ids)
        if len(requested) != len(set(requested)):
            raise ValueError("Duplicate requested catalogue IDs")
        known = {entry.get("catalogue_id") for entry in entries if isinstance(entry, dict)}
        if set(requested) - known:
            raise ValueError(f"Unknown requested catalogue IDs: {sorted(set(requested) - known)}")
        selected = {merges.get(ident, ident) for ident in requested}
        entries = [entry for entry in entries if isinstance(entry, dict)
                   and merges.get(entry.get("catalogue_id"), entry.get("catalogue_id")) in selected]
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
        if "```" in draft or re.search(r"^##(?:\s|$)", draft, re.M):
            raise ValueError(f"{slug}: editorial Markdown must stay outside the paste-ready draft")
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
        if any(record.get("attribution_scope","subject") not in {"subject","comparison"} for record in records):
            raise ValueError(f"{slug}: unsupported record attribution scope")
        subject_records=[record for record in records if record.get("attribution_scope")!="comparison"]
        if not subject_records:
            raise ValueError(f"{slug}: a comparison is not a subject-defining record")
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
        historical += " " + " ".join(str(r.get("year") or "") for r in subject_records)
        basis = entry.get("historical_basis") or {}
        latest_birth = basis.get("latest_birth_year")
        age_proven = (isinstance(latest_birth, int) and latest_birth < date.today().year - 120
                      and catalogue._is_external_public_url(basis.get("source_url", "")))
        if not age_proven and not any(int(year) <= 1900 for year in re.findall(r"\b(1\d{3})\b", historical)):
            raise ValueError(f"{slug}: public historical status is not established")
    entries = _project_creation_merges(entries, merges, reasons)
    return entries


def reviewed_records(root=ROOT, catalogue_ids=None):
    """Standard builder rows, grouped under the reviewed canonical identity."""
    rows = []
    for entry in reviewed_people(root, catalogue_ids):
        for source in entry["records"]:
            if source.get("attribution_scope")=="comparison":
                continue
            row = deepcopy(source)
            # The catalogue's canonical supplement convention is record-<id>.
            row.update(person=entry["name"], profile_id="",
                       supplement_id=entry["catalogue_id"].removeprefix("record-"))
            if not entry.get("birth"):
                row["birth_status"] = "unknown"
            rows.append(row)
    return rows


def reviewed_audits(root=ROOT, catalogue_ids=None):
    return {entry["catalogue_id"]: {
        "recommended_action": "create_new_profile" if entry.get("creation_status", "creation_ready") == "creation_ready" else "hold",
        "identity_status": "distinct_documentary_person" if entry.get("creation_status", "creation_ready") == "creation_ready" else entry["creation_status"],
        "identity_note": entry["assessment"], "draft_path": entry["draft_path"],
        "review_method": "Reviewed documentary identity and duplicate assessment",
        "reviewed_at": entry.get("reviewed_at") or "2026-10-17", "candidates": deepcopy(entry.get("candidates") or []),
    } for entry in reviewed_people(root, catalogue_ids)}


def decorate_person(person, entry):
    """Apply reviewed fields after _build_people, including deliberately unknowns."""
    if person.get("profile_ids"):
        raise ValueError(f"{entry['catalogue_id']}: refusing to replace an existing-profile identity")
    ready = entry.get("creation_status", "creation_ready") == "creation_ready"
    person.update(catalogue_id=entry["catalogue_id"], name=entry["name"],
                  pending_profile_creation=True, creation_ready=ready,
                  creation_status=entry.get("creation_status", "creation_ready"),
                  uncertain_identity=entry.get("creation_status") == "identity_hold",
                  profile_work_status=("creation_ready" if ready else
                                       "existing_profile_candidate" if entry.get("candidates") else "identity_hold"),
                  profile_work_candidate_count=len(entry.get("candidates") or []),
                  creation_candidates=deepcopy(entry.get("candidates") or []),
                  has_wikitree_destination=False, wikitree_free_space_url="", profile_disposition="",
                  missing_profile=True, needs_wikitree_update=True,
                  creation_subject_id=entry["subject_id"], creation_assessment=entry["assessment"],
                  creation_draft_path=entry["draft_path"], creation_draft_wikitext=entry["draft_wikitext"],
                  creation_source_url=entry["source_subject_url"],
                  creation_merged_source_accounts=deepcopy(entry.get("merged_source_accounts") or []),
                  retired_catalogue_ids=deepcopy(entry.get("retired_catalogue_ids") or []),
                  creation_historical_basis=deepcopy(entry.get("historical_basis") or {}),
                  creation_relationship_changes=[normalise_change(change, entry["catalogue_id"])
                                                 for change in entry.get("relationship_changes", [])])
    person["creation_relationship_changes"] = [c for c in person["creation_relationship_changes"] if c]
    person["record_comparisons"] = [deepcopy(record) for record in entry["records"]
                                    if record.get("attribution_scope")=="comparison"]
    for key in ("first_names", "last_names_at_birth", "last_names_current"):
        person[key] = deepcopy(entry[key])
    for key in ("gender", "birth", "birth_note", "birth_location", "birth_location_note", "death", "death_location"):
        person[key] = entry.get(key) or ""
    if "occupations" in entry:
        occupations = entry["occupations"]
        if not isinstance(occupations, list) or any(not isinstance(value, str) or not value.strip() for value in occupations):
            raise ValueError(f"{entry['catalogue_id']}: occupations must be a list of nonblank strings")
        person["occupations"] = deepcopy(occupations)
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
                    else f"Review the draft for {person['name']}; resolve the identity before creation."
                    if person.get("creation_status") == "identity_hold"
                    else f"Review the draft for {person['name']}; verify the source before creation."),
        "candidates": deepcopy(person.get("creation_candidates") or []),
        "candidate_count": person.get("profile_work_candidate_count", 0),
        "profile_url": person.get("creation_source_url") or "",
        "draft_path": person.get("creation_draft_path") or "",
        "proposed_wikitext": person.get("creation_draft_wikitext") or "",
        "draft_wikitext": person.get("creation_draft_wikitext") or "",
        "remote_wikitext": "", "remote_captured_at": "", "remote_revision": "",
        "assessment": person.get("creation_assessment") or "",
        "relationship_changes": deepcopy(person.get("creation_relationship_changes") or []),
    }


def _hold_title(status):
    return ("New profile draft — identity on HOLD" if status == "identity_hold"
            else "New profile draft — source verification on HOLD")


def creation_panel(update):
    """Full creation text without a fictitious captured/current biography."""
    draft = update.get("proposed_wikitext") or update.get("draft_wikitext") or ""
    title = "Create a new WikiTree profile" if update.get("creation_ready", True) else _hold_title(update.get("creation_status"))
    self_ids = {str(update[key]).casefold() for key in ("catalogue_id", "profile_id") if update.get(key)}
    candidates = [item for item in (update.get("candidates") or [])
                  if str(item.get("profile_id") or "").casefold() not in self_ids]
    candidate_note = ""
    if candidates:
        rendered = []
        for item in candidates:
            profile_id = str(item.get("profile_id") or "")
            label = escape(item.get("name") or profile_id)
            url = str(item.get("url") or "")
            local = ROOT / "www" / "people" / f"{profile_id.lower()}.html"
            if profile_id and local.is_file():
                rendered.append(f'<a href="/people/{escape(profile_id.lower(), quote=True)}.html">{label}</a>')
            else:
                if url.startswith("https://www.wikitree.com/wiki/"):
                    target_id = url.removeprefix("https://www.wikitree.com/wiki/")
                    if target_id.casefold().startswith(("record-", "ancestry-")):
                        url = ""
                url = url or _wikitree_profile_url(profile_id) or ""
                rendered.append(f'<a href="{escape(url, quote=True)}">{label}</a>' if url else label)
        links = ", ".join(rendered)
        candidate_note = f'<p>Reviewed possible existing-profile matches ({len(candidates)}): {links}. Identity remains unresolved.</p>'
    return f'''<section id="wikitree-update" class="profile-update-panel profile-creation-panel">
<div class="candidate-section-heading"><div><p class="kicker">Needs updated on WikiTree</p><h2>{escape(title)}</h2></div><p>Significance {int(update.get('significance') or 0)}/100</p></div>
<p class="lede">{escape(update.get('summary') or '')}</p><p>No existing WikiTree biography is linked to this documentary person. The text below is the complete reviewed creation draft.</p>
<p>{escape(update.get('assessment') or '')}</p>
{candidate_note}
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
               creation_status=person["creation_status"], profile_work_status=person["profile_work_status"],
               profile_work_candidate_count=person["profile_work_candidate_count"], needs_wikitree_update=True,
               wikitree_update_significance=update["significance"], wikitree_update_summary=update["summary"],
               wikitree_update_relationship_changes=deepcopy(catalogue_changes(update)),
               has_original_record="original" in qualities, has_open_questions=bool(dossier["open_questions"]),
               uncertain_identity=person["uncertain_identity"],
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
                   (catalogue, "PROJECT_ROOT", root),
                   (catalogue, "RESEARCH_DIR", root / "research")]
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


def refresh_creation_statistics(root):
    """Refresh catalogue counts and maintained statistical panels from current public models."""
    from bs4 import BeautifulSoup
    from tools.catalogue_search_markup import compact_statistics
    web = Path(root) / 'www'
    people = _read(web / 'data/people.json', {'people': []})['people']
    searches = _read(web / 'data/catalogue-search-index.json', [])
    by_id = {row['id'].casefold(): row for row in searches}
    memberships = {person['catalogue_id']: {
        'primary': by_id.get(person['catalogue_id'].casefold(), {}).get('family_root'),
        'roots': by_id.get(person['catalogue_id'].casefold(), {}).get('family_roots', [])}
        for person in people}
    places = _read(web / 'data/places-index.json', [])
    locations = {place['id']: place['slug'] for place in places}
    records = _read(web / 'assets/research/record-index.json', None)
    record_count = len(records) if records is not None else sum(len(person['records']) for person in people)
    work_counts = Counter(person.get('profile_work_status') or 'unreviewed'
                          for person in people if not person.get('profile_ids'))
    original_count = sum(bool(row.get('has_original_record')) for row in searches)
    html = catalogue._catalogue_statistics(people, memberships, locations, len(places), record_count,
        work_counts, original_count, date.today().strftime('%-d %B %Y'))
    _write(web / 'data/catalogue-statistics.json', {'html': html})
    compact = compact_statistics(html)
    detailed = BeautifulSoup(html, 'html.parser')
    changed = []
    for relative in ('catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html', 'statistics/index.html'):
        path = web / relative
        if not path.exists():
            continue
        original = path.read_text(encoding='utf-8')
        soup = BeautifulSoup(original, 'html.parser')
        hero = soup.select_one('.catalogue-hero .lede')
        if hero is not None:
            hero.string = f'Search {len(people):,} historical people connected with the Glasgow surname.'
        for total in soup.select('#catalogue-total'):
            total.string = f'{len(people):,}'
        section = soup.select_one('#statistics')
        if section is not None:
            fragment = compact if relative != 'statistics/index.html' else html
            section.replace_with(BeautifulSoup(fragment, 'html.parser'))
        elif relative == 'statistics/index.html':
            # The dedicated page has its own reader shell and panel headings.
            for selector in ('.statistics-summary', '.statistics-grid', '.statistics-caution', '.catalogue-refresh'):
                old, new = soup.select_one(selector), detailed.select_one(selector)
                if old is not None and new is not None:
                    old.replace_with(BeautifulSoup(str(new), 'html.parser'))
        updated = str(soup)
        if updated != original:
            path.write_text(updated, encoding='utf-8')
            changed.append(relative)
    return {'people': len(people), 'records': record_count, 'pages': changed}


def retire_creation_context(web, retired, restored=()):
    """Remove retired search identities while retaining every record and event."""
    if not retired and not restored:
        return
    for relative in ('assets/research/registry.json', 'assets/research/search-people.json',
                     'assets/research/search-index.json', 'assets/v3/search-people.json',
                     'assets/v3/people-quick.json'):
        path = web / relative
        if not path.exists():
            continue
        rows = _read(path, [])
        rows = [row for row in rows if
                (row.get('slug') or row.get('id') if isinstance(row, dict) else row[0]) not in retired]
        _write(path, rows)
    packed_path = web / 'assets/v3/registry-packed.json'
    if packed_path.exists():
        packed = _read(packed_path, {})
        positions = [packed['fields'].index(key) for key in ('id', 'slug', 'selection_id') if key in packed['fields']]
        packed['rows'] = [row for row in packed['rows'] if not any(row[index] in retired for index in positions)]
        _write(packed_path, packed)
    for relative in ('assets/research/record-index.json', 'assets/research/event-index.json'):
        path = web / relative
        if not path.exists():
            continue
        rows = _read(path, [])
        for row in rows:
            original = row.get('native_merge_original_person')
            if original in restored and original not in retired:
                row['p'] = row.pop('native_merge_original_person')
            old = row.get('p')
            if old in retired:
                row.setdefault('native_merge_original_person', old)
                row['p'] = retired[old]
            for participant in row.get('participants', []):
                original = participant.get('native_merge_original_id')
                if original in restored and original not in retired:
                    participant['id'] = participant.pop('native_merge_original_id')
                old = participant.get('id')
                if old in retired:
                    participant.setdefault('native_merge_original_id', old)
                    participant['id'] = retired[old]
        _write(path, rows)
    for old, target in retired.items():
        _write(web / 'assets/research/people' / (old + '.json'),
               {'id': old, 'redirect_to': f'/assets/research/people/{target}.json', 'native_merge_redirect': target})


def apply_creations(root=ROOT, catalogue_ids=None):
    """Materialize reviewed identities in the actual catalogue and person pages."""
    from bs4 import BeautifulSoup
    root = Path(root).resolve()
    merges, _ = native_creation_merges(root)
    native_retired = {old: target.casefold() for old, target in merges.items()
                      if not target.startswith("record-")
                      and (catalogue_ids is None or old in catalogue_ids)}
    entries = reviewed_people(root, catalogue_ids)
    if not entries and not native_retired:
        return {"integrated": [], "count": 0}
    all_records = reviewed_records(root, catalogue_ids)
    built = catalogue._build_people(all_records, {}, [], {}, {"profiles": {}})
    by_id = {person['catalogue_id']: person for person in built}
    expected = {entry['catalogue_id'] for entry in entries}
    if len(built) != len(by_id) or set(by_id) != expected:
        raise ValueError('Reviewed source rows did not consolidate to the selected canonical people')
    people = []
    for entry in entries:
        people.append(decorate_person(by_id[entry['catalogue_id']], entry))
    web = root / "www"
    retired = {**native_retired, **{old: entry["catalogue_id"] for entry in entries
                                  for old in entry.get("retired_catalogue_ids", [])}}
    restored_aliases = {}
    for person in people:
        slug = person['catalogue_id']
        previous = _read(web / 'people' / (slug + '.json'), {})
        if previous.get('native_merge_redirect'):
            restored_aliases[slug] = previous['native_merge_redirect']
    routes_content = creation_routes(web, [p['catalogue_id'] for p in people], restored_aliases)
    if routes_content is not None and retired:
        prefix = 'window.GlasgowRoutes='
        routes, end = json.JSONDecoder().raw_decode(routes_content[len(prefix):])
        routes.update(retired)
        routes_content = prefix + json.dumps(routes, separators=(',', ':')) + routes_content[len(prefix) + end:]
    combined = _read(web / "data/people.json", {"people": []})
    for person in people:
        for old in combined["people"]:
            if old.get("catalogue_id") == person["catalogue_id"] and old.get("profile_ids"):
                raise ValueError(f"{person['catalogue_id']}: existing-profile canonical ID collision")
    dossiers, resolver = build_machine_models(people)
    try:
        from publish_resolved_dossiers import resolve
    except ModuleNotFoundError:
        from tools.publish_resolved_dossiers import resolve
    assessments = _read(web / "assets/research/assessments.json", {}).get("assessments", [])
    shared = _read(root / "research/relationship_assessments.json", [])
    dossiers = {slug: resolve(dossier, assessments, shared) for slug, dossier in dossiers.items()}
    from tools.publish_resolved_dossiers import project_catalogue_spouses, project_catalogue_parents
    project_catalogue_spouses(people, {d['id'].casefold(): d for d in dossiers.values()})
    searches = []
    public_index = [row for row in _read(web / "data/people-index.json", []) if row.get("catalogue_id") not in retired]
    links = {p["id"]: p.get("catalogue_id") or p.get("slug") or p["id"].lower() for p in public_index}
    links.update({d["id"]: slug for slug, d in dossiers.items()})
    audits = reviewed_audits(root, catalogue_ids)
    with _root_paths(root) as cases:
        # A maintained canonical findings file supersedes the manifest's
        # short creation conclusion.  Load it through the public-privacy
        # projection so creation pages cannot expose private material.
        from public_privacy import from_sources
        policy = from_sources(_read(root / "data/wikitree/profile-evidence.json", {}),
                              profiles={}, all_exports=True)
        for person in people:
            slug = person["catalogue_id"]
            dossier = dossiers[slug]
            update = creation_update(person)
            findings = policy.project(catalogue._load_research_findings([slug]))
            if not findings:
                findings = [{"profile_id": person["creation_subject_id"], "updated": audits[slug]["reviewed_at"], "sections": [
                {"title": "Current conclusion", "category": "conclusion", "markdown": person["creation_assessment"]},
                {"title": "Source findings", "category": "sources", "markdown": "\n\n".join(
                    f"[{r['source_title']}]({r['source_url']}) — {r.get('year') or 'Undated'}; {r.get('record_location') or 'place not established'}. {r.get('association') or ''} {r.get('note') or ''}" for r in person["records"])}]}]
            finding_source = next((f.get("source_path") for f in findings if f.get("source_path")), str(MANIFEST))
            cases.resolve_relative_urls(dossier, links)
            dossier.update(research_findings=findings, profile_work=audits[slug], pending_profile_creation=True,
                           creation_ready=person["creation_ready"], creation_status=person["creation_status"], wikitree_update=update, similar_people=[], potential_parentage={})
            dossier["provenance"]["research_findings"] = finding_source
            if person["creation_merged_source_accounts"]:
                dossier["provenance"]["merged_source_accounts"] = person["creation_merged_source_accounts"]
            if person["creation_historical_basis"]:
                dossier["historical_basis"] = deepcopy(person["creation_historical_basis"])
            _write(web / f"people/{slug}.json", dossier)
            _write(web / f"people/{slug}.network.json", build_network(dossier, {d["id"]: d for d in dossiers.values()}))
            soup = BeautifulSoup(cases.page_shell(person, dossier, findings, links, resolved=True), "html.parser")
            soup.select_one("#research-tools").insert(0, BeautifulSoup(creation_panel(update), "html.parser"))
            destination = soup.select_one(".profile-wikitree-actions")
            if destination:
                destination.clear()
                destination.append(BeautifulSoup(f'<span>{"New WikiTree profile to create" if person["creation_ready"] else _hold_title(person["creation_status"])}</span><a href="{escape(person["creation_source_url"], quote=True)}">Inspect the original source</a>', "html.parser"))
            for link in soup.select('a[href]'):
                if link.get_text(" ", strip=True) == "View the baptism source":
                    link.string = "Inspect the original source"
            soup.body.append(soup.new_tag("script", src=f"/people/profile-update.js?v={catalogue.CATALOGUE_ASSET_VERSION}", defer=True))
            from tools.site_analytics import with_analytics
            (web / f"people/{slug}.html").write_text(with_analytics(str(soup)), encoding="utf-8")
            searches.append(_search_row(person, dossier))
        project_catalogue_parents(searches, {d["id"].casefold(): d for d in dossiers.values()})
        # Context assets belong to complete sites; tiny build fixtures may omit them.
        if (web / "assets/research/registry.json").exists():
            cases.publish_context(people, dossiers)
    combined["people"] = _merge([row for row in combined["people"] if row.get("catalogue_id") not in retired], people, "catalogue_id")
    combined["count"] = len(combined["people"])
    combined["generated"] = date.today().isoformat()
    _write(web / "data/people.json", combined)
    search = _merge([row for row in _read(web / "data/catalogue-search-index.json", []) if row.get("id") not in retired], searches, "id")
    _write(web / "data/catalogue-search-index.json", search)
    _write(web / "data/people-index.json", _merge(public_index, [compact_resolver_row(row) for row in resolver], "catalogue_id"))
    (web / "data/people-index.js").write_text("window.glasgowPeopleIndex=" + json.dumps(search, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    if routes_content is not None:
        (web / 'assets/unified/routes.js').write_text(routes_content, encoding='utf-8')
    retire_creation_context(web, retired, {person["catalogue_id"] for person in people})
    publish_creation_aliases(root, entries)
    from tools.publish_retired_record_redirects import redirect_page
    for old, target in retired.items():
        (web / "people" / (old + ".html")).write_text(redirect_page(old, target), encoding="utf-8")
        _write(web / "people" / (old + ".json"), {"id": old, "redirect_to": f"/people/{target}.json", "native_merge_redirect": target})
        _write(web / "people" / (old + ".network.json"), {"redirect_to": f"/people/{target}.network.json", "relationships": []})
    refresh_creation_statistics(root)
    return {"integrated": [p["catalogue_id"] for p in people], "count": len(people)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--catalogue-id", action="append", help="Apply only these exact reviewed case IDs; repeat to select several")
    args = parser.parse_args()
    print(json.dumps(apply_creations(args.root, args.catalogue_id), indent=2))
