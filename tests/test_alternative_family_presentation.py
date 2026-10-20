import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
from tools import repair_person_hierarchy as renderer
from tools import relationship_probability as probabilities


class AlternativeFamilyPresentationTests(unittest.TestCase):
    def test_prior_probable_father_is_separate_from_current_parents(self):
        old = dict(id='Old-1', name='Earlier father', relationship='father', status='probable',
                   display='alternative', lifecycle='alternative', status_label='New probable father,76%',
                   probability={'value': .76}, reason='Earlier evidence remains inspectable.')
        current = dict(id='New-1', name='Selected father', relationship='father', status='probable',
                       lifecycle='current', status_label='Probable father · 82%', probability={'value': .82})
        dossier = {'relationships': {'parents': [old, current]}}
        estimates = {('child-1', relative, 'father'): dict(percent=percent, assessment_status='probable',
                     basis='Reviewed evidence', reviewed='2026-10-20')
                     for relative, percent in [('old-1', 76), ('new-1', 82)]}
        def profile(pid):
            return (dossier if pid=='Child-1' else {}, {}, {})
        with patch.object(renderer, '_profile_data', side_effect=profile), \
             patch.dict('sys.modules', {'relationship_probability': probabilities}), \
             patch.object(probabilities, 'reviewed_estimates', return_value=estimates):
            soup = BeautifulSoup(renderer._family_html('Child-1', dossier, {}, {}, {}, {}), 'html.parser')
        parents = soup.select_one('[data-group="parents"]')
        self.assertEqual(len(parents.select('tbody tr')), 1)
        self.assertIn('Selected father', parents.get_text())
        self.assertNotIn('Earlier father', parents.get_text())
        earlier = soup.select_one('[data-group="alternative-parents"]')
        self.assertIn('Earlier and alternative parents', earlier.get_text())
        self.assertIn('Earlier father', earlier.get_text())
        self.assertIn('76%', earlier.get_text())
        self.assertIn('Earlier or alternative father', earlier.get_text())
        self.assertIn('Earlier evidence remains inspectable.', earlier.get_text())
        self.assertNotIn('New probable father', earlier.get_text())

    def test_historical_grade_is_not_overwritten_by_current_pair_assessment(self):
        old = {'id': 'Father-1', 'lifecycle': 'historical', 'status': 'possible', 'probability': {'value': .48}}
        with patch.object(renderer, '_shared_relationship_assessment') as current:
            self.assertEqual(renderer._assessed_relation('Child-1', old, 'parents'), old)
            current.assert_not_called()
