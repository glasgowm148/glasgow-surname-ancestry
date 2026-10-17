/* Shared identity, context and previews. No dependencies and no inferred identities. */
(()=>{'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(glasgo|glasco|glascoe|glassgow|glascow)\b/g,'glasgow').replace(/[^a-z0-9]+/g,' ').trim();
const palette={scotland:{label:'Scotland',color:'#496e95'},ireland:{label:'Ireland / Ulster',color:'#33786b'},america:{label:'United States',color:'#aa7036'},canada:{label:'Canada',color:'#9a5973'},oceania:{label:'Australia / New Zealand',color:'#776499'},england:{label:'England / Wales',color:'#887527'},other:{label:'Other / unknown',color:'#777c76'}};
function versioned(url){try{const u=new URL(url,location.href),v=globalThis.GlasgowDataVersions?.[u.pathname];if(v)u.searchParams.set('v',v);return u.href}catch{return url}}
const cache=new Map();async function json(url){url=versioned(url);if(cache.has(url))return cache.get(url);const promise=fetch(url,{credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('Could not load '+url+' ('+r.status+').');return r.json()}).catch(e=>{cache.delete(url);throw e});cache.set(url,promise);return promise}
let registryPromise;const registry=()=>registryPromise??=(json('/assets/v3/registry-packed.json?v=1').then(x=>x.rows.map(row=>{const p=Object.fromEntries(x.fields.map((k,i)=>[k,row[i]]));p.url='/people/'+p.slug+'.html';return p})).catch(e=>{registryPromise=null;throw e})),branches=()=>json('/assets/research/branches.json');
const canonical=id=>window.GlasgowRoutes?.[String(id||'').toLowerCase()]||String(id||'').toLowerCase();
const person=id=>json('/assets/research/people/'+encodeURIComponent(canonical(id))+'.json');
const original=id=>json('/people/'+encodeURIComponent(canonical(id))+'.json');
const record=id=>/^[a-f0-9]{16}$/.test(id)?json('/assets/research/records/'+id+'.json'):Promise.reject(Error('Invalid record identifier.'));
function safeURL(value){if(!value||!String(value).trim())return '';try{const u=new URL(value,location.origin);return ['http:','https:'].includes(u.protocol)?u.href:''}catch{return ''}}
const storage={get(key,fallback){try{const x=JSON.parse(localStorage.getItem(key)||'null');return x??fallback}catch{return fallback}},set(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true}catch{return false}},sessionGet(key,fallback){try{return JSON.parse(sessionStorage.getItem(key)||'null')??fallback}catch{return fallback}},sessionSet(key,value){try{sessionStorage.setItem(key,JSON.stringify(value));return true}catch{return false}}};
function toast(s){window.GlasgowSite?.toast(s)}
const statusNames={unknown:'Imported / unassessed',possible:'Possible',uncertain:'Uncertain',proved:'Documented',strongly_supported:'Strongly supported',direct:'Direct evidence',circumstantial:'Circumstantial',contradicted:'Contradicted',superseded:'Superseded',exact:'Imported date',estimated:'Estimated',before:'Before',after:'After',tree:'Imported tree'};
function badge(status,label){status=String(status||'unknown');const icon=['proved','direct'].includes(status)?'✓':['possible','uncertain'].includes(status)?'?':['contradicted','superseded'].includes(status)?'×':'·';return `<span class="r-chip" data-status="${esc(status)}"><span class="r-status-icon" aria-hidden="true">${icon}</span>${esc(label||statusNames[status]||status.replace(/_/g,' '))}</span>`}
function country(k){const p=palette[k]||palette.other;return `<span class="r-country" style="--c:${p.color}">${esc(p.label)}</span>`}
function dates(m){return [m.vitals?.birth?.display_date||'Not recorded',m.vitals?.death?.display_date||'Not recorded'].join(' – ')}
function paragraph(s){return '<p>'+esc(s).replace(/\n\n/g,'</p><p>').replace(/\n/g,' ')+'</p>'}
let context=null,contextVersion=0;const params=new URLSearchParams(location.search);
function contextQuery(c=context){const p=new URLSearchParams();if(!c)return p;p.set(c.kind,c.id);if(c.scope==='family')p.set('scope','family');for(const key of ['from','to','country'])if(c[key])p.set(key,c[key]);return p}
function scoped(path,c=context){const u=new URL(path,location.origin);contextQuery(c).forEach((v,k)=>u.searchParams.set(k,v));return u.pathname+u.search+u.hash}
function contextLinks(c=context){if(!c)return [];
 const id=encodeURIComponent(c.id),isPerson=c.kind==='person',overview=isPerson?'/people/'+canonical(c.id)+'.html':c.kind==='branch'?'/branches/'+c.id+'/':'/places/'+c.id+'.html';
 const family=isPerson?(c.atlas?'/onetree/?person='+id+'#person='+id+'&view=family':overview+'#family'):c.kind==='branch'&&c.root?'/onetree/?branch='+id+'#person='+encodeURIComponent(c.root)+'&view=family':'/branches/';
 return [['Overview',overview,'overview'],['Family',family,'family'],['Map',scoped('/map/',c),'map'],['Life events',scoped('/events/',c),'events'],['Records',scoped('/records/',c),'records'],['DNA connections',scoped('/dna/',c),'dna']];}
function renderContext(){let host=$('#r-context');if(!host){host=document.createElement('div');host.id='r-context';host.className='r-context';const sectionTabs=$('#g-page>.v3-view-nav');if(sectionTabs)sectionTabs.after(host);else $('#g-page')?.prepend(host)}if(!host)return;
 host.hidden=!context;if(!context){$$('.g-nav a[data-r-base]').forEach(a=>a.href=a.dataset.rBase);document.documentElement.style.setProperty('--r-context-height','0px');return}
 const c=context,path=location.pathname,active=path.startsWith('/onetree')?'family':path.startsWith('/map')?'map':path.startsWith('/events')?'events':(path.startsWith('/records')||path.startsWith('/sources'))?'records':path.startsWith('/dna')||path.startsWith('/ydna')?'dna':'overview';
 const filterText=[c.from||c.to?[c.from||'Any year',c.to||'present'].join('–'):null,c.country?palette[c.country]?.label:null].filter(Boolean).join(' · ');
 host.innerHTML=`<div class="r-context-top"><div class="r-context-title"><span class="r-scope-label">${c.kind==='person'?'Selected person':'Selected group'}</span><strong>${esc(c.name)}</strong>${c.kind==='person'?`<span class="experience-selection-id">${esc(c.id)}</span>`:''}<span class="experience-scope-help">The views below follow this selection. Use the section tabs above to browse the whole collection.</span><span class="r-context-filters">${esc(filterText)}</span></div><div class="r-context-controls">${c.kind==='person'?`<label class="sr-only" for="r-context-scope">People included</label><select id="r-context-scope"><option value="person">This person</option><option value="family" ${c.scope==='family'?'selected':''}>Immediate family</option></select>`:''}<button class="r-context-clear" id="r-context-clear">Clear selection &amp; show all</button></div></div><nav class="r-view-tabs" aria-label="Views of ${esc(c.name)}">${contextLinks(c).map(([name,url,key])=>`<a data-r-context-link href="${esc(url)}" ${key===active?'aria-current="page"':''}>${name}</a>`).join('')}</nav>`;
 $('#r-context-clear').onclick=()=>{storage.sessionSet('glasgow-context-v2',null);const u=new URL(location.href);['person','branch','scope','place','from','to','country'].forEach(k=>u.searchParams.delete(k));if(path.startsWith('/onetree')){u.hash='view=all';u.searchParams.set('reset','1');storage.sessionSet('glasgow-tree-view-v2',null);clearTimeout(treeSaveTimer)}contextVersion++;context=null;document.dispatchEvent(new CustomEvent('glasgow:context',{detail:null}));if(path.startsWith('/people/')||/^\/branches\/.+/.test(path)){history.replaceState(null,'',u.pathname+u.search+u.hash);renderContext();return}location.href=u.pathname+u.search+u.hash};
 $('#r-context-scope')?.addEventListener('change',e=>{context.scope=e.target.value;storage.sessionSet('glasgow-context-v2',context);const u=new URL(location.href);if(context.scope==='family')u.searchParams.set('scope','family');else u.searchParams.delete('scope');history.replaceState(null,'',u.pathname+u.search+u.hash);renderContext();document.dispatchEvent(new CustomEvent('glasgow:context',{detail:context}))});
 document.documentElement.style.setProperty('--r-context-height',host.offsetHeight+'px');
 // Only views that can actually honour the selected scope inherit it.
 // Global navigation intentionally clears scope; context links above preserve it.
}
async function setPersonContext(id,scope='person',extras={}){const n=++contextVersion;try{const m=await person(id);if(n!==contextVersion)return;context={kind:'person',id:m.selection_id||m.id,name:m.name,atlas:m.atlas,scope,...extras};storage.sessionSet('glasgow-context-v2',context);renderContext();document.dispatchEvent(new CustomEvent('glasgow:context',{detail:context}));return context}catch(e){console.warn('Context:',e.message)}}
async function initContext(){const extras={};for(const k of ['from','to','country'])if(params.get(k))extras[k]=params.get(k);
 if(params.get('person'))return setPersonContext(params.get('person'),params.get('scope')||'person',extras);
 if(document.body.dataset.rPerson)return setPersonContext(document.body.dataset.rPerson,params.get('scope')||'person',extras);
 if(params.get('branch')||document.body.dataset.rBranch){try{const b=(await branches()).find(x=>x.id===(params.get('branch')||document.body.dataset.rBranch));if(b){context={kind:'branch',id:b.id,name:b.label,root:b.rootId||b.root,scope:'group',...extras};storage.sessionSet('glasgow-context-v2',context);renderContext()}}catch(e){console.warn(e.message)}}
 else if(params.get('place')||document.body.dataset.rPlace){const id=params.get('place')||document.body.dataset.rPlace;const p=(await json('/assets/research/place-index.json')).find(p=>p.slug===id||p.id===id);if(p){context={kind:'place',id:p.slug,name:p.name,locationId:p.id,members:p.members,recordIds:p.record_ids,scope:'place',...extras};storage.sessionSet('glasgow-context-v2',context);renderContext()}}
 if(context)document.dispatchEvent(new CustomEvent('glasgow:context',{detail:context}));return context;
}
const ready=initContext();
async function scopeIds(c=context){if(!c)return null;if(c.kind==='place')return new Set(c.members||[]);if(c.kind==='branch'){const b=(await branches()).find(b=>b.id===c.id);return new Set(b?.members||[])}const m=await person(c.id);const ids=new Set([m.catalogue_id]);if(c.scope==='family')for(const rr of Object.values(m.relationships))for(const r of rr)if(r.id&&!r.withheld)ids.add(canonical(r.id));return ids}
// Workers keep name / record search and large filters off the UI thread.
let worker,sequence=0;const jobs=new Map();
function request(type,payload={}){return new Promise((resolve,reject)=>{try{if(!worker){worker=new Worker('/assets/research/search-worker.js?v=1399f9d5af');worker.onmessage=e=>{const job=jobs.get(e.data.id);if(!job)return;jobs.delete(e.data.id);clearTimeout(job.timer);e.data.error?job.reject(Error(e.data.error)):job.resolve(e.data.result)};worker.onerror=e=>{jobs.forEach(j=>{clearTimeout(j.timer);j.reject(Error(e.message||'Search worker unavailable.'))});jobs.clear();worker?.terminate();worker=null}}const id=++sequence,timer=setTimeout(()=>{jobs.delete(id);reject(Error('Search took too long. Please retry.'))},12000);jobs.set(id,{resolve,reject,timer});worker.postMessage({id,type,...payload})}catch(e){reject(e)}})}
async function search(q,tab='all'){return request('search',{q,tab})}
let preview,returnFocus,previewSeq=0;
function createPreview(){if(preview)return preview;preview=document.createElement('dialog');preview.className='r-preview';preview.id='r-preview';preview.setAttribute('aria-labelledby','r-preview-title');preview.innerHTML='<div class="r-preview-head"><span id="r-preview-kind">Research preview</span><button class="r-preview-close" aria-label="Close preview">Close ×</button></div><div class="r-preview-body"></div>';document.body.append(preview);$('.r-preview-close',preview).onclick=()=>preview.close();preview.addEventListener('close',()=>{previewSeq++;returnFocus?.focus?.()});preview.addEventListener('click',e=>{if(e.target!==preview)return;const r=preview.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right)preview.close()});return preview}
function showPreview(kind){const d=createPreview();returnFocus=document.activeElement;for(const other of $$('dialog[open]'))if(other!==d)other.close();$('#r-preview-kind').textContent=kind;$('.r-preview-body',d).innerHTML='<div class="r-loading" role="status">Loading the research…</div>';if(!d.open)d.showModal();return ++previewSeq}
function previewError(e){$('.r-preview-body',preview).innerHTML=`<h2 id="r-preview-title">Unable to load this item.</h2><p class="r-error">${esc(e.message)}</p><a class="r-button" href="/catalogue/">Open the catalogue</a>`}
function peekButton(id){return `<button class="r-peek-button" data-r-preview="${esc(id)}" aria-label="Preview ${esc(id)}" title="Preview without leaving this page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2 3h16v14H2zM11 3v14M5 7h3m-3 3h3"/></svg></button>`}
async function previewPerson(id){const seq=showPreview('Person / quick view');try{const m=await person(id);if(seq!==previewSeq)return;
 const relatives=Object.entries(m.relationships).filter(([,r])=>r.length).map(([k,rr])=>`<h3>${esc(k[0].toUpperCase()+k.slice(1))}</h3><div class="r-preview-list">${rr.slice(0,8).map(r=>`<div><a href="${esc(r.url||'/people/'+canonical(r.id)+'.html')}">${esc(r.name||r.id)}</a>${r.id&&!r.external&&!r.withheld?peekButton(r.id):''}<small>${esc(r.status_label||r.status||'Imported relationship')}</small></div>`).join('')}${rr.length>8?`<p>${rr.length-8} more in the dossier.</p>`:''}</div>`).join('');
 $('.r-preview-body',preview).innerHTML=`<h2 id="r-preview-title">${esc(m.name)}</h2><p>${esc(dates(m))}</p><div class="r-pills">${country(m.vitals.birth?.country)}${m.override?badge('strongly_supported','Reviewed display'):badge('unknown',m.review?'Research assessment available':'Imported catalogue entry')}</div><p style="margin-top:18px">${esc([m.vitals.birth?.place,m.vitals.death?.place].filter(Boolean).join(' → '))}</p>${m.review?`<h3>Current assessment</h3><p>${esc(m.review.summary.slice(0,900))}${m.review.summary.length>900?'…':''}</p><p class="r-caption">Review dated ${esc(m.review.updated)}. Full reasoning and citations remain in the dossier.</p>`:''}<div class="r-actions"><a class="r-button primary" href="${esc(m.url)}">Read full dossier →</a></div>${relatives}<h3>Research groups</h3><div class="r-links-flat">${m.branches.map(b=>`<a href="${esc(b.url)}">${esc(b.label)}</a>`).join('')||'No branch grouping in this snapshot.'}</div>`;
 }catch(e){if(seq===previewSeq)previewError(e)}}
