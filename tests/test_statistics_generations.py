import unittest

from bs4 import BeautifulSoup

from tools.statistics_generations import render_generations_story
from tools.statistics_overview import birth_bins


class StatisticsGenerationsTests(unittest.TestCase):
    def render(self, people, chart=''):
        return BeautifulSoup(render_generations_story(people, chart), 'html.parser')

    def test_public_denominator_coverage_and_first_shown_year(self):
        people = [
            {'birth': 'c. 1799', 'gender': 'Male'},
            {'birth': 'before 1850', 'gender': 'Female'},
            {'birth': '1890–1901', 'gender': 'Female'},
            {'birth': 'after 1801', 'gender': 'Male'},
            {'birth': 'unknown'},
            {'birth': '999'},
            {'birth': '2000', 'likely_living': True},
        ]
        soup = self.render(people)
        metrics = {n['data-metric']: n.get_text(' ', strip=True)
                   for n in soup.select('[data-metric]')}
        self.assertTrue(metrics['dated'].startswith('4 '))
        self.assertTrue(metrics['public'].startswith('6 '))
        self.assertIn('75.0%', metrics['peak'])
        self.assertIn('1800s', metrics['peak'])
        self.assertEqual(soup.select_one('.statistics-generations-dated')['data-count'], '4')
        self.assertEqual(soup.select_one('.statistics-generations-undated')['data-count'], '2')
        self.assertAlmostEqual(float(soup.select_one('.statistics-generations-dated')['style'].split(':')[1][:-1]), 100 * 4 / 6)
        self.assertAlmostEqual(float(soup.select_one('.statistics-generations-undated')['style'].split(':')[1][:-1]), 100 * 2 / 6)
        self.assertIn('research confidence', soup.select_one('.statistics-generations-coverage').text)

    def test_gender_stacks_match_source_bins_and_retain_empty_centuries(self):
        people = [
            {'birth': '1299', 'gender': 'Male'},
            {'birth': 'c. 1450', 'gender': 'Female'},
            {'birth': '1452', 'gender': ''},
            {'birth': '1453', 'gender': 'male'},
            {'birth': '1454', 'gender': 'Unknown'},
            {'birth': '1455', 'gender': 'Other'},
            {'birth': '1301', 'gender': 'Male', 'likely_living': True},
        ]
        soup = self.render(people)
        rows = soup.select('.statistics-generations-century')
        self.assertEqual([r['data-century'] for r in rows], ['12', '13', '14'])
        expected = birth_bins(people)
        for row in rows:
            stacks = row.select('rect[data-count]')
            self.assertEqual(sum(int(n['data-count']) for n in stacks), expected[int(row['data-century'])])
            self.assertEqual(int(row['data-total']), expected[int(row['data-century'])])
            self.assertEqual(len(stacks), 3)
            self.assertTrue(all(n.find('title') for n in stacks))
        self.assertEqual([int(n['data-count']) for n in rows[-1].select('rect[data-count]')], [0, 1, 4])
        self.assertTrue(all(float(n['width']) == 0 for n in rows[1].select('rect[data-count]')))
        self.assertEqual(sum(int(r['data-total']) for r in rows), 6)
        self.assertFalse(soup.select_one('.statistics-generations-values').has_attr('open'))
        self.assertIn('1300s', soup.select_one('.statistics-generations-values').text)

    def test_supplied_interactive_chart_is_embedded_once_and_unchanged(self):
        chart = '<article id="birth-centuries" data-values="keep"><button>View counts</button></article>'
        html = render_generations_story([{'birth': '1801'}], chart)
        self.assertIn(chart, html)
        soup = BeautifulSoup(html, 'html.parser')
        self.assertEqual(len(soup.select('#birth-centuries')), 1)
        self.assertIsNotNone(soup.select_one('.statistics-generations-hero .statistics-generations-chart #birth-centuries'))
        self.assertFalse(soup.select('.statistics-era-histogram'))
        self.assertEqual(len(soup.select('svg')), 1)
        self.assertFalse(soup.select_one('.statistics-generations-method').has_attr('open'))

    def test_empty_and_all_undated_states_have_no_invalid_geometry(self):
        for people in ([], [{'birth': ''}], [{'birth': '2000', 'likely_living': True}]):
            with self.subTest(people=people):
                html = render_generations_story(people)
                soup = BeautifulSoup(html, 'html.parser')
                self.assertIsNotNone(soup.select_one('.statistics-generations-empty'))
                self.assertFalse(soup.select('svg'))
                self.assertNotIn('nan', html.lower())
                self.assertNotIn('inf%', html.lower())
                self.assertEqual(soup.select_one('.statistics-generations-dated')['data-count'], '0')
        soup = self.render([{'birth': ''}])
        self.assertEqual(soup.select_one('.statistics-generations-undated')['style'], 'width:100.0000000000%')

    def test_tied_peak_selects_earliest_and_single_century_uses_full_scale(self):
        soup = self.render([{'birth': '1801'}, {'birth': '1701'}])
        self.assertIn('1700s', soup.select_one('[data-metric="peak"]').text)
        soup = self.render([{'birth': '1801', 'gender': 'Female'}])
        self.assertEqual(soup.select_one('.statistics-generations-gender-chart rect[data-gender="Female"]')['width'], '570.000000')
