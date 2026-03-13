# Reference Account System

This repo seeds the reference account dataset used to drive style extraction for automated X content creation.

## Datasets

- `data/reference_accounts.json` contains the reference account set (username, niche, follower count, avg engagement rate, weight).
- `data/reference_tweets.json` contains the most recent fetched tweets for style analysis.

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

# contentagent
