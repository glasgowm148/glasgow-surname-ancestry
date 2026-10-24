"""Read-only evidence inventory before dispatching an ancestry investigation.

No conclusions, parent selections or confidence grades are inferred here.
"""
from pathlib import Path
import argparse
import json
import re
from urllib.parse import parse_qs, urlsplit


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def bounded(value, limit=6000):
    """Bound serialized context; truncated values remain explicitly marked."""
    encoded = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(encoded) <= limit:
        return {"value": value, "truncated": False}
    return {"excerpt": encoded[:limit], "truncated": True}


def findings_sections(text, limit=6000):
    """Select exact overall conclusion, never historical topic conclusions."""
    sections = []
    for match in re.finditer(r'^## ([^\n]+)\n', text, re.M):
        end = re.search(r'^## ', text[match.end():], re.M)
        stop = match.end() + end.start() if end else len(text)
        title = match.group(1).strip()
        if title.casefold() == 'current conclusion' or re.fullmatch(
                r'next (?:useful test|questions|steps|actions)', title, re.I):
            sections.append({"heading": title, "line": text[:match.start()].count('\n') + 1,
                             **bounded(text[match.end():stop].strip(), limit)})
    return {"current_conclusion": [s for s in sections if s['heading'].casefold() == 'current conclusion'],
            "next_questions": [s for s in sections if s['heading'].casefold() != 'current conclusion'],
            "truncated": any(s['truncated'] for s in sections)}


def source_alias(value):
    """Normalize only an explicit FMP record URL; do not merge companion indexes."""
    if not isinstance(value, str):
        return None
    if value.startswith(('https://', 'http://')):
        parsed = urlsplit(value)
        if parsed.hostname and (parsed.hostname == 'findmypast.co.uk' or parsed.hostname.endswith('.findmypast.co.uk')):
            return parse_qs(parsed.query).get('id', [value])[0]
    return value


def explicit_role(role, kind):
    """Recognize recorded roles only; a comparison or discussion is not paternity."""
    role = role.strip().casefold().split(';', 1)[0]
    # Qualifiers about the later adult after a semicolon do not erase a recorded role.
    if re.search(r'comparison|candidate|possible|excluded|unknown|not (?:named|established|proved)|unproved', role):
        return False
    if kind == 'father':
        return bool(re.match(r'(?:(?:recorded|named|indexed) )?father(?=$|[ ,:])', role))
    return bool(re.match(r'(?:(?:recorded|named|indexed) )?(?:child|son|daughter)\b|(?:birth and )?baptism subject\b|subject:.*\bchild\b', role))



def record_needs_review(record, child, father, assessments):
    roles = record.get('profiles', {})
    if not record.get('publish_to_record_index') or 'inspected' not in record.get('status', '').lower():
        return False
    # "original uninspected" alone is not an inspected transcript.
    status = record.get('status', '').lower()
    if not re.search(r'(?<!un)inspected', status):
        return False
    if not explicit_role(roles.get(child, {}).get('role', ''), 'child'):
        return False
    fathers = [p for p, v in roles.items() if explicit_role(v.get('role', ''), 'father')]
    if father:
        fathers = [p for p in fathers if p == father]
    if not fathers:
        return False
    aliases = {source_alias(record.get(k)) for k in ('record_id', 'provider_record_id', 'source_url')} - {None, ''}
    for parent in fathers:
        pair = [a for a in assessments if parent in a.get('people', [])]
        if any(aliases.intersection(source_alias(s) for s in a.get('source_ids', [])) for a in pair):
            continue
        assertions = {a.get('assertion_id') for a in pair} - {None}
        reviews = record.get('relationship_review', {}).get('assessments', [])
        if any(r.get('subject') == child and r.get('assertion_id') in assertions for r in reviews):
            continue
        return True
    return False


def load_preflight_context(root=Path('.')):
    """Load one reusable read-only snapshot for a dispatch batch; no cache/registry."""
    root = Path(root)
    from tools.genealogy.open_profiles import metadata, eligibility, STATUS
    try:
        rows, origins = metadata(root)
    except FileNotFoundError:
        rows, origins = {}, {}
    checked = read_json(STATUS, {}).get('profiles', {}) if root.resolve() == Path(__file__).resolve().parents[1] else {}
    return {'rows': rows, 'origins': origins, 'checked': checked,
            'assessments': read_json(root / 'research/relationship_assessments.json', []),
            'records': read_json(root / 'research/canonical_records.json', [])}


