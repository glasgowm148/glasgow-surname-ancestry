(()=>{
  const controls={
    query:document.querySelector('#record-query'),from:document.querySelector('#record-from'),to:document.querySelector('#record-to'),
    region:document.querySelector('#record-region'),category:document.querySelector('#record-category'),
    quality:document.querySelector('#record-quality'),status:document.querySelector('#record-status,#r-record-citation'),sort:document.querySelector('#record-sort')
  };
  if(!controls.query) return;
  const count=document.querySelector('#record-count');
  const out=document.querySelector('#record-results'),reset=document.querySelector('#record-reset');
  if(!count||!out) return;
  const pageSize=50;
  const dataUrl=new URL('../data/records-index.json',document.currentScript?.src||location.href);
  const normalise=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(?:glasco|glascow|glasgo|glascoe|glassco|glassgow|glasow|glasoe|glassgo|glasko)\b/g,'glasgow');
  const esc=value=>String(value==null?'':value).replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  const params=new URLSearchParams(location.search);
  controls.query.value=params.get('q')||'';
  ['from','to','region','category','quality','status','sort'].forEach(key=>{if(controls[key])controls[key].value=params.get(key)||controls[key].value||'';});
  let records=[],page=Math.max(0,(Number(params.get('page'))||1)-1),scopeIds=null,scopeLabel='',loaded=false;
  const canonical=value=>window.GlasgowResearch?.canonical?.(value)||String(value||'').toLowerCase();
  function badge(value,kind='evidence'){const status=String(value||'unknown').replaceAll('_','-');const labels={unknown:kind==='evidence'?'Evidence unassessed':'Unclassified',derivative:'Index / transcription',tree_only:'Tree / profile only',candidate:'Possible source match',unresolved:'Citation needed',explicit:'Source cited'};return `<span class="evidence-badge evidence-${esc(status)}">${esc(labels[value]||String(value||'unknown').replaceAll('_',' '))}</span>`;}
  function pager(total){const pages=Math.ceil(total/pageSize);return pages<2?'':`<nav class="record-pagination" aria-label="Record result pages"><button type="button" data-record-page="${page-1}" ${page===0?'disabled':''}>Previous</button><span>Page ${page+1} of ${pages}</span><button type="button" data-record-page="${page+1}" ${page>=pages-1?'disabled':''}>Next</button></nav>`;}
  function updateUrl(){const next=new URLSearchParams();['person','branch','place','scope','country'].forEach(key=>{if(params.has(key))next.set(key,params.get(key));});Object.entries(controls).forEach(([key,control])=>{if(control?.value.trim())next.set(key==='query'?'q':key,control.value.trim());});if(page)next.set('page',page+1);history.replaceState(null,'',`${location.pathname}${next.size?`?${next}`:''}`);}
  function render(){
    if(!loaded)return;
    const terms=normalise(controls.query.value).trim().split(/\s+/).filter(Boolean);
    let from=parseInt(controls.from.value,10),to=parseInt(controls.to.value,10);
    if(!Number.isFinite(from)) from=null;if(!Number.isFinite(to)) to=null;
    if(from!==null&&to!==null&&from>to){count.textContent='Start year must be before end year.';out.innerHTML='';return;}
    const found=records.filter(record=>{
      const text=normalise([record.person,record.profile_ids,record.year,record.region,record.record_location,record.record_category,record.association,record.note,record.evidence,record.source_title,record.supporting_source_title].join(' '));
      if(terms.some(term=>!text.includes(term))) return false;
      if(from!==null&&(record.filter_year===null||record.filter_year<from)) return false;
      if(to!==null&&(record.filter_year===null||record.filter_year>to)) return false;
      if(controls.region.value&&record.region!==controls.region.value) return false;
      if(controls.category.value&&!String(record.record_category||'').includes(controls.category.value)) return false;
      if(controls.quality.value&&record.supporting_source_quality!==controls.quality.value) return false;
      if(controls.status.value&&record.supporting_source_status!==controls.status.value) return false;
      if(scopeIds&&!scopeIds.has(canonical(record.catalogue_id))) return false;
      if(params.get('place')&&!normalise(record.record_location).includes(normalise(params.get('place')))&&!decodeURIComponent(record.place_url||'').includes('/places/'+params.get('place')+'.html'))return false;
      return true;
    }).sort((a,b)=>{if(controls.sort?.value==='name')return a.person.localeCompare(b.person);const ay=a.filter_year==null?null:Number(a.filter_year),by=b.filter_year==null?null:Number(b.filter_year);if(ay===null||by===null)return ay===by?a.person.localeCompare(b.person):ay===null?1:-1;const date=ay-by;return controls.sort?.value==='date-desc'?-date:date||a.person.localeCompare(b.person);});
    page=Math.min(page,Math.max(0,Math.ceil(found.length/pageSize)-1));
    const start=found.length?page*pageSize+1:0,end=Math.min((page+1)*pageSize,found.length);
    count.textContent=found.length?`${start.toLocaleString()}–${end.toLocaleString()} of ${found.length.toLocaleString()} record entries`:'No record matches those filters.';
    if(!found.length) window.dispatchEvent(new CustomEvent('catalogue:zero-results',{detail:{surface:'records',query:controls.query.value}}));
    out.innerHTML=found.slice(page*pageSize,(page+1)*pageSize).map(record=>{
      const place=record.place_url?`<a class="record-place" href="${esc(record.place_url)}">${esc(record.record_location||'Place not supplied')}</a>`:`<span class="record-place">${esc(record.record_location||'Place not supplied')}</span>`;
      const sourceUrl=record.supporting_source_url||record.source_url;
      const sourceTitle=record.supporting_source_title||record.source_title||'Source reference unavailable';
      const source=sourceUrl?`<a class="record-source" href="${esc(sourceUrl)}">${esc(sourceTitle)}</a>`:`<span class="record-source">${esc(sourceTitle)}</span>`;
      return `<article class="record-card record-result"><header class="record-result-head"><span class="record-date">${esc(record.year||'Undated')}</span><span class="record-type">${esc(record.record_category||'Other record')}</span></header><h3 class="record-person"><a href="/people/${encodeURIComponent(record.catalogue_id)}.html">${esc(record.person)}</a></h3><div class="record-meta">${place}</div><p>${esc(record.association||'Recorded occurrence')}</p><div class="badge-row">${badge(record.evidence)}${badge(record.supporting_source_quality,'source')}${badge(record.supporting_source_status,'citation')}</div><details><summary>Record and source details</summary>${record.note?`<p>${esc(record.note)}</p>`:''}<p>${source}</p><p>${esc(record.supporting_source_reason||record.source_status||'')}</p></details></article>`;
    }).join('')||'<p class="notice">No record matches those filters.</p>';
    out.insertAdjacentHTML('beforeend',pager(found.length));
    out.querySelectorAll('[data-record-page]').forEach(button=>button.addEventListener('click',()=>{page=Number(button.dataset.recordPage);render();count.scrollIntoView({block:'start'});}));
    updateUrl();
  }
  async function load(){
    loaded=false;count.textContent='Loading records…';out.innerHTML='';
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
    const timed=promise=>Promise.race([promise,new Promise((_,reject)=>{
      if(controller.signal.aborted)reject(new DOMException('Timed out','AbortError'));
      else controller.signal.addEventListener('abort',()=>reject(new DOMException('Timed out','AbortError')),{once:true});
    })]);
    try{
      const R=window.GlasgowResearch;
      if(['person','branch'].some(key=>params.has(key))){
        if(!R)throw Error('The selected research scope could not be loaded.');
        await timed(R.ready);
        const context=R.context(),key=params.has('branch')?'branch':'person';
        if(!context||context.kind!==key||canonical(context.id)!==canonical(params.get(key)))throw Error('The selected research scope could not be found.');
        scopeIds=await timed(R.scopeIds(context));scopeLabel=context.name;
      }else if(params.has('place'))scopeLabel=params.get('place');
      const scope=document.querySelector('#records-scope');
      if(scope){scope.hidden=!scopeLabel;scope.textContent=scopeLabel?`Showing records for ${scopeLabel}.`:'';}
      const response=await fetch(dataUrl,{signal:controller.signal});
      if(!response.ok)throw Error(`Record data could not be loaded (${response.status}).`);
      const data=await response.json();
      if(!Array.isArray(data))throw Error('Record data is malformed.');
      records=data;loaded=true;render();
    }catch(error){
      count.textContent='Record search unavailable';
      out.innerHTML=`<p class="notice">${esc(error.name==='AbortError'?'Record data took too long to load.':error.message)} <button class="record-retry" type="button" id="record-retry">Retry</button></p>`;
      out.querySelector('#record-retry')?.addEventListener('click',load);
    }finally{clearTimeout(timer)}
  }
  Object.values(controls).forEach(control=>control?.addEventListener(control.tagName==='SELECT'?'change':'input',()=>{page=0;render();}));
  reset?.addEventListener('click',()=>{Object.values(controls).forEach(control=>{if(control)control.value='';});if(controls.sort)controls.sort.value='date-asc';page=0;render();controls.query.focus();});
  load();
})();
