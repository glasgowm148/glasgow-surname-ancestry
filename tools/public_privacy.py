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


def valid_map_item(item):
    return (isinstance(item, list) and len(item) == 4
            and isinstance(item[0], str) and bool(item[0])
            and isinstance(item[1], str) and bool(item[1])
            and (item[2] is None or isinstance(item[2], (int, float)))
            and isinstance(item[3], bool))


def likely_living(*rows, year=None):
    """Positive living screen; unknown dates do not erase historical profiles.

    Explicit withholding wins. Zero dates are unknown, never evidence of death.
    The screen is deliberately conservative, not a claim of actual living status.
    """
    rows = [row for row in rows if isinstance(row, dict)]
    rows += [row["profile_fields"] for row in rows if isinstance(row.get("profile_fields"), dict)]
    if any(row.get("likely_living") or row.get("withheld") or
           str(row.get("IsLiving", "")).strip().casefold() in {"1", "true"}
           for row in rows):
        return True
    if any(_value(row, "death_date", "DeathDate") or _value(row, "death_location", "DeathLocation")
           or re.fullmatch(r"\d{3}0s", str(_value(row, "death_date_decade", "DeathDateDecade")))
           for row in rows):
        return False
    from genealogy.dates import wikitree_date
    from genealogy.publication import HISTORICAL_YEARS, birth_upper_year

    current = year or date.today().year
    years = []
    recent_decade = False
    for row in rows:
        # The toolkit's date reading: exact years, bounds and approximate dates
        # (ABT 1990 counts as up to 2000). Unreadable values fall back to a
        # leading year, then to a redacted birth decade.
        birth = wikitree_date(str(_value(row, "birth_date", "BirthDate")) or None)
        upper = birth_upper_year(birth)
        match = re.match(r"^(\d{4})", birth or "")
        if upper is not None:
            years.append(upper)
        elif match and int(match[1]):
            years.append(int(match[1]))
        else:
            decade = re.fullmatch(r"(\d{3}0)s", str(_value(row, "birth_date_decade", "BirthDateDecade")))
            if decade:
                # The latest possible birth controls this conservative screen.
                latest = int(decade[1]) + 9
                recent_decade |= latest >= current - HISTORICAL_YEARS
    return recent_decade or bool(years and min(years) >= current - HISTORICAL_YEARS)


