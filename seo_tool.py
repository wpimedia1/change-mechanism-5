import os
import re
import json
import ssl
import time
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import streamlit as st

# ---------------------------------------------------------
# 1. THE 17 SEO PROMPTS (FROM INFOGRAPHIC)
# ---------------------------------------------------------

PROMPTS = {
    "Keyword Research": {
        "Top 50 Page Analysis": "Analyze the top ranking pages for [keyword] and identify common on-page SEO patterns, including word count, heading structure, and keyword density.",
        "Long-Tail Keyword Generation": "Generate a list of low-competition, high-intent long-tail keywords for [topic], with metrics like keyword difficulty, CPC, and search volume.",
        "Search Intent Comparison": "Compare the search intent of [keyword A] and [keyword B] by analyzing SERP results, user behavior, and top-ranking content types."
    },
    "On-Page SEO Optimization": {
        "Article Optimization": "Improve this article for SEO: [paste text]. Suggest better headings, internal links, and optimized keyword placement.",
        "Meta Tag Enhancement": "Rewrite this meta title and description to boost CTR while keeping it keyword-rich: [paste current meta tags]."
    },
    "Content Strategy": {
        "Topical Map": "Outline a topical map for [niche], including pillar pages, clusters, and supporting content.",
        "Content Gap Analysis": "Identify missing topics on [competitor URL] vs. [your URL] and suggest high-value content to create."
    },
    "Technical SEO": {
        "Site Structure Audit": "Analyze [website URL]'s site structure and recommend fixes for internal linking, crawlability, and indexation.",
        "Structured Data Markup": "Create a schema.org markup for a [topic] blog post to increase rich snippet chances."
    },
    "Link Building": {
        "Guest Post Opportunities": "Find high-DA websites in [niche] accepting guest posts, with contact details and domain authority scores."
    },
    "Advanced Strategies": {
        "Backlink Analysis": "Analyze backlinks of [competitor URL] and suggest replicable link-building tactics. Note: Use live search to find domain mentions and referring domains.",
        "Content Performance Fixes": "Audit low-traffic pages on [website URL] and recommend updates/consolidation strategies based on on-page UX data.",
        "Core Web Vitals": "Diagnose Core Web Vitals for [website URL] and provide steps to improve speed/UX.",
        "Content Repurposing": "Suggest ways to repurpose [content URL] for max visibility (e.g., videos, infographics)."
    },
    "Engagement SEO": {
        "Bounce Rate Analysis": "Analyze the UX layout, content hooks, and CTAs for [website URL] and suggest UX improvements to increase time-on-page and reduce exits.",
        "Mobile-First Optimization": "Audit [website URL] for mobile usability issues (e.g., tap targets, font size, responsive design) and provide fixes to align with Google's mobile-first indexing.",
        "Video SEO Strategy": "Suggest ways to optimize embedded videos on [webpage URL] for SEO, including schema markup, transcripts, and engagement-boosting tactics."
    }
}

# ---------------------------------------------------------
# 2. SAFETY: URL VALIDATION & SSRF PROTECTION
# ---------------------------------------------------------

# Block scraping of internal/private network ranges
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
BLOCKED_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                    "172.30.", "172.31.", "192.168.", "169.254.")

MAX_BODY_CHARS = 15000  # Truncate scraped text to control Gemini token usage
SCRAPE_DELAY_SECONDS = 1.5  # Polite delay between bulk scrapes


