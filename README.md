# Reference Account System

This repo seeds the reference account dataset used to drive style extraction for automated X content creation.

## Datasets

- `data/reference_accounts.json` contains the reference account set (username, niche, follower count, avg engagement rate, weight).
- `data/reference_tweets.json` contains the most recent fetched tweets for style analysis.
- `data/topic_stream.json` stores raw tweets collected for topic discovery.
- `data/topic_candidates.json` stores extracted topic candidates prior to validation.
- `data/topic_signals.json` stores approved topic signals for downstream tweet generation.
- `data/recent_topics.json` stores recently used topics for deduplication.
- `data/topic_discovery_config.json` holds the topic discovery configuration.

## Refreshing data

The fetcher uses the X API v2. Set `X_BEARER_TOKEN` and run:

```bash
python scripts/fetch_reference_tweets.py --max-results 10 --update-accounts
```

Engagement rate is computed as:

```
avg_engagement_rate = avg((likes + replies + retweets + quotes) / follower_count) across recent tweets
```

Accounts stay in `pending_engagement_verification` until fresh tweets are pulled and rates are computed.

# Topic discovery

The topic discovery pipeline scans reference accounts and keyword searches to surface early, controversial, or high-engagement discussions. It writes the `topic_stream`, `topic_candidates`, and `topic_signals` datasets.

Run with:

```bash
python scripts/topic_discovery.py
```

You can adjust keywords, lookback window, or signal thresholds in `data/topic_discovery_config.json`.

# contentagent
