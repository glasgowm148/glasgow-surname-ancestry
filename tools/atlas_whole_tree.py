"""Whole-tree (canopy) fixes for the approved atlas renderer.

``documentary_renderer`` applies these to ``assets/research/atlas.js``. Each
patch replaces one exact fragment of the approved source and is skipped once
its replacement is present, so the transform is idempotent and the
publication-boundary check (``normalise(www) == documentary_renderer(src)``)
still holds.

Fixes, in order:
1. Layout CSS: the canvas no longer overflows its card when the toolbar wraps;
   the heading and status text get a paper backdrop over branches; the year
   slider narrows beside the heading on mid-width canvases and moves below it on
   narrow ones; mobile drops the pan pad, status line and minimap that collided
   with the slider.
2. ``canopyInsets()`` measures the overlay controls so fit, the early-core
   view, branch focus and unfolding use the real free area instead of fixed
   154/75px margins.
3. Zooms can never be negative. Camera easing used the frame timestamp, which
   can precede the animation start after a long task, so start-up moves (the
   ``#era=early`` link in particular) overshot to a negative zoom and the canvas
   threw IndexSizeError; ``focusEarly`` could also go negative on a short canvas.
   The early-core camera is kept after resizes.
4. Selecting a person zooms to about four times the overview, not to an
   absolute 0.8 (about 900%).
5. The label guard includes the pan controls.
6. Century ring labels reserve space instead of being drawn under labels.
7. Rim family names keep their profile count when shortened.
8. Clearer status text, including the early-core mode.
9. "Show: Everyone | Grandparents only" beside the year slider
   (``#view=all&filter=grandparents``): only people with a recorded grandchild,
   dot size from their recorded descendants, grandparent-to-grandparent lines
   solid and the rest of the tree as a faint outline.
10. Overview declutter: split birth/death dots appear once zoomed in, century
    rings are stronger, and family names sit in two
    horizontal columns with leader lines (radial names remain when zoomed in).
11. Families first: each family branch is a tinted sector from its oldest
    member to the rim; hovering anywhere inside lights the branch up and shows
    its summary, clicking zooms to it. Overview labels use full names.
12. "Colour: Country | Family" (``&colour=branch``): neighbouring families get
    different colours and very large families are split by their main lines.
13. A "Key" card explains colours, lines, dot size and Y-DNA markers and holds
    five research-mark switches (father uncertain, no father recorded, no
    children recorded, no spouse recorded, died before 16).
14. Family sun (``&sun=<id>``), opened from a selected family or person: rings
    are generations, slice width is the share of descendants, colour follows
    each line; click for a profile, double-click to re-centre.
15. "Arrange: By year | By generation" (``&layout=gen``): one ring per
    generation from each family's founder, with labelled generation rings.
16. Research layer: "Colour: Evidence" draws each parent link by its evidence
    grade; the key adds research-status marks (researched, new finding since a
    date, WikiTree update waiting or blocked, needs a decision) from
    ``tree-research-status.json`` (``tools/build_tree_research_status.py``),
    Y-DNA coverage marks, "Families to connect" (unattached family heads with
    date-and-place leads, never proposed parents) and CSV downloads.
17. Profile links (``#person=<id>&view=family|lanes|all``) open the view they
    ask for.
18. One family tree replaces the descendants / ancestors / close-family
    lenses: an hourglass with ancestors above, the person with partners and
    siblings across the middle and descendants below, one shaded row per
    generation (labelled with its birth years). Parents are centred over their
    own ancestors, families are packed generation by generation, links are
    square, and a pill on a link shows its evidence grade where it is not
    simply confident. "Ancestors − n +", "Descendants − n +" and "Siblings"
    set what is shown, and "Vertical | Horizontal" turns the tree (horizontal
    puts ancestors to the right, as FamilySearch does; the choice is
    remembered). Round chevron buttons beside a card open one line of parents
    or children; while a card is hovered a turned-round button folds its open
    line away again.
19. Controls inside a closed menu no longer blank part of the canvas (Chrome
    still reports a box for them).
Ideas 12-15 and 18 follow Tree Prism (prism.vibe-genealogy.com): its By-branch
colour, Branches marks, Descendant Sun, generation rings and Tree view.
"""
from __future__ import annotations

import json

MARKER = 'whole-tree-fixes'

