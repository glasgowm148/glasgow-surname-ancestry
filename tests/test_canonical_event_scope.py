import unittest

from tools.ingest_canonical_records import reviewed_event_rows


class CanonicalEventScopeTests(unittest.TestCase):
    def test_comparison_is_not_an_established_personal_event_and_dates_survive(self):
        event = {'p': 'fictional-1', 'source_url': 'https://example.org/entry', 'kind': 'personal',
                 'event_type': 'baptism', 'date': '1800-02-03', 'year': 1800, 'note': 'Earlier attribution'}
        source = {'source_url': event['source_url'], 'profiles': {'Fictional-1': {
            'timeline_group': 'Possible family records', 'role': 'Research comparison only: child/adult identity unproved'}}}
        result = reviewed_event_rows([event], [source])[0]
        self.assertEqual(result['kind'], 'unresolved')
        self.assertTrue(result['research'])
        self.assertEqual(result['date'], event['date'])
        self.assertEqual(result['source_scope_correction']['previous'], event)
        self.assertEqual(reviewed_event_rows([result], [source]), [result])

    def test_literal_parent_and_unrelated_events_are_retained(self):
        events = [{'p': 'fictional-1', 'source_url': 'https://example.org/entry', 'kind': 'family'},
                  {'p': 'fictional-2', 'source_url': 'https://example.org/other', 'kind': 'personal'}]
        source = {'source_url': events[0]['source_url'], 'profiles': {'fictional-1': {
            'timeline_group': 'Family records', 'role': 'Named father'}}}
        self.assertEqual(reviewed_event_rows(events, [source]), events)

    def test_birth_only_index_is_not_rendered_as_baptism(self):
        event = {'p': 'fictional-1', 'source_url': 'https://example.org/entry', 'event_type': 'baptism'}
        source = {'source_url': event['source_url'], 'person': 'Fictional Example',
                  'event_role': 'child born (indexed birth)', 'note': 'Indexed birth; no baptism date',
                  'profiles': {'fictional-1': {'timeline_group': 'Life events', 'role': 'Indexed child'}}}
        self.assertEqual(reviewed_event_rows([event], [source])[0]['event_type'], 'birth_index')