def is_safe_url(url: str) -> bool:
    """Validates a URL is public and not targeting internal network services (SSRF protection)."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname in BLOCKED_HOSTS:
            return False
        if any(hostname.startswith(p) for p in BLOCKED_PREFIXES):
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        return True
    except Exception:
        return False


def sanitize_url(url: str) -> str:
    """Ensures URL has a scheme and is safe to fetch."""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    if not is_safe_url(url):
        raise ValueError(f"URL blocked for safety: {url}")
    return url


# ---------------------------------------------------------
# 3. THE DATA ENGINES
# ---------------------------------------------------------

def fetch_serp_urls(keyword: str, num_results: int = 10) -> list:
    """Scrapes DuckDuckGo HTML results to find top ranking URLs for a keyword."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    query_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(keyword)}"
    links = []
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(query_url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", class_="result__url"):
            href = a.get("href")
            if href and "http" in href:
                parsed_href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
                if is_safe_url(parsed_href) and parsed_href not in links:
                    links.append(parsed_href)
                    if len(links) >= num_results:
                        break
    except Exception:
        pass
    return links


def fetch_html(url: str) -> str:
    """Fetches HTML content using proper SSL verification."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            return response.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP Error {e.code}: {e.reason}")
    except Exception as e:
        raise Exception(f"Connection failed: {str(e)}")


def universal_scraper(url: str) -> str:
    """Downloads a page and extracts SEO-relevant architecture data."""
    url = sanitize_url(url)
    try:
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, "html.parser")
        domain = urlparse(url).netloc

        title = soup.title.string.strip() if soup.title and soup.title.string else "None"
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag["content"] if meta_desc_tag and meta_desc_tag.get("content") else "None"

        h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]

        internal_links = set()
        external_links = set()
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.startswith("#") or href.startswith("mailto:"):
                continue
            full_url = urljoin(url, href)
            if urlparse(full_url).netloc == domain:
                internal_links.add(full_url.rstrip("/"))
            else:
                external_links.add(full_url)

        body_text = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
        word_count = len(body_text.split())

        # Truncate body text to control token costs
        truncated_text = body_text[:MAX_BODY_CHARS]
        if len(body_text) > MAX_BODY_CHARS:
            truncated_text += "... [TRUNCATED]"

        return f"""
[COMPETITOR DOM DATA FOR: {url}]
Title: {title}
Meta Description: {meta_desc}
Word Count: ~{word_count} words
H1 Tags ({len(h1s)}): {h1s}
H2 Tags ({len(h2s)}): {h2s[:10]}
Internal Links: {len(internal_links)} | External Links: {len(external_links)}
Body Sample: {truncated_text[:3000]}
"""
    except Exception as e:
        return f"[SCRAPE FAILED FOR {url}: {str(e)}]\n"


def get_pagespeed_insights(url: str, api_key: str) -> str:
    """Pings Google's official PageSpeed API for real Core Web Vitals."""
    import requests

    url = sanitize_url(url)
    endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={urllib.parse.quote(url, safe='')}&strategy=mobile"
    if api_key:
        endpoint += f"&key={api_key}"

    try:
        response = requests.get(endpoint, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "lighthouseResult" not in data:
            return f"[PAGESPEED ERROR: Could not analyze {url}. Ensure it is publicly accessible.]"

        audits = data["lighthouseResult"]["audits"]
        lcp = audits.get("largest-contentful-paint", {}).get("displayValue", "N/A")
        cls = audits.get("cumulative-layout-shift", {}).get("displayValue", "N/A")
        speed_index = audits.get("speed-index", {}).get("displayValue", "N/A")

        return f"""
[LIVE GOOGLE PAGESPEED DATA FOR {url} (Mobile)]
Largest Contentful Paint (LCP): {lcp}
Cumulative Layout Shift (CLS): {cls}
Speed Index: {speed_index}
"""
    except Exception as e:
        return f"[PAGESPEED API FAILED FOR {url}: {str(e)}]"


def call_gemini_api(prompt: str, gemini_key: str) -> str:
    """Calls Gemini 2.5 Flash REST API."""
    import requests

    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={gemini_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are an elite Technical SEO expert. Analyze the hard data provided. "
                    "Read the scraped data and identify exact patterns (averages, common headings, keyword usage). "
                    "Provide actionable, data-driven recommendations."
                )
            }]
        },
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(api_url, headers=headers, json=payload, timeout=60)

    if response.status_code == 200:
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "[ERROR: Unexpected response structure from Gemini API. Please try again.]"
    else:
        raise Exception(f"Gemini API Error {response.status_code}: {response.text[:500]}")


# ---------------------------------------------------------
# 4. STREAMLIT UI & LOGIC
# ---------------------------------------------------------

st.set_page_config(page_title="Powerhouse SEO 2026", page_icon="⚡", layout="wide")
st.title("⚡ Powerhouse SEO Tool (2026)")
st.markdown("Powered by Google Gemini & Live SERP Scraping. Bring your own API keys.")

