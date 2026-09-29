const summary=process.argv[2]||'';
const tabs=await fetch("http://127.0.0.1:9333/json/list").then(r=>r.json());
let page=tabs.find(t=>t.id===process.env.WT_TABID)||tabs.find(t=>t.type==="page"&&/wikitree/.test(t.url))||tabs.find(t=>t.type==="page");
const ws=new WebSocket(page.webSocketDebuggerUrl);const pend=new Map();let id=0;
ws.addEventListener("message",ev=>{const m=JSON.parse(ev.data);if(!m.id||!pend.has(m.id))return;const{resolve,reject}=pend.get(m.id);pend.delete(m.id);m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result);});
await new Promise((res,rej)=>{ws.addEventListener("open",res,{once:true});ws.addEventListener("error",rej,{once:true});});
const cmd=(m,p={})=>{const i=++id;ws.send(JSON.stringify({id:i,method:m,params:p}));return new Promise((resolve,reject)=>pend.set(i,{resolve,reject}));};
const ev=async e=>{const r=await cmd("Runtime.evaluate",{expression:e,returnByValue:true});return r.result&&r.result.value;};
const clickSel=async sel=>{const s=await ev(`(()=>{const b=document.querySelector(${JSON.stringify(sel)}); if(!b)return 'null'; b.scrollIntoView({block:'center'}); const r=b.getBoundingClientRect(); return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2});})()`); if(s==='null')return 'null';const{x,y}=JSON.parse(s);await cmd("Input.dispatchMouseEvent",{type:"mousePressed",x,y,button:"left",clickCount:1});await cmd("Input.dispatchMouseEvent",{type:"mouseReleased",x,y,button:"left",clickCount:1});return 'ok';};
await cmd("Page.enable");await cmd("Runtime.enable");
if(summary){ await ev(`(()=>{const el=document.getElementsByName('wpSummary')[0]; if(!el)return 0; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(el,${JSON.stringify(summary)}); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return el.value;})()`); }
await clickSel('#addNewPersonButton');
await new Promise(r=>setTimeout(r,4500));
const st=await ev(`JSON.stringify({url:location.href, text:document.body.innerText.replace(/\\s+/g,' ').slice(0,1000), btns:[...document.querySelectorAll('button')].filter(e=>e.offsetParent!==null).map(b=>({id:b.id||'',t:(b.innerText||'').trim().slice(0,40)})), vis:[...document.querySelectorAll('input,textarea,select')].filter(e=>e.offsetParent!==null).map(e=>({n:e.name||'',id:e.id||'',v:(e.value||'').slice(0,60),ph:e.placeholder||''}))})`);
ws.close(); console.log(JSON.stringify(JSON.parse(st),null,1));
