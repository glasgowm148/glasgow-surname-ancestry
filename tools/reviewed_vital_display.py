"""Project explicitly approved vital displays without changing family links."""
from copy import deepcopy
import json
import re

FIELDS = ('born', 'died', 'year', 'birthDisplay', 'deathDisplay', 'birthplace',
          'deathplace', 'bornApprox', 'birthLocationRegion', 'deathLocationRegion',
          'locationRegion', 'locationLabel', 'locationColor')


def apply(model, site_root, location_for, locations):
    path = site_root / 'assets/research/assessments.json'
    assessments = json.loads(path.read_text()).get('assessments', []) if path.exists() else []
    approved = {a['subject'] for a in assessments
                if a.get('status') == 'approved' and a.get('project_tree_vitals') is True}
    displays = {}
    for person in model['people']:
        if person['id'] not in approved:
            continue
        dossier = json.loads((site_root / 'people' / (person['id'].lower()+'.json')).read_text())
        kinds = {kind for a in dossier.get('research_assessments', [])
                 if a.get('status') == 'approved' and a.get('project_tree_vitals') is True
                 for kind in a.get('vitals', {})}
        fields = {}
        for kind in kinds & {'birth', 'death'}:
            vital = dossier['vitals'][kind]
            date = str(vital.get('date') or '')
            year = re.search(r'(?<!\d)(\d{4})(?!\d)', date)
            if not year or not vital.get('place'):
                raise ValueError('Reviewed tree vital requires a dated, located replacement')
            fields['born' if kind == 'birth' else 'died'] = int(year[1])
            fields[kind+'Display'] = vital.get('display_date') or date
            fields[kind+'place'] = vital['place']
            fields[kind+'LocationRegion'] = location_for(vital['place'])
            if kind == 'birth':
                fields['bornApprox'] = vital.get('status') not in {'certain', 'exact', 'proved', 'confident'}
                fields['year'] = int(year[1])
        birth_region = fields.get('birthLocationRegion', person.get('birthLocationRegion', 'other'))
        region = birth_region if birth_region != 'other' else fields.get('deathLocationRegion', person.get('deathLocationRegion', 'other'))
        if region in locations:
            fields.update(locationRegion=region, locationLabel=locations[region]['label'], locationColor=locations[region]['color'])
        person.update(fields)
        displays[person['id']] = deepcopy(fields)
    model['meta']['reviewedVitalDisplay'] = displays
    return displays


def refresh_family_summaries(model, site_root):
    """Keep existing family summaries consistent with the opted-in reviews."""
    from bs4 import BeautifulSoup
    from tools.repair_site_experience import description, branch_topic_ids, branch_navigation
    displays = model['meta'].get('reviewedVitalDisplay', {})
    if not displays:
        return
    registry_path = site_root/'assets/research/registry.json'
    registry = json.loads(registry_path.read_text())
    people = {p['slug']: p for p in registry}
    old = deepcopy(people)
    for ident, fields in displays.items():
        row = people.get(ident.lower())
        if not row:
            continue
        if 'born' in fields:
            row.update(birth=fields['birthDisplay'],birthPlace=fields['birthplace'],
                       country=fields['birthLocationRegion'], **{'from':fields['born']})
            row['life'] = fields['birthDisplay'] + (' – '+str(row['life'].split(' – ',1)[-1]) if ' – ' in row.get('life','') else '')
    registry_path.write_text(json.dumps(registry,ensure_ascii=False,separators=(',',':'))+'\n')
    packed_path=site_root/'assets/v3/registry-packed.json'
    packed=json.loads(packed_path.read_text());slug_index=packed['fields'].index('slug')
    for row in packed['rows']:
        person=people.get(row[slug_index])
        if person and person['id'] in displays:
            for i,key in enumerate(packed['fields']):
                if key in person:row[i]=person[key]
    packed_path.write_text(json.dumps(packed,ensure_ascii=False,separators=(',',':'))+'\n')
    branches_path=site_root/'assets/research/branches.json'
    branches=json.loads(branches_path.read_text())
    palette=json.loads((site_root/'assets/research/palette.json').read_text())
    records_path=site_root/'assets/research/record-index.json'
    records=json.loads(records_path.read_text()) if records_path.exists() else []
    directory_path=site_root/'assets/research/branches-directory.json'
    directory=json.loads(directory_path.read_text()) if directory_path.exists() else None
    for branch in branches:
        root=branch.get('root')
        if branch.get('kind')!='family' or root not in people or people[root]['id'] not in displays:
            continue
        person=people[root];old_label=branch['label'];old_life=old[root].get('life','')
        branch['label']=person['name']+' · '+person['birth']
        branch['from']=person['from']
        counts={}
        for member in branch['members']:
            country=people.get(member,{}).get('country','other');counts[country]=counts.get(country,0)+1
        branch['countries']=counts
        branch['topic_ids']=branch_topic_ids(branch,set(counts))
        associated=[r for r in records if r.get('p') in branch['members']]
        branch['description']=description(branch,people,associated)+' The reviewed birthplace is '+person['birthPlace']+'. See the linked biography for the reviewed evidence and remaining uncertainty.'
        if directory:
            from tools.build_branches_directory import HUB_BBOXES
            for group in directory['groups']:
                if group['id']!=branch['id']:continue
                group.update(label=branch['label'],summary=branch['description'],area=person['birthPlace'],place=person['birthPlace'],regions=branch['topic_ids'],region=branch['topic_ids'][0],records=branch['record_count'],**{'from':branch['from']})
                bbox=HUB_BBOXES.get(group['region'])
                if bbox:
                    group.update(lat=(bbox[0]+bbox[2])/2,lon=(bbox[1]+bbox[3])/2,precision='region',precision_label='Approximate region centre; exact birthplace unknown')
        path=site_root/'branches'/branch['id']/'index.html'
        page=BeautifulSoup(path.read_text(),'html.parser')
        for text in page.find_all(string=True):
            if text.parent.name in {'script','style'}:continue
            value=str(text).replace(old_label,branch['label'])
            if old_life:value=value.replace(old_life,person['life'])
            if value!=str(text):text.replace_with(value)
        lead=page.select_one('.r-page-head .r-lead')
        if lead:lead.string=branch['description']
        for anchor in page.select('a[href="/people/'+root+'.html"]'):
            for small in anchor.select('small'):
                value=small.get_text()
                if old[root].get('birth'):value=value.replace(old[root]['birth'],person['birth'])
                if old[root].get('birthPlace'):value=value.replace(old[root]['birthPlace'],person['birthPlace'])
                small.string=value
        legend=page.select_one('.r-country-legend')
        if legend:
            legend.clear()
            for country,count in sorted(counts.items(),key=lambda item:-item[1]):
                definition=palette.get(country,palette['other'])
                label=page.new_tag('span',attrs={'class':'r-country','style':'--c:'+definition['color']});label.string=definition['label'];legend.append(label)
                number=page.new_tag('span',attrs={'class':'r-caption'});number.string=str(count);legend.append(number)
        actions=page.select_one('.r-page-head + .r-actions')
        if actions:
            nav=branch_navigation(branch,branches,[b for b in branches if b['kind']=='region'])
            actions.replace_with(BeautifulSoup(nav,'html.parser'))
        for meta in page.select('meta[name="description"],meta[property="og:description"]'):meta['content']=branch['description']
        path.write_text(str(page))
    branches_path.write_text(json.dumps(branches,ensure_ascii=False,separators=(',',':'))+'\n')
    if directory:directory_path.write_text(json.dumps(directory,ensure_ascii=False,separators=(',',':'))+'\n')
