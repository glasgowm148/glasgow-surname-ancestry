"""Regression: targeted note refresh must preserve the public boundary."""
import json
import re
import unittest
from unittest.mock import patch
from tools.public_privacy import PublicPrivacy
from tools.sync_catalogue_research import public_findings


class TargetedFindingsPrivacyTests(unittest.TestCase):
    def test_targeted_findings_withhold_private_paragraph_and_keep_record(self):
        policy = PublicPrivacy({'Private-1': {'birth_date': '2000-01-01'}})
        policy.tester_ids = frozenset({'kit-secret'})
        policy.tester_pattern = re.compile(r'kit-secret')
        raw = [{'sections': [{'markdown': 'Private-1 family narrative.\n\n'
                'Public record: [1775 postal list](https://example.org/record).\n\n'
                'Tester kit-secret family narrative.'}]}]
        with patch('tools.sync_catalogue_research.catalogue._load_research_findings', return_value=raw):
            published = json.dumps(public_findings(['Historical-1'], policy))
        self.assertNotIn('Private-1', published)
        self.assertNotIn('kit-secret', published)
        self.assertIn('1775 postal list', published)
        self.assertIn('https://example.org/record', published)
        self.assertIn('Private-1', raw[0]['sections'][0]['markdown'])
