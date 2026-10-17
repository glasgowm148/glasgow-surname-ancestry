'use strict';
/* The builder inserts the existing catalogue predicate; no second matcher to maintain. */
/* MATCH_PREDICATE */
let people=[],sortMode='name:asc',search={},locationSearch={},advancedUrl='',advancedPromise;let queryLocationMatches=new Map();
function matching(word,index){const result=new Set();for(const [token,ids]of Object.entries(index))if(token.includes(word)){let id=0;for(const delta of ids){id+=delta;result.add(id)}};return result}
async function advanced(){return advancedPromise??=fetch(advancedUrl).then(r=>{if(!r.ok)throw Error('Advanced search unavailable');return r.json()}).then(rows=>{rows.forEach((row,i)=>Object.assign(people[i],row));return rows}).catch(e=>{advancedPromise=null;throw e})}
function unpack(value,strings){if(typeof value==='number'&&value<0)return strings[-value-1];if(Array.isArray(value))return value.map(x=>unpack(x,strings));if(value&&typeof value==='object'){if('number'in value)return value.number;return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,unpack(v,strings)]))}return value}
self.onmessage=async({data})=>{
 try{
  let result;
  if(data.type==='load'){
   const response=await fetch(data.url);if(!response.ok)throw Error('Search index returned '+response.status);
   const payload=await response.json();if(payload.schema_version!==1||!Array.isArray(payload.rows))throw Error('Invalid search index');
   search=payload.search;locationSearch=payload.location_search;advancedUrl=data.advancedUrl;people=payload.rows.map(row=>{const p=Object.fromEntries(payload.fields.map((k,i)=>[k,unpack(row[i],payload.strings)]));p._identityExactTokens=new Set(p._identityExactTokens);p._sortValues=Object.fromEntries(payload.sort_keys.map((k,i)=>[k,p._sortValues[i]]));return p});result=people.map(p=>({id:p.id,name:p.name,_name:p._name,_detailShard:p._detailShard,needs_wikitree_update:p.needs_wikitree_update,wikitree_update_relationship_changes:p.wikitree_update_relationship_changes}));
  }else if(data.type==='filter'){sortMode=data.sortMode||'name:asc';const filters=data.filters;
   if(filters.location||filters.excluded.length||filters.sibling)await advanced();
   const sets=filters.exact?[]:filters.query.map(t=>matching(t,search));
   queryLocationMatches=new Map(filters.query.map(t=>[t,new Set([...matching(t,locationSearch)].map(i=>people[i].id))]));
   const predicateFilters=filters.exact?filters:{...filters,query:[]};
   result=people.filter((p,i)=>sets.every(s=>s.has(i))&&matches(p,predicateFilters)).sort((a,b)=>comparePeople(a,b,filters)).map(p=>p.id)}
  else if(data.type==='all'){await advanced();result=people}
  else throw Error('Unknown search operation');
  self.postMessage({id:data.id,result});
 }catch(error){self.postMessage({id:data.id,error:error.message})}
};