class PublicPrivacy:
    def __init__(self, profiles=()):
        self.rows = {}
        values = profiles.items() if isinstance(profiles, dict) else profiles
        for key, row in values:
            if isinstance(row, dict) and key:
                self.rows.setdefault(str(key).casefold(), []).append(row)
        self.blocked = {key for key, rows in self.rows.items() if likely_living(*rows)}
        self.private_names = set()
        for key in self.blocked:
            for row in self.rows[key]:
                for fields in (row, row.get('profile_fields', {})):
                    names = [fields.get(k, '') for k in ('name', 'full_name', 'LongName', 'BirthName', 'LongNamePrivate', 'BirthNamePrivate')]
                    names.append(' '.join(str(fields.get(k) or '') for k in (
                        'Prefix', 'FirstName', 'MiddleName', 'LastNameCurrent', 'Suffix')).strip())
                    names.append(' '.join(str(v) for v in (
                        fields.get('FirstName') or fields.get('RealName') or '',
                        fields.get('MiddleName') or '', fields.get('LastNameCurrent') or fields.get('LastNameAtBirth') or '') if v))
                    self.private_names.update(str(name).casefold() for name in names if len(str(name).split()) >= 2)
        self.tester_ids = frozenset()
        self.allow_approved_dna = False

    def contains_private_id(self, value, *, include_testers=True):
        text = str(value)
        return any(token.casefold() in self.blocked for token in PROFILE_TOKEN.findall(text)) or bool(
            include_testers and not self.allow_approved_dna
            and self.tester_ids and self.tester_pattern.search(text))

    def private_subject(self, row):
        """Identify a subject across full, compact and record-index schemas."""
        if not isinstance(row, dict):
            return False
        values = [row.get(key, '') for key in ('id', 'profile_id', 'Name', 'catalogue_id', 'p', 'slug')]
        ids = row.get('profile_ids', [])
        values.extend(ids if isinstance(ids, list) else PROFILE_TOKEN.findall(str(ids)))
        if any(isinstance(value, str) and value.casefold() in self.blocked for value in values):
            return True
        # Recover old output whose identifier was blanked before its name.
        own_keys = [key for key in ('catalogue_id', 'p') if key in row]
        own_keys = own_keys or [key for key in ('id', 'profile_id', 'Name', 'slug') if key in row]
        orphan = bool(own_keys) and all(row.get(key) in (None, '', WITHHELD_TEXT) for key in own_keys)
        return orphan and any(str(row.get(key, '')).casefold() in self.private_names for key in ('name', 'person'))

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
            if {'fields', 'rows', 'strings', 'search', 'location_search'} <= value.keys():
                return self.project_search_table(value)
            if {'lat', 'lon', 'items'} <= value.keys() and isinstance(value['items'], list):
                items = [deepcopy(item) for item in value['items'] if valid_map_item(item)
                         and not self.contains_private_id(item[1])]
                return {**self.project({key: item for key, item in value.items() if key != 'items'}), 'items': items}
            if value.get('format') == 2 and {'strings', 'schemas', 'value'} <= value.keys():
                try:
                    from tools.site_payloads import pack_model, unpack_model
                except ModuleNotFoundError:
                    from site_payloads import pack_model, unpack_model
                return pack_model(self.project(unpack_model(value)))
            if (isinstance(value.get("fields"), list) and isinstance(value.get("rows"), list)
                    and all(isinstance(field, str) for field in value['fields'])):
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
            if self.private_subject(value):
                return deepcopy(WITHHELD)
            if "profile_id" in value and any(key in value for key in ("profile_fields", "privacy", "relations", "biography_text", "record_passages", "publication_scope")):
                value = self.capture(value)
            return {key: (None if key == "catalogueId" else "") if is_link_key(key) and isinstance(item, str) and self.contains_private_id(item) else self.project(item) for key, item in value.items()
                    if key not in RAW_FIELDS and (self.allow_approved_dna or key not in {"kits", "kit_ids", "tester_ids", "referenceKit"}) and not self.contains_private_id(key)}
        if isinstance(value, list):
            return [self.project(item) for item in value
                    if not self.private_subject(item)
                    and not (isinstance(item, str) and self.contains_private_id(item))]
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

    def project_search_table(self, value):
        """Repack prepared catalogue rows and remap their delta-coded postings."""
        def decode(cell):
            if isinstance(cell, (int, float)) and cell < 0:
                return value['strings'][-cell - 1]
            if isinstance(cell, list):
                return [decode(item) for item in cell]
            if isinstance(cell, dict):
                return cell['number'] if set(cell) == {'number'} else {k: decode(v) for k, v in cell.items()}
            return cell
        rows, positions = [], {}
        for old_index, row in enumerate(value['rows']):
            if len(row) != len(value['fields']):
                raise ValueError('Malformed prepared search table')
            named = dict(zip(value['fields'], map(decode, row)))
            if not self.private_subject(named):
                positions[old_index] = len(rows)
                rows.append(self.project(named))
        strings, string_ids = [], {}
        def encode(cell):
            if isinstance(cell, str):
                if cell not in string_ids:
                    string_ids[cell] = len(strings); strings.append(cell)
                return -string_ids[cell] - 1
            if isinstance(cell, list):
                return [encode(item) for item in cell]
            if isinstance(cell, dict):
                return {k: encode(v) for k, v in cell.items()}
            return {'number': cell} if isinstance(cell, (int, float)) and cell < 0 else cell
        result = self.project({k: v for k, v in value.items() if k not in {'strings', 'rows', 'search', 'location_search'}})
        result['rows'] = [[encode(row.get(field)) for field in value['fields']] for row in rows]
        result['strings'] = strings
        for key in ('search', 'location_search'):
            postings = {}
            for word, deltas in value[key].items():
                current, retained = 0, []
                for delta in deltas:
                    current += delta
                    if current in positions:
                        retained.append(positions[current])
                if retained and not self.contains_private_id(word):
                    postings[word] = [retained[0]] + [b - a for a, b in zip(retained, retained[1:])]
            result[key] = postings
        return result


def from_sources(evidence=None, profiles=None, *, all_exports=False):
    """The privacy policy from WikiTree evidence and tree exports.

    ``all_exports`` adds every merged export to the given ``profiles``: a
    builder that works on a subset must still withhold a relative whose living
    status only another export records.
    """
    if evidence is None:
        path = ROOT / "data/wikitree/profile-evidence.json"
        evidence = json.loads(path.read_text()) if path.exists() else {}
    merged = None
    if profiles is None or all_exports:
        try:
            from project_paths import merged_map_profiles
        except ModuleNotFoundError:
            from tools.project_paths import merged_map_profiles
        if profiles is None:
            profiles, _ = merged_map_profiles()
        else:
            try:
                merged, _ = merged_map_profiles()
            except FileNotFoundError:   # no exports here (a fresh clone or CI): nothing more to add
                merged = None
    rows = list((profiles or {}).items()) + list((merged or {}).items())
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


def remove_withheld_subject_routes(web, people, policy):
    """Remove direct subject files, whose names/prose may omit profile tokens."""
    removed = 0
    for person in people:
        if not any(str(key).casefold() in policy.blocked for key in person.get('profile_ids', [])):
            continue
        slug = person.get('catalogue_id', '')
        if not re.fullmatch(r'[a-z0-9_-]+', slug):
            raise ValueError('Unsafe withheld catalogue slug')
        paths = [web / 'people' / (slug + suffix) for suffix in ('.html', '.json', '.network.json')]
        paths += [web / 'people' / slug / 'index.html',
                  web / 'assets/research/people' / (slug + '.json'),
                  web / 'assets/v3/events' / (slug + '.json')]
        for path in paths:
            if not path.resolve().is_relative_to(web.resolve()):
                raise ValueError('Withheld route escapes public site')
            if path.is_file():
                path.unlink()
                removed += 1
    return removed


