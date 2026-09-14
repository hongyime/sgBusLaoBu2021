import contextlib
import io
import unittest
from unittest.mock import patch

import main
import transit


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.client = main.app.test_client()
        self.form = {'latitude1': '1.3', 'longitude1': '103.8', 'slider': '0.2'}

    def test_rejects_invalid_inputs_before_querying(self):
        invalid = [('latitude1', 'nan'), ('latitude1', 'inf'), ('latitude1', '91'),
                   ('longitude1', '-181'), ('longitude1', '-inf'), ('slider', 'nan'),
                   ('slider', 'inf'), ('slider', '0.09'), ('slider', '1.01'), ('longitude1', '')]
        with patch.object(transit, 'search') as query:
            for field, value in invalid:
                with self.subTest(field=field, value=value):
                    response = self.client.post('/findabus', data=self.form | {field: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b'role="alert"', response.data)
                    query.assert_not_called()

    def test_valid_search_makes_one_query_without_saving_or_logging_location(self):
        output = io.StringIO()
        with patch.object(transit, 'search', return_value={'results': [], 'has_more': False}) as query, \
             patch('sqlite3.connect') as database, patch('pathlib.Path.write_text') as write, \
             contextlib.redirect_stdout(output):
            response = self.client.post('/findabus', data=self.form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No MRT Stations Found Nearby', response.data)
        query.assert_called_once_with(1.3, 103.8, 0.2)
        database.assert_not_called()
        write.assert_not_called()
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn(b'console.log(', response.data)
        self.assertTrue(response.cache_control.private)
        self.assertTrue(response.cache_control.no_store)
        self.assertNotIn('Vercel-CDN-Cache-Control', response.headers)

    def test_geolocation_and_radius_endpoints(self):
        with patch.object(transit, 'search', return_value={'results': [], 'has_more': False}):
            for radius in ['0.1', '1.0']:
                response = self.client.post('/findabus', data={'latitude': '1.3', 'longitude': '103.8', 'slider': radius})
                self.assertEqual(response.status_code, 200)

    def test_unavailable_database_is_not_presented_as_no_results(self):
        with patch.object(transit, 'search', side_effect=transit.TransitUnavailable('private detail')):
            response = self.client.post('/findabus', data=self.form)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'temporarily unavailable', response.data)
        self.assertNotIn(b'private detail', response.data)
        self.assertTrue(response.cache_control.no_store)

    def test_truncation_is_visible(self):
        with patch.object(transit, 'search', return_value={'results': [], 'has_more': True}):
            response = self.client.post('/findabus', data=self.form)
        self.assertIn(b'Showing the closest 200 routes', response.data)

    def test_static_pages_need_no_database_and_are_cdn_cacheable(self):
        with patch.object(transit, '_rpc') as query:
            for path in ['/', '/help', '/getyourlocation', '/static/style.css']:
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['Vercel-CDN-Cache-Control'], 'public, max-age=86400')
                response.close()
            query.assert_not_called()

    def test_history_remains_private_and_debugger_disabled(self):
        self.assertFalse(main.app.debug)
        for path, status in [('/coordinates', 410), ('/static/coordinates.json', 404),
                             ('/static/%2e/coordinates.json', 404),
                             ('/static/../data/txt/coordinates.txt', 404)]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, status)
            self.assertTrue(response.cache_control.no_store)
            self.assertNotIn(b'maps.googleapis.com', response.data)

    def test_oversized_forms_are_rejected(self):
        response = self.client.post('/findabus', data={'latitude1': '1'*5000})
        self.assertEqual(response.status_code, 413)


if __name__ == '__main__':
    unittest.main()
