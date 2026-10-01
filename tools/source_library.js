/* Progressive source library: real initial HTML; errors never replace it with a spinner. */
(()=>{'use strict';
const R=window.GlasgowResearch,V=window.GlasgowV3;
const out=document.getElementById('v3-source-results')||document.getElementById('v3-source-rows');
const form=document.getElementById('v3-source-search');
if(!out||!form||!R||!V)return;
const q=document.getElementById('v3-source-q'),kind=document.getElementById('v3-source-kind'),count=document.getElementById('v3-source-count'),pages=document.getElementById('v3-source-pages'),notice=document.getElementById('repair-source-notice');
const reset=document.getElementById('source-reset')||document.createElement('button');
if(!reset.id){reset.id='source-reset';reset.type='button';reset.className='r-button';reset.textContent='Clear search';form.append(reset)}
out.setAttribute('aria-label',out.getAttribute('aria-label')||'Source search results');
const p=new URLSearchParams(location.search),E=R.esc;
q.value=p.get('q')||'';kind.value=p.get('kind')||'all';if(!kind.value)kind.value='all';
let page=Math.max(0,(parseInt(p.get('page'),10)||1)-1),serial=0;
const initialCount=count.textContent;
const basisLabels={'exact source URL':'Linked source URL','citation text within this dossier':'Citation on person’s page','explicit archive volume and image/page':'Archive reference'};
function label(value){return basisLabels[value]||value||'Source item'}
function plural(n,one,many){return `${n.toLocaleString()} ${n===1?one:many}`}
function row(d){const date=d.from!=null?String(d.from)+(d.to!=null&&d.to!==d.from?'–'+d.to:''):'Undated';const context=R.context();const url='/sources/'+encodeURIComponent(d.id)+'/'+(context?.kind==='person'?'?person='+encodeURIComponent(context.id):'');return `<article class="v3-source-row"><div class="v3-source-date">${E(date)}<small>${d.date_basis==='reviewed event date'?'Reviewed event date':'Associated dates'}</small></div><div><span class="r-kicker" title="${E(d.basis)}">${E(label(d.basis))}</span><h3><a href="${E(url)}">${E(d.title)}</a></h3><p>${plural(d.members.length,'linked person','linked people')} · ${plural(d.citations,'citation','citations')} · ${plural(d.records,'record entry','record entries')}</p></div><span class="v3-source-availability">${d.image?'Image available':d.transcription?'Transcription available':'Citation and related records'}</span></article>`}
function resetSearch(){q.value='';kind.value='all';page=0;V.update({q:null,kind:null,page:null});render();q.focus()}
function error(e){notice.hidden=false;notice.innerHTML='<p><strong>Live source search is unavailable.</strong> The listing below is still usable. The complete source index also works without JavaScript.</p><button class="r-button" type="button" id="repair-source-retry">Retry search</button><a class="r-button" href="/sources/browse/">Browse all source items</a>';notice.title=e.message||String(e);document.getElementById('repair-source-retry').onclick=render;count.textContent=out.dataset.summary||initialCount;form.removeAttribute('aria-busy');out.removeAttribute('aria-busy')}
async function render(){const seq=++serial;notice.hidden=true;count.textContent='Searching source items…';form.setAttribute('aria-busy','true');out.setAttribute('aria-busy','true');let timer;
try{const result=await Promise.race([(async()=>{await R.ready;const ids=await R.scopeIds(),c=R.context();return R.request('sources',{q:q.value,kind:kind.value,ids:ids?[...ids]:null,from:c?.from,to:c?.to,page,size:24})})(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Source search timed out.')),12000)})]);if(seq!==serial)return;
page=result.page;const scoped=R.context()?' in selected scope':'';const range=result.count?`${page*24+1}–${Math.min(result.count,(page+1)*24)} of `:'0 of ';const text=range+result.count.toLocaleString()+' source items'+scoped;out.dataset.summary=text;count.textContent=text;
out.innerHTML=result.items.map(row).join('')||'<div class="r-empty"><h3>No matching source items.</h3><p>Try a surname, archive reference or broader date range. Clear the active scope to search the whole library.</p><button type="button" class="r-button" id="repair-clear-source-search">Clear this search</button></div>';
document.getElementById('repair-clear-source-search')?.addEventListener('click',resetSearch);V.pageNav(pages,result.pages,result.page,n=>{page=n;render();form.scrollIntoView({block:'start'})});V.update({q:q.value,kind:kind.value==='all'?null:kind.value,page:page? page+1:null});form.removeAttribute('aria-busy');out.removeAttribute('aria-busy');out.dataset.ready='true';
}catch(e){if(seq===serial)error(e)}finally{clearTimeout(timer)}}
reset.addEventListener('click',resetSearch);form.addEventListener('submit',e=>{e.preventDefault();page=0;render()});q.addEventListener('input',V.debounce(()=>{page=0;render()},260));kind.addEventListener('change',()=>{page=0;render()});document.addEventListener('glasgow:context',()=>{page=0;render()});render();
})();