async function previewRecord(id){const seq=showPreview('Source / record association');try{const r=await record(id);if(seq!==previewSeq)return;const url=safeURL(r.supporting_source_url||r.source_url||'');
 $('.r-preview-body',preview).innerHTML=`<span class="r-kicker">${esc(r.year||'Undated')} · ${esc(r.record_category||'Record')}</span><h2 id="r-preview-title">${esc(r.person)}</h2><div class="r-pills">${badge(r.display_status||r.evidence)}${country(r.country)}</div><h3>${esc(r.association||'Recorded occurrence')}</h3><p>${esc(r.note||'')}</p><p><strong>Location:</strong> ${esc(r.record_location||'Not supplied')}<br><small>${esc(r.record_precision||'Precision not supplied')}</small></p>${r.review_note?`<p class="r-audit">${esc(r.review_note)}</p>`:''}<h3>Source & provenance</h3><p>${esc(r.supporting_source_title||r.source_title||'No source title supplied.')}</p><p>${esc(r.supporting_source_reason||r.source_status||'')}</p><div class="r-actions">${url?`<a class="r-button primary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open original source ↗</a>`:''}${r.document_id?`<a class="r-button primary" href="/sources/${esc(r.document_id)}/">Read source with its family →</a>`:""}<a class="r-button" href="${esc(r.person_url)}">Person dossier</a></div><p class="r-caption">This is an association in the supplied catalogue, not a new source examination. ${r.research_date?'Its date belongs to later research, not the person’s life.':''}</p>`;
 }catch(e){if(seq===previewSeq)previewError(e)}}
