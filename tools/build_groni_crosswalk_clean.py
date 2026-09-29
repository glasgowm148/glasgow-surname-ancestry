#!/usr/bin/env python3
"""Clean GRONI birth/marriage leads against the subject's death date."""
import csv, json, re
from datetime import date
from pathlib import Path

SRC = Path('surname-research/indexes/groni-birth-marriage-crosswalk-raw-2026-09-23.json')
OUT = Path('surname-research/indexes/groni-birth-marriage-crosswalk-clean-2026-09-23.json')

def parse_date(value):
    if not value:
        return None
    m = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})', str(value), re.I)
    if not m:
        return None
    months = {x.lower(): i for i, x in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'), 1)}
    month = months.get(m.group(2).lower())
    return date(int(m.group(3)), month, int(m.group(1))) if month else None

def year_date(value):
    m = re.search(r'(\d{4})', str(value or ''))
    return date(int(m.group(1)), 1, 1) if m else None

def main():
    data = json.loads(SRC.read_text())
    out = []
    counts = {'death_rows': len(data['rows']), 'birth_leads': 0, 'marriage_leads': 0, 'birth_after_death_excluded': 0, 'marriage_after_death_excluded': 0}
    for row in data['rows']:
        death = row['death_record']; dd = date.fromisoformat(death['death_date'])
        births, marriages, excluded = [], [], []
        for c in row.get('candidate_births', []):
            bd = parse_date(c.get('date_of_birth')) or year_date(c.get('year'))
            if bd and bd > dd:
                counts['birth_after_death_excluded'] += 1
                excluded.append({'type':'birth', 'registration_number':c.get('registration_number'), 'reason':'birth_date_after_death_date'})
            else:
                births.append(c)
        for c in row.get('candidate_marriages', []):
            md = parse_date(c.get('date_of_marriage')) or year_date(c.get('year'))
            if md and md > dd:
                counts['marriage_after_death_excluded'] += 1
                excluded.append({'type':'marriage', 'registration_number':c.get('registration_number'), 'reason':'marriage_date_after_death_date'})
            else:
                marriages.append(c)
        counts['birth_leads'] += len(births); counts['marriage_leads'] += len(marriages)
        out.append({'audit_row': row['audit_row'], 'death_registration_number': death['registration_number'], 'death_date': death['death_date'], 'district': death['district'], 'forename': death['forename_as_supplied'], 'compatible_births': births, 'compatible_marriages': marriages, 'excluded': excluded, 'lead_status': 'birth_and_marriage_leads' if births and marriages else 'birth_leads' if births else 'marriage_leads' if marriages else 'none'})
    result = {'schema_version':'1.0', 'generated_at':'2026-09-23', 'source':str(SRC), 'source_inputs':['Glasgow_births_master.csv (307 rows)', 'GRONI marriage transcription supplied 23 September 2026 (102 rows)', 'GRONI death transcription supplied 23 September 2026 (152 rows)'], 'counts':counts, 'rows':out, 'interpretation':'Birth and marriage entries are indexed leads only; same-name records are not identity conclusions.'}
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(counts))

if __name__ == '__main__': main()
