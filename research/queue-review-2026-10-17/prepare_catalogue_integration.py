"""Reconcile reviewed people with the durable main-catalogue integration input."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BATCH = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def main():
    inventory = read(BATCH / 'main-catalogue-inventory.json')
    suggestions = {p['id']: p for p in read(ROOT / 'www/data/wikitree-new-profile-suggestions.json')['people']}
    subject_path = ROOT / 'research/latest-findings-subjects/subjects.json'
    subject_payload = read(subject_path)
    subjects = {'subject-' + g['slug'] + '-' + p['anchor']: (g, p)
                for g in subject_payload['groups'] for p in g['people']}
    path = BATCH / 'catalogue-integration.json'
    output = read(path) if path.exists() else {'schema_version': 1, 'profile_updates': {}}
    output.update(reviewed_on='2026-10-17', new_people=[])
    # Reported census ages establish historical status and approximate dates;
    # they are not exact births or proof of cross-record identity.
    census_ages = {'peter-mccaughern': 48, 'ellen-elder': 38,
                   'matilda-mulholland': 52, 'caroline-mccaughern': 47,
                   'sara-jane-mccaughern': 45, 'jas-alex-mccaughern': 43, 'geo-mulholland': 14}
    for item in inventory['suggested_subjects']:
        ident = item['subject_id']; suggestion = suggestions[ident]
        group, subject = subjects[ident]
        # Keep parallel newspaper issues and editorial source notes accessible
        # in the complete draft as well as the evidence account.
        draft = subject['wikitext']
        missing_sources = {s['url']: s['title'] for f in subject['facts'] for s in f['sources']
                           if s['url'].startswith(('https://', 'http://')) and s['url'] not in draft}
        if missing_sources:
            draft = draft.replace('<references />', '<references />\n\n' + '\n'.join(
                f'* [{url} {title}].' for url, title in missing_sources.items()), 1)
            draft_path = ROOT / item['draft_path']
            old = draft_path.read_text()
            assert subject['wikitext'] in old, ident
            draft_path.write_text(old.replace(subject['wikitext'], draft, 1))
            subject['wikitext'] = draft
        fields, vitals, event = item['structured_identity'], item['structured_vitals'], item['documentary_event']
        entry = {
            'subject_id': ident, 'catalogue_id': item['proposed_stable_id'], 'name': item['name'],
            'source_subject_url': subject['facts'][0]['sources'][0]['url'],
            'research_subject_url': suggestion['url'], 'draft_path': item['draft_path'],
            'draft_wikitext': draft, 'assessment': suggestion['assessment'],
            'creation_status': item['creation_status'], 'reviewed_at': '2026-10-17',
            'first_names': fields['first_names'], 'last_names_at_birth': [fields['last_name_at_birth']],
            'last_names_current': [], 'gender': fields['gender'] if fields['gender'] in {'Male', 'Female'} else '',
            'birth': (vitals.get('birth') or {}).get('value', ''), 'birth_note': '',
            'death': (vitals.get('death') or {}).get('value', ''),
            'birth_location': (vitals.get('birthplace') or {}).get('value', ''),
            'birth_location_note': (vitals.get('birthplace') or {}).get('basis', ''), 'death_location': '', 'records': [],
        }
        # Preserve middle names in the actual name filters.
        plain_name = item['name'].split(',')[0].split(' of ')[0].strip()
        surname = fields['last_name_at_birth']
        if plain_name.endswith(' ' + surname):
            entry['first_names'] = [plain_name[:-len(surname)].strip()]
        anchor = subject['anchor']
        if anchor in census_ages:
            age = census_ages[anchor]
            entry.update(birth=f'about {1911-age}', birth_note=f'Estimated from the reported age {age} in the 1911 census; exact birth unrecorded.')
            entry['historical_basis'] = {'latest_birth_year': 1911-age,
                                         'source_url': next(s['url'] for f in subject['facts'] for s in f['sources'] if 'census' in s['url'])}
        if 'birthplace County Antrim, directly reported' in subject['minimum_fields']:
            entry.update(birth_location='County Antrim, Ireland', birth_location_note='Reported birthplace in the inspected census.')
        if anchor == 'alexander-elder':
            entry.update(death='1943-01-05', death_location='',
                         historical_basis={'latest_birth_year': 1887, 'source_url': 'https://genealogy.torrens.org/BannValley/church/RasharkinP/graveyard.html'})
            # The 1908 marriage transcript calls him full age (at least 21).
            entry.update(birth='before 1888', birth_note='Upper bound from full age in the 18 June 1908 marriage transcript; exact birth unrecorded.')
        for fact in subject['facts']:
            for source in fact['sources']:
                if not source['url'].startswith(('https://', 'http://')):
                    continue  # related local accounts are navigation, not original citations
                # Every distinct cited record remains independently accessible.
                year = re.search(r'\b(1\d{3}|20\d{2})\b', str(event['year_or_date']))
                entry['records'].append({
                    'year': str(event['year_or_date']), 'filter_year': int(year[1]) if year else None,
                    'family_group': group['title'], 'region': event.get('place') or '',
                    'record_location': event.get('place') or '', 'association': fact['finding'],
                    'note': fact.get('qualification') or '', 'source_title': source['title'],
                    'source_url': source['url'],
                    'source_type': 'Inspected original record' if source.get('original_inspected') else 'Published transcription or historical source',
                    'source_status': '; '.join(filter(None, [fact.get('qualification'), source.get('entry_image_ref')])),
                    'evidence': 'Documented record; identity qualifications retained',
                    'record_precision': 'Documented event context',
                    'location_basis': 'Record location; not automatically a birth or death place',
                })
        output['new_people'].append(entry)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    subject_path.write_text(json.dumps(subject_payload, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'new_people': len(output['new_people']), 'profile_updates': len(output['profile_updates'])}))


if __name__ == '__main__':
    main()
