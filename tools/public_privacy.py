"""Output-only privacy projection. Raw research captures stay outside www."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WITHHELD = {"id": "", "name": "Living person (details withheld)", "withheld": True, "outside_export": False}
RAW_FIELDS = {"biography_text", "biography_wikitext", "record_passages"}
WITHHELD_TEXT = "Private family details withheld."
# Values under these keys are identifiers or link targets. When one carries a
# withheld identity it is blanked, never replaced by WITHHELD_TEXT: a renderer
# that builds an href from it must see an empty value, not a sentence.
LINK_KEYS = frozenset({"id", "profile_id", "catalogue_id", "catalogueId", "parent", "child", "redirectedTo", "url", "href",
                       "profile_url", "slug", "selection_id", "html_url", "json_url", "network_url", "canonical_url"})


def is_link_key(key) -> bool:
    key = str(key)
    return key in LINK_KEYS or key.endswith(("_url", "Url", "_href", "_slug", "_path"))


def safe_href(value) -> str:
    """Return a link target fit for an href, or "" when there is none.

    A withheld or empty value gives "", so the caller prints the label as text.
    """
    text = str(value or "").strip()
    if not text or any(char.isspace() for char in text) or "withheld" in text.casefold():
        return ""
    return text
PROFILE_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+\b")


def tester_identifier_pattern(identifiers):
    # Symbolic kit labels can be ordinary historical surnames. Their DNA
    # containers are withheld separately; a surname alone is not private data.
    tokens = [token for token in identifiers if any(char.isdigit() for char in token)]
    return re.compile(r"(?<![A-Za-z0-9_-])(?:" + "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True)) + r")(?![A-Za-z0-9_-])") if tokens else re.compile(r"(?!)")


def _value(row, *keys):
    return next((row[key] for key in keys if row.get(key) not in (None, "", "0000-00-00", "0000")), "")


def identifier(row):
    return str(_value(row, "id", "profile_id", "Name"))


def public_capture(raw):
    try:
        return int(raw.get("privacy", raw.get("profile_fields", {}).get("Privacy", 50))) >= 50
    except (TypeError, ValueError):
        return False


def likely_living(*rows, year=None):
    """Positive living screen; unknown dates do not erase historical profiles.

    Explicit withholding wins. Zero dates are unknown, never evidence of death.
    The screen is deliberately conservative, not a claim of actual living status.
    """
    rows = [row for row in rows if isinstance(row, dict)]
    rows += [row["profile_fields"] for row in rows if isinstance(row.get("profile_fields"), dict)]
    if any(row.get("likely_living") or row.get("withheld") for row in rows):
        return True
    if any(_value(row, "death_date", "DeathDate") or _value(row, "death_location", "DeathLocation") for row in rows):
        return False
    years = []
    for row in rows:
        match = re.match(r"^(\d{4})", str(_value(row, "birth_date", "BirthDate")))
        if match and int(match[1]):
            years.append(int(match[1]))
    return bool(years and min(years) >= (year or date.today().year) - 120)


class PublicPrivacy:
    def __init__(self, profiles=()):
        self.rows = {}
        values = profiles.items() if isinstance(profiles, dict) else profiles
        for key, row in values:
            if isinstance(row, dict) and key:
                self.rows.setdefault(str(key).casefold(), []).append(row)
        self.blocked = {key for key, rows in self.rows.items() if likely_living(*rows)}
        self.tester_ids = frozenset()
        self.allow_approved_dna = False

    def contains_private_id(self, value, *, include_testers=True):
        text = str(value)
        return any(token.casefold() in self.blocked for token in PROFILE_TOKEN.findall(text)) or bool(
            include_testers and self.tester_ids and self.tester_pattern.search(text))

    def relation(self, row):
        key = identifier(row).casefold()
        if key in self.blocked or likely_living(*self.rows.get(key, []), row):
            return deepcopy(WITHHELD)
        return deepcopy(row)

    def capture(self, raw):
        # Capture-local names can occur in citations and URLs as well as prose.
        # Discard raw narrative altogether; reject citations carrying identifiers
        # of any withheld relative rather than attempting partial text rewriting.
        try:
            from catalogue_machine_data import _profile_assessment_flags
        except ModuleNotFoundError:
            from tools.catalogue_machine_data import _profile_assessment_flags
        flags = _profile_assessment_flags({"wikitree_evidence": [raw]})
        if not public_capture(raw):
            return {key: deepcopy(raw[key]) for key in ("profile_id", "profile_url", "captured_at", "last_updated") if key in raw} | {
                "assessment_flags": flags,
                "publication_scope": "Restricted capture withheld; consult the original profile for access permitted by WikiTree.",
            }
        public_keys = {"profile_id", "profile_url", "captured_at", "last_updated", "created", "privacy", "connected",
                       "profile_fields", "categories", "location_claims", "relations", "sources", "external_urls", "evidence_status"}
        output = {key: deepcopy(value) for key, value in raw.items() if key in public_keys}
        private_tokens = set(self.blocked)
        relations = {}
        for role, relatives in (raw.get("relations") or {}).items():
            relations[role] = []
            for relative in relatives:
                projected = self.relation(relative)
                if projected.get("withheld"):
                    private_tokens.update(str(relative.get(key) or "").casefold() for key in ("id", "profile_id", "Name", "name", "LongName", "BirthName"))
                relations[role].append(projected)
        private_tokens.discard("")
        def safe(value):
            text = json.dumps(value, ensure_ascii=False).casefold()
            return not any(token in text for token in private_tokens)
        for key in ("sources", "external_urls", "categories", "location_claims"):
            if key in output:
                output[key] = [item for item in output[key] if safe(item)]
        # Numeric relationship pointers can resolve back to a withheld identity.
        fields = output.get("profile_fields", {})
        public_fields = {"Name", "FirstName", "MiddleName", "LastNameAtBirth", "LastNameCurrent", "LongName", "Gender",
                         "BirthDate", "BirthLocation", "DeathDate", "DeathLocation", "Privacy", "DataStatus"}
        output["profile_fields"] = {key: deepcopy(value) for key, value in fields.items() if key in public_fields}
        output.update(relations=relations, assessment_flags=flags,
                      publication_scope="Public historical profile fields and filtered citations; raw narrative retained privately.")
        return output

    def project(self, value):
        """Also cover nested relation mirrors and imported capture copies."""
        if isinstance(value, dict):
            if isinstance(value.get("fields"), list) and isinstance(value.get("rows"), list):
                # Packed tables have positional cells. Project named records,
                # then repack; filtering cells would shift every later field.
                fields = value["fields"]
                rows = []
                for row in value["rows"]:
                    if not isinstance(row, list) or len(row) != len(fields):
                        raise ValueError("Malformed packed table: row width differs from fields")
                    projected = self.project(dict(zip(fields, row)))
                    if not projected.get("withheld"):
                        rows.append([projected.get(field) for field in fields])
                return {**self.project({key: item for key, item in value.items() if key not in {"fields", "rows"}}),
                        "fields": deepcopy(fields), "rows": rows}
            key_id = identifier(value).casefold()
            if key_id in self.blocked and "catalogue_id" not in value:
                return deepcopy(WITHHELD)
            if "profile_id" in value and any(key in value for key in ("profile_fields", "privacy", "relations", "biography_text", "record_passages", "publication_scope")):
                value = self.capture(value)
            return {key: (None if key == "catalogueId" else "") if is_link_key(key) and isinstance(item, str) and self.contains_private_id(item) else self.project(item) for key, item in value.items()
                    if key not in RAW_FIELDS and (self.allow_approved_dna or key not in {"kits", "kit_ids", "tester_ids", "referenceKit"}) and not self.contains_private_id(key)}
        if isinstance(value, list):
            return [self.project(item) for item in value
                    if not (isinstance(item, str) and self.contains_private_id(item))]
        if isinstance(value, str) and self.contains_private_id(value):
            # A value without spaces is an identifier, slug or URL, not prose:
            # blank it so it can never end up as link text inside an href.
            if not any(char.isspace() for char in value.strip()):
                return ""
            # A free-text paragraph can carry the name alongside its ID. Keep
            # other paragraphs, but omit the complete sensitive paragraph.
            return "\n\n".join(WITHHELD_TEXT if self.contains_private_id(paragraph) else paragraph
                                 for paragraph in re.split(r"\n\s*\n", value))
        return value


def from_sources(evidence=None, profiles=None):
    if evidence is None:
        path = ROOT / "data/wikitree/profile-evidence.json"
        evidence = json.loads(path.read_text()) if path.exists() else {}
    if profiles is None:
        try:
            from project_paths import merged_map_profiles
        except ModuleNotFoundError:
            from tools.project_paths import merged_map_profiles
        profiles, _ = merged_map_profiles()
    rows = list((profiles or {}).items())
    for profile_id, capture in (evidence or {}).get("profiles", {}).items():
        rows.append((profile_id, capture))
        for relatives in (capture.get("relations") or {}).values():
            rows.extend((identifier(relative), relative) for relative in relatives if identifier(relative))
    policy = PublicPrivacy(rows)
    try:
        from tools.repair_public_dna import private_tester_ids
    except ModuleNotFoundError:
        from repair_public_dna import private_tester_ids
    policy.tester_ids = private_tester_ids()
    policy.tester_pattern = tester_identifier_pattern(policy.tester_ids)
    return policy


def evidence_envelope(evidence, people):
    # Raw envelope ID lists and errors are local operational information.
    result = {key: evidence[key] for key in ("schema_version", "generated_at", "scope") if key in evidence}
    result["profiles"] = {capture["profile_id"]: capture for person in people
                          for capture in person.get("wikitree_evidence", []) if capture.get("profile_id")}
    return result


def repair(web=ROOT / "www"):
    policy = from_sources()
    changed = 0
    people_path = web / "data/people.json"
    payload = json.loads(people_path.read_text())
    original_people = payload["people"]
    people = [policy.project(person) for person in original_people if not any(str(key).casefold() in policy.blocked for key in person.get("profile_ids", []))]
    payload.update(people=people, count=len(people), withheld_likely_living_count=payload.get("withheld_likely_living_count", 0) + len(original_people) - len(people))
    def write(path, value):
        nonlocal changed
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
        if path.read_text() != text:
            path.write_text(text)
            changed += 1
    write(people_path, payload)
    evidence_path = web / "data/wikitree-profile-evidence.json"
    write(evidence_path, evidence_envelope(json.loads(evidence_path.read_text()), people))
    # Dossiers contain imported snapshots and machine evidence as well as current
    # relationships. Project every JSON mirror, retaining its research structure.
    for directory in (web / "people", web / "assets", web / "data", web / "onetree", web / "map/data"):
        for path in directory.rglob("*.json"):
            if path == people_path or path == evidence_path:
                continue
            raw = path.read_text()
            if not policy.contains_private_id(raw) and '"profile_id"' not in raw and not any('"' + field + '"' in raw for field in RAW_FIELDS) and '\\u' not in raw:
                continue
            value = json.loads(raw)
            try:
                from tools.public_ydna_research import approved_document
            except ModuleNotFoundError:
                from public_ydna_research import approved_document
            page_policy = policy
            if approved_document(path.relative_to(web).as_posix(), raw):
                from copy import copy
                page_policy = copy(policy)
                page_policy.tester_ids = frozenset()
                page_policy.tester_pattern = re.compile(r"(?!)")
                page_policy.allow_approved_dna = True
            projected = page_policy.project(value)
            if projected != value:
                write(path, projected)
    # Targeted releases also need to replace snapshots in previously generated
    # HTML; repairing JSON alone leaves that independent public sink exposed.
    try:
        from build_research_catalog import _wikitree_evidence_html
    except ModuleNotFoundError:
        from tools.build_research_catalog import _wikitree_evidence_html
    by_slug = {person["catalogue_id"]: person for person in people}
    snapshots = re.compile(r'<section\b[^>]*class=["\']profile-evidence["\'][^>]*>.*?</section>', re.S)
    for path in (web / "people").glob("*.html"):
        html = path.read_text()
        if not snapshots.search(html):
            continue
        captures = by_slug.get(path.stem, {}).get("wikitree_evidence", [])
        replacement = _wikitree_evidence_html(captures, {})
        replaced = False
        def replace_snapshot(match):
            nonlocal replaced
            if replaced:
                return ""
            replaced = True
            return replacement
        updated = snapshots.sub(replace_snapshot, html)
        if updated != html:
            path.write_text(updated)
            changed += 1
    search_path = web / "data/catalogue-search-index.json"
    script = web / "data/people-index.js"
    if search_path.exists() and script.exists():
        updated = "window.glasgowPeopleIndex=" + search_path.read_text().strip() + ";\n"
        if script.read_text() != updated:
            script.write_text(updated)
            changed += 1
    try:
        from repair_public_mirrors import repair as repair_mirrors
    except ModuleNotFoundError:
        from tools.repair_public_mirrors import repair as repair_mirrors
    changed += repair_mirrors(web, policy)
    return {"privacy_files": changed, "withheld_profile_count": len(policy.blocked)}


if __name__ == "__main__":
    print(repair())
