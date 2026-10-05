(()=>{'use strict';const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const params=new URLSearchParams(location.search);let index;const years=r=>r.years||(r.year?[r.year]:[]);const inYear=(r,y)=>y==='undated'?years(r).length===0:years(r).includes(Number(y));
function card(r){const href='/sources/'+encodeURIComponent(r.id)+'/';const original=r.original_url?`<a href="${esc(r.original_url)}">${r.original_kind==='profile'?'Profile / family account':'Original / provider link'} ↗</a>`:'<span>Original link not recorded; see the citation</span>';const places=r.places.slice(0,2).join(' · ');const people=r.categories.includes('census')&&(r.people||[]).length?`<p class="sc-census-people">People linked to this reference: ${r.people.map(p=>`<a href="${esc(p.url||href)}">${esc(p.name)}</a>`).join(' · ')}</p>`:'';return `<article class="sc-reference"><div class="sc-year">${years(r).join(', ')||'Year unresolved'}<small>${esc(r.year_basis)}</small></div><div><h3><a href="${href}">${esc(r.display_title||r.title)}</a></h3><p>${r.members.length} linked people · ${r.citations} citations</p>${people}${places?`<p>Linked record places: ${esc(places)}</p>`:``}<div class="sc-record-links"><a href="${href}">Evidence & people</a>${original}</div></div></article>`}
for(const root of document.querySelectorAll('.sc-browser')){const form=root.querySelector('form'),out=root.querySelector('.sc-results'),count=root.querySelector('.sc-result-count'),pager=root.querySelector('.sc-pager');let page=0,rows=[];const d=root.dataset;const fields=['q','country','year','availability'];for(const k of fields)if(params.has(k))form.elements[k].value=params.get(k);if(d.country){form.elements.country.value=d.country;form.elements.country.disabled=true}if(d.year){form.elements.year.value=d.year;form.elements.year.disabled=true}const matchBase=r=>r.categories.includes(d.category)&&(!d.country||r.countries.includes(d.country))&&(!d.year||inYear(r,d.year))&&(!d.period||(d.period==='undated'?r.year===null:d.period==='before-1800'?r.year!==null&&r.year<1800:d.period==='1950-onwards'?r.year>=1950:r.year!==null&&r.year>=Number(d.period.slice(0,4))&&r.year<=Number(d.period.slice(5,9))));function render(){const q=form.elements.q.value.toLowerCase().trim().split(/\s+/).filter(Boolean),country=form.elements.country.value,year=form.elements.year.value,availability=form.elements.availability.value;const filtered=rows.filter(r=>(!country||r.countries.includes(country))&&(!year||inYear(r,year))&&(!availability||(availability==='original'?r.original_kind==='record or provider':!r.original_url))&&q.every(t=>[r.title,...r.places,...r.members,...(r.people||[]).map(p=>p.name)].join(' ').toLowerCase().includes(t)));const total=filtered.length;page=Math.max(0,Math.min(page,Math.max(0,Math.ceil(total/24)-1)));out.innerHTML=filtered.slice(page*24,(page+1)*24).map(card).join('')||'<p>No references match these filters. Try a spelling variant or clear the filters; a missing match is not evidence of absence.</p>';count.textContent=total?`${page*24+1}–${Math.min((page+1)*24,total)} of ${total.toLocaleString()} reference items · earliest first`:'No matching reference items';pager.innerHTML=total>24?`<button type="button" data-step="-1" ${page===0?'disabled':''}>← Previous</button><span>Page ${page+1} of ${Math.ceil(total/24)}</span><button type="button" data-step="1" ${(page+1)*24>=total?'disabled':''}>Next →</button>`:'';}form.addEventListener('submit',ev=>ev.preventDefault());form.addEventListener('input',()=>{page=0;render()});form.addEventListener('change',()=>{page=0;render()});form.addEventListener('reset',()=>setTimeout(()=>{if(d.country)form.elements.country.value=d.country;if(d.year)form.elements.year.value=d.year;page=0;render()},0));pager.addEventListener('click',ev=>{const b=ev.target.closest('button[data-step]');if(b){page+=Number(b.dataset.step);render();count.scrollIntoView({block:'start'})}});(index||(index=fetch('/assets/sources/collection-index.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('source index');return r.json()}))).then(data=>{rows=data.filter(matchBase).sort((a,b)=>(a.year??9999)-(b.year??9999)||a.title.localeCompare(b.title)||a.id.localeCompare(b.id));render()}).catch(()=>{count.textContent='Search unavailable. Use the complete collection index below; all reference links remain accessible.'})}
const nf=document.querySelector('.sc-newspaper-filters');const section=document.getElementById('newspaper-records');let npOpen=()=>{};
if(nf&&section){
 const cards=[...section.querySelectorAll('.sc-newspaper-list>.sc-newspaper')],count=document.getElementById('sc-newspaper-count');
 const list=section.querySelector('.sc-newspaper-list'),tools=section.querySelector('.sc-np-tools'),timeline=section.querySelector('.sc-np-timeline'),facetBox=section.querySelector('.sc-np-facets'),peopleBox=section.querySelector('.sc-np-people');
 const evidenceControl=nf.elements.evidence||nf.elements.relationship||nf.elements.relationships;
 const identityControl=nf.elements.identity;
 const relationshipTags=new Set(['spouse','parent-child','siblings','other-kin']);
 const valid={clip:new Set(['','1','relationships','spouse','parent-child','siblings','other-kin','occupation','residence','birth','death','unassigned','matched']),identity:new Set(['','unassigned','possible','matched','strong','probable']),evidence:new Set(['','relationships','spouse','parent-child','siblings','other-kin','occupation','residence','birth','death'])};
 const setFromUrl=(control,names,values)=>{if(!control)return;for(const name of names)if(params.has(name)){const value=params.get(name);if(!values||values.has(value)){if(control.tagName==='SELECT'&&![...control.options].some(o=>(o.value||o.text)===value)){const o=document.createElement('option');o.value=value;o.textContent=value;o.hidden=true;control.append(o)}control.value=value;return}}};
 setFromUrl(nf.elements.q,['q']);setFromUrl(nf.elements.year,['year']);setFromUrl(nf.elements.paper,['paper']);
 setFromUrl(nf.elements.clip,['clip'],valid.clip);setFromUrl(evidenceControl,['evidence','relationship','relationships'],valid.evidence);setFromUrl(identityControl,['identity'],valid.identity);
 // Chip facets and timeline state (kept in the URL with the form controls).
 let events=[];try{events=JSON.parse(section.dataset.events||'[]')}catch{}
 const eventLabels=new Map(events);
 const identityChips=[['matched','Probable / strong'],['possible','Possible'],['unassigned','No profile yet']];
 const state={event:params.get('event')||'',country:params.get('country')||'',variant:params.get('variant')||'',decade:/^\d{4}$/.test(params.get('decade')||'')?params.get('decade'):'',view:params.get('view')==='people'?'people':'notices'};
 const info=cards.map(c=>({c,years:(c.dataset.year||'').split(',').filter(Boolean),first:Number((c.dataset.year||'').split(',')[0])||null,papers:(c.dataset.paper||'').split('|'),tags:new Set((c.dataset.evidence||'').trim().split(/\s+/).filter(Boolean)),identity:c.dataset.identity||'possible',event:c.dataset.event||'other',country:c.dataset.country||'Unresolved',variants:(c.dataset.variant||'').split(/\s+/).filter(Boolean),text:c.textContent.toLowerCase()}));
 const evidenceHit=(r,value)=>!value||(value==='relationships'?(r.tags.has('relationships')||[...relationshipTags].some(t=>r.tags.has(t))):r.tags.has(value));
 const identityHit=(r,value)=>!value||(value==='matched'?(r.identity==='probable'||r.identity==='strong'):r.identity===value);
 function hits(r,skip){
  const terms=(nf.elements.q?.value||'').toLowerCase().trim().split(/\s+/).filter(Boolean),clip=nf.elements.clip?.value||'';
  if(!terms.every(t=>r.text.includes(t)))return false;
  if(skip!=='time'){const y=nf.elements.year?.value;if(y&&!r.years.includes(y))return false;if(state.decade&&!r.years.some(v=>v.slice(0,3)===state.decade.slice(0,3)))return false}
  if(nf.elements.paper?.value&&!r.papers.includes(nf.elements.paper.value))return false;
  if(clip==='1'&&r.c.dataset.clip!=='1')return false;
  if(clip&&clip!=='1'&&!(clip==='unassigned'||clip==='matched'?identityHit(r,clip):evidenceHit(r,clip)))return false;
  if(!evidenceHit(r,evidenceControl?.value||''))return false;
  if(skip!=='identity'&&!identityHit(r,identityControl?.value||''))return false;
  if(skip!=='event'&&state.event&&r.event!==state.event)return false;
  if(skip!=='country'&&state.country&&r.country!==state.country)return false;
  if(skip!=='variant'&&state.variant&&!r.variants.includes(state.variant))return false;
  return true;
 }
 const chip=(group,value,label,n,on)=>`<button type="button" class="sc-chip" data-group="${group}" data-value="${esc(value)}" aria-pressed="${on}"${n||on?'':' disabled'}>${esc(label)} <span>${n}</span></button>`;
 function renderFacets(){
  const tally=(skip,key)=>{const m=new Map();for(const r of info)if(hits(r,skip))for(const k of [].concat(key(r)))m.set(k,(m.get(k)||0)+1);return m};
  const ev=tally('event',r=>r.event),co=tally('country',r=>r.country),va=tally('variant',r=>r.variants),id=new Map(identityChips.map(([v])=>[v,info.filter(r=>hits(r,'identity')&&identityHit(r,v)).length]));
  const countries=[...new Set(info.map(r=>r.country))].sort((a,b)=>a==='Unresolved'?1:b==='Unresolved'?-1:a.localeCompare(b));
  const variants=[...new Set(info.flatMap(r=>r.variants))].sort((a,b)=>(a==='Glasgow'?-1:b==='Glasgow'?1:a.localeCompare(b)));
  const idValue=identityControl?.value||'';
  facetBox.innerHTML=
   `<div class="sc-facet"><span class="sc-facet-label">Event</span>${events.filter(([k])=>info.some(r=>r.event===k)).map(([k,l])=>chip('event',k,l,ev.get(k)||0,state.event===k)).join('')}</div>`+
   `<div class="sc-facet"><span class="sc-facet-label">Published in</span>${countries.map(c=>chip('country',c,c==='Unresolved'?'Country unresolved':c,co.get(c)||0,state.country===c)).join('')}</div>`+
   `<div class="sc-facet"><span class="sc-facet-label">Spelling</span>${variants.map(v=>chip('variant',v,v,va.get(v)||0,state.variant===v)).join('')}</div>`+
   `<div class="sc-facet"><span class="sc-facet-label">Profile match</span>${identityChips.map(([v,l])=>chip('identity',v,l,id.get(v)||0,idValue===v||(v==='possible'&&idValue==='possible'))).join('')}</div>`;
 }
 function renderTimeline(){
  const firstYears=info.map(r=>r.first).filter(Boolean);if(!firstYears.length){timeline.hidden=true;return}
  const lo=Math.floor(Math.min(...firstYears)/10)*10,hi=Math.floor(Math.max(...firstYears)/10)*10+9;
  const per=new Map(),all=new Map();for(const r of info){for(const y of r.years){all.set(y,(all.get(y)||0)+1);if(hits(r,'time'))per.set(y,(per.get(y)||0)+1)}}
  const max=Math.max(1,...all.values()),year=nf.elements.year?.value||'';
  let bars='',labels='';
  for(let y=lo;y<=hi;y++){const n=per.get(String(y))||0,t=all.get(String(y))||0,sel=year===String(y)||(state.decade&&String(y).slice(0,3)===state.decade.slice(0,3));bars+=`<button type="button" class="sc-tl-bar${sel?' is-selected':''}" data-year="${y}" ${t?'':'disabled'} title="${y}: ${n} notice${n===1?'':'s'}" aria-label="${y}: ${n} notices" style="--h:${n?Math.max(6,Math.round(n/max*100)):0}%;--ht:${t?Math.max(6,Math.round(t/max*100)):0}%"></button>`}
  for(let d=lo;d<=hi;d+=10){let n=0;for(let y=d;y<d+10;y++)n+=per.get(String(y))||0;labels+=`<button type="button" class="sc-tl-decade${state.decade===String(d)?' is-selected':''}" data-decade="${d}" ${n?'':'disabled'}><i>${String(d).slice(0,2)}</i>${String(d).slice(2)}<u>s</u><span>${n}</span></button>`}
  timeline.innerHTML=`<div class="sc-tl-head"><span class="sc-facet-label">Timeline</span><span class="sc-tl-hint">Notices per year · select a bar or decade</span>${year||state.decade?'<button type="button" class="sc-tl-clear">All years</button>':''}</div><div class="sc-tl-bars" style="--cols:${hi-lo+1}">${bars}</div><div class="sc-tl-decades" style="--cols:${(hi-lo+1)/10}">${labels}</div>`;
 }
 function syncUrl(){
  const q=new URLSearchParams();const put=(k,v)=>{if(v)q.set(k,v)};
  put('q',nf.elements.q?.value.trim());put('year',nf.elements.year?.value);put('decade',state.decade);put('paper',nf.elements.paper?.value);put('clip',nf.elements.clip?.value);put('evidence',evidenceControl?.value);put('identity',identityControl?.value);put('event',state.event);put('country',state.country);put('variant',state.variant);if(state.view==='people')q.set('view','people');
  const qs=q.toString();try{history.replaceState(history.state,'',location.pathname+(qs?'?'+qs:'')+location.hash)}catch{}
 }
 function renderPeople(visible){
  const people=new Map(),none=[];
  for(const r of visible){const ms=[...r.c.querySelectorAll('.sc-profile-match:not(.sc-draft)')];let any=false;for(const m of ms){const a=m.querySelector('.sc-profile-head a');if(!a)continue;any=true;const key=a.getAttribute('href');if(!people.has(key))people.set(key,{name:a.textContent.trim(),href:key,rows:[]});const p=people.get(key);if(!p.rows.some(x=>x.r===r))p.rows.push({r,conf:(m.querySelector('.sc-confidence-badge')?.textContent||'').trim()})}if(!any)none.push(r)}
  const rank={strong:0,probable:1,possible:2};const best=p=>Math.min(...p.rows.map(x=>rank[x.conf.toLowerCase()]??3));
  const sorted=[...people.values()].sort((a,b)=>best(a)-best(b)||b.rows.length-a.rows.length||a.name.localeCompare(b.name));
  const line=(r,conf)=>{const c=r.c,name=[...c.querySelectorAll('.sc-target-name')].map(n=>n.textContent).join(' & '),kind=c.querySelector('.sc-record-kind')?.textContent||'';return `<li><a href="#${esc(c.id)}" data-open="${esc(c.id)}"><b>${esc(c.dataset.year.split(',')[0])}</b> ${esc(name)} <span>· ${esc(kind)} · ${esc((c.dataset.paper||'').split('|')[0])}</span></a>${conf?` <span class="sc-confidence-badge sc-conf-${esc(conf.toLowerCase())}">${esc(conf)}</span>`:''}</li>`};
  peopleBox.innerHTML=`<p class="sc-people-intro">${sorted.length} WikiTree profiles are suggested as candidates for the ${visible.length} notices shown. A notice can list several candidates, so it may appear under more than one person; strongest assessments first.</p>`+sorted.map(p=>`<section class="sc-person"><h3><a href="${esc(p.href)}">${esc(p.name)}</a> <span>${p.rows.length} notice${p.rows.length===1?'':'s'}</span></h3><ul>${p.rows.sort((a,b)=>(a.r.first||0)-(b.r.first||0)).map(x=>line(x.r,x.conf)).join('')}</ul></section>`).join('')+(none.length?`<section class="sc-person sc-person-unresolved"><h3>No profile assigned yet <span>${none.length} notice${none.length===1?'':'s'}</span></h3><p class="sc-muted">Research queue: notices whose subject has no checked candidate profile.</p><ul>${none.map(r=>line(r,'')).join('')}</ul></section>`:'');
 }
 function filter(){
  let n=0,pages=0;const visible=[];
  for(const r of info){const hit=hits(r);r.c.hidden=!hit;if(hit){n++;pages+=Number(r.c.dataset.groupSize||1);visible.push(r)}}
  count.textContent=`${n} of ${cards.length} distinct notices · ${pages} source ${pages===1?'page':'pages'} · earliest first`;
  renderFacets();renderTimeline();
  const people=state.view==='people';list.hidden=people;peopleBox.hidden=!people;if(people)renderPeople(visible);
  for(const b of tools.querySelectorAll('[data-view]'))b.setAttribute('aria-selected',String(b.dataset.view===state.view));
  syncUrl();
 }
 // Compact rows: each card header becomes a toggle; full detail opens in place.
 const expanded=tools.querySelector('[name=expanded]');
 const setOpen=(c,open)=>{c.classList.toggle('is-open',open);c.querySelector('.sc-np-toggle')?.setAttribute('aria-expanded',String(open))};
 for(const c of cards){const h=c.querySelector('.sc-card-header');if(!h)continue;const b=document.createElement('button');b.type='button';b.className='sc-np-toggle';b.setAttribute('aria-expanded','false');b.setAttribute('aria-controls',c.id);b.innerHTML='<span class="sc-np-toggle-open">Open notice</span><span class="sc-np-toggle-close">Close</span>';h.append(b);h.addEventListener('click',ev=>{if(!section.classList.contains('sc-compact'))return;if(ev.target.closest('a,summary,details')&&!ev.target.closest('.sc-np-toggle'))return;setOpen(c,!c.classList.contains('is-open'))})}
 const setDensity=()=>{section.classList.toggle('sc-compact',!expanded.checked)};
 let compactPref=null;try{compactPref=localStorage.getItem('sc-np-expanded')}catch{}
 expanded.checked=compactPref==='1';setDensity();
 expanded.addEventListener('change',()=>{setDensity();try{localStorage.setItem('sc-np-expanded',expanded.checked?'1':'0')}catch{}});
 tools.hidden=false;timeline.hidden=false;facetBox.hidden=false;
 const identityLabel=identityControl?.closest('label');if(identityLabel)identityLabel.hidden=true;
 facetBox.addEventListener('click',ev=>{const b=ev.target.closest('.sc-chip');if(!b)return;const g=b.dataset.group,v=b.dataset.value;if(g==='identity'){identityControl.value=identityControl.value===v?'':v}else state[g]=state[g]===v?'':v;filter()});
 timeline.addEventListener('click',ev=>{const bar=ev.target.closest('.sc-tl-bar'),dec=ev.target.closest('.sc-tl-decade'),clr=ev.target.closest('.sc-tl-clear');const ys=nf.elements.year;
  if(bar){const y=bar.dataset.year;state.decade='';if(ys){if(![...ys.options].some(o=>(o.value||o.text)===y)){const o=document.createElement('option');o.textContent=y;o.hidden=true;ys.append(o)}ys.value=ys.value===y?'':y}}
  else if(dec){const d=dec.dataset.decade;if(ys)ys.value='';state.decade=state.decade===d?'':d}
  else if(clr){if(ys)ys.value='';state.decade=''}else return;filter()});
 tools.addEventListener('click',ev=>{const b=ev.target.closest('[data-view]');if(!b)return;state.view=b.dataset.view;filter()});
 peopleBox.addEventListener('click',ev=>{const a=ev.target.closest('[data-open]');if(!a)return;ev.preventDefault();npOpen(a.dataset.open,true)});
 npOpen=(id,scroll)=>{const c=document.getElementById(id);if(!c||!cards.includes(c))return false;if(c.hidden){nf.reset();state.event=state.country=state.variant=state.decade=''}state.view='notices';filter();setOpen(c,true);if(scroll){try{history.replaceState(history.state,'',location.pathname+location.search+'#'+id)}catch{}c.scrollIntoView({block:'start'})}return true};
 nf.elements.year?.addEventListener('change',()=>{state.decade=''});
 nf.addEventListener('submit',ev=>ev.preventDefault());nf.addEventListener('input',filter);nf.addEventListener('change',filter);nf.addEventListener('reset',()=>setTimeout(()=>{state.event=state.country=state.variant=state.decade='';filter()},0));filter()
}
function openAnchor(){const el=document.getElementById(location.hash.slice(1));if(!el)return;for(let p=el.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;const card=el.closest('.sc-newspaper');if(card&&npOpen(card.id,false)){setTimeout(()=>el.scrollIntoView(),0);return}if(card&&card.hidden){nf?.reset();setTimeout(()=>{card.hidden=false;card.scrollIntoView()},0)}}addEventListener('hashchange',openAnchor);openAnchor();
})();

