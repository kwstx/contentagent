import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone


API_BASE = "https://api.x.com/2"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def api_get(path, params=None, token=None):
    if token is None:
        token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise RuntimeError("Missing X_BEARER_TOKEN environment variable.")
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}{query}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def get_user_id(username, token=None):
    data = api_get(f"/users/by/username/{username}", token=token)
    return data.get("data", {}).get("id")


def get_recent_tweets(user_id, max_results, token=None):
    params = {
        "max_results": max_results,
        "exclude": "retweets,replies",
        "tweet.fields": "created_at,public_metrics",
    }
    data = api_get(f"/users/{user_id}/tweets", params=params, token=token)
    return data.get("data", [])


def compute_engagement_rate(tweets, follower_count):
    if not tweets or not follower_count:
        return None
    total = 0.0
    for tweet in tweets:
        metrics = tweet.get("public_metrics", {})
        total += (
            metrics.get("like_count", 0)
            + metrics.get("reply_count", 0)
            + metrics.get("retweet_count", 0)
            + metrics.get("quote_count", 0)
        ) / float(follower_count)
    return total / len(tweets)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Fetch reference tweets for style analysis.")
    parser.add_argument(
        "--accounts",
        default=os.path.join("data", "reference_accounts.json"),
        help="Path to reference_accounts.json",
    )
    parser.add_argument(
        "--out",
        default=os.path.join("data", "reference_tweets.json"),
        help="Output path for reference_tweets.json",
    )
    parser.add_argument("--max-results", type=int, default=10, help="Tweets per account")
    parser.add_argument(
        "--update-accounts",
        action="store_true",
        help="Update avg_engagement_rate in reference_accounts.json",
    )
    args = parser.parse_args()

    accounts_data = load_json(args.accounts)
    accounts = accounts_data.get("accounts", [])
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        print("Error: X_BEARER_TOKEN is required to call the X API.", file=sys.stderr)
        sys.exit(1)

    fetched_at = utc_now_iso()
    tweets_out = []
    for account in accounts:
        username = account.get("username")
        if not username:
            continue
        user_id = get_user_id(username, token=token)
        if not user_id:
            continue
        tweets = get_recent_tweets(user_id, args.max_results, token=token)
        for tweet in tweets:
            tweets_out.append(
                {
                    "account_username": username,
                    "tweet_id": tweet.get("id"),
                    "created_at": tweet.get("created_at"),
                    "text": tweet.get("text"),
                    "public_metrics": tweet.get("public_metrics", {}),
                    "url": f"https://x.com/{username}/status/{tweet.get('id')}",
                    "fetched_at": fetched_at,
                }
            )

        if args.update_accounts:
            engagement_rate = compute_engagement_rate(
                tweets, account.get("follower_count")
            )
            if engagement_rate is not None:
                account["avg_engagement_rate"] = engagement_rate
                account["avg_engagement_rate_source"] = "computed_from_reference_tweets"
                account["avg_engagement_rate_as_of"] = fetched_at
                account["status"] = "eligible"

    write_json(args.out, {"dataset": "reference_tweets", "generated_at": fetched_at, "tweets": tweets_out})

    if args.update_accounts:
        accounts_data["generated_at"] = fetched_at
        write_json(args.accounts, accounts_data)

    print(f"Wrote {len(tweets_out)} tweets to {args.out}")


if __name__ == "__main__":
    main()
