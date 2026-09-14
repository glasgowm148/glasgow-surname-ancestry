// clusteredFallbackRendering: keep summaries at geography, never stack callouts.
function describeMapCluster(g){
 const local=g.rows.filter(p=>!p.broad).reduce((n,p)=>n+p.visible.length,0);
 const state=g.rows.filter(p=>p.stateFallback).reduce((n,p)=>n+p.visible.length,0);
 const country=g.count-local-state;
 const name=g.rows.length===1?g.rows[0].name:g.rows.length+' representative locations';
 const precision=[local?local.toLocaleString()+' local':null,state?state.toLocaleString()+' approximate state-level':null,country?country.toLocaleString()+' country-level':null].filter(Boolean).join(', ');
 return name+' / '+precision+' associations'+(g.rows.length>1?'. Click to zoom in.':'');
}
function draw(){
 if(!width||!height)return;
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
 ctx.fillStyle='#eff3ed';ctx.fillRect(0,0,width,height);drawLand();drawTiles();
 const grid=new Map(),cell=camera.z>10?24:43;
 const radius=count=>Math.min(25,7+Math.log2(count+1)*2.1);
 for(const p of filtered){
  const s=project(p);
  if(s.x<-30||s.y<-30||s.x>width+30||s.y>height+30)continue;
  // State, country and local points all participate in spatial clustering.
  const key=Math.floor(s.x/cell)+':'+Math.floor(s.y/cell);
  let g=grid.get(key);
  if(!g){g={x:0,y:0,rows:[],count:0};grid.set(key,g)}
  g.x+=s.x;g.y+=s.y;g.rows.push(p);g.count+=p.visible.length;
 }
 clusters=[...grid.values()];
 for(const g of clusters){g.x/=g.rows.length;g.y/=g.rows.length;g.r=radius(g.count)}
 // Merge overlapping circles, rather than displacing any marker. Each pass
 // removes a cluster or stops, so even dense views have a bounded layout.
 let changed=true;
 while(changed){
  changed=false;
  for(let i=0;i<clusters.length;i++)for(let j=clusters.length-1;j>i;j--){
   const a=clusters[i],b=clusters[j];
   if(Math.hypot(a.x-b.x,a.y-b.y)>=a.r+b.r+9)continue;
   const n=a.rows.length,m=b.rows.length;
   a.x=(a.x*n+b.x*m)/(n+m);a.y=(a.y*n+b.y*m)/(n+m);
   a.rows.push(...b.rows);a.count+=b.count;a.r=radius(a.count);
   clusters.splice(j,1);changed=true;
  }
 }
 for(const g of clusters){
  g.broad=g.rows.every(p=>p.broad);
  g.hasFallback=g.rows.some(p=>p.broad);
  const countries=new Set(g.rows.map(p=>p.country));
  g.country=countries.size===1?g.rows[0].country:'other';
  ctx.fillStyle=g.broad?'#faf4e5':R.palette[g.country]?.color||'#777c76';
  ctx.beginPath();ctx.arc(g.x,g.y,g.r,0,Math.PI*2);ctx.fill();
  if(!g.broad&&countries.size>1){
   let angle=-Math.PI/2;const counts={};
   for(const p of g.rows)counts[p.country]=(counts[p.country]||0)+p.visible.length;
   for(const [key,n] of Object.entries(counts)){
    const next=angle+2*Math.PI*n/g.count;
    ctx.fillStyle=R.palette[key]?.color||'#777c76';ctx.beginPath();
    ctx.moveTo(g.x,g.y);ctx.arc(g.x,g.y,g.r,angle,next);ctx.closePath();ctx.fill();angle=next;
   }
  }
  ctx.beginPath();ctx.arc(g.x,g.y,g.r,0,Math.PI*2);
  ctx.strokeStyle=g.broad?'#796446':'#fffffa';ctx.lineWidth=1.8;
  ctx.setLineDash(g.broad?[3,3]:[]);ctx.stroke();ctx.setLineDash([]);
  if(g.hasFallback&&!g.broad){
   ctx.beginPath();ctx.arc(g.x,g.y,g.r+3,0,Math.PI*2);
   ctx.strokeStyle='#796446';ctx.lineWidth=1.5;ctx.setLineDash([3,3]);ctx.stroke();ctx.setLineDash([]);
  }
  if(g.count>1||g.broad){
   ctx.font='600 '+(g.count>999?10:11)+'px sans-serif';ctx.fillStyle=g.broad?'#59482e':'#fffdf4';
   ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(g.count.toLocaleString(),g.x,g.y+.5);
  }
  if(selected&&g.rows.some(p=>p.key===selected)){
   ctx.beginPath();ctx.arc(g.x,g.y,g.r+6,0,Math.PI*2);
   ctx.strokeStyle='#243f31';ctx.lineWidth=2;ctx.stroke();
  }
 }
 // Labels may be omitted in a dense view; records and counts never are.
 // Keep each label inside the canvas and clear of every marker and label.
 ctx.font='11px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
 const placed=[],labelLimit=width<600?8:16;
 for(const g of [...clusters].sort((a,b)=>b.count-a.count)){
  if(placed.length>=labelLimit)break;
  if(!g.hasFallback&&camera.z<7)continue;
  let text;
  if(g.rows.length===1){
   const p=g.rows[0];text=p.broad&&!p.stateFallback?(R.palette[p.country]?.label||'Country summary'):p.name.split(' \u00b7 ')[0];
  }else text=g.country==='other'?g.rows.length+' locations':R.palette[g.country]?.label||g.rows.length+' locations';
  const maxLabelWidth=Math.min(150,width-24);
  if(ctx.measureText(text).width>maxLabelWidth){while(text.length&&ctx.measureText(text+'...').width>maxLabelWidth)text=text.slice(0,-1);text+='...'}
  const w=ctx.measureText(text).width+12,h=20;
  const x=g.x-w/2,y=g.y+g.r+7;
  if(x<6||x+w>width-6||y<6||y+h>height-6)continue;
  if(placed.some(b=>x<b.x+b.w+4&&x+w+4>b.x&&y<b.y+b.h+4&&y+h+4>b.y))continue;
  if(clusters.some(b=>{const dx=b.x-Math.max(x,Math.min(b.x,x+w)),dy=b.y-Math.max(y,Math.min(b.y,y+h));return dx*dx+dy*dy<(b.r+5)**2}))continue;
  placed.push({x,y,w,h});ctx.fillStyle='#f7f9f2ee';ctx.beginPath();ctx.roundRect(x,y,w,h,4);ctx.fill();
  ctx.fillStyle='#3d5837';ctx.fillText(text,g.x,y+h/2);
 }
 $('#r-map-view-count').textContent=clusters.reduce((n,g)=>n+g.count,0).toLocaleString()+' associations in view (including fallback summaries)';
}
