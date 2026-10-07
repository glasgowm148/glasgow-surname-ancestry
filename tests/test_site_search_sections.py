"""Site search finds families, studies, research questions and latest findings (S1-08)."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import site_search
from tools.site_search import ROOT, build_search_indexes, install_search, section_rows

WEB = ROOT / "www"


def write(root: Path, relative: str, content) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def fixture_site(root: Path) -> Path:
    write(root, "assets/research/branches.json", [
        {"id": "lisnagaver-rasharkin", "label": "Lisnagaver & Rasharkin", "kind": "place", "url": "/branches/lisnagaver-rasharkin/",
         "rootId": "Glasgow-951", "count": 28, "from": 1790.0, "to": 1896.0, "topic_ids": ["early-ireland"],
         "description": "Alexander and Mary Glasgow’s six-child family is documented through baptisms. More text follows."},
        {"id": "family-glasgow-1", "label": "John Glasgow · c. 1700", "kind": "family", "url": "/branches/family-glasgow-1/",
         "rootId": "Glasgow-1", "count": 1, "description": "Browse the relationships attached to John Glasgow."},
        {"id": "unbuilt", "label": "Not built", "kind": "family", "url": "/branches/unbuilt/"},
    ])
    write(root, "branches/lisnagaver-rasharkin/index.html", "<html></html>")
    write(root, "branches/family-glasgow-1/index.html", "<html></html>")
    write(root, "research/index.html", "<html></html>")
    write(root, "research/subjects/ballymena-1857/subjects.json",
          {"title": "Ballymena Hillis Elder 1857", "people": [{"name": "Alex Hillis"}, {"name": "Annie Elder"}]})
    write(root, "research/subjects/ballymena-1857/index.html", "<html></html>")
    write(root, "research/transcriptions/geillis-1603/index.html", "<main><h1>Geillis Glasgow, spouse to Thomas Wilson</h1></main>")
    write(root, "data/latest-findings-index.json", [{"id": "finding-larne-1700", "url": "/latest-findings/page/2/"}])
    write(root, "findings.json", {"findings": [
        {"id": "larne-1700", "found_on": "2026-10-06", "finding": "The Larne session minutes belong to 1700 and 1701. A second sentence.",
         "people": [{"id": "Glasgow-1502", "name": "Robert Glasgow"}]},
        {"id": "unpublished", "found_on": "2026-10-06", "finding": "Not on any page yet.", "people": []},
    ]})
    write(root, "data/places-index.json", [
        {"id": "kilrea", "slug": "kilrea", "name": "Kilrea", "region": "Ireland", "people": 1, "records": 2,
         "year_from": 1831, "year_to": 1831, "surnames": ["Glasgow"], "url": "/places/kilrea.html"},
        {"id": "missing", "slug": "missing", "name": "Missing", "url": "/places/missing.html"},
    ])
    write(root, "places/kilrea.html", "<html></html>")
    return root


class SectionIndexTests(unittest.TestCase):
    def test_fixture_rows_carry_type_url_and_short_description(self):
        with tempfile.TemporaryDirectory() as directory:
            site = fixture_site(Path(directory))
            rows = {row[0]: dict(zip(site_search.SECTION_FIELDS, row)) for row in section_rows(site, site / "findings.json")}
        study = rows["study-lisnagaver-rasharkin"]
        self.assertEqual(("Lisnagaver & Rasharkin", "/branches/lisnagaver-rasharkin/", "Local study"),
                         (study["name"], study["url"], study["type"]))
        self.assertTrue(study["sub"].startswith("Local study · 28 people · 1790–1896 · Alexander and Mary"))
        self.assertNotIn("More text", study["sub"])
        self.assertEqual("Family group", rows["study-family-glasgow-1"]["type"])
        self.assertIn("1 person", rows["study-family-glasgow-1"]["sub"])
        self.assertNotIn("study-unbuilt", rows)
        finding = rows["finding-larne-1700"]
        self.assertEqual("/latest-findings/page/2/#finding-larne-1700", finding["url"])
        self.assertEqual("The Larne session minutes belong to 1700 and 1701.", finding["name"])
        self.assertEqual("Latest finding · 6 October 2026 · Robert Glasgow", finding["sub"])
        self.assertIn("Glasgow-1502", finding["search"])
        self.assertNotIn("finding-unpublished", rows)
        self.assertEqual("Record study", rows["subject-ballymena-1857"]["type"])
        self.assertIn("Alex Hillis", rows["subject-ballymena-1857"]["sub"])
        self.assertEqual("Wills & transcriptions · 1603", rows["transcription-geillis-1603"]["sub"])
        questions = [row for row in rows.values() if row["type"] == "Research question"]
        from tools.repair_research_questions import QUESTIONS, ADDITIONAL_QUESTIONS
        self.assertEqual(len(QUESTIONS) + len(ADDITIONAL_QUESTIONS), len(questions))
        self.assertTrue(all(row["url"].startswith("/") for row in questions), "questions stay on the site")

    def test_indexes_are_written_idempotently_and_not_for_an_empty_site(self):
        with tempfile.TemporaryDirectory() as directory:
            site = fixture_site(Path(directory))
            first = build_search_indexes(site, site / "findings.json")
            self.assertEqual(3, first["search_indexes"])
            self.assertEqual(1, first["search_place_rows"])
            self.assertNotIn("search_indexes", build_search_indexes(site, site / "findings.json"))
            payload = json.loads((site / site_search.SECTION_INDEX).read_text())
            self.assertEqual(site_search.SECTION_FIELDS, payload["fields"])
            places = json.loads((site / "assets/v3/search-places.json").read_text())
            self.assertEqual([["kilrea", "Kilrea", "/places/kilrea.html", "Ireland · 1 person · 2 records · 1831", "Ireland Glasgow"]], places)
            unified = json.loads((site / "assets/unified/search-places.json").read_text())
            self.assertEqual({"name", "url", "meta", "search"}, set(unified[0]))
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual({}, build_search_indexes(Path(directory), Path(directory) / "none.json"))
            self.assertEqual({"shared_search_assets": 2}, install_search(Path(directory)))
            self.assertFalse((Path(directory) / site_search.SECTION_INDEX).exists())

    @unittest.skipUnless((WEB / "assets/research/branches.json").exists(), "built site not present")
    def test_built_site_rows_point_at_published_pages_and_stay_small(self):
        rows = section_rows(WEB)
        types = {row[5] for row in rows}
        self.assertLessEqual({"Family group", "Local study", "Research question", "Latest finding", "Record study"}, types)
        urls = {row[2] for row in rows}
        self.assertIn("/branches/lisnagaver-rasharkin/", urls)
        for row in rows:
            path = row[2].split("#")[0]
            target = WEB / (path.strip("/") + "/index.html" if path.endswith("/") else path.lstrip("/"))
            self.assertTrue(target.exists(), row[2])
        size = len(json.dumps({"rows": rows}, ensure_ascii=False, separators=(",", ":")).encode())
        self.assertLess(size, 600_000)
        self.assertEqual(len(json.loads((WEB / "data/places-index.json").read_text())), len(site_search.place_rows(WEB)))


class WorkerSearchTests(unittest.TestCase):
    def run_node(self, script):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            install_search(site)
            return json.loads(subprocess.check_output(["node", "-e", script, str(site)], text=True))

    def test_worker_finds_section_pages_and_keeps_people_results(self):
        result = self.run_node(r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const sections={schema_version:1,fields:['id','name','url','sub','search','type'],rows:[
 ['study-lisnagaver-rasharkin','Lisnagaver & Rasharkin','/branches/lisnagaver-rasharkin/','Local study · 28 people','Glasgow-951','Local study'],
 ['finding-x','James Glasgow of Lisnagaver signed the lease','/latest-findings/#finding-x','Latest finding · 6 October 2026 · James Glasgow','Glasgow-1','Latest finding'],
 ['question-glasgow-951',"Who were Alexander of Lisnagaver's parents?",'/people/glasgow-951.html','Research question · Alexander Glasgow','glasgow-951','Research question']]};
const datasets={
 '/assets/v3/search-people.json':Array.from({length:30},(_,i)=>['person-'+i,'James Glasgow '+i,'/people/p-'+i+'.html','','']),
 '/assets/v3/search-records.json':[],'/assets/v3/search-places.json':[['lisnagaver','Lisnagaver','/places/lisnagaver.html','','']],
 '/assets/research/free-space-index.json':[],'/assets/v3/search-sections.json':sections};
let response;
const ctx={URL,importScripts:()=>{},globalThis:{},fetch:async url=>({ok:true,json:async()=>datasets[new URL(url).pathname]}),
 self:{location:{href:'https://fixture.test/assets/research/search-worker.js'},postMessage:r=>response=structuredClone(r)}};
vm.runInNewContext(fs.readFileSync(path.join(process.argv[1],'assets/research/search-worker.js'),'utf8'),ctx);
(async()=>{const out={};
 for(const [q,tab] of [['lisnagaver','pages'],['lisnagaver','all'],['james','people'],['james','all'],['latest findings','pages']]){
  await ctx.self.onmessage({data:{id:1,type:'search',q,tab}});if(response.error)throw Error(response.error);
  out[q+'|'+tab]={items:response.result.map(r=>({name:r.name,url:r.url,kind:r.kind,type:r.type||null,meta:r.meta})),counts:response.result.counts};
 }
 // The ranking function is a plain top-level function in the worker.
 const row=(name,boost)=>({_key:name,_title:name,_id:'x',boost});
 out.rank={exact:ctx.score(row('lisnagaver',0),'lisnagaver',['lisnagaver']),route:ctx.score(row('lisnagaver rasharkin',4),'lisnagaver',['lisnagaver']),
  finding:ctx.score(row('lisnagaver rasharkin',0),'lisnagaver',['lisnagaver']),miss:ctx.score(row('larne',4),'lisnagaver',['lisnagaver'])};
 console.log(JSON.stringify(out));
})().catch(e=>{console.error(e);process.exitCode=1});
''')
        pages = result["lisnagaver|pages"]["items"]
        self.assertEqual("/branches/lisnagaver-rasharkin/", pages[0]["url"])
        self.assertEqual("Local study", pages[0]["type"])
        self.assertTrue(pages[0]["meta"].startswith("Local study"))
        self.assertEqual({"/branches/lisnagaver-rasharkin/", "/latest-findings/#finding-x", "/people/glasgow-951.html"},
                         {row["url"] for row in pages})
        everything = result["lisnagaver|all"]
        self.assertEqual(1, everything["counts"]["place"])
        self.assertEqual(3, everything["counts"]["page"])
        # People results are unchanged: same rows, same order, no section rows among them.
        people = result["james|people"]["items"]
        self.assertEqual(30, len(people))
        self.assertTrue(all(row["kind"] == "person" for row in people))
        self.assertEqual(30, result["james|all"]["counts"]["person"])
        self.assertEqual(1, result["james|all"]["counts"]["page"])
        self.assertEqual("/latest-findings/", result["latest findings|pages"]["items"][0]["url"])
        rank = result["rank"]
        self.assertGreater(rank["exact"], rank["route"])
        self.assertGreater(rank["route"], rank["finding"])
        self.assertEqual(-1, rank["miss"])

    def test_fallback_search_includes_sections_and_offers_starting_points(self):
        result = self.run_node(r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const empty=()=>null,body={dataset:{},classList:{contains:()=>false,add:()=>{}}};
const data={'/assets/research/free-space-index.json':[],'/assets/v3/search-sections.json':{fields:['id','name','url','sub','search','type'],
 rows:[['study-l','Lisnagaver & Rasharkin','/branches/lisnagaver-rasharkin/','Local study · 28 people','Glasgow-951','Local study']]}};
const ctx={window:{},document:{body,querySelector:empty,getElementById:empty,querySelectorAll:()=>[],addEventListener:()=>{}},
 localStorage:{getItem:()=>null,setItem:()=>{}},MutationObserver:class{observe(){}},innerWidth:1440,
 matchMedia:()=>({matches:false}),setTimeout,clearTimeout,URL,location:{origin:'https://fixture.test'},
 fetch:async url=>({ok:true,json:async()=>data[url]})};
ctx.window.addEventListener=()=>{};
const source=fs.readFileSync(path.join(process.argv[1],'assets/unified/site.js'),'utf8');
vm.runInNewContext(source,ctx);
(async()=>{const found=await ctx.window.GlasgowSite.search('lisnagaver','pages');
 console.log(JSON.stringify({found:found.map(r=>({url:r.url,meta:r.meta,type:r.type})),hint:/latest-findings/.test(source.match(/const SEARCH_ROUTES=.*/)[0])}))})().catch(e=>{console.error(e);process.exitCode=1});
''')
        self.assertEqual([{"url": "/branches/lisnagaver-rasharkin/", "meta": "Local study · 28 people", "type": "Local study"}],
                         result["found"])
        self.assertTrue(result["hint"])


if __name__ == "__main__":
    unittest.main()
