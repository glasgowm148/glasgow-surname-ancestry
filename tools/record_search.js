(()=>{
  const controls={
    query:document.querySelector('#record-query'),from:document.querySelector('#record-from'),to:document.querySelector('#record-to'),
    region:document.querySelector('#record-region'),category:document.querySelector('#record-category'),
    quality:document.querySelector('#record-quality'),status:document.querySelector('#record-status')
  };
  if(!controls.query) return;
  const count=document.querySelector('#record-count');
  const out=document.querySelector('#record-results');
  const normalise=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(?:glasco|glascow|glasgo|glascoe|glassco|glassgow|glasow|glasoe|glassgo|glasko)\b/g,'glasgow');
  const esc=value=>String(value==null?'':value).replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  const params=new URLSearchParams(location.search);
  controls.query.value=params.get('q')||params.get('place')||'';
  ['from','to','region','category','quality','status'].forEach(key=>{controls[key].value=params.get(key)||'';});
  let records=[];
  function badge(value){const status=String(value||'unknown').replaceAll('_','-');return `<span class="evidence-badge evidence-${esc(status)}">${esc(String(value||'unknown').replaceAll('_',' '))}</span>`;}
  function render(){
    const terms=normalise(controls.query.value).trim().split(/\s+/).filter(Boolean);
    let from=parseInt(controls.from.value,10),to=parseInt(controls.to.value,10);
    if(!Number.isFinite(from)) from=null;if(!Number.isFinite(to)) to=null;
    const found=records.filter(record=>{
      const text=normalise([record.person,record.profile_ids,record.year,record.region,record.record_location,record.record_category,record.association,record.note,record.evidence,record.source_title,record.supporting_source_title].join(' '));
      if(terms.some(term=>!text.includes(term))) return false;
      if(from!==null&&(record.filter_year===null||record.filter_year<from)) return false;
      if(to!==null&&(record.filter_year===null||record.filter_year>to)) return false;
      if(controls.region.value&&record.region!==controls.region.value) return false;
      if(controls.category.value&&!String(record.record_category||'').includes(controls.category.value)) return false;
      if(controls.quality.value&&record.supporting_source_quality!==controls.quality.value) return false;
      if(controls.status.value&&record.supporting_source_status!==controls.status.value) return false;
      return true;
    }).sort((a,b)=>(Number(a.filter_year)||99999)-(Number(b.filter_year)||99999)||a.person.localeCompare(b.person));
    count.textContent=`${found.length.toLocaleString()} record association${found.length===1?'':'s'}${found.length>300?' · first 300 shown':''}`;
    if(!found.length) window.dispatchEvent(new CustomEvent('catalogue:zero-results',{detail:{surface:'records',query:controls.query.value}}));
    out.innerHTML=found.slice(0,300).map(record=>{
      const place=record.place_url?`<a href="${esc(record.place_url)}">${esc(record.record_location||'Place not supplied')}</a>`:esc(record.record_location||'Place not supplied');
      const sourceUrl=record.supporting_source_url||record.source_url;
      const sourceTitle=record.supporting_source_title||record.source_title||'Source/provenance unavailable';
      const source=sourceUrl?`<a href="${esc(sourceUrl)}">${esc(sourceTitle)}</a>`:esc(sourceTitle);
      return `<article class="record-card"><h3><a href="/people/${encodeURIComponent(record.catalogue_id)}.html">${esc(record.person)}</a></h3><div class="record-meta"><span>${esc(record.year||'Undated')}</span><span>${place}</span><span>${esc(record.record_category||'Other record')}</span></div><p>${esc(record.association||'Recorded occurrence')}</p>${record.note?`<p>${esc(record.note)}</p>`:''}<div class="badge-row">${badge(record.evidence)}${badge(record.supporting_source_quality)}${badge(record.supporting_source_status)}</div><details><summary>Source assessment</summary><p>${source}</p><p>${esc(record.supporting_source_reason||record.source_status||'')}</p></details></article>`;
    }).join('')||'<p class="notice">No record matches those filters.</p>';
    const next=new URLSearchParams();
    Object.entries(controls).forEach(([key,control])=>{if(control.value.trim()) next.set(key==='query'?'q':key,control.value.trim());});
    history.replaceState(null,'',`${location.pathname}${next.size?`?${next}`:''}`);
  }
  fetch(new URL('../data/records-index.json',document.currentScript.src)).then(response=>response.json()).then(data=>{records=data;render();}).catch(error=>{count.textContent='Record search unavailable';out.innerHTML=`<p class="notice">${esc(error.message)}</p>`;});
  Object.values(controls).forEach(control=>control.addEventListener(control.tagName==='SELECT'?'change':'input',render));
})();
