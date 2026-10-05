"""Guard source-grounded documentary newspaper card targets."""
import json
import unittest
from unittest.mock import patch

from tools.build_source_collections import WEB, newspaper_card
from tools.newspaper_card_targets import SOURCE, evidence_tags, identity_status, target_for, load_targets, reading_hash


def row(**changes):
    base = {
        'image_id': 'target-test',
        'date': '1841-03-12',
        'paper': 'Belfast News-Letter',
        'page': 3,
        'source_url': 'https://www.newspapers.com/image/390556571/',
        'status': 'confirmed surname',
        'reading': 'Rev. Adam Glasgow is listed among the clergy.',
        'assessment': 'This passage does not establish a family relationship.',
        'profile_ids': [],
    }
    base.update(changes)
    return base


def target(**changes):
    value = {
        'people': [{
            'name': 'Rev. Adam Glasgow',
            'place': 'Place not stated',
            'birth_label': 'Birth unknown',
            'birth_basis': '',
            'details': ['Listed among clergymen on and around the platform.'],
        }],
        'record_type': 'Meeting report',
        'evidence_tags': [],
        'summary': 'A source-described minister; identity unassigned.',
    }
    value.update(changes)
    return value


class NewspaperCardTargetTests(unittest.TestCase):
    def test_changed_reading_cannot_keep_stale_family_or_birth_summary(self):
        stale = target(evidence_tags=['spouse'], people=[{
            'name': 'Old reading', 'place': 'Old place', 'birth_label': 'b. by c. 1800',
            'birth_basis': 'Old estimate', 'details': ['Named wife.'],
        }])
        stale['reading_sha256'] = reading_hash(row(reading='Old reading names his wife.'))
        with patch('tools.newspaper_card_targets.load_targets', return_value={'target-test': stale}):
            current = row(reading='The corrected passage is a different person.')
            self.assertEqual(evidence_tags(current), set())
            self.assertNotIn('Old reading', str(target_for(current)))
            self.assertEqual(target_for(current)['people'][0]['birth_label'], 'Birth unknown')

    def test_every_retained_target_matches_its_maintained_reading(self):
        source = SOURCE.parents[2] / 'surname-research/indexes/glasgow-newspaper-review.json'
        rows = json.loads(source.read_text())['rows']
        retained = [r for r in rows if r['status'] in ('confirmed surname', 'place study')]
        targets = load_targets()
        self.assertEqual(set(targets), {str(r['image_id']) for r in retained})
        for item in retained:
            with self.subTest(image_id=item['image_id']):
                self.assertEqual(targets[str(item['image_id'])]['reading_sha256'], reading_hash(item))
                self.assertTrue(target_for(item)['people'])

    def test_card_target_override_remains_documentary_and_candidate_dates_do_not_leak(self):
        item = row(
            card_target=target(),
            profile_ids=['Glasgow-1781'],
            profile_matches=[{
                'profile_id': 'Glasgow-1781', 'confidence': 'possible',
                'role': 'candidate', 'basis': 'Profile gives a birth estimate c. 1802.',
                'birth_date': 'c. 1802',
            }],
        )
        result = target_for(item)
        self.assertEqual(result['people'][0]['name'], 'Rev. Adam Glasgow')
        self.assertEqual(result['people'][0]['birth_label'], 'Birth unknown')
        self.assertEqual(result['people'][0]['birth_basis'], '')
        self.assertNotIn('1802', str(result['people'][0]))

    def test_approximate_birth_label_requires_a_basis(self):
        item = row(card_target=target(people=[{
            'name': 'Recorded person', 'place': 'Place not stated',
            'birth_label': 'by c. 1800', 'birth_basis': '', 'details': [],
        }]))
        with self.assertRaisesRegex(ValueError, 'basis'):
            target_for(item)

        item['card_target']['people'][0]['birth_basis'] = 'Estimated from the source chronology.'
        self.assertEqual(target_for(item)['people'][0]['birth_label'], 'by c. 1800')

    def test_relationship_prose_and_candidate_roles_do_not_create_relationship_tags(self):
        item = row(
            reading='The notice names a possible father and a candidate wife elsewhere.',
            assessment='No kinship is inferred; these are candidate descriptions only.',
            profile_ids=['Glasgow-1'],
            profile_matches=[{'profile_id': 'Glasgow-1', 'role': 'possible father and wife',
                              'basis': 'No relationship is proved.'}],
            card_target=target(evidence_tags=['occupation']),
        )
        tags = evidence_tags(item)
        self.assertIn('occupation', tags)
        self.assertNotIn('relationships', tags)
        self.assertFalse(tags & {'spouse', 'parent-child', 'siblings', 'other-kin'})

    def test_explicit_curated_kinship_tag_adds_relationship_aggregate(self):
        for tag in ('spouse', 'parent-child', 'siblings', 'other-kin'):
            with self.subTest(tag=tag):
                item = row(card_target=target(evidence_tags=[tag]))
                tags = evidence_tags(item)
                self.assertIn(tag, tags)
                self.assertIn('relationships', tags)

    def test_identity_defaults_to_possible_unless_curated_grade_is_explicit(self):
        item = row(profile_ids=['Glasgow-3444'])
        self.assertEqual(identity_status(item), 'possible')
        item['profile_matches'] = [{
            'profile_id': 'Glasgow-3444', 'role': 'strong family possibility',
            'basis': 'Strong-sounding prose is not a confidence grade.',
        }]
        self.assertEqual(identity_status(item), 'possible')
        item['profile_matches'][0]['confidence'] = 'probable'
        self.assertEqual(identity_status(item), 'probable')
        self.assertEqual(identity_status(row()), 'unassigned')

    def test_documentary_card_target_text_is_html_escaped(self):
        item = row(card_target=target(
            people=[{
                'name': 'Rev. Adam <Glasgow>',
                'place': 'Townsend & Rosemary-street',
                'birth_label': 'by c. 1810',
                'birth_basis': 'Estimate <basis> & source',
                'details': ['<speaker> & minister'],
            }],
            record_type='<meeting report>',
        ))
        html = newspaper_card(item, {}, WEB)
        self.assertIn('Rev. Adam &lt;Glasgow&gt;', html)
        self.assertIn('Townsend &amp; Rosemary-street', html)
        self.assertIn('by c. 1810', html)
        self.assertIn('Estimate &lt;basis&gt; &amp; source', html)
        self.assertIn('&lt;speaker&gt; &amp; minister', html)
        self.assertIn('&lt;meeting report&gt;', html)
        self.assertNotIn('<meeting report>', html)


if __name__ == '__main__':
    unittest.main()
