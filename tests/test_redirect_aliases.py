"""Merged person routes resolve to current accounts without changing evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from tools import publish_wikitree_redirect_aliases as aliases


class RedirectAliasTests(unittest.TestCase):
    def test_alias_keeps_current_route_and_retains_old_machine_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            people = root / "www/people"
            people.mkdir(parents=True)
            data = root / "data/wikitree"
            data.mkdir(parents=True)
            (data / "live-profile-overrides.json").write_text(json.dumps({"redirects": {"Old-1": "Current-2"}}))
            (people / "current-2.html").write_text("Current account")
            (people / "old-1.html").write_text("Earlier imported account")
            old_evidence = people / "old-1.json"
            old_evidence.write_text('{"original_evidence":"preserved"}')
            with patch.object(aliases, "ROOT", root):
                self.assertEqual(1, aliases.publish())
                self.assertEqual(0, aliases.publish())
            page = BeautifulSoup((people / "old-1.html").read_text(), "html.parser")
            self.assertEqual("https://glasgow.phenotype.dev/people/current-2.html", page.select_one('link[rel="canonical"]')["href"])
            self.assertEqual("0; url=current-2.html", page.select_one('meta[http-equiv="refresh"]')["content"])
            self.assertEqual('{"original_evidence":"preserved"}', old_evidence.read_text())