def repair_orphaned_subjects(web, policy):
    """Recover older redacted index/detail objects without dropping safe namesakes."""
    changed = removed = 0
    for path in Path(web).rglob('*.json'):
        raw = path.read_text()
        if WITHHELD_TEXT not in raw and not re.search(r'"(?:id|p|catalogue_id)"\s*:\s*""', raw):
            continue
        value = json.loads(raw)
        projected = policy.project(value)
        if isinstance(projected, dict) and projected.get('withheld'):
            path.unlink()
            removed += 1
        elif value != projected:
            path.write_text(json.dumps(projected, ensure_ascii=False, separators=(',', ':')) + '\n')
            changed += 1
    return {'orphan_mirrors': changed, 'orphan_subject_files': removed}


def refresh_positional_search_mirrors(web, policy):
    """Recreate old positional caches from their safe named-record source."""
    source = Path(web) / 'assets/research/search-people.json'
    if not source.exists():
        return {'positional_search_mirrors': 0}
    people = [row for row in policy.project(json.loads(source.read_text()))
              if row.get('id') and not row.get('withheld')]
    outputs = {
        'assets/v3/search-people.json': [[r['id'], r['name'], r.get('url', ''), r.get('meta', ''), r.get('search', '')] for r in people],
        'assets/v3/people-quick.json': [[r['id'], r['name'], r.get('life', ''), r.get('place', ''),
                                      r.get('url', '').split('/')[-1].removesuffix('.html')] for r in people],
    }
    changed = 0
    for relative, rows in outputs.items():
        path = Path(web) / relative
        if path.exists() and json.loads(path.read_text()) != rows:
            path.write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + '\n')
            changed += 1
    return {'positional_search_mirrors': changed}


def refresh_registry_mirror(web, policy):
    """Retain safe named registry rows and rebuild their positional mirror."""
    web = Path(web)
    path = web / 'assets/research/registry.json'
    if not path.exists():
        return {'registry_files': 0, 'registry_withheld_rows': 0, 'registry_restored_aliases': 0}
    original = json.loads(path.read_text())
    owners = {row['id'].casefold(): row for row in json.loads((web / 'data/catalogue-search-index.json').read_text())}
    rows = [row for row in policy.project(original) if not row.get('withheld')]
    restored = 0
    for row in rows:
        if re.fullmatch(r'[a-z0-9_-]+', row.get('slug', '')):
            continue
        owner = owners.get(str(row.get('selection_id') or row.get('id') or '').casefold())
        if not owner or owner.get('name') != row.get('name'):
            raise ValueError('Registry alias has no matching public canonical owner')
        slug = owner['id']
        if not (web / 'people' / (slug + '.json')).is_file():
            raise ValueError('Registry alias owner has no published dossier')
        row.update(slug=slug, url=f'/people/{slug}.html')
        restored += 1
    if len({row['slug'] for row in rows}) != len(rows):
        raise ValueError('Duplicate canonical registry slug')
    outputs = {path: rows}
    packed_path = web / 'assets/v3/registry-packed.json'
    if packed_path.exists():
        packed = json.loads(packed_path.read_text())
        packed['rows'] = [[row.get(field) for field in packed['fields']] for row in rows]
        outputs[packed_path] = packed
    changed = 0
    for target, value in outputs.items():
        if json.loads(target.read_text()) != value:
            target.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
            changed += 1
    return {'registry_files': changed, 'registry_withheld_rows': len(original) - len(rows),
            'registry_restored_aliases': restored}


def remove_withheld_model_nodes(web):
    """Old privacy sentinels are relationships, never standalone tree nodes."""
    files = nodes = 0
    for relative in ('assets/research/atlas-model.json', 'assets/research/atlas-import.json',
                     'onetree/glasgow-one-tree-polished-3/model.json'):
        path = Path(web) / relative
        if not path.exists():
            continue
        model = json.loads(path.read_text())
        people = [p for p in model['people'] if p.get('id') and not p.get('withheld')]
        if len(people) == len(model['people']):
            continue
        nodes += len(model['people']) - len(people)
        model['people'] = people
        model['meta']['people'] = sum(p.get('kind') == 'person' for p in people)
        path.write_text(json.dumps(model, ensure_ascii=False, separators=(',', ':')) + '\n')
        files += 1
    return {'model_privacy_files': files, 'withheld_model_nodes': nodes}


def repair(web=ROOT / "www", *, json_directories=("people", "assets", "data", "onetree", "map/data")):
    policy = from_sources()
    changed = 0
    people_path = web / "data/people.json"
    payload = json.loads(people_path.read_text())
    original_people = payload["people"]
    changed += remove_withheld_subject_routes(web, original_people, policy)
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
    for relative in json_directories:
        directory = web / relative
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
    orphan_counts = repair_orphaned_subjects(web, policy)
    changed += sum(orphan_counts.values())
    changed += refresh_positional_search_mirrors(web, policy)['positional_search_mirrors']
    changed += refresh_registry_mirror(web, policy)['registry_files']
    changed += remove_withheld_model_nodes(web)['model_privacy_files']
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
