import unittest
from bs4 import BeautifulSoup
from tools.statistics_journeys import normalise_flows, render_journeys_story


class StatisticsJourneyTests(unittest.TestCase):
    def test_duplicate_pairs_merge_and_invalid_rows_do_not_count(self):
        rows = [['Ireland', 'Canada', 3], ['Ireland', 'Canada', 2],
                ['Scotland', 'United States', 7], ['Ireland', 'Ireland', 9],
                ['Ireland', 'Canada', True], ['Ireland', 'Canada', -1]]
        self.assertEqual(normalise_flows(rows),
                         [('Scotland', 'United States', 7), ('Ireland', 'Canada', 5)])

    def test_hero_corridors_and_endpoints_use_the_whole_cohort(self):
        rows = [['Ireland', 'United States', 10], ['Scotland', 'United States', 5],
                ['Ireland', 'Canada', 5]]
        soup = BeautifulSoup(render_journeys_story(rows, '<div id="original-chart">chart</div>', outline=[]), 'html.parser')
        self.assertEqual(soup.select_one('.statistics-story-metrics strong').text, '20')
        self.assertEqual(len(soup.select('.statistics-journeys-corridor')), 3)
        self.assertIn('50.0%', soup.select_one('.statistics-journeys-corridor').text)
        self.assertEqual(soup.select_one('#original-chart').text, 'chart')
        self.assertEqual([node.text for node in soup.select('.statistics-journeys-endpoints strong')],
                         ['Ireland', 'United States'])
        self.assertIn('not reconstructed travel routes', soup.select_one('.statistics-journeys-geography').text)

    def test_map_is_bounded_but_unknown_regions_remain_in_the_totals(self):
        rows = [['Unlocated region', 'United States', 10],
                ['Ireland', 'Canada', 5]]
        soup = BeautifulSoup(render_journeys_story(rows, outline=[]), 'html.parser')
        self.assertEqual(soup.select_one('.statistics-story-metrics strong').text, '15')
        self.assertEqual(len(soup.select('.statistics-journeys-arc')), 1)
        self.assertIn('Unlocated region', soup.select_one('.statistics-journeys-corridors').text)
        empty = BeautifulSoup(render_journeys_story([], outline=[]), 'html.parser')
        self.assertEqual(empty.select_one('.statistics-story-metrics strong').text, '0')
        self.assertIn('No mappable', empty.text)
