/* Lossless compact source data; parsing/unpacking stays off the UI thread. */
(()=>{
 const fail=e=>{const h=document.getElementById('app');if(h)h.textContent=(e.message||e)+' Reload the page or open the catalogue.'};
 function unpack(p){function d(x){if(typeof x==='number'&&x<0)return p.strings[-x-1];if(Array.isArray(x)){if(x[0]==='l')return x[1].map(d);if(x[0]==='o')return Object.fromEntries(p.schemas[x[1]].map((k,i)=>[k,d(x[2][i])]));if(x[0]==='n')return x[1]}return x}return d(p.value)}
 const url='/assets/research/atlas-model-packed.json?v=1';
 const fallback=()=>fetch(url).then(r=>{if(!r.ok)throw Error('Atlas data unavailable.');return r.json()}).then(unpack);
 const load=()=>typeof Worker==='undefined'?fallback():new Promise((resolve,reject)=>{const blob=new Blob(['const unpack='+unpack.toString()+';onmessage=async e=>{try{const r=await fetch(e.data);if(!r.ok)throw Error("Atlas data unavailable");postMessage({model:unpack(await r.json())})}catch(error){postMessage({error:error.message})}}'],{type:'text/javascript'}),src=URL.createObjectURL(blob);let worker;try{worker=new Worker(src)}catch(e){URL.revokeObjectURL(src);fallback().then(resolve,reject);return}const cleanup=()=>{worker.terminate();URL.revokeObjectURL(src)};worker.onmessage=({data})=>{cleanup();data.error?reject(Error(data.error)):resolve(data.model)};worker.onerror=()=>{cleanup();fallback().then(resolve,reject)};worker.postMessage(new URL(url,location.href).href)});
 load().then(model=>{window.GlasgowAtlasModel=model;const x=document.createElement('script');x.src='/assets/research/atlas.js?v=1';x.onerror=()=>fail(Error('Atlas engine could not be loaded.'));document.body.append(x)}).catch(fail);
})();
