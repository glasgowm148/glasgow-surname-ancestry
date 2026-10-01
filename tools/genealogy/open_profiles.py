"""Project open-profile search projection; never stage raw API narratives."""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path.home() / 'Library/Application Support/genealogy-tools'
STATUS = RUNTIME / 'open-profile-status.json'
FIELDS = ('Name', 'FirstName', 'MiddleName', 'LastNameAtBirth', 'LastNameCurrent',
          'LongName', 'BirthDate', 'BirthLocation', 'DeathDate', 'DeathLocation',
          'Gender', 'Privacy', 'IsLiving', 'Touched')
PROFILE_ID = re.compile(r"\b[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+\b")
EXCLUDED = re.compile(r'\b(?:DNA|GEDmatch|FTDNA|haplogroup|chromosome|tester|kit\s*(?:id|number)|transcription|licensed|restricted|credentials)\b', re.I)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def metadata(root=ROOT):
    """Match the repo's export -> capture -> live override precedence, metadata only."""
    rows, origins = {}, {}
    paths = sorted((root / 'data/exports/one-tree').glob('ONT_Glas*.json'),
                   key=lambda p: p.name.split('_', 2)[-1])
    for path in paths:
        for key, raw in load(path).get('data', {}).items():
            ident = raw.get('Name')
            if ident:
                rows[ident] = {k: raw[k] for k in FIELDS if k in raw}
                origins[ident] = f'{path.relative_to(root) }#/data/{key}'
    for name, nested in [('profile-evidence.json', True), ('live-profile-overrides.json', False)]:
        path = root / 'data/wikitree' / name
        for ident, raw in load(path).get('profiles', {}).items():
            fields = raw.get('profile_fields', {}) if nested else raw
            rows[ident] = {k: fields[k] for k in FIELDS if k in fields}
            if nested:
                rows[ident]['Privacy'] = raw.get('privacy', fields.get('Privacy'))
            origins[ident] = f'{path.relative_to(root)}#/profiles/{ident}' + ('/profile_fields' if nested else '')
    return rows, origins


def eligibility(row, checked=None):
    checked = checked or {}
    if str(row.get('Privacy')) != '60' or (checked and str(checked.get('Privacy')) != '60'):
        return 'not_open'
    if str(row.get('IsLiving', '')).lower() in ('1', 'true') or str(checked.get('IsLiving', '')).lower() in ('1', 'true'):
        return 'living'
    if row.get('likely_living') or row.get('withheld'):
        return 'living'
    if str(row.get('IsLiving', '')).lower() in ('0', 'false') or str(checked.get('IsLiving', '')).lower() in ('0', 'false'):
        return 'explicit_nonliving'
    def year(key):
        match = re.match(r'^(\d{4})', str(row.get(key, '')))
        return int(match[1]) if match else 0
    if 0 < year('DeathDate') <= date.today().year:
        return 'recorded_death'
    if 0 < year('BirthDate') <= date.today().year - 120:
        return 'historical_birth'
    return 'living_status_unknown'