CSS = (
    "@media (min-width:701px){.v3-site.g-kind-tree #canvas-area,.exploration-atlas #canvas-area{min-height:0!important}}"
    "#canvas-area{container:canopy/inline-size}"
    "#canvas-area #canvas-heading{background:#fcfbf6d9;box-shadow:0 0 14px 12px #fcfbf6d9;border-radius:12px}"
    "#canvas-area .canvas-status{background:#fcfbf6d9;box-shadow:0 0 10px 7px #fcfbf6d9;border-radius:6px}"
    "#canvas-area .canvas-status{min-width:0;overflow:hidden}"
    "#canvas-area .canvas-status button{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    "@container canopy (min-width:741px) and (max-width:960px){#canvas-area #canopy-tools input[type=range]{width:120px}"
    "#canvas-area #canopy-tools{max-width:380px!important}#canvas-area #canvas-heading{max-width:calc(100% - 420px)!important}}"
    "@media (min-width:701px){@container canopy (max-width:740px){#canvas-area #canopy-tools{top:96px;left:22px;right:auto}}}"
    "#canvas-area #canopy-tools{flex-wrap:wrap;row-gap:6px;max-width:min(470px,calc(100% - 32px))}"
    "#canopy-tools .grand-row{flex-basis:100%;display:flex;align-items:center;gap:6px}"
    "#canopy-tools .grand-label{font-size:8px;letter-spacing:1.2px;text-transform:uppercase;color:#7d8a72;min-width:46px}"
    "#canopy-tools .grand-row button.active{background:#4d6b43;border-color:#4d6b43;color:#fcfbf6}"
    "#canopy-tools .grand-label2{margin-left:10px;min-width:0}#canopy-tools .grand-break{flex-basis:100%;height:0}#canopy-tools .grand-row{flex-wrap:wrap;row-gap:6px}#canopy-tools .grand-row>*{order:1}#canopy-tools .grand-row>.g-arr,#canopy-tools .grand-row>#layout-year,#canopy-tools .grand-row>#layout-gen{order:2}"
    "#canopy-tools .grand-row>.g-col,#canopy-tools .grand-row>#colour-country,#canopy-tools .grand-row>#colour-branch,#canopy-tools .grand-row>#colour-evidence,#canopy-tools .grand-row>#sun-open{order:3}#canopy-tools .sun-open{margin-left:auto}"
    "@media (max-width:700px){#canopy-tools .grand-label2{margin-left:0;min-width:46px}#canopy-tools .g-arr{flex-basis:auto}}"
    "#canvas-area .canopy-key{position:absolute;right:16px;bottom:118px;z-index:4;width:228px;background:#fcfbf6f2;border:1px solid #dfe3d6;border-radius:8px;font-size:10px;color:#4a5a46;box-shadow:0 2px 10px #2b3b2a10}"
    "#canvas-area .canopy-key[hidden]{display:none}"
    "#canvas-area .key-toggle{display:flex;width:100%;justify-content:space-between;align-items:center;padding:7px 10px;font-size:8px;letter-spacing:1.2px;text-transform:uppercase;color:#6f7d66;background:none;border:0;cursor:pointer}"
    "#canvas-area .key-toggle::after{content:'▾';font-size:10px}#canvas-area .canopy-key[data-open='0'] .key-toggle::after{content:'▸'}"
    "#canvas-area .canopy-key[data-open='0'] .key-body{display:none}#canvas-area .canopy-key[data-open='0']{width:auto}"
    "#canvas-area .key-body{padding:0 10px 9px;max-height:46vh;overflow:auto}"
    "#canvas-area .key-row{display:flex;align-items:center;gap:7px;margin:4px 0;line-height:1.3}"
    "#canvas-area .key-row small{margin-left:auto;color:#8b9682}"
    "#canvas-area .key-sw{width:24px;height:7px;border-radius:4px;flex:none}"
    "#canvas-area .key-dots{display:inline-flex;align-items:center;gap:2px;width:24px;flex:none}#canvas-area .key-dots i{display:block;width:5px;height:5px;border-radius:50%;background:#55705a}#canvas-area .key-dots i+i{width:10px;height:10px}"
    "#canvas-area .key-dna{width:24px;text-align:center;color:#66304f;flex:none}"
    "#canvas-area .key-head{margin:9px 0 3px;font-size:8px;letter-spacing:1.2px;text-transform:uppercase;color:#7d8a72}"
    "#canvas-area .key-mark{cursor:pointer}#canvas-area .key-mark input{margin:0;accent-color:#4d6b43}"
    "#canvas-area .key-sq{width:8px;height:8px;flex:none}"
    "#canvas-area .key-note{margin:7px 0 0;font-size:9px;line-height:1.4;color:#8b9682}"
    "#canvas-area .canopy-key{width:262px;display:flex;flex-direction:column;max-height:calc(100% - 250px)}#canvas-area .key-body{max-height:none;flex:1 1 auto;min-height:0;overflow:auto}"
    "#canvas-area .key-head.first{margin-top:2px}#canvas-area .key-row input[type=date]{font-size:9px;padding:0 2px;border:1px solid #d6dccb;border-radius:3px;background:#fffef9;color:#4a5a46;width:104px}"
    "#canvas-area .key-link{display:block;margin:5px 0 2px;padding:0;border:0;background:none;color:#2f5a3a;font-size:10px;text-decoration:underline;cursor:pointer;text-align:left}"
    "#canvas-area .key-filter{margin:6px 0 4px;padding:7px 8px;border-radius:6px;background:#eef3e8;color:#2f4a33;font-size:11px}#canvas-area .key-filter .key-link{margin-top:6px}"
    "#canvas-area .key-seg{display:flex;gap:4px;margin-top:6px}#canvas-area .key-seg button{flex:1;font-size:10px;padding:3px 6px;border:1px solid #cfd8c4;border-radius:4px;background:#fffef9;cursor:pointer}"
    "#canvas-area .key-seg button.active{background:#4d6b43;border-color:#4d6b43;color:#fcfbf6}#canvas-area .key-hint{margin:6px 0 2px}"
    "#canvas-area .key-foot{margin-top:10px;padding-top:6px;border-top:1px solid #e3e6dc}"
    ".tooltip .tt-rs{color:#3d5a8a}"
    ".hunt-intro{font-size:12px;line-height:1.5;color:#4a5a46}.hunt-tools{display:flex;flex-wrap:wrap;gap:10px;align-items:center;font-size:12px}.hunt-tools input[type=number]{width:72px}"
    ".directory-table .link-button{display:block;padding:0;border:0;background:none;color:#2f5a3a;font:inherit;text-align:left;text-decoration:underline;cursor:pointer;margin-top:3px}"
    ".directory-table td small{display:block;color:#7d8a72;font-size:10px}.hunt-actions{display:flex;gap:8px;margin-top:12px}"
    "@media (max-width:700px){#canvas-area .canopy-key{display:none}}"
    "@media (max-width:700px){#canvas-area .v3-pan-controls,#canvas-area .canvas-status,#canvas-area #minimap-wrap{display:none!important}}"
)

STYLE_JS = (
    "/* Whole-tree layout fixes; generated by tools/atlas_whole_tree.py. */\n"
    "if(!document.getElementById('" + MARKER + "')){const st=document.createElement('style');st.id='" + MARKER + "';"
    "st.textContent=" + json.dumps(CSS) + ";document.head.append(st)}\n"
)

INSETS_JS = (
    "/* Free canvas area below the heading/year slider and above the bottom controls. */\n"
    "function canopyInsets(){const base=canvas.getBoundingClientRect();let top=24,bottom=24;"
    "for(const sel of ['#canvas-heading','#canopy-tools','#sun-tools','.canvas-bottom']){const el=$(sel);if(!el||!el.getClientRects().length)continue;"
    "const b=el.getBoundingClientRect(),y0=b.top-base.top,y1=b.bottom-base.top;if(y1<=0||y0>=H)continue;"
    "if(y0+y1<H)top=Math.max(top,y1+12);else bottom=Math.max(bottom,H-y0+10)}"
    "if(H-top-bottom<160){const f=Math.max(0,H-160)/Math.max(1,top+bottom);top*=Math.min(1,f);bottom*=Math.min(1,f)}"
    "return {top,bottom}}\n"
    "function earlyCam(animate=true){const b=atlas.coreBounds,{top,bottom}=canopyInsets(),ah=Math.max(120,H-top-bottom),"
    "k=Math.max(fitScale||.01,Math.min((W-70)/b.w,ah/b.h,1.1));setCam({k,x:W/2,y:top+ah/2},animate)}\n"
)

GRAND_JS = (
    "/* Grandparents filter: people with a recorded grandchild, sized by all their recorded descendants. */\n"
    "let GRAND=null,GRAND_RANK=[];\n"
    "function grandData(){if(GRAND)return GRAND;GRAND=new Map();for(const id of P.keys()){const kids=FAMILY.children.get(id)||[];"
    "if(kids.some(ch=>(FAMILY.children.get(ch)||[]).length))GRAND.set(id,FAMILY.descendants(id).length)}"
    "GRAND_RANK=[...GRAND.keys()].sort((a,b)=>GRAND.get(b)-GRAND.get(a));GRAND.ids=new Set(GRAND.keys());return GRAND}\n"
    "function grandPx(id){return clamp(1.8+Math.sqrt(GRAND.get(id)||0)*.42,2.2,14)*clamp(Math.pow(cam.k/fitScale,.35),1,1.7)}\n"
    "function setGrand(on){state.grand=!!on;if(state.grand)grandData();"
    "for(const [sel,val] of [['#grand-toggle',state.grand],['#grand-all',!state.grand]]){const b=$(sel);if(b){b.setAttribute('aria-pressed',String(val));b.classList.toggle('active',val)}}"
    "hideTooltip();uiBoxes=null;renderKey();invalidate();setHash()}\n"
    "function drawGrandLabels(guard,z){const max=z<1.6?14:z<3?26:z<7?45:70,v=canopyVis;let used=0;"
    "const order=state.selected&&GRAND.has(state.selected)?[state.selected,...GRAND_RANK.filter(id=>id!==state.selected)]:GRAND_RANK;"
    "for(const id of order){const n=scene.map.get(id);if(!n||!v.visible.has(id)||v.collapsedSet.has(id))continue;"
    "if(canopyFocus&&!canopyFocus.has(id)&&id!==state.selected)continue;if(!isMatch(n)||(MF&&!MF.has(id)))continue;"
    "const p=screen(n);if(p.x<12||p.x>W-12||p.y<64||p.y>H-54)continue;const pr=grandPx(id),person=P.get(id);"
    "ctx.font='12px '+SANS;const title=person.name+(yearNum(person)?' · '+yearText(person,'born'):''),sub=fmt(GRAND.get(id))+' descendants · '+shortPlace(person);"
    "const width=clamp(Math.max(ctx.measureText(title).width,ctx.measureText(sub).width*.8)+14,110,230),height=35,gap=pr+5;"
    "const tries=[{x:p.x+gap,y:p.y-height/2},{x:p.x-width-gap,y:p.y-height/2},{x:p.x-width/2,y:p.y-height-gap},{x:p.x-width/2,y:p.y+gap}];let b=null;"
    "for(const t of tries){const bb={...t,w:width,h:height,id,kind:'person-label'};if(guard.add({...bb,x:bb.x-2,y:bb.y-2,w:bb.w+4,h:bb.h+4})){b=bb;break}}if(!b)continue;"
    "const sel=state.selected===id;ctx.fillStyle=sel?'#edf3e5f5':'#fcfbf6f2';roundRect(b.x,b.y,b.w,b.h,4);ctx.fill();"
    "ctx.fillStyle=sel?'#2c5639':TEXTC[n.geo]||'#34503a';ctx.font='12px '+SANS;ctx.fillText(trimText(title,b.w-12),b.x+6,b.y+15);"
    "ctx.font='9px '+SANS;ctx.fillStyle='#68755e';ctx.fillText(trimText(sub,b.w-12),b.x+6,b.y+28);"
    "labels.push(b);addHit(id,'label',b);if(++used>=max)break}}\n"
)

GRAND_UI_JS = (
    "{const tools=$('#canopy-tools');if(tools&&!$('#grand-toggle')){const row=document.createElement('div');row.className='grand-row';"
    "row.innerHTML='<span class=\"grand-label\">Show</span><button type=\"button\" id=\"grand-all\" class=\"active\" aria-pressed=\"true\">Everyone</button>"
    "<button type=\"button\" id=\"grand-toggle\" aria-pressed=\"false\" title=\"Only people with at least one recorded grandchild. Dot size shows how many recorded descendants they have.\">Grandparents</button>';"
    "tools.append(row);$('#grand-toggle').onclick=()=>setGrand(true);$('#grand-all').onclick=()=>setGrand(false);"
    "row.insertAdjacentHTML('beforeend','<span class=\"grand-break g-col\"></span><span class=\"grand-label g-col\">Colour</span><button type=\"button\" id=\"colour-country\" class=\"active\" aria-pressed=\"true\">Country</button>"
    "<button type=\"button\" id=\"colour-branch\" aria-pressed=\"false\" title=\"Give neighbouring families different colours\">Family</button>"
    "<button type=\"button\" id=\"colour-evidence\" aria-pressed=\"false\" title=\"Colour each parent link by its evidence grade\">Evidence</button>"
    "<button type=\"button\" id=\"sun-open\" class=\"g-col sun-open\" title=\"Descendants of the selected person or family, one ring per generation\">☀ Family sun</button>');"
    "$('#sun-open').onclick=()=>enterSun(sunPick());"
    "$('#colour-country').onclick=()=>setLineColour('country');$('#colour-branch').onclick=()=>setLineColour('branch');$('#colour-evidence').onclick=()=>setLineColour('evidence');"
    "row.insertAdjacentHTML('beforeend','<span class=\"grand-label grand-label2 g-arr\">Arrange by</span><button type=\"button\" id=\"layout-year\" class=\"active\" aria-pressed=\"true\">Year</button>"
    "<button type=\"button\" id=\"layout-gen\" aria-pressed=\"false\" title=\"One ring per generation\">Generation</button>');"
    "$('#layout-year').onclick=()=>setLayout('year');$('#layout-gen').onclick=()=>setLayout('gen')}}\n"
    "{const area=$('#canvas-area');if(area&&!$('#canopy-key')){const k=document.createElement('section');k.id='canopy-key';k.className='canopy-key';k.setAttribute('aria-label','Key');"
    "let open=false;try{const v=localStorage.getItem('glasgow-atlas-key');if(v)open=v==='open'}catch{}k.dataset.open=open?'1':'0';"
    "k.innerHTML='<button type=\"button\" class=\"key-toggle\" aria-expanded=\"'+open+'\">Key</button><div class=\"key-body\"></div>';area.append(k);"
    "k.querySelector('.key-toggle').onclick=()=>{const o=k.dataset.open!=='1';k.dataset.open=o?'1':'0';k.querySelector('.key-toggle').setAttribute('aria-expanded',String(o));"
    "try{localStorage.setItem('glasgow-atlas-key',o?'open':'closed')}catch{};uiBoxes=null;renderKey();invalidate()};"
    "k.addEventListener('change',e=>{const g=e.target.dataset.gap;if(!g)return;if(e.target.checked)gapOn.add(g);else gapOn.delete(g);if(GAPS.find(x=>x.id===g)?.group==='status')loadRS();renderKey();invalidate()});renderKey()}}\n"
    "{const area=$('#canvas-area');if(area&&!$('#sun-tools')){area.insertAdjacentHTML('beforeend','<div class=\"canopy-tools sun-tools\" id=\"sun-tools\" hidden><button type=\"button\" data-action=\"sun-exit\">← Back to the whole tree</button></div>')}"
    "document.addEventListener('glasgow:tree-ready',()=>{if(state.sun)setTimeout(()=>sunFit(false),350)})}\n"
)

RIM_LABELS_JS = (
    " // Overview: horizontal family names in two columns, joined to their rim segment.\n"
    " if(cam.k/fitScale<=1.6&&W>=700){const z=cam.k/fitScale,per=Math.max(3,Math.min(Math.floor((H-140)/18),z<1.25?13:24)),gap=17,"
    "cand=s.wedges.filter(w=>w.kind!=='locality').sort((a,b)=>(b===fw||b===hw)-(a===fw||a===hw)||b.count-a.count),sides={l:[],r:[]};"
    "for(const w of cand){const a=(w.a0+w.a1)/2,dx=Math.cos(a),dy=Math.sin(a),side=dx<0?'l':'r';if(sides[side].length>=per)continue;"
    "sides[side].push({w,dx,dy,y:c.y+dy*(R+46)})}"
    "for(const side of ['l','r']){const list=sides[side].sort((p,q)=>p.y-q.y),sx=side==='r'?1:-1,colX=c.x+sx*(R+62),room=Math.min(230,side==='r'?W-14-colX:colX-14);if(room<70)continue;"
    "const minY=70,maxY=H-58;for(let i=0;i<list.length;i++)list[i].y=Math.max(list[i].y,i?list[i-1].y+gap:minY);"
    "for(let i=list.length-1;i>=0;i--)list[i].y=Math.min(list[i].y,i<list.length-1?list[i+1].y-gap:maxY);"
    "for(const L of list){const w=L.w,on=w===fw||w===hw;if(L.y<minY-1)continue;ctx.font=(on?'600 ':'')+'10.5px '+SANS;"
    "const tail=' · '+fmt(w.count),tailW=ctx.measureText(tail).width,name=trimText(w.name+(w.sub?' · '+w.sub:''),Math.max(30,room-tailW)),nameW=ctx.measureText(name).width,tw=nameW+tailW,"
    "bx=side==='r'?colX:colX-tw,box={x:bx-3,y:L.y-8,w:tw+6,h:16};if(!guard.add(box))continue;"
    "ctx.globalAlpha=fw&&!on&&!hw?.3:on?.95:.5;ctx.strokeStyle=geoOrBranch(w);ctx.lineWidth=on?1.3:.8;ctx.beginPath();"
    "ctx.moveTo(c.x+L.dx*(R+31),c.y+L.dy*(R+31));ctx.lineTo(c.x+L.dx*(R+40),c.y+L.dy*(R+40));ctx.lineTo(colX-sx*5,L.y);ctx.stroke();"
    "ctx.globalAlpha=fw&&!on&&!hw?.45:1;ctx.textBaseline='middle';ctx.textAlign='left';ctx.fillStyle=on?'#23402a':state.branch?wedgeColour(w):TEXTC[w.geo]||'#34503a';ctx.fillText(name,bx,L.y);"
    "ctx.font='10px '+SANS;ctx.fillStyle='#7d8a72';ctx.fillText(tail,bx+nameW,L.y);addHit(w.id,'wedge',box,{wedge:w})}}}\n"
    " else{\n"
)

FAMILY_AREAS_JS = (
    "/* Families first: each family branch is a tinted sector from its oldest member to the rim.\n"
    " * Hovering anywhere in it lights the branch up; clicking zooms to it. Fades out as you zoom in. */\n"
    "function wedgeInner(w){if(w.r0==null){let m=Infinity,M=0;for(const id of w.ids){const n=scene.map.get(id);if(n){if(n.r<m)m=n.r;if(n.r>M)M=n.r}}w.r0=Math.max(0,(isFinite(m)?m:scene.coreR)-26);w.rMax=M+40}return w.r0}\n"
    "function wedgeOuter(w,R){wedgeInner(w);return atlasGenMode?Math.min(R+4,w.rMax*cam.k):R+4}\n"
    "function drawFamilyAreas(c,R){const z=cam.k/fitScale;if(z>2.8||!scene.wedges)return;const fade=z<1.8?1:(2.8-z),fw=focusWedgeObj(),hw=hoverWedge;"
    "const list=scene.wedges.slice().sort((a,b)=>a.a0-b.a0);ctx.save();"
    "for(const [i,w] of list.entries()){const on=w===hw||w===fw,dim=state.geo&&!wedgeMix(w)[state.geo],r0=wedgeInner(w)*cam.k,r1=wedgeOuter(w,R);if(r1-r0<3)continue;"
    "const g=w.a1-w.a0>.004?.0015:0;ctx.beginPath();ctx.arc(c.x,c.y,r1,w.a0+g,w.a1-g);ctx.arc(c.x,c.y,r0,w.a1-g,w.a0+g,true);ctx.closePath();"
    "ctx.fillStyle=geoOrBranch(w);ctx.globalAlpha=fade*(on?.17:dim?.015:state.branch?.06:(i%2?.03:.07));ctx.fill();"
    "if(on){ctx.globalAlpha=fade*.65;ctx.strokeStyle=geoOrBranch(w);ctx.lineWidth=1.2;ctx.stroke()}}ctx.restore()}\n"
    "function familyAreaHit(x,y){if(scene?.type!=='all'||!scene.wedges||cam.k/fitScale>2.8)return null;const c=screen({x:0,y:0}),d=Math.hypot(x-c.x,y-c.y);"
    "if(d>scene.rimR*cam.k+4)return null;const w=wedgeAt(Math.atan2(y-c.y,x-c.x));if(!w||d<wedgeInner(w)*cam.k||d>wedgeOuter(w,scene.rimR*cam.k))return null;return {id:w.id,type:'wedge',wedge:w}}\n"
)

EXTRAS_JS = (
    "/* Colour by family branch: neighbouring families get different colours. */\n"
    "const BRANCH_PAL=['#3f6e9a','#b0652f','#3d8a6e','#9b4f74','#7a6bb0','#a8892a','#4f8fa8','#b4534f','#6b8a3a'];\n"
    "function branchColours(){const s=atlas;if(s.branchCol)return s.branchCol;const m=new Map(),list=s.wedges.slice().sort((a,b)=>a.a0-b.a0);let i=0;"
    "for(const w of list)w.colourB=w.kind==='locality'?'#a3a69c':BRANCH_PAL[i++%BRANCH_PAL.length];"
    "const fam=list.filter(w=>w.kind!=='locality');if(fam.length>2&&fam[0].colourB===fam.at(-1).colourB)fam.at(-1).colourB=BRANCH_PAL[(i+3)%BRANCH_PAL.length];"
    "for(const w of list)for(const id of w.ids)m.set(id,w.colourB);"
    "/* Very large families: colour each main sub-branch separately, as a family sun colours each child's line. */"
    "let j=i+5;const big=n=>n.children.map(id=>s.map.get(id)).filter(k=>k&&subtreeInfo(k).count>=25).sort((a,b)=>a.a0-b.a0);"
    "const split=(n,depth)=>{let kids=big(n);while(kids.length===1){n=kids[0];kids=big(n)}if(kids.length<2)return false;"
    "for(const k of kids){if(subtreeInfo(k).count>600&&depth<2&&split(k,depth+1))continue;const col=BRANCH_PAL[j++%BRANCH_PAL.length];for(const id of subtreeInfo(k).ids)m.set(id,col)}return true};"
    "for(const w of fam)if(w.count>=250){const n=s.map.get(w.id);if(n)split(n,0)}"
    "s.branchCol=m;return m}\n"
    "function branchColour(id){return branchColours().get(id)||'#a3a69c'}\n"
    "function wedgeColour(w){branchColours();return w.colourB||'#a3a69c'}\n"
    "function geoOrBranch(w){return state.branch?wedgeColour(w):(C[w.geo]||C.other)}\n"
    "function setBranch(on){setLineColour(on?'branch':'country')}\n"

)

SUN_JS = (
    "/* Family sun (after Tree Prism's Descendant Sun): rings are generations, a slice's width is its share of the\n"
    " * descendants, colour follows each child's line. Built from recorded parent links; a person reached by a second\n"
    " * line is drawn once more as an outline. */\n"
    "let SUN=null,sunHover=null,sunReturn=null;const SUN_R0=70,SUN_T=56;\n"
    "function sunBuild(rootId){const seen=new Set();let maxGen=0;"
    "function mk(id,gen,parent){const again=seen.has(id);seen.add(id);const node={id,gen,children:[],size:1,again,parent};if(gen>maxGen)maxGen=gen;"
    "if(!again&&gen<16)for(const c of (FAMILY.children.get(id)||[]).slice().sort((a,b)=>(yearNum(P.get(a))||9999)-(yearNum(P.get(b))||9999))){const ch=mk(c,gen+1,node);node.children.push(ch);node.size+=ch.size}return node}"
    "const root=mk(rootId,0,null),rings=[];"
    "(function lay(n,a0,a1,branch){n.a0=a0;n.a1=a1;n.branch=branch;(rings[n.gen]||(rings[n.gen]=[])).push(n);let a=a0;const tot=n.size-1||1;"
    "for(const c of n.children){const w=(a1-a0)*c.size/tot;lay(c,a,a+w,n.gen===0?c:branch);a+=w}})(root,-Math.PI/2,Math.PI*1.5,null);"
    "/* Colours start where the family first splits into real lines; a dominant line is split again. */"
    "const total=root.size;let j=0;const paint=(n,col)=>{n.col=col;for(const c of n.children)paint(c,col)};"
    "const assign=(n,depth)=>{let kids=n.children.filter(c=>c.size>=Math.max(3,total*.01));while(kids.length===1){n=kids[0];kids=n.children.filter(c=>c.size>=Math.max(3,total*.01))}"
    "for(const c of n.children){if(kids.includes(c)&&c.size>total*.45&&depth<2){assign(c,depth+1);continue}paint(c,kids.includes(c)?BRANCH_PAL[j++%BRANCH_PAL.length]:'#8f9c86')}};assign(root,0);"
    "return {root,rings,maxGen,unique:seen.size-1}}\n"
    "function sunPick(){const kids=id=>(FAMILY.children.get(id)||[]).length;if(state.selected&&P.has(state.selected)&&kids(state.selected))return state.selected;"
    "const fw=focusWedgeObj();if(fw&&fw.founder)return fw.founder;const w=atlas.wedges.filter(w=>w.founder).sort((a,b)=>b.count-a.count)[0];return w?w.founder:[...P.keys()][0]}\n"
    "function sunFit(animate=true){if(!SUN)return;const {top,bottom}=canopyInsets(),R=SUN_R0+Math.max(1,SUN.maxGen)*SUN_T+24,ah=Math.max(160,H-top-bottom),"
    "k=Math.min((W-40)/(2*R),ah/(2*R));SUN.fitK=k;setCam({k,x:W/2,y:top+ah/2},animate)}\n"
    "function enterSun(id){if(!P.has(id))return;if(state.view!=='all')goView('all');if(!state.sun)sunReturn={cam:{...cam},branchFocus:state.branchFocus};"
    "state.sun=id;state.branchFocus=null;hoverWedge=null;canopyFocus=null;SUN=sunBuild(id);sunHover=null;hideTooltip();uiBoxes=null;syncUI();sunFit(true);setHash()}\n"
    "function exitSun(){if(!state.sun)return;state.sun=null;SUN=null;sunHover=null;hideTooltip();uiBoxes=null;const back=sunReturn;sunReturn=null;"
    "if(back){state.branchFocus=back.branchFocus;syncUI();setCam(back.cam)}else{syncUI();fit()}setHash()}\n"
    "function sunSync(){const on=!!state.sun&&state.view==='all',st=$('#sun-tools');if(st)st.hidden=!on;if(!on)return;"
    "for(const sel of ['#canopy-tools','#minimap-wrap']){const el=$(sel);if(el)el.hidden=true}const p=P.get(state.sun);"
    "$('#canvas-overline').textContent='FAMILY SUN';$('#canvas-title').textContent=p.name+' & descendants';"
    "$('#canvas-sub').textContent='Rings are generations. A slice’s width shows its share of the descendants; colour follows each child’s line.';"
    "$('#interaction-hint').textContent='Hover to follow a line · click for a profile · double-click to centre the sun there'}\n"
    "function sunNodeAt(wx,wy){if(!SUN)return null;const r=Math.hypot(wx,wy);if(r<SUN_R0)return SUN.root;const g=Math.ceil((r-SUN_R0)/SUN_T);if(g<1||g>SUN.maxGen)return null;"
    "let a=Math.atan2(wy,wx);if(a<-Math.PI/2)a+=TAU;const ring=SUN.rings[g]||[];let lo=0,hi=ring.length-1;"
    "while(lo<=hi){const m=(lo+hi)>>1,n=ring[m];if(a<n.a0)hi=m-1;else if(a>=n.a1)lo=m+1;else return n}return null}\n"
    "function sunHit(x,y){const n=sunNodeAt((x-cam.x)/cam.k,(y-cam.y)/cam.k);if(n!==sunHover){sunHover=n;invalidate()}return n?{id:n.id,type:'sun',node:n,x:x-4,y:y-4,w:8,h:8}:null}\n"
    "function sunCol(n){return n.col||'#7d9471'}\n"
    "function drawSun(){const t0=performance.now();ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#fcfbf6';ctx.fillRect(0,0,W,H);hits=[];labels=[];dnaPinPositions.clear();"
    "{const kk=$('#canopy-key');if(kk)kk.hidden=true}if(!SUN)return;const k=cam.k,c={x:cam.x,y:cam.y},hv=sunHover&&sunHover!==SUN.root?sunHover:null,sel=state.selected,"
    "inHv=n=>!hv||(n.a1>hv.a0+1e-9&&n.a0<hv.a1-1e-9),fillA=g=>Math.max(.28,.9-g*.07);"
    "for(let g=1;g<=SUN.maxGen;g++){const r0=(SUN_R0+(g-1)*SUN_T)*k,r1=(SUN_R0+g*SUN_T-3)*k;if(r1<1)continue;"
    "for(const n of SUN.rings[g]||[]){const span=n.a1-n.a0;if(span*r1<.25)continue;const gap=Math.min(.004,span*.12),a0=n.a0+gap,a1=n.a1-gap,col=sunCol(n);"
    "ctx.beginPath();ctx.arc(c.x,c.y,r1,a0,a1);ctx.arc(c.x,c.y,r0,a1,a0,true);ctx.closePath();ctx.globalAlpha=(inHv(n)?1:.22)*fillA(g);ctx.fillStyle=n.again?'#fcfbf6':col;ctx.fill();"
    "if(n.again){ctx.globalAlpha=inHv(n)?.85:.25;ctx.strokeStyle=col;ctx.lineWidth=1;ctx.stroke()}"
    "if(n.id===sel){ctx.globalAlpha=1;ctx.strokeStyle='#23402a';ctx.lineWidth=2;ctx.stroke()}"
    "if(state.pins&&DNA.has(n.id)&&!n.again&&span*r1>7){const mid=(n.a0+n.a1)/2;ctx.globalAlpha=inHv(n)?1:.3;drawDNAMarker(DNA.get(n.id),c.x+Math.cos(mid)*(r1-7),c.y+Math.sin(mid)*(r1-7),false)}}}"
    "ctx.globalAlpha=1;ctx.textBaseline='middle';"
    "for(let g=1;g<=SUN.maxGen;g++){const th=(SUN_T-3)*k,rm=(SUN_R0+(g-.5)*SUN_T)*k;if(th<9)break;const light=fillA(g)<.55;"
    "for(const n of SUN.rings[g]||[]){if(!inHv(n))continue;const span=n.a1-n.a0,al=span*rm;if(al<9)continue;const p=P.get(n.id),mid=(n.a0+n.a1)/2,x=c.x+Math.cos(mid)*rm,y=c.y+Math.sin(mid)*rm;"
    "if(x<-60||x>W+60||y<-60||y>H+60)continue;const ink=n.again||light?'#1f3324':'#ffffff';ctx.save();ctx.translate(x,y);ctx.textAlign='center';"
    "if(al>th*1.2&&al>54){let rot=mid+Math.PI/2;if(Math.sin(mid)>0)rot+=Math.PI;ctx.rotate(rot);const fs=clamp(th*.26,8,13),two=th>fs*2.7;"
    "ctx.font=fs+'px '+SANS;ctx.fillStyle=ink;ctx.fillText(trimText(p.name,al-8),0,two?-fs*.6:0);"
    "if(two){ctx.font=(fs-1.5)+'px '+SANS;ctx.globalAlpha=.85;ctx.fillText(trimText((yearNum(p)?yearText(p,'born'):'')+(n.size>1?(yearNum(p)?' · ':'')+fmt(n.size-1)+' desc.':''),al-8),0,fs*.75);ctx.globalAlpha=1}}"
    "else if(th>40){let rot=mid;if(Math.cos(mid)<0)rot+=Math.PI;ctx.rotate(rot);const fs=clamp(al*.7,7,11);ctx.font=fs+'px '+SANS;ctx.fillStyle=ink;"
    "ctx.fillText(trimText(firstName(p)+(yearNum(p)?' · '+yearText(p,'born'):''),th-6),0,0)}ctx.restore()}}"
    "const rp=P.get(SUN.root.id),cr=SUN_R0*k;ctx.beginPath();ctx.arc(c.x,c.y,Math.max(0,cr-3),0,TAU);ctx.fillStyle=SUN.root.id===sel?'#edf3e5':'#fffef8';ctx.fill();ctx.strokeStyle='#c9d3bd';ctx.lineWidth=1;ctx.stroke();"
    "if(cr>34){ctx.textAlign='center';ctx.fillStyle='#23402a';const fs=clamp(cr*.19,10,22);ctx.font=fs+'px '+SERIF;ctx.fillText(trimText(rp.name,cr*1.8),c.x,c.y-fs*.6);"
    "ctx.font=clamp(cr*.11,8,12)+'px '+SANS;ctx.fillStyle='#55665a';ctx.fillText(trimText(life(rp),cr*1.7),c.x,c.y+fs*.4);"
    "ctx.fillText(fmt(SUN.unique)+' descendants · '+SUN.maxGen+' generations',c.x,c.y+fs*.4+clamp(cr*.13,10,15))}"
    "ctx.textAlign='left';ctx.textBaseline='alphabetic';"
    "$('#zoom-readout').textContent=Math.round(cam.k/(SUN.fitK||cam.k)*100)+'%';"
    "$('#visible-records').textContent=`${fmt(SUN.unique)} descendants of ${rp.name} · ${SUN.maxGen} generations`;"
    "perf={...perf,drawMs:performance.now()-t0,frames:(perf.frames||0)+1};drawMini()}\n"
)

GEN_JS = (
    "/* Arrange by generation (after Tree Prism's Branches view): each person one ring outside their parent,\n"
    " * every family starting on the first ring; partners share their spouse's ring. */\n"
    "let atlasGenMode=false;const GEN_R0=260,GEN_STEP=110;\n"
    "function setLayout(mode){const gen=mode==='gen';if(gen===atlasGenMode)return;atlasGenMode=gen;"
    "for(const [sel,val] of [['#layout-gen',gen],['#layout-year',!gen]]){const b=$(sel);if(b){b.setAttribute('aria-pressed',String(val));b.classList.toggle('active',val)}}"
    "const keep=state.branchFocus;atlas=makeAtlas();canopyVis=null;overlayCache={set:null,mode:'',paths:null};hoverWedge=null;canopyFocus=null;"
    "if(state.view==='all'&&!state.sun){scene=atlas;state.branchFocus=null;if(state.early){state.early=false}syncUI();fit(true)}else if(state.view==='all')scene=atlas;"
    "const sub=$('#canvas-sub');if(sub&&!state.sun&&state.view==='all'&&!state.early)sub.textContent=gen?'Each ring is one generation: a person sits one ring outside their parent, and every family starts on the first ring.':'Time runs outward from 1450. Drag the year slider to watch the families grow.';"
    "setHash()}\n"
)

RESEARCH_JS = r'''
/* Marks filter: when any mark is ticked, only the people who match are drawn, labelled and clickable. */
let MF=null,markMode='any',mfKey='',mfCache=null,gapVer=0;
function markFilter(){if(!gapOn.size)return null;const data=gapData(),key=[...gapOn].sort().join(',')+'|'+markMode+'|'+gapVer;if(mfCache&&mfKey===key)return mfCache;
 const on=GAPS.filter(g=>gapOn.has(g.id));let out;
 if(markMode==='all'){out=new Set(data.get(on[0].id));for(const g of on.slice(1)){const set=data.get(g.id);for(const id of [...out])if(!set.has(id))out.delete(id)}}
 else{out=new Set();for(const g of on)for(const id of data.get(g.id))out.add(id)}
 mfCache=out;mfKey=key;return out}
function markColour(id){const data=gapData();for(const g of GAPS)if(gapOn.has(g.id)&&data.get(g.id).has(id))return g.col;return '#9aa294'}
function markSummary(){return GAPS.filter(g=>gapOn.has(g.id)).map(g=>g.id==='new'?'new finding since '+fmtDay(newSince):g.label.replace(/^([A-Z])([a-z]*)(?=[\s,])/,(m,a,b)=>a.toLowerCase()+b)).join(markMode==='all'?' and ':' or ')}
/* Research layer: evidence grades on links, research status, Y-DNA coverage and the connection hunt.
 * Status flags come from /assets/research/tree-research-status.json (tools/build_tree_research_status.py). */
/* (filter helpers below) */
const EV=[
 {id:'proven',label:'Documented or DNA-confirmed',col:'#1d5c3a',w:2.3,st:['proved','DNA-confirmed','dna_confirmed']},
 {id:'strong',label:'Strongly supported',col:'#3f8a55',w:1.9,st:['strongly_supported']},
 {id:'probable',label:'Probable',col:'#c08a1e',w:1.7,st:['probable']},
 {id:'uncertain',label:'Possible or uncertain',col:'#c0453c',w:1.6,st:['possible','uncertain']},
 {id:'tree',label:'Marked confident on WikiTree, not reviewed',col:'#8ea4bc',w:1.05,st:['confident']},
 {id:'unassessed',label:'Not yet assessed',col:'#d2d6cb',w:.85,st:['unmarked','']}];
const EV_BY_STATUS=new Map(),EV_BY_COL=new Map();EV.forEach((g,i)=>{g.rank=i;g.st.forEach(s=>EV_BY_STATUS.set(s,g));EV_BY_COL.set(g.col,g)});
function evidenceGroup(status){return EV_BY_STATUS.get(status||'')||EV[EV.length-1]}
function evidenceColour(e){return e.type!=='recorded'?'#d9dcd2':evidenceGroup(e.status).col}
function evRank(key){const g=EV_BY_COL.get(String(key).split('|')[0]);return g?EV.length-g.rank:0}
function evWidth(col){const g=EV_BY_COL.get(col);return g?g.w:1.05}
let EV_COUNTS=null;
function evidenceCounts(){if(EV_COUNTS)return EV_COUNTS;EV_COUNTS=new Map(EV.map(g=>[g.id,0]));for(const rr of FAMILY.parents.values())for(const r of rr){const g=evidenceGroup(r.status);EV_COUNTS.set(g.id,EV_COUNTS.get(g.id)+1)}return EV_COUNTS}
function dotColour(n){return MF?markColour(n.id):state.evidence?'#9aa294':state.branch?branchColour(n.id):n.colour}
function setLineColour(mode){state.branch=mode==='branch';state.evidence=mode==='evidence';canopyVis=null;overlayCache.set=null;
 for(const [sel,val] of [['#colour-country',mode==='country'],['#colour-branch',state.branch],['#colour-evidence',state.evidence]]){const b=$(sel);if(b){b.setAttribute('aria-pressed',String(val));b.classList.toggle('active',val)}}
 renderKey();invalidate();setHash()}

let RS=null,rsLoading=null,newSince='';
function loadRS(){if(RS)return Promise.resolve(RS);if(!rsLoading)rsLoading=fetch('/assets/research/tree-research-status.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('missing');return r.json()}).then(d=>{RS=d;
  if(!newSince){const t=new Date((d.generated||new Date().toISOString().slice(0,10))+'T00:00:00');t.setDate(t.getDate()-30);newSince=t.toISOString().slice(0,10)}
  gapCache=null;renderKey();invalidate();return RS}).catch(()=>{RS={people:{},failed:true};renderKey();return RS});return rsLoading}
const rsOf=id=>RS&&RS.people&&RS.people[id]||null;
const fmtDay=s=>{const d=new Date(String(s)+'T00:00:00');return isNaN(d)?String(s):d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})};
function rsLine(id){const r=rsOf(id);if(!r)return '';const bits=[];if(r.r)bits.push(r.c?'research notes with a conclusion':'research notes');if(r.n)bits.push('newest finding '+fmtDay(r.n));
 if(r.q==='open')bits.push('WikiTree update waiting');if(r.q==='blocked')bits.push('WikiTree update blocked (another manager)');
 if(r.d&&r.d.length)bits.push('needs a decision: '+r.d.map(c=>(RS.decisionLabels||{})[c]||c).join('; '));return bits.length?`<small class="tt-rs">${esc(bits.join(' · '))}</small>`:''}

const glasName=id=>/^glas/i.test(String(P.get(id)?.surname||''));
const fatherOf=id=>{const r=(FAMILY.parents.get(id)||[]).find(r=>r.role==='father');return r&&P.has(r.id)?r.id:null};
let YD=null;
function ydnaData(){if(YD)return YD;const topOf=new Map(),clans=new Map();
 const top=id=>{if(topOf.has(id))return topOf.get(id);const seen=new Set([id]);let t=id;for(;;){const f=fatherOf(t);if(!f||seen.has(f))break;seen.add(f);t=f}topOf.set(id,t);return t};
 for(const id of P.keys()){if(P.get(id).sex!=='Male'||!glasName(id))continue;const t=top(id);if(!clans.has(t))clans.set(t,{top:t,men:[]});clans.get(t).men.push(id)}
 const covered=new Set(),gap=new Set(),gaps=[];let tested=0;
 for(const c of clans.values()){c.tested=DNA.has(c.top)||c.men.some(id=>DNA.has(id));if(c.tested){tested++;c.men.forEach(id=>covered.add(id))}else if(c.men.length>=10){c.men.forEach(id=>gap.add(id));gaps.push(c)}}
 gaps.sort((a,b)=>b.men.length-a.men.length);YD={covered,gap,gaps,clans,tested};return YD}

let HUNT=new Set(),HUNT_BASE=null,huntFilter={geo:'all',from:1700,to:1900,min:1,cands:true};
const COUNTRY_WORDS=new Set(['united kingdom','uk','great britain','britain','united states','united states of america','usa','us','ireland','northern ireland','republic of ireland','scotland','england','wales','canada','australia','new zealand']);
function placeParts(s){const parts=String(s||'').split(',').map(x=>x.trim().toLowerCase()).filter(Boolean);while(parts.length&&COUNTRY_WORDS.has(parts.at(-1)))parts.pop();return {region:(parts.at(-1)||'').replace(/^(county|co\.?)\s+/,'').replace(/\s+(county|shire)$/,'')}}
function huntBase(){if(HUNT_BASE)return HUNT_BASE;const men=[],heads=[];
 for(const id of P.keys()){const p=P.get(id);if(p.sex!=='Male'||!glasName(id))continue;const y=yearNum(p);if(!y)continue;
  men.push({id,y,d:yearNum(p,'died'),b:placeParts(p.birthplace),dp:placeParts(p.deathplace),home:place(id).home,kids:(FAMILY.children.get(id)||[]).map(c=>yearNum(P.get(c))).filter(Boolean)})}
 for(const id of P.keys()){if(!glasName(id)||fatherOf(id))continue;const p=P.get(id),y=yearNum(p);if(y&&y>1920)continue;
  heads.push({id,y,size:FAMILY.descendants(id).length,home:place(id).home,b:placeParts(p.birthplace||p.deathplace)})}
 HUNT_BASE={men,heads};return HUNT_BASE}
function huntCandidates(h){if(h.cands)return h.cands;const out=[];
 if(h.y)for(const m of huntBase().men){if(m.id===h.id)continue;const gap=h.y-m.y;if(gap<17||gap>55||(m.d&&m.d<h.y-1))continue;let score=0;const why=[];
  if(h.b.region&&(m.b.region===h.b.region||m.dp.region===h.b.region)){score+=3;why.push('same county or state ('+h.b.region.replace(/\b\w/g,c=>c.toUpperCase())+')')}
  else if(m.home===h.home&&h.home!=='other'){score+=1;why.push('same country')}
  const near=m.kids.filter(y=>Math.abs(y-h.y)<=12);if(near.length){score+=2;why.push('children born '+(Math.min(...near)===Math.max(...near)?Math.min(...near):Math.min(...near)+'–'+Math.max(...near)))}
  if(gap>=22&&gap<=40)score+=1;why.push('born '+gap+' years earlier');if(score>=3)out.push({id:m.id,score,why,gap})}
 out.sort((a,b)=>b.score-a.score||Math.abs(a.gap-30)-Math.abs(b.gap-30));h.cands=out.slice(0,3);return h.cands}
function huntRows(){const f=huntFilter;return huntBase().heads.filter(h=>h.y&&h.y>=f.from&&h.y<=f.to&&(f.geo==='all'||h.home===f.geo)&&h.size+1>=f.min&&(!f.cands||huntCandidates(h).length)).sort((a,b)=>b.size-a.size||a.y-b.y)}
function openHunt(){modal('Families to connect',`<p class="hunt-intro">People with the Glasgow surname and no father in the tree: each heads a separate family. <b>People to check</b> are men of the surname born 17–55 years earlier in the same county or state and alive at the birth, preferring men with other children born near that time. They are leads chosen by date and place only, not proposed fathers; a link needs a record.</p>
<div class="dir-tools hunt-tools"><select id="hunt-geo" class="subtle-select" aria-label="Country"><option value="all">All places</option>${GEO.map(g=>`<option value="${g.id}">${esc(g.short)}</option>`).join('')}</select>
<label>Born <input id="hunt-from" type="number" min="1450" max="1920" step="10" value="${huntFilter.from}"> to <input id="hunt-to" type="number" min="1450" max="1920" step="10" value="${huntFilter.to}"></label>
<select id="hunt-min" class="subtle-select" aria-label="Family size"><option value="1">Any family size</option><option value="2">2 or more people</option><option value="5">5 or more</option><option value="10">10 or more</option><option value="25">25 or more</option></select>
<label><input id="hunt-cands" type="checkbox" ${huntFilter.cands?'checked':''}> Only with people to check</label></div>
<div class="query-count" id="hunt-count"></div><div class="table-wrap"><table class="directory-table hunt-table"><thead><tr><th>PERSON</th><th>BORN</th><th>PLACE</th><th>FAMILY</th><th>PEOPLE TO CHECK</th></tr></thead><tbody id="hunt-body"></tbody></table></div>
<div class="hunt-actions"><button type="button" class="tool-btn" data-action="hunt-show">Mark these on the tree</button><button type="button" class="tool-btn" data-action="hunt-csv">Download CSV</button></div>`,true);
 $('#hunt-geo').value=huntFilter.geo;$('#hunt-min').value=String(huntFilter.min);
 const upd=()=>{huntFilter={geo:$('#hunt-geo').value,from:+$('#hunt-from').value||1450,to:+$('#hunt-to').value||1920,min:+$('#hunt-min').value||1,cands:$('#hunt-cands').checked};renderHunt()};
 for(const id of ['hunt-geo','hunt-from','hunt-to','hunt-min','hunt-cands'])$('#'+id).onchange=upd;renderHunt()}
function renderHunt(){const rows=huntRows(),shown=rows.slice(0,150);
 $('#hunt-count').textContent=`${fmt(rows.length)} ${rows.length===1?'person':'people'}${rows.length>shown.length?' · showing the '+shown.length+' largest families':''}`;
 $('#hunt-body').innerHTML=shown.map(h=>{const p=P.get(h.id),c=huntCandidates(h);return `<tr><td><button class="link-button" data-action="dir-person" data-id="${esc(h.id)}">${esc(p.name)}</button><small>${esc(h.id)}</small></td><td>${esc(yearText(p,'born')||'—')}</td><td>${esc(shortPlace(p))}</td><td>${fmt(h.size+1)}</td><td>${c.length?c.map(x=>{const q=P.get(x.id);return `<button class="link-button" data-action="dir-person" data-id="${esc(x.id)}">${esc(q.name)} · ${esc(yearText(q,'born'))}</button><small>${esc(x.why.join(' · '))}</small>`}).join(''):'<small>none in the tree</small>'}</td></tr>`}).join('')||'<tr><td colspan="5">No one matches these filters.</td></tr>'}
function huntShow(){HUNT=new Set(huntRows().map(h=>h.id));gapOn.add('hunt');gapCache=null;closeModal();const k=$('#canopy-key');if(k&&k.dataset.open!=='1')k.querySelector('.key-toggle').click();renderKey();invalidate();toast(fmt(HUNT.size)+' people marked on the tree')}
function csvCell(v){return '"'+String(v??'').replace(/"/g,'""')+'"'}
const pageUrl=id=>new URL(P.get(id)?.researchUrl||('/people/'+id.toLowerCase()+'.html'),location.href).href;
function csvText(rows){return rows.map(r=>r.map(csvCell).join(',')).join('\n')+'\n'}
function huntCsv(){const rows=[['ID','Name','Born','Place','Family size','Page','Person to check 1','Why 1','Person to check 2','Why 2','Person to check 3','Why 3']];
 for(const h of huntRows()){const p=P.get(h.id),row=[h.id,p.name,yearText(p,'born'),shortPlace(p),h.size+1,pageUrl(h.id)];for(const c of huntCandidates(h)){const q=P.get(c.id);row.push(`${q.name} (${c.id}) ${yearText(q,'born')}`,c.why.join('; '))}rows.push(row)}
 download('glasgow-families-to-connect.csv',csvText(rows),'text/csv')}
function openYdna(){const y=ydnaData();modal('Male lines without a Y-DNA result',`<p class="hunt-intro">Glasgow-surname men grouped by their earliest male-line ancestor in the tree. ${fmt(y.tested)} lines include a numbered Y-DNA marker; these ${fmt(y.gaps.length)} lines of 10 or more men have none. A test by a living male-line descendant would place the line on the project’s Y-DNA tree. Lines follow recorded father links of any grade, so an uncertain link can join or split a line.</p>
<div class="table-wrap"><table class="directory-table"><thead><tr><th>EARLIEST MALE-LINE ANCESTOR</th><th>BORN</th><th>PLACE</th><th>MEN</th><th>LATEST BIRTH</th></tr></thead><tbody>${y.gaps.map(c=>{const p=P.get(c.top),latest=Math.max(0,...c.men.map(id=>yearNum(P.get(id))||0));
 return `<tr><td><button class="link-button" data-action="dir-person" data-id="${esc(c.top)}">${esc(p.name)}</button><small>${esc(c.top)}</small></td><td>${esc(yearText(p,'born')||'—')}</td><td>${esc(shortPlace(p))}</td><td>${fmt(c.men.length)}</td><td>${latest||'—'}</td></tr>`}).join('')}</tbody></table></div>
<div class="hunt-actions"><button type="button" class="tool-btn" data-action="ydna-csv">Download CSV</button></div>`,true)}
function ydnaCsv(){const rows=[['Earliest male-line ancestor','ID','Born','Place','Men in the line','Latest birth','Page']];
 for(const c of ydnaData().gaps){const p=P.get(c.top);rows.push([p.name,c.top,yearText(p,'born'),shortPlace(p),c.men.length,Math.max(0,...c.men.map(id=>yearNum(P.get(id))||0))||'',pageUrl(c.top)])}
 download('glasgow-male-lines-without-ydna.csv',csvText(rows),'text/csv')}
function exportMarked(){const data=gapData(),on=GAPS.filter(g=>gapOn.has(g.id));if(!on.length){toast('Switch on a mark in the key first.');return}
 const rows=[['ID','Name','Born','Died','Birthplace','Deathplace','Marks','Page']];
 for(const [id,p] of P){const marks=on.filter(g=>data.get(g.id).has(id)).map(g=>g.id==='new'?'New finding since '+newSince:g.label);if(!marks.length)continue;
  rows.push([id,p.name,p.birthDisplay||p.born||'',p.deathDisplay||p.died||'',p.birthplace||'',p.deathplace||'',marks.join('; '),pageUrl(id)])}
 download('glasgow-tree-marked-people.csv',csvText(rows),'text/csv');toast(fmt(rows.length-1)+' people downloaded')}

/* Research marks: small squares beside a person. */
function diedYoung(id){const p=P.get(id),b=yearNum(p),d=yearNum(p,'died');return !!(b&&d&&d>=b&&d-b<16)}
const GAPS=[
 {id:'researched',group:'status',label:'Researched',col:'#2f7d55',test:id=>!!rsOf(id)?.r},
 {id:'new',group:'status',label:'New finding since',col:'#e3a21a',test:id=>{const r=rsOf(id);return !!(r&&r.n&&newSince&&r.n>=newSince)}},
 {id:'wt-open',group:'status',label:'WikiTree update waiting',col:'#2f6db5',test:id=>rsOf(id)?.q==='open'},
 {id:'wt-blocked',group:'status',label:'WikiTree update blocked',col:'#7b7f86',test:id=>rsOf(id)?.q==='blocked'},
 {id:'decide',group:'status',label:'Needs a decision',col:'#d23b2f',test:id=>!!(rsOf(id)?.d?.length)},
 {id:'father-uncertain',group:'gaps',label:'Father uncertain',col:'#8a3b6f',test:id=>(FAMILY.parents.get(id)||[]).some(r=>r.role==='father'&&(r.status==='uncertain'||!!r.hypothesis))},
 {id:'no-father',group:'gaps',label:'No father recorded',col:'#c0563f',test:id=>!(FAMILY.parents.get(id)||[]).some(r=>r.role==='father')},
 {id:'no-children',group:'gaps',label:'No children recorded',col:'#b5862a',test:id=>!(FAMILY.children.get(id)||[]).length&&!diedYoung(id)&&(yearNum(P.get(id))||0)<1920},
 {id:'no-spouse',group:'gaps',label:'No spouse recorded',col:'#4f6f8f',test:id=>!(FAMILY.partners.get(id)||[]).length&&!diedYoung(id)&&(yearNum(P.get(id))||0)<1920},
 {id:'died-young',group:'gaps',label:'Died before 16',col:'#7a5fb0',test:id=>diedYoung(id)},
 {id:'ydna-tested',group:'ydna',label:'Male line with a Y-DNA result',col:'#5b2a86',test:id=>ydnaData().covered.has(id)},
 {id:'ydna-gap',group:'ydna',label:'Large male line, no result',col:'#e07b28',test:id=>ydnaData().gap.has(id)},
 {id:'hunt',group:'hunt',label:'Families to connect (your list)',col:'#c2185b',test:id=>HUNT.has(id)}];
let gapOn=new Set(),gapCache=null;
function gapData(){if(gapCache)return gapCache;gapVer++;gapCache=new Map();for(const g of GAPS){const set=new Set();for(const id of P.keys())if(g.test(id))set.add(id);gapCache.set(g.id,set)}return gapCache}
function drawGapMarks(viewbox){if(!gapOn.size||!canopyVis||gapOn.size<2)return;const data=gapData(),v=canopyVis,c=screen({x:0,y:0}),order=GAPS.filter(g=>gapOn.has(g.id)),paths=order.map(()=>new Path2D()),sz=cam.k/fitScale<1.5?2.6:3.4;
 for(const n of v.persons){if(state.grand&&!GRAND.has(n.id))continue;if(v.collapsedSet.has(n.id)||!intersects({x:n.x,y:n.y,w:0,h:0},viewbox))continue;let k=0,p=null,a=0;
  for(let i=0;i<order.length;i++){if(!data.get(order[i].id).has(n.id))continue;if(!p){p=screen(n);a=Math.atan2(p.y-c.y,p.x-c.x)}
   const d=(state.grand?grandPx(n.id):2.6)+2.4+k*(sz+1.2);paths[i].rect(p.x+Math.cos(a)*d-sz/2,p.y+Math.sin(a)*d-sz/2,sz,sz);k++}}
 ctx.save();ctx.globalAlpha=canopyFocus?.4:.95;order.forEach((g,i)=>{ctx.fillStyle=g.col;ctx.fill(paths[i])});ctx.restore()}

/* The key card: encodings, then the research switches and lists. */
function renderKey(){const el=$('#canopy-key');if(!el)return;const body=el.querySelector('.key-body'),open=el.dataset.open==='1',mf=MF=markFilter();
 if(open||[...gapOn].some(id=>GAPS.find(g=>g.id===id)?.group==='status'))loadRS();
 if(!el.dataset.bound){el.dataset.bound='1';el.addEventListener('change',e=>{if(e.target.id==='key-since'){newSince=e.target.value;gapCache=null;renderKey();invalidate()}});
  el.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.keyMode){markMode=b.dataset.keyMode;renderKey();invalidate()}else if(b.dataset.keyClear){gapOn.clear();renderKey();invalidate()}})}
 const data=gapData(),
 line=(dash,label,col='#55705a',w=1.6)=>`<div class="key-row"><svg width="24" height="8" aria-hidden="true"><line x1="1" y1="4" x2="23" y2="4" stroke="${col}" stroke-width="${w}" stroke-dasharray="${dash}"/></svg><span>${label}</span></div>`,
 grad=cols=>`linear-gradient(90deg,${cols.join(',')})`,
 rows=group=>GAPS.filter(g=>g.group===group).map(g=>`<label class="key-row key-mark"><input type="checkbox" data-gap="${g.id}" ${gapOn.has(g.id)?'checked':''}><span class="key-sq" style="background:${g.col}"></span><span>${esc(g.label)}${g.id==='new'?` <input type="date" id="key-since" value="${esc(newSince)}" aria-label="New since">`:''}</span><small>${g.group==='status'&&!RS?'…':fmt(data.get(g.id).size)}</small></label>`).join('');
 const colour=state.evidence
  ?'<div class="key-head first">Parent links by evidence</div>'+EV.map(g=>`<div class="key-row"><svg width="24" height="8" aria-hidden="true"><line x1="1" y1="4" x2="23" y2="4" stroke="${g.col}" stroke-width="${Math.max(1.3,g.w*1.2)}" ${g.id==='uncertain'?'stroke-dasharray="5 3"':''}/></svg><span>${esc(g.label)}</span><small>${fmt(evidenceCounts().get(g.id))}</small></div>`).join('')
  :(state.branch?`<div class="key-row"><span class="key-sw" style="background:${grad(BRANCH_PAL.slice(0,6))}"></span>Colour: family branch</div>`
   :`<div class="key-row"><span class="key-sw" style="background:${grad(['scotland','ireland','america','canada','england'].map(g=>C[g]))}"></span>Colour: country${state.colourMode==='journeys'?' (birth → death)':''}</div>`)
   +line('','Parent → child')+line('5 3','Uncertain parentage');
 body.innerHTML=colour+line('2 3','Partner or co-parent')
  +(state.grand?'<div class="key-row"><span class="key-dots"><i></i><i></i></span>Dot size: recorded descendants</div>':'<div class="key-row"><span class="key-dots"><i></i></span>One dot, one person</div>')
  +'<div class="key-row"><span class="key-dna">◆</span>Numbered Y-DNA ancestor</div>'
  +(mf?`<div class="key-filter"><div><b>${fmt(mf.size)}</b> ${mf.size===1?'person matches':'people match'}</div>${gapOn.size>1?`<div class="key-seg"><button type="button" data-key-mode="any" class="${markMode==='any'?'active':''}">Any mark</button><button type="button" data-key-mode="all" class="${markMode==='all'?'active':''}">All marks</button></div>`:''}<button type="button" class="key-link" data-key-clear="1">Clear marks and show everyone</button></div>`:'<p class="key-note key-hint">Tick a mark to show only the people it applies to.</p>')
  +`<div class="key-head">Research status${RS?.failed?' · not available here':RS?' · '+esc(fmtDay(RS.generated)):''}</div>`+rows('status')
  +'<div class="key-head">Record gaps</div>'+rows('gaps')
  +'<div class="key-head">Y-DNA</div>'+rows('ydna')+'<button type="button" class="key-link" data-action="ydna-list">List male lines with no result…</button>'
  +'<div class="key-head">Connecting families</div>'+(HUNT.size?rows('hunt'):'')+'<button type="button" class="key-link" data-action="hunt">Find families to connect…</button>'
  +'<div class="key-foot"><button type="button" class="key-link" data-action="key-csv">Download marked people (CSV)</button><p class="key-note">Marks show where the record is thin or work is waiting. A missing record does not prove there was no child, spouse or father.</p></div>'}
'''

TREE_JS = r'''
/* One family tree (hourglass, as in Tree Prism): ancestors above, the person with partners and
   siblings across the middle, descendants below; one shaded band per generation. Horizontal puts
   ancestors to the right and descendants to the left, as FamilySearch's landscape tree does.
   Replaces the separate descendants / ancestors / close-family lenses. Generated by
   tools/atlas_whole_tree.py. Layout works in "across" (along a generation) and "row" (generation)
   and is mapped to x/y at the end. */
const TREE={cw:172,ch:70,limit:320,v:{across:172,couple:24,unit:30,pitch:176},h:{across:70,couple:8,unit:18,pitch:322}};
state.treeUp=4;state.treeDown=3;state.treeSibs=true;state.treeAuto=true;state.treeOrient='v';state.treeRoot=null;
state.treeOpen={up:new Set(),down:new Set()};state.treeShut={up:new Set(),down:new Set()};
try{const o=localStorage.getItem('glasgow-tree-orient');if(o==='h'||o==='v')state.treeOrient=o}catch{}
/* Until the reader picks a depth, open as many generations of descendants (up to 3) as keep each row to about a screen's width. */
function treeAutoDown(id){let gen=[id],g=0;const seen=new Set([id]);while(g<3){const next=[];for(const p of gen)for(const c of FAMILY.children.get(p)||[])if(!seen.has(c)){seen.add(c);next.push(c)}if(!next.length||(g>0&&next.length*1.6>18))break;gen=next;g++}return Math.max(1,g)}
const TREE_TIER={uncertain:0,possible:0,probable:1,strongly_supported:1,unmarked:2,confident:2,proved:3,'DNA-confirmed':3,dna_confirmed:3};
const TREE_LABEL={uncertain:'Uncertain',possible:'Possible',probable:'Probable',strongly_supported:'Strongly supported',proved:'Proved','DNA-confirmed':'DNA-confirmed',dna_confirmed:'DNA-confirmed'};
function treeTier(r){const t=TREE_TIER[String(r?.status||'unmarked')];return t===undefined?2:t}
function treePill(r,prefix){const st=String(r?.status||'');if(!TREE_LABEL[st])return null;const v=r.probability&&typeof r.probability.value==='number'?' · '+Math.round(r.probability.value*100)+'%':'';const tier=treeTier(r);return {text:(prefix?prefix+': ':'')+(r.assessmentLabel||TREE_LABEL[st])+v,tone:tier===0?'weak':tier===3?'strong':'mid'}}
function makeTree(id){
 uiBoxes=null;
 if(state.treeRoot!==id){state.treeRoot=id;for(const k of ['up','down']){state.treeOpen[k].clear();state.treeShut[k].clear()}}
 if(state.treeAuto)state.treeDown=treeAutoDown(id);
 const T=TREE,O=state.treeOrient,G=T[O],CA=G.across,cw=T.cw,ch=T.ch,map=new Map(),nodes=[],edges=[],rows=new Map(),pills=[],units=new Map();let truncated=false;
 const openD=(pid,deflt)=>!state.treeShut.down.has(pid)&&(deflt||state.treeOpen.down.has(pid)),openU=(pid,deflt)=>!state.treeShut.up.has(pid)&&(deflt||state.treeOpen.up.has(pid));
 const yearOf=pid=>yearNum(P.get(pid))||9999,byYear=(a,b)=>yearOf(a)-yearOf(b)||a.localeCompare(b);
 const room=()=>{if(nodes.length>=T.limit){truncated=true;return false}return true};
 const add=(pid,row)=>{if(map.has(pid))return map.get(pid);const p=P.get(pid),n={id:pid,type:'person',name:p.name,geo:place(p).home,colour:countryColour(p),children:[],depth:row,row,x:0,y:0,a:0,count:stats.get(pid).size,isRoot:pid===id,attachment:stats.get(pid).attachment,hidden:0,hiddenUp:0,kidsShown:0,parentsShown:0};nodes.push(n);map.set(pid,n);if(!rows.has(row))rows.set(row,[]);rows.get(row).push(n);return n};
 const pairKey=(a,b)=>[a,b].sort().join('|');
 // Descendants: a unit is a person with their partners; children sit under the couple.
 function unit(pid,row,open,withPartners){
  add(pid,row);const u={id:pid,row,partners:[],kids:[],w:0,kw:0};units.set(pid,u);
  const kidsAll=FAMILY.children.get(pid)||[],partners=withPartners||open?[...(FAMILY.partners.get(pid)||[])]:[];
  if(open)for(const c of kidsAll)for(const r of FAMILY.parents.get(c))if(r.id!==pid&&!partners.includes(r.id))partners.push(r.id);
  for(const q of partners){if(map.has(q)||!P.has(q))continue;if(!room())break;const m=add(q,row);m.familyRole=FAMILY.pairs.has(pairKey(pid,q))?'Partner':'Co-parent';m.peerOf=pid;u.partners.push(q)}
  if(open){const other=c=>FAMILY.parents.get(c).find(r=>r.id!==pid)?.id,slot=c=>{const i=u.partners.indexOf(other(c));return i<0?99:i};
   for(const c of kidsAll.filter(c=>!map.has(c)).sort((a,b)=>slot(a)-slot(b)||byYear(a,b))){if(map.has(c))continue;if(!room())break;u.kids.push(unit(c,row+1,openD(c,row+1<state.treeDown),true))}}
  const n=map.get(pid);n.owner=true;n.kidsShown=u.kids.length;return u;
 }
 const unitW=u=>(1+u.partners.length)*CA+u.partners.length*G.couple;
 // Compact tidy layout: each family is pushed against its neighbours generation by generation.
 function lay(u){const half=unitW(u)/2,L=[-half],R=[half];u.koff=[];
  if(u.kids.length){let aL=null,aR=null;const offs=[];
   for(const k of u.kids){lay(k);let off=0;if(aR){off=-Infinity;for(let d=0;d<Math.min(aR.length,k.L.length);d++)off=Math.max(off,aR[d]-k.L[d]+G.unit)}offs.push(off);
    if(!aR){aL=k.L.slice();aR=k.R.slice()}else for(let d=0;d<k.L.length;d++){if(d<aR.length){aR[d]=Math.max(aR[d],k.R[d]+off);aL[d]=Math.min(aL[d],k.L[d]+off)}else{aL[d]=k.L[d]+off;aR[d]=k.R[d]+off}}}
   const shift=-(offs[0]+offs.at(-1))/2;u.koff=offs.map(o=>o+shift);for(let d=0;d<aL.length;d++){L[d+1]=aL[d]+shift;R[d+1]=aR[d]+shift}}
  u.L=L;u.R=R;return u}
 function placeUnit(u,cx){let a=cx-unitW(u)/2;for(const pid of [u.id,...u.partners]){map.get(pid).a=a;a+=CA+G.couple}u.kids.forEach((k,i)=>placeUnit(k,cx+u.koff[i]))}
 const rootParents=(FAMILY.parents.get(id)||[]).slice().sort((a,b)=>(a.role==='father'?0:1)-(b.role==='father'?0:1));
 const rootUnit=unit(id,0,openD(id,state.treeDown>0),true),older=[],younger=[];
 if(state.treeSibs){const set=new Set();for(const r of rootParents)for(const c of FAMILY.children.get(r.id)||[])if(c!==id)set.add(c);
  for(const s of [...set].sort(byYear)){if(map.has(s))continue;if(!room())break;(byYear(s,id)<0?older:younger).push(unit(s,0,openD(s,false),openD(s,false)))}}
 lay(rootUnit);placeUnit(rootUnit,0);
 // Siblings stand beside the person; an unfolded sibling's family is packed alongside.
 const aL=rootUnit.L.slice(),aR=rootUnit.R.slice();
 for(const s of younger){lay(s);let off=-Infinity;for(let d=0;d<Math.min(aR.length,s.L.length);d++)off=Math.max(off,aR[d]-s.L[d]+G.unit);placeUnit(s,off);for(let d=0;d<s.L.length;d++){aR[d]=d<aR.length?Math.max(aR[d],s.R[d]+off):s.R[d]+off;if(d>=aL.length)aL[d]=s.L[d]+off}}
 for(const s of older.slice().reverse()){lay(s);let off=Infinity;for(let d=0;d<Math.min(aL.length,s.R.length);d++)off=Math.min(off,aL[d]-s.R[d]-G.unit);placeUnit(s,off);for(let d=0;d<s.L.length;d++){aL[d]=d<aL.length?Math.min(aL[d],s.L[d]+off):s.L[d]+off;if(d>=aR.length)aR[d]=s.R[d]+off}}
 // Ancestors: each parent is centred over their own ancestors; a couple's line meets above the child.
 const anc=new Map();
 function ancBuild(pid,row){const a={id:pid,parents:[],w:CA};anc.set(pid,a);const gen=-row;
  if(openU(pid,gen<state.treeUp))for(const r of (FAMILY.parents.get(pid)||[]).slice().sort((x,y)=>(x.role==='father'?0:1)-(y.role==='father'?0:1))){if(map.has(r.id)||!P.has(r.id))continue;if(!room())break;add(r.id,row-1);a.parents.push(ancBuild(r.id,row-1))}
  map.get(pid).parentsShown=a.parents.length;return a}
 const top=[];if(openU(id,state.treeUp>0))for(const r of rootParents){if(map.has(r.id)||!P.has(r.id))continue;if(!room())break;add(r.id,-1);top.push(ancBuild(r.id,-1))}
 function ancMeasure(a){const pw=a.parents.reduce((s,p)=>s+ancMeasure(p),0)+Math.max(0,a.parents.length-1)*G.unit;a.w=Math.max(CA,pw);a.pw=pw;return a.w}
 function ancPlace(a,cx){map.get(a.id).a=cx-CA/2;let px=cx-a.pw/2;for(const p of a.parents){ancPlace(p,px+p.w/2);px+=p.w+G.unit}}
 map.get(id).parentsShown=top.length;
 if(top.length){const me=map.get(id),cx0=me.a+CA/2,tw=top.reduce((s,a)=>s+ancMeasure(a),0)+Math.max(0,top.length-1)*G.unit;
  let px=cx0-tw/2;for(const a of top){ancPlace(a,px+a.w/2);px+=a.w+G.unit}}
 for(const n of nodes){if(O==='v'){n.x=n.a;n.y=n.row*G.pitch}else{n.x=-n.row*G.pitch;n.y=n.a}}
 // What is folded away, for the round fold buttons.
 for(const n of nodes){if(units.has(n.id))n.hidden=(FAMILY.children.get(n.id)||[]).filter(c=>!map.has(c)).length;
  if(n.row<0||n.id===id)n.hiddenUp=(FAMILY.parents.get(n.id)||[]).filter(r=>P.has(r.id)&&!map.has(r.id)).length}
 // Parent-to-child links leave from the middle of the parents' partner line.
 const between=(A,B)=>{const lo=Math.min(A.a,B.a),hi=Math.max(A.a,B.a);return (rows.get(A.row)||[]).some(n=>n!==A&&n!==B&&n.a>lo&&n.a<hi)};
 function origin(rr){let ps=rr.map(r=>map.get(r.id));if(ps.length>1&&between(ps[0],ps[1]))ps=[ps[0].a>ps[1].a?ps[0]:ps[1]];
  if(ps.length>1){const [A,B]=ps[0].a<ps[1].a?ps:[ps[1],ps[0]];return O==='v'?{x:(A.x+cw+B.x)/2,y:A.y+ch/2}:{x:A.x+16,y:(A.y+ch+B.y)/2}}
  const p=ps[0];return O==='v'?{x:p.x+cw/2,y:p.y+ch}:{x:p.x,y:p.y+ch/2}}
 for(const c of nodes){const rr=FAMILY.parents.get(c.id).filter(r=>map.has(r.id)&&map.get(r.id).row===c.row-1);if(!rr.length)continue;
  const weakest=rr.slice().sort((a,b)=>treeTier(a)-treeTier(b))[0],o=origin(rr);let pts,pill;
  if(O==='v'){const cx=c.x+cw/2,cy=c.y,bus=cy-(G.pitch-ch)/2;pts=[o.x,o.y,o.x,bus,cx,bus,cx,cy];pill={x:cx,y:cy-22,align:'r'}}
  else{const cx=c.x+cw,cy=c.y+ch/2,bus=cx+(G.pitch-cw)/2;pts=[o.x,o.y,bus,o.y,bus,cy,cx,cy];pill={x:cx,y:cy,align:'l'}}
  for(const r of rr)edges.push({a:r.id,b:c.id,geo:c.geo,colour:c.colour,type:'recorded',orient:O,status:treeTier(r)===0?'uncertain':r.status,realStatus:r.status,role:r.role,contextOnly:r!==weakest,points:pts});
  const differ=rr.length>1&&treeTier(rr[0])!==treeTier(rr[1]),pp=treePill(weakest,differ?(weakest.role==='father'?'Father':weakest.role==='mother'?'Mother':'Parent'):'');if(pp)pills.push({...pill,...pp})}
 // Partner lines; they arc round any card standing between the two partners.
 const linked=new Set();
 function partner(a,b,type){const k=pairKey(a,b);if(linked.has(k))return;const A0=map.get(a),B0=map.get(b);if(!A0||!B0||A0.row!==B0.row)return;linked.add(k);const [A,B]=A0.a<B0.a?[A0,B0]:[B0,A0],gap=between(A,B);let pts;
  if(O==='v')pts=gap?[A.x+cw-20,A.y,A.x+cw-20,A.y-44,B.x+20,B.y-44,B.x+20,B.y]:[A.x+cw,A.y+ch/2,A.x+cw+(B.x-A.x-cw)/3,A.y+ch/2,A.x+cw+(B.x-A.x-cw)*2/3,B.y+ch/2,B.x,B.y+ch/2];
  else pts=gap?[A.x+cw,A.y+ch-12,A.x+cw+38,A.y+ch-12,B.x+cw+38,B.y+12,B.x+cw,B.y+12]:[A.x+16,A.y+ch,A.x+16,A.y+ch+(B.y-A.y-ch)/3,A.x+16,A.y+ch+(B.y-A.y-ch)*2/3,B.x+16,B.y];
  edges.push({a:A.id,b:B.id,geo:B.geo,colour:B.colour,type,status:null,role:type==='partner'?'spouse':'co-parent',points:pts})}
 for(const p of FAMILY.pairs.values())partner(p.a,p.b,'partner');
 for(const p of FAMILY.coPairs.values())if(p.children.some(c=>map.has(c)))partner(p.a,p.b,'coparent');
 const result={id:++sceneSerial,type:'family',tree:true,orient:O,G,rows:[...rows.keys()].sort((a,b)=>a-b),rowNodes:rows,pills,nodes,map,edges,root:id,bounds:boundsOf(nodes.flatMap(n=>[{x:n.x-46,y:n.y-46},{x:n.x+cw+46,y:n.y+ch+46}]),10),groups:[],truncated};
 prepareScene(result);treeChunks(result);return result;
}
/* Square links, as a printed family tree draws them: out from the parents, along a bar, in to the child. */
function treeElbow(e){const [ox,oy,bx,by,,,cx,cy]=e.points,path=new Path2D();path.moveTo(ox,oy);
 if(e.orient==='h'){if(Math.abs(cy-oy)<1){path.lineTo(cx,cy);return path}const r=Math.min(10,Math.abs(cy-oy)/2,Math.abs(ox-bx)),dy=cy>oy?1:-1,dx=bx<ox?-1:1;
  path.lineTo(bx-dx*r,oy);path.arcTo(bx,oy,bx,oy+dy*r,r);path.lineTo(bx,cy-dy*r);path.arcTo(bx,cy,bx+(cx<bx?-1:1)*r,cy,r);path.lineTo(cx,cy);return path}
 if(Math.abs(cx-ox)<1){path.lineTo(cx,cy);return path}const r=Math.min(10,Math.abs(cx-ox)/2,Math.abs(by-oy)),dir=cx>ox?1:-1;
 path.lineTo(ox,by-r);path.arcTo(ox,by,ox+dir*r,by,r);path.lineTo(cx-dir*r,by);path.arcTo(cx,by,cx,by+r,r);path.lineTo(cx,cy);return path}
function treeChunks(s){for(const e of s.edges)if(e.type==='recorded')e.path=treeElbow(e);
 for(const mode of ['first','journeys']){const chunks=new Map();for(const e of s.edges){if(e.contextOnly)continue;const key=[e.colour,e.type,e.status==='uncertain'?'u':''].join('|');
  if(!chunks.has(key))chunks.set(key,{path:new Path2D(),geo:e.geo,type:e.type,colour:e.colour,uncertain:e.status==='uncertain',pts:[]});const ch=chunks.get(key);ch.path.addPath(e.path);ch.pts.push({x:e.box.x,y:e.box.y},{x:e.box.x+e.box.w,y:e.box.y+e.box.h})}
  s.chunkModes[mode]=[...chunks.values()].map(ch=>{ch.box=boundsOf(ch.pts,4);delete ch.pts;return ch})}
 s.chunks=s.chunkModes[state.colourMode]}
function treeRowLabel(r,s,short){const n=Math.abs(r),up=['THIS GENERATION','PARENTS','GRANDPARENTS','GREAT-GRANDPARENTS'],down=['THIS GENERATION','CHILDREN','GRANDCHILDREN','GREAT-GRANDCHILDREN'];
 let t=r<0?(n<4?up[n]:(n-2)+'× GREAT-GRANDPARENTS'):(n<4?down[n]:(n-2)+'× GREAT-GRANDCHILDREN');const ys=(s.rowNodes.get(r)||[]).map(x=>yearNum(P.get(x.id))).filter(Boolean);
 if(ys.length){const a=Math.min(...ys),b=Math.max(...ys);t+=(short?' · ':' · BORN ')+(a===b?a:a+'–'+b)}return t}
function drawTreeBands(){const s=scene,T=TREE,G=s.G,b=s.bounds,h=s.orient==='h';ctx.beginPath();
 for(const r of s.rows){ctx.fillStyle=r===0?'#eef2e4':(Math.abs(r)%2?'#f5f2e7':'#fbf9f2');
  if(h){const x=-r*G.pitch-(G.pitch-T.cw)/2;ctx.fillRect(x,b.y-6000,G.pitch,b.h+12000);ctx.moveTo(x,b.y-6000);ctx.lineTo(x,b.y+b.h+6000)}
  else{const y=r*G.pitch-(G.pitch-T.ch)/2;ctx.fillRect(b.x-6000,y,b.w+12000,G.pitch);ctx.moveTo(b.x-6000,y);ctx.lineTo(b.x+b.w+6000,y)}}
 ctx.strokeStyle='#e2dccb';ctx.lineWidth=1/cam.k;ctx.stroke()}
function drawTreeLabels(){const s=scene,T=TREE,G=s.G,h=s.orient==='h';
 if(cam.k>=.4)for(const p of s.pills){const q=screen(p);if(q.x<-120||q.x>W+120||q.y<40||q.y>H)continue;ctx.font='600 '+clamp(10*cam.k,9,11)+'px '+SANS;const tw=ctx.measureText(p.text).width+14,hh=17,col=p.tone==='weak'?['#fbeee8','#cf9a87','#8a3f28']:p.tone==='strong'?['#e9f3e6','#9cbd8e','#2f5e2f']:['#fbf3df','#d7bd7c','#71530f'];
  const x0=p.align==='c'?q.x-tw/2:q.x+6,y0=p.align==='l'?q.y-hh-3:q.y-hh/2;
  ctx.fillStyle=col[0];ctx.strokeStyle=col[1];ctx.lineWidth=.8;roundRect(x0,y0,tw,hh,8);ctx.fill();ctx.stroke();ctx.fillStyle=col[2];ctx.textAlign='center';ctx.fillText(p.text,x0+tw/2,y0+hh/2+3.6);ctx.textAlign='left'}
 ctx.font='600 10px '+SANS;
 for(const r of s.rows){const txt0=treeRowLabel(r,s,h);
  if(h){const x=(-r*G.pitch-(G.pitch-T.cw)/2)*cam.k+cam.x,w=G.pitch*cam.k;if(x+w<0||x>W)continue;const txt=trimText(txt0,w-20),tw=ctx.measureText(txt).width,lx=clamp(x+w/2-tw/2,x+6,x+w-tw-6),yy=158;
   ctx.fillStyle='rgba(252,251,246,.86)';roundRect(lx-6,yy-11,tw+12,16,4);ctx.fill();ctx.fillStyle=r===0?'#4f6d43':'#7d8a6f';ctx.fillText(txt,lx,yy)}
  else{const y=(r*G.pitch-(G.pitch-T.ch)/2)*cam.k+cam.y,hh=G.pitch*cam.k;if(y+hh<70||y>H-60)continue;const yy=clamp(y+15,72,y+hh-6),tw=ctx.measureText(txt0).width;
   ctx.fillStyle='rgba(252,251,246,.86)';roundRect(10,yy-11,tw+12,16,4);ctx.fill();ctx.fillStyle=r===0?'#4f6d43':'#7d8a6f';ctx.fillText(txt0,16,yy)}}}
/* Round fold buttons beside a card, as FamilySearch draws them: the chevron points the way the
   tree will grow. Once a line is open, a turned-round button that folds it away again appears
   while the card is hovered. */
function treeButtons(n,box){const s=scene,h=s.orient==='h',r=clamp(11*Math.sqrt(cam.k/.62),8,13),list=[];
 if(n.owner){if(n.kidsShown)list.push({dir:'down',act:'close',label:'Hide children'});else if(n.hidden)list.push({dir:'down',act:'open',label:'Show '+n.hidden+(n.hidden===1?' child':' children')})}
 if(n.row<0||n.isRoot){if(n.parentsShown)list.push({dir:'up',act:'close',label:'Hide parents'});else if(n.hiddenUp)list.push({dir:'up',act:'open',label:n.hiddenUp===1?'Show parent':'Show parents'})}
 for(const b of list){const down=b.dir==='down',open=b.act==='open';let cx,cy,vx,vy;
  if(h){cx=down?box.x-r-3:box.x+box.w+r+3;cy=open?box.y+box.h/2:box.y+box.h-r-3;vx=down?-1:1;vy=0}
  else{cx=open?box.x+box.w/2:down?box.x+box.w-r-6:box.x+r+4;cy=down?box.y+box.h+r+3:box.y-r-3;vx=0;vy=down?1:-1}
  if(!open){vx=-vx;vy=-vy;const hv=hover==='card:'+n.id||hover==='expand:'+n.id;if(!hv){addHit(n.id,'expand',{x:cx-r-3,y:cy-r-3,w:2*r+6,h:2*r+6},b);continue}}
  ctx.save();ctx.shadowColor='rgba(40,52,40,.22)';ctx.shadowBlur=4;ctx.shadowOffsetY=1;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fillStyle='#ffffff';ctx.fill();ctx.restore();
  ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.strokeStyle=open?'#b9c8b3':'#d3dacf';ctx.lineWidth=1;ctx.stroke();
  const sz=r*.42,px=-vy,py=vx;ctx.beginPath();ctx.moveTo(cx-vx*sz*.45+px*sz,cy-vy*sz*.45+py*sz);ctx.lineTo(cx+vx*sz*.55,cy+vy*sz*.55);ctx.lineTo(cx-vx*sz*.45-px*sz,cy-vy*sz*.45-py*sz);
  ctx.strokeStyle=open?'#315a43':'#8d9c88';ctx.lineWidth=1.8;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke();ctx.lineCap='butt';ctx.lineJoin='miter';
  addHit(n.id,'expand',{x:cx-r-3,y:cy-r-3,w:2*r+6,h:2*r+6},b)}}
function treeToggle(id,dir,act){const open=state.treeOpen[dir],shut=state.treeShut[dir];if(act==='open'){shut.delete(id);open.add(id)}else{open.delete(id);shut.add(id)}treeRebuild(id)}
function treeStart(n){const s=scene,T=TREE,id=n.id,top=205,bottom=80,aw=W-60,ah=H-top-bottom,all=s.bounds,fitAll=Math.min(aw/all.w,ah/all.h);let b=all,k=fitAll;
 if(fitAll<.62){const near=[id,...(FAMILY.parents.get(id)||[]).map(r=>r.id),...(FAMILY.children.get(id)||[]),...(FAMILY.partners.get(id)||[])].filter(x=>s.map.has(x));b=boundsOf(near.flatMap(x=>{const m=s.map.get(x);return [{x:m.x,y:m.y-30},{x:m.x+T.cw,y:m.y+T.ch}]}),30);k=clamp(Math.min(aw/b.w,ah/b.h),.62,.9)}else k=Math.min(.95,fitAll);
 const v=all.h*k<=ah?all:b;setCam({k,x:W/2-(b.x+b.w/2)*k,y:top+ah/2-(v.y+v.h/2)*k})}
function treeUI(){const host=$('#family-lens');if(!host)return;
 if(!document.getElementById('tree-lens-css')){const st=document.createElement('style');st.id='tree-lens-css';st.textContent='#family-lens.tree-lens{display:inline-flex;flex-wrap:wrap;align-items:center;gap:6px 14px;padding:4px 10px}#family-lens.tree-lens .tl-group{display:inline-flex;align-items:center;gap:4px;font-size:12px;color:#55684c}#family-lens.tree-lens .tl-name{margin-right:2px}#family-lens.tree-lens .tl-group button{min-width:26px;padding:2px 0;font-size:14px;line-height:18px}#family-lens.tree-lens b{min-width:14px;text-align:center;font-variant-numeric:tabular-nums;color:#2f4b2f}#family-lens.tree-lens .tl-sibs[aria-pressed="false"]{opacity:.65}#family-lens.tree-lens .tl-orient{gap:0}#family-lens.tree-lens .tl-orient button{min-width:0;padding:2px 9px;font-size:12px;border-radius:0}#family-lens.tree-lens .tl-orient button:first-child{border-radius:6px 0 0 6px}#family-lens.tree-lens .tl-orient button:last-child{border-radius:0 6px 6px 0}';document.head.append(st)}
 if(!host.dataset.tree){host.dataset.tree='1';host.classList.add('tree-lens');host.setAttribute('aria-label','Generations shown');
  host.innerHTML='<span class="tl-group" title="Generations of ancestors"><span class="tl-name">Ancestors</span><button data-tree="up" data-d="-1" aria-label="Show one fewer generation of ancestors">−</button><b id="tl-up"></b><button data-tree="up" data-d="1" aria-label="Show one more generation of ancestors">+</button></span><span class="tl-group" title="Generations of descendants"><span class="tl-name">Descendants</span><button data-tree="down" data-d="-1" aria-label="Show one fewer generation of descendants">−</button><b id="tl-down"></b><button data-tree="down" data-d="1" aria-label="Show one more generation of descendants">+</button></span><button data-tree="sibs" class="tl-sibs">Siblings</button><span class="tl-group tl-orient" role="group" aria-label="Tree direction"><button data-tree="orient" data-o="v" title="Ancestors above, descendants below">↕ Vertical</button><button data-tree="orient" data-o="h" title="Ancestors to the right, descendants to the left">↔ Horizontal</button></span>';
  host.addEventListener('click',e=>{const b=e.target.closest('[data-tree]');if(!b)return;e.stopPropagation();const k=b.dataset.tree;if(k==='orient'){if(state.treeOrient===b.dataset.o)return;state.treeOrient=b.dataset.o;try{localStorage.setItem('glasgow-tree-orient',state.treeOrient)}catch{}treeRebuild(null,true);return}if(k==='sibs')state.treeSibs=!state.treeSibs;else{const key=k==='up'?'treeUp':'treeDown';if(key==='treeDown')state.treeAuto=false;state[key]=clamp(state[key]+Number(b.dataset.d),0,12)}treeRebuild()})}
 $('#tl-up').textContent=state.treeUp;$('#tl-down').textContent=state.treeDown;const sb=host.querySelector('.tl-sibs');sb.setAttribute('aria-pressed',String(state.treeSibs));sb.classList.toggle('active',state.treeSibs);for(const o of host.querySelectorAll('[data-tree=orient]')){const on=o.dataset.o===state.treeOrient;o.classList.toggle('active',on);o.setAttribute('aria-pressed',String(on))}}
function treeRebuild(anchor,refit){if(state.view!=='family'||!state.familyRoot)return;const id=anchor&&scene.map.has(anchor)?anchor:state.familyRoot,n=scene.map.get(id),pos=n?screen(n):null;scene=makeFamily(state.familyRoot,'tree');if(refit){const r=scene.map.get(state.familyRoot);if(r)treeStart(r)}else if(pos&&scene.map.has(id)){const now=scene.map.get(id);cam.x=pos.x-now.x*cam.k;cam.y=pos.y-now.y*cam.k}syncUI();updateSelection();invalidate();if(scene.truncated)toast('A very large family: showing the first '+TREE.limit+' people. Show fewer generations, or open a child’s tree.')}
'''


PATCHES = [
    # 1. Layout CSS, injected once at start-up.
    ("(() => {\nconst D=window.GlasgowAtlasModel;",
     "(() => {\n" + STYLE_JS + "const D=window.GlasgowAtlasModel;"),
    # 2. Inset helper and early-core camera, defined beside fit().
    ("function fit(animate=true){",
     INSETS_JS + "function fit(animate=true){"),
    ("const b=scene.bounds,top=state.view==='family'?205:154,bottom=75,",
     "const b=scene.bounds,ins=scene.type==='all'?canopyInsets():{top:state.view==='family'?205:154,bottom:75},top=ins.top,bottom=ins.bottom,"),
    ("const b=atlas.coreBounds,top=W<760?220:180,bottom=70,k=Math.min((W-70)/b.w,(H-top-bottom)/b.h,1.1);setCam({k,x:W/2,y:top+(H-top-bottom)/2});",
     "earlyCam();"),
    ("const b=w.bounds,top=154,bottom=75,side=W<540?28:90,k=Math.min(fitScale*14,(W-side*2)/b.w,(H-top-bottom)/b.h);",
     "const b=w.bounds,{top,bottom}=canopyInsets(),side=W<540?28:90,k=Math.max(fitScale,Math.min(fitScale*14,(W-side*2)/b.w,Math.max(120,H-top-bottom)/b.h));"),
    ("b=boundsOf(pts,30),top=154,bottom=75,k=Math.min(fitScale*40,(W-180)/b.w,(H-top-bottom)/b.h);",
     "b=boundsOf(pts,30),{top,bottom}=canopyInsets(),k=Math.min(fitScale*40,(W-180)/b.w,Math.max(120,H-top-bottom)/b.h);"),
    # 3. Never accept a non-positive zoom; keep the early-core framing on resize.
    # The frame timestamp can precede ``start`` after a long task (start-up),
    # which made the eased progress hugely negative and the zoom negative.
    ("function step(t){const v=Math.min(1,(t-start)/280)", "function step(t){const v=clamp((t-start)/280,0,1)"),
    ("function setCam(to,animate=true){cancelAnimationFrame(anim);",
     "function setCam(to,animate=true){cancelAnimationFrame(anim);if(!(to.k>0))to={...to,k:Math.max(1e-3,fitScale||.05)};"),
    ("ctx.arc(c.x,c.y,s.coreR*k,0,TAU)", "ctx.arc(c.x,c.y,Math.max(0,s.coreR*k),0,TAU)"),
    ("fit(false);else if(state.view==='lanes'){",
     "fit(false);else if(state.early&&state.view==='all'&&!state.selected)earlyCam(false);else if(state.view==='lanes'){"),
    # 4. Gentler zoom when a person is selected or found by search.
    ("const kk=k||Math.max(cam.k,scene.type==='all'?.8:.95);",
     "const kk=k||Math.max(cam.k,scene.type==='all'?Math.min(.8,fitScale*4):.95);"),
    # 5. Labels avoid the pan controls.
    # Controls inside a closed menu still report a box in Chrome; they are not on screen.
    ("'.canvas-bottom','#minimap-wrap']){const el=$(sel);if(!el||!el.getClientRects().length)continue;",
     "'.canvas-bottom','#minimap-wrap','.v3-pan-controls','#canopy-key','#sun-tools']){const el=$(sel);if(!el||!el.getClientRects().length||el.closest('details:not([open])>:not(summary)'))continue;"),
    # 6. Century labels reserve their space before people are labelled.
    ("function drawCanopyRings(c,R){\n const s=scene,k=cam.k;ctx.save();",
     "let ringLabels=[];\nfunction drawRingLabels(guard){ctx.save();ctx.font='9px '+SANS;ctx.textAlign='center';"
     "for(const l of ringLabels){const tw=ctx.measureText(l.t).width+10,b={x:l.x-tw/2,y:l.y-8,w:tw,h:15};if(!guard.add(b))continue;"
     "ctx.fillStyle='#fcfbf6';roundRect(b.x,b.y,b.w,b.h,3);ctx.fill();ctx.fillStyle='#7f8a73';ctx.fillText(l.t,l.x,l.y+3)}"
     "ctx.textAlign='left';ctx.restore()}\n"
     "function drawCanopyRings(c,R){\n const s=scene,k=cam.k;ringLabels=[];ctx.save();"),
    ("if(x>10&&x<W-10&&yy>70&&yy<H-50){ctx.fillStyle='#fcfbf6';ctx.fillRect(x-15,yy-7,30,13);ctx.fillStyle='#7f8a73';ctx.fillText(String(y),x,yy+3)}",
     "if(x>10&&x<W-10&&yy>70&&yy<H-50)ringLabels.push({x,y:yy,t:atlasGenMode?'Gen '+y:String(y)})"),
    ("if(!focusSet)drawMigrationPoints(viewbox);\n const guard=guardUI();let visible=0;",
     "if(!focusSet&&!MF&&!state.grand&&!state.branch&&!state.evidence&&k/fitScale>=1.6)drawMigrationPoints(viewbox);drawGapMarks(viewbox);\n const guard=guardUI();drawRingLabels(guard);let visible=0;"),
    # 7. Shorten the family name, not its profile count.
    ("let text=w.kind==='locality'?w.name+' · '+fmt(w.count):w.name+(w.sub?' · '+w.sub:'')+' · '+fmt(w.count);",
     "const tail=' · '+fmt(w.count),head=w.kind==='locality'?w.name:w.name+(w.sub?' · '+w.sub:'');let text=head+tail;"),
    ("text=trimText(text,room);tw=ctx.measureText(text).width;",
     "text=trimText(head,Math.max(24,room-ctx.measureText(tail).width))+tail;tw=ctx.measureText(text).width;"),
    # 8. Status text says what the rim and the centre are.
    (":(state.maxYear>=YEAR_MAX?`${fmt(P.size)} records · ${fmt(s.wedges.filter(w=>w.kind!=='locality').length)} families around the rim`",
     ":MF?`${fmt(MF.size)} ${MF.size===1?'person matches':'people match'}: ${markSummary()}`"
     ":state.grand?`${fmt(v.persons.filter(n=>GRAND.has(n.id)).length)} grandparents · dot size shows recorded descendants`"
     ":state.early?`${fmt(EARLY.size)} profiles dated 1450–1600 at the centre · ${fmt(P.size)} in all`"
     ":(state.maxYear>=YEAR_MAX?`${fmt(P.size)} people · ${fmt(s.wedges.filter(w=>w.kind!=='locality').length)} named family branches around the edge`"),
    # 9. Grandparents filter (toggle beside the year slider; #filter=grandparents).
    ("function drawCanopy(){", GRAND_JS + FAMILY_AREAS_JS + EXTRAS_JS + SUN_JS + RESEARCH_JS + "function drawCanopy(){"),
    ("let state={view:'all',early:false,", "let state={view:'all',early:false,grand:false,branch:false,evidence:false,sun:null,"),
    ("function makeAtlas(){", GEN_JS + "function makeAtlas(){"),
    ("atlas=makeAtlas();lanes=makeLanes(state.laneSort);scene=atlas;syncUI();resize();fit(false);",
     GRAND_UI_JS + "atlas=makeAtlas();lanes=makeLanes(state.laneSort);scene=atlas;syncUI();resize();fit(false);"),
    ("const base=focusSet?.12:state.dnaFocus?.18:.88;", "const base=focusSet?.12:state.dnaFocus?.18:state.grand||MF?.13:.88;"),
    ("ctx.setLineDash([]);\n const dotR=clamp(k*.75+.8,1,2.6)/k",
     "ctx.setLineDash([]);\n if(state.grand&&!focusSet){for(const [key,path] of overlayPaths(GRAND.ids)){const [col,kind]=key.split('|');ctx.strokeStyle=col;"
     "ctx.globalAlpha=kind==='c'?.4:.85;ctx.lineWidth=1.25/k;ctx.setLineDash(kind==='p'?[2/k,3/k]:kind==='u'?[4/k,3/k]:kind==='c'?[1.5/k,3/k]:[]);ctx.stroke(path)}ctx.setLineDash([])}\n"
     " const dotR=clamp(k*.75+.8,1,2.6)/k"),
    ("for(const n of v.persons){if(!intersects({x:n.x,y:n.y,w:0,h:0},viewbox))continue;const key=n.colour;",
     "for(const n of (state.grand||MF?v.persons.filter(n=>(!state.grand||GRAND.has(n.id))&&(!MF||MF.has(n.id))):v.persons)){if(!intersects({x:n.x,y:n.y,w:0,h:0},viewbox))continue;const key=dotColour(n);"),
    ("const r=v.collapsedSet.has(n.id)?Math.max(dotR*1.8,3.2/k):n.early?Math.max(dotR,2/k):dotR;",
     "const r=state.grand?grandPx(n.id)/k:MF?Math.max(dotR*1.7,2.6/k):v.collapsedSet.has(n.id)?Math.max(dotR*1.8,3.2/k):n.early?Math.max(dotR,2/k):dotR;"),
    ("for(const [col,path] of dots){ctx.fillStyle=col;ctx.globalAlpha=focusSet?.18:state.dnaFocus?.25:.97;ctx.fill(path)}",
     "for(const [col,path] of dots){ctx.fillStyle=col;ctx.globalAlpha=focusSet?.18:state.dnaFocus?.25:state.grand?.78:.97;ctx.fill(path);"
     "if(state.grand&&!focusSet){ctx.globalAlpha=.9;ctx.strokeStyle='#fcfbf6';ctx.lineWidth=.9/k;ctx.stroke(path)}}"),
    ("for(const n of v.persons){if(!intersects({x:n.x,y:n.y,w:0,h:0},viewbox))continue;const p=screen(n);if(p.x<0||p.x>W||p.y<0||p.y>H)continue;visible++;addHit(n.id,'dot',{x:p.x-5,y:p.y-5,w:10,h:10,cx:p.x,cy:p.y})}",
     "for(const n of v.persons){if(state.grand&&!GRAND.has(n.id))continue;if(MF&&!MF.has(n.id))continue;if(!intersects({x:n.x,y:n.y,w:0,h:0},viewbox))continue;const p=screen(n);if(p.x<0||p.x>W||p.y<0||p.y>H)continue;visible++;"
     "const hr=state.grand?Math.max(5,grandPx(n.id)):5;addHit(n.id,'dot',{x:p.x-hr,y:p.y-hr,w:hr*2,h:hr*2,cx:p.x,cy:p.y})}"),
    ("drawPersonLabels(guard,z,true);drawPersonLabels(guard,z);",
     "if(state.grand)drawGrandLabels(guard,z);else{drawPersonLabels(guard,z,true);drawPersonLabels(guard,z)}"),
    (":'#view='+state.view+(state.early?'&era=early':'');",
     ":'#view='+state.view+(state.early?'&era=early':'')+(state.grand&&state.view==='all'&&!state.early?'&filter=grandparents':'')+(state.view==='all'&&!state.early&&(state.branch||state.evidence)?'&colour='+(state.evidence?'evidence':'branch'):'')+(state.sun&&state.view==='all'?'&sun='+encodeURIComponent(state.sun):'')+(atlasGenMode&&state.view==='all'?'&layout=gen':'');"),
    ("const geo=params.get('geo');if(geo&&geoMap.has(geo))highlightGeo(geo)}",
     "const geo=params.get('geo');if(geo&&geoMap.has(geo))highlightGeo(geo);if(params.get('filter')==='grandparents'&&state.view==='all')setGrand(true);if(['branch','evidence'].includes(params.get('colour'))&&state.view==='all')setLineColour(params.get('colour'));if(params.get('layout')==='gen'&&state.view==='all')setLayout('gen');const sunId=params.get('sun');if(sunId&&P.has(sunId)&&!id&&state.view==='all')enterSun(sunId)}"),
    # 10. Declutter the overview: pins only when zoomed or focused, stronger century rings,
    #     horizontal family labels with leader lines (radial names remain when zoomed in).
#     Y-DNA pins stay visible at every zoom.
    ("ctx.strokeStyle=y%100===0&&y!==1500?'#7d8a7026':'#7d8a7016';", "ctx.strokeStyle=y%100===0&&y!==1500?'#7d8a7046':'#7d8a7022';"),
    (" // Radial family names, largest first, spaced by angle.\n", RIM_LABELS_JS + " // Radial family names, largest first, spaced by angle.\n"),
    ("addHit(w.id,'wedge',{x:Math.min(px,ex)-3,y:Math.min(py,ey)-6,w:Math.abs(ex-px)+6,h:Math.abs(ey-py)+12},{wedge:w});\n }\n ctx.restore();",
     "addHit(w.id,'wedge',{x:Math.min(px,ex)-3,y:Math.min(py,ey)-6,w:Math.abs(ex-px)+6,h:Math.abs(ey-py)+12},{wedge:w});\n }}\n ctx.restore();"),
    # 11. Families first: tinted family sectors, hoverable and clickable anywhere inside.
    ("drawCanopyRings(c,R);drawSectors(c,focusSet);", "drawCanopyRings(c,R);drawFamilyAreas(c,R);drawSectors(c,focusSet);"),
    ("if(!best)return canopySectorAt(x,y);return best}", "if(!best)return canopySectorAt(x,y)||familyAreaHit(x,y);return best}"),
    # 12. The few overview labels use full names, not first names.
    ("full=state.selected===n.id||z>5||early&&z>2", "full=state.selected===n.id||z>5||early&&z>2||z<1.7"),
    # 13. Colour by family branch (lines, focus dots, tick band) and the key card.
    ("for(const e of scene.edges){if(e.type==='group'||!P.has(e.a)||!P.has(e.b)||!pred(e))continue;",
     "for(const e of scene.edges){if(e.type==='group'||!P.has(e.a)||!P.has(e.b)||!pred(e))continue;"
     "if(state.branch||state.evidence){add((state.evidence?evidenceColour(e):branchColour(e.b))+'|'+(e.type!=='recorded'?'p':e.contextOnly?'c':e.status==='uncertain'?'u':'r'),e.points);continue}"),
    ("ctx.globalAlpha=1;ctx.fillStyle=n.colour;ctx.beginPath();ctx.arc(n.x,n.y,r,0,TAU);ctx.fill()",
     "ctx.globalAlpha=1;ctx.fillStyle=dotColour(n);ctx.beginPath();ctx.arc(n.x,n.y,r,0,TAU);ctx.fill()"),
    ("ctx.strokeStyle=C[w.geo];ctx.lineWidth=on?9:5;", "ctx.strokeStyle=geoOrBranch(w);ctx.lineWidth=on?9:5;"),
    ("if(scene.type==='lanes'){drawLanes();drawMini();return}",
     "{const kk=$('#canopy-key');if(kk){kk.hidden=scene.type!=='all'||!!state.sun;if(!kk.hidden&&kk.dataset.open==='1'){const cr=canvas.getBoundingClientRect(),t=$('#canopy-tools'),tb=t&&!t.hidden?t.getBoundingClientRect().bottom:cr.top;kk.style.maxHeight=Math.max(140,cr.bottom-118-tb-12)+'px'}}}if(scene.type==='lanes'){drawLanes();drawMini();return}"),
    # 14. Family sun: drawing, hit-testing, entry and exit points.
    ("\n const t0=performance.now(),s=scene,k=cam.k;ctx.setTransform", "\n if(state.sun){drawSun();return}\n MF=markFilter();\n const t0=performance.now(),s=scene,k=cam.k;ctx.setTransform"),
    ("function hit(x,y){let best=null", "function hit(x,y){if(state.sun&&scene?.type==='all')return sunHit(x,y);let best=null"),
    ("if(!scene)return;if(scene.type==='lanes'){fitLanes(animate);return}", "if(!scene)return;if(state.sun&&scene.type==='all'){sunFit(animate);return}if(scene.type==='lanes'){fitLanes(animate);return}"),
    ("if(h.type==='sector'){hideTooltip();unfold(h.id);return}",
     "if(h.type==='sun'){const now=performance.now();if(lastClick&&lastClick.id===h.id&&now-lastClick.time<380){lastClick=null;clearTimeout(clickTimer);hideTooltip();enterSun(h.id);return}"
     "lastClick={id:h.id,time:now};clearTimeout(clickTimer);clickTimer=setTimeout(()=>openPerson(h.id,false),230);return}if(h.type==='sector'){hideTooltip();unfold(h.id);return}"),
    ("if(h.type==='sector'){const n=atlas.map.get(h.id),e=subtreeInfo(n)",
     "if(h.type==='sun'){const p=P.get(h.id),n=h.node;t.innerHTML=`${esc(p.name)}<small>${esc(life(p))} · generation ${n.gen}<br>${n.again?'Also descends through another line':fmt(n.size-1)+' descendants'}</small><small>Click for the profile · double-click to centre the sun here</small>`}"
     "else if(h.type==='sector'){const n=atlas.map.get(h.id),e=subtreeInfo(n)"),
    ("case 'clear-branch':clearBranch();fit();break;", "case 'sun':enterSun(id);break;case 'sun-exit':exitSun();break;case 'hunt':openHunt();break;case 'hunt-show':huntShow();break;case 'hunt-csv':huntCsv();break;case 'ydna-list':openYdna();break;case 'ydna-csv':ydnaCsv();break;case 'key-csv':exportMarked();break;case 'clear-branch':clearBranch();fit();break;"),
    ("function goView(view,historyEntry=true){if(historyEntry)pushView();state.early=false;", "function goView(view,historyEntry=true){if(historyEntry)pushView();state.early=false;state.sun=null;SUN=null;"),
    ("function focus(id,k){const n=scene.map.get(id);if(!n)return;", "function focus(id,k){if(state.sun)exitSun();const n=scene.map.get(id);if(!n)return;"),
    ("$$('[data-branch]').forEach(b=>b.classList.toggle('active',b.dataset.branch===state.familyRoot));\n}", "$$('[data-branch]').forEach(b=>b.classList.toggle('active',b.dataset.branch===state.familyRoot));sunSync();\n}"),
    ("<button data-action=\"family\" data-id=\"${esc(p.id)}\">Read this family ↗</button>`}else $('#selection-pill').hidden=true;",
     "<button data-action=\"family\" data-id=\"${esc(p.id)}\">Read this family ↗</button>${(FAMILY.children.get(p.id)||[]).length&&state.sun!==p.id?` <button data-action=\"sun\" data-id=\"${esc(p.id)}\">☀ Descendants sun</button>`:''}`}else $('#selection-pill').hidden=true;"),
    ("${fwb.founder?`<button data-action=\"family\" data-id=\"${esc(fwb.founder)}\">Open the family tree ↗</button> `:",
     "${fwb.founder?`<button data-action=\"sun\" data-id=\"${esc(fwb.founder)}\">☀ Family sun</button> `:''}${fwb.founder?`<button data-action=\"family\" data-id=\"${esc(fwb.founder)}\">Open the family tree ↗</button> `:"),
    # 15. Generation layout: radii, core, rings, year front and early plaque.
    ("let r=y?eraRadius(y):1740+(hash(id)%85);const pa=map.get(parent);\n  if(pa?.type==='person'&&st.attachment?.type==='recorded')r=Math.max(r,pa.r+(EARLY.has(id)?22:29));",
     "let r=y?eraRadius(y):1740+(hash(id)%85);const pa=map.get(parent);\n  if(pa?.type==='person'&&st.attachment?.type==='recorded')r=Math.max(r,pa.r+(EARLY.has(id)?22:29));"
     "if(atlasGenMode)r=pa?.type==='person'?(st.attachment?.type==='recorded'?pa.r+GEN_STEP:pa.r):GEN_R0;"),
    ("const earlyNodes=nodes.filter(n=>n.early),coreR=Math.max(560,...earlyNodes.map(n=>n.r+24));",
     "const earlyNodes=nodes.filter(n=>n.early),coreR=atlasGenMode?GEN_R0-70:Math.max(560,...earlyNodes.map(n=>n.r+24));"),
    ("for(const y of [1500,1600,1700,1800,1900,2000]){const r=s.eraRadius(y)*k;",
     "for(const y of (atlasGenMode?[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]:[1500,1600,1700,1800,1900,2000])){const r=(atlasGenMode?GEN_R0+(y-1)*GEN_STEP:s.eraRadius(y))*k;"),
    ("const z=k/fitScale;drawCoreLabel(guard,z);", "const z=k/fitScale;if(!atlasGenMode)drawCoreLabel(guard,z);"),
    ("function drawYearFront(c){const cut=state.maxYear;if(cut>=YEAR_MAX)return;", "function drawYearFront(c){const cut=state.maxYear;if(cut>=YEAR_MAX||atlasGenMode)return;"),
    # 16. Research layer: evidence-graded lines (drawing order and width) and status in tooltips.
    ("return [...byColour];", "return state.evidence?[...byColour].sort((a,b)=>evRank(a[0])-evRank(b[0])):[...byColour];"),
    ("ctx.strokeStyle=col;ctx.globalAlpha=base*(kind==='p'?.7:1);ctx.lineWidth=1.05/k;",
     "ctx.strokeStyle=col;ctx.globalAlpha=base*(kind==='p'?.7:1);ctx.lineWidth=(state.evidence?evWidth(col):1.05)/k;"),
    ("<small>${h.type==='expand'?'Unfold more generations':'Click for the profile · double-click for the family'}</small>",
     "${rsLine(p.id)}<small>${h.type==='expand'?esc(h.label||'Unfold more generations'):'Click for the profile · double-click for the family'}</small>"),
    # 17. Marks filter: labels, importance and Y-DNA pins follow the ticked marks.
    ("for(const n of prioritised){if(!n||!isMatch(n))continue;", "for(const n of prioritised){if(!n||!isMatch(n)||(MF&&scene.type==='all'&&!MF.has(n.id)))continue;"),
    ("important=early||pin||n.id===state.selected;", "important=early||pin||n.id===state.selected||!!(MF&&MF.size<=400);"),
    ("if(!n||!v.visible.has(n.id)||!isMatch(n)||(focusSet&&!focusSet.has(n.id)))continue;const o=screen(n);",
     "if(!n||!v.visible.has(n.id)||!isMatch(n)||(focusSet&&!focusSet.has(n.id))||(MF&&!MF.has(n.id)))continue;const o=screen(n);"),
    # 18. Family sun from the profile panel.
    ("${icon('tree')}Read the family</button></section>`;",
     "${icon('tree')}Read the family</button>${(FAMILY.children.get(p.id)||[]).length?` <button class=\"tool-btn\" data-action=\"sun\" data-id=\"${esc(p.id)}\">☀ Descendants as a family sun</button>`:''}</section>`;"),
    # 19. Profile links (#person=ID&view=family&lens=ancestors|close, &view=lanes) open the asked-for view.
    ("if(id&&P.has(id)){if(v==='family')goFamily(id);else openPerson(id,true)}",
     "if(id&&P.has(id)){const lens=params.get('lens');if(v==='family')goFamily(id,['ancestors','close'].includes(lens)?lens:'descendants');"
     "else if(v==='lanes'||v==='all'){if(state.view!==v)goView(v,false);openPerson(id,true)}else openPerson(id,true)}"),
    # 20. One family tree (hourglass) in place of the descendants / ancestors / close-family lenses.
    ("function makeFamily(id,lens='descendants'){", TREE_JS + "function makeFamily(id,lens='descendants'){if(TREE)return makeTree(id);"),
    ("state.lens=lens;", "state.lens='tree';"),
    ("$('#canvas-sub').textContent=family?(",
     "$('#canvas-sub').textContent=family?state.lens==='tree'?(state.treeOrient==='h'?'Ancestors to the right, descendants to the left, one band per generation.':'Ancestors above, descendants below, one band per generation.')+' Use − / + for more generations; the round buttons open or fold away one line.':("),
    ("function focusFamilyStart(id){const n=scene.map.get(id);if(!n)return;",
     "function focusFamilyStart(id){const n=scene.map.get(id);if(!n)return;if(scene.tree){treeStart(n);return}"),
    ("if(scene.type==='all')drawEraGround();", "if(scene.type==='all')drawEraGround();else if(scene.tree)drawTreeBands();"),
    ("ctx.restore();\n }\n perf={drawMs", "if(scene.tree)drawTreeLabels();ctx.restore();\n }\n perf={drawMs"),
    ("ctx.textAlign='left';addHit(n.id,'expand',b)}}", "ctx.textAlign='left';addHit(n.id,'expand',b)}if(scene.tree)treeButtons(n,box)}"),
    ("ctx.strokeStyle=sel?'#8bab78':'#d2dcc7';ctx.lineWidth=sel?1.3:.8;",
     "const rootCard=n.isRoot&&scene.tree;ctx.strokeStyle=sel?'#8bab78':rootCard?'#4f6d43':'#d2dcc7';ctx.lineWidth=sel?1.3:rootCard?1.8:.8;"),
    ("const p=screen(n),scale=cam.k,ww=232*scale,hh=76*scale;", "const p=screen(n),scale=cam.k,ww=(scene.tree?TREE.cw:232)*scale,hh=(scene.tree?TREE.ch:76)*scale;"),
    ("x:(W-right)/2-(n.x+(scene.type==='family'?116:0))*kk,y:Math.max(235,H*.52)-(n.y+(scene.type==='family'?38:0))*kk",
     "x:(W-right)/2-(n.x+(scene.tree?TREE.cw/2:scene.type==='family'?116:0))*kk,y:Math.max(235,H*.52)-(n.y+(scene.tree?TREE.ch/2:scene.type==='family'?38:0))*kk"),
    ("ctx.fillText(trimText(life(p)+' · '+p.id,b.w-28*k)", "ctx.fillText(trimText(scene.tree?life(p):life(p)+' · '+p.id,b.w-28*k)"),
    # Tree fold buttons replace the "+n" badges; a click opens or folds one line.
    ("addHit(n.id,'card',box);if(n.hidden){", "addHit(n.id,'card',box);if(n.hidden&&!scene.tree){"),
    ("else if(h.type==='expand')expandFamily(h.id);else goFamily(h.id);return}", "else if(h.type==='expand'){if(!h.dir)expandFamily(h.id)}else goFamily(h.id);return}"),
    ("else if(h.type==='expand')expandFamily(h.id);else clickTimer=setTimeout(()=>openPerson(h.id,false),210)",
     "else if(h.type==='expand')expandFamily(h.id,h);else clickTimer=setTimeout(()=>openPerson(h.id,false),210)"),
    ("function expandFamily(id){if(state.view!=='family'){goFamily(id);return}",
     "function expandFamily(id,h){if(h&&h.dir&&scene&&scene.tree){treeToggle(id,h.dir,h.act);return}if(state.view!=='family'){goFamily(id);return}"),
    ("if(hover===key)return;hover=key;", "if(hover===key)return;hover=key;if(scene&&scene.tree)invalidate();"),
    ("function hideTooltip(){$('#tooltip').hidden=true;hover=null}", "function hideTooltip(){$('#tooltip').hidden=true;if(hover&&scene&&scene.tree)invalidate();hover=null}"),
    ("textContent=family?'Click a profile · use + badges to unfold · F to fit'", "textContent=family?(scene?.tree?'Click a profile · round buttons open or fold a line · F to fit':'Click a profile · use + badges to unfold · F to fit')"),
    ("$$('[data-lens]').forEach(b=>b.classList.toggle('active',b.dataset.lens===state.lens));",
     "$$('[data-lens]').forEach(b=>b.classList.toggle('active',b.dataset.lens===state.lens));treeUI();"),
]


def whole_tree_renderer(page: str) -> str:
    """Apply the canopy fixes once; pages without the canopy pass through."""
    if 'function drawCanopy(' not in page:
        return page
    for old, new in PATCHES:
        if new in page:
            continue
        if page.count(old) != 1:
            raise ValueError('Whole-tree patch anchor not found exactly once: ' + old[:70])
        page = page.replace(old, new, 1)
    return page