async function previewEvidence(id,eid){const seq=showPreview('Evidence / source assessment');try{const [d,m]=await Promise.all([original(id),person(id)]),e=d.evidence?.find(x=>x.id===eid);if(!e)throw Error('Evidence entry not found.');if(seq!==previewSeq)return;const revised=[...m.events,...m.mentions,...m.family_events,...m.unresolved_events,...m.research_events].find(x=>x.evidence_id===eid),did=m.evidence_documents?.[eid];const source=e.source||{},url=safeURL(source.url||''),claims=d.claims?.filter(c=>(e.claim_ids||[]).includes(c.id))||[];
 $('.r-preview-body',preview).innerHTML=`<h2 id="r-preview-title">${esc(e.record_type||'Source evidence')}</h2><p>${esc([revised?.date||e.date,revised?.place||e.place].filter(Boolean).join(' · '))}</p>${revised?.basis==='reviewed_event_role'?`<p class="r-audit">${esc(revised.label)} · ${esc(revised.role)}<br>${esc(revised.note||'')}</p>`:''}${badge(e.evidence_status)}${badge(e.source_quality,e.source_quality?e.source_quality+' source':'Source quality unassessed')}<p style="margin-top:18px">${esc(e.assertion||'')}</p><h3>What it supports</h3>${claims.map(c=>`<p>${esc(c.claim)}</p>${badge(c.status,c.status_label)}`).join('')||'<p>No separate claim linkage supplied.</p>'}<h3>Source</h3><p>${esc(source.title||'Unspecified source')}</p><p>${esc(source.reference||'')}</p><div class="r-actions">${url?`<a class="r-button primary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:''}${did?`<a class="r-button primary" href="/sources/${esc(did)}/">Open source reader →</a>`:""}<a class="r-button" href="/people/${esc(canonical(id))}.html#research">Read full evidence</a></div>`;
 }catch(e){if(seq===previewSeq)previewError(e)}}
