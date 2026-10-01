#!/usr/bin/env python3
"""Backfill documented confidence reviews without inventing earlier grades."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def profile_id(value):
    return re.search(r'([A-Za-z]+-\d+)', value)[0]


def backfill():
    path = ROOT / 'research/latest-findings.json'; ledger = json.loads(path.read_text())
    audit = json.loads((ROOT / 'research/historical-relationship-audit-2026-09-30.json').read_text())
    assessments = json.loads((ROOT / 'research/relationship_assessments.json').read_text())
    records = {r['record_id']: r for r in json.loads((ROOT / 'research/canonical_records.json').read_text())}
    known = {r['id'] for r in ledger['findings']}; added = 0
    for row in audit['additional_exact_uncertain_to_confident'] + audit['unmarked_to_confident']:
        child, parent = profile_id(row['subject']), profile_id(row['relative'])
        assessment = next(a for a in assessments if set(a['people']) == {child, parent})
        ident = 'certainty-review-' + child.lower() + '-' + parent.lower() + '-' + row['date']
        if ident in known: continue
        people = []
        for person_id in (child, parent):
            public = ROOT / ('www/people/' + person_id.lower() + '.json')
            name = json.loads(public.read_text()).get('name', person_id) if public.exists() else person_id
            local = '/people/' + person_id.lower() + '.html'
            people.append(dict(id=person_id, name=name, url=local if (ROOT / ('www' + local)).exists() else 'https://www.wikitree.com/wiki/' + person_id))
        basis = row.get('evidence') or assessment.get('source_summary') or assessment.get('perspectives', {}).get(child, {}).get('reason') or row['evidence_basis']
        citations = []
        for source_id in assessment.get('source_ids', []):
            record = records.get(source_id, {})
            if record.get('source_url', '').startswith('https://'):
                citations.append(dict(title=record.get('association') or basis, url=record['source_url']))
        if not citations:
            if child == 'Glassford-289':
                citations.append(dict(title='Fasti Ecclesiae Scoticanae, vol. III, p. 116', url='https://archive.org/stream/fastiecclesiaesc03scot/fastiecclesiaesc03scot_djvu.txt'))
            elif child == 'Bryse-13':
                citations.append(dict(title='Linlithgow 1613 christening, FamilySearch X1RN-H3Y', url='https://www.familysearch.org/tree/person/details/X1RN-H3Y'))
            elif 'OPR' in basis or 'baptis' in basis.lower() or 'christen' in basis.lower():
                citations.append(dict(title=basis, url='https://www.scotlandspeople.gov.uk/search-records/church-registers'))
            elif 'CC' in basis or 'testament' in basis.lower():
                citations.append(dict(title=basis, url='https://www.scotlandspeople.gov.uk/search-records/legal-records/wills'))
            else:
                citations.append(dict(title='Recorded biography citations and father review: ' + basis, url='https://www.wikitree.com/wiki/' + child))
        qualifier = ('The previous WikiTree father grade was unmarked, not explicitly uncertain. This is the documented move to Confident; no earlier unknown relationship is invented. ' if row['before'] == 'unmarked' else '')
        qualifier += 'Historical confidence review of existing citations; no new source-image inspection is claimed in this backfill. ' + assessment.get('identity_scope', '')
        if assessment['status'] == 'strongly_supported':
            qualifier += ' Confidence rests on the stated supported inference or compiled evidence, rather than a new direct parent clause.'
        entry = dict(id=ident, found_on=row['date'], kind='relationship',
            finding=f"{people[0]['name']}’s father relationship to {people[1]['name']} was recorded as Confident in the dated profile review. {basis}",
            status='confirmed', qualification=qualifier.strip(), people=people, sources=citations,
            detail_url=people[0]['url'] + ('#archive-tools' if people[0]['url'].startswith('/') else ''),
            relationship_changes=[dict(relationship='father', subject=row['subject'], relative=row['relative'], before=row['before'], after='certain', explanation=basis, previous_status_provenance=row['source_refs'])],
            provenance=row['source_refs'] + ['research/historical-relationship-audit-2026-09-30.json'])
        ledger['findings'].append(entry); known.add(ident); added += 1
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2)+'\n'); return added


if __name__ == '__main__':
    print('Added historical certainty reviews:', backfill())
