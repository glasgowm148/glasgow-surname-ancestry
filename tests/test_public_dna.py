from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import repair_public_dna
from tools.site_sources.ydna_story import build as ydna_build
from tools.public_ydna_research import PRIVATE, STUDY, LINES, approved_inputs, study_is_approved
from tools.public_privacy import PublicPrivacy, tester_identifier_pattern
from tools.repair_public_mirrors import repair as repair_mirrors


def study() -> dict[str, object]:
    return {
        "metadata": {"referenceKit": "KIT-REFERENCE"},
        "kits": [{"id": "KIT-A"}, {"id": "KIT-B"}],
        "roots": [{
            "kitIds": ["KIT-A"], "name": "Alexander Glasgow", "years": "c.1811",
            "profile": "Glasgow-951", "haplo": "R-FT20271", "route": "Antrim to Scotland",
        }],
        "pairs": {"KIT-A|KIT-B": {"gd": 3}},
        "audit": {"ids": ["KIT-B"]},
    }


def atlas_model() -> dict[str, object]:
    return {
        "meta": {"dnaCoverage": "old coverage", "catalogueGenerated": "2026-09-06"},
        "people": [],
        "landmarks": ["@root", "Glasgow-951"],
        "dna": [{"id": "Glasgow-951", "kits": ["KIT-A"]}],
    }


def renderer(relative: str) -> str:
    if relative == "assets/repair/atlas.js":
        return "const rows = panel.querySelectorAll('[data-dna-search]');\n"
    script = "function dnaCallout(d){return d.kits.join('')}\nfunction renderDetail(){}\nfunction renderDNA(){}\nlet searchItems=[];"
    if relative.endswith("template.html"):
        return '<html><head></head><body><script id="tree-data" type="application/json">__MODEL__</script>' + script + "</body></html>"
    if relative.endswith("index.html") and "onetree/" in relative:
        return '<html><head></head><body><a class="g-snapshot-link" href="/status/" title="old">old</a><aside id="repair-tester-panel"><article class="repair-tester-row" data-dna-search="KIT-A"></article></aside><script id="tree-data" type="application/json">' + json.dumps(atlas_model()) + "</script>" + script + "</body></html>"
    if relative.endswith("standalone.html"):
        return '<html><head></head><body><script id="tree-data" type="application/json">' + json.dumps(atlas_model()) + "</script>" + script + "</body></html>"
    return script


requires_approved_study = unittest.skipUnless(
    all((PRIVATE / relative).is_file() for relative in (STUDY, LINES)),
    "requires local approved private Y-DNA inputs",
)
requires_approved_atlas = unittest.skipUnless(
    (repair_public_dna.ROOT / "data/private/publication-source-archives/original-upload.html").is_file()
    and (repair_public_dna.ROOT / "data/private/approved-restoration-sources/assets/research/atlas-model.json").is_file(),
    "requires local approved restoration source archives",
)


