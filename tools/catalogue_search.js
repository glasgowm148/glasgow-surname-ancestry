(()=>{
  const form=document.querySelector('#catalogue-search');
  if(!form) return;
  const panel=document.querySelector('#catalogue-search-panel');
  const advanced=document.querySelector('.catalogue-advanced');
  const out=document.querySelector('#catalogue-results');
  const count=document.querySelector('#catalogue-results-count');
  const clear=document.querySelector('#catalogue-search-clear');
  const viewResults=document.querySelector('#catalogue-view-results');
  const scriptUrl=document.currentScript&&document.currentScript.src;
  const indexUrl=new URL('../data/catalogue-search-index.json',scriptUrl||window.location.href);
  const ids={
    query:'catalogue-query',exact:'catalogue-exact-name',first:'catalogue-first-name',last:'catalogue-last-name',
    dateType:'catalogue-date-type',from:'catalogue-date-from',to:'catalogue-date-to',spouse:'catalogue-spouse-name',
    father:'catalogue-father-name',mother:'catalogue-mother-name',location:'catalogue-location',
    locationType:'catalogue-location-type',
    excludeDeath:'catalogue-death-exclude',region:'catalogue-region',cluster:'catalogue-cluster',
    recordType:'catalogue-record-type',sourceQuality:'catalogue-source-quality',
    males:'catalogue-males-only',missingFather:'catalogue-missing-father',missingMother:'catalogue-missing-mother',
    missingProfile:'catalogue-missing-profile',needsUpdate:'catalogue-needs-wikitree-update',descendants:'catalogue-has-descendants',
    wives:'catalogue-women-married-glasgow',suffix:'catalogue-has-suffix'
  };
  const controls=Object.fromEntries(Object.entries(ids).map(([key,id])=>[key,document.getElementById(id)]));
  const textParams={q:'query',first:'first',last:'last',dateType:'dateType',from:'from',to:'to',spouse:'spouse',father:'father',mother:'mother',locationType:'locationType',location:'location',excludeDeath:'excludeDeath',region:'region',cluster:'cluster',recordType:'recordType',quality:'sourceQuality'};
  const flagParams={exact:'exact',males:'males',missingFather:'missingFather',missingMother:'missingMother',missingProfile:'missingProfile',needsUpdate:'needsUpdate',descendants:'descendants',wives:'wives',suffix:'suffix'};
  if(advanced&&window.matchMedia('(max-width: 700px)').matches) advanced.open=false;
  const normaliseLiteral=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim();
  const normalise=value=>normaliseLiteral(value).replace(/\b(?:glasco|glascow|glasgo|glascoe|glassco|glassgow|glasow|glasoe|glassgo|glasko)\b/g,'glasgow');
  const normaliseDeath=value=>normalise(value).replace(/\bunited states of america\b|\bu s a\b/g,'united states');
  const relationText=relations=>(relations||[]).map(relation=>relation.name||relation.id||'').join(' ');
  const esc=value=>String(value==null?'':value).replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  const personUrl=person=>new URL(`${encodeURIComponent(person.id)}.html`,scriptUrl||window.location.href).href;
  const wikiLinks=person=>(person.profile_ids||[]).map(id=>`<a href="https://www.wikitree.com/wiki/${encodeURIComponent(id)}">${esc(id)}</a>`).join(' · ')||'No profile yet';
  const relationConfidence=relation=>{
    const treeFallback={'5':'non_biological','10':'uncertain','20':'confident','30':'dna_confirmed'};
    const allowed=new Set(['proved','strongly_supported','probable','possible','disputed','contradicted','dna_confirmed','confident','uncertain','non_biological','unmarked']);
    let key=relation.certainty||treeFallback[String(relation.data_status||'')]||'unmarked';
    if(!allowed.has(key)) key='unmarked';
    const labels={proved:'Documented',strongly_supported:'Supported',probable:'Probable',possible:'Uncertain',disputed:'Disputed',contradicted:'Contradicted',dna_confirmed:'DNA confirmed',confident:'Confident',uncertain:'Uncertain',non_biological:'Non-biological',unmarked:'Unmarked'};
    return {key,label:labels[key],title:relation.certainty_label||labels[key]};
  };
  const relationHtml=(relations,showConfidence=false)=>{
    const values=(relations||[]).filter(relation=>relation.name||relation.id);
    if(!values.length) return '—';
    return values.map(relation=>{
      const id=relation.id||'';
      const name=relation.name||id;
      const confidence=relationConfidence(relation);
      const confidenceHtml=showConfidence?`<small class="catalogue-relation-confidence confidence-${confidence.key}" title="${esc(confidence.title)}"><i aria-hidden="true"></i>${esc(confidence.label)}</small>`:'';
      if(!id) return `<span class="catalogue-relation">${esc(name)}${confidenceHtml}</span>`;
      const idLabel=normalise(name)!==normalise(id)?`<small>${esc(id)}</small>`:'';
      return `<span class="catalogue-relation"><a href="https://www.wikitree.com/wiki/${encodeURIComponent(id)}">${esc(name)}</a>${idLabel}${confidenceHtml}</span>`;
    }).join('');
  };
  let people=[];
  let loadPromise;
  let renderNumber=0;
  let sortMode='relevance';
  let groupLocations=false;
  let groupFamilies=false;
  let locationGroupSort='geography';
  let familyGroupSort='name:asc';
  const collapsedFamilies=new Set();
  let locationLevel='3';
  let timer;

  function setStatus(text,state='ready'){
    count.textContent=text;
    count.dataset.state=state;
  }
  function hasActiveFilter(){
    return Object.values(controls).some(control=>control&&(control.type==='checkbox'?control.checked:Boolean(control.value.trim())));
  }
  function updateClear(){
    clear.disabled=!hasActiveFilter();
  }
  function prepare(source){
    source.forEach(person=>{
      const relations=[relationText(person.spouses),relationText(person.father),relationText(person.mother),relationText(person.children)];
      const identity=[person.name,...(person.profile_ids||[]),...(person.first_names||[]),
        ...(person.last_names_at_birth||[]),...(person.last_names_current||[]),...(person.suffixes||[])];
      person._search=normalise([
        person.name,...(person.profile_ids||[]),...(person.first_names||[]),...(person.last_names_at_birth||[]),
        ...(person.last_names_current||[]),...(person.suffixes||[]),person.birth,person.death,person.birth_location,
        person.death_location,...(person.locations||[]),...(person.location_aliases||[]),...(person.regions||[]),
        ...(person.recorded_in||[]),person.cluster,...(person.clusters||[]),...(person.evidence_terms||[]),person.wikitree_update_summary,
        ...((person.family_roots||[]).flatMap(root=>[root.name,root.id])),...relations
      ].join(' '));
      person._identity=normalise(identity.join(' '));
      person._identityExact=normaliseLiteral(identity.join(' '));
      person._identityExactTokens=new Set(person._identityExact.split(' ').filter(Boolean));
      person._name=normalise(person.name);
      person._nameExact=normaliseLiteral(person.name);
      person._first=normalise((person.first_names||[]).join(' ')||person.name);
      person._last=normalise([...(person.last_names_at_birth||[]),...(person.last_names_current||[])].join(' ')||person.name);
      person._firstExact=normaliseLiteral((person.first_names||[]).join(' ')||person.name);
      person._lastExact=normaliseLiteral([...(person.last_names_at_birth||[]),...(person.last_names_current||[])].join(' ')||person.name);
      person._relations={spouse:normalise(relations[0]),father:normalise(relations[1]),mother:normalise(relations[2])};
      person._location=normalise([...(person.locations||[]),...(person.location_aliases||[]),...(person.regions||[])].join(' '));
      person._birthLocation=normalise(person.birth_location);
      person._deathLocation=normalise(person.death_location);
      person._regions=normalise((person.regions||[]).join(' '));
      person._clusters=normalise((person.clusters||[]).join(' '));
      person._recordTypes=normalise((person.record_types||[]).join(' '));
      person._qualities=normalise((person.source_qualities||[]).join(' '));
    });
    return source;
  }
  function loadPeople(){
    if(loadPromise) return loadPromise;
    setStatus('Loading searchable index…','busy');
    panel.setAttribute('aria-busy','true');
    form.classList.add('is-loading');
    loadPromise=(async()=>{
      const embedded=Array.isArray(window.glasgowPeopleIndex)?window.glasgowPeopleIndex:null;
      if(embedded) return prepare(embedded);
      const response=await fetch(indexUrl,{headers:{Accept:'application/json'}});
      if(!response.ok) throw new Error(`Search index returned ${response.status}`);
      const data=await response.json();
      if(!Array.isArray(data)) throw new Error('Search index has an invalid format');
      return prepare(data);
    })().then(data=>{
      people=data;
      panel.setAttribute('aria-busy','false');
      form.classList.remove('is-loading');
      return data;
    }).catch(error=>{
      panel.setAttribute('aria-busy','false');
      form.classList.remove('is-loading');
      setStatus('Search unavailable','error');
      out.innerHTML=`<p class="notice"><strong>The catalogue search could not load.</strong><br>${esc(error.message)}. Try refreshing the page.</p>`;
      throw error;
    });
    return loadPromise;
  }
  function criteria(){
    let from=parseInt(controls.from.value,10),to=parseInt(controls.to.value,10);
    if(!Number.isFinite(from)) from=null;
    if(!Number.isFinite(to)) to=null;
    if(from!==null&&to!==null&&from>to) [from,to]=[to,from];
    const queryNormaliser=controls.exact.checked?normaliseLiteral:normalise;
    return {
      query:queryNormaliser(controls.query.value).split(' ').filter(Boolean),
      phrase:queryNormaliser(controls.query.value),exact:controls.exact.checked,
      first:normalise(controls.first.value),last:normalise(controls.last.value),
      spouse:normalise(controls.spouse.value),father:normalise(controls.father.value),mother:normalise(controls.mother.value),
      dateType:controls.dateType.value,locationType:controls.locationType.value,
      location:normalise(controls.location.value),region:normalise(controls.region.value),cluster:normalise(controls.cluster.value),
      recordType:normalise(controls.recordType.value),sourceQuality:normalise(controls.sourceQuality.value),
      excluded:String(controls.excludeDeath.value||'').split(/[,;]+/).map(normaliseDeath).map(term=>/^(?:us|america)$/.test(term)?'united states':term).filter(Boolean),from,to
    };
  }
  function matches(person,filters){
    if(filters.exact){
      if(filters.query.some(term=>!person._identityExactTokens.has(term))) return false;
    }else if(filters.query.some(term=>!person._search.includes(term))) return false;
    if(filters.first&&!person._first.includes(filters.first)) return false;
    if(filters.last&&!person._last.includes(filters.last)) return false;
    if(filters.spouse&&!person._relations.spouse.includes(filters.spouse)) return false;
    if(filters.father&&!person._relations.father.includes(filters.father)) return false;
    if(filters.mother&&!person._relations.mother.includes(filters.mother)) return false;
    const locationText=filters.locationType==='birth'?person._birthLocation:filters.locationType==='death'?person._deathLocation:person._location;
    if(filters.location&&!locationText.includes(filters.location)) return false;
    if(filters.region&&!person._regions.includes(filters.region)) return false;
    if(filters.cluster&&!person._clusters.includes(filters.cluster)) return false;
    if(filters.recordType&&!person._recordTypes.includes(filters.recordType)) return false;
    if(filters.sourceQuality&&!person._qualities.includes(filters.sourceQuality)) return false;
    if(filters.excluded.some(term=>normaliseDeath(person.death_location).includes(term))) return false;
    const dateYears=filters.dateType==='birth'?[person.birth_year]:filters.dateType==='death'?[person.death_year]:(person.date_years||[]);
    if((filters.from!==null||filters.to!==null)&&!dateYears.some(year=>Number.isFinite(year)&&(filters.from===null||year>=filters.from)&&(filters.to===null||year<=filters.to))) return false;
    if(controls.males.checked&&String(person.gender).toLowerCase()!=='male') return false;
    if(controls.missingFather.checked&&!person.missing_father) return false;
    if(controls.missingMother.checked&&!person.missing_mother) return false;
    if(controls.missingProfile.checked&&!person.missing_profile) return false;
    if(controls.needsUpdate.checked&&!person.needs_wikitree_update) return false;
    if(controls.descendants.checked&&!(person.descendants>0)) return false;
    if(controls.wives.checked&&!person.woman_married_glasgow) return false;
    if(controls.suffix.checked&&!person.has_suffix) return false;
    return true;
  }
  function relevance(person,filters){
    if(!filters.query.length) return 0;
    let score=0;
    const profileIds=(filters.exact?normaliseLiteral:normalise)((person.profile_ids||[]).join(' '));
    if(profileIds===filters.phrase) score+=180;
    const identity=filters.exact?person._identityExact:person._identity;
    const name=filters.exact?person._nameExact:person._name;
    const first=filters.exact?person._firstExact:person._first;
    const last=filters.exact?person._lastExact:person._last;
    if(name===filters.phrase) score+=120;
    else if(name.includes(filters.phrase)) score+=70;
    filters.query.forEach(term=>{
      const numeric=/^\d{3,4}$/.test(term);
      if(identity.includes(term)) score+=numeric?8:24;
      if(first.includes(term)||last.includes(term)) score+=10;
      if(numeric){
        const year=Number(term);
        if(String(person.birth||'').includes(term)) score+=48;
        else if(String(person.death||'').includes(term)) score+=18;
        else if((person.date_years||[]).includes(year)) score+=10;
      }
      if(person._relations.spouse.includes(term)||person._relations.father.includes(term)||person._relations.mother.includes(term)) score+=12;
      if(person._location.includes(term)) score+=8;
      if(person._clusters.includes(term)) score+=4;
    });
    score+=Math.min(Number(person.record_count)||0,6);
    if(person.has_original_record) score+=4;
    if(person.has_profile) score+=1;
    return score;
  }
  function relationSurname(relations){
    return (relations||[]).map(relation=>{
      const name=relation.name||relation.id||'';
      const birthSurname=name.match(/\(([^)]+)\)/);
      return normalise(birthSurname?birthSurname[1]:(name.split(/\s+/).pop()||''));
    }).filter(Boolean).sort()[0]||'';
  }
  function sortValue(person,key){
    if(key==='name') return person._name;
    if(key==='birth'||key==='death'){
      const text=String(person[key]||'');
      const year=text.match(/\b\d{4}\b/);
      return year?`${year[0]} ${normalise(text)}`:'';
    }
    if(key==='birthLocation') return normalise(person.birth_location);
    if(key==='deathLocation') return normalise(person.death_location);
    if(key==='spouse') return relationSurname(person.spouses);
    if(key==='father') return relationSurname(person.father);
    if(key==='mother') return relationSurname(person.mother);
    if(key==='recorded') return normalise((person.recorded_in||[]).join(' '));
    if(key==='cluster') return normalise(person.cluster);
    if(key==='profile') return normalise((person.profile_ids||[]).join(' '));
    if(key==='significance') return String(Number(person.wikitree_update_significance)||0).padStart(3,'0');
    return '';
  }
  function comparePeople(a,b,filters){
    if(sortMode==='relevance'){
      const order=relevance(b,filters)-relevance(a,filters);
      if(order) return order;
      const records=(Number(b.record_count)||0)-(Number(a.record_count)||0);
      if(records) return records;
      return a._name.localeCompare(b._name,undefined,{numeric:true,sensitivity:'base'});
    }
    const [key,direction]=sortMode.split(':');
    const left=sortValue(a,key),right=sortValue(b,key);
    if(!left&&!right) return a._name.localeCompare(b._name);
    if(!left) return 1;
    if(!right) return -1;
    const order=left.localeCompare(right,undefined,{numeric:true,sensitivity:'base'});
    return (direction==='desc'?-order:order)||a._name.localeCompare(b._name);
  }
  function sortHeader(key,label){
    const active=sortMode.startsWith(`${key}:`);
    const direction=active?(sortMode.endsWith(':asc')?'ascending':'descending'):'none';
    const arrow=active?(sortMode.endsWith(':asc')?'↑':'↓'):'↕';
    return `<th aria-sort="${direction}"><button class="catalogue-sort" type="button" data-sort="${key}">${label}<span aria-hidden="true">${arrow}</span></button></th>`;
  }
  function updateUrl(){
    if(location.protocol==='file:') return;
    const params=new URLSearchParams();
    Object.entries(textParams).forEach(([param,key])=>{if(controls[key].value.trim()) params.set(param,controls[key].value.trim());});
    Object.entries(flagParams).forEach(([param,key])=>{if(controls[key].checked) params.set(param,'1');});
    if(sortMode!=='relevance') params.set('sort',sortMode);
    if(groupLocations) params.set('groupLocation','1');
    if(groupFamilies) params.set('groupFamily','1');
    if(groupLocations&&locationGroupSort!=='geography') params.set('locationSort',locationGroupSort);
    if(groupFamilies&&familyGroupSort!=='name:asc') params.set('familySort',familyGroupSort);
    if(groupLocations&&locationLevel!=='3') params.set('locationLevel',locationLevel);
    const query=params.toString();
    history.replaceState(null,'',`${location.pathname}${query?`?${query}`:''}${location.hash}`);
  }
  function restoreUrl(){
    const params=new URLSearchParams(location.search);
    Object.entries(textParams).forEach(([param,key])=>{const value=params.get(param);if(value!==null) controls[key].value=value;});
    Object.entries(flagParams).forEach(([param,key])=>{controls[key].checked=/^(?:1|true|yes)$/i.test(params.get(param)||'');});
    const requestedSort=params.get('sort');
    if(requestedSort==='family:asc'){
      groupFamilies=true;
      sortMode='birth:asc';
    }else if(requestedSort) sortMode=requestedSort;
    groupLocations=/^(?:1|true|yes)$/i.test(params.get('groupLocation')||'');
    groupFamilies=groupFamilies||/^(?:1|true|yes)$/i.test(params.get('groupFamily')||'');
    if(groupFamilies) groupLocations=false;
    if(['geography','name:asc','name:desc','count:desc','count:asc'].includes(params.get('locationSort'))) locationGroupSort=params.get('locationSort');
    if(['name:asc','count:desc','count:asc','birth:asc','birth:desc'].includes(params.get('familySort'))) familyGroupSort=params.get('familySort');
    if(['1','2','3'].includes(params.get('locationLevel'))) locationLevel=params.get('locationLevel');
  }
  function sortOptions(){
    const options=[['relevance','Best match'],['significance:desc','Update significance'],['name:asc','Name A–Z'],['birth:asc','Birth: oldest first'],['birth:desc','Birth: newest first'],['death:asc','Death: oldest first'],['death:desc','Death: newest first']];
    return options.map(([value,label])=>`<option value="${value}"${sortMode===value?' selected':''}>${label}</option>`).join('');
  }
  function familySortOptions(){
    const options=[['name:asc','Ancestor name A–Z'],['count:desc','Branch size: most people'],['count:asc','Branch size: fewest people'],['birth:asc','Earliest ancestor: oldest first'],['birth:desc','Earliest ancestor: newest first']];
    return options.map(([value,label])=>`<option value="${value}"${familyGroupSort===value?' selected':''}>${label}</option>`).join('');
  }
  function locationSortOptions(){
    const options=[['geography','Geographic order'],['name:asc','Location A–Z'],['name:desc','Location Z–A'],['count:desc','Most people'],['count:asc','Fewest people']];
    return options.map(([value,label])=>`<option value="${value}"${locationGroupSort===value?' selected':''}>${label}</option>`).join('');
  }
  function locationKey(group,level=locationLevel){
    if(level==='1') return group.country;
    if(level==='2') return `${group.country}|${group.area}`;
    return `${group.country}|${group.area}|${group.locality}`;
  }
  function personLocationGroups(person){
    return (person.location_groups&&person.location_groups.length)?person.location_groups:[{
      country:(person.regions||[])[0]||'Region not specified',area:'Area not specified',locality:'Location not specified'
    }];
  }
  function locationRepeat(person,currentKey){
    if(!groupLocations||!currentKey) return '';
    const memberships=new Map();
    personLocationGroups(person).forEach(group=>memberships.set(locationKey(group),group));
    const others=[...memberships.entries()].filter(([key])=>key!==currentKey);
    if(!others.length) return '';
    const label=locationLevel==='1'?'country or region':locationLevel==='2'?'county or area':'locality';
    const title=others.map(([,group])=>[group.country,locationLevel!=='1'&&group.area,locationLevel==='3'&&group.locality].filter(Boolean).join(' · ')).join(' / ');
    return `<small class="catalogue-location-repeat" title="${esc(title)}">Also recorded in ${others.length} other ${label}${others.length===1?'':'s'}</small>`;
  }
  function resultRow(person,currentKey='',groupKind='',familyKey='',collapsed=false){
    const rowClass=groupKind?` class="catalogue-${groupKind}-child"`:'';
    const familyAttributes=familyKey?` data-family-member="${esc(familyKey)}"${collapsed?' hidden':''}`:'';
    const update=person.needs_wikitree_update?`<small class="catalogue-update-badge">Needs WikiTree update · significance ${Number(person.wikitree_update_significance)||0}</small>`:'';
    return `<tr${rowClass}${familyAttributes}><td><a href="${esc(personUrl(person))}"><strong>${esc(person.name)}</strong></a><small class="catalogue-wikitree-id">${wikiLinks(person)}</small>${update}${locationRepeat(person,currentKey)}</td><td>${esc(person.birth||'—')}</td><td>${esc(person.birth_location||'—')}</td><td>${esc(person.death||'—')}</td><td>${esc(person.death_location||'—')}</td><td class="catalogue-family-cell">${relationHtml(person.spouses)}</td><td class="catalogue-family-cell">${relationHtml(person.father,true)}</td><td class="catalogue-family-cell">${relationHtml(person.mother,true)}</td></tr>`;
  }
  function resultCard(person,currentKey='',groupKind='',familyKey='',collapsed=false){
    const locations=[person.birth_location,person.death_location].filter(Boolean).join(' → ')||'Location not supplied';
    const parents=[...(person.father||[]),...(person.mother||[])];
    const familyAttributes=familyKey?` data-family-member="${esc(familyKey)}"${collapsed?' hidden':''}`:'';
    const update=person.needs_wikitree_update?`<small class="catalogue-update-badge">Needs WikiTree update · significance ${Number(person.wikitree_update_significance)||0}</small>`:'';
    return `<article class="catalogue-result-card${groupKind?` catalogue-${groupKind}-child`:''}"${familyAttributes}><h3><a href="${esc(personUrl(person))}">${esc(person.name)}</a></h3>${update}<p class="result-vitals">${esc(person.birth||'Birth unknown')} – ${esc(person.death||'Death unknown')}</p>${locationRepeat(person,currentKey)}<dl><dt>Location</dt><dd>${esc(locations)}</dd><dt>Parents</dt><dd>${relationHtml(parents,true)}</dd><dt>Spouse</dt><dd>${relationHtml(person.spouses)}</dd></dl><details><summary>More catalogue details</summary><dl><dt>Recorded in</dt><dd>${esc((person.recorded_in||[]).join(' / ')||'—')}</dd><dt>Cluster</dt><dd>${esc(person.cluster||'—')}</dd><dt>WikiTree</dt><dd>${wikiLinks(person)}</dd><dt>Evidence</dt><dd>${esc((person.source_qualities||[]).join(', ')||'Unclassified')}</dd></dl></details></article>`;
  }
  function locationBuckets(source){
    const buckets=new Map();
    source.forEach(person=>personLocationGroups(person).forEach(group=>{
      const key=locationKey(group);
      if(!buckets.has(key)) buckets.set(key,{key,country:group.country,area:group.area,locality:group.locality,people:new Map()});
      buckets.get(key).people.set(person.id,person);
    }));
    const countryOrder=['Ireland','Scotland','England','Wales','United Kingdom'];
    return [...buckets.values()].sort((a,b)=>{
      if(locationGroupSort==='count:desc'||locationGroupSort==='count:asc'){
        const order=a.people.size-b.people.size;
        if(order) return locationGroupSort==='count:desc'?-order:order;
      }
      if(locationGroupSort==='name:asc'||locationGroupSort==='name:desc'){
        const order=a.key.localeCompare(b.key,undefined,{numeric:true,sensitivity:'base'});
        if(order) return locationGroupSort==='name:desc'?-order:order;
      }
      const ai=countryOrder.indexOf(a.country),bi=countryOrder.indexOf(b.country);
      return (ai<0?999:ai)-(bi<0?999:bi)||a.country.localeCompare(b.country)||a.area.localeCompare(b.area)||a.locality.localeCompare(b.locality);
    });
  }
  function locationHeading(kind,bucket){
    const parts=[bucket.country,locationLevel!=='1'&&bucket.area,locationLevel==='3'&&bucket.locality].filter(Boolean);
    const path=parts.map((part,index)=>`${index?'<i aria-hidden="true">›</i>':''}<b>${esc(part)}</b>`).join('');
    const level=locationLevel==='1'?'Country / region':locationLevel==='2'?'County / area':'Townland / locality';
    const count=bucket.people.size;
    if(kind==='table') return `<tr class="catalogue-location-group catalogue-location-path-group"><th colspan="8"><span>${level}</span><div class="catalogue-location-path"><strong>${path}</strong><small>${count} individual${count===1?'':'s'}</small></div></th></tr>`;
    return `<h3 class="catalogue-location-card-heading catalogue-location-path-group catalogue-location-path"><span>${level}</span><strong>${path}</strong><small>${count} individual${count===1?'':'s'}</small></h3>`;
  }
  function groupedResults(source){
    const rows=[],cards=[];
    locationBuckets(source).forEach(bucket=>{
      rows.push(locationHeading('table',bucket));
      cards.push(locationHeading('card',bucket));
      bucket.people.forEach(person=>{
        rows.push(resultRow(person,bucket.key,'location'));
        cards.push(resultCard(person,bucket.key,'location'));
      });
    });
    return {rows:rows.join(''),cards:cards.join('')};
  }
  function familyRoot(person){
    return person.family_root||{id:'',name:'Unconnected profiles',catalogue_id:'',birth:'',birth_location:''};
  }
  function familyHeading(kind,root,count,key,collapsed){
    const familyLabel=root.name||'unconnected profiles';
    const toggle=`<button class="catalogue-family-toggle" type="button" data-family-toggle="${esc(key)}" data-family-label="${esc(familyLabel)}" aria-expanded="${collapsed?'false':'true'}" aria-label="${collapsed?'Expand':'Collapse'} ${esc(familyLabel)} branch"><span aria-hidden="true">${collapsed?'▸':'▾'}</span><b>${collapsed?'Expand':'Collapse'} branch</b></button>`;
    if(!root.id){
      const note=`<small>${count} individual${count===1?'':'s'} · no shared exported ancestor; not a family branch</small>`;
      const copy=`<div class="catalogue-family-heading-copy"><span>Unconnected profiles</span>No shared exported parent chain ${note}</div>`;
      if(kind==='table') return `<tr class="catalogue-location-group catalogue-family-group catalogue-family-unconnected" data-family-heading="${esc(key)}"><th colspan="8">${toggle}${copy}</th></tr>`;
      return `<section class="catalogue-location-card-heading catalogue-family-group catalogue-family-unconnected" data-family-heading="${esc(key)}">${toggle}${copy}</section>`;
    }
    const name=root.catalogue_id?`<a href="${esc(personUrl({id:root.catalogue_id}))}">${esc(root.name)}</a>`:esc(root.name);
    const id=root.id?` <small><a href="https://www.wikitree.com/wiki/${encodeURIComponent(root.id)}" target="_blank" rel="noopener noreferrer">${esc(root.id)}</a> · ${count} individual${count===1?'':'s'} in these results</small>`:` <small>· ${count} individual${count===1?'':'s'}</small>`;
    const birth=[root.birth?`Born ${esc(root.birth)}`:'Birth year not recorded',root.birth_location?esc(root.birth_location):'Birthplace not recorded'].join(' · ');
    const vitals=`<small class="catalogue-family-root-vitals">${birth}</small>`;
    const copy=`<div class="catalogue-family-heading-copy"><span>Earliest exported ancestor</span>${name}${id}${vitals}</div>`;
    if(kind==='table') return `<tr class="catalogue-location-group catalogue-family-group" data-family-heading="${esc(key)}"><th colspan="8">${toggle}${copy}</th></tr>`;
    return `<section class="catalogue-location-card-heading catalogue-family-group" data-family-heading="${esc(key)}">${toggle}${copy}</section>`;
  }
  function familyRootYear(root){
    const match=String(root.birth||'').match(/\b(?:1[0-9]|20)\d{2}\b/);
    return match?Number(match[0]):null;
  }
  function compareFamilyGroups(a,b){
    const disconnected=Number(!a.root.id)-Number(!b.root.id);
    if(disconnected) return disconnected;
    const [key,direction]=familyGroupSort.split(':');
    let order=0;
    if(key==='count') order=a.people.length-b.people.length;
    else if(key==='birth'){
      const left=familyRootYear(a.root),right=familyRootYear(b.root);
      if(left===null&&right!==null) return 1;
      if(left!==null&&right===null) return -1;
      order=(left||0)-(right||0);
    }else order=a.root.name.localeCompare(b.root.name,undefined,{numeric:true,sensitivity:'base'});
    if(direction==='desc') order=-order;
    return order||a.root.name.localeCompare(b.root.name,undefined,{numeric:true,sensitivity:'base'})||a.root.id.localeCompare(b.root.id);
  }
  function groupedFamilyResults(source){
    const groups=new Map();
    source.forEach(person=>{
      const root=familyRoot(person),key=root.id||'__unlinked__';
      if(!groups.has(key)) groups.set(key,{root,people:[]});
      groups.get(key).people.push(person);
    });
    const rows=[],cards=[];
    [...groups.values()].sort(compareFamilyGroups).forEach(group=>{
      const key=group.root.id||'__unlinked__',collapsed=collapsedFamilies.has(key);
      rows.push(familyHeading('table',group.root,group.people.length,key,collapsed));
      cards.push(familyHeading('card',group.root,group.people.length,key,collapsed));
      group.people.forEach(person=>{rows.push(resultRow(person,'','family',key,collapsed));cards.push(resultCard(person,'','family',key,collapsed));});
    });
    return {rows:rows.join(''),cards:cards.join('')};
  }
  async function render(options={}){
    const current=++renderNumber;
    updateClear();
    if(!hasActiveFilter()){
      out.innerHTML='';
      viewResults.hidden=true;
      updateUrl();
      try{
        const loaded=await loadPeople();
        if(current===renderNumber) setStatus(`Ready · ${loaded.length.toLocaleString()} people`,'ready');
      }catch(_error){}
      return;
    }
    setStatus('Searching…','busy');
    let source;
    try{source=await loadPeople();}catch(_error){return;}
    if(current!==renderNumber) return;
    const filters=criteria();
    if(!filters.query.length&&sortMode==='relevance') sortMode=controls.needsUpdate.checked?'significance:desc':'birth:asc';
    const found=source.filter(person=>matches(person,filters)).sort((a,b)=>comparePeople(a,b,filters));
    const groupedMode=groupLocations||groupFamilies;
    // Grouping must use the complete filtered population. Slicing first made
    // branch sizes depend on whichever 500 people happened to sort first.
    const shown=groupedMode?found:found.slice(0,500);
    setStatus(`${found.length.toLocaleString()} individual${found.length===1?'':'s'}${!groupedMode&&found.length>shown.length?' · first 500 shown':''}`,'ready');
    viewResults.hidden=!found.length;
    updateUrl();
    if(!found.length){
      out.innerHTML='<p class="notice">No catalogue match. Try removing one filter or broadening the date range.</p>';
      window.dispatchEvent(new CustomEvent('catalogue:zero-results',{detail:{surface:'people',query:controls.query.value}}));
      return;
    }
    const grouped=groupLocations?groupedResults(shown):(groupFamilies?groupedFamilyResults(shown):null);
    const rows=grouped?grouped.rows:shown.map(person=>resultRow(person)).join('');
    const cards=grouped?grouped.cards:shown.map(person=>resultCard(person)).join('');
    const groupSortLabel=groupLocations?'Sort locations':'Sort branches';
    const groupSortChoices=groupLocations?locationSortOptions():familySortOptions();
    out.innerHTML=`<div class="catalogue-result-toolbar"><strong>${found.length.toLocaleString()} result${found.length===1?'':'s'}</strong><div class="catalogue-result-options"><div class="catalogue-group-controls" role="group" aria-label="Group results"><span>Group</span><label class="catalogue-group-toggle"><input id="catalogue-group-locations" type="checkbox"${groupLocations?' checked':''}> Location</label><label class="catalogue-group-toggle"><input id="catalogue-group-families" type="checkbox"${groupFamilies?' checked':''}> Family branch</label></div><label${groupLocations?'':' hidden'}>Location detail <select id="catalogue-location-level"${groupLocations?'':' disabled'}><option value="1"${locationLevel==='1'?' selected':''}>Country</option><option value="2"${locationLevel==='2'?' selected':''}>County / area</option><option value="3"${locationLevel==='3'?' selected':''}>Townland / locality</option></select></label><label${groupedMode?'':' hidden'}>${groupSortLabel} <select id="catalogue-group-sort"${groupedMode?'':' disabled'}>${groupSortChoices}</select></label><label>${groupedMode?'Sort within groups':'Sort results'} <select id="catalogue-result-sort">${sortOptions()}</select></label></div></div><div class="table-wrap catalogue-result-table-wrap"><table class="catalogue-results-table"><thead><tr>${sortHeader('name','Individual')}${sortHeader('birth','Birth')}${sortHeader('birthLocation','Birth location')}${sortHeader('death','Death')}${sortHeader('deathLocation','Death location')}${sortHeader('spouse','Spouse(s)')}${sortHeader('father','Father')}${sortHeader('mother','Mother')}</tr></thead><tbody>${rows}</tbody></table></div><div class="catalogue-result-cards">${cards}</div>`;
    if(options.scroll&&window.matchMedia('(max-width: 800px)').matches){
      if(advanced) advanced.open=false;
      out.scrollIntoView({behavior:'smooth',block:'start'});
    }
  }
  const schedule=()=>{clearTimeout(timer);updateClear();setStatus('Searching…','busy');timer=setTimeout(()=>render(),160);};
  form.addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);sortMode='relevance';render({scroll:true});});
  form.querySelectorAll('input,select').forEach(input=>input.addEventListener(input.type==='checkbox'||input.tagName==='SELECT'?'change':'input',schedule));
  clear.addEventListener('click',()=>{
    form.querySelectorAll('input,select').forEach(input=>{if(input.type==='checkbox') input.checked=false;else input.value='';});
    sortMode='relevance';
    render();
    controls.query.focus();
  });
  viewResults.addEventListener('click',()=>out.scrollIntoView({behavior:'smooth',block:'start'}));
  out.addEventListener('change',event=>{
    if(event.target.id==='catalogue-group-locations'){
      groupLocations=event.target.checked;
      if(groupLocations) groupFamilies=false;
    }
    else if(event.target.id==='catalogue-group-families'){
      groupFamilies=event.target.checked;
      if(groupFamilies) groupLocations=false;
    }
    else if(event.target.id==='catalogue-location-level') locationLevel=event.target.value;
    else if(event.target.id==='catalogue-group-sort'){
      if(groupLocations) locationGroupSort=event.target.value;
      else if(groupFamilies) familyGroupSort=event.target.value;
    }
    else if(event.target.id==='catalogue-result-sort') sortMode=event.target.value;
    else return;
    render();
  });
  out.addEventListener('click',event=>{
    const familyToggle=event.target.closest('button[data-family-toggle]');
    if(familyToggle){
      const key=familyToggle.dataset.familyToggle,collapse=familyToggle.getAttribute('aria-expanded')==='true';
      if(collapse) collapsedFamilies.add(key); else collapsedFamilies.delete(key);
      out.querySelectorAll('[data-family-member]').forEach(item=>{if(item.dataset.familyMember===key) item.hidden=collapse;});
      out.querySelectorAll('button[data-family-toggle]').forEach(button=>{if(button.dataset.familyToggle===key){button.setAttribute('aria-expanded',String(!collapse));button.setAttribute('aria-label',`${collapse?'Expand':'Collapse'} ${button.dataset.familyLabel} branch`);button.querySelector('span').textContent=collapse?'▸':'▾';button.querySelector('b').textContent=collapse?'Expand branch':'Collapse branch';}});
      return;
    }
    const button=event.target.closest('button[data-sort]');
    if(!button) return;
    const key=button.dataset.sort;
    sortMode=sortMode===`${key}:asc`?`${key}:desc`:`${key}:asc`;
    render();
  });
  restoreUrl();
  render();
})();
