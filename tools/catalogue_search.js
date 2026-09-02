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
    wives:'catalogue-women-married-glasgow',glasgowBirth:'catalogue-glasgow-at-birth',suffix:'catalogue-has-suffix'
  };
  const controls=Object.fromEntries(Object.entries(ids).map(([key,id])=>[key,document.getElementById(id)]));
  const textParams={q:'query',first:'first',last:'last',dateType:'dateType',from:'from',to:'to',spouse:'spouse',father:'father',mother:'mother',locationType:'locationType',location:'location',excludeDeath:'excludeDeath',region:'region',cluster:'cluster',recordType:'recordType',quality:'sourceQuality'};
  const flagParams={exact:'exact',males:'males',missingFather:'missingFather',missingMother:'missingMother',missingProfile:'missingProfile',needsUpdate:'needsUpdate',descendants:'descendants',wives:'wives',glasgowBirth:'glasgowBirth',suffix:'suffix'};
  if(advanced&&window.matchMedia('(max-width: 700px)').matches) advanced.open=false;
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
  let groupOneTree=false;
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
      person._birthLastNames=(person.last_names_at_birth||[]).map(normalise).filter(Boolean);
      person._marriageSurnames=(person.spouses||[]).map(relationBirthSurname).filter(Boolean);
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
      first:normalise(controls.first.value),last:birthSurnameOnly?'':normalise(controls.last.value),
      birthSurname:normalise(birthSurnameOnly),
      spouse:marriageSurnameOnly?'':normalise(controls.spouse.value),marriageSurname:canonicalMarriageSurname(marriageSurnameOnly),father:normalise(controls.father.value),mother:normalise(controls.mother.value),
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
    if(filters.birthSurname&&!person._birthLastNames.includes(filters.birthSurname)) return false;
    if(filters.last&&!person._last.includes(filters.last)) return false;
    if(filters.spouse&&!person._relations.spouse.includes(filters.spouse)) return false;
    if(filters.marriageSurname&&(!person._birthLastNames.includes('glasgow')||!person._marriageSurnames.includes(filters.marriageSurname))) return false;
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
    Object.entries(textParams).forEach(([param,key])=>{if(key!=='last'&&controls[key].value.trim()) params.set(param,controls[key].value.trim());});
    if(birthSurnameOnly) params.set('birthSurname',birthSurnameOnly);
    else if(controls.last.value.trim()) params.set('last',controls.last.value.trim());
    if(marriageSurnameOnly) params.set('marriageSurname',marriageSurnameOnly);
    Object.entries(flagParams).forEach(([param,key])=>{if(controls[key].checked) params.set(param,'1');});
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
    if(groupOneTree&&expandedTreePeople.size) params.set('treeExpanded',[...expandedTreePeople].slice(0,40).join(','));
    if(groupOneTree&&collapsedTreePeople.size) params.set('treeCollapsed',[...collapsedTreePeople].slice(0,40).join(','));
    if(groupLocations&&locationGroupSort!=='geography') params.set('locationSort',locationGroupSort);
    if(groupFamilies&&familyGroupSort!=='name:asc') params.set('familySort',familyGroupSort);
    if(groupLocations&&locationLevel!=='3') params.set('locationLevel',locationLevel);
    const query=params.toString();
    history.replaceState(null,'',`${location.pathname}${query?`?${query}`:''}${location.hash}`);
  }
  function restoreUrl(){
    const params=new URLSearchParams(location.search);
    Object.entries(textParams).forEach(([param,key])=>{const value=params.get(param);if(value!==null) controls[key].value=value;});
    birthSurnameOnly=params.get('birthSurname')||'';
    if(birthSurnameOnly) controls.last.value=birthSurnameOnly;
    marriageSurnameOnly=params.get('marriageSurname')||'';
    if(marriageSurnameOnly) controls.spouse.value=marriageSurnameOnly;
    Object.entries(flagParams).forEach(([param,key])=>{controls[key].checked=/^(?:1|true|yes)$/i.test(params.get(param)||'');});
    const requestedSort=params.get('sort');
    if(requestedSort==='family:asc'){
      groupFamilies=true;
      sortMode='birth:asc';
    }else if(requestedSort) sortMode=requestedSort;
    groupLocations=/^(?:1|true|yes)$/i.test(params.get('groupLocation')||'');
    groupFamilies=groupFamilies||/^(?:1|true|yes)$/i.test(params.get('groupFamily')||'');
    groupOneTree=/^(?:1|true|yes)$/i.test(params.get('groupTree')||'');
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
      const life=[person.birth||'Birth unknown',person.death||'Death unknown'].join(' – '),place=person.birth_location||person.death_location||'';
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
      const confidenceHtml=confidence?`<small class="catalogue-relation-confidence confidence-${confidence.key}" title="${esc(confidence.title)}"><i aria-hidden="true"></i>${esc(confidence.label)}</small>`:'';
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
        childContent+=renderChildren(items,`Children with ${esc(entry.relation.name||entry.relation.id)}${event?` · married ${event}`:''}`);
      });
      childContent+=renderChildren(unassigned,spouseEntries.length?'Other children':'');
      const children=hasChildren&&!collapsed?`<ol role="group" data-tree-children="${esc(key)}">${childContent}</ol>`:'';
      const expanded=hasChildren?` aria-expanded="${String(!collapsed)}"`:'';
      const relationClass=confidence&&['possible','uncertain','disputed','contradicted'].includes(confidence.key)?' catalogue-tree-uncertain-link':'';
      const matchClass=directIds.has(person.id)?' catalogue-tree-direct-match':matchedIds.has(person.id)?' catalogue-tree-related-match':' catalogue-tree-context';
      const research=treeResearchState(person),overlayClass=treeOverlay==='none'?'':research.hit?' catalogue-tree-overlay-hit':' catalogue-tree-overlay-muted';
      const status=research.labels.map(([state,label])=>`<span class="catalogue-tree-status status-${state}">${label}</span>`).join('');
      const deepClass=depth>=5?' catalogue-tree-deep':'',tabIndex=tabAssigned?'-1':'0';tabAssigned=true;
      const yearOffset=treeTimeline&&Number.isFinite(Number(person.birth_year))?Math.round(((Number(person.birth_year)-minYear)/yearSpan)*240):0;
      const branchActions=`<details class="catalogue-tree-branch-actions"><summary aria-label="More options for ${esc(person.name)}">•••</summary><div><button type="button" data-tree-focus="${esc(person.id)}">Focus here</button><button type="button" data-tree-branch="ancestors" data-person="${esc(person.id)}">Show ancestors</button><button type="button" data-tree-branch="descendants" data-person="${esc(person.id)}">Show descendants</button><button type="button" data-tree-branch="isolate" data-person="${esc(person.id)}">Show local branch</button><button type="button" data-tree-pin="${esc(person.id)}">${treePinnedPeople.has(person.id)?'Unpin':'Pin'}</button><button type="button" data-tree-copy-branch="${esc(person.id)}">Copy link</button></div></details>`;
      const spouses=spouseEntries.length?`<span class="catalogue-tree-spouses">${spouseEntries.map(entry=>`<span class="catalogue-tree-spouse-inline"><b>m.</b> ${entry.link}${entry.event?` <small>${entry.event}</small>`:''}${entry.cross}</span>`).join('')}</span>`:'';
      const couple=`<div class="catalogue-tree-couple-node" role="group" aria-label="${esc(person.name)}${spouseEntries.length?' and partner':''}"><div class="catalogue-tree-person-copy"><span class="catalogue-tree-person-main"><strong><a href="${esc(personUrl(person))}">${esc(person.name)}</a></strong>${wiki}<span class="catalogue-tree-vitals">${esc(life)}${place?` · ${esc(place)}`:''}</span></span>${spouses}<span class="catalogue-tree-statuses">${status}</span>${confidenceHtml}${secondary}</div><div class="catalogue-tree-person-actions">${branchActions}</div></div>`;
      return `<li class="catalogue-tree-person${relationClass}${matchClass}${deepClass}${overlayClass}" data-tree-person="${esc(person.id)}" data-tree-name="${esc(normaliseLiteral(person.name))}" data-lineage="${esc(nextLineage.join(' › '))}" data-birth-year="${esc(person.birth_year||'')}" role="treeitem" aria-level="${depth+1}" aria-posinset="${position}" aria-setsize="${siblingCount}" tabindex="${tabIndex}" style="--tree-year-offset:${yearOffset}px"${depth===0?' data-tree-root="true"':''}${expanded}><div class="catalogue-tree-line">${toggle}${couple}</div>${children}</li>`;
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
    const legend='<details class="catalogue-tree-help"><summary>Legend</summary><div class="catalogue-tree-legend"><span class="direct">Name match</span><span class="related">Related match</span><span class="context">Family context</span><span class="uncertain">Uncertain link</span></div></details>';
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
    const groupedMode=groupLocations||groupFamilies||groupOneTree;
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
    const pathIds=groupOneTree&&treePathMode?await connectedTreePathIds(shown,source,filters):null;
    if(current!==renderNumber) return;
    const grouped=groupLocations?groupedResults(shown):(groupFamilies?groupedFamilyResults(shown):(groupOneTree?oneTreeResults(shown,source,filters,pathIds):null));
    const rows=grouped?grouped.rows:shown.map(person=>resultRow(person)).join('');
    const cards=grouped?grouped.cards:shown.map(person=>resultCard(person)).join('');
    const groupSortLabel=groupLocations?'Sort locations':'Sort branches';
    const groupSortChoices=groupLocations?locationSortOptions():familySortOptions();
    const resultViews=groupOneTree?grouped.tree:`<div class="table-wrap catalogue-result-table-wrap"><table class="catalogue-results-table"><thead><tr>${sortHeader('name','Individual')}${sortHeader('birth','Birth')}${sortHeader('birthLocation','Birth location')}${sortHeader('death','Death')}${sortHeader('deathLocation','Death location')}${sortHeader('spouse','Spouse(s)')}${sortHeader('father','Father')}${sortHeader('mother','Mother')}</tr></thead><tbody>${rows}</tbody></table></div><div class="catalogue-result-cards">${cards}</div>`;
    const treeContextControls=groupOneTree?`<div class="catalogue-tree-context-controls"><label>Ancestors <select id="catalogue-tree-ancestors"${treePathMode?' disabled':''}>${treeDepthOptions(treeAncestorDepth)}</select></label><label>Descendants <select id="catalogue-tree-descendants"${treePathMode?' disabled':''}>${treeDepthOptions(treeDescendantDepth)}</select></label><label>Evidence <select id="catalogue-tree-evidence">${treeEvidenceOptions()}</select></label><details class="catalogue-tree-display-options"><summary>Display options</summary><div><label>Primary parent <select id="catalogue-tree-parent"><option value="strongest"${treeParentPreference==='strongest'?' selected':''}>Strongest evidence</option><option value="father"${treeParentPreference==='father'?' selected':''}>Father first</option><option value="mother"${treeParentPreference==='mother'?' selected':''}>Mother first</option></select></label><label>Research overlay <select id="catalogue-tree-overlay"><option value="none"${treeOverlay==='none'?' selected':''}>None</option><option value="sourced"${treeOverlay==='sourced'?' selected':''}>Sourced</option><option value="unsourced"${treeOverlay==='unsourced'?' selected':''}>No original source</option><option value="questions"${treeOverlay==='questions'?' selected':''}>Open questions</option><option value="missing-parent"${treeOverlay==='missing-parent'?' selected':''}>Missing parents</option><option value="uncertain"${treeOverlay==='uncertain'?' selected':''}>Uncertain identity</option><option value="update"${treeOverlay==='update'?' selected':''}>WikiTree update</option></select></label><label class="catalogue-group-toggle"><input id="catalogue-tree-paths" type="checkbox"${treePathMode?' checked':''}> Connecting paths</label><label class="catalogue-group-toggle"><input id="catalogue-tree-timeline" type="checkbox"${treeTimeline?' checked':''}> Timeline</label></div></details></div>`:'';
    out.innerHTML=`<div class="catalogue-result-toolbar"><strong>${found.length.toLocaleString()} result${found.length===1?'':'s'}</strong><div class="catalogue-result-options"><div class="catalogue-group-controls" role="group" aria-label="Group results"><span>Group</span><label class="catalogue-group-toggle"><input id="catalogue-group-locations" type="checkbox"${groupLocations?' checked':''}> Location</label><label class="catalogue-group-toggle"><input id="catalogue-group-families" type="checkbox"${groupFamilies?' checked':''}> Family branch</label><label class="catalogue-group-toggle"><input id="catalogue-group-tree" type="checkbox"${groupOneTree?' checked':''}> One tree</label></div>${treeContextControls}<label${groupLocations?'':' hidden'}>Location detail <select id="catalogue-location-level"${groupLocations?'':' disabled'}><option value="1"${locationLevel==='1'?' selected':''}>Country</option><option value="2"${locationLevel==='2'?' selected':''}>County / area</option><option value="3"${locationLevel==='3'?' selected':''}>Townland / locality</option></select></label><label${groupedMode&&!groupOneTree?'':' hidden'}>${groupSortLabel} <select id="catalogue-group-sort"${groupedMode&&!groupOneTree?'':' disabled'}>${groupSortChoices}</select></label><label>${groupOneTree?'Sort each generation':groupedMode?'Sort within groups':'Sort results'} <select id="catalogue-result-sort">${sortOptions()}</select></label></div></div>${resultViews}`;
    if(options.scroll&&window.matchMedia('(max-width: 800px)').matches){
      if(advanced) advanced.open=false;
      out.scrollIntoView({behavior:'smooth',block:'start'});
    }
  }
  const schedule=()=>{clearTimeout(timer);updateClear();setStatus('Searching…','busy');timer=setTimeout(()=>render(),160);};
  form.addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);sortMode='relevance';render({scroll:true});});
  form.querySelectorAll('input,select').forEach(input=>input.addEventListener(input.type==='checkbox'||input.tagName==='SELECT'?'change':'input',()=>{
    if(input===controls.last) birthSurnameOnly='';
    if(input===controls.spouse) marriageSurnameOnly='';
    schedule();
  }));
  clear.addEventListener('click',()=>{
    form.querySelectorAll('input,select').forEach(input=>{if(input.type==='checkbox') input.checked=false;else input.value='';});
    birthSurnameOnly='';
    marriageSurnameOnly='';
    sortMode='relevance';
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
    else if(event.target.id==='catalogue-result-sort') sortMode=event.target.value;
    else return;
    render();
  });
  out.addEventListener('click',event=>{
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
    const button=event.target.closest('button[data-sort]');
    if(!button) return;
    const key=button.dataset.sort;
    sortMode=sortMode===`${key}:asc`?`${key}:desc`:`${key}:asc`;
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
  restoreUrl();
  render();
})();
