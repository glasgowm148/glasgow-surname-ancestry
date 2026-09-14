/* Reconcile coverage with every matching catalogue association. */
(()=>{'use strict';
const R=window.GlasgowResearch,V=window.GlasgowV3;if(!R||!V)return;
const $=s=>document.querySelector(s),out=$('#v3-country-counts');if(!out)return;
let sources,serial=0;
async function render(){
 const version=++serial;
 try{
  await R.ready;
  sources??=Promise.all([R.json('/assets/research/record-index.json'),R.json('/assets/research/map-points.json'),R.json('/assets/v3/map-country-associations.json')]);
  const [records,local,broad]=await sources,ids=await R.scopeIds(),context=R.context();
  if(version!==serial)return;
  const recordIds=context?.kind==='place'?new Set(context.recordIds||[]):null;
  const values=Object.fromEntries(['q','country','from','to'].map(k=>[k,$('#r-map-'+k)?.value||'']));
  if(values.from&&values.to&&+values.from>+values.to){out.textContent='Start year must be before end year.';return}
  const terms=R.norm(values.q).split(' ').filter(Boolean),localIds=new Set(local.flatMap(p=>p.items.map(x=>x[0]))),broadIds=new Set(broad.flatMap(p=>p.items.map(x=>x[0]))),usStates=['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming','District of Columbia'],hasUsState=place=>{const value=' '+String(place||'').toLowerCase().replace(/[^a-z]+/g,' ')+' ';return usStates.some(state=>value.includes(' '+state.toLowerCase()+' '))},counts=new Map();
  for(const r of records){
   if(ids&&!ids.has(r.p)||recordIds&&!recordIds.has(r.id)||values.country&&r.country!==values.country||values.from&&(r.y==null||r.y<+values.from)||values.to&&(r.y==null||r.y>+values.to)||!terms.every(t=>R.norm([r.person,r.p,r.place,R.palette[r.country]?.label].join(' ')).includes(t)))continue;
   if(!counts.has(r.country))counts.set(r.country,{total:0,local:0,state:0,country:0,missing:0});
   const row=counts.get(r.country);row.total++;row[localIds.has(r.id)?'local':broadIds.has(r.id)&&r.country==='america'&&hasUsState(r.place)?'state':broadIds.has(r.id)?'country':'missing']++;
  }
  const link=country=>{const u=new URL(R.scoped('/records/'),location.origin);for(const [k,v]of Object.entries(values))if(v)u.searchParams.set(k,v);if(country)u.searchParams.set('country',country);return u.pathname+u.search};
  const rows=[...counts].sort((a,b)=>b[1].total-a[1].total),totals=rows.reduce((a,[,r])=>{for(const k of Object.keys(a))a[k]+=r[k];return a},{total:0,local:0,state:0,country:0,missing:0});
  out.innerHTML=rows.map(([key,row])=>`<a class="v3-country-total" href="${R.esc(link(key))}">${R.country(key)}<strong>${row.total.toLocaleString()}</strong><small>${row.local.toLocaleString()} with local coordinates<br>${row.state.toLocaleString()} at US state level<br>${row.country.toLocaleString()} at country level<br>${row.missing.toLocaleString()} without coordinates</small><span>Browse all records</span></a>`).join('')||'<p>No records match these filters.</p>';
  $('#r-map-coverage').innerHTML=`<strong>${totals.total.toLocaleString()} matching record associations</strong><span>${totals.local.toLocaleString()} with local coordinates; ${totals.state.toLocaleString()} at approximate US state points; ${totals.country.toLocaleString()} at country level; ${totals.missing.toLocaleString()} without coordinates.</span><a href="${R.esc(link())}">Browse all matching records</a>`;
  out.dataset.count=totals.total;
  window.GlasgowCountrySummary={total:totals.total,counts:Object.fromEntries(rows.map(([k,r])=>[k,r.total])),coverage:totals};
 }catch(error){out.textContent=error.message}
}
document.querySelectorAll('[data-v3-map-pan]').forEach(b=>b.onclick=()=>window.GlasgowMap?.pan(...b.dataset.v3MapPan.split(',').map(Number)));
document.addEventListener('glasgow:filters',V.debounce(render,50));document.addEventListener('glasgow:context',render);render();
})();
