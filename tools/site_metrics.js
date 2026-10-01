/* Browser-local measurements; no network reporting or visitor identifiers. */
(()=>{
 const metrics=window.GlasgowMetrics??={longTasks:[],lcp:null,layoutShift:0};
 const interactions=new Map();
 metrics.inp=null;
 document.addEventListener('catalogue:ready',e=>{metrics.searchReady??=e.detail.readyMs});
 try{
  new PerformanceObserver(list=>{
   for(const e of list.getEntries())if(e.interactionId)interactions.set(e.interactionId,Math.max(interactions.get(e.interactionId)||0,e.duration));
   const durations=[...interactions.values()].sort((a,b)=>b-a);
   const count=performance.interactionCount??interactions.size;
   if(durations.length)metrics.inp=durations[Math.min(durations.length-1,Math.floor(count/50))];
  }).observe({type:'event',buffered:true,durationThreshold:40});
 }catch{}
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')document.dispatchEvent(new CustomEvent('glasgow:metrics',{detail:{...metrics}}))});
})();
