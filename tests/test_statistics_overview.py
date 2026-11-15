import unittest

from bs4 import BeautifulSoup
from tools import statistics_overview as overview


class StatisticsOverviewTests(unittest.TestCase):
    def test_coordinates_are_deduplicated_and_private_living_rows_excluded(self):
        people = [
            {'catalogue_id': 'a', 'records': [{'latitude': 55, 'longitude': -3}] * 2},
            {'catalogue_id': 'b', 'records': [{'latitude': 55, 'longitude': -3}]},
            {'catalogue_id': 'c', 'records': [{'latitude': 40, 'longitude': -75}]},
            {'catalogue_id': 'hidden', 'likely_living': True,
             'records': [{'latitude': 55, 'longitude': -3}]},
            {'catalogue_id': 'invalid', 'records': [
                {'latitude': True, 'longitude': 0}, {'latitude': 91, 'longitude': 0},
                {'latitude': 'nan', 'longitude': 0}]},
        ]
        cells, mapped = overview.record_cells(people)
        self.assertEqual(mapped, 3)
        self.assertEqual(sorted(cell['count'] for cell in cells), [1, 2])
        html = overview.render_dashboard_overview('', people, [], outline=[])
        soup = BeautifulSoup(html, 'html.parser')
        radii = sorted(float(node['r']) for node in soup.select('.statistics-map-dot'))
        self.assertAlmostEqual((radii[1] / radii[0]) ** 2, 2, places=2)

    def test_empty_periods_and_root_denominator_are_preserved(self):
        people = [
            {'catalogue_id': 'a', 'birth': 'c. 1299'},
            {'catalogue_id': 'b', 'birth': 'before 1450'},
            {'catalogue_id': 'c', 'birth': ''},
        ]
        index = [{'id': 'A', 'family_root': {'id': 'root'}},
                 {'id': 'outside', 'family_root': {'id': 'root'}}]
        soup = BeautifulSoup(overview.render_dashboard_overview('', people, index, outline=[]), 'html.parser')
        self.assertEqual([node.text for node in soup.select('.statistics-era-label')],
                         ['1200s', '1300s', '1400s'])
        self.assertEqual([node.text for node in soup.select('.statistics-era-count')], ['1', '0', '1'])
        self.assertEqual(soup.select_one('.statistics-coverage-total').text, '1 / 3')
        self.assertEqual(soup.select_one('.statistics-coverage-percent').text, '33.3%')
        self.assertFalse(soup.select('.statistics-map-land'))

    def test_geographic_marks_stay_bounded_without_losing_people(self):
        people = [{'catalogue_id': str(index), 'records': [
            {'latitude': -87.5 + 5 * (index // 72), 'longitude': -177.5 + 5 * (index % 72)}]}
                  for index in range(576)]
        cells, mapped = overview.record_cells(people, max_cells=100)
        self.assertLessEqual(len(cells), 100)
        self.assertEqual(mapped, 576)
        self.assertEqual(sum(cell['count'] for cell in cells), 576)
