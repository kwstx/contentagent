# Reference Account System

This repo seeds the reference account dataset used to drive style extraction for automated X content creation.

## Datasets

- `data/reference_accounts.json` contains the reference account set (username, niche, follower count, avg engagement rate, weight).
- `data/reference_tweets.json` contains the most recent fetched tweets for style analysis.
- `data/topic_stream.json` stores raw tweets collected for topic discovery.
- `data/topic_candidates.json` stores extracted topic candidates prior to validation.
- `data/topic_signals.json` stores scored topic signals with detailed scoring metadata.
- `data/approved_topics.json` stores approved topics that pass the scoring threshold.
- `data/recent_topics.json` stores recently used topics for deduplication.
- `data/topic_discovery_config.json` holds the topic discovery configuration.
- `data/candidate_viral_tweets.json` stores raw candidates before engagement normalization filtering.
- `data/viral_tweet_dataset.json` stores normalized, labeled, high-performing tweets for training.
- `data/viral_tweet_config.json` holds the viral tweet dataset configuration.
- `data/tweet_patterns.json` stores extracted structural templates for tweet generation.

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

The topic discovery pipeline scans reference accounts and keyword searches to surface early, controversial, or high-engagement discussions. It writes the `topic_stream`, `topic_candidates`, `topic_signals`, and `approved_topics` datasets.

Run with:

```bash
python scripts/topic_discovery.py
```

You can adjust keywords, lookback window, signal thresholds, or scoring weights in `data/topic_discovery_config.json`.

# viral tweet dataset

Build the viral tweet dataset from manual CSV input with:

```bash
python scripts/build_viral_tweet_dataset.py
```

The script reads `data/manual_viral_tweets.csv`, writes `data/candidate_viral_tweets.json`, and promotes tweets into `data/viral_tweet_dataset.json` after normalization.

# manual collection

Fill `data/manual_viral_tweets.csv` with tweets you collect manually from the X UI and run:

```bash
python scripts/build_viral_tweet_dataset.py
```

Required columns are `text`, `author_followers`, `like_count`, `reply_count`, `retweet_count`, `quote_count`. Optional columns are `tweet_id`, `url`, `created_at`, `author_username`, `author_id`, `impression_count`, `source_type`, `source_query`.

# contentagent

# tweet pattern extraction

Once the viral dataset is populated, extract reusable structure templates with:

```bash
python scripts/build_tweet_patterns.py
```

# tweet ranking

Rank generated tweet candidates with:

```bash
python scripts/rank_tweets.py --top 12
```
