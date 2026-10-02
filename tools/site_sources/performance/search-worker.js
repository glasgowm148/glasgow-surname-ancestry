/* Lazy, worker-owned indexes. Opening a page does not fetch the search corpus. */
'use strict';
importScripts('/assets/unified/data-versions.js?v=1');
const normal=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(glasgo|glasco|glascoe|glassgow|glascow)\b/g,'glasgow').replace(/[^a-z0-9]+/g,' ').trim();
const cache=new Map();
async function load(path){if(!cache.has(path))cache.set(path,fetch((()=>{const u=new URL(path,self.location.href),v=globalThis.GlasgowDataVersions?.[u.pathname];if(v)u.searchParams.set('v',v);return u.href})()).then(r=>{if(!r.ok)throw Error('Index unavailable ('+r.status+').');return r.json()}).catch(e=>{cache.delete(path);throw e}));return cache.get(path)}
const pages=/* PUBLIC_SEARCH_ROUTES */[];
const searchCache=new Map();
async function slice(kind){if(searchCache.has(kind))return searchCache.get(kind);const rows=kind==='page'?[...pages.map((p,i)=>({...p,id:'page-'+i,sub:p.meta,kind,search:p.meta+' '+p.search})),...(await load('/assets/research/free-space-index.json')).map(r=>({id:'free-space-'+r.wikitreeId,name:r.title,url:r.url||r.viewUrl,sub:'Free-space page · '+r.category+(r.location?' · '+r.location:''),kind,search:[r.wikitreeId,r.category,r.location,r.startDate,r.endDate,...r.tags].join(' ')}))]:(await load('/assets/v3/search-'+{person:'people',record:'records',place:'places'}[kind]+'.json')).map(([id,name,url,sub,search])=>({id,name,url,sub,search,kind}));const seen=new Set(),unique=kind==='page'?rows.filter(r=>{if(seen.has(r.url))return false;seen.add(r.url);return true}):rows;const cooked=unique.map(r=>({...r,meta:r.sub,icon:({person:"person",record:"records",place:"pin",page:"arrow"})[r.kind],_key:normal([r.name,r.sub,r.id,r.search].join(' ')),_title:normal(r.name),_id:normal(r.id)}));searchCache.set(kind,cooked);return cooked}
let recordRows,sourceRows;
self.onmessage=async({data:m})=>{try{let result;
 if(m.type==='search'){
  const q=normal(m.q),terms=q.split(' ').filter(Boolean),kind={people:'person',places:'place',records:'record',pages:'page'}[m.tab],rows=(await Promise.all((kind?[kind]:['person','place','record','page']).map(slice))).flat();
  const matched=rows.filter(r=>terms.every(t=>r._key.includes(t))).map(r=>{let score=0;if(r._id===q)score+=160;if(r._title===q)score+=100;if(r._title.startsWith(q))score+=50;if(r._title.includes(q))score+=20;for(const t of terms)if(r._title.split(' ').includes(t))score+=5;const {_key,_title,_id,search,...out}=r;return {...out,score}}).sort((a,b)=>b.score-a.score||a.name.localeCompare(b.name));
  const counts={person:0,place:0,record:0,page:0},shown={...counts};for(const r of matched)counts[r.kind]++;
  // Keep the array contract for readers already open when a release is uploaded.
  // Structured cloning preserves these enumerable array properties.
  result=Object.assign(matched.filter(r=>shown[r.kind]++<160),{counts,total:matched.length});
 }else if(m.type==='records'){
  recordRows??=(await load('/assets/research/record-index.json')).map(r=>({...r,meta:r.sub,icon:({person:"person",record:"records",place:"pin",page:"arrow"})[r.kind],_key:normal([r.id,r.person,r.p,r.year,r.place,r.category,r.association,r.title,r.status,r.citation].join(' '))}));const terms=normal(m.q).split(' ').filter(Boolean),ids=m.ids?new Set(m.ids):null,rids=m.recordIds?new Set(m.recordIds):null;
  const rows=recordRows.filter(r=>(!ids||ids.has(r.p))&&(!rids||rids.has(r.id))&&(!m.country||r.country===m.country)&&(!m.from||r.y!=null&&r.y>=Number(m.from))&&(!m.to||r.y!=null&&r.y<=Number(m.to))&&(!m.category||r.category.split(' | ').includes(m.category))&&(!m.quality||r.quality===m.quality)&&(!m.citation||r.citation===m.citation)&&(!m.historical||!r.research_date)&&terms.every(t=>r._key.includes(t))).sort((a,b)=>(a.y??99999)-(b.y??99999)||a.person.localeCompare(b.person));
  result=paginate(rows,m);result.categories=[...new Set(recordRows.flatMap(r=>r.category.split(' | ')))].sort();
 }else if(m.type==='sources'){
  if(!sourceRows){const packed=await load('/assets/v3/source-index-packed.json');sourceRows=packed.rows.map(row=>{const r=Object.fromEntries(packed.fields.map((k,i)=>[k,row[i]]));r._key=normal([r.title,...r.members].join(' '));return r})}
  const terms=normal(m.q).split(' ').filter(Boolean),ids=m.ids?new Set(m.ids):null;
  if(terms.length&&!sourceRows.namesAdded){const names=new Map((await load('/assets/v3/people-quick.json')).map(r=>[r[4],normal(r[1])]));for(const r of sourceRows)r._key+=' '+r.members.map(id=>names.get(id)||'').join(' ');sourceRows.namesAdded=true;}
  const rows=sourceRows.filter(r=>(!ids||r.members.some(id=>ids.has(id)))&&(!m.kind||m.kind==='all'||(m.kind==='image'?(r.image||r.transcription):m.kind==='transcription'?r.transcription:m.kind==='shared'?r.members.length>1:true))&&(!m.from||r.to!=null&&r.to>=+m.from)&&(!m.to||r.from!=null&&r.from<=+m.to)&&terms.every(t=>r._key.includes(t))).sort((a,b)=>(a.from??9999)-(b.from??9999)||a.title.localeCompare(b.title));result=paginate(rows,m);
 }else throw Error('Unknown search request.');self.postMessage({id:m.id,result});
 }catch(e){self.postMessage({id:m.id,error:e.message||String(e)})}};
function paginate(rows,m){const size=Math.min(100,m.size||24),pages=Math.max(1,Math.ceil(rows.length/size)),page=Math.max(0,Math.min(m.page||0,pages-1));return{count:rows.length,pages,page,items:rows.slice(page*size,page*size+size).map(({_key,...r})=>r)}}
