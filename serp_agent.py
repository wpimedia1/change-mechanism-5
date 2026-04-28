import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any

from seo_tool import (
    PROMPTS,
    SCRAPE_DELAY_SECONDS,
    call_gemini_api,
    fetch_serp_urls,
    get_pagespeed_insights,
    sanitize_url,
    universal_scraper,
)


@dataclass
class AgentConfig:
    keyword: str
    prompt_name: str
    max_urls: int
    delay_seconds: float
    include_pagespeed: bool
    gemini_key: str | None
    pagespeed_key: str | None


DEFAULT_PROMPT = "Top 50 Page Analysis"


def resolve_prompt(prompt_name: str) -> str:
    for category_prompts in PROMPTS.values():
        if prompt_name in category_prompts:
            return category_prompts[prompt_name]
    raise ValueError(f"Unknown prompt: {prompt_name}")


def build_master_prompt(prompt_template: str, keyword: str, scraped_context: str) -> str:
    final_prompt = prompt_template.replace("[keyword]", keyword)
    if scraped_context.strip():
        return (
            "Here is verified data pulled directly from live web scraping. "
            "Base your entire analysis on this specific data. "
            "Read it and analyze it thoroughly.\n\n"
            f"{scraped_context}\n\n"
            "Based on the exact data above, execute the following SEO task:\n"
            f"TASK: {final_prompt}"
        )
    return final_prompt


def run_agent(config: AgentConfig) -> dict[str, Any]:
    prompt_template = resolve_prompt(config.prompt_name)
    urls = fetch_serp_urls(config.keyword, num_results=config.max_urls)

    results: list[dict[str, Any]] = []
    scraped_context_parts: list[str] = []

    for idx, url in enumerate(urls):
        try:
            safe_url = sanitize_url(url)
            scrape_text = universal_scraper(safe_url)
            scraped_context_parts.append(scrape_text)

            item: dict[str, Any] = {
                "url": safe_url,
                "scrape": scrape_text,
            }

            if config.include_pagespeed:
                item["pagespeed"] = get_pagespeed_insights(safe_url, config.pagespeed_key or "")

            results.append(item)

        except Exception as exc:
            results.append({"url": url, "error": str(exc)})

        if idx < len(urls) - 1 and config.delay_seconds > 0:
            time.sleep(config.delay_seconds)

    context = "\n".join(scraped_context_parts)
    master_prompt = build_master_prompt(prompt_template, config.keyword, context)

    gemini_output = None
    if config.gemini_key:
        gemini_output = call_gemini_api(master_prompt, config.gemini_key)

    return {
        "keyword": config.keyword,
        "prompt_name": config.prompt_name,
        "prompt_template": prompt_template,
        "urls_found": len(urls),
        "results": results,
        "master_prompt": master_prompt,
        "gemini_output": gemini_output,
    }


def parse_args(argv: list[str]) -> AgentConfig:
    parser = argparse.ArgumentParser(
        description="SERP agent that scrapes targeted search results and optionally runs Gemini analysis.")
    parser.add_argument("--keyword", required=True, help="SERP keyword to target")
    parser.add_argument(
        "--prompt-name",
        default=DEFAULT_PROMPT,
        help="Prompt name from seo_tool.PROMPTS",
    )
    parser.add_argument("--max-urls", type=int, default=10, help="Maximum URLs to process")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=SCRAPE_DELAY_SECONDS,
        help="Delay between URL fetches",
    )
    parser.add_argument(
        "--include-pagespeed",
        action="store_true",
        help="Include Google PageSpeed lookups",
    )
    parser.add_argument("--gemini-key", default=None, help="Optional Gemini key for final analysis")
    parser.add_argument("--pagespeed-key", default=None, help="Optional Google PageSpeed API key")

    args = parser.parse_args(argv)

    if args.max_urls < 1:
        raise ValueError("--max-urls must be >= 1")
    if args.delay_seconds < 0:
        raise ValueError("--delay-seconds must be >= 0")

    return AgentConfig(
        keyword=args.keyword.strip(),
        prompt_name=args.prompt_name,
        max_urls=args.max_urls,
        delay_seconds=args.delay_seconds,
        include_pagespeed=args.include_pagespeed,
        gemini_key=args.gemini_key,
        pagespeed_key=args.pagespeed_key,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        config = parse_args(argv if argv is not None else sys.argv[1:])
        output = run_agent(config)
        print(json.dumps(output, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
