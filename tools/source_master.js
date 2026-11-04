// Master source list: one searchable, filterable table of every reference item.
// Category, country and year pages pass a fixed base filter via data attributes.
(()=>{'use strict';
const root=document.querySelector('.sc-master');if(!root)return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const d=root.dataset,P=d.prefix||'',CHUNK=100;
const LABELS={newspapers:'Newspapers',census:'Census',births:'Births & baptisms',marriages:'Marriages & banns',deaths:'Deaths & burials','wills-probate':'Wills & probate','land-tax':'Land, tax & valuation',church:'Church & parish',military:'Military & service',directories:'Directories',education:'Schools & universities',histories:'Histories & biographies',pedigrees:'Profiles & family accounts',other:'Other references'};
const LEVELS=['Original','Image','Transcript','Index','Published account','Family account','Not assessed'];
const LINKED=[['yes','Linked profile'],['pending','Profile pending'],['no','No profile']];
const SORTS={date:'Date, earliest first','-date':'Date, latest first',name:'Person named, A–Z',collection:'Collection, A–Z'};
const form=root.querySelector('.sc-m-search'),facetBox=root.querySelector('.sc-m-facets'),timeline=root.querySelector('.sc-m-timeline'),count=root.querySelector('.sc-m-count'),out=root.querySelector('.sc-m-results'),more=root.querySelector('.sc-m-more');
const KEYS=['q','cat','country','provider','decade','year','linked','level','sort'];
let rows=[],base=[],cats=[],state={},shown=0,filtered=[],zoom='';
const read=()=>{const u=new URLSearchParams(location.search);const s={};for(const k of KEYS)s[k]=u.get(P+k)||'';if(!SORTS[s.sort])s.sort='date';if(!/^\d{4}$|^undated$/.test(s.year))s.year='';if(!/^\d{3}0$/.test(s.decade))s.decade='';return s};
function write(push){const u=new URLSearchParams(location.search);for(const k of KEYS){const v=k==='sort'&&state.sort==='date'?'':state[k];if(v)u.set(P+k,v);else u.delete(P+k)}const qs=u.toString(),url=location.pathname+(qs?'?'+qs:'')+location.hash;try{history[push?'pushState':'replaceState']({sc:1},'',url)}catch{}}
const linkedOf=r=>r.p?'yes':r.pp?'pending':'no';
const decadeOf=r=>r.y==null?'':String(Math.floor(r.y/10)*10);
function hit(r,skip){
 if(skip!=='cat'&&state.cat&&!r.c.includes(cats.indexOf(state.cat)))return false;
 if(skip!=='country'&&state.country&&!(state.country==='unresolved'?!r.co.length:r.co.includes(state.country)))return false;
 if(skip!=='provider'&&state.provider&&(r.pv||'Not recorded')!==state.provider)return false;
 if(skip!=='linked'&&state.linked&&linkedOf(r)!==state.linked)return false;
 if(skip!=='level'&&state.level&&r.lv!==state.level)return false;
 if(skip!=='time'){if(state.year==='undated'?r.y!=null:state.year&&!(r.y===Number(state.year)||(r.ys||[]).includes(Number(state.year))))return false;if(state.decade&&decadeOf(r)!==state.decade)return false}
 if(state.terms.length&&!state.terms.every(t=>r.h.includes(t)))return false;
 return true}
const tally=(skip,key)=>{const m=new Map();for(const r of base)if(hit(r,skip))for(const k of [].concat(key(r)))m.set(k,(m.get(k)||0)+1);return m};
const chip=(g,v,l,n,on)=>`<button type="button" class="sc-chip" data-group="${g}" data-value="${esc(v)}" aria-pressed="${on}" ${n||on?'':'disabled'}>${esc(l)} <span>${n.toLocaleString()}</span></button>`;
function renderFacets(){
 const parts=[];
 if(d.category){parts.push(`<div class="sc-facet"><span class="sc-facet-label">Record type</span><span class="sc-chip" aria-pressed="true">${esc(LABELS[d.category]||d.category)}</span><a class="sc-m-all" href="/sources/${esc(allQuery())}">All record types →</a></div>`)}
 else{const m=tally('cat',r=>r.c.map(i=>cats[i]));parts.push(`<div class="sc-facet"><span class="sc-facet-label">Record type</span>${cats.map(c=>chip('cat',c,LABELS[c]||c,m.get(c)||0,state.cat===c)).join('')}</div>`)}
 if(!d.country){const m=tally('country',r=>r.co.length?r.co:['unresolved']);const list=[...m.keys()].filter(k=>k!=='unresolved').sort((a,b)=>m.get(b)-m.get(a));if(state.country&&!m.has(state.country))list.push(state.country);parts.push(`<div class="sc-facet"><span class="sc-facet-label">Country</span>${list.map(c=>chip('country',c,c,m.get(c)||0,state.country===c)).join('')}${chip('country','unresolved','Unresolved',m.get('unresolved')||0,state.country==='unresolved')}</div>`)}
 const pm=tally('provider',r=>r.pv||'Not recorded');const prov=[...pm.entries()].sort((a,b)=>b[1]-a[1]);const top=prov.slice(0,9).map(([k])=>k);if(state.provider&&!top.includes(state.provider))top.push(state.provider);
 const rest=prov.filter(([k])=>!top.includes(k));
 parts.push(`<div class="sc-facet"><span class="sc-facet-label">Provider</span>${top.map(k=>chip('provider',k,k,pm.get(k)||0,state.provider===k)).join('')}${rest.length?`<label class="sc-m-more-prov"><span class="sr-only">More providers</span><select data-group="provider"><option value="">${rest.length} more…</option>${rest.map(([k,n])=>`<option value="${esc(k)}">${esc(k)} (${n})</option>`).join('')}</select></label>`:''}</div>`);
 const lm=tally('linked',linkedOf);parts.push(`<div class="sc-facet"><span class="sc-facet-label">Linked profile</span>${LINKED.map(([v,l])=>chip('linked',v,l,lm.get(v)||0,state.linked===v)).join('')}</div>`);
 const vm=tally('level',r=>r.lv);parts.push(`<div class="sc-facet"><span class="sc-facet-label">Source level</span>${LEVELS.filter(v=>vm.has(v)||state.level===v).map(v=>chip('level',v,v,vm.get(v)||0,state.level===v)).join('')}</div>`);
 facetBox.innerHTML=parts.join('')}
function allQuery(){const u=new URLSearchParams();for(const k of KEYS)if(state[k]&&k!=='cat'&&!(k==='sort'&&state.sort==='date'))u.set(k,state[k]);if(d.category)u.set('cat',d.category);const s=u.toString();return s?'?'+s+'#source-list':'#source-list'}
function renderTimeline(){
 const per=new Map(),all=new Map();let undated=0,undatedHit=0;
 for(const r of base){if(r.y==null){undated++;if(hit(r,'time'))undatedHit++;continue}all.set(r.y,(all.get(r.y)||0)+1);if(hit(r,'time'))per.set(r.y,(per.get(r.y)||0)+1)}
 if(!all.size){timeline.hidden=true;return}timeline.hidden=false;
 const ys=[...all.keys()],lo0=Math.min(...ys),hi0=Math.max(...ys);
 const cz=zoom||(state.decade?String(Math.floor(state.decade/100)*100):state.year&&state.year!=='undated'?String(Math.floor(state.year/100)*100):'');
 const span=hi0-lo0;let bars='',labels='',cols,labelCols,hint;
 if(cz||span<=110){
  const lo=cz?Number(cz):Math.floor(lo0/10)*10,hi=cz?lo+99:Math.floor(hi0/10)*10+9;cols=hi-lo+1;labelCols=cols/10;let max=1;for(let y=lo;y<=hi;y++)max=Math.max(max,all.get(y)||0);
  for(let y=lo;y<=hi;y++){const n=per.get(y)||0,t=all.get(y)||0,sel=state.year===String(y)||(state.decade&&Math.floor(y/10)*10===Number(state.decade));bars+=`<button type="button" class="sc-tl-bar${sel?' is-selected':''}" data-year="${y}" ${t?'':'disabled'} title="${y}: ${n.toLocaleString()} of ${t.toLocaleString()}" aria-label="${y}: ${n} references" style="--h:${n?Math.max(4,Math.round(n/max*100)):0}%;--ht:${t?Math.max(4,Math.round(t/max*100)):0}%"></button>`}
  for(let x=lo;x<=hi;x+=10){let n=0;for(let y=x;y<x+10;y++)n+=per.get(y)||0;labels+=`<button type="button" class="sc-tl-decade${state.decade===String(x)?' is-selected':''}" data-decade="${x}" ${n?'':'disabled'}><i>${String(x).slice(0,2)}</i>${String(x).slice(2)}<u>s</u><span>${n.toLocaleString()}</span></button>`}
  hint=`References per year${cz?`, ${cz}s`:''} · select a bar or decade`;
 }else{
  const lo=Math.floor(lo0/100)*100,hi=Math.floor(hi0/10)*10;cols=(hi-lo)/10+1;labelCols=cols;const dec=new Map(),decAll=new Map();for(const [y,t] of all){const k=Math.floor(y/10)*10;decAll.set(k,(decAll.get(k)||0)+t);dec.set(k,(dec.get(k)||0)+(per.get(y)||0))}const max=Math.max(1,...decAll.values());
  for(let x=lo;x<=hi;x+=10){const n=dec.get(x)||0,t=decAll.get(x)||0;bars+=`<button type="button" class="sc-tl-bar${state.decade===String(x)?' is-selected':''}" data-decade="${x}" ${t?'':'disabled'} title="${x}s: ${n.toLocaleString()} of ${t.toLocaleString()}" aria-label="${x}s: ${n} references" style="--h:${n?Math.max(4,Math.round(n/max*100)):0}%;--ht:${t?Math.max(4,Math.round(t/max*100)):0}%"></button>`}
  for(let c=lo;c<=hi;c+=100){let n=0;for(let x=c;x<c+100;x+=10)n+=dec.get(x)||0;const w=Math.min(10,(hi-c)/10+1);labels+=`<button type="button" class="sc-tl-decade sc-tl-century" style="grid-column:span ${w}" data-century="${c}" ${n?'':'disabled'}>${c}s<span>${n.toLocaleString()}</span></button>`}
  hint='References per decade · select a decade, or a century to see its years';
 }
 const active=state.year||state.decade||zoom;
 timeline.innerHTML=`<div class="sc-tl-head"><span class="sc-facet-label">Timeline</span><span class="sc-tl-hint">${hint}</span>${undated?`<button type="button" class="sc-chip sc-tl-undated" data-undated="1" aria-pressed="${state.year==='undated'}">Date unresolved <span>${undatedHit.toLocaleString()}</span></button>`:''}${active?'<button type="button" class="sc-tl-clear">All years</button>':''}</div><div class="sc-tl-bars" style="--cols:${cols}">${bars}</div><div class="sc-tl-decades" style="--cols:${labelCols}">${labels}</div>`}
const sorters={date:(a,b)=>(a.y??9999)-(b.y??9999),name:(a,b)=>a.sn.localeCompare(b.sn)||(a.y??9999)-(b.y??9999),collection:(a,b)=>a.sc.localeCompare(b.sc)||(a.y??9999)-(b.y??9999)};
const pill=m=>`<span class="sc-m-match sc-m-match-${esc(m.toLowerCase().replace(/\W+/g,'-'))}">${esc(m)}</span>`;
function row(r,i){
 const href='/sources/'+encodeURIComponent(r.i)+'/';
 const date=r.y==null?(r.ys?r.ys.join(', '):'—'):(r.d||String(r.y));
 const people=(r.n||[]).slice(0,3).map(([n,role])=>`<span class="sc-m-name">${esc(n)}${role?` <small>${esc(role)}</small>`:''}</span>`).join('')+((r.n||[]).length>3||r.nn?`<small class="sc-m-extra">+${(r.nn||r.n.length)-3} more</small>`:'');
 const profiles=(r.p||[]).slice(0,2).map(([n,u,m])=>`<a href="${esc(u||href)}">${esc(n)}</a> ${pill(m)}`).join('<br>')+((r.p||[]).length>2?`<small class="sc-m-extra">+${(r.pn||r.p.length)-2} more</small>`:'')+(r.pp?`<span class="sc-m-pending">${pill('Draft pending')}</span>`:'');
 const cats_=r.c.map(i=>LABELS[cats[i]]||cats[i]);
 const place=(r.pl&&r.pl[0]?`<span>${esc(r.pl[0])}</span>`:'<span class="sc-dim">—</span>')+(r.co.length?`<small>${esc(r.co.join(', '))}</small>`:'');
 const prov=r.u?`<a class="sc-src sc-src-${r.k==='p'?'profile':'original'}" href="${esc(r.u)}" rel="noopener">${esc(r.pv||'Provider')} ↗</a>`:'<span class="sc-src sc-src-none" title="Provider link not recorded; see the citation">No link</span>';
 return `<tbody class="sc-m-item" data-i="${i}"><tr class="sc-m-row">`+
 `<td class="sc-m-c-date" data-label="Date"><button type="button" class="sc-m-toggle" aria-expanded="false" aria-label="Show details"></button><span>${esc(date)}</span><small>${esc(r.ds)}</small></td>`+
 `<td class="sc-m-c-people" data-label="Person named">${people||'<span class="sc-dim">—</span>'}</td>`+
 `<td class="sc-m-c-type" data-label="Record"><a href="${href}" class="sc-m-title">${esc(r.rt||cats_[0]||'Reference')}</a><small>${esc(r.t.length>110?r.t.slice(0,107)+'…':r.t)}</small></td>`+
 `<td class="sc-m-c-place" data-label="Place">${place}</td>`+
 `<td class="sc-m-c-coll" data-label="Collection">${r.cl?esc(r.cl):'<span class="sc-dim">—</span>'}<small>${esc(r.pv||'Provider not recorded')}</small></td>`+
 `<td class="sc-m-c-ref" data-label="Reference">${r.rf?esc(r.rf):'<span class="sc-dim">—</span>'}</td>`+
 `<td class="sc-m-c-prof" data-label="Linked profile">${profiles||'<span class="sc-dim">None</span>'}</td>`+
 `<td class="sc-m-c-level" data-label="Level">${esc(r.lv)}</td>`+
 `<td class="sc-m-c-links" data-label="Links"><a href="${href}">Source page</a>${prov}</td></tr></tbody>`}
function detail(r){
 const href='/sources/'+encodeURIComponent(r.i)+'/';
 const li=a=>a.length?'<ul>'+a.join('')+'</ul>':'<p class="sc-dim">None recorded.</p>';
 return `<tr class="sc-m-detail"><td colspan="9"><div class="sc-m-detail-grid"><div><h3>${esc(r.t)}</h3><p><strong>Record types:</strong> ${esc(r.c.map(i=>LABELS[cats[i]]||cats[i]).join(', '))} · <strong>Date:</strong> ${esc(r.y==null?(r.ys?r.ys.join(', '):'unresolved'):(r.d||r.y))} (${esc(r.ds)})${r.r?` · <strong>Record entries:</strong> ${r.r}`:''}</p><p><strong>Places:</strong> ${esc((r.pl||[]).join('; ')||'—')}${r.co.length?' · '+esc(r.co.join(', ')):''}</p><p><strong>Collection:</strong> ${esc(r.cl||'—')} · <strong>Provider:</strong> ${esc(r.pv||'not recorded')} · <strong>Reference:</strong> ${esc(r.rf||'—')} · <strong>Level:</strong> ${esc(r.lv)}</p></div>`+
 `<div><h4>People named</h4>${li((r.n||[]).map(([n,role])=>`<li>${esc(n)}${role?` — ${esc(role)}`:''}</li>`))}${r.nn?`<p class="sc-dim">${r.nn} people in all; see the source page.</p>`:''}</div>`+
 `<div><h4>Linked profiles</h4>${li((r.p||[]).map(([n,u,m,role])=>`<li><a href="${esc(u||href)}">${esc(n)}</a> ${pill(m)}${role?`<br><small>${esc(role)}</small>`:''}</li>`))}${r.pp?`<p>${r.pp} catalogue draft${r.pp>1?'s':''} not yet published; the link follows when the profile page exists.</p>`:''}${r.pn?`<p class="sc-dim">${r.pn} linked profiles in all.</p>`:''}<p><a href="${href}">Open the source page →</a>${r.u?` · <a href="${esc(r.u)}" rel="noopener">${esc(r.pv||'Provider')} ↗</a>`:''}</p></div></div></td></tr>`}
const HEAD='<thead><tr><th scope="col" class="sc-m-c-date"><button type="button" data-sort="date">Date</button></th><th scope="col" class="sc-m-c-people"><button type="button" data-sort="name">Person named · role</button></th><th scope="col" class="sc-m-c-type">Record</th><th scope="col" class="sc-m-c-place">Place · country</th><th scope="col" class="sc-m-c-coll"><button type="button" data-sort="collection">Collection · provider</button></th><th scope="col" class="sc-m-c-ref">Archive ref.</th><th scope="col" class="sc-m-c-prof">Linked profile</th><th scope="col" class="sc-m-c-level">Level</th><th scope="col" class="sc-m-c-links">Links</th></tr></thead>';
function appendChunk(){const t=out.querySelector('table');if(!t)return;const html=filtered.slice(shown,shown+CHUNK).map((r,j)=>row(r,shown+j)).join('');t.insertAdjacentHTML('beforeend',html);shown=Math.min(filtered.length,shown+CHUNK);more.hidden=shown>=filtered.length;more.textContent=`Show more (${(filtered.length-shown).toLocaleString()} remaining)`}
function render(){
 state.terms=state.q.toLowerCase().trim().split(/\s+/).filter(Boolean);
 filtered=base.filter(r=>hit(r));const key=state.sort.replace('-',''),dir=state.sort.startsWith('-')?-1:1;filtered.sort((a,b)=>dir*sorters[key](a,b)||a.i.localeCompare(b.i));
 renderFacets();renderTimeline();
 const total=filtered.length;shown=0;
 out.scrollTop=0;out.innerHTML=total?`<table class="sc-m-table">${HEAD}</table>`:'<p class="sc-m-empty">No references match these filters. Try a spelling variant or clear the filters; a missing match is not evidence of absence.</p>';
 for(const b of out.querySelectorAll('[data-sort]')){const on=b.dataset.sort===key;b.closest('th').setAttribute('aria-sort',on?(dir>0?'ascending':'descending'):'none')}
 appendChunk();
 count.textContent=total?`${total.toLocaleString()} of ${base.length.toLocaleString()} reference items${state.q?` matching “${state.q}”`:''} · ${SORTS[state.sort].toLowerCase()}`:'No matching reference items';
 form.elements.sort.value=state.sort;if(form.elements.q.value!==state.q)form.elements.q.value=state.q}
function set(changes,push=true){Object.assign(state,changes);write(push);render()}
// Desktop: the table scrolls in its own box so the header stays visible (the
// site shell makes the page itself unsuitable for sticky headers). Phones use
// the page scroll and load more cards as the end approaches.
const boxed=()=>out.scrollHeight>out.clientHeight+4;
const io='IntersectionObserver' in window?new IntersectionObserver(es=>{if(!boxed()&&es.some(e=>e.isIntersecting)&&shown<filtered.length)appendChunk()},{rootMargin:'600px'}):null;
out.addEventListener('scroll',()=>{if(shown<filtered.length&&out.scrollTop+out.clientHeight>out.scrollHeight-900)appendChunk()},{passive:true});
more.addEventListener('click',appendChunk);
let typing;form.addEventListener('input',ev=>{if(ev.target.name!=='q')return;clearTimeout(typing);typing=setTimeout(()=>{const first=!state.q;set({q:ev.target.value},first)},120)});
form.addEventListener('change',ev=>{if(ev.target.name==='sort')set({sort:ev.target.value})});
form.addEventListener('submit',ev=>ev.preventDefault());
form.addEventListener('reset',ev=>{ev.preventDefault();zoom='';set({q:'',cat:'',country:'',provider:'',decade:'',year:'',linked:'',level:'',sort:'date'})});
facetBox.addEventListener('click',ev=>{const b=ev.target.closest('button.sc-chip');if(!b)return;const g=b.dataset.group,v=b.dataset.value;set({[g]:state[g]===v?'':v})});
facetBox.addEventListener('change',ev=>{const s=ev.target.closest('select[data-group]');if(s&&s.value)set({[s.dataset.group]:s.value})});
timeline.addEventListener('click',ev=>{const t=ev.target.closest('button');if(!t||t.disabled)return;
 if(t.dataset.year)set({year:state.year===t.dataset.year?'':t.dataset.year,decade:''});
 else if(t.dataset.decade){const v=state.decade===t.dataset.decade?'':t.dataset.decade;set({decade:v,year:''})}
 else if(t.dataset.century){zoom=t.dataset.century;render()}
 else if(t.dataset.undated)set({year:state.year==='undated'?'':'undated',decade:''});
 else if(t.classList.contains('sc-tl-clear')){zoom='';set({year:'',decade:''})}});
out.addEventListener('click',ev=>{const s=ev.target.closest('[data-sort]');if(s){const k=s.dataset.sort;set({sort:state.sort===k?'-'+k:k});return}
 const tg=ev.target.closest('.sc-m-toggle')||(!ev.target.closest('a,button')&&ev.target.closest('.sc-m-row'));if(!tg)return;const body=tg.closest('.sc-m-item');const btn=body.querySelector('.sc-m-toggle');const open=btn.getAttribute('aria-expanded')!=='true';btn.setAttribute('aria-expanded',String(open));body.classList.toggle('is-open',open);const det=body.querySelector('.sc-m-detail');if(open&&!det)body.insertAdjacentHTML('beforeend',detail(filtered[Number(body.dataset.i)]));else if(det)det.hidden=!open});
addEventListener('popstate',()=>{state=read();zoom='';render()});
const started=performance.now();
count.textContent='Loading the complete source list…';
fetch('/assets/sources/master-index.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('master index');return r.json()}).then(data=>{
 cats=data.categories;rows=data.rows;
 for(const r of rows){r.h=[r.t,r.pv,r.cl,r.rf,r.rt,...(r.pl||[]),...(r.n||[]).flat(),...(r.p||[]).map(p=>p[0]),r.y,r.d].join(' ').toLowerCase();r.sn=((r.n&&r.n[0]&&r.n[0][0])||(r.p&&r.p[0]&&r.p[0][0])||'￿').split(/\s+/).reverse().join(' ').toLowerCase();r.sc=(r.cl||r.pv||'￿').toLowerCase()}
 const ci=d.category?cats.indexOf(d.category):-1,yr=d.year,per=d.period;
 base=rows.filter(r=>(ci<0||r.c.includes(ci))&&(!d.country||r.co.includes(d.country))&&(!yr||(yr==='undated'?r.y==null:(r.y===Number(yr)||(r.ys||[]).includes(Number(yr)))))&&(!per||(per==='undated'?r.y==null:r.y!=null&&r.y>=Number(per.slice(0,4)||0)&&(per.endsWith('onwards')||r.y<=Number(per.slice(5,9))))));
 if(per==='before-1800')base=rows.filter(r=>(ci<0||r.c.includes(ci))&&(!d.country||r.co.includes(d.country))&&r.y!=null&&r.y<1800);
 state=read();if(d.category)state.cat='';
 root.classList.add('is-live');render();if(io)io.observe(more);
 root.dataset.loadMs=String(Math.round(performance.now()-started));
}).catch(()=>{count.textContent='The interactive list is unavailable. The first references and the complete index below remain accessible.'});
})();