def related_parent_account(child_id, father_id, *, root, context, text_limit=3000):
    """One independently eligible parent account; never expand its relatives."""
    if not father_id:
        return {'available': False, 'reason': 'No father ID supplied'}
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*-\d+', father_id) or father_id not in context['rows']:
        return {'available': False, 'reason': 'No existing profile metadata; record-only or unavailable parent'}
    from tools.genealogy.open_profiles import eligibility
    reason = eligibility(context['rows'][father_id], context['checked'].get(father_id))
    if reason not in ('explicit_nonliving', 'recorded_death', 'historical_birth'):
        return {'available': False, 'withheld': True, 'eligibility': reason}
    kinship = biography_kinship_leads(father_id, child_id, root=root, context=context)
    path = Path('research') / father_id / 'findings.md'
    sections = findings_sections((root / path).read_text() if (root / path).exists() else '', text_limit)
    remaining = text_limit
    for key in ('current_conclusion', 'next_questions'):
        for section in sections[key]:
            text = section.pop('value', section.pop('excerpt', ''))
            clipped = len(text) > remaining
            section['value'] = text[:remaining]
            remaining = max(0, remaining - len(section['value']))
            section['truncated'] = section['truncated'] or clipped
    sections['truncated'] = any(s['truncated'] for key in ('current_conclusion', 'next_questions') for s in sections[key])
    records = [(i, r) for i, r in enumerate(context['records'])
               if father_id in r.get('profiles', {}) and child_id not in r.get('profiles', {})]
    return {'available': True, 'withheld': False, 'eligibility': reason,
            'biographical_kinship_leads': kinship,
            'findings': {'path': str(path), 'exists': (root / path).exists(), **sections},
            'parent_only_sources': {'total': len(records), 'truncated': len(records) > 3,
                'items': [{'path': 'research/canonical_records.json', 'pointer': f'/{i}',
                           'record_id': str(r.get('record_id', ''))[:150],
                           'status': str(r.get('status', r.get('source_status', '')))[:200]}
                          for i, r in records[:3]]}}


def _safe_research_path(root, value):
    """Resolve only existing, non-symlink paths contained under research/."""
    if not isinstance(value, str) or not value or '\\' in value:
        return None
    rel = Path(value)
    if rel.is_absolute() or not rel.parts or rel.parts[0] != 'research' or '..' in rel.parts:
        return None
    base = (root / 'research').resolve()
    candidate = root / rel
    probe = root
    for part in rel.parts:
        probe = probe / part
        if probe.is_symlink():
            return None
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return resolved if resolved.is_file() and base in resolved.parents else None


def _biography_inputs(root, context):
    """Load capture and pending-draft manifest once, on first eligible account request."""
    cached = context.get('_biography_inputs')
    if cached is not None:
        return cached
    evidence_path = root / 'data/wikitree/profile-evidence.json'
    integration_path = root / 'research/queue-review-2026-10-17/catalogue-integration.json'
    evidence = read_json(evidence_path, {})
    integration = read_json(integration_path, {})
    cached = {'evidence': evidence.get('profiles', {}) if isinstance(evidence, dict) else {},
              'updates': integration.get('profile_updates', {}) if isinstance(integration, dict) else {},
              'evidence_path': 'data/wikitree/profile-evidence.json'}
    context['_biography_inputs'] = cached
    return cached


def _counterpart_names(counterpart_id, context, captured):
    names = set()
    for source in (context.get('rows', {}).get(counterpart_id, {}),
                   captured.get(counterpart_id, {}).get('profile_fields', {})):
        for key in ('Name', 'RealName', 'FirstName'):
            value = source.get(key)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    names.add(value.split()[0])
    return names


