import { readFileSync } from 'fs';
const P = JSON.parse(readFileSync('/tmp/wt_patch.json','utf8'));
const tabs=await fetch("http://127.0.0.1:9333/json/list").then(r=>r.json());
const pin=process.env.TABID||"";let page=(pin&&tabs.find(t=>t.id===pin))||tabs.find(t=>t.type==="page"&&/wikitree/.test(t.url))||tabs.find(t=>t.type==="page");
const ws=new WebSocket(page.webSocketDebuggerUrl);const pend=new Map();let id=0;
ws.addEventListener("message",ev=>{const m=JSON.parse(ev.data);if(!m.id||!pend.has(m.id))return;const{resolve,reject}=pend.get(m.id);pend.delete(m.id);m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result);});
await new Promise((res,rej)=>{ws.addEventListener("open",res,{once:true});ws.addEventListener("error",rej,{once:true});});
const cmd=(m,p={})=>{const i=++id;ws.send(JSON.stringify({id:i,method:m,params:p}));return new Promise((resolve,reject)=>pend.set(i,{resolve,reject}));};
const ev=async e=>{const r=await cmd("Runtime.evaluate",{expression:e,returnByValue:true});return r.result&&r.result.value;};
const clickSel=async sel=>{const s=await ev(`(()=>{const b=document.querySelector(${JSON.stringify(sel)}); if(!b)return 'null'; b.scrollIntoView({block:'center'}); const r=b.getBoundingClientRect(); return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2});})()`); if(s==='null')return 'null';const{x,y}=JSON.parse(s);await cmd("Input.dispatchMouseEvent",{type:"mousePressed",x,y,button:"left",clickCount:1});await cmd("Input.dispatchMouseEvent",{type:"mouseReleased",x,y,button:"left",clickCount:1});return 'ok';};
await cmd("Page.enable");await cmd("Runtime.enable");
await cmd("Page.navigate",{url:`https://www.wikitree.com/index.php?title=Special:EditPerson&u=${P.u}`});await new Promise(r=>setTimeout(r,3500));
// CDP Page.navigate can return while the previous edit page is still active.
// Never apply a biography to a form for a different person.
let loaded=false;
for(let attempt=0;attempt<80;attempt++){
  const state=await ev(`JSON.stringify({url:location.href,ready:!!document.getElementById('wpTextbox1'),draft:[...document.querySelectorAll('a')].some(x=>/Discard the Draft/i.test(x.innerText))})`).catch(()=>null);
  if(state){const s=JSON.parse(state);if((s.url.includes(`u=${P.u}`)&&(s.ready||s.draft))||(s.url.includes('displayDraft=1')&&s.draft)){loaded=true;break;}}
  await new Promise(r=>setTimeout(r,500));
}
if(!loaded){ws.close();throw new Error(`Target edit form did not load for u=${P.u}`);}
// if draft interstitial
if(!(await ev(`!!document.getElementById('wpSave')`))){ const d=await ev(`(()=>{const a=[...document.querySelectorAll('a')].find(x=>/Discard the Draft/i.test(x.innerText));return a?a.href:'';})()`); if(d){await cmd("Page.navigate",{url:d});await new Promise(r=>setTimeout(r,3000));await cmd("Page.navigate",{url:`https://www.wikitree.com/index.php?title=Special:EditPerson&u=${P.u}`});for(let attempt=0;attempt<80;attempt++){if(await ev(`location.href.includes('u=${P.u}')&&!!document.getElementById('wpTextbox1')`).catch(()=>false))break;await new Promise(r=>setTimeout(r,500));}}}
// Structured-only edits leave the biography and enhanced editor untouched.
const hadEditor = await ev(`!!document.querySelector('.CodeMirror, .cm-editor, [contenteditable=true]')`);
if(P.text !== undefined){
  if(hadEditor){ await clickSel('#toggleMarkupColor'); await new Promise(r=>setTimeout(r,1800)); }
  await ev(`(()=>{const ta=document.getElementById('wpTextbox1'); if(!ta)return 0; const s=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set; s.call(ta,${JSON.stringify(P.text)}); ta.dispatchEvent(new Event('input',{bubbles:true})); ta.dispatchEvent(new Event('change',{bubbles:true})); return ta.value.length;})()`);
}
// structured fields: P.set {id/name: value}; P.check {radioName: value}
if(P.set||P.check){ const r=await ev(`(()=>{const out=[];const S=${JSON.stringify(P.set||{})},C=${JSON.stringify(P.check||{})};for(const[k,v] of Object.entries(S)){const e=document.getElementById(k)||document.getElementsByName(k)[0];if(!e){out.push('missing:'+k);continue;}const z=Object.getOwnPropertyDescriptor(e.tagName==='SELECT'?window.HTMLSelectElement.prototype:window.HTMLInputElement.prototype,'value').set;z.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));out.push(k+'='+e.value);}for(const[k,v] of Object.entries(C)){const e=[...document.getElementsByName(k)].find(x=>x.value===v);if(!e){out.push('missing:'+k+'='+v);continue;}e.checked=true;e.dispatchEvent(new Event('change',{bubbles:true}));out.push(k+':'+v);}return out.join(';');})()`); console.error('fields:',r); if(/missing/.test(r)){ws.close();throw new Error('field missing: '+r);} }
await clickSel('#'+P.sugid);
await new Promise(r=>setTimeout(r,400));
await ev(`(()=>{const s=document.getElementsByName('wpSummary')[0]; if(!s)return 0; const z=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; z.call(s,${JSON.stringify(P.summary)}); s.dispatchEvent(new Event('input',{bubbles:true})); s.dispatchEvent(new Event('change',{bubbles:true})); return 1;})()`);
await new Promise(r=>setTimeout(r,300));
const targetUrl=await ev(`location.href`);
if(!targetUrl.includes(`u=${P.u}`)){ws.close();throw new Error(`Edit target changed before save: ${targetUrl}`);}
await clickSel('#wpSave'); await new Promise(r=>setTimeout(r,4000));
const st=await ev(`JSON.stringify({url:location.href, title:document.title})`);
const after=JSON.parse(st);
ws.close();
console.log(JSON.stringify({hadEditor, after}));
if(!after.url.includes('errcode=saved')) throw new Error(`WikiTree did not confirm Full Save: ${after.url}`);
