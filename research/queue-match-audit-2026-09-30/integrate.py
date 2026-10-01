"""Apply reviewed public identity conclusions; raw captures stay outside www."""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
DATE = '2026-09-30'

def load(path):
    return json.loads((ROOT / path).read_text())

def save(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def read_reports():
    older = load(AUDIT / 'older-drafts.json')['rows']
    opr = load(AUDIT / 'scottish-opr.json')['items']
    irish_data = load(AUDIT / 'irish-collateral.json')
    irish = irish_data.get('entries')
    assert isinstance(irish, list), list(irish_data)
    normalized = []
    for name, items in [('older-drafts', older), ('scottish-opr', opr), ('irish-collateral', irish)]:
        for item in items:
            row = dict(item)
            row['id'] = item.get('id', item.get('queue_id'))
            row['assessment'] = item.get('identity_argument', item.get('argument', item.get('assessment')))
            row['exclusions'] = item.get('exclusions', item.get('concrete_exclusions', []))
            row['candidates'] = item.get('candidates', item.get('candidate_public_evidence', []))
            if row['id'] == 'subject-rasharkin-john-elder-marriages-john-elder':
                row['status'] = 'partly_matched'
                row['record_mappings'] = [dict(finding_id=fid, status=status, profile_ids=ids, assessment=row['assessment'])
                    for fid,status,ids in [('new-17sep-8b874ec0e8e2','matched',['Elder-5907']),
                                          ('new-17sep-0652ac06be27','compatible_candidate',['Elder-5907']),
                                          ('new-17sep-5c3f1cfb8d0b','compatible_candidate',['Elder-7230','Elder-4387'])]]
            assert row['id'] and row['assessment'], row.keys()
            row['report'] = f'research/queue-match-audit-2026-09-30/{name}.json'
            normalized.append(row)
    return normalized

def candidate_reasons(row):
    result = {}
    for candidate in row.get('candidates', []):
        pid = candidate.get('profile_id', candidate.get('id'))
        if not pid:
            continue
        reason = candidate.get('argument', candidate.get('identity_argument', candidate.get('reason')))
        if not reason:
            capture = candidate.get('public_capture', candidate.get('fields', {}))
            reason = 'Current public profile compared; ' + row['assessment']
            if capture:
                reason += f" Profile birth {capture.get('BirthDate', 'unknown')}, death {capture.get('DeathDate', 'unknown')}; qualifiers retained in the review."
        result[pid] = reason
    for record in row.get('record_mappings', []):
        for candidate in record.get('candidates', []):
            pid = candidate.get('profile_id', candidate.get('id'))
            if pid:
                result.setdefault(pid, candidate.get('argument', row['assessment']))
    return result

def person_url(pid):
    return '/people/' + pid.lower() + '.html' if (ROOT / 'www/people' / (pid.lower() + '.html')).exists() else 'https://www.wikitree.com/wiki/' + pid

def integrate():
    rows = read_reports()
    registry = load('research/research-queue-matches.json')
    for row in rows:
        registry['reviews'][row['id']] = dict(id=row['id'], status=row['status'],
            profile_ids=list(dict.fromkeys(row['profile_ids'])), assessment=row['assessment'],
            reviewed_on=DATE, source_refs=[row['report']],
            searches_performed=row.get('actual_searches', []))
    baseline = load(AUDIT / 'baseline.json')['rows']
    assert {r['id'] for r in baseline} == set(registry['reviews']), 'Incomplete baseline review'
    assert len(registry['reviews']) == 140
    registry['summary'] = dict(Counter(r['status'] for r in registry['reviews'].values()))
    save('research/research-queue-matches.json', registry)

    subjects = load('research/latest-findings-subjects/subjects.json')
    subjects['reviewed_on'] = DATE
    lookup = {row['id']: row for row in rows}
    findings = load('research/latest-findings.json')
    ledger = {f['id']: f for f in findings['findings']}
    labels = {'matched': 'MATCHED — existing profile', 'already_linked': 'MATCHED — existing profile',
              'partly_matched': 'PARTLY MATCHED — separate record identities',
              'compatible_candidate': 'HOLD — compatible profile linked',
              'no_compatible_profile': 'DRAFT — no compatible profile found',
              'unnamed_record': 'UNNAMED — original needed'}
    for group in subjects['groups']:
        for person in group['people']:
            qid = 'subject-' + group['slug'] + '-' + person['anchor']
            row = lookup[qid]
            if 'prior_identity_review' not in person:
                person['prior_identity_review'] = {k: person.get(k) for k in ('status', 'identity_note', 'candidates', 'next_test')}
            person['status'] = labels[row['status']]
            person['identity_note'] = row['assessment']
            reasons = candidate_reasons(row)
            person['candidates'] = [dict(id=pid, reason=reasons.get(pid, row['assessment'])) for pid in row['profile_ids']]
            person['duplicate_check'] = [f'Public existing-profile search and biography review completed {DATE}. Missing fields or an unproved extra bridge do not exclude a compatible person.']
            person['duplicate_check'] += [str(e.get('reason', e.get('argument', e))) if isinstance(e, dict) else str(e) for e in row.get('exclusions', [])]
            if row['status'] in ('matched', 'already_linked'):
                person['next_test'] = 'Use the existing profile for this record-defined subject. Preserve the stated record and relationship qualifications; no duplicate creation is needed.'
            elif row['status'] in ('compatible_candidate', 'partly_matched'):
                person['next_test'] = 'Compare the linked compatible profiles with the cited record household. Keep the candidates linked while identification remains qualified; do not create a duplicate from missing fields.'
            elif row['status'] == 'no_compatible_profile':
                person['next_test'] = 'The complete sourced record draft is retained. No compatible profile was found within the recorded search scope; review the original and this current duplicate check before any live creation.'
            else:
                person['next_test'] = 'Inspect the original to establish a name and role before attributing this entry to a profile.'
            mappings = row.get('record_mappings') or []
            person['record_matches'] = []
            for fact in person['facts']:
                mapping = next((m for m in mappings if m.get('finding_id') == fact['finding_id']), None)
                if mapping is None and mappings:
                    # A shared-name subject is not a blanket identity across its events.
                    continue
                mapping = mapping or row
                ids = mapping.get('profile_ids', [])
                assessment = mapping.get('identity_argument', mapping.get('assessment', row['assessment']))
                person['record_matches'].append(dict(finding_id=fact['finding_id'], status=mapping['status'], profile_ids=ids, assessment=assessment))
                finding = ledger.get(fact['finding_id'])
                if not finding:
                    continue
                route = '/research/subjects/' + group['slug'] + '/#' + person['anchor']
                for named in finding.get('people', []):
                    if named.get('draft_url', named.get('url')) == route:
                        named['role'] = 'Matched existing profile' if mapping['status'] in ('matched', 'already_linked') else 'Compatible candidate; identity qualified' if ids else 'Sourced record draft; no compatible profile found' if mapping['status'] != 'unnamed_record' else 'Unnamed record subject'
                        if ids:
                            named['id'] = ids[0]
                            named['url'] = person_url(ids[0])
                            named['draft_url'] = route
                        else:
                            named.pop('id', None)
                            named['url'] = route
                finding.setdefault('profile_match_reviews', {})[person['anchor']] = dict(reviewed_on=DATE, status=mapping['status'], profile_ids=ids, assessment=assessment)
                if row['report'] not in finding.setdefault('provenance', []):
                    finding['provenance'].append(row['report'])
            person['wikitext'] = re.sub(r'== Research Notes ==.*?(?=== Sources ==)',
                lambda _: '== Research Notes ==\n' + person['identity_note'] + '\n' +
                    ('Existing profile destinations: ' + ', '.join('[[' + c['id'] + ']]' for c in person['candidates']) + '.\n' if person['candidates'] else '') +
                    person['next_test'] + '\n\n', person['wikitext'], flags=re.S)
    retirements = load(AUDIT / 'older-drafts-retirements.json')
    # Paths in the subject handoff remain durable after the old duplicate is retired.
    for group in subjects['groups']:
        for person in group['people']:
            for index, path in enumerate(person.get('draft_sources', [])):
                if not (ROOT / path).exists() and '1674_Scotland_Didup' in path:
                    replacements = list((ROOT / 'research/latest-findings-subjects/didup-james-1674').glob('*1674*'))
                    assert len(replacements) == 1, replacements
                    person['draft_sources'][index] = str(replacements[0].relative_to(ROOT))
    save('research/latest-findings-subjects/subjects.json', subjects)

    opr_report = load(AUDIT / 'scottish-opr.json')
    opr = load('surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json')
    record_reviews = {r['finding_id']: r for r in opr_report['record_assessments']}
    for record in opr['rows']:
        review = record_reviews.get(record['id'])
        if not review:
            continue
        record.setdefault('prior_identity_review', {k: record.get(k) for k in ('status', 'profile_ids', 'candidate_profile_ids', 'assessment')})
        all_ids = list(dict.fromkeys(review['profile_ids'] + review.get('spouse_profile_ids', [])))
        matched = review['status'] == 'matched'
        record.update(profile_ids=all_ids if matched else [], candidate_profile_ids=[] if matched else all_ids,
                      status=labels[review['status']], assessment=review['identity_argument'], profile_match_reviewed_on=DATE)
        record['next_action'] = 'Use the existing couple. Inspect the original only to refine event type and reading; no new profiles are needed.' if matched else 'Compare the linked record-specific candidates and original household details.' if all_ids else 'Use the sourced record draft; original review remains open.'
        finding = ledger.get(record['id'])
        if finding:
            finding['qualification'] = 'User-supplied official parish index; original image uninspected. The combined index date does not alone distinguish banns from marriage. ' + review['identity_argument']
            finding['people'] = []
            for name, ids in [(record['forename'].title() + ' Glasgow', review['profile_ids']), (record['spouse'], review.get('spouse_profile_ids', []))]:
                if ids:
                    finding['people'].append(dict(id=ids[0], name=name, url=person_url(ids[0]), role='Matched existing profile' if matched else 'Compatible candidate; identity qualified'))
                else:
                    finding['people'].append(dict(name=name, url='/branches/scottish-families/#' + record['id'], role='Record subject; identity unresolved'))
            finding['profile_match_reviews'] = dict(record=dict(reviewed_on=DATE, status=review['status'], profile_ids=all_ids, assessment=review['identity_argument']))
    for draft in opr['new_drafts']:
        row = lookup['opr-' + '-'.join(map(str, draft['rows']))]
        draft.update(status=labels[row['status']], assessment=row['assessment'])
        path = ROOT / draft['path']
        text = path.read_text()
        marker = '<!-- profile-match-review-20260930 -->'
        if marker not in text:
            path.write_text(marker + '\n**Current identity review, 30 September 2026:** ' + row['assessment'] + '\n\n' + text)
    opr['reviewed_at'] = DATE
    opr['conclusion'] = 'All supplied entries retain their original index provenance. The 30 September profile review links exact existing couples and compatible record-specific candidates, keeping unresolved identity and event-type questions explicit.'
    save('surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json', opr)
    save('research/latest-findings.json', findings)
    print(json.dumps(dict(reviewed=len(registry['reviews']), counts=registry['summary'])))

if __name__ == '__main__':
    integrate()