def atomic_text(path, text):
    if path.is_file() and path.read_text(encoding='utf-8') == text:
        return
    tmp = path.with_suffix('.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def stage(directory, root=ROOT, status_path=STATUS):
    rows, origins = metadata(root)
    checked = load(status_path).get('profiles', {}) if status_path.exists() else {}
    reasons = {ident: eligibility(row, checked.get(ident)) for ident, row in rows.items()}
    eligible = {ident for ident, reason in reasons.items() if reason in ('explicit_nonliving', 'recorded_death', 'historical_birth')}
    # Reuse the website's private tester screening; deny non-open identities too.
    sys.path.insert(0, str(root))
    from tools.public_privacy import from_sources
    policy = from_sources()
    policy.blocked.difference_update(ident.casefold() for ident in eligible)
    policy.blocked.update(ident.casefold() for ident in rows if ident not in eligible)
    eligible_folded = {ident.casefold() for ident in eligible}
    def safe(value):
        text = json.dumps(value, ensure_ascii=False)
        return not EXCLUDED.search(text) and not policy.contains_private_id(text) and all(
            token.casefold() in eligible_folded for token in PROFILE_ID.findall(text))
    index = load(root / 'www/data/people-index.json')
    dossiers = {}
    for entry in index:
        for ident in [entry['id'], *entry.get('alternate_ids', [])]:
            dossiers[ident] = entry
    directory.mkdir(parents=True, exist_ok=True)
    mapping, detailed = {}, 0
    aliases = {}
    for ident in eligible:
        canonical = checked.get(ident, {}).get('canonical_name')
        if canonical and canonical != ident:
            aliases.setdefault(canonical, []).append(ident)
    for ident in sorted(eligible):
        canonical = checked.get(ident, {}).get('canonical_name', ident)
        if canonical != ident and canonical in eligible:
            continue  # Index the current profile once; retain its old IDs as aliases.
        row = rows[ident]
        name = row.get('LongName') or ' '.join(str(row.get(k) or '') for k in ('FirstName', 'MiddleName', 'LastNameAtBirth')).strip() or ident
        lines = [f'# {name} — {ident}', f'WikiTree: https://www.wikitree.com/wiki/{canonical}',
                 'Profile statements and local conclusions are leads; verify original records.',
                 f'Eligibility: Open (Privacy 60); {reasons[ident]}.',
                 f'Metadata source: {origins[ident]}']
        if aliases.get(ident):
            lines.append('Former profile IDs: ' + ', '.join(sorted(aliases[ident])))
        if canonical != ident:
            lines.append(f'Former profile ID {ident} now redirects to {canonical}; old captured statements require verification against the current profile.')
        for key in ('BirthDate', 'BirthLocation', 'DeathDate', 'DeathLocation', 'Gender'):
            if row.get(key) and safe(row[key]):
                lines.append(f'{key}: {row[key]} [source: {origins[ident]}/{key}]')
        sources = [origins[ident]]
        entry = dossiers.get(ident)
        path = root / (entry.get('json_url', '').lstrip('/') if entry else '')
        # Site URLs are rooted at www, with no directory-wide source indexing.
        if entry:
            path = root / 'www' / entry.get('json_url', '').lstrip('/')
        if entry and path.is_file() and not path.is_symlink() and path.resolve().is_relative_to((root / 'www/people').resolve()):
            dossier = load(path)
            source = str(path.relative_to(root))
            sources.append(source)
            lines.append(f'Public research account: {source}')
            def add(pointer, value):
                if value and safe(value):
                    lines.append(f'{json.dumps(value, ensure_ascii=False)} [source: {source}#{pointer}]')
            add('/vitals', dossier.get('vitals'))
            for role, relatives in dossier.get('relationships', {}).items():
                for n, relation in enumerate(relatives):
                    if relation.get('id') in eligible:
                        add(f'/relationships/{role}/{n}', {k: relation[k] for k in ('id', 'name', 'relationship', 'status_label', 'evidence_ids') if k in relation})
            for section in ('claims', 'evidence', 'source_summary', 'open_questions'):
                for n, item in enumerate(dossier.get(section, [])):
                    add(f'/{section}/{n}', item)
            for n, findings in enumerate(dossier.get('research_findings', [])):
                for j, section in enumerate(findings.get('sections', [])):
                    if section.get('category') in ('conclusion', 'assessment', 'actions'):
                        add(f'/research_findings/{n}/sections/{j}', section)
            detailed += 1
        filename = ident + '.md'
        atomic_text(directory / filename, '\n\n'.join(lines) + '\n')
        mapping[filename] = {'sources': sources, 'sha256': hashlib.sha256((directory / filename).read_bytes()).hexdigest()}
    for path in directory.iterdir():
        if path.name not in mapping:
            if path.is_dir() or path.is_symlink():
                raise ValueError('Unexpected directory/symlink in generated profile corpus')
            path.unlink()
    atomic_text(RUNTIME / 'open-profile-sources.json', json.dumps(mapping, ensure_ascii=False, sort_keys=True) + '\n')
    return {'open_profiles': len(mapping), 'eligible_profile_ids': len(eligible), 'redirected_aliases': sum(len(v) for v in aliases.values()), 'public_research_accounts': detailed,
            'eligibility_counts': dict(Counter(reasons.values()))}