class PublicDnaRepairTests(unittest.TestCase):
    @requires_approved_atlas
    def test_public_atlas_preserves_approved_tester_models_and_controls(self) -> None:
        web = repair_public_dna.WEB
        from tools.approved_restorations import audit, entries, source
        self.assertEqual([], audit(web))
        for relative in repair_public_dna.ATLAS_MODELS:
            model = json.loads((web / relative).read_text(encoding="utf-8"))
            original = json.loads(source(entries()[relative]))
            self.assertEqual(original['dna'], model['dna'])
            self.assertTrue(set(original['landmarks']).issubset(model['landmarks']))
        self.assertIn("Atlas · 6 Sep 2026", (web / "onetree/index.html").read_text(encoding="utf-8"))
        self.assertIn('id="repair-tester-panel"', (web / "onetree/index.html").read_text())
        self.assertIn('dnaMarkers:()=>[...DNA.values()]', (web / "assets/research/atlas.js").read_text())

    @requires_approved_atlas
    def test_restoration_approval_rejects_changed_or_unscoped_payloads(self):
        from tools.approved_restorations import approved_document, entries, source
        path = 'assets/research/atlas-model.json'
        content = source(entries()[path])
        self.assertTrue(approved_document(path, content))
        changed = json.loads(content)
        changed['dna'].append({'id':'Unapproved-100', 'kits':['NEW-KIT']})
        self.assertFalse(approved_document(path, json.dumps(changed)))
        self.assertFalse(approved_document('unapproved/model.json', content))

    def test_approved_dna_projection_keeps_kits_and_rejects_living_details(self):
        from copy import copy
        policy = PublicPrivacy({'PrivateExample-1': {'birth_date':'2000-01-01'}})
        approved = copy(policy)
        approved.allow_approved_dna = True
        value = {'kits':['REFERENCE-KIT'], 'relatives':[{'id':'PrivateExample-1', 'name':'Private name'}]}
        self.assertNotIn('kits', policy.project(value))
        rendered = approved.project(value)
        self.assertEqual(['REFERENCE-KIT'], rendered['kits'])
        self.assertNotIn('Private name', json.dumps(rendered))

    @patch("tools.public_ydna_research.approved_inputs", return_value=None)
    def test_safe_renderer_excludes_tester_fields(self, _approved_inputs) -> None:
        page = ydna_build.render(study(), canonical="https://example.test/ydna/")
        for identifier in ("KIT-REFERENCE", "KIT-A", "KIT-B", "research-data"):
            self.assertNotIn(identifier, page)
        self.assertIn("Alexander Glasgow", page)
        self.assertIn('href="/people/Glasgow-951/"', page)
        self.assertIn("R-FT20271", page)

    @requires_approved_study
    def test_curated_approval_does_not_authorize_new_tester_records(self) -> None:
        inputs = approved_inputs()
        self.assertIsNotNone(inputs)
        data = json.loads(json.dumps(inputs[STUDY]))
        self.assertTrue(study_is_approved(data))
        data["kits"].append({"id": "UNAPPROVED-TESTER", "name": "Unapproved person"})
        self.assertFalse(study_is_approved(data))
        page = ydna_build.render(data, canonical="https://example.test/ydna/")
        self.assertNotIn("research-data", page)
        self.assertNotIn("UNAPPROVED-TESTER", page)

    @requires_approved_study
    def test_privacy_mirror_exception_is_scoped_and_keeps_living_filter(self) -> None:
        data = approved_inputs()[STUDY]
        page = ydna_build.render(data, canonical="https://example.test/ydna/")
        identifier = data["metadata"]["referenceKit"]
        policy = PublicPrivacy({"PrivateExample-1": {"birth_date": "2000-01-01"}})
        policy.tester_ids = frozenset({identifier})
        policy.tester_pattern = tester_identifier_pattern(policy.tester_ids)
        self.assertTrue(policy.contains_private_id(identifier))
        self.assertFalse(policy.contains_private_id(identifier, include_testers=False))
        self.assertTrue(policy.contains_private_id("PrivateExample-1", include_testers=False))
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            target = web / "ydna/index.html"
            target.parent.mkdir()
            target.write_text(page.replace("</main>", "<p>PrivateExample-1</p></main>", 1))
            other = web / "unapproved.html"
            other.write_text(f"<p>Private comparison kit {identifier}</p>")
            repair_mirrors(web, policy)
            self.assertIn(identifier, target.read_text())
            self.assertNotIn("PrivateExample-1", target.read_text())
            self.assertNotIn(identifier, other.read_text())
            self.assertTrue(policy.contains_private_id(identifier))

    @patch("tools.public_ydna_research.approved_inputs", return_value=None)
    def test_repair_archives_private_sources_then_withholds_public_assets(self, _approved_inputs) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "www"
            private = root / "private"
            for relative in repair_public_dna.WITHHELD_ASSETS:
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if relative.endswith("data.json"):
                    path.write_text(json.dumps(study()), encoding="utf-8")
                elif relative.endswith("dna-index.json"):
                    path.write_text(json.dumps([{"kits": ["KIT-INDEX"]}]), encoding="utf-8")
                else:
                    path.write_text("KIT-A private material", encoding="utf-8")
            public_index = web / repair_public_dna.DNA_INDEX
            public_index.parent.mkdir(parents=True, exist_ok=True)
            public_index.write_text(json.dumps([{"kits": ["KIT-INDEX"]}]), encoding="utf-8")
            for relative in repair_public_dna.SAFE_PAGES:
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("old KIT-A explorer", encoding="utf-8")
            for relative in repair_public_dna.ATLAS_MODELS:
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(atlas_model()), encoding="utf-8")
            for relative in repair_public_dna.ATLAS_RENDERERS:
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(renderer(relative), encoding="utf-8")

            changed = repair_public_dna.repair(web, private)
            self.assertEqual(len(repair_public_dna.WITHHELD_ASSETS) * 2, changed["withheld_assets"])
            self.assertEqual(2, changed["preserved_pages"])
            self.assertEqual(1, changed["preserved_dna_index"])
            self.assertEqual(1, changed["safe_dna_index"])
            self.assertEqual(2, changed["safe_pages"])
            self.assertEqual(len(repair_public_dna.ATLAS_MODELS), changed["atlas_models"])
            self.assertEqual(len(repair_public_dna.ATLAS_RENDERERS), changed["atlas_renderers"])
            self.assertEqual([], repair_public_dna.audit(web, private))
            self.assertTrue({"KIT-REFERENCE", "KIT-A", "KIT-B", "KIT-INDEX"}.issubset(
                repair_public_dna.private_tester_ids(private)
            ))
            for relative in repair_public_dna.WITHHELD_ASSETS:
                self.assertFalse((web / relative).exists(), relative)
                self.assertTrue((private / relative).exists(), relative)
            self.assertEqual("[]\n", (web / repair_public_dna.DNA_INDEX).read_text(encoding="utf-8"))
            self.assertTrue((private / repair_public_dna.DNA_INDEX).exists())
            for relative in repair_public_dna.ATLAS_MODELS:
                self.assertTrue((private / relative).exists())
                model = json.loads((web / relative).read_text(encoding="utf-8"))
                self.assertEqual([], model["dna"])
                self.assertEqual(repair_public_dna.DNA_COVERAGE, model["meta"]["dnaCoverage"])
            for relative in repair_public_dna.ATLAS_RENDERERS:
                self.assertTrue((private / relative).exists())
                page = (web / relative).read_text(encoding="utf-8")
                self.assertNotIn("data-dna-search", page)
                self.assertNotIn("d.kits", page)
            page = (web / "ydna/index.html").read_text(encoding="utf-8")
            self.assertIn("Historical branch summary", page)
            self.assertNotIn("KIT-A", page)
            self.assertNotIn("research-data", page)
            self.assertEqual(
                {
                    "withheld_assets": 0,
                    "preserved_pages": 0,
                    "preserved_dna_index": 0,
                    "safe_dna_index": 0,
                "safe_pages": 0,
                "approved_lines": 0,
                    "atlas_models": 0,
                    "atlas_renderers": 0,
                    "onetree_snapshot": 0,
                },
                repair_public_dna.repair(web, private),
            )


if __name__ == "__main__":
    unittest.main()
