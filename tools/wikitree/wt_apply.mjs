// Robust WikiTree CDP apply. Usage: node wt_apply.mjs /path/patch.json
// patch: { u, text, summary, sugid, set:{mBirthDate,..}, status:{BirthDate:'before'|'certain'|'guess'|'after'|'blank', BirthLocation, DeathDate, DeathLocation} }
// Env TABID pins a specific CDP target. Dismisses JS dialogs (never accepts them) and never hangs.
import { readFileSync, openSync, closeSync, unlinkSync } from 'fs';
const P = JSON.parse(readFileSync(process.argv[2],'utf8'));
const tabs=await fetch("http://127.0.0.1:9333/json/list").then(r=>r.json());
const pin=process.env.TABID||"";
if(process.env.WT_PARALLEL==="1"&&!pin)throw new Error('WT_PARALLEL requires a pinned TABID');
let page=pin?tabs.find(t=>t.id===pin):tabs.find(t=>t.type==="page"&&/wikitree/.test(t.url))||tabs.find(t=>t.type==="page");
if(!page)throw new Error(`WikiTree CDP tab ${pin||'(automatic)'} not found`);
const ws=new WebSocket(page.webSocketDebuggerUrl);const pend=new Map();let id=0;let dialogMsg="";
const cmd=(m,p={})=>{const i=++id;ws.send(JSON.stringify({id:i,method:m,params:p}));return Promise.race([new Promise((resolve,reject)=>pend.set(i,{resolve,reject})),new Promise((_,rej)=>setTimeout(()=>rej(new Error("cdp-timeout "+m)),20000))]);};
ws.addEventListener("message",ev=>{
  const m=JSON.parse(ev.data);
  if(m.method==="Page.javascriptDialogOpening"){ dialogMsg=m.params.message||"dialog"; cmd("Page.handleJavaScriptDialog",{accept:false}).catch(()=>{}); return; }
  if(!m.id||!pend.has(m.id))return;const{resolve,reject}=pend.get(m.id);pend.delete(m.id);m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result);
});
await new Promise((res,rej)=>{ws.addEventListener("open",res,{once:true});ws.addEventListener("error",rej,{once:true});});
const ev=async e=>{try{const r=await cmd("Runtime.evaluate",{expression:e,returnByValue:true});return r.result&&r.result.value;}catch(err){return "__ERR__"+err.message;}};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const parallel=process.env.WT_PARALLEL==="1";
// A navigation in another CDP tab can hide this tab between form entry and
// the trusted Save click. Hold the lock for the whole edit, not just the click.
let editLock;
const releaseEditLock=()=>{
  if(editLock!==undefined){closeSync(editLock);editLock=undefined;unlinkSync('/tmp/wikitree-cdp-save.lock');}
};
if(parallel){
  for(let attempt=0;attempt<6000;attempt++){
    try{editLock=openSync('/tmp/wikitree-cdp-save.lock','wx');break;}
    catch(err){if(err.code!=='EEXIST')throw err;await sleep(100);}
  }
  if(editLock===undefined)throw new Error('Timed out waiting for WikiTree edit lock');
  process.once('exit',releaseEditLock);
}
const clickSel=async sel=>{
  let lock;
  if(parallel&&editLock===undefined){
    for(let attempt=0;attempt<1200;attempt++){
      try{lock=openSync('/tmp/wikitree-cdp-save.lock','wx');break;}
      catch(err){if(err.code!=='EEXIST')throw err;await sleep(100);}
    }
    if(lock===undefined)throw new Error('Timed out waiting for WikiTree click lock');
  }
  try{
    await cmd("Page.bringToFront");
    for(let attempt=0;attempt<12;attempt++){
      if(await ev(`document.visibilityState==='visible'`))break;
      await sleep(150);
    }
    if(!(await ev(`document.visibilityState==='visible'`)))throw new Error(`WikiTree tab stayed hidden before clicking ${sel}`);
    const s=await ev(`(()=>{const b=document.querySelector(${JSON.stringify(sel)}); if(!b)return 'null'; b.scrollIntoView({block:'center'}); const r=b.getBoundingClientRect(); return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2});})()`);
    if(s==='null'||String(s).startsWith('__ERR__'))return String(s);
    const{x,y}=JSON.parse(s);
    await cmd("Input.dispatchMouseEvent",{type:"mousePressed",x,y,button:"left",clickCount:1});
    await cmd("Input.dispatchMouseEvent",{type:"mouseReleased",x,y,button:"left",clickCount:1});
    return 'ok';
  }finally{if(lock!==undefined){closeSync(lock);unlinkSync('/tmp/wikitree-cdp-save.lock');}}
};
await cmd("Page.enable");await cmd("Runtime.enable");
if(!parallel) await cmd("Page.bringToFront");
const editUrl=`https://www.wikitree.com/index.php?title=Special:EditPerson&u=${P.u}`;
const waitForEdit=async()=>{
  for(let i=0;i<80;i++){
    if(await ev(`document.readyState==='complete' && ((location.href.includes('u=${P.u}') && !!document.getElementById('wpSave')) || [...document.querySelectorAll('a')].some(a=>/Discard the Draft/i.test(a.innerText) && a.href.includes('u=${P.u}')))`))return;
    await sleep(250);
  }
  throw new Error(`WikiTree edit form did not load for ${P.u}`);
};
await cmd("Page.navigate",{url:editUrl});await waitForEdit();
// always clear any pending draft first
{
  const d=await ev(`(()=>{const a=[...document.querySelectorAll('a')].find(x=>/Discard the Draft/i.test(x.innerText));return a?a.getAttribute('href'):'';})()`);
  if(d&&typeof d==="string"){
    await cmd("Page.navigate",{url:new URL(d,'https://www.wikitree.com').href});
    await sleep(1500);
    await cmd("Page.navigate",{url:editUrl});
    await waitForEdit();
  }
}
const hadEditor = await ev(`document.querySelector('#toggleMarkupColor')?.value==='Turn Off Enhanced Editor'`);
if(P.text!=null && hadEditor===true){
  await ev(`document.querySelector('#toggleMarkupColor')?.click()`);
  await sleep(600);
  const editorOff=await ev(`document.querySelector('#toggleMarkupColor')?.value==='Turn On Enhanced Editor' && getComputedStyle(document.querySelector('#wpTextbox1')).display!=='none'`);
  if(!editorOff)throw new Error('Could not turn off enhanced editor');
}
if(P.text!=null){
  const assigned=await ev(`(()=>{const ta=document.getElementById('wpTextbox1'); if(!ta)return 0; const s=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set; s.call(ta,${JSON.stringify(P.text)}); ta.dispatchEvent(new Event('input',{bubbles:true})); ta.dispatchEvent(new Event('change',{bubbles:true})); return ta.value.length;})()`);
  if(assigned!==P.text.length)throw new Error(`Biography assignment failed: ${assigned} / ${P.text.length}`);
}
for(const [k,v] of Object.entries(P.set||{})){
  await ev(`(()=>{const e=document.getElementById(${JSON.stringify(k)}); if(!e)return 0; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(e,${JSON.stringify(v)}); e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return 1;})()`);
}
for(const [k,v] of Object.entries(P.status||{})){
  const ids=['mStatus_'+k+'_'+v, k.toLowerCase()+'_'+v,
             ({BirthDate:'birthdate',DeathDate:'deathdate',BirthLocation:'birthlocation',DeathLocation:'deathlocation'}[k]||'')+'_'+v];
  const names=['mStatus_'+k, 'newUser_mDataStatus_m'+k];
  await ev(`(()=>{const cands=[...document.querySelectorAll('input[type=radio]')];let el=cands.find(x=>${JSON.stringify(ids)}.includes(x.id));if(!el)el=cands.find(x=>${JSON.stringify(names)}.includes(x.name)&&x.value===${JSON.stringify(v)});if(!el)return 'null';el.click();el.checked=true;el.dispatchEvent(new Event('change',{bubbles:true}));return el.id;})()`);
  await sleep(200);
}
if(P.sugid){ await ev(`(()=>{const e=document.getElementById(${JSON.stringify(P.sugid)});if(e){e.click();e.checked=true;e.dispatchEvent(new Event('change',{bubbles:true}));}return e?e.checked:null;})()`); }
await sleep(300);
if(P.summary!=null){
  await ev(`(()=>{const s=document.getElementsByName('wpSummary')[0]; if(!s)return 0; const z=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; z.call(s,${JSON.stringify(P.summary)}); s.dispatchEvent(new Event('input',{bubbles:true})); s.dispatchEvent(new Event('change',{bubbles:true})); return 1;})()`);
}
await sleep(300);
const pre=await ev(`JSON.stringify({bd:document.getElementById('mBirthDate')?.value,bl:document.getElementById('mBirthLocation')?.value,st:[...document.querySelectorAll('input[type=radio]:checked')].filter(r=>/mDataStatus|mStatus_/.test(r.name)).map(r=>r.name+'='+r.value),sum:document.getElementsByName('wpSummary')[0]?.value})`);
await clickSel('#wpSave');
releaseEditLock();
let after=null;
for(let i=0;i<30;i++){
  await sleep(500);
  const s=await ev(`JSON.stringify({url:location.href,title:document.title,saved:/errcode=saved/.test(location.href),stillForm:!!document.getElementById('wpSave')})`);
  if(typeof s==="string"&&!s.startsWith("__ERR__")){after=JSON.parse(s); if(after.saved) break; }
  if(dialogMsg) break;
}
if(P.enterFallback && !(after&&after.saved)){
  await ev(`(()=>{const b=document.getElementById('wpSave');if(b){b.focus();}return !!b;})()`);
  await cmd("Input.dispatchKeyEvent",{type:"keyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
  await cmd("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
  for(let i=0;i<8;i++){
    await sleep(1500);
    const s=await ev(`JSON.stringify({url:location.href,title:document.title,saved:/errcode=saved/.test(location.href),stillForm:!!document.getElementById('wpSave')})`);
    if(typeof s==="string"&&!s.startsWith("__ERR__")){after=JSON.parse(s); if(after.saved) break; }
  }
}
ws.close();
console.log(JSON.stringify({hadEditor,pre:typeof pre==="string"?JSON.parse(pre):pre,after,dialog:dialogMsg}));
