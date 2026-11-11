import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import build_research_catalog as catalogue


class CatalogueCsvExportsTests(unittest.TestCase):
    def test_refresh_preserves_quoted_evidence_family_ids_and_mirrors(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            person={'catalogue_id':'fictional-person','name':'Example, "One"',
                    'records':[], 'profile_information':[], 'wikitree_evidence':[],
                    'relationship_warnings':[]}
            for field in ('profile_ids','first_names','last_names_at_birth','last_names_current',
                          'suffixes','clusters','evidence','recorded_in','regions','spouses','father','mother','children'):
                person[field]=[]
            person['father']=[{'name':'Parent, Two','id':'Example-2'}]
            record={'record_id':'record-one','note':'Quoted, evidence\nsecond line',
                    'source_type':'explicit','supporting_source_status':'unresolved'}
            with patch.object(catalogue,'DATA_DIR',root):
                catalogue.write_csv_exports([person],[record],'2026-11-11','test-export')
                person['name']='Updated example'
                catalogue.write_csv_exports([person],[record],'2026-11-11','test-export')
            def rows(name):
                with (root/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
            self.assertEqual('Updated example',rows('people.csv')[0]['name'])
            self.assertEqual('Parent, Two [Example-2]',rows('people.csv')[0]['father'])
            self.assertEqual(record['note'],rows('records.csv')[0]['note'])
            self.assertEqual([],rows('source-gaps.csv'))
            self.assertEqual('record-one',rows('source-review.csv')[0]['record_id'])
            for name in ('people.csv','records.csv','source-gaps.csv','source-review.csv'):
                self.assertEqual((root/name).read_bytes(),(root/(name+'.txt')).read_bytes())
