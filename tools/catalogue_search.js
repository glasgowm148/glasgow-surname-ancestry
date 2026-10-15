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
  const indexUrl=new URL('../data/catalogue-search-fast.json?v=1',scriptUrl||window.location.href);
  const advancedUrl=new URL('../data/catalogue-search-advanced.json?v=1',scriptUrl||window.location.href);
  const workerUrl=new URL('catalogue-worker.js?v=1',scriptUrl||window.location.href);
  const ids={
    query:'catalogue-query',exact:'catalogue-exact-name',name:'catalogue-name',first:'catalogue-first-name',last:'catalogue-last-name',sibling:'catalogue-sibling-name',child:'catalogue-child-name',
    dateType:'catalogue-date-type',from:'catalogue-date-from',to:'catalogue-date-to',spouse:'catalogue-spouse-name',
    father:'catalogue-father-name',mother:'catalogue-mother-name',location:'catalogue-location',
    locationType:'catalogue-location-type',
    excludeDeath:'catalogue-death-exclude',region:'catalogue-region',cluster:'catalogue-cluster',
    recordType:'catalogue-record-type',sourceQuality:'catalogue-source-quality',
    males:'catalogue-males-only',missingFather:'catalogue-missing-father',missingMother:'catalogue-missing-mother',
    missingProfile:'catalogue-missing-profile',needsUpdate:'catalogue-needs-wikitree-update',descendants:'catalogue-has-descendants',
    wives:'catalogue-women-married-glasgow',glasgowBirth:'catalogue-glasgow-at-birth',suffix:'catalogue-has-suffix'
  };
  const controls=Object.fromEntries(Object.entries(ids).map(([key,id])=>[key,document.getElementById(id)]));
  const lastScope=document.getElementById('catalogue-last-scope');
  const totalLabel=document.getElementById('catalogue-total');
  const legacyGender=controls.males;
  let genderInputs=[...form.querySelectorAll('input[name="catalogue-gender"]')];
  if(legacyGender){const label=legacyGender.closest('label');if(label) label.outerHTML='<div class="catalogue-gender-toggle" aria-label="Gender" role="group"><span>Gender</span><label><input name="catalogue-gender" type="radio" value="male"><span>Male</span></label><label><input name="catalogue-gender" type="radio" value="female"><span>Female</span></label><label><input checked name="catalogue-gender" type="radio" value="both"><span>Both</span></label></div>';genderInputs=[...form.querySelectorAll('input[name="catalogue-gender"]')];}
  const selectedGender=()=>genderInputs.find(input=>input.checked)?.value||'both';
  const controlValue=control=>control?String(control.value||''):'';
  const textParams={q:'query',name:'name',first:'first',last:'last',sibling:'sibling',child:'child',dateType:'dateType',from:'from',to:'to',spouse:'spouse',father:'father',mother:'mother',locationType:'locationType',location:'location',excludeLocation:'excludeDeath',region:'region',cluster:'cluster',recordType:'recordType',quality:'sourceQuality'};
  const flagParams={exact:'exact',missingFather:'missingFather',missingMother:'missingMother',missingProfile:'missingProfile',needsUpdate:'needsUpdate',descendants:'descendants',wives:'wives',glasgowBirth:'glasgowBirth',suffix:'suffix'};
  // Search filters start expanded on desktop and mobile; visitors can collapse them.
  const normaliseLiteral=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim();
  const normalise=value=>normaliseLiteral(value).replace(/\b(?:glasco|glascow|glasgo|glascoe|glassco|glassgow|glasow|glasoe|glassgo|glasko)\b/g,'glasgow');
  const canonicalMarriageSurname=value=>{
    const surname=normaliseLiteral(value),key=surname.replace(/[^a-z]/g,'');
    if(new Set(['unknown','notknown','detailswithheld','withheld','private','living']).has(key)) return '';
    return new Set(['cunningham','cuningham','cunninghame','cuninghame','cunyngham','cunynghame','conyngham','conynghame']).has(key)?'cunningham':surname;
  };
  const relationBirthSurname=relation=>{
    const id=String(relation.id||''),profile=id.match(/^(.+)-\d+$/);
    if(profile) return canonicalMarriageSurname(profile[1].replace(/_/g,' '));
    const name=String(relation.name||''),birth=name.match(/\(([^)]+)\)/);
    return canonicalMarriageSurname(birth?birth[1]:(name.split(/\s+/).pop()||''));
  };
  const normaliseDeath=value=>normalise(value).replace(/\bunited states of america\b|\bu s a\b|\busa\b/g,'united states');
  const relationText=relations=>(relations||[]).map(relation=>relation.name||relation.id||'').join(' ');
  const esc=value=>String(value==null?'':value).replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  const personUrl=person=>new URL(`${encodeURIComponent(person.id)}.html`,scriptUrl||window.location.href).href;
  const wikiLinks=person=>(person.profile_ids||[]).map(id=>`<a href="https://www.wikitree.com/wiki/${encodeURIComponent(id)}" target="_blank" rel="noopener noreferrer">${esc(id)}</a>`).join(' · ')||'No profile yet';
  const relationConfidence=relation=>{
    const treeFallback={'5':'non_biological','10':'uncertain','20':'confident','30':'dna_confirmed'};
    const allowed=new Set(['proved','strongly_supported','probable','possible','disputed','contradicted','dna_confirmed','confident','uncertain','non_biological','unmarked']);
    let key=relation.certainty||treeFallback[String(relation.data_status||'')]||'unmarked';
    if(!allowed.has(key)) key='unmarked';
    // Canonical wording: tools/evidence_labels.py (explained at /evidence/).
    const labels={proved:'Documented',strongly_supported:'Strongly supported',probable:'Probable',possible:'Possible',disputed:'Disputed',contradicted:'Contradicted',dna_confirmed:'Tree-marked DNA confirmed',confident:'Tree-marked confident',uncertain:'Uncertain',non_biological:'Tree-marked non-biological',unmarked:'Unassessed'};
    return {key,label:labels[key],title:relation.certainty_label||labels[key]};
  };
  const relationHtml=(relations,showConfidence=false)=>{
    const values=(relations||[]).filter(relation=>relation.name||relation.id);
    if(!values.length) return '—';
    return values.map(relation=>{
      const id=relation.id||'';
      const name=relation.name||id;
      const confidence=relationConfidence(relation);
      const compact=confidence.key==='confident';
      // The label links to its entry in the evidence guide (/evidence/#state-<key>).
      const guideUrl=`/evidence/#state-${confidence.key.replaceAll('_','-')}`;
      const confidenceHtml=showConfidence?`<span class="catalogue-relation-status confidence-${confidence.key}" title="${esc(confidence.title)}" > <a class="ev-label-link" href="${guideUrl}">${compact?'<span aria-hidden="true">✓</span><span class="sr-only">'+esc(confidence.label)+'</span>':esc(confidence.label)}</a></span>`:'';
      const classes=`catalogue-relation${showConfidence?` catalogue-parent confidence-${confidence.key}`:''}`;
      if(!id) return `<span class="${classes}">${esc(name)} ${confidenceHtml}</span>`;
      const idLabel=normalise(name)!==normalise(id)?`<small>${esc(id)}</small>`:'';
      return `<span class="${classes}"><a href="https://www.wikitree.com/wiki/${encodeURIComponent(id)}" target="_blank" rel="noopener noreferrer">${esc(name)}</a> ${confidenceHtml}${idLabel}</span>`;
    }).join('');
  };
  const fieldConfidence=(person,field)=>{
    const key=person.field_statuses?.[field]||'unmarked';
    const labels={certain:'Tree-marked certain',uncertain:'Uncertain',estimated:'Estimated',before:'Before this date',after:'After this date',disputed:'Disputed',contradicted:'Contradicted',unmarked:'Unassessed'};
    return {key:labels[key]?key:'unmarked',label:labels[key]||labels.unmarked};
  };
  const fieldAttributes=(person,field)=>{
    if(!person[field]) return ` data-field="${field}"`;
    const confidence=fieldConfidence(person,field);
    return ` data-field="${field}" class="catalogue-status-cell confidence-${confidence.key}" title="${esc(confidence.label)}"`;
  };
  const fieldHtml=(person,field)=>{
    const value=esc(person[field]||'—');
    return person[field]?`${value}<span class="sr-only"> · ${esc(fieldConfidence(person,field).label)}</span>`:value;
  };
  let people=[];
  let loadPromise;
  let renderNumber=0;
  let sortMode='relevance';
  let legacyNameFilter='';
  let legacyFirstFilter='';
  let legacyLastFilter='';
  let groupLocations=false;
  let groupFamilies=false;
  let groupOneTree=false;
  let resultView='table';
  let birthSurnameOnly='',marriageSurnameOnly='';
  let locationGroupSort='geography';
  let familyGroupSort='name:asc';
  const collapsedFamilies=new Set();
  const collapsedTreePeople=new Set();
  const expandedTreePeople=new Set();
  let treeAncestorDepth='0';
  let treeDescendantDepth='0';
  const treeMobile=window.matchMedia('(max-width: 650px)').matches;
  let treeExpansionDepth=treeMobile?'1':'2';
  let treeEvidenceMode='all';
  let treeFocusId='';
  let treeCompact=treeMobile;
  let treeMatchCursor=-1;
  let treePathMode=false;
  let treeParentPreference='strongest';
  let treeOverlay='none';
  let treeTimeline=false;
  let treeRenderLimit=600;
  const treeFocusHistory=[];
  let storedTreePins=[];try{storedTreePins=JSON.parse(localStorage.getItem('glasgow-tree-pins')||'[]');}catch(_error){}
  const treePinnedPeople=new Set(Array.isArray(storedTreePins)?storedTreePins:[]);
  let treePathCache={key:'',ids:null};
  let locationLevel='3';
  let catalogueMapDataPromise;
  let catalogueMapResizeObserver=null;
  function disconnectCatalogueMap(){
    if(catalogueMapResizeObserver){catalogueMapResizeObserver.disconnect();catalogueMapResizeObserver=null;}
  }
  // Pagination (ungrouped results) and history: committed actions push a
  // history entry; typing only replaces the current one.
  const pageSizes=[25,50,100,250];
  let page=1,perPage=50,pendingPush=false,autoBrowseSort=false;
  let timer;
  let restoreResultsAnchor=location.hash==='#catalogue-results';

  function setStatus(text,state='ready'){
    count.textContent=text;
    count.dataset.state=state;
  }
  function hasActiveFilter(){
    return legacyNameFilter||legacyFirstFilter||legacyLastFilter||birthSurnameOnly||marriageSurnameOnly||selectedGender()!=='both'||Object.entries(controls).some(([key,control])=>control&&key!=='males'&&(control.type==='checkbox'?control.checked:Boolean(control.value.trim())));
  }
  function updateClear(){
    clear.disabled=!hasActiveFilter();
    refreshFilterUi();
  }
  function prepare(source){
    const parentGroups=new Map();
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
      person._lastBirth=normalise((person.last_names_at_birth||[]).join(' '));
      person._lastCurrent=normalise((person.last_names_current||[]).join(' '));
      person._birthLastNames=(person.last_names_at_birth||[]).map(normalise).filter(Boolean);
      person._marriageSurnames=(person.spouses||[]).map(relationBirthSurname).filter(Boolean);
      person._firstExact=normaliseLiteral((person.first_names||[]).join(' ')||person.name);
      person._lastExact=normaliseLiteral([...(person.last_names_at_birth||[]),...(person.last_names_current||[])].join(' ')||person.name);
      person._relations={spouse:normalise(relations[0]),father:normalise(relations[1]),mother:normalise(relations[2])};
      person._nameFilter=normalise([...(person.first_names||[]),...(person.last_names_at_birth||[]),...(person.last_names_current||[])].join(' '));
      person._children=normalise(relationText(person.children));
      person._parentIds=[...(person.father||[]),...(person.mother||[])].map(relation=>normaliseLiteral(relation.id)).filter(Boolean);
      person._parentIds.forEach(parentId=>{if(!parentGroups.has(parentId)) parentGroups.set(parentId,[]);parentGroups.get(parentId).push(person);});
      person._recordLocation=normaliseDeath([...(person.locations||[]),...(person.location_aliases||[]),...(person.regions||[])].join(' '));
      person._birthLocation=normaliseDeath(person.birth_location);
      person._deathLocation=normaliseDeath(person.death_location);
      person._marriageLocation=normaliseDeath([...(person.marriage_locations||[]),...(person.spouses||[]).map(spouse=>spouse.marriage_location)].join(' '));
      person._biography=normaliseDeath(person.biography_text);
      person._location=[person._recordLocation,person._birthLocation,person._deathLocation,person._marriageLocation,person._biography].join(' ');
      person._regions=normalise((person.regions||[]).join(' '));
      person._clusters=normalise((person.clusters||[]).join(' '));
      person._recordTypes=normalise((person.record_types||[]).join(' '));
      person._qualities=normalise((person.source_qualities||[]).join(' '));
    });
    source.forEach(person=>{const siblings=new Map();person._parentIds.forEach(parentId=>(parentGroups.get(parentId)||[]).forEach(sibling=>{if(sibling!==person) siblings.set(sibling.id,sibling);}));person._siblings=normalise([...siblings.values()].flatMap(sibling=>[sibling.name,...(sibling.last_names_current||[]),...(sibling.last_names_at_birth||[])].join(' ')));});
    return source;
  }
  let searchWorker=null,workerSequence=0;
  const workerJobs=new Map(),detailCache=new Map();
  function workerRequest(type,payload={}){
    return new Promise((resolve,reject)=>{
      try{
        if(!searchWorker){searchWorker=new Worker(workerUrl);searchWorker.onmessage=({data})=>{const job=workerJobs.get(data.id);if(!job)return;clearTimeout(job.timer);workerJobs.delete(data.id);data.error?job.reject(Error(data.error)):job.resolve(data.result)};searchWorker.onerror=()=>{for(const job of workerJobs.values()){clearTimeout(job.timer);job.reject(Error('Search worker unavailable'))}workerJobs.clear();searchWorker.terminate();searchWorker=null}};
        const id=++workerSequence,timer=setTimeout(()=>{workerJobs.delete(id);reject(Error('Search timed out. Please retry.'))},15000);workerJobs.set(id,{resolve,reject,timer});searchWorker.postMessage({id,type,...payload});
      }catch(error){reject(error)}
    });
  }
  function unpackSearch(value,strings){if(typeof value==='number'&&value<0)return strings[-value-1];if(Array.isArray(value))return value.map(x=>unpackSearch(x,strings));if(value&&typeof value==='object'){if('number'in value)return value.number;return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,unpackSearch(v,strings)]))}return value}
  async function preparedPeople(useWorker=true){
    if(useWorker&&typeof Worker!=='undefined')try{return await workerRequest('load',{url:indexUrl.href,advancedUrl:advancedUrl.href})}catch(error){searchWorker?.terminate();searchWorker=null;}
    const response=await fetch(indexUrl);if(!response.ok)throw Error(`Search index returned ${response.status}`);
    const payload=await response.json();if(payload.schema_version!==1||!Array.isArray(payload.rows))throw Error('Invalid search index');
    const records=payload.rows.map(row=>{const p=Object.fromEntries(payload.fields.map((k,i)=>[k,unpackSearch(row[i],payload.strings)]));p._identityExactTokens=new Set(p._identityExactTokens);p._sortValues=Object.fromEntries(payload.sort_keys.map((k,i)=>[k,p._sortValues[i]]));p._search='';return p});
    for(const [word,deltas]of Object.entries(payload.search)){let i=0;for(const delta of deltas){i+=delta;records[i]._search+=word+' '}}
    const extra=await fetch(advancedUrl);if(!extra.ok)throw Error('Advanced search unavailable');(await extra.json()).forEach((row,i)=>Object.assign(records[i],row));return records;
  }
  async function hydrateDetails(rows){
    const urls=[...new Set(rows.filter(p=>p._detailShard&&!p._hydrated).map(p=>p._detailShard))];
    await Promise.all(urls.map(async url=>{
      if(!detailCache.has(url))detailCache.set(url,fetch(url).then(r=>{if(!r.ok)throw Error('Person details unavailable');return r.json()}).catch(e=>{detailCache.delete(url);throw e}));
      const details=await detailCache.get(url);const byId=new Map(details.map(p=>[p.id,p]));
      for(const p of rows)if(p._detailShard===url&&byId.has(p.id)){Object.assign(p,byId.get(p.id));p._hydrated=true}
    }));
  }
  function loadPeople(){
    if(loadPromise) return loadPromise;
    setStatus('Loading searchable index…','busy');
    panel.setAttribute('aria-busy','true');
    form.classList.add('is-loading');
    loadPromise=(async()=>{
      const embedded=Array.isArray(window.glasgowPeopleIndex)?window.glasgowPeopleIndex:null;
      if(embedded) return prepare(embedded);
      return preparedPeople();
    })().then(data=>{
      people=data;
      if(totalLabel){
        // The header total comes from the loaded index, so it always matches what is searchable.
        totalLabel.textContent=data.length.toLocaleString();
        const lede=totalLabel.closest('.catalogue-hero')?.querySelector('.lede');
        if(lede) lede.textContent=lede.textContent.replace(/Search [\d,]+ historical/,`Search ${data.length.toLocaleString()} historical`);
      }
      panel.setAttribute('aria-busy','false');
      form.classList.remove('is-loading');
      return data;
    }).catch(error=>{
      panel.setAttribute('aria-busy','false');
      form.classList.remove('is-loading');
      setStatus('Search unavailable','error');
      out.innerHTML=`<p class="notice"><strong>The catalogue search could not load.</strong><br>${esc(error.message)}. Try refreshing the page.</p>`;
      loadPromise=null;
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
      name:normalise(controlValue(controls.name)||legacyNameFilter),first:normalise(controlValue(controls.first)||legacyFirstFilter),last:normalise(controlValue(controls.last)||legacyLastFilter),lastScope:lastScope?lastScope.value:'',sibling:normalise(controlValue(controls.sibling)),child:normalise(controlValue(controls.child)),
      birthSurname:normalise(birthSurnameOnly),
      spouse:marriageSurnameOnly?'':normalise(controls.spouse.value),marriageSurname:canonicalMarriageSurname(marriageSurnameOnly),father:normalise(controls.father.value),mother:normalise(controls.mother.value),
      dateType:controls.dateType.value,locationType:controls.locationType.value,
      location:normaliseDeath(controls.location.value),region:normalise(controls.region.value),cluster:normalise(controls.cluster.value),
      recordType:normalise(controls.recordType.value),sourceQuality:normalise(controls.sourceQuality.value),
      excluded:String(controls.excludeDeath.value||'').split(/[,;]+/).map(normaliseDeath).map(term=>/^(?:us|america)$/.test(term)?'united states':term).filter(Boolean),from,to
    };
  }
  function matches(person,filters){
    if(filters.exact){
      if(filters.query.some(term=>!person._identityExactTokens.has(term))) return false;
    }else if(filters.query.some(term=>!person._search.includes(term))) return false;
    if(filters.name&&!filters.name.split(' ').every(term=>person._nameFilter.includes(term))) return false;
    if(filters.first&&!filters.first.split(' ').every(term=>person._first.includes(term))) return false;
    if(filters.last){
      // Surname scope is additive: unset ('') keeps the original birth-or-current match.
      const surnames=filters.lastScope==='birth'?person._lastBirth:filters.lastScope==='current'?person._lastCurrent:person._last;
      if(!filters.last.split(' ').every(term=>surnames.includes(term))) return false;
    }
    if(filters.sibling&&!filters.sibling.split(' ').every(term=>person._siblings.includes(term))) return false;
    if(filters.child&&!filters.child.split(' ').every(term=>person._children.includes(term))) return false;
    if(filters.birthSurname&&!person._birthLastNames.includes(filters.birthSurname)) return false;
    if(filters.spouse&&!person._relations.spouse.includes(filters.spouse)) return false;
    if(filters.marriageSurname&&(!person._birthLastNames.includes('glasgow')||!person._marriageSurnames.includes(filters.marriageSurname))) return false;
    if(filters.father&&!person._relations.father.includes(filters.father)) return false;
    if(filters.mother&&!person._relations.mother.includes(filters.mother)) return false;
    const locationText=({birth:person._birthLocation,death:person._deathLocation,marriage:person._marriageLocation,bio:person._biography,record:person._recordLocation})[filters.locationType]??person._location;
    if(filters.location&&!locationText.includes(filters.location)) return false;
    if(filters.region&&!person._regions.includes(filters.region)) return false;
    if(filters.cluster&&!person._clusters.includes(filters.cluster)) return false;
    if(filters.recordType&&!person._recordTypes.includes(filters.recordType)) return false;
    if(filters.sourceQuality&&!person._qualities.includes(filters.sourceQuality)) return false;
    if(filters.excluded.some(term=>locationText.includes(term))) return false;
    const dateYears=filters.dateType==='birth'?[person.birth_year]:filters.dateType==='death'?[person.death_year]:(person.date_years||[]);
    if((filters.from!==null||filters.to!==null)&&!dateYears.some(year=>Number.isFinite(year)&&(filters.from===null||year>=filters.from)&&(filters.to===null||year<=filters.to))) return false;
    if(selectedGender()!=='both'&&String(person.gender).toLowerCase()!==selectedGender()) return false;
    if(controls.missingFather.checked&&!person.missing_father) return false;
    if(controls.missingMother.checked&&!person.missing_mother) return false;
    if(controls.missingProfile.checked&&!person.missing_profile) return false;
    if(controls.needsUpdate.checked&&!person.needs_wikitree_update) return false;
    if(controls.descendants.checked&&!(person.descendants>0)) return false;
    if(controls.wives.checked&&!person.woman_married_glasgow) return false;
    if(controls.glasgowBirth.checked&&!person._birthLastNames.includes('glasgow')) return false;
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
    if(person._sortValues&&key in person._sortValues)return person._sortValues[key];
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
    Object.entries(textParams).forEach(([param,key])=>{const control=controls[key];if(control&&control.value.trim()) params.set(param,control.value.trim());});
    if(lastScope&&lastScope.value&&controlValue(controls.last).trim()) params.set('lastScope',lastScope.value);
    if(legacyNameFilter&&!controls.name) params.set('name',legacyNameFilter);
    if(legacyFirstFilter&&!controls.first) params.set('first',legacyFirstFilter);
    if(legacyLastFilter&&!controls.last) params.set('last',legacyLastFilter);
    if(birthSurnameOnly) params.set('birthSurname',birthSurnameOnly);
    if(marriageSurnameOnly) params.set('marriageSurname',marriageSurnameOnly);
    Object.entries(flagParams).forEach(([param,key])=>{const control=controls[key];if(control&&control.checked) params.set(param,'1');});
    if(selectedGender()!=='both') params.set('gender',selectedGender());
    if(sortMode!=='relevance') params.set('sort',sortMode);
    if(groupLocations) params.set('groupLocation','1');
    if(groupFamilies) params.set('groupFamily','1');
    if(groupOneTree) params.set('groupTree','1');
    if(groupOneTree&&treeAncestorDepth!=='0') params.set('treeAncestors',treeAncestorDepth);
    if(groupOneTree&&treeDescendantDepth!=='0') params.set('treeDescendants',treeDescendantDepth);
    if(groupOneTree&&treeExpansionDepth!==(treeMobile?'1':'2')) params.set('treeExpand',treeExpansionDepth);
    if(groupOneTree&&treeEvidenceMode!=='all') params.set('treeEvidence',treeEvidenceMode);
    if(groupOneTree&&treeFocusId) params.set('treeFocus',treeFocusId);
    if(groupOneTree&&treeCompact) params.set('treeCompact','1');
    if(groupOneTree&&treePathMode) params.set('treePaths','1');
    if(groupOneTree&&treeParentPreference!=='strongest') params.set('treeParent',treeParentPreference);
    if(groupOneTree&&treeOverlay!=='none') params.set('treeOverlay',treeOverlay);
    if(groupOneTree&&treeTimeline) params.set('treeTimeline','1');
    if(resultView==='map') params.set('view','map');
    if(groupOneTree&&expandedTreePeople.size) params.set('treeExpanded',[...expandedTreePeople].slice(0,40).join(','));
    if(groupOneTree&&collapsedTreePeople.size) params.set('treeCollapsed',[...collapsedTreePeople].slice(0,40).join(','));
    if(groupLocations&&locationGroupSort!=='geography') params.set('locationSort',locationGroupSort);
    if(groupFamilies&&familyGroupSort!=='name:asc') params.set('familySort',familyGroupSort);
    if(groupLocations&&locationLevel!=='3') params.set('locationLevel',locationLevel);
    if(page>1) params.set('page',String(page));
    if(perPage!==50) params.set('perPage',String(perPage));
    if(autoBrowseSort) params.delete('sort');
    const query=params.toString();
    const next=`${location.pathname}${query?`?${query}`:''}${location.hash}`;
    if(pendingPush&&next!==`${location.pathname}${location.search}${location.hash}`) history.pushState(null,'',next);
    else history.replaceState(null,'',next);
    pendingPush=false;
    dispatchEvent(new Event('catalogue:filters-changed'));
  }
  function restoreUrl(){
    const params=new URLSearchParams(location.search);
    Object.entries(textParams).forEach(([param,key])=>{const control=controls[key];if(!control) return;const value=params.get(param);if(value!==null) control.value=value;});
    // Restore older death-exclusion bookmarks using their original scope.
    if(params.has('excludeDeath')&&!params.has('excludeLocation')){controls.excludeDeath.value=params.get('excludeDeath');if(!params.has('locationType')) controls.locationType.value='death';}
    if(!controls.name&&params.get('name')&&!params.has('first')&&!params.has('last')) legacyNameFilter=normalise(params.get('name')||'');
    if(!controls.first&&params.get('first')) legacyFirstFilter=normalise(params.get('first')||'');
    if(!controls.last&&params.get('last')) legacyLastFilter=normalise(params.get('last')||'');
    if(lastScope) lastScope.value=['birth','current'].includes(params.get('lastScope'))?params.get('lastScope'):'';
    birthSurnameOnly=params.get('birthSurname')||'';
    marriageSurnameOnly=params.get('marriageSurname')||'';
    if(marriageSurnameOnly&&controls.spouse) controls.spouse.value=marriageSurnameOnly;
    Object.entries(flagParams).forEach(([param,key])=>{const control=controls[key];if(control) control.checked=/^(?:1|true|yes)$/i.test(params.get(param)||'');});
    const requestedGender=params.get('gender')||(params.has('males')?'male':'both');
    genderInputs.forEach(input=>{input.checked=input.value===requestedGender;});
    const requestedPage=parseInt(params.get('page')||'1',10);
    page=Number.isFinite(requestedPage)&&requestedPage>0?requestedPage:1;
    perPage=pageSizes.includes(Number(params.get('perPage')))?Number(params.get('perPage')):50;
    const requestedSort=params.get('sort');
    if(requestedSort==='family:asc'){
      groupFamilies=true;
      sortMode='birth:asc';
    }else if(requestedSort) sortMode=requestedSort;
    groupLocations=/^(?:1|true|yes)$/i.test(params.get('groupLocation')||'');
    groupFamilies=groupFamilies||/^(?:1|true|yes)$/i.test(params.get('groupFamily')||'');
    groupOneTree=/^(?:1|true|yes)$/i.test(params.get('groupTree')||'');
    resultView=params.get('view')==='map'?'map':'table';
    if(groupOneTree){groupLocations=false;groupFamilies=false;}
    else if(groupFamilies) groupLocations=false;
    if(['geography','name:asc','name:desc','count:desc','count:asc'].includes(params.get('locationSort'))) locationGroupSort=params.get('locationSort');
    if(['name:asc','count:desc','count:asc','birth:asc','birth:desc'].includes(params.get('familySort'))) familyGroupSort=params.get('familySort');
    if(['1','2','3'].includes(params.get('locationLevel'))) locationLevel=params.get('locationLevel');
    if(['0','1','2','3','4','all'].includes(params.get('treeAncestors'))) treeAncestorDepth=params.get('treeAncestors');
    if(['0','1','2','3','4','all'].includes(params.get('treeDescendants'))) treeDescendantDepth=params.get('treeDescendants');
    if(['0','1','2','3','4','all'].includes(params.get('treeExpand'))) treeExpansionDepth=params.get('treeExpand');
    if(['all','supported','documented'].includes(params.get('treeEvidence'))) treeEvidenceMode=params.get('treeEvidence');
    treeFocusId=params.get('treeFocus')||'';
    if(params.has('treeCompact')) treeCompact=/^(?:1|true|yes)$/i.test(params.get('treeCompact')||'');
    treePathMode=/^(?:1|true|yes)$/i.test(params.get('treePaths')||'');
    if(['strongest','father','mother'].includes(params.get('treeParent'))) treeParentPreference=params.get('treeParent');
    if(['none','sourced','unsourced','questions','missing-parent','uncertain','update'].includes(params.get('treeOverlay'))) treeOverlay=params.get('treeOverlay');
    treeTimeline=/^(?:1|true|yes)$/i.test(params.get('treeTimeline')||'');
    String(params.get('treeExpanded')||'').split(',').filter(Boolean).slice(0,40).forEach(id=>expandedTreePeople.add(id));
    String(params.get('treeCollapsed')||'').split(',').filter(Boolean).slice(0,40).forEach(id=>collapsedTreePeople.add(id));
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
  function treeDepthOptions(selected,zeroLabel='None'){
    return [['0',zeroLabel],['1','1 generation'],['2','2 generations'],['3','3 generations'],['4','4 generations'],['all','All available']]
      .map(([value,label])=>`<option value="${value}"${selected===value?' selected':''}>${label}</option>`).join('');
  }
  function treeEvidenceOptions(){
    return [['all','All exported links'],['supported','Supported or stronger'],['documented','Documented only']]
      .map(([value,label])=>`<option value="${value}"${treeEvidenceMode===value?' selected':''}>${label}</option>`).join('');
  }
  function treeRelationAllowed(relation){
    if(treeEvidenceMode==='all') return true;
    const key=relationConfidence(relation).key;
    const documented=new Set(['proved','strongly_supported','dna_confirmed']);
    if(treeEvidenceMode==='documented') return documented.has(key);
    return documented.has(key)||new Set(['probable','confident']).has(key);
  }
  function treeConfidenceRank(relation){
    return ({dna_confirmed:7,proved:6,strongly_supported:5,confident:4,probable:3,unmarked:2,possible:1,uncertain:1,non_biological:1,disputed:0,contradicted:-1})[relationConfidence(relation).key]||0;
  }
  function treeResearchState(person){
    const sourced=Boolean(person.has_original_record)||(person.source_qualities||[]).some(value=>normalise(value).includes('original'));
    const states={sourced,unsourced:!sourced,questions:Boolean(person.has_open_questions),'missing-parent':Boolean(person.missing_father||person.missing_mother),uncertain:Boolean(person.uncertain_identity),update:Boolean(person.needs_wikitree_update)};
    const labels=[];
    if(sourced) labels.push(['sourced','Sourced']);else labels.push(['unsourced','No original source']);
    if(states.questions) labels.push(['questions','Open question']);
    if(states['missing-parent']) labels.push(['missing-parent','Missing parent']);
    if(states.uncertain) labels.push(['uncertain','Identity uncertain']);
    if(states.update) labels.push(['update','WikiTree update']);
    return {states,labels,hit:treeOverlay==='none'||Boolean(states[treeOverlay])};
  }
  function treePathGraph(allPeople){
    const aliases=new Map();
    allPeople.forEach(person=>[person.id,...(person.profile_ids||[])].forEach(id=>{if(id) aliases.set(normaliseLiteral(id),person.id);}));
    const graph=Object.fromEntries(allPeople.map(person=>[person.id,[]]));
    const link=(a,b)=>{if(!a||!b||a===b||!graph[a]||!graph[b]) return;if(!graph[a].includes(b)) graph[a].push(b);if(!graph[b].includes(a)) graph[b].push(a);};
    allPeople.forEach(person=>{
      [...(person.father||[]),...(person.mother||[])].forEach(relation=>{if(!relation.outside_export&&treeRelationAllowed(relation)) link(person.id,aliases.get(normaliseLiteral(relation.id)));});
      (person.spouses||[]).forEach(relation=>{if(!relation.outside_export) link(person.id,aliases.get(normaliseLiteral(relation.id)));});
    });
    return graph;
  }
  function connectTreeTargets(graph,targets){
    const kept=new Set(targets.slice(0,1));
    targets.slice(1).forEach(target=>{
      if(kept.has(target)) return;
      const queue=[target],previous=new Map([[target,'']]);let hit='';
      for(let cursor=0;cursor<queue.length&&!hit;cursor++){
        const current=queue[cursor];
        for(const next of graph[current]||[]){
          if(previous.has(next)) continue;
          previous.set(next,current);
          if(kept.has(next)){hit=next;break;}
          queue.push(next);
        }
      }
      kept.add(target);
      if(hit){let current=hit;while(current){kept.add(current);current=previous.get(current)||'';}}
    });
    return [...kept];
  }
  async function connectedTreePathIds(matches,allPeople,filters){
    if(!treePathMode) return null;
    const direct=matches.filter(person=>directTreeIdentityMatch(person,filters));
    const targets=(direct.length>1?direct:matches).slice(0,100).map(person=>person.id);
    const key=`${treeEvidenceMode}|${targets.join('|')}`;
    if(treePathCache.key===key) return treePathCache.ids;
    const graph=treePathGraph(allPeople);
    let ids;
    if(window.Worker&&window.Blob&&window.URL){
      try{
        const source=`onmessage=e=>{const g=e.data.graph,t=e.data.targets,k=new Set(t.slice(0,1));t.slice(1).forEach(s=>{if(k.has(s))return;const q=[s],p=new Map([[s,'']]);let h='';for(let i=0;i<q.length&&!h;i++){const c=q[i];for(const n of g[c]||[]){if(p.has(n))continue;p.set(n,c);if(k.has(n)){h=n;break}q.push(n)}}k.add(s);if(h){let c=h;while(c){k.add(c);c=p.get(c)||''}}});postMessage([...k])}`;
        ids=await new Promise((resolve,reject)=>{const url=URL.createObjectURL(new Blob([source],{type:'text/javascript'})),worker=new Worker(url);const timeout=setTimeout(()=>{worker.terminate();URL.revokeObjectURL(url);reject(new Error('Path worker timed out'));},8000);worker.onmessage=event=>{clearTimeout(timeout);worker.terminate();URL.revokeObjectURL(url);resolve(event.data);};worker.onerror=error=>{clearTimeout(timeout);worker.terminate();URL.revokeObjectURL(url);reject(error);};worker.postMessage({graph,targets});});
      }catch(_error){ids=connectTreeTargets(graph,targets);}
    }else ids=connectTreeTargets(graph,targets);
    treePathCache={key,ids:new Set(ids)};return treePathCache.ids;
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
  function relationshipUpdateTags(person){
    const changes=Array.isArray(person.wikitree_update_relationship_changes)?person.wikitree_update_relationship_changes:[];
    const tags=new Map();
    const relationshipLabels={father:'father',mother:'mother',spouse:'spouse',child:'child',son:'child',daughter:'child',sibling:'sibling',brother:'sibling',sister:'sibling'};
    const uncertainStatuses=new Set(['uncertain','possible','probable','guess']);
    changes.filter(item=>String(item.action||'').toLowerCase()==='add').forEach(change=>{
      const relationship=relationshipLabels[String(change.relationship||'').toLowerCase()];
      if(!relationship) return;
      const status=String(change.status||'').toLowerCase();
      const label=`new ${uncertainStatuses.has(status)?'uncertain ':''}${relationship}`;
      const relative=String(change.relative_id||'');
      const isWikiTree=relative&&!relative.startsWith('record-')&&/^[\p{L}][\p{L}\p{N}_'-]*-\d+$/u.test(relative);
      const tag=isWikiTree
        ?`<a class="catalogue-relationship-badge" href="https://www.wikitree.com/wiki/${encodeURIComponent(relative)}" target="_blank" rel="noopener noreferrer" title="View proposed ${esc(relationship)}: ${esc(relative)}" aria-label="${esc(label)}: ${esc(relative)} on WikiTree">${esc(label)}</a>`
        :`<span class="catalogue-relationship-badge">${esc(label)}</span>`;
      tags.set(`${label}:${relative}`,tag);
    });
    return [...tags.values()].join(' ');
  }
  function updateBadge(person){
    if(!person.needs_wikitree_update) return '';
    const tag=relationshipUpdateTags(person);
    return `<small class="catalogue-update-badge">Needs WikiTree update · significance ${Number(person.wikitree_update_significance)||0}${tag?' '+tag:''}</small>`;
  }
  function resultRow(person,currentKey='',groupKind='',familyKey='',collapsed=false){
    const rowClass=groupKind?` class="catalogue-${groupKind}-child"`:'';
    const familyAttributes=familyKey?` data-family-member="${esc(familyKey)}"${collapsed?' hidden':''}`:'';
    const update=updateBadge(person);
    return `<tr${rowClass}${familyAttributes}><td><a href="${esc(personUrl(person))}"><strong>${esc(person.name)}</strong></a><small class="catalogue-wikitree-id">${wikiLinks(person)}</small>${update}${locationRepeat(person,currentKey)}</td><td${fieldAttributes(person,'birth')}>${fieldHtml(person,'birth')}</td><td${fieldAttributes(person,'birth_location')}>${fieldHtml(person,'birth_location')}</td><td${fieldAttributes(person,'death')}>${fieldHtml(person,'death')}</td><td${fieldAttributes(person,'death_location')}>${fieldHtml(person,'death_location')}</td><td class="catalogue-family-cell${relationshipCellClass(person.spouses)}">${relationHtml(person.spouses,true)}</td><td class="catalogue-family-cell${relationshipCellClass(person.father)}">${relationHtml(person.father,true)}</td><td class="catalogue-family-cell${relationshipCellClass(person.mother)}">${relationHtml(person.mother,true)}</td></tr>`;
  }
  function relationshipCellClass(relations){
    const statuses=[...new Set((relations||[]).map(relation=>relationConfidence(relation).key))];
    return statuses.length===1?` catalogue-parent-cell confidence-${statuses[0]}`:'';
  }
  function resultCard(person,currentKey='',groupKind='',familyKey='',collapsed=false){
    const parents=[...(person.father||[]),...(person.mother||[])];
    const familyAttributes=familyKey?` data-family-member="${esc(familyKey)}"${collapsed?' hidden':''}`:'';
    const update=updateBadge(person);
    return `<article class="catalogue-result-card${groupKind?` catalogue-${groupKind}-child`:''}"${familyAttributes}><h3><a href="${esc(personUrl(person))}">${esc(person.name)}</a></h3>${update}<p class="result-vitals"><span${fieldAttributes(person,'birth')}>${fieldHtml(person,'birth')}</span> – <span${fieldAttributes(person,'death')}>${fieldHtml(person,'death')}</span></p>${locationRepeat(person,currentKey)}<dl><dt>Birth location</dt><dd${fieldAttributes(person,'birth_location')}>${fieldHtml(person,'birth_location')}</dd><dt>Death location</dt><dd${fieldAttributes(person,'death_location')}>${fieldHtml(person,'death_location')}</dd><dt>Parents</dt><dd>${relationHtml(parents,true)}</dd><dt>Spouse</dt><dd>${relationHtml(person.spouses,true)}</dd></dl><details><summary>More catalogue details</summary><dl><dt>Recorded in</dt><dd>${esc((person.recorded_in||[]).join(' / ')||'—')}</dd><dt>Cluster</dt><dd>${esc(person.cluster||'—')}</dd><dt>WikiTree</dt><dd>${wikiLinks(person)}</dd><dt>Evidence</dt><dd>${esc((person.source_qualities||[]).join(', ')||'Unclassified')}</dd></dl></details></article>`;
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
  function treePersonKey(person){
    return normaliseLiteral((person.profile_ids||[])[0]||person.id);
  }
  function directTreeIdentityMatch(person,filters){
    if(!filters.query.length) return true;
    return filters.exact?filters.query.every(term=>person._identityExactTokens.has(term)):filters.query.every(term=>person._identity.includes(term));
  }
  function treeContextResults(matches,allPeople,pathIds=null){
    const lookup=new Map();
    allPeople.forEach(person=>[person.id,...(person.profile_ids||[])].forEach(id=>{if(id) lookup.set(normaliseLiteral(id),person);}));
    let seeds=matches,focused=null;
    if(treeFocusId){focused=lookup.get(normaliseLiteral(treeFocusId))||null;if(focused) seeds=[focused];}
    if(pathIds) return {source:allPeople.filter(person=>pathIds.has(person.id)),focused};
    const included=new Map(seeds.map(person=>[person.id,person])),children=new Map();
    allPeople.forEach(person=>[...(person.father||[]),...(person.mother||[])].forEach(relation=>{
      if(relation.outside_export||!treeRelationAllowed(relation)) return;
      const parent=lookup.get(normaliseLiteral(relation.id));
      if(!parent) return;
      if(!children.has(parent.id)) children.set(parent.id,new Map());
      children.get(parent.id).set(person.id,person);
    }));
    const expand=(direction,setting)=>{
      if(setting==='0') return;
      const limit=setting==='all'?Number.POSITIVE_INFINITY:Number(setting);
      let frontier=[...seeds],depth=0;
      const visited=new Set(frontier.map(person=>person.id));
      while(frontier.length&&depth<limit){
        const next=[];
        frontier.forEach(person=>{
          const relatives=direction==='up'
            ?[...(person.father||[]),...(person.mother||[])].filter(relation=>!relation.outside_export&&treeRelationAllowed(relation)).map(relation=>lookup.get(normaliseLiteral(relation.id))).filter(Boolean)
            :[...(children.get(person.id)||new Map()).values()];
          relatives.forEach(relative=>{if(!visited.has(relative.id)){visited.add(relative.id);included.set(relative.id,relative);next.push(relative);}});
        });
        frontier=next;depth+=1;
      }
    };
    expand('up',treeAncestorDepth);expand('down',treeDescendantDepth);
    return {source:[...included.values()],focused};
  }
  function oneTreeResults(matches,allPeople,filters,pathIds=null){
    const context=treeContextResults(matches,allPeople,pathIds),source=context.source;
    const matchedIds=new Set(matches.map(person=>person.id));
    const directIds=new Set(matches.filter(person=>directTreeIdentityMatch(person,filters)).map(person=>person.id));
    const nodes=new Map(source.map(person=>[person.id,{person,parent:null,parentRelation:null,children:[]}]));
    const lookup=new Map(),allLookup=new Map(),secondaryParents=new Map();
    allPeople.forEach(person=>[person.id,...(person.profile_ids||[])].forEach(id=>{if(id) allLookup.set(normaliseLiteral(id),person);}));
    nodes.forEach(node=>[node.person.id,...(node.person.profile_ids||[])].forEach(id=>{if(id) lookup.set(normaliseLiteral(id),node);}));
    nodes.forEach(node=>{
      const relations=[...(node.person.father||[]).map(relation=>({relation,role:'father'})),...(node.person.mother||[]).map(relation=>({relation,role:'mother'}))];
      relations.sort((a,b)=>{
        if(treeParentPreference==='father'||treeParentPreference==='mother') return Number(b.role===treeParentPreference)-Number(a.role===treeParentPreference)||treeConfidenceRank(b.relation)-treeConfidenceRank(a.relation);
        return treeConfidenceRank(b.relation)-treeConfidenceRank(a.relation)||Number(a.role==='father')-Number(b.role==='father');
      });
      for(const {relation,role} of relations){
        if(relation.outside_export||!treeRelationAllowed(relation)) continue;
        const parent=lookup.get(normaliseLiteral(relation.id));
        if(!parent||parent===node) continue;
        if(node.parent){
          if(!secondaryParents.has(node.person.id)) secondaryParents.set(node.person.id,[]);
          secondaryParents.get(node.person.id).push({parent,relation,role});continue;
        }
        let ancestor=parent,cyclic=false;
        while(ancestor){if(ancestor===node){cyclic=true;break;}ancestor=ancestor.parent;}
        if(cyclic) continue;
        node.parent=parent;node.parentRelation=relation;parent.children.push(node);
      }
    });
    const isGlasgowLine=person=>(person.last_names_at_birth||[]).some(name=>normalise(name)==='glasgow');
    const absorbedBy=new Map(),foldedPartners=new Map();
    nodes.forEach(node=>(node.person.spouses||[]).forEach(relation=>{
      const spouse=lookup.get(normaliseLiteral(relation.id));
      if(!spouse||spouse===node) return;
      const nodeIsGlasgow=isGlasgowLine(node.person),spouseIsGlasgow=isGlasgowLine(spouse.person);
      if(nodeIsGlasgow===spouseIsGlasgow) return;
      const anchor=nodeIsGlasgow?node:spouse,partner=nodeIsGlasgow?spouse:node;
      if(absorbedBy.has(partner.person.id)) return;
      absorbedBy.set(partner.person.id,anchor);
      if(!foldedPartners.has(anchor.person.id)) foldedPartners.set(anchor.person.id,[]);
      foldedPartners.get(anchor.person.id).push(partner);
    }));
    absorbedBy.forEach((anchor,partnerId)=>{
      const partner=nodes.get(partnerId);
      if(partner.parent) partner.parent.children=partner.parent.children.filter(child=>child!==partner);
      partner.children.forEach(child=>{if(child.parent===partner){child.parent=anchor;if(!anchor.children.includes(child)) anchor.children.push(child);}});
      partner.children=[];
    });
    const compareNodes=(a,b)=>comparePeople(a.person,b.person,filters);
    nodes.forEach(node=>node.children.sort(compareNodes));
    const roots=[...nodes.values()].filter(node=>!absorbedBy.has(node.person.id)&&!node.parent).sort(compareNodes);
    const descendantCount=(node,seen=new Set())=>{
      if(seen.has(node.person.id)) return 0;
      const branch=new Set(seen);branch.add(node.person.id);
      return node.children.reduce((total,child)=>total+1+descendantCount(child,branch),0);
    };
    const years=source.map(person=>Number(person.birth_year)).filter(Number.isFinite),minYear=years.length?Math.min(...years):0,maxYear=years.length?Math.max(...years):0,yearSpan=Math.max(1,maxYear-minYear);
    let tabAssigned=false,domRendered=0,virtualOmitted=0;
    const renderNode=(node,position,depth=0,lineage=[],siblingCount=1)=>{
      if(domRendered>=treeRenderLimit){virtualOmitted+=1+descendantCount(node);return '';}
      domRendered+=1;
      const person=node.person,key=treePersonKey(person),hasChildren=node.children.length>0;
      const automaticCollapse=treeExpansionDepth!=='all'&&depth+1>=Number(treeExpansionDepth);
      const collapsed=hasChildren&&(collapsedTreePeople.has(key)||(!expandedTreePeople.has(key)&&automaticCollapse));
      const descendants=hasChildren?descendantCount(node):0;
      const toggle=hasChildren?`<button class="catalogue-tree-toggle" type="button" data-tree-toggle="${esc(key)}" aria-expanded="${collapsed?'false':'true'}" aria-label="${collapsed?'Expand':'Collapse'} ${descendants} descendant${descendants===1?'':'s'} of ${esc(person.name)}"><span aria-hidden="true">${collapsed?'＋':'−'}</span><small>${descendants}</small></button>`:'<span class="catalogue-tree-leaf" aria-hidden="true"></span>';
      const profile=(person.profile_ids||[])[0];
      const wiki=profile?`<a class="catalogue-tree-wikitree" href="https://www.wikitree.com/wiki/${encodeURIComponent(profile)}" target="_blank" rel="noopener noreferrer">${esc(profile)}</a>`:'';
      const life=person.birth&&person.death?`${person.birth} – ${person.death}`:person.birth?`b. ${person.birth}`:person.death?`d. ${person.death}`:'',place=person.birth_location||person.death_location||'';
      const spouseRelations=[...(person.spouses||[])];
      (foldedPartners.get(person.id)||[]).forEach(partner=>{
        const profileId=(partner.person.profile_ids||[])[0]||'';
        if(!spouseRelations.some(relation=>relation.id===profileId)){
          const reverse=(partner.person.spouses||[]).find(relation=>normaliseLiteral(relation.id)===normaliseLiteral(profile||(person.profile_ids||[])[0]||person.id))||{};
          spouseRelations.push({id:profileId,name:partner.person.name,marriage_date:reverse.marriage_date||'',marriage_location:reverse.marriage_location||''});
        }
      });
      const spouseEntries=spouseRelations.filter(relation=>relation.name||relation.id).map(relation=>{
        const spouse=lookup.get(normaliseLiteral(relation.id)),spousePerson=spouse?spouse.person:allLookup.get(normaliseLiteral(relation.id)),folded=spouse&&absorbedBy.get(spouse.person.id)===node;
        const link=folded?`<a class="catalogue-tree-folded-spouse" data-folded-spouse="${esc(spouse.person.id)}" href="${esc(personUrl(spouse.person))}">${esc(relation.name||spouse.person.name)}</a>`:spousePerson?`<a class="catalogue-tree-spouse-link" data-tree-spouse-id="${esc(spousePerson.id)}" href="${esc(personUrl(spousePerson))}">${esc(relation.name||spousePerson.name)}</a>`:relation.id?`<a href="https://www.wikitree.com/wiki/${encodeURIComponent(relation.id)}" target="_blank" rel="noopener noreferrer">${esc(relation.name||relation.id)}</a>`:esc(relation.name);
        const event=[relation.marriage_date?esc(relation.marriage_date):'',relation.marriage_location?esc(relation.marriage_location):''].filter(Boolean).join(' · ');
        const cross=spouse&&!folded&&!absorbedBy.has(spouse.person.id)?'<em>also appears in this tree</em>':'';
        return {relation,spouse,link,event,cross};
      });
      const confidence=node.parentRelation?relationConfidence(node.parentRelation):null;
      const confidenceHtml=confidence?`<span class="catalogue-sr-only">Parent link: ${esc(confidence.label)}</span>`:'';
      const secondary=(secondaryParents.get(person.id)||[]).filter(item=>!absorbedBy.has(item.parent.person.id)).map(item=>`<small class="catalogue-tree-cross-link">Also linked through ${esc(item.role)} <a href="${esc(personUrl(item.parent.person))}">${esc(item.parent.person.name)}</a> · ${esc(relationConfidence(item.relation).label)} <button type="button" data-tree-parent="${esc(item.role)}">Display this parent</button></small>`).join('');
      const childGroups=new Map(),unassigned=[];
      spouseEntries.forEach(entry=>childGroups.set(normaliseLiteral(entry.relation.id),[]));
      node.children.forEach(child=>{
        const parentIds=[...(child.person.father||[]),...(child.person.mother||[])].map(relation=>normaliseLiteral(relation.id));
        const entry=spouseEntries.find(item=>parentIds.includes(normaliseLiteral(item.relation.id)));
        if(entry) childGroups.get(normaliseLiteral(entry.relation.id)).push(child);else unassigned.push(child);
      });
      const nextLineage=[...lineage,person.name];
      const renderChildren=(items,label='')=>items.length?`${label?`<li class="catalogue-tree-union" role="none"><div>${label}</div><ol role="group">`:''}${items.map((child,index)=>renderNode(child,index+1,depth+1,nextLineage,items.length)).join('')}${label?'</ol></li>':''}`:'';
      let childContent='';
      spouseEntries.forEach(entry=>{
        const items=childGroups.get(normaliseLiteral(entry.relation.id))||[];
        if(!items.length) return;
        const event=[entry.relation.marriage_date?esc(entry.relation.marriage_date):'',entry.relation.marriage_location?esc(entry.relation.marriage_location):''].filter(Boolean).join(' · ');
        childContent+=renderChildren(items,spouseEntries.length>1||unassigned.length?`Children with ${esc(entry.relation.name||entry.relation.id)}${event?` · married ${event}`:''}`:'');
      });
      childContent+=renderChildren(unassigned,spouseEntries.length?'Other children':'');
      const children=hasChildren&&!collapsed?`<ol role="group" data-tree-children="${esc(key)}">${childContent}</ol>`:'';
      const expanded=hasChildren?` aria-expanded="${String(!collapsed)}"`:'';
      const relationClass=confidence&&['possible','uncertain','disputed','contradicted'].includes(confidence.key)?' catalogue-tree-uncertain-link':'';
      const matchClass=directIds.has(person.id)?' catalogue-tree-direct-match':matchedIds.has(person.id)?' catalogue-tree-related-match':' catalogue-tree-context';
      const research=treeResearchState(person),overlayClass=treeOverlay==='none'?'':research.hit?' catalogue-tree-overlay-hit':' catalogue-tree-overlay-muted';
      const status=research.labels.map(([,label])=>esc(label)).join(' · ');
      const deepClass=depth>=5?' catalogue-tree-deep':'',tabIndex=tabAssigned?'-1':'0';tabAssigned=true;
      const yearOffset=treeTimeline&&Number.isFinite(Number(person.birth_year))?Math.round(((Number(person.birth_year)-minYear)/yearSpan)*240):0;
      const branchActions=`<details class="catalogue-tree-branch-actions"><summary aria-label="More options for ${esc(person.name)}">•••</summary><div><button type="button" data-tree-focus="${esc(person.id)}">Focus here</button><button type="button" data-tree-branch="ancestors" data-person="${esc(person.id)}">Show ancestors</button><button type="button" data-tree-branch="descendants" data-person="${esc(person.id)}">Show descendants</button><button type="button" data-tree-branch="isolate" data-person="${esc(person.id)}">Show local branch</button><button type="button" data-tree-pin="${esc(person.id)}">${treePinnedPeople.has(person.id)?'Unpin':'Pin'}</button><button type="button" data-tree-copy-branch="${esc(person.id)}">Copy link</button><p class="catalogue-tree-research-note">${confidence?`Parent link: ${esc(confidence.label)}<br>`:''}${status}</p>${secondary}</div></details>`;
      const spouses=spouseEntries.length?`<span class="catalogue-tree-spouses"><span class="catalogue-tree-spouse-label">Spouse${spouseEntries.length>1?'s':''}</span><span class="catalogue-tree-spouse-list">${spouseEntries.map(entry=>`<span class="catalogue-tree-spouse-inline"${entry.event||entry.cross?` title="${entry.event}${entry.cross?' · also appears in this tree':''}"`:''}>${entry.link}${entry.relation.marriage_date?` <small>m. ${esc(entry.relation.marriage_date)}</small>`:''}</span>`).join('')}</span></span>`:'';
      const vitals=life||place?`<span class="catalogue-tree-vitals">${life?`<span class="catalogue-tree-dates">${esc(life)}</span>`:''}${place?`<span class="catalogue-tree-place">${esc(place)}</span>`:''}</span>`:'';
      const couple=`<div class="catalogue-tree-couple-node" role="group" aria-label="${esc(person.name)}${spouseEntries.length?' and partner':''}"><div class="catalogue-tree-person-copy"><span class="catalogue-tree-person-main"><strong><a href="${esc(personUrl(person))}">${esc(person.name)}</a></strong>${wiki}</span>${vitals}${spouses}${confidenceHtml}</div><div class="catalogue-tree-person-actions">${branchActions}</div></div>`;
      return `<li class="catalogue-tree-person${relationClass}${matchClass}${deepClass}${overlayClass}" data-tree-person="${esc(person.id)}" data-parent-confidence="${confidence?confidence.key:'root'}" data-tree-name="${esc(normaliseLiteral(person.name))}" data-lineage="${esc(nextLineage.join(' › '))}" data-birth-year="${esc(person.birth_year||'')}" role="treeitem" aria-level="${depth+1}" aria-posinset="${position}" aria-setsize="${siblingCount}" tabindex="${tabIndex}" style="--tree-year-offset:${yearOffset}px"${depth===0?' data-tree-root="true"':''}${expanded}><div class="catalogue-tree-line">${toggle}${couple}</div>${children}</li>`;
    };
    const tree=roots.map((root,index)=>renderNode(root,index+1,0,[],roots.length)).join('');
    const visibleNodes=source.length-absorbedBy.size,folded=absorbedBy.size;
    const focusLabel=context.focused&&treeFocusId?`<button class="catalogue-tree-clear-focus" type="button">Clear focus on ${esc(context.focused.name)}</button>`:'';
    const pinned=[...treePinnedPeople].map(id=>allPeople.find(person=>person.id===id)).filter(Boolean);
    const pinnedBar=pinned.length?`<div class="catalogue-tree-pins"><strong>Pinned</strong>${pinned.map(person=>`<button type="button" data-tree-focus="${esc(person.id)}">${esc(person.name)}</button>`).join('')}${pinned.length===2?`<a href="${esc(new URL(`../compare.html?a=${encodeURIComponent((pinned[0].profile_ids||[])[0]||pinned[0].id)}&b=${encodeURIComponent((pinned[1].profile_ids||[])[0]||pinned[1].id)}`,scriptUrl||location.href))}">Compare pinned people</a>`:''}</div>`:'';
    const history=treeFocusHistory.length?`<div class="catalogue-tree-history"><button type="button" data-tree-action="back-focus">Back to previous focus</button><span>Recent: ${treeFocusHistory.slice(-4).reverse().map(item=>esc(item.name)).join(' · ')}</span></div>`:'';
    const minimap=roots.length?`<nav class="catalogue-tree-minimap" aria-label="Tree branch overview">${roots.slice(0,80).map((root,index)=>`<button type="button" data-tree-root-jump="${esc(root.person.id)}" style="--branch-size:${Math.min(12,2+Math.ceil(Math.sqrt(descendantCount(root))))}px" aria-label="Jump to ${esc(root.person.name)} branch"><span></span></button>`).join('')}</nav>`:'';
    const timeline=treeTimeline?`<div class="catalogue-tree-timeline-axis" aria-label="Birth-year range"><span>${minYear||'Unknown'}</span><i></i><span>${maxYear||'Unknown'}</span></div>`:'';
    const virtual=virtualOmitted?`<div class="catalogue-tree-virtual-notice" role="status">${virtualOmitted.toLocaleString()} people deferred for performance. <button type="button" data-tree-action="load-more">Load 600 more</button></div>`:'';
    const legend='<details class="catalogue-tree-help"><summary>Legend</summary><div class="catalogue-tree-legend"><span class="direct">Name match</span><span class="related">Related match</span><span class="context">Family context</span><span class="uncertain">Uncertain link</span><span class="parent-high">Documented or tree-marked confident</span><span class="parent-caution">Probable or uncertain</span><span class="parent-disputed">Disputed or contradicted</span><span class="parent-unassessed">Unassessed, non-biological, or root</span><small>Row colour describes the displayed parent link, not overall confidence in the person.</small></div></details>';
    const navigation=pinnedBar||history||minimap?`<details class="catalogue-tree-navigation"><summary>Branch navigation</summary><div>${pinnedBar}${history}${minimap}</div></details>`:'';
    const moreTools=`<details class="catalogue-tree-more"><summary>More</summary><div><button type="button" data-tree-action="previous-match">Previous match</button><button type="button" data-tree-action="next-match">Next match</button><label class="catalogue-tree-compact"><input id="catalogue-tree-compact" type="checkbox"${treeCompact?' checked':''}> Hide details</label><details class="catalogue-tree-export"><summary>Share / export</summary><div><button type="button" data-tree-export="share">Copy view link</button><button type="button" data-tree-export="html">HTML</button><button type="button" data-tree-export="svg">SVG</button><button type="button" data-tree-export="gedcom">GEDCOM</button><button type="button" data-tree-export="print">Print / PDF</button></div></details></div></details>`;
    return {tree:`<section class="catalogue-one-tree${treeCompact?' is-compact':''}${treeTimeline?' is-timeline':''}" data-tree-people="${source.length}" data-tree-nodes="${visibleNodes}" data-folded-spouses="${folded}" aria-label="Nested family tree"><div class="catalogue-one-tree-summary"><div><strong>${treePathMode?'Connecting paths':'One tree'}</strong><span>${visibleNodes.toLocaleString()} people · ${roots.length.toLocaleString()} root${roots.length===1?'':'s'}${folded?` · ${folded.toLocaleString()} partner${folded===1?'':'s'} inline`:''}</span></div><div class="catalogue-tree-breadcrumb" aria-live="polite">Select a person to see their branch path</div></div><div id="catalogue-tree-announcer" class="catalogue-sr-only" aria-live="polite">Tree rendered with ${domRendered} visible people</div><div class="catalogue-tree-tools"><button type="button" data-tree-action="expand-all">Expand</button><button type="button" data-tree-action="collapse-all">Collapse</button><label>Levels <select id="catalogue-tree-expand-depth">${treeDepthOptions(treeExpansionDepth,'Roots only')}</select></label><label class="catalogue-tree-jump">Find <input id="catalogue-tree-jump" type="search" placeholder="Person name"></label>${moreTools}${focusLabel}</div>${navigation}${timeline}${legend}<ol class="catalogue-tree-roots" role="tree">${tree}</ol>${virtual}</section>`};
  }
  function treeViewUrl(personId=''){
    const url=new URL(location.href),params=url.searchParams;
    params.set('groupTree','1');
    if(personId||treeFocusId) params.set('treeFocus',personId||treeFocusId);else params.delete('treeFocus');
    const settings={treeAncestors:[treeAncestorDepth,'0'],treeDescendants:[treeDescendantDepth,'0'],treeExpand:[treeExpansionDepth,treeMobile?'1':'2'],treeEvidence:[treeEvidenceMode,'all'],treeParent:[treeParentPreference,'strongest'],treeOverlay:[treeOverlay,'none']};
    Object.entries(settings).forEach(([key,[value,defaultValue]])=>{if(value!==defaultValue) params.set(key,value);else params.delete(key);});
    treePathMode?params.set('treePaths','1'):params.delete('treePaths');
    treeTimeline?params.set('treeTimeline','1'):params.delete('treeTimeline');
    treeCompact?params.set('treeCompact','1'):params.delete('treeCompact');
    expandedTreePeople.size?params.set('treeExpanded',[...expandedTreePeople].slice(0,40).join(',')):params.delete('treeExpanded');
    collapsedTreePeople.size?params.set('treeCollapsed',[...collapsedTreePeople].slice(0,40).join(',')):params.delete('treeCollapsed');
    return url.href;
  }
  async function copyTreeText(value,message='Copied'){
    try{await navigator.clipboard.writeText(value);}catch(_error){const area=document.createElement('textarea');area.value=value;area.style.position='fixed';area.style.opacity='0';document.body.append(area);area.select();document.execCommand('copy');area.remove();}
    const live=out.querySelector('#catalogue-tree-announcer');if(live) live.textContent=message;
  }
  function downloadTreeFile(name,type,content){
    const url=URL.createObjectURL(new Blob([content],{type})),link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function visibleTreePeople(){
    const ids=new Set([...out.querySelectorAll('[data-tree-person]')].filter(item=>item.offsetParent!==null).map(item=>item.dataset.treePerson));
    out.querySelectorAll('[data-folded-spouse],[data-tree-spouse-id]').forEach(item=>ids.add(item.dataset.foldedSpouse||item.dataset.treeSpouseId));
    return people.filter(person=>ids.has(person.id));
  }
  function treeGedcom(source){
    const ids=new Map(source.map((person,index)=>[person.id,`@I${index+1}@`]));
    const aliases=new Map();source.forEach(person=>[person.id,...(person.profile_ids||[])].forEach(id=>aliases.set(normaliseLiteral(id),person.id)));
    const families=new Map();
    const addFamily=(father,mother,child='')=>{
      if(!father&&!mother) return;
      const key=`${father||''}|${mother||''}`;
      if(!families.has(key)) families.set(key,{father,mother,children:new Set()});
      if(child) families.get(key).children.add(child);
    };
    source.forEach(person=>{
      const father=(person.father||[]).map(relation=>aliases.get(normaliseLiteral(relation.id))).find(id=>ids.has(id))||'';
      const mother=(person.mother||[]).map(relation=>aliases.get(normaliseLiteral(relation.id))).find(id=>ids.has(id))||'';
      addFamily(father,mother,person.id);
      (person.spouses||[]).forEach(relation=>{const spouse=aliases.get(normaliseLiteral(relation.id));if(!spouse||!ids.has(spouse)||person.id>spouse) return;const personMale=normalise(person.gender).startsWith('m');addFamily(personMale?person.id:spouse,personMale?spouse:person.id);});
    });
    const familyIds=new Map([...families.keys()].map((key,index)=>[key,`@F${index+1}@`]));
    const lines=['0 HEAD','1 SOUR Glasgow-Surname-Project','1 GEDC','2 VERS 5.5.1','1 CHAR UTF-8'];
    source.forEach(person=>{
      const surname=[...(person.last_names_at_birth||[]),...(person.last_names_current||[])][0]||'',given=surname?person.name.replace(new RegExp(`${surname.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}$`,'i'),'').trim():person.name;
      lines.push(`0 ${ids.get(person.id)} INDI`,`1 NAME ${given} /${surname}/`);
      if(person.gender) lines.push(`1 SEX ${String(person.gender).charAt(0).toUpperCase()}`);
      if(person.birth){lines.push('1 BIRT',`2 DATE ${person.birth}`);if(person.birth_location) lines.push(`2 PLAC ${person.birth_location}`);}
      if(person.death){lines.push('1 DEAT',`2 DATE ${person.death}`);if(person.death_location) lines.push(`2 PLAC ${person.death_location}`);}
      families.forEach((family,key)=>{if(family.children.has(person.id)) lines.push(`1 FAMC ${familyIds.get(key)}`);if(family.father===person.id||family.mother===person.id) lines.push(`1 FAMS ${familyIds.get(key)}`);});
    });
    families.forEach((family,key)=>{lines.push(`0 ${familyIds.get(key)} FAM`);if(family.father) lines.push(`1 HUSB ${ids.get(family.father)}`);if(family.mother) lines.push(`1 WIFE ${ids.get(family.mother)}`);family.children.forEach(child=>lines.push(`1 CHIL ${ids.get(child)}`));});
    lines.push('0 TRLR');return lines.join('\r\n')+'\r\n';
  }
  function exportTree(format){
    const tree=out.querySelector('.catalogue-one-tree'),source=visibleTreePeople();if(!tree) return;
    if(format==='share'){copyTreeText(treeViewUrl(),'Shareable tree link copied');return;}
    if(format==='print'){window.print();return;}
    if(format==='gedcom'){downloadTreeFile('glasgow-tree.ged','text/plain;charset=utf-8',treeGedcom(source));return;}
    if(format==='html'){
      const cssUrl=new URL('catalogue.css',scriptUrl||location.href).href;
      downloadTreeFile('glasgow-tree.html','text/html;charset=utf-8',`<!doctype html><html><head><meta charset="utf-8"><title>Glasgow family tree</title><link rel="stylesheet" href="${esc(cssUrl)}"></head><body><main>${tree.outerHTML}</main></body></html>`);return;
    }
    if(format==='svg'){
      const items=[...tree.querySelectorAll('[data-tree-person]')].filter(item=>item.offsetParent!==null),height=Math.max(120,items.length*24+50);
      const rows=items.map((item,index)=>`<text x="${20+(Number(item.getAttribute('aria-level'))||1)*22}" y="${35+index*24}" fill="#eef4f1" font-family="sans-serif" font-size="14">${esc(item.dataset.lineage)}</text>`).join('');
      downloadTreeFile('glasgow-tree.svg','image/svg+xml;charset=utf-8',`<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="${height}" viewBox="0 0 1400 ${height}"><rect width="100%" height="100%" fill="#07100e"/><text x="20" y="20" fill="#d4af37" font-family="serif" font-size="16">Glasgow family tree</text>${rows}</svg>`);
    }
  }
  function loadCatalogueMapData(){
    if(catalogueMapDataPromise) return catalogueMapDataPromise;
    const base=scriptUrl||window.location.href;
    const asset=path=>new URL(path,base).href;
    catalogueMapDataPromise=Promise.all([
      fetch(asset('../assets/research/map-points.json'),{headers:{Accept:'application/json'}}).then(response=>{if(!response.ok) throw new Error(`Map points returned ${response.status}`);return response.json();}),
      fetch(asset('../assets/v3/map-country-associations.json'),{headers:{Accept:'application/json'}}).then(response=>response.ok?response.json():[]).catch(()=>[]),
      fetch(asset('../assets/research/world.json'),{headers:{Accept:'application/json'}}).then(response=>response.ok?response.json():[]).catch(()=>[])
    ]).then(([points,broad,world])=>({points:[...(Array.isArray(points)?points:[]),...(Array.isArray(broad)?broad.map(point=>({...point,broad:true})):[])],world:Array.isArray(world)?world:[]}));
    return catalogueMapDataPromise;
  }
  async function catalogueMapModel(source,dataOverride=null){
    const data=dataOverride||await loadCatalogueMapData(),byId=new Map(source.map(person=>[String(person.id),person])),markers=new Map(),mappedPeople=new Set();
    data.points.forEach(point=>{
      if(point.lat===null||point.lat===undefined||point.lon===null||point.lon===undefined||String(point.lat).trim()===''||String(point.lon).trim()==='') return;
      const lat=Number(point.lat),lon=Number(point.lon);
      if(!Number.isFinite(lat)||!Number.isFinite(lon)||lat<-90||lat>90||lon<-180||lon>180) return;
      const matches=new Map();
      (point.items||[]).forEach(item=>{const person=byId.get(String(Array.isArray(item)?item[1]:'') );if(person) matches.set(person.id,person);});
      if(!matches.size) return;
      const key=[lat,lon,point.name||'',point.precision||''].join('|');
      const suppliedPrecision=String(point.precision||'').trim();
      const precision=point.broad&&!/fallback|approximate|representative|country[- ]?level/i.test(suppliedPrecision)
        ?`Approximate country-level representative point · ${suppliedPrecision||'country association'}`
        :(suppliedPrecision||'Supplied representative point');
      if(!markers.has(key)) markers.set(key,{lat,lon,name:point.name||'Supplied location',precision,people:new Map(),broad:Boolean(point.broad)});
      const marker=markers.get(key);matches.forEach((person,id)=>{marker.people.set(id,person);mappedPeople.add(id);});
    });
    const rows=[...markers.values()].sort((a,b)=>a.name.localeCompare(b.name,undefined,{sensitivity:'base'}));
    return {world:data.world,markers:rows,mappedPeople,unmapped:source.length-mappedPeople.size,total:source.length};
  }
  function catalogueMapMarkup(model){
    const mapped=model.mappedPeople.size,locations=model.markers.length;
    const summary=`${mapped.toLocaleString()} of ${model.total.toLocaleString()} filtered people have supplied map points · ${model.unmapped.toLocaleString()} unmapped · ${locations.toLocaleString()} locations`;
    const rows=model.markers.map((marker,index)=>`<button type="button" class="catalogue-map-location" data-catalogue-map-marker="${index}"><strong>${esc(marker.name)}</strong><small>${marker.people.size.toLocaleString()} filtered ${marker.people.size===1?'person':'people'} · ${esc(marker.precision)}</small></button>`).join('');
    return `<section class="catalogue-map-view" aria-label="Map of filtered people"><div class="catalogue-map-summary"><strong>${summary}</strong><span>Coordinates and precision are inherited from the maintained research map; no locations are inferred here.</span></div><div class="catalogue-map-layout"><div class="catalogue-map-stage"><canvas class="catalogue-map-canvas" id="catalogue-map-canvas" tabindex="0" role="img" aria-label="Interactive map of supplied locations"></canvas><div class="catalogue-map-tooltip" id="catalogue-map-tooltip" hidden></div><div class="catalogue-map-controls" role="group" aria-label="Map controls"><button type="button" data-catalogue-map-action="zoom-in" aria-label="Zoom in">+</button><button type="button" data-catalogue-map-action="zoom-out" aria-label="Zoom out">−</button><button type="button" data-catalogue-map-action="fit">Fit</button></div><p class="catalogue-map-boot" id="catalogue-map-boot">${locations?'Loading map…':'No supplied coordinates match these filtered people.'}</p></div><aside class="catalogue-map-sidebar" aria-label="Mapped locations"><h3>Locations in this result</h3><p>${locations.toLocaleString()} supplied location${locations===1?'':'s'} · select a marker for filtered profiles.</p><div class="catalogue-map-location-list">${rows||'<p class="notice">No supplied coordinates are available for this filtered set.</p>'}</div></aside></div><div class="catalogue-map-popup" id="catalogue-map-popup" hidden></div></section>`;
  }
  function installCatalogueMap(model){
    const canvas=out.querySelector('#catalogue-map-canvas'),stage=out.querySelector('.catalogue-map-stage'),popup=out.querySelector('#catalogue-map-popup'),tooltip=out.querySelector('#catalogue-map-tooltip');
    if(!canvas||!stage) return;
    const ctx=canvas.getContext('2d'),world=model.world||[];let width=900,height=520,dpr=1,pending=false,pointer=null,dragged=false,clusters=[];
    let camera={x:.5,y:.36,z:1.45};
    const merc=(lat,lon)=>{const s=Math.sin(Math.max(-85,Math.min(85,lat))*Math.PI/180);return {x:(lon+180)/360,y:.5-Math.log((1+s)/(1-s))/(4*Math.PI)}};
    const project=point=>{const scale=256*2**camera.z,m=merc(point.lat,point.lon);return {x:width/2+(m.x-camera.x)*scale,y:height/2+(m.y-camera.y)*scale}};
    const constrain=()=>{camera.z=Math.max(.25,Math.min(12,camera.z));camera.x=Math.max(0,Math.min(1,camera.x));camera.y=Math.max(0,Math.min(1,camera.y));};
    const queue=()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;draw()})};
    const fit=()=>{if(!model.markers.length){queue();return;}const points=model.markers.map(marker=>merc(marker.lat,marker.lon)),xs=points.map(point=>point.x),ys=points.map(point=>point.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);camera.x=(minX+maxX)/2;camera.y=(minY+maxY)/2;camera.z=Math.min(5.8,Math.log2(Math.min((width-80)/(256*Math.max(maxX-minX,.002)),(height-80)/(256*Math.max(maxY-minY,.002)))));constrain();queue()};
    const drawLand=()=>{const scale=256*2**camera.z;ctx.fillStyle='#e6ecdf';ctx.strokeStyle='#c3d0bf';ctx.lineWidth=.7;for(const polygons of world){if(!Array.isArray(polygons))continue;for(const rings of polygons){if(!Array.isArray(rings))continue;ctx.beginPath();for(const ring of rings||[]){if(!Array.isArray(ring))continue;ring.forEach(([lon,lat],index)=>{const point=merc(lat,lon),x=width/2+(point.x-camera.x)*scale,y=height/2+(point.y-camera.y)*scale;index?ctx.lineTo(x,y):ctx.moveTo(x,y)});}ctx.closePath();ctx.fill('evenodd');ctx.stroke();}}};
    const precisionIsBroad=marker=>marker.broad||/fallback|approximate|representative|inferred|unproved|holding point/i.test(marker.precision);
    const draw=()=>{if(!width||!height)return;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);ctx.fillStyle='#f5f7f1';ctx.fillRect(0,0,width,height);drawLand();const grid=new Map(),cell=camera.z>7?22:34;for(const marker of model.markers){const point=project(marker);if(point.x<-30||point.y<-30||point.x>width+30||point.y>height+30)continue;const key=`${Math.floor(point.x/cell)}:${Math.floor(point.y/cell)}`;let cluster=grid.get(key);if(!cluster){cluster={x:0,y:0,markers:[]};grid.set(key,cluster)}cluster.x+=point.x;cluster.y+=point.y;cluster.markers.push(marker)}clusters=[...grid.values()];for(const cluster of clusters){cluster.x/=cluster.markers.length;cluster.y/=cluster.markers.length;cluster.people=new Set(cluster.markers.flatMap(marker=>[...marker.people.keys()]));cluster.r=Math.min(25,7+Math.log2(cluster.people.size+1)*2.2);const broad=cluster.markers.every(precisionIsBroad);ctx.fillStyle=broad?'#d9b978':'#2b6750';ctx.beginPath();ctx.arc(cluster.x,cluster.y,cluster.r,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#fffdf4';ctx.lineWidth=1.5;ctx.stroke();if(broad){ctx.setLineDash([3,3]);ctx.strokeStyle='#765d32';ctx.stroke();ctx.setLineDash([])}if(cluster.people.size>1){ctx.fillStyle='#fffdf4';ctx.font='600 11px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(cluster.people.size.toLocaleString(),cluster.x,cluster.y)}}};
    const popupFor=marker=>{if(!marker)return;const people=[...marker.people.values()].sort((a,b)=>a.name.localeCompare(b.name,undefined,{sensitivity:'base'}));popup.innerHTML=`<button type="button" class="catalogue-map-popup-close" aria-label="Close location">×</button><h3>${esc(marker.name)}</h3><p class="catalogue-map-precision">${esc(marker.precision)}</p><p class="catalogue-map-coordinate">Supplied representative point: ${marker.lat.toFixed(4)}, ${marker.lon.toFixed(4)}</p><ul>${people.map(person=>`<li><a href="${esc(personUrl(person))}">${esc(person.name)}</a>${person.birth||person.death?` <small>${esc(person.birth||'')} ${person.death?`– ${esc(person.death)}`:''}</small>`:''}</li>`).join('')}</ul>`;popup.hidden=false;popup.querySelector('.catalogue-map-popup-close').onclick=()=>{popup.hidden=true};};
    const choose=cluster=>{if(!cluster)return;if(cluster.markers.length>1){const points=cluster.markers.map(marker=>merc(marker.lat,marker.lon));const xs=points.map(point=>point.x),ys=points.map(point=>point.y);camera.x=(Math.min(...xs)+Math.max(...xs))/2;camera.y=(Math.min(...ys)+Math.max(...ys))/2;camera.z=Math.min(10,camera.z+.8);constrain();queue();return;}popupFor(cluster.markers[0]);};
    const resize=()=>{const box=canvas.getBoundingClientRect();width=Math.max(280,box.width);height=Math.max(320,box.height);dpr=Math.min(devicePixelRatio||1,2);canvas.width=width*dpr;canvas.height=height*dpr;queue()};
    const showTooltip=(event)=>{const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top,cluster=clusters.find(item=>Math.hypot(item.x-x,item.y-y)<item.r+7);tooltip.hidden=!cluster;if(cluster){tooltip.textContent=`${cluster.people.size.toLocaleString()} filtered ${cluster.people.size===1?'person':'people'} · ${cluster.markers.length.toLocaleString()} supplied location${cluster.markers.length===1?'':'s'}`;tooltip.style.left=`${Math.min(width-240,Math.max(8,x+12))}px`;tooltip.style.top=`${Math.max(8,y-34)}px`;canvas.style.cursor='pointer'}else canvas.style.cursor='grab'};
    canvas.addEventListener('wheel',event=>{event.preventDefault();camera.z+=event.deltaY<0?.35:-.35;constrain();queue()},{passive:false});
    canvas.addEventListener('pointerdown',event=>{canvas.setPointerCapture(event.pointerId);pointer={x:event.clientX,y:event.clientY,cx:camera.x,cy:camera.y};dragged=false;tooltip.hidden=true});
    canvas.addEventListener('pointermove',event=>{if(pointer){const dx=event.clientX-pointer.x,dy=event.clientY-pointer.y;if(Math.abs(dx)+Math.abs(dy)>4)dragged=true;const scale=256*2**camera.z;camera.x=pointer.cx-dx/scale;camera.y=pointer.cy-dy/scale;constrain();queue();return}showTooltip(event)});
    canvas.addEventListener('pointerup',event=>{const moved=dragged;pointer=null;if(moved)return;const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;choose(clusters.find(item=>Math.hypot(item.x-x,item.y-y)<item.r+7))});
    canvas.addEventListener('pointerleave',()=>{tooltip.hidden=true});
    canvas.addEventListener('keydown',event=>{if(['+','=','-','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(event.key))event.preventDefault();if(event.key==='+'||event.key==='=')camera.z+=.5;if(event.key==='-')camera.z-=.5;if(event.key==='Home')fit();const scale=256*2**camera.z;if(event.key==='ArrowLeft')camera.x-=70/scale;if(event.key==='ArrowRight')camera.x+=70/scale;if(event.key==='ArrowUp')camera.y-=70/scale;if(event.key==='ArrowDown')camera.y+=70/scale;constrain();queue()});
    out.querySelectorAll('[data-catalogue-map-action]').forEach(button=>button.addEventListener('click',()=>{const action=button.dataset.catalogueMapAction;if(action==='zoom-in')camera.z+=.7;if(action==='zoom-out')camera.z-=.7;if(action==='fit')fit();constrain();queue()}));
    out.querySelectorAll('[data-catalogue-map-marker]').forEach(button=>button.addEventListener('click',()=>popupFor(model.markers[Number(button.dataset.catalogueMapMarker)])));
    disconnectCatalogueMap();
    catalogueMapResizeObserver=new ResizeObserver(resize);catalogueMapResizeObserver.observe(stage);resize();fit();out.querySelector('#catalogue-map-boot').hidden=true;
  }
  function paginationHtml(total,start,count,pageCount){
    const pages=[];
    const add=number=>pages.push(number);
    [1,page-2,page-1,page,page+1,page+2,pageCount].filter(number=>number>=1&&number<=pageCount).forEach(number=>{if(!pages.includes(number)) add(number);});
    pages.sort((a,b)=>a-b);
    const buttons=[];
    pages.forEach((number,index)=>{
      if(index&&number-pages[index-1]>1) buttons.push('<span class="catalogue-page-gap" aria-hidden="true">…</span>');
      buttons.push(number===page?`<button type="button" class="catalogue-page is-current" data-page="${number}" aria-current="page" aria-label="Page ${number}, current page">${number}</button>`:`<button type="button" class="catalogue-page" data-page="${number}" aria-label="Page ${number}">${number}</button>`);
    });
    const sizes=pageSizes.map(size=>`<option value="${size}"${size===perPage?' selected':''}>${size}</option>`).join('');
    const nav=pageCount>1?`<nav class="catalogue-pagination-pages" aria-label="Result pages"><button type="button" class="catalogue-page" data-page="${page-1}"${page<=1?' disabled':''} aria-label="Previous page">‹</button>${buttons.join('')}<button type="button" class="catalogue-page" data-page="${page+1}"${page>=pageCount?' disabled':''} aria-label="Next page">›</button></nav>`:'<span></span>';
    return `<div class="catalogue-pagination">${nav}<div class="catalogue-pagination-meta"><label>Show <select id="catalogue-per-page">${sizes}</select> per page</label><span>${total?`${(start+1).toLocaleString()}–${(start+count).toLocaleString()} of ${total.toLocaleString()}`:'0 results'}</span></div></div>`;
  }
  async function render(options={}){
    const current=++renderNumber;
    disconnectCatalogueMap();
    updateClear();
    // With no filters the whole catalogue is browsable, A–Z by default.
    const browsing=!hasActiveFilter();
    if(!browsing&&autoBrowseSort){sortMode='relevance';autoBrowseSort=false;}
    setStatus('Searching…','busy');
    let source;
    try{source=await loadPeople();}catch(_error){return;}
    if(current!==renderNumber) return;
    const filters=criteria();
    if(browsing&&sortMode==='relevance'){sortMode='name:asc';autoBrowseSort=true;}
    if(!filters.query.length&&sortMode==='relevance') sortMode=controls.needsUpdate.checked?'significance:desc':'birth:asc';
    let matchesSource,workerSorted=false;
    if(searchWorker){try{const flags=Object.fromEntries(Object.entries(controls).map(([key,c])=>[key,Boolean(c?.checked)]));const ids=await workerRequest('filter',{filters:{...filters,gender:selectedGender(),flags},sortMode});const byId=new Map(source.map(p=>[p.id,p]));matchesSource=ids.map(id=>byId.get(id));workerSorted=true}catch(error){searchWorker?.terminate();searchWorker=null;source=people=await preparedPeople(false);matchesSource=source.filter(p=>matches(p,filters))}}
    else matchesSource=source.filter(p=>matches(p,filters));
    if(current!==renderNumber)return;
    const found=workerSorted?matchesSource:matchesSource.sort((a,b)=>comparePeople(a,b,filters));
    const groupedMode=groupLocations||groupFamilies||groupOneTree;
    // Grouping must use the complete filtered population, so only ungrouped
    // results are paginated.
    const pageCount=Math.max(1,Math.ceil(found.length/perPage));
    if(page>pageCount) page=pageCount;
    const start=(page-1)*perPage;
    const shown=groupedMode?found:found.slice(start,start+perPage);
    if(groupOneTree&&searchWorker){const all=await workerRequest('all');const byId=new Map(all.map(p=>[p.id,p]));for(const p of source)Object.assign(p,byId.get(p.id));}
    try{await hydrateDetails(groupOneTree?source:groupedMode||resultView==='map'?found:shown)}catch(error){setStatus('Details unavailable — retry search','error');out.innerHTML='<p class="notice">The result details could not load. Search again to retry.</p>';return;}
    if(current!==renderNumber)return;
    window.GlasgowSearchMetrics={readyMs:performance.now(),people:source.length};
    document.dispatchEvent(new CustomEvent('catalogue:ready',{detail:window.GlasgowSearchMetrics}));
    const range=!groupedMode&&found.length>shown.length?` · ${(start+1).toLocaleString()}–${(start+shown.length).toLocaleString()} shown`:'';
    setStatus(browsing?`Browsing all ${found.length.toLocaleString()} people${range}`:`${found.length.toLocaleString()} individual${found.length===1?'':'s'}${range}`,'ready');
    viewResults.hidden=!found.length;
    updateUrl();
    if(!found.length){
      out.innerHTML='<p class="notice">No catalogue match. Try removing one filter or broadening the date range.</p>';
      window.dispatchEvent(new CustomEvent('catalogue:zero-results',{detail:{surface:'people',query:controls.query.value}}));
      return;
    }
    const pathIds=groupOneTree&&treePathMode?await connectedTreePathIds(shown,source,filters):null;
    if(current!==renderNumber) return;
    let mapModel=null;
    if(resultView==='map'){
      try{mapModel=await catalogueMapModel(found);}catch(error){out.innerHTML=`<p class="notice"><strong>The catalogue map could not load.</strong><br>${esc(error.message)}. Return to the table to keep browsing the filtered people.</p>`;return;}
      if(current!==renderNumber) return;
    }
    const grouped=groupLocations?groupedResults(shown):(groupFamilies?groupedFamilyResults(shown):(groupOneTree?oneTreeResults(shown,source,filters,pathIds):null));
    const rows=grouped?grouped.rows:shown.map(person=>resultRow(person)).join('');
    const groupSortLabel=groupLocations?'Sort locations':'Sort branches';
    const groupSortChoices=groupLocations?locationSortOptions():familySortOptions();
    const resultViews=resultView==='map'?catalogueMapMarkup(mapModel):(groupOneTree?grouped.tree:`<div class="table-wrap catalogue-result-table-wrap"><table class="catalogue-results-table"><thead><tr>${sortHeader('name','Individual')}${sortHeader('birth','Birth')}${sortHeader('birthLocation','Birth location')}${sortHeader('death','Death')}${sortHeader('deathLocation','Death location')}${sortHeader('spouse','Spouse(s)')}${sortHeader('father','Father')}${sortHeader('mother','Mother')}</tr></thead><tbody>${rows}</tbody></table></div>`);
    const treeContextControls=groupOneTree?`<div class="catalogue-tree-context-controls"><label>Ancestors <select id="catalogue-tree-ancestors"${treePathMode?' disabled':''}>${treeDepthOptions(treeAncestorDepth)}</select></label><label>Descendants <select id="catalogue-tree-descendants"${treePathMode?' disabled':''}>${treeDepthOptions(treeDescendantDepth)}</select></label><label>Evidence <select id="catalogue-tree-evidence">${treeEvidenceOptions()}</select></label><details class="catalogue-tree-display-options"><summary>Display options</summary><div><label>Primary parent <select id="catalogue-tree-parent"><option value="strongest"${treeParentPreference==='strongest'?' selected':''}>Strongest evidence</option><option value="father"${treeParentPreference==='father'?' selected':''}>Father first</option><option value="mother"${treeParentPreference==='mother'?' selected':''}>Mother first</option></select></label><label>Research overlay <select id="catalogue-tree-overlay"><option value="none"${treeOverlay==='none'?' selected':''}>None</option><option value="sourced"${treeOverlay==='sourced'?' selected':''}>Sourced</option><option value="unsourced"${treeOverlay==='unsourced'?' selected':''}>No original source</option><option value="questions"${treeOverlay==='questions'?' selected':''}>Open questions</option><option value="missing-parent"${treeOverlay==='missing-parent'?' selected':''}>Missing parents</option><option value="uncertain"${treeOverlay==='uncertain'?' selected':''}>Uncertain identity</option><option value="update"${treeOverlay==='update'?' selected':''}>WikiTree update</option></select></label><label class="catalogue-group-toggle"><input id="catalogue-tree-paths" type="checkbox"${treePathMode?' checked':''}> Connecting paths</label><label class="catalogue-group-toggle"><input id="catalogue-tree-timeline" type="checkbox"${treeTimeline?' checked':''}> Timeline</label></div></details></div>`:'';
    const pagination=resultView==='map'||groupedMode?'':paginationHtml(found.length,start,shown.length,pageCount);
    out.innerHTML=`<div class="catalogue-result-toolbar"><strong>${browsing?`All ${found.length.toLocaleString()} people`:`${found.length.toLocaleString()} result${found.length===1?'':'s'}`}</strong><div class="catalogue-result-view-tabs" role="tablist" aria-label="Catalogue result view"><button type="button" data-catalogue-view="table" role="tab" aria-selected="${resultView==='table'}">Table</button><button type="button" data-catalogue-view="map" role="tab" aria-selected="${resultView==='map'}">Map</button></div><div class="catalogue-result-options"><div class="catalogue-group-controls" role="group" aria-label="Group results"><span>Group</span><label class="catalogue-group-toggle"><input id="catalogue-group-locations" type="checkbox"${groupLocations?' checked':''}> Location</label><label class="catalogue-group-toggle"><input id="catalogue-group-families" type="checkbox"${groupFamilies?' checked':''}> Family branch</label><label class="catalogue-group-toggle"><input id="catalogue-group-tree" type="checkbox"${groupOneTree?' checked':''}> One tree</label></div>${treeContextControls}<label${groupLocations?'':' hidden'}>Location detail <select id="catalogue-location-level"${groupLocations?'':' disabled'}><option value="1"${locationLevel==='1'?' selected':''}>Country</option><option value="2"${locationLevel==='2'?' selected':''}>County / area</option><option value="3"${locationLevel==='3'?' selected':''}>Townland / locality</option></select></label><label${groupedMode&&!groupOneTree?'':' hidden'}>${groupSortLabel} <select id="catalogue-group-sort"${groupedMode&&!groupOneTree?'':' disabled'}>${groupSortChoices}</select></label><label>${groupOneTree?'Sort each generation':groupedMode?'Sort within groups':'Sort results'} <select id="catalogue-result-sort">${sortOptions()}</select></label></div></div>${resultViews}${pagination}`;
    if(resultView==='map') installCatalogueMap(mapModel);
    if(restoreResultsAnchor){restoreResultsAnchor=false;requestAnimationFrame(()=>out.scrollIntoView({block:'start'}));}
    if(options.scroll&&window.matchMedia('(max-width: 800px)').matches){
      if(advanced) advanced.open=false;
      closeFilterPanel();
      out.scrollIntoView({behavior:'smooth',block:'start'});
    }
  }
  const schedule=()=>{clearTimeout(timer);page=1;updateClear();setStatus('Searching…','busy');timer=setTimeout(()=>render(),160);};
  form.addEventListener('submit',event=>{event.preventDefault();closeFilterPanel();clearTimeout(timer);sortMode='relevance';autoBrowseSort=false;page=1;pendingPush=true;render({scroll:true});});
  form.querySelectorAll('input,select').forEach(input=>input.addEventListener(input.type==='checkbox'||input.tagName==='SELECT'?'change':'input',()=>{
    if(input===controls.name||input===controls.first||input===controls.last||input===controls.query){legacyNameFilter='';legacyFirstFilter='';legacyLastFilter='';}
    if(input===controls.name||input===controls.first||input===controls.last) birthSurnameOnly='';
    if(input===controls.spouse) marriageSurnameOnly='';
    if(input.type==='checkbox'||input.type==='radio'||input.tagName==='SELECT') pendingPush=true;
    schedule();
  }));
  clear.addEventListener('click',()=>{
    closeFilterPanel();
    form.querySelectorAll('input,select').forEach(input=>{if(input.matches('[data-relative-select]')) return;if(input.type==='checkbox'||input.type==='radio') input.checked=false;else input.value='';});
    genderInputs.find(input=>input.value==='both').checked=true;
    birthSurnameOnly='';
    marriageSurnameOnly='';
    legacyNameFilter='';
    legacyFirstFilter='';
    legacyLastFilter='';
    sortMode='relevance';
    autoBrowseSort=false;
    page=1;
    pendingPush=true;
    syncRelatives(true);
    render();
    controls.query.focus();
  });
  viewResults.addEventListener('click',()=>out.scrollIntoView({behavior:'smooth',block:'start'}));
  out.addEventListener('change',event=>{
    if(event.target.id==='catalogue-group-locations'){
      groupLocations=event.target.checked;
      if(groupLocations){groupFamilies=false;groupOneTree=false;}
    }
    else if(event.target.id==='catalogue-group-families'){
      groupFamilies=event.target.checked;
      if(groupFamilies){groupLocations=false;groupOneTree=false;}
    }
    else if(event.target.id==='catalogue-group-tree'){
      groupOneTree=event.target.checked;
      if(groupOneTree){groupLocations=false;groupFamilies=false;}
    }
    else if(event.target.id==='catalogue-tree-ancestors') treeAncestorDepth=event.target.value;
    else if(event.target.id==='catalogue-tree-descendants') treeDescendantDepth=event.target.value;
    else if(event.target.id==='catalogue-tree-evidence') treeEvidenceMode=event.target.value;
    else if(event.target.id==='catalogue-tree-parent') treeParentPreference=event.target.value;
    else if(event.target.id==='catalogue-tree-overlay') treeOverlay=event.target.value;
    else if(event.target.id==='catalogue-tree-paths'){
      treePathMode=event.target.checked;treePathCache={key:'',ids:null};collapsedTreePeople.clear();expandedTreePeople.clear();
    }
    else if(event.target.id==='catalogue-tree-timeline') treeTimeline=event.target.checked;
    else if(event.target.id==='catalogue-tree-expand-depth'){
      treeExpansionDepth=event.target.value;collapsedTreePeople.clear();expandedTreePeople.clear();
    }
    else if(event.target.id==='catalogue-tree-compact') treeCompact=event.target.checked;
    else if(event.target.id==='catalogue-location-level') locationLevel=event.target.value;
    else if(event.target.id==='catalogue-group-sort'){
      if(groupLocations) locationGroupSort=event.target.value;
      else if(groupFamilies) familyGroupSort=event.target.value;
    }
    else if(event.target.id==='catalogue-result-sort'){sortMode=event.target.value;autoBrowseSort=false;}
    else if(event.target.id==='catalogue-per-page'){perPage=Number(event.target.value)||50;}
    else return;
    page=1;
    pendingPush=true;
    render();
  });
  out.addEventListener('click',event=>{
    const viewButton=event.target.closest('button[data-catalogue-view]');
    if(viewButton){
      const nextView=viewButton.dataset.catalogueView==='map'?'map':'table';
      if(resultView!==nextView){resultView=nextView;pendingPush=true;page=1;render({scroll:true});}
      return;
    }
    const treeToggle=event.target.closest('button[data-tree-toggle]');
    if(treeToggle){
      const item=treeToggle.closest('[data-tree-person]'),personId=item&&item.dataset.treePerson;
      const key=treeToggle.dataset.treeToggle,collapse=treeToggle.getAttribute('aria-expanded')==='true';
      if(collapse){collapsedTreePeople.add(key);expandedTreePeople.delete(key);}
      else{collapsedTreePeople.delete(key);expandedTreePeople.add(key);}
      render().then(()=>{const replacement=[...out.querySelectorAll('[data-tree-person]')].find(candidate=>candidate.dataset.treePerson===personId);if(replacement) replacement.focus();});
      return;
    }
    const treeFocus=event.target.closest('button[data-tree-focus]');
    if(treeFocus){
      const focused=people.find(person=>person.id===treeFocus.dataset.treeFocus);
      if(focused&&treeFocusHistory.at(-1)?.id!==focused.id) treeFocusHistory.push({id:focused.id,name:focused.name});
      treeFocusId=treeFocus.dataset.treeFocus;
      if(treeAncestorDepth==='0'&&treeDescendantDepth==='0'){treeAncestorDepth='2';treeDescendantDepth='2';}
      collapsedTreePeople.clear();expandedTreePeople.clear();render();return;
    }
    if(event.target.closest('.catalogue-tree-clear-focus')){treeFocusId='';render();return;}
    const parentChoice=event.target.closest('button[data-tree-parent]');
    if(parentChoice){treeParentPreference=parentChoice.dataset.treeParent;render();return;}
    const branch=event.target.closest('button[data-tree-branch]');
    if(branch){
      const focused=people.find(person=>person.id===branch.dataset.person);if(focused&&treeFocusHistory.at(-1)?.id!==focused.id) treeFocusHistory.push({id:focused.id,name:focused.name});
      treeFocusId=branch.dataset.person;
      if(branch.dataset.treeBranch==='ancestors'){treeAncestorDepth='all';treeDescendantDepth='0';}
      else if(branch.dataset.treeBranch==='descendants'){treeAncestorDepth='0';treeDescendantDepth='all';}
      else{treeAncestorDepth='3';treeDescendantDepth='3';}
      treePathMode=false;collapsedTreePeople.clear();expandedTreePeople.clear();render();return;
    }
    const pin=event.target.closest('button[data-tree-pin]');
    if(pin){treePinnedPeople.has(pin.dataset.treePin)?treePinnedPeople.delete(pin.dataset.treePin):treePinnedPeople.add(pin.dataset.treePin);try{localStorage.setItem('glasgow-tree-pins',JSON.stringify([...treePinnedPeople]));}catch(_error){}render();return;}
    const copyBranch=event.target.closest('button[data-tree-copy-branch]');
    if(copyBranch){copyTreeText(treeViewUrl(copyBranch.dataset.treeCopyBranch),'Branch link copied');return;}
    const rootJump=event.target.closest('button[data-tree-root-jump]');
    if(rootJump){const root=[...out.querySelectorAll('[data-tree-root]')].find(item=>item.dataset.treePerson===rootJump.dataset.treeRootJump);if(root){root.focus();root.scrollIntoView({behavior:'smooth',block:'center'});}return;}
    const treeExport=event.target.closest('button[data-tree-export]');
    if(treeExport){exportTree(treeExport.dataset.treeExport);return;}
    const treeAction=event.target.closest('button[data-tree-action]');
    if(treeAction){
      const action=treeAction.dataset.treeAction;
      if(action==='expand-all'){treeExpansionDepth='all';collapsedTreePeople.clear();expandedTreePeople.clear();render();return;}
      if(action==='collapse-all'){treeExpansionDepth='0';collapsedTreePeople.clear();expandedTreePeople.clear();render();return;}
      if(action==='load-more'){treeRenderLimit+=600;render();return;}
      if(action==='back-focus'){
        if(treeFocusHistory.length&&treeFocusHistory.at(-1).id===treeFocusId) treeFocusHistory.pop();
        const previous=treeFocusHistory.at(-1);treeFocusId=previous?previous.id:'';render();return;
      }
      const matches=[...out.querySelectorAll('.catalogue-tree-direct-match,.catalogue-tree-related-match')].filter(item=>item.offsetParent!==null);
      if(!matches.length) return;
      treeMatchCursor=(treeMatchCursor+(action==='previous-match'?-1:1)+matches.length)%matches.length;
      matches[treeMatchCursor].focus();matches[treeMatchCursor].scrollIntoView({behavior:'smooth',block:'center'});
      const crumb=out.querySelector('.catalogue-tree-breadcrumb');if(crumb) crumb.textContent=matches[treeMatchCursor].dataset.lineage;
      return;
    }
    const treeLine=event.target.closest('.catalogue-tree-line');
    if(treeLine){const item=treeLine.closest('[data-lineage]'),crumb=out.querySelector('.catalogue-tree-breadcrumb');if(item&&crumb) crumb.textContent=item.dataset.lineage;}
    const familyToggle=event.target.closest('button[data-family-toggle]');
    if(familyToggle){
      const key=familyToggle.dataset.familyToggle,collapse=familyToggle.getAttribute('aria-expanded')==='true';
      if(collapse) collapsedFamilies.add(key); else collapsedFamilies.delete(key);
      out.querySelectorAll('[data-family-member]').forEach(item=>{if(item.dataset.familyMember===key) item.hidden=collapse;});
      out.querySelectorAll('button[data-family-toggle]').forEach(button=>{if(button.dataset.familyToggle===key){button.setAttribute('aria-expanded',String(!collapse));button.setAttribute('aria-label',`${collapse?'Expand':'Collapse'} ${button.dataset.familyLabel} branch`);button.querySelector('span').textContent=collapse?'▸':'▾';button.querySelector('b').textContent=collapse?'Expand branch':'Collapse branch';}});
      return;
    }
    const pageButton=event.target.closest('button[data-page]');
    if(pageButton){
      page=Number(pageButton.dataset.page)||1;pendingPush=true;
      render().then(()=>{out.scrollIntoView({block:'start'});out.querySelector('.catalogue-page.is-current')?.focus({preventScroll:true});});
      return;
    }
    const button=event.target.closest('button[data-sort]');
    if(!button) return;
    const key=button.dataset.sort;
    sortMode=sortMode===`${key}:asc`?`${key}:desc`:`${key}:asc`;
    autoBrowseSort=false;page=1;pendingPush=true;
    render();
  });
  out.addEventListener('input',event=>{
    if(event.target.id!=='catalogue-tree-jump') return;
    const query=normaliseLiteral(event.target.value),items=[...out.querySelectorAll('[data-tree-name]')].filter(item=>item.offsetParent!==null);
    const match=query&&items.find(item=>item.dataset.treeName.includes(query));
    if(match){match.focus();match.scrollIntoView({behavior:'smooth',block:'center'});const crumb=out.querySelector('.catalogue-tree-breadcrumb');if(crumb) crumb.textContent=match.dataset.lineage;}
  });
  out.addEventListener('keydown',event=>{
    const current=event.target.closest('[role="treeitem"]');if(!current||!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Home','End','*'].includes(event.key)) return;
    const items=[...out.querySelectorAll('[role="treeitem"]')].filter(item=>item.offsetParent!==null),index=items.indexOf(current);
    if(event.key==='Home'){items[0]?.focus();event.preventDefault();}
    else if(event.key==='End'){items.at(-1)?.focus();event.preventDefault();}
    else if(event.key==='*'){
      const group=current.parentElement;[...(group?group.children:[])].forEach(item=>{const toggle=item.querySelector(':scope > .catalogue-tree-line button[data-tree-toggle]');if(toggle&&toggle.getAttribute('aria-expanded')==='false') expandedTreePeople.add(toggle.dataset.treeToggle);});collapsedTreePeople.clear();render();event.preventDefault();
    }
    else if(event.key==='ArrowUp'&&index>0){items[index-1].focus();event.preventDefault();}
    else if(event.key==='ArrowDown'&&index<items.length-1){items[index+1].focus();event.preventDefault();}
    else if(event.key==='ArrowRight'){
      const toggle=current.querySelector(':scope > .catalogue-tree-line button[data-tree-toggle]');
      if(toggle&&toggle.getAttribute('aria-expanded')==='false'){toggle.click();event.preventDefault();}
      else{const child=current.querySelector(':scope > ol [role="treeitem"]');if(child){child.focus();event.preventDefault();}}
    }else if(event.key==='ArrowLeft'){
      const toggle=current.querySelector(':scope > .catalogue-tree-line button[data-tree-toggle]');
      if(toggle&&toggle.getAttribute('aria-expanded')==='true'){toggle.click();event.preventDefault();}
      else{const parent=current.parentElement&&current.parentElement.closest('[role="treeitem"]');if(parent){parent.focus();event.preventDefault();}}
    }
  });
  // Filter toolbar: a thin presentation layer over the controls above. The
  // controls stay the single source of truth; panels only show/hide them and
  // the applied-filter chips are derived from their current values.
  const filterBar=document.getElementById('catalogue-filters');
  const appliedBox=document.getElementById('catalogue-applied');
  const appliedList=document.getElementById('catalogue-applied-list');
  const filterBackdrop=form.querySelector('.catalogue-filter-backdrop');
  const relativeRows=document.getElementById('catalogue-relative-rows');
  const addRelative=document.getElementById('catalogue-add-relative');
  const relationOrder=['spouse','father','mother','child','sibling'];
  const relationLabels={spouse:'Spouse',father:'Father',mother:'Mother',child:'Child',sibling:'Sibling'};
  const panelNames={name:'Name',relatives:'Relatives',dates:'Dates',places:'Places',evidence:'Evidence',filters:'Filters',wikitree:'WikiTree'};
  const flagChips=[['glasgowBirth','filters','Glasgow at birth'],['wives','filters','Women who married a Glasgow'],['suffix','filters','Has suffix'],['missingFather','filters','Missing father'],['missingMother','filters','Missing mother'],['descendants','filters','Has descendants'],['missingProfile','wikitree','No confirmed WikiTree link'],['needsUpdate','wikitree','Needs updated on WikiTree']];
  const narrowPanels=window.matchMedia('(max-width: 720px)');
  let openPanelKey='';
  const panelToggle=key=>document.getElementById(`catalogue-filter-toggle-${key}`);
  const panelBody=key=>document.getElementById(`catalogue-filter-panel-${key}`);
  const focusableIn=root=>[...root.querySelectorAll('button,input,select,textarea,a[href]')].filter(element=>!element.disabled&&element.getClientRects().length);
  function positionFilterPanel(body){
    body.style.left='';
    if(narrowPanels.matches) return;
    const bounds=panel.getBoundingClientRect(),rect=body.getBoundingClientRect();
    const right=Math.min(bounds.right,document.documentElement.clientWidth)-8,left=Math.max(bounds.left,0)+8;
    const overflow=rect.right-right;
    if(overflow>0) body.style.left=`${-Math.min(overflow,rect.left-left)}px`;
  }
  function closeFilterPanel(options={}){
    if(!openPanelKey) return;
    const key=openPanelKey,body=panelBody(key),toggle=panelToggle(key);
    openPanelKey='';
    body.hidden=true;body.setAttribute('role','group');body.removeAttribute('aria-modal');
    toggle.setAttribute('aria-expanded','false');
    if(filterBackdrop) filterBackdrop.hidden=true;
    document.documentElement.classList.remove('catalogue-sheet-open');
    if(options.focus) toggle.focus();
  }
  function openFilterPanel(key){
    const body=panelBody(key),toggle=panelToggle(key);
    if(!body||!toggle) return;
    if(openPanelKey!==key){
      closeFilterPanel();
      openPanelKey=key;body.hidden=false;toggle.setAttribute('aria-expanded','true');
      if(narrowPanels.matches){
        body.setAttribute('role','dialog');body.setAttribute('aria-modal','true');
        if(filterBackdrop) filterBackdrop.hidden=false;
        document.documentElement.classList.add('catalogue-sheet-open');
      }
      positionFilterPanel(body);
    }
    const first=focusableIn(body).find(element=>!element.matches('[data-filter-close]'));
    (first||body).focus();
  }
  function visibleRelations(){
    return relativeRows?[...relativeRows.querySelectorAll('.catalogue-relative-row:not([hidden])')].map(row=>row.dataset.relation):[];
  }
  const relationRow=key=>relativeRows&&relativeRows.querySelector(`.catalogue-relative-row[data-relation="${key}"]`);
  function refreshRelativeRows(){
    if(!relativeRows) return;
    const visible=visibleRelations();
    relativeRows.querySelectorAll('.catalogue-relative-row').forEach(row=>{
      const select=row.querySelector('[data-relative-select]');
      select.value=row.dataset.relation;
      [...select.options].forEach(option=>{option.disabled=option.value!==row.dataset.relation&&visible.includes(option.value);});
    });
    if(addRelative) addRelative.disabled=visible.length>=relationOrder.length;
  }
  // Rows with a value are always shown. reset=true also hides empty rows and
  // restores the default single Spouse row.
  function syncRelatives(reset=false){
    if(!relativeRows) return;
    relationOrder.forEach(key=>{
      const row=relationRow(key),hasValue=Boolean(controlValue(controls[key]).trim());
      if(!row) return;
      if(reset){row.hidden=!hasValue;relativeRows.appendChild(row);}
      else if(hasValue&&row.hidden){row.hidden=false;relativeRows.appendChild(row);}
    });
    if(!visibleRelations().length){const row=relationRow('spouse');row.hidden=false;relativeRows.prepend(row);}
    refreshRelativeRows();
  }
  function appliedFilters(){
    const list=[],text=control=>controlValue(control).trim();
    const add=(id,panelKey,label,clearCondition)=>list.push({id,panel:panelKey,label,clear:clearCondition});
    const resetControls=(...keys)=>()=>keys.forEach(key=>{const control=controls[key];if(!control) return;if(control.type==='checkbox') control.checked=false;else control.value='';});
    const optionText=control=>control&&control.selectedIndex>=0?control.options[control.selectedIndex].textContent:text(control);
    if(controls.exact&&controls.exact.checked) add('exact','name','Exact name spelling',resetControls('exact'));
    if(text(controls.first)) add('first','name',`First name: ${text(controls.first)}`,resetControls('first'));
    if(text(controls.last)){
      const scope=lastScope?lastScope.value:'';
      add('last','name',`${scope==='birth'?'Surname at birth':scope==='current'?'Current/last surname':'Last name'}: ${text(controls.last)}`,()=>{controls.last.value='';if(lastScope) lastScope.value='';});
    }
    if(text(controls.name)) add('name','name',`Full name: ${text(controls.name)}`,resetControls('name'));
    if(legacyNameFilter) add('legacy-name','name',`Name: ${legacyNameFilter}`,()=>{legacyNameFilter='';});
    if(legacyFirstFilter) add('legacy-first','name',`First name: ${legacyFirstFilter}`,()=>{legacyFirstFilter='';});
    if(legacyLastFilter) add('legacy-last','name',`Last name: ${legacyLastFilter}`,()=>{legacyLastFilter='';});
    if(selectedGender()!=='both') add('gender','name',`Gender: ${selectedGender()==='male'?'Male':'Female'}`,()=>genderInputs.forEach(input=>{input.checked=input.value==='both';}));
    if(birthSurnameOnly) add('birth-surname','name',`Surname at birth (exact): ${birthSurnameOnly}`,()=>{birthSurnameOnly='';});
    if(marriageSurnameOnly) add('marriage-surname','relatives',`Glasgow-born, spouse’s surname: ${marriageSurnameOnly}`,()=>{marriageSurnameOnly='';if(controls.spouse) controls.spouse.value='';});
    relationOrder.forEach(key=>{
      if(key==='spouse'&&marriageSurnameOnly) return; // the spouse box is ignored while the marriage-surname link applies
      if(text(controls[key])) add(key,'relatives',`${relationLabels[key]}: ${text(controls[key])}`,resetControls(key));
    });
    let from=parseInt(controls.from.value,10),to=parseInt(controls.to.value,10);
    if(!Number.isFinite(from)) from=null;
    if(!Number.isFinite(to)) to=null;
    if(from!==null&&to!==null&&from>to) [from,to]=[to,from];
    if(from!==null||to!==null){
      const scope=controls.dateType.value==='birth'?'Birth':controls.dateType.value==='death'?'Death':'Any date';
      const range=from!==null&&to!==null?(from===to?String(from):`${from}–${to}`):from!==null?`${from} or later`:`${to} or earlier`;
      add('dates','dates',`${scope}: ${range}`,()=>{controls.from.value='';controls.to.value='';controls.dateType.value='';});
    }
    if(text(controls.location)){
      const scope=({birth:'Birth location',death:'Death location',marriage:'Marriage location',bio:'Bio',record:'Record location'})[controls.locationType.value]||'Any location';
      add('location','places',`${scope}: ${text(controls.location)}`,()=>{controls.location.value='';if(!controlValue(controls.excludeDeath).trim()) controls.locationType.value='';});
    }
    if(text(controls.region)) add('region','places',`Country or region: ${optionText(controls.region)}`,resetControls('region'));
    if(text(controls.excludeDeath)) add('excludeDeath','places',`Exclude location: ${text(controls.excludeDeath)}`,resetControls('excludeDeath'));
    if(text(controls.cluster)) add('cluster','evidence',`Possible group: ${optionText(controls.cluster)}`,resetControls('cluster'));
    if(text(controls.recordType)) add('recordType','evidence',`Record type: ${optionText(controls.recordType)}`,resetControls('recordType'));
    if(text(controls.sourceQuality)) add('sourceQuality','evidence',`Source quality: ${optionText(controls.sourceQuality)}`,resetControls('sourceQuality'));
    flagChips.forEach(([key,panelKey,label])=>{if(controls[key]&&controls[key].checked) add(key,panelKey,label,resetControls(key));});
    return list;
  }
  function refreshFilterUi(){
    if(!appliedList) return;
    const applied=appliedFilters();
    appliedList.innerHTML=applied.map(item=>`<li class="catalogue-chip"><button type="button" class="catalogue-chip-text" data-chip-open="${item.panel}" title="Edit in ${esc(panelNames[item.panel])}">${esc(item.label)}</button><button type="button" class="catalogue-chip-remove" data-chip-remove="${esc(item.id)}" aria-label="Remove filter: ${esc(item.label)}"><span aria-hidden="true">×</span></button></li>`).join('');
    if(appliedBox) appliedBox.classList.toggle('has-filters',applied.length>0);
    Object.keys(panelNames).forEach(key=>{
      const badge=panelToggle(key)&&panelToggle(key).querySelector('.catalogue-filter-count');
      if(!badge) return;
      const total=applied.filter(item=>item.panel===key).length;
      badge.hidden=!total;
      badge.innerHTML=total?`${total}<span class="catalogue-sr-only"> active</span>`:'';
    });
  }
  if(filterBar){
    filterBar.addEventListener('click',event=>{
      const toggle=event.target.closest('button[data-filter-panel]');
      if(toggle){
        if(openPanelKey===toggle.dataset.filterPanel) closeFilterPanel({focus:true});
        else openFilterPanel(toggle.dataset.filterPanel);
        return;
      }
      if(event.target.closest('[data-filter-close]')) closeFilterPanel({focus:true});
    });
    filterBar.addEventListener('focusout',event=>{
      if(!openPanelKey||narrowPanels.matches||!event.relatedTarget) return;
      const item=panelToggle(openPanelKey).closest('.catalogue-filter-item');
      if(!item.contains(event.relatedTarget)) closeFilterPanel();
    });
    // Capture phase: Escape must close the panel instead of clearing a search box.
    document.addEventListener('keydown',event=>{
      if(!openPanelKey) return;
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeFilterPanel({focus:true});return;}
      if(event.key==='Tab'&&narrowPanels.matches){
        const items=focusableIn(panelBody(openPanelKey));
        if(!items.length) return;
        if(event.shiftKey&&document.activeElement===items[0]){items.at(-1).focus();event.preventDefault();}
        else if(!event.shiftKey&&document.activeElement===items.at(-1)){items[0].focus();event.preventDefault();}
      }
    },true);
    document.addEventListener('pointerdown',event=>{
      if(!openPanelKey) return;
      const item=panelToggle(openPanelKey).closest('.catalogue-filter-item');
      if(!item.contains(event.target)&&!event.target.closest('[data-chip-open]')) closeFilterPanel();
    });
    narrowPanels.addEventListener('change',()=>closeFilterPanel());
    window.addEventListener('resize',()=>{if(openPanelKey) positionFilterPanel(panelBody(openPanelKey));});
  }
  if(relativeRows){
    relativeRows.addEventListener('change',event=>{
      const select=event.target.closest('[data-relative-select]');
      if(!select) return;
      const row=select.closest('.catalogue-relative-row'),from=row.dataset.relation,to=select.value,target=relationRow(to);
      if(from===to||!target) return;
      // Changing the relationship moves the typed name to that relationship's own control.
      controls[to].value=controls[from].value;controls[from].value='';
      relativeRows.insertBefore(target,row);target.hidden=false;row.hidden=true;
      [controls[from],controls[to]].forEach(input=>input.dispatchEvent(new Event('input',{bubbles:true})));
      refreshRelativeRows();
      target.querySelector('[data-relative-select]').focus();
    });
    relativeRows.addEventListener('click',event=>{
      const remove=event.target.closest('[data-relative-remove]');
      if(!remove) return;
      const row=remove.closest('.catalogue-relative-row'),key=row.dataset.relation;
      const index=visibleRelations().indexOf(key),hadValue=Boolean(controls[key].value);
      controls[key].value='';
      if(hadValue) controls[key].dispatchEvent(new Event('input',{bubbles:true}));
      row.hidden=true;
      syncRelatives();
      const remaining=[...relativeRows.querySelectorAll('.catalogue-relative-row:not([hidden])')];
      (remaining[Math.min(index,remaining.length-1)]||row).querySelector('input').focus();
    });
  }
  if(addRelative) addRelative.addEventListener('click',()=>{
    const key=relationOrder.find(relation=>relationRow(relation).hidden);
    if(!key) return;
    const row=relationRow(key);
    relativeRows.appendChild(row);row.hidden=false;
    refreshRelativeRows();
    row.querySelector('[data-relative-select]').focus();
  });
  if(appliedList) appliedList.addEventListener('click',event=>{
    const open=event.target.closest('[data-chip-open]');
    if(open){openFilterPanel(open.dataset.chipOpen);return;}
    const remove=event.target.closest('[data-chip-remove]');
    if(!remove) return;
    const index=[...appliedList.querySelectorAll('[data-chip-remove]')].indexOf(remove);
    const item=appliedFilters().find(entry=>entry.id===remove.dataset.chipRemove);
    if(!item) return;
    item.clear();
    syncRelatives();
    clearTimeout(timer);
    page=1;
    pendingPush=true;
    render();
    const remaining=appliedList.querySelectorAll('[data-chip-remove]');
    (remaining[Math.min(index,remaining.length-1)]||controls.query).focus();
  });
  // Back/forward: rebuild every control from the URL, then search again.
  window.addEventListener('popstate',()=>{
    clearTimeout(timer);
    closeFilterPanel();
    form.querySelectorAll('input,select').forEach(input=>{if(input.matches('[data-relative-select]')) return;if(input.type==='checkbox'||input.type==='radio') input.checked=false;else input.value='';});
    genderInputs.forEach(input=>{input.checked=input.value==='both';});
    birthSurnameOnly='';marriageSurnameOnly='';legacyNameFilter='';legacyFirstFilter='';legacyLastFilter='';
    sortMode='relevance';autoBrowseSort=false;groupLocations=false;groupFamilies=false;groupOneTree=false;
    locationGroupSort='geography';familyGroupSort='name:asc';locationLevel='3';
    treeAncestorDepth='0';treeDescendantDepth='0';treeExpansionDepth=treeMobile?'1':'2';treeEvidenceMode='all';treeFocusId='';treeCompact=treeMobile;treePathMode=false;treeParentPreference='strongest';treeOverlay='none';treeTimeline=false;
    collapsedTreePeople.clear();expandedTreePeople.clear();
    restoreUrl();
    syncRelatives(true);
    render();
  });
  restoreUrl();
  syncRelatives(true);
  render();
})();
