"""Keep map fallbacks useful without presenting profile locality as a precise pin."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"


def patch(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Expected map fragment was not found: {old[:72]}")
    return text.replace(old, new, 1)


def repair() -> dict[str, int]:
    changed: dict[str, int] = {}
    path = WEB / "assets/research/map.js"
    original = text = path.read_text(encoding="utf-8")
    states = """const stateFallbacks={Alabama:[32.8067,-86.7911],Alaska:[61.3707,-152.4044],Arizona:[33.7298,-111.4312],Arkansas:[34.9697,-92.3731],California:[36.1162,-119.6816],Colorado:[39.0598,-105.3111],Connecticut:[41.5978,-72.7554],Delaware:[39.3185,-75.5071],Florida:[27.7663,-81.6868],Georgia:[33.0406,-83.6431],Hawaii:[21.0943,-157.4983],Idaho:[44.2405,-114.4788],Illinois:[40.3495,-88.9861],Indiana:[39.8494,-86.2583],Iowa:[42.0115,-93.2105],Kansas:[38.5266,-96.7265],Kentucky:[37.6681,-84.6701],Louisiana:[31.1695,-91.8678],Maine:[44.6939,-69.3819],Maryland:[39.0639,-76.8021],Massachusetts:[42.2302,-71.5301],Michigan:[43.3266,-84.5361],Minnesota:[45.6945,-93.9002],Mississippi:[32.7416,-89.6787],Missouri:[38.4561,-92.2884],Montana:[46.9219,-110.4544],Nebraska:[41.1254,-98.2681],Nevada:[38.3135,-117.0554],"New Hampshire":[43.4525,-71.5639],"New Jersey":[40.2989,-74.521],"New Mexico":[34.8405,-106.2485],"New York":[42.1657,-74.9481],"North Carolina":[35.6301,-79.8064],"North Dakota":[47.5289,-99.784],Ohio:[40.3888,-82.7649],Oklahoma:[35.5653,-96.9289],Oregon:[44.572,-122.0709],Pennsylvania:[40.5908,-77.2098],"Rhode Island":[41.6809,-71.5118],"South Carolina":[33.8569,-80.945],"South Dakota":[44.2998,-99.4388],Tennessee:[35.7478,-86.6923],Texas:[31.0545,-97.5635],Utah:[40.150,-111.8624],Vermont:[44.0459,-72.7107],Virginia:[37.7693,-78.17],Washington:[47.4009,-121.4905],"West Virginia":[38.4912,-80.9545],Wisconsin:[44.2685,-89.6165],Wyoming:[42.756,-107.3025],"District of Columbia":[38.9072,-77.0369]};
const stateFromPlace=place=>{const value=String(place||'');return Object.keys(stateFallbacks).find(state=>new RegExp('(^|[,\\\\s])'+state.replace(/ /g,'\\\\\\\\s+')+'(?=$|[,.)\\\\s])','i').test(value))||null};
const splitUnitedStatesFallbacks=(broad,records)=>broad.flatMap(point=>{if(point.country!=='america')return [point];const groups=new Map(),country=[];for(const item of point.items){const state=stateFromPlace(records.get(item[0])?.place);if(state)(groups.get(state)||groups.set(state,[]).get(state)).push(item);else country.push(item)}return [...groups].map(([state,items])=>{const [lat,lon]=stateFallbacks[state];return {...point,lat,lon,name:state+' · approximate state-level point',precision:'Approximate state-centre fallback from profile locality',items,level:'state',precision_level:'state',stateFallback:true}}).concat(country.length?[{...point,items:country}]:[])});"""
    # Replace the entire owned block, including duplicates from older repairs.
    # Exact-string insertion is unsafe when a helper's escaping changes.
    matcher_start = states.index("const stateFromPlace=")
    matcher_end = states.index("\nconst splitUnitedStatesFallbacks=", matcher_start)
    states = states[:matcher_start] + "const stateFromPlace=place=>{const value=' '+String(place||'').toLowerCase().replace(/[^a-z]+/g,' ')+' ';return Object.keys(stateFallbacks).sort((a,b)=>b.length-a.length).find(state=>value.includes(' '+state.toLowerCase()+' '))||null};" + states[matcher_end:]
    controls_start = text.index("const controls=")
    states_start = text.find("const stateFallbacks=")
    start = states_start if states_start >= 0 else controls_start
    text = text[:start] + states + "\n" + text[controls_start:]
    text = patch(text, "points=[...ps,...broad.map(p=>({...p,broad:true}))].map(p=>({...p,key:(p.broad?'country-':'loc-')+p.lat+'-'+p.lon}));", "points=[...ps,...splitUnitedStatesFallbacks(broad,recordLookup).map(p=>({...p,broad:true}))].map(p=>({...p,key:(p.broad?'fallback-':'loc-')+p.lat+'-'+p.lon}));")
    text = patch(text, "+' country summaries'", "+' fallback summaries'")
    text = patch(text, "' associations in view (including country summaries)'", "' associations in view (including fallback summaries)'")
    if "clusteredFallbackRendering" not in text:
        text = patch(text, "g.broad?'Country summary: '+g.count.toLocaleString()+' associations awaiting local coordinates'", "g.broad?(g.rows[0].stateFallback?'State-level fallback: ':'Country summary: ')+g.count.toLocaleString()+' associations awaiting local coordinates'")
    rendering = (ROOT / "tools/map_cluster_rendering.js").read_text(encoding="utf-8")
    start = text.find("// clusteredFallbackRendering")
    if start < 0:
        start = text.index("function draw(){")
    end = text.index("function resize(){", start)
    text = text[:start] + rendering.rstrip() + "\n" + text[end:]
    tooltip_start = text.index("tooltip.textContent=")
    tooltip_end = text.index(";tooltip.style.left", tooltip_start)
    text = text[:tooltip_start] + "tooltip.textContent=describeMapCluster(g)" + text[tooltip_end:]
    if text != original:
        path.write_text(text, encoding="utf-8")
        changed["map_state_fallbacks"] = 1

    page_path = WEB / "map/index.html"
    page = page_path.read_text(encoding="utf-8")
    revised = page.replace("Country summary: local coordinates pending", "Fallback summary: country or approximate US state")
    layout = """<style id="map-control-layout">
.r-map-frame{display:grid;grid-template-rows:minmax(0,1fr) auto auto}
.r-map-frame canvas{grid-row:1;min-height:0}
.r-map-frame .v3-pan-controls.map-pan{top:15px;left:60px;bottom:auto}
.r-map-frame .r-map-legend{position:static;grid-row:2;max-width:none;margin:8px 12px 4px;padding:8px 10px}
.r-map-frame .r-map-attribution{position:static;grid-row:3;text-align:right;line-height:1.5;padding:5px 9px}
</style>"""
    if 'id="map-control-layout"' not in revised:
        revised = revised.replace("</head>", layout + "\n</head>", 1)
    if revised != page:
        page_path.write_text(revised, encoding="utf-8")
        changed["map_legend"] = 1
    return changed


if __name__ == "__main__":
    print(repair())
