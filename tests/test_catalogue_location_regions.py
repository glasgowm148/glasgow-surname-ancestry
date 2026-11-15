import unittest
from unittest.mock import patch

from tools import catalogue_location_regions as regions


class CatalogueLocationRegionsTests(unittest.TestCase):
    def setUp(self):
        self.held = patch.object(regions, '_held_labels', return_value={})
        self.gaz = patch.object(regions, '_gazetteer', return_value={
            'glasgow': {'name': 'Glasgow', 'county': 'Lanarkshire', 'country': 'Scotland', 'provenance': 'curated'},
            'cookstown': {'name': 'Cookstown', 'county': 'Tyrone', 'country': 'Ireland', 'provenance': 'curated'},
        })
        self.held.start()
        self.gaz.start()
        self.addCleanup(self.held.stop)
        self.addCleanup(self.gaz.stop)

    def test_explicit_country_and_county_components(self):
        for place, expected in [
            ('Kilbirnie,Ayr,Scotland', 'Scotland'),
            ('Kensington, London, England, W', 'England'),
            ('Belfast, Northern Ireland', 'Ireland'),
            ('Jersey City, New Jersey, USA', 'United States'),
            ('Dunedin, Nz', 'New Zealand'),
            ('Rome, Italy', 'Italy'),
            ('Preston, Halifax, Nova Scotia, Canada', 'Canada'),
            ('Shotts, Lanarkshire', 'Scotland'),
            ('22 Wellwood Road, Goodmayes, Essex', 'England'),
            ('John St, Newbridge Co Kildare', 'Ireland'),
        ]:
            with self.subTest(place=place):
                self.assertEqual(regions.region_for_location(place), expected)

    def test_reviewed_distinctive_towns_inside_addresses(self):
        for place, expected in [
            ('Kensington, London', 'England'),
            ('162 Bellingdon Road, Chesham, Bucks', 'England'),
            ('101 Starcliffe Street, Great Lever, Bolton, Lancs', 'England'),
            ('279 Scotswood Road Newcastle On Tyne', 'England'),
            ('106 Vine Street Gateshead On Tyne', 'England'),
            ('30 Robert Hall St Derby St Salford Manchester', 'England'),
            ('25 Nansen Rd Sparkhill Birmingham', 'England'),
            ('17 King Street, Stirling', 'Scotland'),
            ('25 Daleneny Street, Leith', 'Scotland'),
            ('22 Crown Square, Prestonpans', 'Scotland'),
            ('205 Main St, Shettelston Glasgow', 'Scotland'),
            ('London Road United Presbyterian, Glasgow', 'Scotland'),
        ]:
            with self.subTest(place=place):
                self.assertEqual(regions.region_for_location(place), expected)

    def test_reviewed_residual_named_towns_and_historic_counties(self):
        for place, expected in [
            ('17 Sandown St Ardwick Manchester', 'England'),
            ('Albert Terr Esh Winning Durham', 'England'),
            ('48 Stansfield St Monkwearmouth', 'England'),
            ('3 Jubilee Terrace Hamsterley Colliery Ebchester', 'England'),
            ('26 Hindpool Road Barrow In Furness', 'England'),
            ('3 Reads Avenue Blackpool', 'England'),
            ('19 Brownlow Street, Haggerston', 'England'),
            ('1 Percy Road, Kilburn, Willesden N W', 'England'),
            ('High Field House Ruhydfro Pontardawe', 'Wales'),
            ('Mintholme Rhayader', 'Wales'),
            ('Rosebank Cottage, Leadhills', 'Scotland'),
            ('Lawrence Haddington', 'Scotland'),
            ('Barony, Lanark', 'Scotland'),
            ('Newry', 'Ireland'), ('Derryloran', 'Ireland'),
            ('Stewartstown', 'Ireland'),
            ('Henderson Ky.', 'United States'),
            ('Sandusky City, Ohio', 'United States'),
            ('Jacksonville Fla', 'United States'),
            ('Royal Victoria Hospital, Hound Near Southampton', 'England'),
            ('Elephant & Castle, 1 Merchant St', 'England'),
            ('Ogonaloe', 'Ireland'),
            ('Tyanee', 'Ireland'),
        ]:
            with self.subTest(place=place):
                self.assertEqual(regions.region_for_location(place), expected)

    def test_placeholders_collection_titles_names_and_ambiguous_streets_excluded(self):
        for place in [
            '', None, 'Bath', 'Lee', 'Location not supplied — profile holding point',
            'Non-Subscribing Presbyterian Church of Ireland',
            'Scotland Births and Baptisms records', 'England census',
            'John Glasgow', 'Glasgow surname records',
            '64 Victor Street', '23 Eastburne Avenue, Walker',
            '141 Boulton Road, Handsworth', '175 Helmsley Rd N Cle',
            '10 London Road',
        ]:
            with self.subTest(place=place):
                self.assertEqual(regions.region_for_location(place), '')

    def test_contradictions_and_exact_held_labels(self):
        self.assertEqual(regions.region_for_location('Denbighshire, England'), '')
        self.assertEqual(regions.region_for_location('Glasgow, Scotland, England'), '')
        with patch.object(regions, '_held_labels', return_value={'exact old village': {'Scotland'}}):
            region, basis = regions.classify_location('Exact Old Village')
            self.assertEqual(region, 'Scotland')
            self.assertIn('Exact geographic record_location', basis)
            self.assertEqual(regions.region_for_location('near Exact Old Village'), '')
        with patch.object(regions, '_held_labels', return_value={'exact old village': {'Scotland', 'England'}}):
            self.assertEqual(regions.region_for_location('Exact Old Village'), '')

    def test_gazetteer_uses_whole_components_and_provides_basis(self):
        region, basis = regions.classify_location('Drum, Cookstown')
        self.assertEqual(region, 'Ireland')
        self.assertIn('Cookstown / Tyrone / Ireland', basis)
        self.assertEqual(regions.region_for_location('Cookstown Street'), '')