function addPeekButtons(root=document){for(const a of $$('a[data-r-person-link]',root)){if(a.dataset.rPeekAdded)continue;const m=a.getAttribute('href')?.match(/\/people\/([^/?#]+)\.html/);if(!m)continue;a.dataset.rPeekAdded='1';a.insertAdjacentHTML('afterend',peekButton(m[1]))}}
document.addEventListener('click',async e=>{const el=e.target.closest('[data-r-preview],[data-r-record],[data-r-evidence],[data-r-save]');if(!el)return;e.preventDefault();if(el.dataset.rPreview)return previewPerson(el.dataset.rPreview);if(el.dataset.rRecord)return previewRecord(el.dataset.rRecord);if(el.dataset.rEvidence){const [id,eid]=el.dataset.rEvidence.split(':');return previewEvidence(id,eid)}if(el.dataset.rSave){try{const m=await person(el.dataset.rSave);window.GlasgowSite?.save({id:m.selection_id||m.id,name:m.name,url:m.url,life:dates(m),tree:m.atlas})}catch(e){toast(e.message)}}});
// Restoring the canvas camera is independent from restoring the selected person.
let treeSaveTimer;function saveTree(){const t=window.GlasgowTree;if(!t)return;storage.sessionSet('glasgow-tree-view-v2',{...t.view(),path:location.pathname+location.search+location.hash})}
window.addEventListener('pagehide',saveTree);document.addEventListener('glasgow:selection',e=>{const id=e.detail?.id;if(id&&id!==context?.id)setPersonContext(id,context?.scope||'person');clearTimeout(treeSaveTimer);treeSaveTimer=setTimeout(saveTree,250)});
document.addEventListener('glasgow:tree-ready',async()=>{const t=window.GlasgowTree,saved=storage.sessionGet('glasgow-tree-view-v2',null);await ready;const p=new URLSearchParams(location.search),hash=new URLSearchParams(location.hash.slice(1)),requested=p.get('person')||hash.get('person');const askKey=h=>[...new URLSearchParams(String(h||'').split('#')[1]||'')].map(([k,v])=>k+'='+v).sort().join('&'),asked=location.hash.slice(1),sameAsk=!asked||askKey(saved?.path)===askKey('#'+asked);if(saved&&sameAsk&&(!requested||canonical(requested)===canonical(saved.selected))&&!p.has('reset')&&hash.get('era')!=='early'){
 try{if(saved.colourMode)t.colourMode(saved.colourMode);if(saved.mode==='family'&&saved.readingRoot)t.readFamily(saved.readingRoot,saved.lens||'descendants',false);else if(saved.selected)t.reveal(saved.selected);if(saved.geo)t.focusRegion(saved.geo);requestAnimationFrame(()=>{t.setCamera(saved.cam);saveTree()})}catch(e){console.warn('Tree position could not be restored',e)}}
 else if(requested&&!hash.get('person')){try{t.readFamily(requested)}catch{}}
 if(t.view().selected)setPersonContext(t.view().selected,context?.scope||'person');
 const detail=$('#detail-content');if(detail){const decorate=()=>{const id=t.view().selected;if(!id||!detail.querySelector('.profile-name')||detail.querySelector('.r-tree-review'))return;const box=document.createElement('div');box.className='r-tree-review';box.innerHTML=`<a href="/people/${esc(canonical(id))}.html">Read current assessment & sources →</a><a href="${esc(scoped('/records/',{kind:'person',id,scope:'person'}))}">Open this person’s records</a>`;detail.querySelector('.profile-actions')?.after(box)};new MutationObserver(decorate).observe(detail,{childList:true});decorate()}});
window.addEventListener('resize',()=>{const h=$('#r-context');if(h&&!h.hidden)document.documentElement.style.setProperty('--r-context-height',h.offsetHeight+'px')});
// Open anchor targets even when their historical section is collapsed.
async function revealHash(){
 if(!location.hash||location.hash.includes('='))return;let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{return}
 let target=document.getElementById(id);const owner=target?.closest('details[data-r-fragment]')||$$('details[data-r-fragment]').find(d=>(d.dataset.rFragmentAnchors||'').split(' ').includes(id));
 if(owner){owner.open=true;await loadFragment(owner);target=document.getElementById(id)||owner}
 if(!target)return;if(target.tagName==='DETAILS')target.open=true;for(let el=target.parentElement;el;el=el.parentElement)if(el.tagName==='DETAILS')el.open=true;setTimeout(()=>target.scrollIntoView({block:'start'}),60)
}
window.addEventListener('hashchange',revealHash);addPeekButtons();
document.addEventListener('glasgow:filters',e=>{if(!context)return;for(const k of ['from','to','country']){if(e.detail?.[k])context[k]=e.detail[k];else delete context[k]}storage.sessionSet('glasgow-context-v2',context);renderContext()});
// Large imported technical captures are fetched only when opened. Inline source
// URLs are trusted only as provided local fragments, never injected user input.
async function loadFragment(d){
 if(d.dataset.rLoaded==='yes')return;if(d._rLoading)return d._rLoading;
 d._rLoading=(async()=>{try{const res=await fetch(d.dataset.rFragment);if(!res.ok)throw Error('The source fragment could not be loaded.');const doc=new DOMParser().parseFromString(await res.text(),'text/html'),details=doc.querySelector('details');if(!details)throw Error('Source fragment is malformed.');for(const n of [...d.children])if(n.tagName!=='SUMMARY')n.remove();for(const n of [...details.childNodes])if(n.nodeName!=='SUMMARY')d.append(document.importNode(n,true));d.dataset.rLoaded='yes';addPeekButtons(d);document.dispatchEvent(new CustomEvent('glasgow:fragment-loaded',{detail:{root:d}}));return true}catch(e){d.querySelector('.r-fragment-error')?.remove();const p=document.createElement('p');p.className='r-error r-fragment-error';p.textContent=e.message+' ';const retry=document.createElement('button');retry.textContent='Retry';retry.onclick=()=>loadFragment(d);p.append(retry);d.append(p);return false}finally{delete d._rLoading}})();return d._rLoading;
}
for(const d of $$('details[data-r-fragment]'))d.addEventListener('toggle',()=>{if(d.open)loadFragment(d)});
window.GlasgowFragmentLoad=loadFragment;revealHash();
window.GlasgowResearch={$,all:$$,esc,norm,json,registry,branches,person,original,record,canonical,safeURL,storage,toast,badge,country,palette,dates,ready,context:()=>context,scoped,scopeIds,search,request,previewPerson,previewRecord,previewEvidence,peekButton,addPeekButtons,showPreview,previewBody:()=>$('.r-preview-body',createPreview()),closePreview:()=>preview?.close(),setPersonContext};
})();
/* Profile tree links: every person page that is in the family tree gets a row of
   links to that person's tree views (family sun, family tree, whole tree,
   timeline). Built here, in the shared profile script, so profile pages
   themselves never need regenerating. Counts come from
   /assets/research/tree-research-status.json ("lines"); without it every link shows. */
(()=>{'use strict';
const host=document.querySelector('.dossier-header .dossier-actions');
let me=null;try{me=JSON.parse(document.body?.dataset.gPerson||'null')}catch{}
if(!host||!me||!me.id||me.tree!==true||document.getElementById('profile-tree-links'))return;
const id=String(me.id),enc=encodeURIComponent(id),at='/onetree/#person='+enc;
if(!document.getElementById('profile-tree-links-css')){const st=document.createElement('style');st.id='profile-tree-links-css';st.textContent=
'.profile-tree-links{--ptl-fg:#315a43;--ptl-bd:#b8cbbd;--ptl-bg:#fffef9;--ptl-gold:#a77a16;--ptl-fs:.9rem;--ptl-rad:6px;margin:14px 0 0;display:flex;flex-wrap:wrap;align-items:center;gap:8px}'+
'.profile-tree-links>.ptl-label{flex:0 0 100%;font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ptl-gold);font-weight:600}'+
'.profile-tree-links a{display:inline-flex;align-items:center;gap:6px;min-height:36px;padding:6px 12px;border:1px solid var(--ptl-bd);border-radius:var(--ptl-rad);background:var(--ptl-bg);color:var(--ptl-fg);font-size:var(--ptl-fs);text-decoration:none;line-height:1.2}'+
'.profile-tree-links a:hover,.profile-tree-links a:focus-visible{background:color-mix(in srgb,var(--ptl-fg) 12%,var(--ptl-bg))}'+
'.profile-tree-links a.ptl-sun{border-color:var(--ptl-gold);background:color-mix(in srgb,var(--ptl-gold) 16%,var(--ptl-bg))}'+
'.profile-tree-links a.ptl-sun:hover,.profile-tree-links a.ptl-sun:focus-visible{background:color-mix(in srgb,var(--ptl-gold) 30%,var(--ptl-bg))}'+
'.profile-tree-links a.ptl-sun svg{color:var(--ptl-gold)}'+
'.profile-tree-links a small{color:inherit!important;opacity:.8;font-size:.85em;font-weight:400}'+
'.profile-tree-links svg{width:15px;height:15px;flex:0 0 auto}'+
'@media (max-width:560px){.profile-tree-links a{flex:1 1 auto;justify-content:center}}';
document.head.append(st)}
const ic={
sun:'<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="2.4" fill="currentColor"/><circle cx="8" cy="8" r="4.6" fill="none" stroke="currentColor" stroke-width="1.2" opacity=".7"/><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.1" opacity=".45"/></svg>',
down:'<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="5" cy="2.4" r="1.4"/><circle cx="11" cy="2.4" r="1.4"/><path d="M5 3.8v1.6h6V3.8M8 5.4v1.4"/><rect x="5.6" y="6.8" width="4.8" height="2.6" rx=".8" fill="currentColor" stroke="none"/><path d="M8 9.4v1.4M3.5 10.8h9M3.5 10.8v1.2M8 10.8v1.2M12.5 10.8v1.2"/><circle cx="3.5" cy="13.4" r="1.3"/><circle cx="8" cy="13.4" r="1.3"/><circle cx="12.5" cy="13.4" r="1.3"/></svg>',
all:'<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="8" cy="8" r="6.3"/><circle cx="8" cy="8" r="1.6" fill="currentColor"/><path d="M8 1.7v4.7M2 8h4.4M14 8H9.6M8 14.3V9.6"/></svg>',
time:'<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M1.5 4h9M4 8h10.5M2.5 12h7"/><circle cx="10.5" cy="4" r="1.3" fill="currentColor"/><circle cx="4" cy="8" r="1.3" fill="currentColor"/><circle cx="9.5" cy="12" r="1.3" fill="currentColor"/></svg>'};
const name=String(me.name||'this person');
const items=[
 {k:'sun',cls:'ptl-sun',href:'/onetree/#view=all&sun='+enc,label:'Family sun',title:'All of '+name+'’s recorded descendants as rings, one ring per generation',needs:'d'},
 {k:'down',href:at+'&view=family',label:'Family tree',title:name+'’s ancestors above and descendants below, one row per generation',needs:'any'},
 {k:'all',href:at+'&view=all',label:'Whole tree',title:'Find '+name+' in the whole Glasgow tree'},
 {k:'time',href:at+'&view=lanes',label:'Timeline',title:name+' on the family timeline'}];
const nav=document.createElement('nav');nav.id='profile-tree-links';nav.className='profile-tree-links';nav.setAttribute('aria-label','Family tree views for '+name);
const lab=document.createElement('span');lab.className='ptl-label';lab.textContent='In the family tree';nav.append(lab);
const els={};
for(const it of items){const a=document.createElement('a');a.href=it.href;a.title=it.title;a.dataset.view=it.k;if(it.cls)a.className=it.cls;a.innerHTML=ic[it.k]+'<span>'+it.label+'</span>';nav.append(a);els[it.k]=a}
host.after(nav);
/* Follow the header's own button and kicker colours, so the row fits light and dark headers alike. */
try{const ref=host.querySelector('a:nth-child(2)')||host.querySelector('a'),cs=ref&&getComputedStyle(ref),kick=document.querySelector('.dossier-header .kicker');
 if(cs){const clear=c=>!c||c==='transparent'||/rgba\([^)]*,\s*0\)$/.test(c);nav.style.setProperty('--ptl-fg',cs.color);nav.style.setProperty('--ptl-bd',cs.borderTopColor);
  nav.style.setProperty('--ptl-bg',clear(cs.backgroundColor)?'transparent':cs.backgroundColor);nav.style.setProperty('--ptl-fs',cs.fontSize);nav.style.setProperty('--ptl-rad',cs.borderTopLeftRadius)}
 if(kick)nav.style.setProperty('--ptl-gold',getComputedStyle(kick).color)}catch{}
const plural=(n,w)=>n.toLocaleString('en-GB')+' '+w+(n===1?'':'s');
fetch('/assets/research/tree-research-status.json',{credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(data=>{
 const lines=data&&data.lines;if(!lines)return;
 const [d,a]=lines[id]||[0,0];
 for(const it of items){if(!it.needs)continue;const n=it.needs==='d'?d:d+a,el=els[it.k];
  if(!n){el.remove();continue}
  if(it.k==='sun'){const s=document.createElement('small');s.textContent=plural(n,'descendant');el.append(s)}}
}).catch(()=>{});
})();
