# ⚡ Powerful SEO Tool for (2026)

A Streamlit-powered SEO analysis tool that combines **live SERP scraping** with **Google Gemini AI** to deliver data-driven SEO insights. No mock data — every analysis is built on real, freshly-scraped web data.

## What It Does

Choose from **17 SEO strategies** across 7 categories:

| Category | Tasks |
|---|---|
| **Keyword Research** | Top 50 Page Analysis, Long-Tail Keywords, Search Intent Comparison |
| **On-Page SEO** | Article Optimization, Meta Tag Enhancement |
| **Content Strategy** | Topical Map, Content Gap Analysis |
| **Technical SEO** | Site Structure Audit, Structured Data Markup |
| **Link Building** | Guest Post Opportunities |
| **Advanced Strategies** | Backlink Analysis, Content Performance, Core Web Vitals, Content Repurposing |
| **Engagement SEO** | Bounce Rate Analysis, Mobile-First Optimization, Video SEO Strategy |

## How It Works

1. **You pick a strategy** from the sidebar
2. **You fill in your target** (keyword, URL, or content)
3. **The tool scrapes live data** — actual DOM structure, headings, word counts, link graphs
4. **Gemini AI analyzes** the scraped data and returns actionable recommendations

For keyword research, it scrapes the **top 10 DuckDuckGo results** and feeds all competitor data to Gemini. For URL-based tasks, it pulls the real page architecture.

## API Keys — Bring Your Own

**This tool never stores your keys.** They live only in your active browser session and are sent directly to Google's APIs.

### Required

| API | What It Powers | How to Get One |
|---|---|---|
| **Gemini API** | All AI analysis (Gemini 2.5 Flash) | Free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

### Optional

| API | What It Powers | How to Get One |
|---|---|---|
| **Google PageSpeed Insights API** | Core Web Vitals & Mobile-First audits only | Free at [console.cloud.google.com](https://console.cloud.google.com) (enable PageSpeed Insights API) |

> Without the PageSpeed key, the tool still works for all 15 other strategies. The PageSpeed API also works without a key but at lower rate limits.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/powerhouse-seo-tool.git
cd powerhouse-seo-tool

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run seo_tool.py
```

The app opens at `http://localhost:8501`. Paste your Gemini API key in the sidebar and go.


## SERP Agent (CLI)

Run automated SERP-targeted scraping from the command line:

```bash
python serp_agent.py --keyword "best crm for startups" --max-urls 10
```

With optional AI summary:

```bash
python serp_agent.py --keyword "best crm for startups" --max-urls 10 --gemini-key "$GEMINI_API_KEY"
```

This prints JSON with discovered URLs, scrape payloads, assembled master prompt, and optional Gemini output.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set `seo_tool.py` as the main file
4. Deploy — no secrets needed in the dashboard (users paste their own keys)

## Project Structure

```
├── seo_tool.py          # Main application
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── LICENSE              # MIT License
```

## Safety & Privacy

- **No keys stored** — API keys exist only in the user's active Streamlit session
- **SSRF protection** — Private/internal network URLs are blocked from scraping
- **SSL verification enabled** — All outbound requests use proper certificate validation
- **Rate-limited scraping** — 1.5s delay between bulk scrapes to be respectful to target servers
- **Truncated payloads** — Scraped content is capped to prevent runaway Gemini API token costs
- **No data collection** — The tool collects zero user data; everything runs in the user's session

## Limitations

- SERP scraping uses DuckDuckGo HTML, which may rate-limit under heavy use
- Some websites block automated scraping (403 errors are reported clearly)
- PageSpeed data requires the target URL to be publicly accessible
- Gemini API free tier has daily request limits

## License

MIT — use it, fork it, improve it.
