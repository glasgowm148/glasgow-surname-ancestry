(()=>{
  const query=document.querySelector('#place-query');
  if(!query) return;
  const region=document.querySelector('#place-region');
  const from=document.querySelector('#place-from');
  const to=document.querySelector('#place-to');
  const count=document.querySelector('#place-count');
  const out=document.querySelector('#place-results');
  const normalise=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(?:glasco|glascow|glasgo|glascoe|glassco|glassgow|glasow|glasoe|glassgo|glasko)\b/g,'glasgow');
  const esc=value=>String(value==null?'':value).replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  const params=new URLSearchParams(location.search);
  query.value=params.get('q')||'';
  region.value=params.get('region')||'';
  from.value=params.get('from')||'';
  to.value=params.get('to')||'';
  let places=[];
  function render(){
    const term=normalise(query.value).trim();
    const regionTerm=normalise(region.value);
    let yearFrom=parseInt(from.value,10),yearTo=parseInt(to.value,10);
    if(!Number.isFinite(yearFrom)) yearFrom=null;
    if(!Number.isFinite(yearTo)) yearTo=null;
    const found=places.filter(place=>{
      const haystack=normalise([place.name,place.region,...(place.surnames||[])].join(' '));
      if(term&&!term.split(/\s+/).every(part=>haystack.includes(part))) return false;
      if(regionTerm&&normalise(place.region)!==regionTerm) return false;
      if(yearFrom!==null&&(place.year_to===null||place.year_to<yearFrom)) return false;
      if(yearTo!==null&&(place.year_from===null||place.year_from>yearTo)) return false;
      return true;
    }).sort((a,b)=>(b.records-a.records)||a.name.localeCompare(b.name));
    count.textContent=`${found.length.toLocaleString()} place${found.length===1?'':'s'}${found.length>200?' · first 200 shown':''}`;
    out.innerHTML=found.slice(0,200).map(place=>`<article class="place-result-card"><h3><a href="${esc(place.url)}">${esc(place.name)}</a></h3><p>${esc(place.region)} · ${place.people.toLocaleString()} people · ${place.records.toLocaleString()} records</p><p>${place.year_from||'Undated'}${place.year_to&&place.year_to!==place.year_from?`–${place.year_to}`:''}</p>${place.surnames.length?`<p><small>${esc(place.surnames.slice(0,8).join(' · '))}</small></p>`:''}</article>`).join('')||'<p class="notice">No place matches those filters.</p>';
    if(!found.length) window.dispatchEvent(new CustomEvent('catalogue:zero-results',{detail:{surface:'places',query:query.value}}));
    const next=new URLSearchParams();
    if(query.value.trim()) next.set('q',query.value.trim());
    if(region.value) next.set('region',region.value);
    if(from.value) next.set('from',from.value);
    if(to.value) next.set('to',to.value);
    history.replaceState(null,'',`${location.pathname}${next.size?`?${next}`:''}`);
  }
  fetch(new URL('../data/places-index.json',document.currentScript.src)).then(response=>response.json()).then(data=>{places=data;render();}).catch(error=>{count.textContent='Place search unavailable';out.innerHTML=`<p class="notice">${esc(error.message)}</p>`;});
  [query,region,from,to].forEach(control=>control.addEventListener(control.tagName==='SELECT'?'change':'input',render));
})();
