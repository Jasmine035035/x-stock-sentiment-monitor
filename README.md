# X Stock Sentiment Monitor

A Python tool that monitors stock-related X (Twitter) influencers, stores their posts in a local database, and uses an AI model (Qwen, via Alibaba Cloud's MaaS service) to generate sentiment analysis, trend summaries, and forward-looking insights. Results are automatically sent to a Feishu group chat.

## Features

- Data Collection: Fetches recent posts from a curated list of finance-focused X influencers using the X API.
- Structured Storage: Saves all fetched posts into a local SQLite database, deduplicated by tweet ID.
- AI-Powered Analysis: Sends accumulated data to Qwen (qwen3.5-plus) for:
  - Daily snapshot of overall market sentiment by topic (macro, semiconductors, commercial space, biotech, AI/tech, new energy, etc.)
  - Per-influencer sentiment summary
  - Trend analysis across multiple days
  - Forward-looking, non-binding outlook based on recent discussion themes
- **Automated Reporting**: Generates text reports and Excel summaries, then pushes results directly to a Feishu group via webhook.

## Project Structure

```
.
├── config.py            # List of monitored usernames and fetch settings
├── fetch.py              # X API data fetching logic
├── db.py                 # SQLite storage and retrieval
├── analyze.py            # AI analysis via Qwen (Alibaba Cloud MaaS)
├── report.py             # Text/Excel report generation
├── send_feishu.py        # Feishu webhook integration
├── main.py               # Orchestrates the full pipeline
├── requirements.txt      # Python dependencies
├── test_token.py         # Quick script to verify X API token validity
├── test_feishu.py        # Quick script to test Feishu webhook
├── test_analyze.py       # Quick script to test AI analysis independently
└── data/                 # SQLite database (gitignored)
└── reports/              # Generated reports (gitignored)
```
