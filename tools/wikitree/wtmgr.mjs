// check management: usage node wtmgr.mjs Glasgow-951 Glasgow-4070 ...
import { createRequire } from 'module';
const ids = process.argv.slice(2);
const tabs = await fetch("http://127.0.0.1:9333/json/list").then(r=>r.json());
let page = tabs.find(t=>t.id===process.env.WT_TABID)||tabs.find(t=>t.type==="page" && /wikitree/.test(t.url));
if(!page) page = tabs.find(t=>t.type==="page");
const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending=new Map(); let id=0;
socket.addEventListener("message",ev=>{const m=JSON.parse(ev.data);if(!m.id||!pending.has(m.id))return;const{resolve,reject}=pending.get(m.id);pending.delete(m.id);m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result);});
await new Promise((res,rej)=>{socket.addEventListener("open",res,{once:true});socket.addEventListener("error",rej,{once:true});});
const cmd=(m,p={})=>{const i=++id;socket.send(JSON.stringify({id:i,method:m,params:p}));return new Promise((resolve,reject)=>pending.set(i,{resolve,reject}));};
await cmd("Page.enable"); await cmd("Runtime.enable");
for (const pid of ids){
  await cmd("Page.navigate",{url:`https://www.wikitree.com/wiki/${pid}`});
  await new Promise(r=>setTimeout(r,2800));
  const e=`JSON.stringify((()=>{const t=document.body?document.body.innerText:'';const hasEdit=!![...document.querySelectorAll('a')].find(a=>a.innerText&&a.innerText.trim().toLowerCase()==='edit');const m=[...new Set([...t.matchAll(/(?:Profile Manager|managed by|Trusted List|Unlisted|Private|Public|Open)[^\\n]{0,60}/gi)].map(x=>x[0].replace(/\\s+/g,' ').trim().slice(0,70)))];const mn=[...t.matchAll(/Glasgow-933|M Glasgow/gi)].length;return {pid:${JSON.stringify(pid)},hasEdit,managerHits:m.slice(0,6),selfRef:mn};})())`;
  const r=await cmd("Runtime.evaluate",{expression:e,returnByValue:true});
  try{ console.log(JSON.parse(r.result.value)); }catch(err){ console.log(r.result.value?r.result.value.slice(0,200):'no result'); }
}
socket.close();
