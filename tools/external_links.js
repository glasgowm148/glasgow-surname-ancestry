(()=>{
  function secureExternalLink(link){
    if(!(link instanceof HTMLAnchorElement)) return;
    const href=link.getAttribute('href')||'';
    if(!/^(?:https?:)?\/\//i.test(href)) return;
    let url;
    try{url=new URL(href,window.location.href);}catch(_error){return;}
    if(url.origin===window.location.origin) return;
    link.target='_blank';
    const rel=new Set((link.rel||'').split(/\s+/).filter(Boolean));
    rel.add('noopener');
    rel.add('noreferrer');
    link.rel=[...rel].join(' ');
  }
  function scan(root){
    if(root instanceof HTMLAnchorElement) secureExternalLink(root);
    if(root.querySelectorAll) root.querySelectorAll('a[href]').forEach(secureExternalLink);
  }
  scan(document);
  new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{
    if(node.nodeType===Node.ELEMENT_NODE) scan(node);
  }))).observe(document.documentElement,{childList:true,subtree:true});
})();
