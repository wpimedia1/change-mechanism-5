from unittest.mock import patch

import serp_agent


def test_resolve_prompt_success():
    prompt = serp_agent.resolve_prompt("Top 50 Page Analysis")
    assert "Analyze the top ranking pages" in prompt


def test_resolve_prompt_error():
    try:
        serp_agent.resolve_prompt("does-not-exist")
    except ValueError as exc:
        assert "Unknown prompt" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


@patch('serp_agent.call_gemini_api', return_value='AI RESULT')
@patch('serp_agent.universal_scraper', side_effect=['scrape-1', 'scrape-2'])
@patch('serp_agent.sanitize_url', side_effect=['https://a.com', 'https://b.com'])
@patch('serp_agent.fetch_serp_urls', return_value=['a.com', 'b.com'])
def test_run_agent_happy_path(mock_fetch, mock_sanitize, mock_scrape, mock_gemini):
    config = serp_agent.AgentConfig(
        keyword='test keyword',
        prompt_name='Top 50 Page Analysis',
        max_urls=2,
        delay_seconds=0,
        include_pagespeed=False,
        gemini_key='key',
        pagespeed_key=None,
    )

    output = serp_agent.run_agent(config)

    assert output['urls_found'] == 2
    assert len(output['results']) == 2
    assert output['gemini_output'] == 'AI RESULT'
    assert 'TASK:' in output['master_prompt']
    mock_fetch.assert_called_once()
    mock_gemini.assert_called_once()


@patch('serp_agent.get_pagespeed_insights', return_value='ps-data')
@patch('serp_agent.universal_scraper', return_value='scrape')
@patch('serp_agent.sanitize_url', return_value='https://a.com')
@patch('serp_agent.fetch_serp_urls', return_value=['a.com'])
def test_run_agent_with_pagespeed(mock_fetch, _mock_sanitize, _mock_scrape, mock_pagespeed):
    config = serp_agent.AgentConfig(
        keyword='kw',
        prompt_name='Top 50 Page Analysis',
        max_urls=1,
        delay_seconds=0,
        include_pagespeed=True,
        gemini_key=None,
        pagespeed_key='pg',
    )

    output = serp_agent.run_agent(config)

    assert output['results'][0]['pagespeed'] == 'ps-data'
    mock_pagespeed.assert_called_once_with('https://a.com', 'pg')


def test_parse_args_validation():
    try:
        serp_agent.parse_args(['--keyword', 'abc', '--max-urls', '0'])
    except ValueError as exc:
        assert '>= 1' in str(exc)
    else:
        raise AssertionError('Expected ValueError for max-urls')
