(()=>{
  const left=document.querySelector('#compare-a');
  if(!left) return;
  const right=document.querySelector('#compare-b');
  const button=document.querySelector('#compare-submit');
  const status=document.querySelector('#compare-status');
  const out=document.querySelector('#compare-results');
  const datalist=document.querySelector('#people-options');
  const dossiers=window.glasgowCompareDossiers||{};
  const normalise=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\b(?:glasco|glascow|glasgo|glascoe|glassco|glassgow|glasow|glasoe|glassgo|glasko)\b/g,'glasgow').trim();
  const esc=value=>String(value==null?'':value).replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  const params=new URLSearchParams(location.search);
  left.value=params.get('a')||'';right.value=params.get('b')||'';
  let index=[];
  button.disabled=true;
  function resolve(value){
    const term=normalise(value);if(!term) return {error:'Enter a person on both sides.'};
    const exactId=index.filter(person=>[person.id,person.catalogue_id,...(person.alternate_ids||[])].some(id=>normalise(id)===term));
    if(exactId.length===1) return {person:exactId[0]};
    const exactName=index.filter(person=>normalise(person.name)===term);
    if(exactName.length===1) return {person:exactName[0]};
    if(exactName.length>1) return {error:`${exactName.length} people share that name. Enter a WikiTree ID.`};
    return {error:`No exact person or WikiTree ID matches “${value}”.`};
  }
  const relationIds=dossier=>new Set(Object.values(dossier.relationships).flat().map(item=>item.id).filter(Boolean));
  const setValues=values=>new Set((values||[]).filter(Boolean));
  const shared=(a,b)=>[...a].filter(value=>b.has(value));
  const chips=values=>values.length?`<div class="compare-list">${values.map(value=>`<span>${esc(value)}</span>`).join('')}</div>`:'<p class="empty-state">None identified.</p>';
  const portableUrl=value=>String(value||'#').startsWith('/')?String(value).slice(1):String(value||'#');
  function personCard(dossier){
    const quality={};dossier.evidence.forEach(item=>quality[item.source_quality]=(quality[item.source_quality]||0)+1);
    const family=Object.entries(dossier.relationships).map(([group,items])=>items.length?`<p><strong>${esc(group)}:</strong> ${items.map(item=>`<a href="${esc(portableUrl(item.url||item.wikitree_url||'#'))}">${esc(item.name||item.id)}</a>`).join(' · ')}</p>`:'').join('');
    return `<article class="compare-card"><h3><a href="${esc(portableUrl(dossier.local_url||dossier.wikitree_url))}">${esc(dossier.name)}</a></h3><p>${esc(dossier.vitals.birth.date||'?')} – ${esc(dossier.vitals.death.date||'?')}</p><p>${esc(dossier.vitals.birth.place||'Birthplace unknown')} → ${esc(dossier.vitals.death.place||'Death place unknown')}</p>${family}<p><strong>Evidence:</strong> ${esc(Object.entries(quality).map(([key,value])=>`${key.replaceAll('_',' ')} ${value}`).join(' · ')||'None')}</p><p><strong>Open questions:</strong> ${Number(dossier.open_question_count)||0}</p></article>`;
  }
  async function compare(){
    if(!index.length){status.textContent='The comparison index is not ready.';out.innerHTML='';return;}
    const a=resolve(left.value),b=resolve(right.value);
    if(a.error||b.error){status.textContent=a.error||b.error;out.innerHTML='';return;}
    status.textContent='Preparing comparison…';
    try{
      const da=dossiers[a.person.catalogue_id],db=dossiers[b.person.catalogue_id];
      if(!da||!db) throw new Error('The bundled comparison data is incomplete. Rebuild the catalogue.');
      const sharedLocations=shared(setValues(da.identity.locations),setValues(db.identity.locations));
      const sharedClusters=shared(setValues(da.identity.research_clusters),setValues(db.identity.research_clusters));
      const sharedRelatives=shared(relationIds(da),relationIds(db));
      const direct=Object.values(da.relationships).flat().find(item=>item.id===db.id||db.alternate_ids.includes(item.id));
      const datesA=da.evidence.map(item=>item.date).filter(Boolean),datesB=db.evidence.map(item=>item.date).filter(Boolean);
      status.textContent=`Comparing ${da.name} and ${db.name}`;
      out.innerHTML=`${personCard(da)}${personCard(db)}<article class="compare-card compare-shared"><h3>Connections and contrasts</h3><p><strong>Direct relationship:</strong> ${direct?`${esc(direct.relationship)} · ${esc(direct.status_label||direct.status||'tree only')}`:'None recorded'}</p><h4>Shared places</h4>${chips(sharedLocations)}<h4>Shared research clusters</h4>${chips(sharedClusters)}<h4>Shared relatives</h4>${chips(sharedRelatives)}<h4>Recorded date ranges</h4><p>${esc(datesA[0]||'Undated')} – ${esc(datesA.at(-1)||'Undated')} compared with ${esc(datesB[0]||'Undated')} – ${esc(datesB.at(-1)||'Undated')}</p><div class="actions"><a class="button secondary" href="${esc(portableUrl(da.network_url))}">First family network JSON</a><a class="button secondary" href="${esc(portableUrl(db.network_url))}">Second family network JSON</a></div></article>`;
      history.replaceState(null,'',`${location.pathname}?a=${encodeURIComponent(a.person.id)}&b=${encodeURIComponent(b.person.id)}`);
    }catch(error){status.textContent='Comparison unavailable';out.innerHTML=`<p class="notice">${esc(error.message)}</p>`;}
  }
  function initialise(data){
    index=data;
    datalist.innerHTML=data.map(person=>`<option value="${esc(person.id)}">${esc(person.name)}</option>`).join('');
    button.disabled=false;
    status.textContent=right.value?'Ready to compare':'Choose a second person to compare.';
    if(left.value&&right.value) compare();
  }
  const bundled=window.glasgowCompareIndex;
  if(Array.isArray(bundled)&&bundled.length&&Object.keys(dossiers).length){
    initialise(bundled);
  }else{
    status.textContent='Comparison assets unavailable. Rebuild or redeploy the catalogue.';
    button.disabled=true;
  }
  button.addEventListener('click',compare);
  [left,right].forEach(input=>input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();compare();}}));
})();
