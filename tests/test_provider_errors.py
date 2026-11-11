import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from providers import Provider, post_json


class ProviderErrorTests(unittest.TestCase):
    def error_text(self, body):
        stream = io.BytesIO(body)
        error = urllib.error.HTTPError('https://example.invalid', 400, 'Bad Request', {}, stream)
        with patch('providers.urllib.request.urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                post_json('https://example.invalid', {}, {})
        self.assertTrue(stream.closed)
        return str(caught.exception)

    def test_google_reason_without_sensitive_body(self):
        body = {'error': {'status': 'INVALID_ARGUMENT', 'message': 'private request text SECRET',
                          'details': [{'reason': 'API_KEY_INVALID', 'metadata': {'key': 'SECRET'}}]}}
        text = self.error_text(json.dumps(body).encode())
        self.assertIn('HTTP 400', text)
        self.assertIn('API_KEY_INVALID', text)
        self.assertNotIn('SECRET', text)
        self.assertNotIn('private request', text)

    def test_list_error_and_known_message(self):
        text = self.error_text(json.dumps([{'error': {'message': 'API key not valid. SECRET'}}]).encode())
        self.assertIn('API_KEY_INVALID', text)
        self.assertNotIn('SECRET', text)

    def test_google_auth_key_error(self):
        body = {'error': {'status': 'INVALID_ARGUMENT', 'message': 'Invalid Auth key.'}}
        text = self.error_text(json.dumps(body).encode())
        self.assertIn('API_KEY_INVALID', text)

    def test_non_json_response_keeps_http_status(self):
        text = self.error_text(b'<html>SECRET</html>')
        self.assertIn('HTTP 400', text)
        self.assertNotIn('SECRET', text)

    def test_untrusted_status_is_not_logged(self):
        text = self.error_text(json.dumps({'error': {'status': 'private key=SECRET'}}).encode())
        self.assertNotIn('SECRET', text)


class OutputLimitTests(unittest.TestCase):
    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'dummy', 'MAX_OUTPUT_TOKENS': '2048'})
    @patch('providers.post_json')
    def test_output_limit_sent_to_provider(self, post):
        post.return_value = {'choices': [{'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': 'stop'}]}
        Provider('openrouter', 'test-model').complete([{'role': 'user', 'content': 'test'}], [])
        self.assertEqual(post.call_args.args[2]['max_tokens'], 2048)

    def test_invalid_limit_is_rejected(self):
        for value in ('0', '-1', 'not-an-integer'):
            with self.subTest(value=value), patch.dict(os.environ, {'OPENROUTER_API_KEY': 'dummy', 'MAX_OUTPUT_TOKENS': value}):
                with self.assertRaises(ValueError):
                    Provider('openrouter', 'test-model')


class JsonModeTests(unittest.TestCase):
    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'dummy'})
    @patch('providers.post_json')
    def test_judge_can_request_json_output(self, post):
        post.return_value = {'choices': [{'message': {'role': 'assistant', 'content': '{}'}, 'finish_reason': 'stop'}]}
        Provider('openrouter', 'test-model', json_mode=True).complete([{'role': 'user', 'content': 'Return JSON'}], [])
        self.assertEqual(post.call_args.args[2]['response_format'], {'type': 'json_object'})

    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'dummy'})
    @patch('providers.post_json')
    def test_agent_output_format_is_unchanged(self, post):
        post.return_value = {'choices': [{'message': {'role': 'assistant', 'content': 'answer'}, 'finish_reason': 'stop'}]}
        Provider('openrouter', 'test-model').complete([{'role': 'user', 'content': 'hello'}], [])
        self.assertNotIn('response_format', post.call_args.args[2])
