// WikiTree CDP driver: navigate + dump. Usage: node wt.mjs '<url>' [wait] [js]
const [urlArg, waitArg, expr] = process.argv.slice(2);
const waitMs = Number(waitArg || 5000);
const tabs = await fetch("http://127.0.0.1:9333/json/list").then(r=>r.json());
const sel = process.env.TAB || "";
const pin = process.env.TABID || "";
const page = (pin && tabs.find(t=>t.id===pin)) || tabs.find(t=>t.type==="page" && (t.url.includes(sel)||t.title.includes(sel))) || tabs.find(t=>t.type==="page");
const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map(); let id=0;
socket.addEventListener("message", ev=>{const m=JSON.parse(ev.data); if(!m.id||!pending.has(m.id))return; const {resolve,reject}=pending.get(m.id); pending.delete(m.id); m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result);});
await new Promise((res,rej)=>{socket.addEventListener("open",res,{once:true});socket.addEventListener("error",rej,{once:true});});
const cmd=(method,params={})=>{const i=++id;socket.send(JSON.stringify({id:i,method,params}));return Promise.race([new Promise((resolve,reject)=>pending.set(i,{resolve,reject})),new Promise((_,rej)=>setTimeout(()=>rej(new Error("cdp-timeout "+method)),20000))]);};
await cmd("Page.enable"); await cmd("Runtime.enable");
if (urlArg && urlArg!=="-") await cmd("Page.navigate",{url:urlArg});
await new Promise(r=>setTimeout(r,waitMs));
const e = expr || `JSON.stringify({url:location.href,title:document.title,text:document.body?document.body.innerText:''})`;
const res = await cmd("Runtime.evaluate",{expression:e,returnByValue:true,awaitPromise:true});
console.log(typeof res.result.value==="string"?res.result.value:JSON.stringify(res.result.value));
socket.close();
