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
