import json
from pathlib import Path
import tempfile
import unittest

from tools.catalogue_machine_data import _assessment_claim
from tools.repair_assessment_dates import PROVENANCE, correct, repair
from tools.publish_static_sources import block
from tools.repair_sources_page import source_row


class AssessmentDatesTests(unittest.TestCase):
    def test_narrative_numbers_never_become_dates(self):
        assessment = dict(person_a='Glasgow-3172', person_b='Glasgow-3970',
                          relationship='possible relative of', status='possible',
                          status_label='Possible', source_url=None, provenance=PROVENANCE,
                          basis='James-1081 remained active in 1726; archive 1634, page 1680.')
        self.assertIsNone(_assessment_claim(assessment, {})[1]['date'])
        assessment['event_date'] = '1679-11-08'
        self.assertEqual(_assessment_claim(assessment, {})[1]['date'], '1679-11-08')

    def test_correction_preserves_reviewed_events_and_unrelated_dates(self):
        data = [dict(id='E-target', date='1081', year=1081),
                dict(evidence_id='E-target', date='1679', basis='reviewed_event_role'),
                dict(id='E-other', date='1081')]
        self.assertEqual(correct(data, {'E-target'}), 1)
        self.assertIsNone(data[0]['date'])
        self.assertEqual(data[0]['date_correction']['previous']['year'], 1081)
        self.assertEqual(data[1]['date'], '1679')
        self.assertEqual(data[2]['date'], '1081')
        self.assertEqual(correct(data, {'E-target'}), 0)

    def test_public_mirrors_and_source_range_are_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            def save(relative, data):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data))
            save('people/example.json', {'evidence': [dict(id='E-target', date='1081', provenance=PROVENANCE)]})
            save('assets/v3/events/example.json', [dict(evidence_id='E-target', date='1081', year=1081)])
            save('assets/v3/sources/source.json', {'citations': [dict(evidence_id='E-target', date='1081'), dict(evidence_id='E-real', date='1774')]})
            save('assets/v3/source-index.json', [dict(id='source', title='Source', **{'from':1081, 'to':1774})])
            self.assertEqual(repair(web)['date_corrections'], 3)
            row = json.loads((web/'assets/v3/source-index.json').read_text())[0]
            self.assertEqual((row['from'], row['to']), (1774,1774))
            self.assertEqual(repair(web).get('json_files', 0), 0)

    def test_static_known_source_mirrors_preserve_narrative_and_real_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            def save(relative, data):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data))
            rows = []
            for ident, evidence, false, real in [('s-948d67e0bace40ea','E-aeab90664d7c','1081',None),('s-705d7926892450e7','E-4a3273fb6588','1024','25 Mar 1774')]:
                narrative = f'Glasgow-{false} is a profile ID; original analysis remains intact.'
                citation = dict(evidence_id=evidence,date=false,type='research assessment',assertion=narrative)
                citations = [citation, *([dict(evidence_id='E-real',date=real,type='Birth')] if real else [])]
                doc = dict(id=ident,citations=citations,events=[dict(evidence_id=evidence,date=false,year=int(false))])
                save(f'people/{ident}.json',dict(evidence=[dict(id=evidence,date=false,provenance=PROVENANCE)]))
                save(f'assets/v3/sources/{ident}.json',doc)
                reader = web / f'sources/{ident}/index.html'
                reader.parent.mkdir(parents=True, exist_ok=True)
                reader.write_text('<main>Preserved introduction' + block(doc) + '<div id="v3-reader"></div></main>Preserved footer')
                rows.append(dict(id=ident,title=ident,**{'from':int(false),'to':1774 if real else int(false)}))
            save('assets/v3/source-index.json',rows)
            self.assertEqual(repair(web)['source_readers'],2)
            for ident, false in [('s-948d67e0bace40ea','1081'),('s-705d7926892450e7','1024')]:
                text = (web/f'sources/{ident}/index.html').read_text()
                self.assertNotIn(f'research assessment — {false}',text)
                self.assertIn(f'Glasgow-{false} is a profile ID',text)
                self.assertIn('Preserved introduction',text)
                self.assertIn('Preserved footer',text)
            self.assertIn('25 Mar 1774',(web/'sources/s-705d7926892450e7/index.html').read_text())
            self.assertEqual(repair(web).get('source_readers',0),0)

    def test_complete_browse_resorts_all_rows_and_skips_unrelated_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            (web/'assets/v3').mkdir(parents=True)
            rows = [dict(id=f's-{n}',title=f'Source {n:03}',**{'from':1800+n,'to':1800+n}) for n in range(102)]
            (web/'assets/v3/source-index.json').write_text(json.dumps(rows))
            browse = web/'sources/browse'
            browse.mkdir(parents=True)
            for name, chunk in [('index.html',rows[:100]),('page-2.html',rows[100:])]:
                (browse/name).write_text('<main>Preserved shell'+''.join(source_row(row) for row in reversed(chunk))+'</main>')
            (browse/'help.html').write_text('Unrelated help')
            repair(web)
            first = (browse/'index.html').read_text()
            second = (browse/'page-2.html').read_text()
            self.assertEqual(first.count('class="v3-source-row"'),100)
            self.assertEqual(second.count('class="v3-source-row"'),2)
            self.assertLess(first.index('/sources/s-0/'),first.index('/sources/s-99/'))
            self.assertLess(second.index('/sources/s-100/'),second.index('/sources/s-101/'))
            self.assertEqual((browse/'help.html').read_text(),'Unrelated help')
            self.assertEqual(repair(web).get('source_browse_pages',0),0)
            (browse/'page-2.html').write_text('<main>'+source_row(rows[100])+'</main>')
            with self.assertRaisesRegex(ValueError,'row count mismatch'):
                repair(web)


if __name__ == '__main__':
    unittest.main()
