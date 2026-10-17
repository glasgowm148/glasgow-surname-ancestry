"""Integrate scoped identity reviews; no live WikiTree writes or deployment."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BATCH = Path(__file__).resolve().parent
DATE = '2026-10-17'


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def wiki(text):
    text = re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)', r'[\2 \1]', text)
    return re.sub(r'(?<![\w/\[-])([A-Za-z]+-\d+)(?![\w\]-])', r'[[\1]]', text)


def draft_text(path):
    text = (ROOT / path).read_text()
    block = re.search(r'```(?:wikitext|wiki)?\s*\n(.*?)\n```', text, re.S | re.I)
    if block:
        text = block[1]
    else:
        starts = [text.find(x) for x in ('[[Category:', '== Biography ==') if x in text]
        text = text[min(starts):] if starts else ''
    assert all(x in text for x in ('== Biography ==', '== Sources ==', '<references />', '<ref')), path
    assert len(text) > 250, path
    return text.strip() + '\n'


def record_reviews(person, review):
    output = []
    for index, fact in enumerate(person['facts']):
        finding_id = fact.get('finding_id', 'subject-fact-' + str(index + 1))
        mappings = review.get('record_mappings') or []
        mapping = next((m for m in mappings if m.get('finding_id') == finding_id), None)
        if mapping is None:
            mapping = next((m for m in mappings if m.get('record_index') == index), None)
        # Never flatten a reviewed multi-event mapping into one blanket identity.
        mapping = mapping or (person.get('record_matches', [])[index]
                              if mappings and len(person.get('record_matches', [])) == len(person['facts'])
                              and any('finding_id' in m for m in mappings) else review)
        output.append(dict(finding_id=finding_id, status=mapping.get('status', review['status']),
                           profile_ids=mapping.get('profile_ids', review.get('profile_ids', [])),
                           assessment=mapping.get('assessment', mapping.get('qualification', review['assessment']))))
    return output


def sync_source_indexes(registry, subjects):
    """Carry scoped identities into the original public record collections."""
    path = ROOT / 'surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json'
    opr = read(path)
    for draft in opr['new_drafts']:
        review = registry['reviews'].get('opr-' + '-'.join(map(str, draft['rows'])))
        if not review:
            continue
        if draft['assessment'] != review['assessment']:
            draft.setdefault('assessment_history', []).append(dict(status=draft['status'], assessment=draft['assessment']))
        draft['assessment'] = review['assessment']
        draft['status'] = {'matched': 'MATCHED — existing profiles', 'compatible_candidate': 'HOLD — compatible existing profiles linked',
                           'partly_matched': 'PARTLY MATCHED — separate person assessments',
                           'no_compatible_profile': 'SUGGESTED NEW — complete sourced draft',
                           'unnamed_record': 'RECORD ONLY — insufficient personal identity'}.get(review['status'], draft['status'])
        for row in opr['rows']:
            if row['row'] not in draft['rows']:
                continue
            if row['assessment'] != review['assessment']:
                row.setdefault('assessment_history', []).append(dict(status=row['status'], assessment=row['assessment']))
            row['assessment'] = review['assessment']
            row['status'] = draft['status']
            row['profile_match_reviewed_on'] = review.get('reviewed_on', DATE)
            row['profile_ids'] = review.get('profile_ids', []) if review['status'] == 'matched' else []
            row['candidate_profile_ids'] = review.get('profile_ids', []) if review['status'] != 'matched' else []
    save(path, opr)

    indexed = {}
    for group in subjects['groups']:
        for person in group['people']:
            qid = 'subject-' + group['slug'] + '-' + person['anchor']
            review = registry['reviews'].get(qid, {})
            if not review:
                continue
            matches = {m['finding_id']: m for m in person.get('record_matches', [])}
            for i, fact in enumerate(person['facts']):
                mapping = matches.get(fact.get('finding_id', 'subject-fact-' + str(i + 1)), review)
                for source in fact['sources']:
                    url = source['url'].split('?')[0].rstrip('/')
                    if 'newspapers.com/image/' not in url:
                        continue
                    item = dict(subject_id=qid, name=person['name'], status=mapping.get('status', review['status']),
                                profile_ids=mapping.get('profile_ids', review.get('profile_ids', [])),
                                assessment=mapping.get('assessment', review['assessment']),
                                url='/research/subjects/' + group['slug'] + '/#' + person['anchor'])
                    indexed.setdefault(url, {})[qid] = item
    path = ROOT / 'surname-research/indexes/glasgow-newspaper-review.json'
    newspapers = read(path)
    for row in newspapers['rows']:
        entries = indexed.get(row.get('source_url', '').split('?')[0].rstrip('/'))
        if not entries:
            continue
        entries = list(entries.values())
        if row.get('identity_reviews') == entries:
            continue
        row.setdefault('previous_profile_assessment', {k: row.get(k) for k in ('assessment', 'profile_ids', 'profile_matches', 'reviewed_on')})
        row['identity_reviews'] = entries
        row['profile_ids'] = list(dict.fromkeys(pid for e in entries for pid in e['profile_ids']))
        row['profile_matches'] = [dict(profile_id=pid, confidence='strong' if e['status'] == 'matched' else 'possible',
                                       role=e['name'], basis=e['assessment']) for e in entries for pid in e['profile_ids']]
        row['subject_links'] = [dict(name=e['name'], url=e['url']) for e in entries]
        row['draft_url'] = entries[0]['url']
        row['assessment'] = ' '.join(e['name'] + ': ' + e['assessment'] for e in entries)
        row['profile_match_reviewed_on'] = DATE
    save(path, newspapers)


def main(scopes):
    registry = read(ROOT / 'research/research-queue-matches.json')
    progress = read(BATCH / 'progress.json')
    subjects = read(ROOT / 'research/latest-findings-subjects/subjects.json')
    collections = {g['slug'] for g in subjects['groups']}
    findings = read(ROOT / 'research/latest-findings.json')
    ledger = {f['id']: f for f in findings['findings']}
    overrides = read(ROOT / 'research/research-queue-overrides.json')
    reviews = {}
    for scope in scopes:
        report = read(BATCH / (scope + '.json'))
        expected = {x['row']['id'] for x in read(BATCH / (scope + '-input.json'))['items']}
        assert expected == set(report['baseline_results']), (scope, 'incomplete baseline coverage')
        assert all(r['disposition'] != 'needs_review' for r in report['baseline_results'].values()), scope
        progress['baseline_results'].update(report['baseline_results'])
        for ident, supplied in report['reviews'].items():
            prior = registry['reviews'].get(ident, {})
            review = dict(prior, **supplied, reviewed_on=DATE)
            if supplied.get('canonical_group') in collections:
                # A source collection contains different people. Only the
                # reviewed person key may consolidate its paired draft rows.
                key = supplied.get('canonical_subject') or supplied.get('canonical_person') or ident
                review['canonical_group'] = 'identity:' + supplied['canonical_group'] + ':' + key
                # Retain only explicitly scoped, earlier case groups.
                if not supplied.get('canonical_groups'):
                    earlier = [g for g in prior.get('canonical_groups', []) if g not in collections and not g.startswith('identity:')]
                    review['canonical_groups'] = earlier or [review['canonical_group']]
            review['source_refs'] = supplied.get('source_refs', [])
            review['review_report'] = str((BATCH / (scope + '.json')).relative_to(ROOT))
            if prior and (prior.get('status'), prior.get('profile_ids'), prior.get('assessment')) != (
                    review.get('status'), review.get('profile_ids'), review.get('assessment')):
                history = review.setdefault('previous_reviews', [])
                historical = {k: prior[k] for k in ('status', 'profile_ids', 'assessment', 'reviewed_on', 'source_refs') if k in prior}
                if historical not in history:
                    history.append(historical)
            registry['reviews'][ident] = review
            reviews[ident] = review

    changed_subjects = []
    for group in subjects['groups']:
        for person in group['people']:
            ident = 'subject-' + group['slug'] + '-' + person['anchor']
            review = reviews.get(ident)
            if not review:
                continue
            changed_subjects.append(ident)
            prior_note = person['identity_note']
            if prior_note != review['assessment']:
                person.setdefault('identity_review_history', []).append(dict(
                    previous_status=person['status'], previous_assessment=prior_note, superseded_on=DATE))
            status = review['status']
            labels = {'matched': 'MATCHED — existing profile', 'compatible_candidate': 'CANDIDATE LINKED — identity review complete',
                      'no_compatible_profile': 'SUGGESTED NEW PROFILE — sourced draft',
                      'unnamed_record': 'RECORD ONLY — insufficient personal identity',
                      'disregarded': 'EXCLUDED FROM PROFILE CREATION', 'partly_matched': 'PARTLY MATCHED — separate record identities'}
            person['status'] = labels.get(status, person['status'])
            person['identity_note'] = review['assessment']
            person['candidates'] = [dict(id=pid, reason=review['assessment']) for pid in review.get('profile_ids', [])]
            searches = review.get('searches_performed') or []
            person['duplicate_check'] = [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in searches]
            person['next_test'] = ('Use the linked existing profile with the stated identity qualification; do not create a duplicate. Retain the record-specific source and family questions.'
                                   if review.get('profile_ids') else
                                   'Review the complete sourced suggestion and its recorded duplicate audit before live creation; preserve source-reading and family qualifications.'
                                   if status == 'no_compatible_profile' else
                                   'Retain the source occurrence; no separate person should be created from the available identification.')
            if status == 'no_compatible_profile' and review.get('draft_path'):
                person['wikitext'] = draft_text(review['draft_path'])
                if review['draft_path'] not in person.setdefault('draft_sources', []):
                    person['draft_sources'].append(review['draft_path'])
            else:
                body = person['wikitext']
                current_note = wiki(review['assessment'])
                if current_note not in body and review['assessment'] not in body:
                    if prior_note in body:
                        body = body.replace(prior_note, current_note)
                    else:
                        body = body.replace('== Research Notes ==', '== Research Notes ==\n' + current_note + '\n', 1)
                # Existing evidence remains; older audit text is retained separately above.
                body = re.sub(r'Possible profile identities:.*?(?=\n\n|\n==|$)',
                              lambda _: 'Possible profile identities: ' + (', '.join('[[' + p + ']]' for p in review.get('profile_ids', [])) or 'none identified within the recorded search scope') + '.', body, flags=re.S)
                person['wikitext'] = body
            person['record_matches'] = record_reviews(person, review)
            url = '/research/subjects/' + group['slug'] + '/#' + person['anchor']
            for mapping in person['record_matches']:
                finding = ledger.get(mapping['finding_id'])
                if not finding:
                    continue
                finding.setdefault('profile_match_reviews', {})[person['anchor']] = dict(mapping, reviewed_on=DATE)
                for named in finding.get('people', []):
                    if named.get('draft_url', named.get('url')) != url:
                        continue
                    ids = mapping['profile_ids']
                    if ids:
                        named['id'] = ids[0]
                        named['url'] = '/people/' + ids[0].lower() + '.html' if (ROOT / 'www/people' / (ids[0].lower() + '.html')).exists() else 'https://www.wikitree.com/wiki/' + ids[0]
                        named['draft_url'] = url
                        named['role'] = 'Matched existing profile' if mapping['status'] == 'matched' else 'Tentative existing-profile match; see record assessment'
                    else:
                        named.pop('id', None)
                        named['url'] = url
                        named['role'] = 'Suggested new profile with sourced draft' if status == 'no_compatible_profile' else 'Record retained; insufficient identity for profile creation'

    # Paired draft rows now lead to their complete canonical evidence account.
    all_subjects = {'subject-' + g['slug'] + '-' + p['anchor']: (g, p) for g in subjects['groups'] for p in g['people']}
    for ident, review in reviews.items():
        if not ident.startswith('draft-') or review['status'] != 'superseded':
            continue
        target = review.get('canonical_subject') or review.get('superseded_by')
        if isinstance(target, dict):
            target = target.get('id')
        if target not in all_subjects:
            continue
        group, person = all_subjects[target]
        stem = next((p.stem for p in (ROOT / 'surname-research/new-people').glob('*.md')
                     if 'draft-' + p.stem.lower().replace('_', '-') == ident), None)
        if stem:
            overrides['draft_replacements'][stem] = dict(url='/research/subjects/' + group['slug'] + '/#' + person['anchor'], reason=review['assessment'])

    complete = {'existing_profile', 'new_profile', 'disregarded', 'study'}
    progress['reviewed_items'] = sum(r['disposition'] in complete for r in progress['baseline_results'].values())
    progress['remaining_items'] = progress['baseline_items'] - progress['reviewed_items']
    progress['percent_complete'] = round(100 * progress['reviewed_items'] / progress['baseline_items'], 1)
    progress['reviewed_on'] = DATE
    registry['latest_reviewed_on'] = DATE
    registry['summary'] = dict(Counter(r['status'] for r in registry['reviews'].values()))
    sync_source_indexes(registry, subjects)
    save(ROOT / 'research/research-queue-matches.json', registry)
    save(ROOT / 'research/latest-findings-subjects/subjects.json', subjects)
    save(ROOT / 'research/latest-findings.json', findings)
    save(ROOT / 'research/research-queue-overrides.json', overrides)
    save(BATCH / 'progress.json', progress)
    print(dict(changed_subjects=len(changed_subjects), reviewed=progress['reviewed_items'], remaining=progress['remaining_items']))


if __name__ == '__main__':
    main(sys.argv[1:])