with st.sidebar:
    st.header("🔑 API Credentials")
    st.caption("Keys are never stored. They exist only in your browser session.")
    gemini_key = st.text_input(
        "Gemini API Key (Required)",
        type="password",
        value=os.environ.get("GEMINI_API_KEY", ""),
        help="Get one free at https://aistudio.google.com/apikey",
    )
    google_key = st.text_input(
        "Google PageSpeed API Key (Optional)",
        type="password",
        value=os.environ.get("GOOGLE_API_KEY", ""),
        help="Only needed for Core Web Vitals / Mobile audits. Get one at https://console.cloud.google.com",
    )

    st.divider()
    st.header("🎯 Strategy Selector")
    category = st.selectbox("1. Category", list(PROMPTS.keys()))
    prompt_name = st.selectbox("2. Task", list(PROMPTS[category].keys()))

template = PROMPTS[category][prompt_name]
variables = re.findall(r"\[(.*?)\]", template)
inputs = {}

with st.form("seo_form"):
    st.info(f"**Selected Strategy:** {template}")
    for var in variables:
        if any(kw in var.lower() for kw in ("paste", "text", "tags")):
            inputs[var] = st.text_area(f"Enter {var}", height=150)
        else:
            inputs[var] = st.text_input(f"Enter {var}")
    submitted = st.form_submit_button("Run Deep Analysis 🚀")

if submitted:
    if not gemini_key:
        st.error("⚠️ You must provide a Gemini API key to run the analysis.")
        st.stop()

    final_prompt = template
    for var, val in inputs.items():
        final_prompt = final_prompt.replace(f"[{var}]", val)

    live_data_context = ""
    needs_pagespeed = prompt_name in ["Core Web Vitals", "Mobile-First Optimization"]

    with st.spinner("Compiling real-world data footprint..."):

        # --- BULK SERP SCRAPING FOR KEYWORD RESEARCH ---
        if prompt_name == "Top 50 Page Analysis" and "keyword" in inputs:
            keyword = inputs["keyword"]
            st.toast(f"Hunting top SERP results for '{keyword}'...")
            top_urls = fetch_serp_urls(keyword, num_results=10)

            if not top_urls:
                st.warning("Could not retrieve SERP URLs. DuckDuckGo may be rate-limiting requests. Try again shortly.")
            else:
                st.write(f"✅ Found {len(top_urls)} top-ranking pages. Scraping...")
                progress = st.progress(0)
                for idx, url in enumerate(top_urls):
                    st.toast(f"Scraping {idx + 1}/{len(top_urls)}: {urlparse(url).netloc}")
                    live_data_context += universal_scraper(url) + "\n"
                    progress.progress((idx + 1) / len(top_urls))
                    if idx < len(top_urls) - 1:
                        time.sleep(SCRAPE_DELAY_SECONDS)

        # --- SINGLE URL SCRAPING ---
        else:
            for var, val in inputs.items():
                if "url" in var.lower() and val.strip():
                    st.toast(f"Scraping DOM architecture for {val}...")
                    live_data_context += universal_scraper(val)

                    if needs_pagespeed:
                        st.toast(f"Pinging Google PageSpeed API for {val}...")
                        live_data_context += get_pagespeed_insights(val, google_key)

    # Assemble the Master Prompt
    if live_data_context:
        master_prompt = (
            "Here is verified data pulled directly from live web scraping. "
            "Base your entire analysis on this specific data. "
            "Read it and analyze it thoroughly.\n\n"
            f"{live_data_context}\n\n"
            "Based on the exact data above, execute the following SEO task:\n"
            f"TASK: {final_prompt}"
        )
    else:
        master_prompt = final_prompt

    with st.expander("🔍 View Raw Master Prompt & Scraped Data Payload"):
        st.code(master_prompt, language="text")

    st.markdown("### 🧠 AI Analysis & Insights")

    with st.spinner("Processing through Gemini..."):
        try:
            response_text = call_gemini_api(master_prompt, gemini_key)
            st.markdown(response_text)
        except Exception as e:
            st.error(f"❌ Execution Error: {e}")