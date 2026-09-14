import json
import unittest
from unittest.mock import MagicMock, patch

import requests
import transit


class TransitTests(unittest.TestCase):
    def response(self, body):
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [body]
        return response

    @patch.dict('os.environ', {'SUPABASE_URL': 'https://fixture.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'fixture'})
    def test_payload_uses_post_with_bounded_timeout_and_body(self):
        with patch.object(requests, 'post', return_value=self.response(b'{"results":[],"has_more":false}')) as post:
            self.assertEqual(transit.search(1.3, 103.8, 0.2), {'results': [], 'has_more': False})
        args, kwargs = post.call_args
        self.assertNotIn('1.3', args[0])
        self.assertEqual(kwargs['json'], {'p_lat': 1.3, 'p_lon': 103.8, 'p_radius': 0.2})
        self.assertEqual(kwargs['timeout'], (2, 5))
        self.assertTrue(kwargs['stream'])
        post.assert_called_once()

    @patch.dict('os.environ', {'SUPABASE_URL': 'https://fixture.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'fixture'})
    def test_oversized_invalid_and_failed_responses_are_safe_errors(self):
        for body in [b'x'*(transit.MAX_RESPONSE_BYTES+1), b'invalid json', b'null']:
            with self.subTest(length=len(body)), patch.object(requests, 'post', return_value=self.response(body)):
                with self.assertRaises(transit.TransitUnavailable):
                    transit.search(1.3, 103.8, 0.2)
        with patch.object(requests, 'post', side_effect=requests.Timeout('private-key-and-input')) as post:
            with self.assertRaises(transit.TransitUnavailable) as error:
                transit.search(1.3, 103.8, 0.2)
            self.assertNotIn('private-key', str(error.exception))
            post.assert_called_once()

    def test_unbounded_or_malformed_results_are_rejected(self):
        for payload in [{'results': [{}]*201, 'has_more': True}, {'results': [], 'has_more': 1},
                        {'results': [{}], 'has_more': False}, {'results': {}, 'has_more': False}]:
            with patch.object(transit, '_rpc', return_value=payload):
                with self.assertRaises(transit.TransitUnavailable):
                    transit.search(1.3, 103.8, 0.2)

    def test_fact_cache_does_not_repeat_database_reads(self):
        transit.facts.cache_clear()
        payload = {key: {} for key in ['smrt', 'sbst', 'tts', 'gas']}
        payload.update({key+'_len': 1 for key in ['smrt', 'sbst', 'tts', 'gas']})
        with patch.object(transit, '_rpc', return_value=payload) as query:
            self.assertEqual(transit.facts(), payload)
            self.assertEqual(transit.facts(), payload)
            query.assert_called_once_with('bus_facts', {})
        transit.facts.cache_clear()
