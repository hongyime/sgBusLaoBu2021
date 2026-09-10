import contextlib
import io
import unittest
from unittest.mock import patch

import main


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.client = main.app.test_client()
        self.form = {'latitude1': '1.3', 'longitude1': '103.8', 'slider': '0.2'}
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        # Never read or mutate historical location records while testing.
        self.history_read = self.stack.enter_context(patch.object(main, 'import_json', return_value=[], create=True))
        self.history_write = self.stack.enter_context(patch.object(main, 'export_json', create=True))
        self.text_write = self.stack.enter_context(patch.object(main, 'coordinates_2_txt', create=True))
        self.stdout = self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def test_rejects_nonfinite_coordinates_and_radius_outside_the_ui_bounds_before_querying(self):
        invalid = [('latitude1', 'nan'), ('latitude1', 'inf'), ('latitude1', '91'),
                   ('longitude1', '-181'), ('longitude1', '-inf'), ('slider', 'nan'),
                   ('slider', 'inf'), ('slider', '0.09'), ('slider', '1.01')]
        with patch.object(main.stops, 'getbusstopdistance', return_value=[]) as query:
            for field, value in invalid:
                with self.subTest(field=field, value=value):
                    query.reset_mock()
                    response = self.client.post('/findabus', data=self.form | {field: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b'role="alert"', response.data)
                    query.assert_not_called()

    def test_valid_search_uses_coordinates_without_saving_or_logging_them(self):
        with patch.object(main.stops, 'getbusstopdistance', return_value=[]) as query:
            response = self.client.post('/findabus', data=self.form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No MRT Stations Found Nearby', response.data)
        self.assertEqual(query.call_args.kwargs, {'userlat': 1.3, 'userlon': 103.8, 'radius': 0.2})
        self.history_read.assert_not_called()
        self.history_write.assert_not_called()
        self.text_write.assert_not_called()
        self.assertEqual(self.stdout.getvalue(), '')

    def test_geolocation_inputs_and_radius_endpoints_remain_supported(self):
        with patch.object(main.stops, 'getbusstopdistance', return_value=[]):
            for radius in ['0.1', '1.0']:
                with self.subTest(radius=radius):
                    response = self.client.post('/findabus', data={'latitude': '1.3', 'longitude': '103.8', 'slider': radius})
                    self.assertEqual(response.status_code, 200)

    def test_personalized_search_response_is_not_shared_cached(self):
        with patch.object(main.stops, 'getbusstopdistance', return_value=[]):
            response = self.client.post('/findabus', data=self.form)
        self.assertTrue(response.cache_control.private)
        self.assertTrue(response.cache_control.no_store)
        self.assertFalse(response.cache_control.public)

    def test_only_forward_destinations_are_returned_without_per_pair_database_queries(self):
        nearby = [{'BusStopCode': 100, 'Description': 'Board here', 'ServiceNo': '10', 'Direction': 1,
                   'StopSequence': 5, 'Distance': 0.123, 'BusStopLat': 1.3, 'BusStopLon': 103.8}]
        destinations = [
            {'BusStopCode': 200, 'Description': 'Earlier Stn', 'ServiceNo': '10', 'Direction': 1, 'StopSequence': 3},
            {'BusStopCode': 300, 'Description': 'Later Stn', 'ServiceNo': '10', 'Direction': 1, 'StopSequence': 9},
        ]
        with patch.object(main.stops, 'getbusstopdistance', return_value=nearby), \
             patch.object(main, 'allmrtbusstops', destinations), \
             patch.object(main.stops, 'description_2_mrtname', side_effect=lambda description: (description, 'North-South')), \
             patch.object(main.stops, 'findstopsequence', side_effect=lambda command, **kw: {'100': 5, '200': 3, '300': 9}[kw['busstopcode']]) as sequence_query, \
             patch.object(main, 'render_template', return_value='results') as render:
            response = self.client.post('/findabus', data=self.form)
        self.assertEqual(response.status_code, 200)
        results = render.call_args.kwargs['data']
        self.assertEqual([(row['mrt_station'], row['numberofstops'], row['walkdistance']) for row in results], [('Later Stn', 4, '123m')])
        sequence_query.assert_not_called()

    def test_unmapped_station_does_not_crash_the_search(self):
        nearby = [{'BusStopCode': 100, 'Description': 'Board here', 'ServiceNo': '10', 'Direction': 1,
                   'StopSequence': 5, 'Distance': 0.123, 'BusStopLat': 1.3, 'BusStopLon': 103.8}]
        destination = {'BusStopCode': 300, 'Description': 'Unmapped Stn', 'ServiceNo': '10', 'Direction': 1, 'StopSequence': 9}
        with patch.object(main.stops, 'getbusstopdistance', return_value=nearby), \
             patch.object(main, 'allmrtbusstops', [destination]), \
             patch.object(main.stops, 'description_2_mrtname', return_value=None):
            response = self.client.post('/findabus', data=self.form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No MRT Stations Found Nearby', response.data)


if __name__ == '__main__':
    unittest.main()