def _kinship_excerpts(text, *, account_id, counterpart_id, source_kind, source_path,
                      counterpart_names, max_excerpts=3, max_chars=2400):
    """Return bounded literal paragraph leads with stable line/offset locators."""
    if not isinstance(text, str) or not text:
        return {'total_matches': 0, 'truncated': False, 'items': []}
    kin = re.compile(r'\b(?:son|daughter|child(?:ren)?|father|parents?)\b', re.I) if counterpart_id else re.compile(
        r'\b(?:father|mother|parents?|grandfather|grandmother|brother|sister|uncle|aunt|niece|nephew)\b|\b(?:son|daughter)\s+of\b', re.I)
    id_term = re.compile(rf'(?<![\w-]){re.escape(counterpart_id)}(?![\w-])', re.I) if counterpart_id else None
    name_terms = [re.compile(rf'(?<![\w-]){re.escape(v)}(?![\w-])', re.I)
                  for v in sorted(counterpart_names) if v]
    matches = []
    for m in re.finditer(r'\S[\s\S]*?(?=\n[ \t]*\n|\Z)', text):
        raw = m.group(0)
        if not raw.strip():
            continue
        kin_hits = list(kin.finditer(raw))
        if not kin_hits:
            continue
        id_hits = list(id_term.finditer(raw)) if id_term else []
        hits = id_hits or [hit for term in name_terms for hit in term.finditer(raw)]
        if not hits and counterpart_id:
            continue
        if not counterpart_id:
            hits = kin_hits
        kin_hit, hit = min(((k, h) for k in kin_hits for h in hits),
                           key=lambda pair: (abs(pair[0].start()-pair[1].start()), pair[1].start(), pair[0].start()))
        matches.append((0 if id_hits else 1 if counterpart_id else 2, m.start(), m.end(), raw, kin_hit.span(), hit.span()))
    matches.sort(key=lambda x: (x[0], x[1]))
    items = []
    used = 0
    truncated = len(matches) > max_excerpts
    per_item = max(1, max_chars // max(1, max_excerpts))
    for rank, para_start, para_end, paragraph, kin_span, counterpart_span in matches[:max_excerpts]:
        remaining = max_chars - used
        if remaining <= 0:
            truncated = True
            break
        budget = min(remaining, per_item)
        # Center a bounded window on both the kinship word and counterpart mention.
        anchor_start = min(kin_span[0], counterpart_span[0])
        anchor_end = max(kin_span[1], counterpart_span[1])
        if anchor_end - anchor_start > budget:
            truncated = True
            continue
        left = max(0, anchor_start - max(0, (budget - (anchor_end-anchor_start)) // 2))
        right = min(len(paragraph), left + budget)
        left = max(0, right - budget)
        excerpt = paragraph[left:right]
        excerpt_start = para_start + left
        if left > 0 or right < len(paragraph):
            truncated = True
        line = text.count('\n', 0, excerpt_start) + 1
        item = {'source_kind': source_kind, 'path': source_path,
                'line': line, 'char_offset': excerpt_start, 'excerpt': excerpt,
                'match_kind': 'counterpart_id' if rank == 0 else 'counterpart_name' if counterpart_id else 'parent_kinship_term',
                'source_context': ('Literal paragraph window containing the kinship term and counterpart mention.' if counterpart_id else
                                   'Literal child-account paragraph with a parent or kinship term; no father candidate supplied or inferred.')}
        if source_kind == 'captured_biography':
            item['pointer'] = f'/profiles/{account_id}/biography_wikitext'
        items.append(item)
        used += len(excerpt)
    return {'total_matches': len(matches), 'truncated': truncated, 'items': items,
            'characters': used}


def biography_kinship_leads(account_id, counterpart_id, *, root, context,
                           max_excerpts=3, max_chars=2400):
    """Private literal leads from one eligible account's captured and pending prose."""
    from tools.genealogy.open_profiles import eligibility
    reason = eligibility(context.get('rows', {}).get(account_id, {}),
                         context.get('checked', {}).get(account_id))
    if reason not in ('explicit_nonliving', 'recorded_death', 'historical_birth'):
        return {'available': False, 'withheld': True, 'eligibility': reason,
                'total_matches': 0, 'truncated': False, 'characters': 0,
                'interpretation': 'Literal text-match leads only; not a relationship assertion.',
                'sources': {'captured_biography': 'withheld', 'pending_draft': 'withheld'}, 'items': []}
    sources = _biography_inputs(root, context)
    captured = sources['evidence'].get(account_id, {})
    names = _counterpart_names(counterpart_id, context, sources['evidence'])
    per_source = []
    source_status = {}
    capture_text = captured.get('biography_wikitext') if isinstance(captured, dict) else None
    if isinstance(capture_text, str):
        found = _kinship_excerpts(capture_text, account_id=account_id, counterpart_id=counterpart_id,
                                  source_kind='captured_biography', source_path=sources['evidence_path'],
                                  counterpart_names=names, max_excerpts=max_excerpts, max_chars=max_chars)
        per_source.append(found); source_status['captured_biography'] = 'available'
    else:
        per_source.append({'total_matches': 0, 'truncated': False, 'items': []})
        source_status['captured_biography'] = 'missing'
    update = sources['updates'].get(account_id, {})
    draft_value = update.get('draft_path') if isinstance(update, dict) else None
    draft_path = _safe_research_path(root, draft_value)
    if draft_path is None:
        per_source.append({'total_matches': 0, 'truncated': False, 'items': []})
        source_status['pending_draft'] = 'withheld' if draft_value else 'missing'
    else:
        draft_text = draft_path.read_text()
        found = _kinship_excerpts(draft_text, account_id=account_id, counterpart_id=counterpart_id,
                                  source_kind='pending_draft', source_path=str(draft_path.relative_to(root.resolve())),
                                  counterpart_names=names, max_excerpts=max_excerpts, max_chars=max_chars)
        per_source.append(found); source_status['pending_draft'] = 'available'
    # Preserve source diversity when possible, while ranking ID matches ahead of name-only matches.
    available = [list(x['items']) for x in per_source]
    selected = []
    nonempty = [(idx, rows[0]) for idx, rows in enumerate(available) if rows]
    if max_excerpts >= len(nonempty):
        selected.extend(item for _, item in sorted(
            nonempty, key=lambda pair: (pair[1]['match_kind'] != 'counterpart_id', pair[0])))
        for idx, _ in nonempty:
            available[idx].pop(0)
    candidates = [(item['match_kind'] != 'counterpart_id', idx, item)
                  for idx, rows in enumerate(available) for item in rows]
    candidates.sort(key=lambda value: (value[0], value[1], value[2]['char_offset']))
    selected.extend(item for _, _, item in candidates[:max(0, max_excerpts-len(selected))])
    total = sum(x['total_matches'] for x in per_source)
    truncated = any(x['truncated'] for x in per_source) or total > len(selected)
    result_items = []
    used = 0
    for item in selected:
        room = max_chars - used
        if room <= 0:
            truncated = True
            break
        clipped = item['excerpt'][:room]
        if len(clipped) < len(item['excerpt']):
            truncated = True
        result_items.append({**item, 'excerpt': clipped})
        used += len(clipped)
    return {'total_matches': total, 'truncated': truncated, 'characters': used,
            'interpretation': 'Literal text-match leads only; not a relationship assertion.',
            'sources': source_status, 'items': result_items[:max_excerpts]}


def build_preflight(profile_id, father_id=None, *, root=Path('.'), source_limit=5, text_limit=6000, context=None):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*-\d+', profile_id):
        raise ValueError('Expected a profile ID such as Glasgow-1333')
    root = Path(root)
    from tools.genealogy.open_profiles import eligibility
    context = load_preflight_context(root) if context is None else context
    rows, origins, checked = (context[k] for k in ('rows', 'origins', 'checked'))
    reason = eligibility(rows.get(profile_id, {}), checked.get(profile_id))
    privacy = {'reason': reason, 'metadata_pointer': origins.get(profile_id)}
    if reason not in ('explicit_nonliving', 'recorded_death', 'historical_birth'):
        return {'profile_id': profile_id, 'father_id': father_id, 'internal_only': True,
                'withheld': True, 'eligibility': privacy,
                'limitations': ['Profile content withheld by existing open-profile eligibility policy.']}
    case = Path('research') / profile_id
    findings = case / 'findings.md'
    output = {'profile_id': profile_id, 'father_id': father_id, 'internal_only': True,
              'withheld': False, 'eligibility': privacy,
              'findings': {'path': str(findings), 'exists': (root / findings).exists(),
                           **findings_sections((root / findings).read_text() if (root / findings).exists() else '', text_limit)}}
    output['biographical_kinship_leads'] = biography_kinship_leads(profile_id, father_id, root=root, context=context)
    for filename, key, fields in [('research_plan.json', 'research_plan', None),
                                   ('presentation.json', 'presentation', ('research_tasks', 'completed_searches'))]:
        path = case / filename
        data = read_json(root / path, {})
        output[key] = {'path': str(path), 'exists': (root / path).exists(), 'pointer': '',
                       **bounded(data if fields is None else {k: data[k] for k in fields if k in data}, text_limit)}
    path = Path('research/relationship_assessments.json')
    pairs = [(i, a) for i, a in enumerate(context['assessments'])
             if a.get('publication_status') == 'approved' and profile_id in a.get('people', [])
             and a.get('perspectives', {}).get(profile_id, {}).get('relationship') == 'father'
             and (not father_id or father_id in a.get('people', []))]
    output['related_parent_account'] = related_parent_account(profile_id, father_id, root=root, context=context)
    output['assessments'] = [{'path': str(path), 'pointer': f'/{i}', **bounded(a, text_limit)} for i, a in pairs]
    path = Path('research/canonical_records.json')
    records = [(i, r) for i, r in enumerate(context['records']) if profile_id in r.get('profiles', {})]
    inventory = []
    pending = []
    for i, record in records:
        needs = record_needs_review(record, profile_id, father_id, [a for _, a in pairs])
        item = {'path': str(path), 'pointer': f'/{i}', 'record_id': record.get('record_id'),
                'linked_parent_record_needs_review': needs, **bounded(record, text_limit)}
        if needs:
            pending.append({'path': str(path), 'pointer': f'/{i}', 'record_id': record.get('record_id')})
        inventory.append(item)
    output['source_inventory'] = {'total': len(inventory), 'items': inventory[:max(0, source_limit)],
                                  'truncated': len(inventory) > max(0, source_limit)}
    output['linked_parent_record_needs_review'] = bool(pending)
    output['pending_source_pointers'] = pending
    output['limitations'] = ['Internal research packet: may contain unpublished plans and records; do not publish this output.',
                             'Inventory only: no parent selection, identity inference or confidence change.',
                             'No fresh source is inferred from dates or file modification times.']
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--father')
    args = parser.parse_args()
    print(json.dumps(build_preflight(args.id, args.father), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
