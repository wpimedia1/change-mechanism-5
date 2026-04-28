from unittest.mock import patch

import pytest

import seo_tool


def fake_getaddrinfo_public(host, port):
    return [
        (2, 1, 6, '', ('93.184.216.34', 0)),
    ]


def fake_getaddrinfo_private(host, port):
    return [
        (2, 1, 6, '', ('127.0.0.1', 0)),
    ]


def fake_getaddrinfo_mixed(host, port):
    return [
        (2, 1, 6, '', ('93.184.216.34', 0)),
        (2, 1, 6, '', ('127.0.0.1', 0)),
    ]


class DummyResponse:
    def __init__(self, body: bytes, final_url: str = 'https://example.com', content_type: str = 'text/html'):
        self._body = body
        self._final_url = final_url
        self.headers = {'Content-Type': content_type}

    def read(self, size=-1):
        if size is None or size < 0:
            return self._body
        return self._body[:size]

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@patch('seo_tool.socket.getaddrinfo', side_effect=fake_getaddrinfo_public)
def test_is_safe_url_allows_public_domain(_mock_resolve):
    assert seo_tool.is_safe_url('https://example.com/path') is True


@patch('seo_tool.socket.getaddrinfo', side_effect=fake_getaddrinfo_private)
def test_is_safe_url_rejects_private_resolution(_mock_resolve):
    assert seo_tool.is_safe_url('https://evil.test') is False


@patch('seo_tool.socket.getaddrinfo', side_effect=fake_getaddrinfo_mixed)
def test_is_safe_url_rejects_mixed_public_private_resolution(_mock_resolve):
    assert seo_tool.is_safe_url('https://mixed.test') is False


def test_is_safe_url_rejects_credentials():
    assert seo_tool.is_safe_url('https://user:pass@example.com') is False


@patch('seo_tool.socket.getaddrinfo', side_effect=fake_getaddrinfo_public)
def test_sanitize_url_adds_scheme_and_strips_fragment(_mock_resolve):
    cleaned = seo_tool.sanitize_url('example.com/path#frag')
    assert cleaned == 'https://example.com/path'


@patch('seo_tool.sanitize_url', return_value='https://example.com')
@patch('seo_tool.is_safe_url', return_value=True)
@patch('seo_tool.urllib.request.urlopen')
def test_fetch_html_rejects_non_html(_mock_open, _mock_safe, _mock_sanitize):
    _mock_open.return_value = DummyResponse(b'data', content_type='application/octet-stream')
    with pytest.raises(Exception, match='Unsupported content type'):
        seo_tool.fetch_html('https://example.com')


@patch('seo_tool.sanitize_url', return_value='https://example.com')
@patch('seo_tool.is_safe_url', side_effect=[False])
@patch('seo_tool.urllib.request.urlopen')
def test_fetch_html_blocks_unsafe_redirect(_mock_open, _mock_safe, _mock_sanitize):
    _mock_open.return_value = DummyResponse(b'<html></html>', final_url='http://127.0.0.1/admin')
    with pytest.raises(Exception, match='Unsafe redirect target blocked'):
        seo_tool.fetch_html('https://example.com')
