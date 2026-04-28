from unittest.mock import Mock, patch

import seo_tool


@patch('requests.post')
def test_gemini_key_sent_in_header_not_url(mock_post):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]
    }
    mock_post.return_value = response

    result = seo_tool.call_gemini_api('hello', 'SECRET_KEY')

    assert result == 'ok'
    args, kwargs = mock_post.call_args
    assert 'key=' not in args[0]
    assert kwargs['headers']['x-goog-api-key'] == 'SECRET_KEY'


@patch('requests.get')
@patch('seo_tool.sanitize_url', return_value='https://example.com')
def test_pagespeed_key_sent_in_header_not_url(_mock_sanitize, mock_get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        'lighthouseResult': {
            'audits': {
                'largest-contentful-paint': {'displayValue': '2.0 s'},
                'cumulative-layout-shift': {'displayValue': '0.01'},
                'speed-index': {'displayValue': '3.0 s'},
            }
        }
    }
    mock_get.return_value = response

    text = seo_tool.get_pagespeed_insights('https://example.com', 'PAGESPEED_SECRET')

    assert 'LIVE GOOGLE PAGESPEED DATA' in text
    args, kwargs = mock_get.call_args
    assert 'key=' not in args[0]
    assert kwargs['headers']['x-goog-api-key'] == 'PAGESPEED_SECRET'
    assert kwargs['params']['url'] == 'https://example.com'
