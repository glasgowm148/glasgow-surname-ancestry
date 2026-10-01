import json, unittest
from tools.site_payloads import pack_model, unpack_model

class SitePayloadTests(unittest.TestCase):
    def test_lossless_mixed_fields(self):
        model = {"people": [{"id":"x", "null":None, "zero":0, "false":False, "missing":[], "rel":{"status":"open"}}], "root":"x", "negative":-12.5, "tags":["l","o","n"]}
        self.assertEqual(unpack_model(pack_model(model)), model)
    def test_repeated_metadata_shrinks(self):
        model = {"people": [{"name":"Repeated metadata", "location":"Same place", "status":"open"} for _ in range(500)]}
        raw = json.dumps(model, separators=(",", ":")); packed = json.dumps(pack_model(model), separators=(",", ":"))
        self.assertLess(len(packed), len(raw) * .95)

if __name__ == "__main__": unittest.main()
