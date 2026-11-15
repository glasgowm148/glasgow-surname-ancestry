"""Review missing catalogue geography using held structured evidence only.

Classifications are person-place associations, never invented birthplaces.
Prepared decisions enter the authoritative workbench before public projection.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def unknown(value):
    value = str(value or '').strip().casefold()
    return not value or value in {'unspecified', 'unknown'} or value.startswith('location not ')


def memberships(person):
    """Known associations supersede empty-record placeholders, not source facts."""
    if not person.get('records') and not person.get('location_associations'):return []
    rows = [dict(r) for r in person.get('records', []) if not unknown(r.get('record_location'))]
    rows += [dict(record_location=a['place'], region=a['region'],
                  location_id=a.get('location_id', ''), uncertain=True)
             for a in person.get('location_associations', [])]
    if rows:
        known_regions={r['region'] for r in rows if not unknown(r.get('region'))}
        # Empty region on one event is not evidence that a classified person is unlocated.
        if known_regions:
            for r in rows:
                if unknown(r.get('region')):r['region']=''
        return rows
    regions = [r for r in person.get('regions', []) if not unknown(r)]
    if regions:
        return [dict(region=r, record_location='Location not specified') for r in regions]
    return [dict(region='Unspecified', record_location='Location not specified')]


def captured_kin_anchors(person, region_for_location):
    """Original relative fields retained in the already public profile capture."""
    anchors=[]
    for ci,capture in enumerate(person.get('wikitree_evidence',[])):
        for role,relatives in capture.get('relations',{}).items():
            for ri,relative in enumerate(relatives):
                if relative.get('withheld') or relative.get('living') is True:
                    continue
                rid=str(relative.get('id') or f'{ci}:{role}:{ri}')
                for field in ('birth_location','death_location','marriage_location'):
                    place=relative.get(field)
                    reg=region_for_location(place) if not unknown(place) else ''
                    if not reg:continue
                    anchors.append(dict(relative_id=rid,role=role,place=place,region=reg,
                        evidence=dict(catalogue_id=person['catalogue_id'],
                            field=f'wikitree_evidence[{ci}].relations.{role}[{ri}].{field} ({rid})',
                            value=place,url=capture.get('profile_url',''))))
    return anchors


def captured_kin_association(person, region_for_location):
    """Use relatives embedded in held public captures, even outside the export."""
    anchors=captured_kin_anchors(person,region_for_location)
    if not anchors:return []
    # A shared parent locality is more informative than country-only grouping.
    parent_places=defaultdict(set)
    all_places=defaultdict(set)
    for a in anchors:
        all_places[(a['place'],a['region'])].add(a['relative_id'])
        if a['role']=='parents':
            parent_places[(a['place'],a['region'])].add(a['relative_id'])
    agreed=[key for key,ids in parent_places.items() if len(ids)>=2]
    if not agreed:
        regions={a['region'] for a in anchors}
        if len(regions)!=1:return []
        agreed=[key for key,ids in all_places.items() if len(ids)>=2]
        if not agreed:agreed=[(next(iter(regions)),next(iter(regions)))]
    # Prefer a shared locality over its broader country/state suffix.
    agreed=[key for key in agreed if not any(
        key!=other and other[1]==key[1] and other[0].casefold().endswith(', '+key[0].casefold())
        for other in agreed)]
    result=[]
    for place,reg in agreed:
        supporting=[a for a in anchors if a['region']==reg]
        refs=sorted({a['role']+' '+a['relative_id'] for a in supporting})
        result.append(dict(place=place,region=reg,basis_kind='kin',
            basis='Uncertain family-place association from relatives embedded in the saved public profile capture: '+
                '; '.join(refs)+'. Their held locations support this association even when the relatives are outside the catalogue export. No birthplace, residence or event location is asserted for this subject.',
            evidence=[a['evidence'] for a in supporting],record_regions={}))
    return result


def prepare(people, baseline_ids, region_for_location):
    """Read original locations and bounded held-kin routes; never reuse estimates."""
    aliases = {}
    for p in people:
        for key in [p['catalogue_id'], *p.get('profile_ids', [])]:
            aliases[key.casefold()] = p
    def evidence(p, field, value, row=None):
        row = row or {}
        return dict(catalogue_id=p['catalogue_id'], field=field, value=value,
                    record_id=row.get('record_id', ''), url=row.get('source_url', ''))
    def region(place, supplied=''):
        return region_for_location(place) or (supplied if not unknown(supplied) else '')
    own = defaultdict(list)
    for p in people:
        key = p['catalogue_id']
        for r in p.get('records', []):
            place = r.get('record_location')
            reg = region(place, r.get('region')) if not unknown(place) else ''
            if reg:
                own[key].append(dict(place=place, region=reg, basis_kind='own_record',
                    basis='Associated location explicitly carried by this held record; source identity and reliability retain their existing qualifications.',
                    evidence=[evidence(p, 'record_location', place, r)],
                    record_regions={r['record_id']:reg} if unknown(r.get('region')) else {}))
        for field in ('birth_location', 'death_location'):
            place = p.get(field)
            reg = region(place) if not unknown(place) else ''
            if reg:
                own[key].append(dict(place=place, region=reg, basis_kind='own_profile',
                    basis='Location already recorded in the local profile '+field+' field; retained as a profile association, not independently verified.',
                    evidence=[evidence(p, field, place)], record_regions={}))
        for spouse in p.get('spouses', []):
            place = spouse.get('marriage_location')
            reg = region(place) if not unknown(place) else ''
            if reg:
                own[key].append(dict(place=place, region=reg, basis_kind='own_profile',
                    basis='Subject’s own marriage location already attached in the held family fields.',
                    evidence=[evidence(p, 'spouses.marriage_location', place)],record_regions={}))
        for capture in p.get('wikitree_evidence', []):
            for claim in capture.get('location_claims', []):
                place=claim.get('location')
                reg=region(place) if not unknown(place) else ''
                if reg:
                    own[key].append(dict(place=place,region=reg,basis_kind='own_profile',
                        basis='Subject’s '+str(claim.get('event','life event'))+' location in the held public profile capture; '+str(claim.get('status','profile lead'))+'.',
                        evidence=[evidence(p,'wikitree_evidence.location_claims',place)],
                        record_regions={}))
    # Exact entry-level shared URLs can carry a parent/witness's contextual place.
    shared=defaultdict(list)
    for p in people:
        for a in own[p['catalogue_id']]:
            for e in a['evidence']:
                url=e.get('url','')
                if re.search(r'/records/[^/?]+|/ark:/|[?&]id=',url):
                    shared[url].append((p,a))
    # Build direct, non-withheld family adjacency from held catalogue links.
    kin=defaultdict(dict)
    for p in people:
        for role in ('father','mother','spouses','children'):
            for rel in p.get(role,[]):
                target=aliases.get(str(rel.get('id','')).casefold())
                if target and not rel.get('withheld'):
                    kin[p['catalogue_id']][target['catalogue_id']]=role
                    kin[target['catalogue_id']][p['catalogue_id']]='recorded '+role+' counterpart'
    # Captured relatives can carry fields and graph edges missing from the export.
    # These are original held fields, never previously inferred associations.
    captured_places=defaultdict(list)
    for p in people:
        key=p['catalogue_id']
        for capture in p.get('wikitree_evidence',[]):
            for role,relatives in capture.get('relations',{}).items():
                for relative in relatives:
                    rid=str(relative.get('id') or '')
                    if not rid or relative.get('withheld') or relative.get('living') is True:continue
                    target=aliases.get(rid.casefold())
                    node=target['catalogue_id'] if target else 'captured:'+rid.casefold()
                    kin[key][node]=role
                    kin[node][key]='recorded '+role+' counterpart'
        for a in captured_kin_anchors(p,region_for_location):
            target=aliases.get(a['relative_id'].casefold())
            node=target['catalogue_id'] if target else 'captured:'+a['relative_id'].casefold()
            kin[key][node]=a['role']
            kin[node][key]='recorded '+a['role']+' counterpart'
            captured_places[node].append(dict(place=a['place'],region=a['region'],
                basis_kind='own_profile',
                basis='Original profile field for this subject retained as a relative in the saved capture for '+key+'. This is a held profile lead, not newly verified evidence.',
                evidence=[a['evidence']],record_regions={}))
    def original_places(node):
        return own[node]+captured_places[node]
    def farther_kin(key):
        visited={key};frontier=[(key,[key])]
        for depth in range(1,4):
            following=[];anchors=[]
            for node,route in frontier:
                for other in kin[node]:
                    if other in visited:continue
                    visited.add(other)
                    path=route+[other]
                    following.append((other,path))
                    for a in original_places(other):anchors.append((path,a))
            if anchors:
                # Conflicting nearest original anchors stay unresolved.
                regions={a['region'] for _,a in anchors}
                if len(regions)!=1:return []
                reg=next(iter(regions))
                routes=sorted({' → '.join(n.removeprefix('captured:') for n in route) for route,_ in anchors})
                return [dict(place=reg,region=reg,basis_kind='kin',
                    basis='Uncertain broad family-region association from original held fields along '+str(depth)+' relationship steps: '+'; '.join(routes)+'. Captured relatives outside the main export are included. No inferred location is reused and no birthplace, residence or event location is asserted.',
                    evidence=[a_e for _,a in anchors for a_e in a['evidence']]+[
                        dict(catalogue_id=key,field='held_kin_route',value=route) for route in routes],
                    record_regions={})]
            frontier=following
        return []
    decisions=[];unresolved=[]
    for p in people:
        key=p['catalogue_id']
        if key not in baseline_ids or p.get('likely_living'):
            continue
        candidates=original_places(key)
        if not candidates:
            connected=[]
            for row in p.get('records',[]):
                for other,a in shared.get(row.get('source_url',''),[]):
                    if other['catalogue_id']!=key:
                        connected.append({**a,'basis_kind':'shared_record',
                            'basis':'Uncertain contextual association: the exact held entry is also attached to '+other['name']+' ('+other['catalogue_id']+'), whose entry carries this location. This does not establish this subject’s residence or birthplace.',
                            'record_regions':{},'evidence':a['evidence']+[evidence(p,'shared_entry',row.get('source_url',''),row)]})
            candidates=connected
        if not candidates:
            candidates=captured_kin_association(p,region_for_location)
        if not candidates:
            context=[]
            for other_id,role in kin[key].items():
                for a in original_places(other_id):
                    context.append((other_id,role,a))
            # Keep the broadest defensible common country, not a relative's exact street.
            countries={a['region'] for _,_,a in context}
            if len(countries)==1:
                reg=next(iter(countries))
                candidates=[dict(place=reg,region=reg,basis_kind='kin',
                    basis='Uncertain family-location association from directly attached kin: '+ '; '.join(sorted({role+' '+other for other,role,_ in context}))+'. Only their common region is assigned; no birthplace, residence or event location is asserted.',
                    evidence=[e for _,role,a in context for e in a['evidence']],record_regions={})]
        if not candidates:
            candidates=farther_kin(key)
        if not candidates:
            unresolved.append(dict(catalogue_id=key,name=p['name'],reason='No usable original subject, shared-entry or consistent kin location within three held relationship steps, including saved capture relatives. No external lookup performed.'))
            continue
        merged={}
        for a in candidates:
            k=(a['place'],a['region'])
            if k not in merged:
                merged[k]={**a,'catalogue_id':key,'evidence':list(a['evidence']),'record_regions':dict(a['record_regions'])}
            else:
                merged[k]['record_regions'].update(a['record_regions'])
                for e in a['evidence']:
                    if e not in merged[k]['evidence']:merged[k]['evidence'].append(e)
        decisions.extend(merged.values())
    return decisions,unresolved


def project(people, associations):
    changed=[]
    for p in people:
        rows=associations.get(p['catalogue_id'],[])
        if not rows or p.get('likely_living'):continue
        p['location_associations']=rows
        record_regions={rid:(reg,a['place']) for a in rows for rid,reg in a.get('record_regions',{}).items()}
        for r in p.get('records',[]):
            if unknown(r.get('region')) and r.get('record_id') in record_regions and r.get('record_location')==record_regions[r['record_id']][1]:
                r['region']=record_regions[r['record_id']][0]
                r['region_basis']='Reviewed classification from this record’s own explicit location; source wording retained.'
        p['regions']=sorted({r['region'] for r in memberships(p) if not unknown(r.get('region'))})
        p['recorded_in']=sorted({r['record_location'] for r in memberships(p) if not unknown(r.get('record_location'))})
        p['estimated_location']=any(a['basis_kind'] in ('kin','shared_record') for a in rows)
        changed.append(p['catalogue_id'])
    return changed

def association_html(person):
    from html import escape
    rows=person.get('location_associations',[])
    if not rows:return ''
    items=[]
    for a in rows:
        links=[]
        for e in a.get('evidence',[]):
            if e.get('catalogue_id') and e['catalogue_id']!=person.get('catalogue_id'):
                links.append('<a href="/people/'+escape(e['catalogue_id'],quote=True)+'.html">Family / record context</a>')
            if e.get('url','').startswith(('https://','http://')):
                links.append('<a href="'+escape(e['url'],quote=True)+'">Held source reference</a>')
        items.append('<li><strong>'+escape(a['place'])+'</strong> · uncertain association<p>'+escape(a['basis'])+'</p>'+(' · '.join(dict.fromkeys(links)))+'</li>')
    return '<section id="location-associations" class="research-callout"><h2>Reviewed location associations</h2><p>Places supported by held records or family context. These associations do not establish a birthplace or residence. Original event locations remain unchanged.</p><ul>'+''.join(items)+'</ul></section>'


def region_pages(people, location_to_slug, root=ROOT, web=None):
    from html import escape
    from tools.build_research_catalog import _page,_slug,_count_words
    web=Path(web) if web is not None else Path(root)/'www'
    by_region=defaultdict(lambda:defaultdict(dict))
    for p in people:
        rows=memberships(p)
        known={r['region'] for r in rows if not unknown(r.get('region'))}
        for r in rows:
            reg=r.get('region') or 'Unspecified'
            if unknown(reg) and known:continue
            loc=r.get('record_location') or 'Location not specified'
            by_region[reg][loc][p['catalogue_id']]=p
    cards=[]
    for reg,locations in sorted(by_region.items()):
        members={key:p for rows in locations.values() for key,p in rows.items()}
        sections=[]
        for loc,rows in sorted(locations.items()):
            links=' · '.join('<a href="/people/'+p['catalogue_id']+'.html">'+escape(p['name'])+'</a>' for p in sorted(rows.values(),key=lambda p:p['name'].casefold()))
            lid=next((r.get('location_id') for p in rows.values() for r in p['records'] if r.get('record_location')==loc and r.get('location_id') in location_to_slug),None)
            heading=('<a href="/places/'+escape(location_to_slug[lid],quote=True)+'.html">'+escape(loc)+'</a>') if lid else escape(loc)
            sections.append('<section><h2>'+heading+'</h2><p>'+links+'</p></section>')
        route='/people/locations/'+_slug(reg)+'.html'
        body='<p class="kicker">Browse by location</p><h1>'+escape(reg)+'</h1><p class="lede">'+_count_words(len(members),'person','people')+' across '+_count_words(len(locations),'associated place','associated places')+'. Includes reviewed uncertain associations from held records and direct family context. Open a person for the evidence; these are not necessarily birthplaces.</p>'+''.join(sections)
        path=web/route.lstrip('/')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(_page('People associated with '+reg,'People grouped by associated location.',body,route))
        cards.append('<a class="browse-card" href="'+route+'"><strong>'+escape(reg)+'</strong><span>'+_count_words(len(members),'individual','individuals')+' · '+_count_words(len(locations),'location','locations')+'</span></a>')
    return by_region,cards


def sync(root=ROOT):
    from tools.catalogue_location_assessments import load_associations
    from tools.catalogue_search_index import refresh
    root=Path(root);web=root/'www'
    def read(path):return json.loads(path.read_text())
    def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    payload=read(web/'data/people.json')
    people=payload['people']
    associations=load_associations(root,eligible_catalogue_ids={p['catalogue_id'] for p in people})
    changed=project(people,associations)
    write(web/'data/people.json',payload)
    byid={p['catalogue_id']:p for p in people}
    for relative in ('data/catalogue-search-index.json','data/people-index.json','assets/research/search-people.json'):
        path=web/relative
        if not path.exists():continue
        data=read(path);rows=data if isinstance(data,list) else data.get('people',[])
        for row in rows:
            key=str(row.get('catalogue_id') or row.get('slug') or row.get('id') or '').casefold()
            p=byid.get(key)
            if key not in associations or not p:continue
            for field in ('regions','recorded_in'):
                row[field]=p[field]
            # Provenance belongs in the person dossier, not every compact resolver row.
            row.pop('location_associations',None)
            row['locations']=sorted({v for v in [*row.get('locations',[]),*p['recorded_in']] if not unknown(v)})
            row['estimated_location']=bool(row.get('estimated_location') or p.get('estimated_location'))
        write(path,data)
    import csv
    for filename in ('people.csv','records.csv'):
        path=web/'data'/filename
        if not path.exists():continue
        with path.open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle);fields=list(reader.fieldnames);csv_rows=list(reader)
        if filename=='people.csv':
            if 'location_associations' not in fields:fields.append('location_associations')
            for row in csv_rows:
                p=byid.get(row.get('catalogue_id'))
                if not p or p['catalogue_id'] not in associations:continue
                row['regions']=' | '.join(p['regions']);row['recorded_in']=' | '.join(p['recorded_in'])
                row['location_associations']=json.dumps([{k:a[k] for k in ('claim_id','place','region','status','basis_kind')} for a in p['location_associations']],ensure_ascii=False,separators=(',',':'))
        else:
            approved={r['record_id']:r for p in people for r in p['records'] if r.get('region_basis')}
            for row in csv_rows:
                r=approved.get(row.get('record_id'))
                if r and row.get('record_location')==r.get('record_location') and unknown(row.get('region')):row['region']=r['region']
        with path.open('w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(csv_rows)
    full=read(web/'data/catalogue-search-index.json')
    (web/'data/people-index.js').write_text('window.glasgowPeopleIndex='+json.dumps(full,ensure_ascii=False,separators=(',',':'))+';\n')
    for key in changed:
        p=byid[key]
        for relative in (f'people/{key}.json',f'assets/research/people/{key}.json'):
            path=web/relative
            if path.exists():
                data=read(path)
                data['location_associations']=p['location_associations']
                if isinstance(data.get('identity'),dict):
                    data['identity']['locations']=sorted({v for v in [*data['identity'].get('locations',[]),*p['recorded_in']] if not unknown(v)})
                write(path,data)
        path=web/f'people/{key}.html'
        if path.exists():
            text=path.read_text()
            text=re.sub(r'<section id="location-associations".*?</section>','',text,flags=re.S)
            # Place the concise association account before existing evidence sections.
            text=text.replace('</main>',association_html(p)+'</main>',1)
            path.write_text(text)
    locations={r.get('location_id'):re.sub(r'[^a-z0-9]+','-',r.get('location_id','').casefold()).strip('-') for p in people for r in p['records'] if r.get('location_id')}
    region_pages(people,locations,root)
    # Refresh only the two geography panels, preserving unrelated statistics/source markup.
    from bs4 import BeautifulSoup
    from tools.build_research_catalog import _stat_bars,_slug
    artifact=web/'data/catalogue-statistics.json';stats=read(artifact)
    counts=defaultdict(set);places=defaultdict(set)
    for p in people:
        rows=memberships(p)
        if not rows:continue
        for reg in {r['region'] for r in rows if not unknown(r.get('region'))} or {'Unspecified'}:counts[reg].add(p['catalogue_id'])
        for loc in {r['record_location'] for r in rows if not unknown(r.get('record_location'))} or {'Location not specified'}:places[loc].add(p['catalogue_id'])
    from html import escape
    region_values=[(r,len(ids),'<a href="/people/locations/'+_slug(r)+'.html">'+escape(r)+'</a>') for r,ids in counts.items()]
    place_links={r.get('record_location'):_slug(r['location_id']) for p in people for r in p['records'] if r.get('location_id') and not unknown(r.get('record_location'))}
    place_values=[(loc,len(ids),('<a href="/places/'+escape(place_links[loc],quote=True)+'.html">'+escape(loc)+'</a>') if loc in place_links else escape(loc)) for loc,ids in places.items()]
    for values in (region_values,place_values):values.sort(key=lambda v:(-v[1],v[0]))
    soup=BeautifulSoup(stats['html'],'html.parser')
    for title,description,values in [
        ('People by region','Distinct people per associated region, including reviewed uncertain family context. Unspecified means no usable region is held.',region_values),
        ('Most frequent mapped places','Distinct people per associated place, including reviewed uncertain family context. Empty individual event fields do not make a located person unspecified.',place_values)]:
        h=next(h for h in soup.find_all(['h2','h3']) if h.get_text(' ',strip=True)==title)
        panel=h.find_parent('section') or h.find_parent('article')
        replacement=BeautifulSoup(_stat_bars(title,description,values),'html.parser')
        panel.replace_with(replacement)
    stats['html']=str(soup);write(artifact,stats)
    from tools.build_statistics_page import repair
    repair()
    search_result=refresh(web)
    outputs=[web/'data/people.json',web/'data/people.csv',web/'data/records.csv',web/'data/catalogue-search-index.json',web/'data/people-index.json',web/'data/people-index.js',web/'assets/research/search-people.json',artifact,web/'statistics/index.html',web/'data/catalogue-search-fast.json',web/'data/catalogue-search-advanced.json']
    outputs.extend(web/relative for key in changed for relative in (f'people/{key}.json',f'people/{key}.html',f'assets/research/people/{key}.json'))
    outputs.extend((web/'people/locations').glob('*.html'))
    assets=register_outputs(root,outputs)
    return {'classified_people':len(changed),'unlocated_people':len(counts.get('Unspecified',set())),'registered_asset_versions':assets,**search_result}
def register_outputs(root, paths):
    """Version changed derived site assets; never alter earlier asset hashes."""
    from genealogy.store import open_project
    from genealogy.store.assets import register_asset
    root=Path(root).resolve()
    project=open_project(root)
    count=0
    try:
        with project.store.write(actor='catalogue-location-review',tool='catalogue location projection',
                                 source='workbench associated_place assessments',
                                 reason='Register regenerated catalogue location views without altering source captures or earlier asset versions.') as tx:
            seen=set()
            for path in paths:
                path=Path(path)
                if not path.is_file():continue
                relative=path.resolve().relative_to(root).as_posix()
                if relative in seen:continue
                seen.add(relative)
                earlier=project.store.one("SELECT * FROM asset WHERE root='repository' AND path=? ORDER BY rowid DESC LIMIT 1",(relative,))
                if not earlier:continue
                import hashlib
                if hashlib.sha256(path.read_bytes()).hexdigest()==earlier['sha256']:continue
                register_asset(project,tx,path,root='repository',kind='generated',access=earlier['access'],
                    provenance='Derived local website location classification; workbench associated_place claims; 2026-11-15.',
                    supersedes_id=earlier['id'])
                count+=1
    finally:project.store.close()
    return count


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync",action="store_true",help="Project reviewed workbench locations into the local catalogue")
    args=parser.parse_args()
    if args.sync:print(sync())
    else:parser.print_help()
