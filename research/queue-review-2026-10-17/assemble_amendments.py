"""Integrate reviewed record passages into complete, preserved replacements."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_research_catalog as catalogue
import queue_profile_amendments
from public_privacy import from_sources, public_capture, likely_living

BATCH = Path(__file__).resolve().parent
SCRATCH = ROOT / 'tmp/catalogue-integration-2026-10-17'
START = '<!-- queue-record-integration-2026-10-17:start -->'
END = '<!-- queue-record-integration-2026-10-17:end -->'


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return sha256(value.strip().encode()).hexdigest()


def profile_objects(value, ident):
    if isinstance(value, dict):
        if value.get('Name') == ident and ('bio' in value or 'Biography' in value):
            yield value
        for child in value.values():
            yield from profile_objects(child, ident)
    elif isinstance(value, list):
        for child in value:
            yield from profile_objects(child, ident)


def capture_missing(evidence, entries):
    added = []
    fields = {'Id', 'Name', 'FirstName', 'MiddleName', 'LastNameAtBirth', 'LastNameCurrent',
              'BirthDate', 'DeathDate', 'BirthLocation', 'DeathLocation', 'Privacy',
              'IsLiving', 'Gender', 'DataStatus', 'Father', 'Mother', 'Touched', 'LongName'}
    for ident, reviews in entries.items():
        if (evidence['profiles'].get(ident) or {}).get('biography_wikitext'):
            continue
        paths = set()
        for review in reviews:
            paths.update(str(p).split('#')[0] for p in review.get('sourcepaths', []) + review.get('source_paths', []) if '.json' in str(p))
            capture = review.get('capture') or {}
            if capture.get('path'):
                paths.add(capture['path'])
            if review.get('current_capture_path'):
                paths.add(review['current_capture_path'].split('#')[0])
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'tmp/queue-review-2026-10-17').rglob(f'*{ident}*.json'))
        raw = None
        for value in sorted(paths):
            path = ROOT / value
            if not path.is_file():
                continue
            raw = next(profile_objects(read(path), ident), None)
            if raw:
                break
        if not raw or int(raw.get('Privacy') or 0) < 60 or likely_living(raw):
            raise ValueError(f'Missing approved Open historical capture: {ident}')
        text = (raw.get('bio') or raw.get('Biography') or '').strip()
        evidence['profiles'][ident] = {
            **evidence['profiles'].get(ident, {}), 'profile_id': ident,
            'profile_url': catalogue.WIKITREE_URL + ident, 'privacy': 60,
            'profile_fields': {k: v for k, v in raw.items() if k in fields},
            'biography_wikitext': text, 'captured_at': '2026-10-17',
            'last_updated': raw.get('Touched') or '',
            'evidence_status': 'Public historical WikiTree capture; original records assessed separately.',
            'external_urls': re.findall(r'https?://[^\s<>\]"\'}]+', text),
        }
        added.append(ident)
    return added


def insert(text, passage, placement):
    passage = passage.strip()
    if passage in text:
        return text
    notes = re.search(r'^==\s*Research [Nn]otes\s*==\s*$', text, re.M)
    sources = re.search(r'^==\s*Sources\s*==\s*$', text, re.M | re.I)
    if placement == 'biography':
        position = notes.start() if notes else sources.start() if sources else len(text)
        return text[:position].rstrip() + '\n\n' + passage + '\n\n' + text[position:].lstrip()
    if not notes:
        position = sources.start() if sources else len(text)
        text = text[:position].rstrip() + '\n\n== Research Notes ==\n\n' + text[position:].lstrip()
        notes = re.search(r'^== Research Notes ==\s*$', text, re.M)
    # Put candidate qualifications in Research Notes, before its Sources heading.
    sources = re.search(r'^==\s*Sources\s*==\s*$', text[notes.end():], re.M | re.I)
    position = notes.end() + sources.start() if sources else len(text)
    return text[:position].rstrip() + '\n\n' + passage + '\n\n' + text[position:].lstrip()


def markdown(text):
    text = re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]', lambda m: f'[{m[2]}](https://www.wikitree.com/wiki/{m[1]})', text)
    text = re.sub(r'\[\[([^]]+)\]\]', lambda m: '' if m[1].startswith('Category:') else f'[{m[1]}](https://www.wikitree.com/wiki/{m[1]})', text)
    text = re.sub(r'\[(https?://[^\s\]]+)(?:\s+([^]]+))?\]', lambda m: f'[{m[2] or "Source"}]({m[1]})', text)
    text = re.sub(r'<ref\b[^>]*>(.*?)</ref>', lambda m: ' (' + m[1].strip() + ')', text, flags=re.S)
    text = re.sub(r'<ref\b[^>]*/>', '', text)
    text = re.sub(r'^===\s*(.*?)\s*===$', r'### \1', text, flags=re.M)
    return text.replace("'''", '**').replace("''", '*').strip()


def passage_label(text):
    first = text.splitlines()[0]
    first = re.sub(r'^=+\s*|\s*=+$', '', first)
    first = re.sub(r'<ref\b.*', '', first)
    first = re.sub(r'\[\[(?:[^]|]+\|)?([^]]+)\]\]', r'\1', first)
    first = re.split(r'\.\s|\.<ref', first, 1)[0].strip().rstrip('.')
    first = re.sub(r'^A possible identification concerns\s+', '', first)
    return first if len(first) <= 100 else first[:97].rsplit(' ', 1)[0] + '…'


def main():
    entries = defaultdict(list)
    statuses = defaultdict(list)
    for lane in ('previous-reviewed', 'early-families', 'early-newspapers', 'later-newspapers'):
        path = BATCH / f'amendments/{lane}.json'
        if not path.is_file():
            raise ValueError('Missing amendment lane: ' + lane)
        payload = read(path)
        lane_entries = payload.get('profiles', payload.get('entries', []))
        if isinstance(lane_entries, dict):
            lane_entries = [dict(value, profile_id=ident) for ident, value in lane_entries.items()]
        for entry in lane_entries:
            statuses[entry['profile_id']].append(entry['status'])
            if entry.get('insertions') or entry.get('replacements') or entry.get('necessary_corrections'):
                entries[entry['profile_id']].append(entry)
    evidence = catalogue._load_wikitree_evidence()
    added_captures = capture_missing(evidence, entries)
    if added_captures:
        catalogue.WIKITREE_PROFILE_EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, separators=(',', ':')) + '\n')
    policy = from_sources(evidence)
    # Compare with the pre-integration effective queue on reruns too; otherwise
    # our own summary would be mistaken for the prior outstanding instruction.
    original_loader = queue_profile_amendments.reviewed_amendments
    try:
        queue_profile_amendments.reviewed_amendments = lambda root: {}
        updates = catalogue._load_profile_updates(evidence)
    finally:
        queue_profile_amendments.reviewed_amendments = original_loader
    manifest_path = BATCH / 'catalogue-integration.json'
    manifest = read(manifest_path)
    manifest['profile_updates'] = {}
    report = {'reviewed_on': '2026-10-17', 'captures_added': added_captures, 'profiles': {}}
    for ident, reviews in sorted(entries.items()):
        capture = evidence['profiles'][ident]
        assert public_capture(capture) and not likely_living(capture), ident
        current = (capture.get('biography_wikitext') or '').strip()
        base_path = SCRATCH / f'biography-bases/{ident}.wiki'
        if base_path.exists():
            base = base_path.read_text().strip()
        else:
            base = (updates.get(ident, {}).get('proposed_wikitext') or current).strip()
            base_path.parent.mkdir(parents=True, exist_ok=True)
            base_path.write_text(base + '\n')
        proposed = base
        corrections, passages = [], []
        for review in reviews:
            for replacement in review.get('replacements', []) + review.get('necessary_corrections', []):
                old, new = replacement['old'], replacement['new']
                if old in proposed:
                    proposed = proposed.replace(old, new, 1)
                elif new not in proposed:
                    raise ValueError(f'Stale necessary correction: {ident}: {old[:100]}')
                corrections.append(replacement)
            for addition in review.get('insertions', []):
                text = addition['wikitext'].strip()
                proposed = insert(proposed, text, addition['placement'])
                if text not in passages:
                    passages.append(text)
        if '== Sources ==' not in proposed:
            proposed += '\n\n== Sources ==\n<references />'
        proposed = catalogue._normalise_complete_wikitree_profile(proposed, ident, capture)
        proposed = catalogue._restore_captured_named_ref_definitions(proposed, current, ident)
        missing = catalogue._source_identity_keys(current).keys() - catalogue._source_identity_keys(proposed).keys()
        if missing:
            raise ValueError(f'Replacement loses captured sources: {ident}: {missing}')
        private = policy.contains_private_id(proposed) or policy.contains_private_id(current)
        draft = (Path('data/wikitree/queue-review-2026-10-17') if private else Path('research') / ident) / 'queue-review-2026-10-17.wiki'
        if private:
            draft = Path('data/wikitree/queue-review-2026-10-17') / f'{ident}.wiki'
        (ROOT / draft).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / draft).write_text(proposed.strip() + '\n')
        headings = list(dict.fromkeys(passage_label(text) for text in passages))
        summary = 'Add the cited record account' + ('s' if len(headings) > 1 else '') + ': ' + '; '.join(headings[:3])
        if len(headings) > 3:
            summary += f'; and {len(headings)-3} other record accounts'
        summary += '. Retain the stated identity and relationship limits.'
        previous_summary = read(manifest_path).get('profile_updates', {}).get(ident, {}).get('prior_work_summary')
        if previous_summary is None:
            previous_summary = updates.get(ident, {}).get('work_queue_summary') or updates.get(ident, {}).get('summary') or ''
        if previous_summary and previous_summary != summary and summary not in previous_summary:
            summary = previous_summary + '\n\n' + summary
        manifest['profile_updates'][ident] = {
            'draft_path': str(draft), 'summary': summary, 'work_queue_summary': summary,
            'queued_at': '2026-10-17', 'status': 'OPEN', 'pending': True,
            'findings_path': f'research/{ident}/findings.md',
            'review_ids': sorted({rid for review in reviews for rid in review.get('review_ids', [])} |
                                 {rid for review in reviews for a in review.get('insertions', []) for rid in a.get('review_ids', [])}),
            'private_comparison': private,
            'prior_work_summary': previous_summary,
            **({'public_addition_wikitext': '\n\n'.join(passages)} if private else {}),
        }
        finding = ROOT / f'research/{ident}/findings.md'
        before = finding.read_text() if finding.exists() else f'# {ident} research\n\nLast updated: 17 October 2026\n\n## Current conclusion\n\nThe cited records below are assessed separately from the identity of this profile. The proposed biography preserves those qualifications.\n'
        safe = markdown('\n\n'.join(passages))
        assert not policy.contains_private_id(safe), ident
        section = START + '\n## Record findings and identity limits — 17 October 2026\n\n' + safe + '\n'
        if corrections:
            section += '\n### Corrected interpretation\n\n' + '\n\n'.join(markdown(x['new']) + ' ' + x.get('reason', '') for x in corrections) + '\n'
        section += END
        if START in before:
            before = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: section, before, flags=re.S)
        else:
            before = before.rstrip() + '\n\n' + section + '\n'
        finding.parent.mkdir(parents=True, exist_ok=True); finding.write_text(before)
        report['profiles'][ident] = {'draft_path': str(draft), 'private_comparison': private,
            'current_sha256': digest(current), 'prior_proposed_sha256': digest(base),
            'proposed_sha256': digest(proposed), 'insertions': len(passages), 'corrections': len(corrections),
            'base_characters': len(base), 'proposed_characters': len(proposed),
            'current_sources_preserved': not missing, 'headings': headings}
    report['already_covered'] = sorted(ident for ident, values in statuses.items() if ident not in entries)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    (BATCH / 'amendment-integration.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'profile_amendments': len(entries), 'already_covered': len(report['already_covered']),
                      'private_comparisons': sum(p['private_comparison'] for p in report['profiles'].values()),
                      'captures_added': len(added_captures)}))


if __name__ == '__main__':
    main()
