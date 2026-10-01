/* One linked preview. Geography is a colour key, not a pedigree partition. */
(()=>{'use strict';
const R=window.GlasgowResearch,canvas=document.getElementById('r-home-canopy');if(!R||!canvas)return;
const alias={australia:'oceania',nz:'oceania',wales:'england'};
const names={scotland:'Scotland',ireland:'Ireland & Ulster',america:'United States',canada:'Canada',oceania:'Australia & New Zealand',australia:'Australia',nz:'New Zealand',england:'England & Wales',wales:'Wales',other:'Other / unknown'};
const colour=k=>R.palette[alias[k]||k]?.color||R.palette.other.color;
let data;
function draw(){
 if(!data)return;
 const {width:w,height:h}=canvas.getBoundingClientRect();if(w<1||h<1)return;
 const dpr=Math.min(devicePixelRatio||1,2);canvas.width=w*dpr;canvas.height=h*dpr;
 const c=canvas.getContext('2d');c.scale(dpr,dpr);
 const scale=Number.parseFloat(getComputedStyle(canvas).getPropertyValue('--canopy-scale'))||1;
 const b=data.bounds,k=Math.min((w-24)/b.w,(h-24)/b.h)*scale,ox=(w-b.w*k)/2-b.x*k,oy=(h-b.h*k)/2-b.y*k;
 c.lineWidth=.65;c.globalAlpha=.28;
 for(const e of data.edges){let a,z;if(e.length>=4){a=[e[0],e[1]];z=[e[2],e[3]]}else{a=data.nodes[e[0]];z=data.nodes[e[1]]}if(!a||!z)continue;c.strokeStyle=colour(e[4]||a[2]);c.beginPath();c.moveTo(ox+a[0]*k,oy+a[1]*k);c.lineTo(ox+z[0]*k,oy+z[1]*k);c.stroke()}
 c.globalAlpha=.94;
 for(const n of data.nodes){c.fillStyle=colour(n[2]);c.beginPath();c.arc(ox+n[0]*k,oy+n[1]*k,w<460?1.05:1.25,0,Math.PI*2);c.fill()}
 const core=document.querySelector('.repair-canopy-core');if(core){core.style.left=ox+'px';core.style.top=oy+'px'}
}
R.json('/assets/research/canopy.json').then(d=>{
 data=d;const counts=new Map();for(const n of d.nodes)counts.set(n[2],(counts.get(n[2])||0)+1);
 const host=document.getElementById('repair-home-group-links');
 if(host)host.innerHTML=[...counts].sort((a,b)=>b[1]-a[1]).map(([id,count])=>`<span class="repair-home-group-label" style="--group-colour:${colour(id)}"><strong>${R.esc(names[id]||R.palette[id]?.label||id)}</strong><small>${count.toLocaleString()} profiles</small></span>`).join('');
 new ResizeObserver(draw).observe(canvas);draw();
}).catch(()=>{const caption=document.querySelector('.repair-canopy-caption');if(caption)caption.textContent='Open the Atlas to explore the family tree.'});
const context=R.storage.sessionGet('glasgow-context-v2',null),host=document.getElementById('r-home-resume');
if(context&&host){host.hidden=false;const url=context.kind==='person'?'/people/'+R.canonical(context.id)+'.html':context.kind==='branch'?'/branches/'+context.id+'/':'/places/'+context.id+'.html';host.className='r-resume';host.innerHTML=`<span><span class="r-kicker">Continue exploring</span><strong>${R.esc(context.name)}</strong></span><a class="r-button" href="${R.esc(url)}">Return to this research</a>`}
})();
