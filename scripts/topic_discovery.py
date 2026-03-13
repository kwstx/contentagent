import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone


API_BASE = "https://api.x.com/2"
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
}
DOMAIN_TERMS = [
    ("artificial intelligence", {"ai", "artificial", "llm", "model", "foundation"}),
    ("AI agents", {"agent", "agents", "multi", "autonomous", "coordination", "interoperability"}),
    ("autonomous systems", {"autonomous", "robot", "robotics", "systems"}),
    ("programming and software engineering", {"programming", "software", "code", "developer", "engineering"}),
    ("startups", {"startup", "founder", "venture", "funding", "vc"}),
    ("business strategy", {"strategy", "growth", "pricing", "distribution", "market"}),
    ("technology news", {"release", "launch", "announce", "news", "update"}),
    ("technology", {"tech", "infrastructure", "cloud", "hardware", "platform"}),
]


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def chunk_list(values, size):
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"@[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"#[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_keywords(text, min_length, max_keywords):
    tokens = [
        token
        for token in normalize_text(text).split()
        if token not in STOPWORDS and len(token) >= min_length
    ]
    if not tokens:
        return []
    counts = Counter(tokens)
    keywords = [token for token, _ in counts.most_common(max_keywords)]
    return keywords


def compute_engagement(tweet):
    metrics = tweet.get("public_metrics", {})
    return (
        metrics.get("like_count", 0)
        + metrics.get("reply_count", 0)
        + metrics.get("retweet_count", 0)
        + metrics.get("quote_count", 0)
    )


def compute_engagement_rate(tweet, follower_count):
    if not follower_count:
        return None
    return compute_engagement(tweet) / float(follower_count)


def load_reference_accounts(path):
    data = load_json(path)
    accounts = {}
    for account in data.get("accounts", []):
        username = account.get("username")
        if username:
            accounts[username.lower()] = account
    return accounts


def get_user_id(username, token=None):
    data = api_get(f"/users/by/username/{username}", token=token)
    return data.get("data", {}).get("id")


def get_recent_tweets(user_id, max_results, token=None):
    params = {
        "max_results": max_results,
        "exclude": "retweets,replies",
        "tweet.fields": "created_at,public_metrics,conversation_id",
    }
    data = api_get(f"/users/{user_id}/tweets", params=params, token=token)
    return data.get("data", [])


def search_recent_tweets(query, start_time, max_results, token=None):
    params = {
        "query": query,
        "start_time": start_time,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,conversation_id",
        "expansions": "author_id",
        "user.fields": "username,public_metrics",
    }
    data = api_get("/tweets/search/recent", params=params, token=token)
    tweets = data.get("data", [])
    users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
    return tweets, users


def classify_domain(keywords):
    keyword_set = set(keywords)
    for domain, terms in DOMAIN_TERMS:
        if keyword_set.intersection(terms):
            return domain
    return None


def score_domain_relevance(keywords, topic_scope):
    keyword_set = set(keywords)
    best_domain = None
    best_ratio = 0.0
    for domain, terms in DOMAIN_TERMS:
        if domain not in topic_scope:
            continue
        overlap = len(keyword_set.intersection(terms))
        if overlap == 0:
            continue
        denom = max(1, min(len(keyword_set), len(terms)))
        ratio = overlap / float(denom)
        if ratio > best_ratio:
            best_ratio = ratio
            best_domain = domain
    if not best_domain:
        return None, 0.0
    score = min(100.0, 50.0 + best_ratio * 50.0)
    return best_domain, score


def detect_product_relevance(keywords, product_keywords):
    keyword_set = set(keywords)
    for phrase in product_keywords:
        parts = normalize_text(phrase).split()
        if not parts:
            continue
        if keyword_set.intersection(parts):
            return True
    return False


def jaccard_similarity(a, b):
    if not a or not b:
        return 0.0
    a_set = set(a)
    b_set = set(b)
    overlap = a_set.intersection(b_set)
    union = a_set.union(b_set)
    return len(overlap) / float(len(union))


def aggregate_signal_rate(signals, key):
    if not signals:
        return 0.0
    hits = sum(1 for signal in signals if signal.get(key))
    return hits / float(len(signals))


def score_controversy(signals, keywords, scoring_cfg):
    contrarian_rate = aggregate_signal_rate(signals, "contrarian")
    debate_rate = aggregate_signal_rate(signals, "debate")
    base_score = (contrarian_rate * 0.7 + debate_rate * 0.3) * 100.0

    keyword_bonus = 0.0
    controversy_terms = scoring_cfg.get("controversy_keywords", [])
    if controversy_terms:
        term_tokens = set()
        for phrase in controversy_terms:
            term_tokens.update(normalize_text(phrase).split())
        overlap = set(keywords).intersection(term_tokens)
        if overlap:
            keyword_bonus = min(15.0, 5.0 * len(overlap))

    return min(100.0, base_score + keyword_bonus)


def score_dark_humor(keywords, scoring_cfg):
    humor_terms = scoring_cfg.get("dark_humor_keywords", [])
    if not humor_terms:
        return 0.0
    term_tokens = set()
    for phrase in humor_terms:
        term_tokens.update(normalize_text(phrase).split())
    overlap = set(keywords).intersection(term_tokens)
    if not overlap:
        return 0.0
    ratio = len(overlap) / float(max(1, min(len(keywords), len(term_tokens))))
    return min(100.0, ratio * 100.0)


def score_engagement(supporting_tweets, signals_cfg):
    if not supporting_tweets:
        return 0.0, {}

    engagements = []
    rates = []
    reply_ratios = []

    for tweet in supporting_tweets:
        engagements.append(compute_engagement(tweet))
        rate = compute_engagement_rate(tweet, tweet.get("author_followers"))
        if rate is not None:
            rates.append(rate)
        metrics = tweet.get("public_metrics", {})
        like_count = metrics.get("like_count", 0)
        reply_count = metrics.get("reply_count", 0)
        if like_count > 0:
            reply_ratios.append(reply_count / float(like_count))

    avg_engagement = sum(engagements) / float(len(engagements))
    avg_rate = sum(rates) / float(len(rates)) if rates else None
    avg_reply_ratio = sum(reply_ratios) / float(len(reply_ratios)) if reply_ratios else 0.0

    baseline_rate = signals_cfg.get("baseline_engagement_rate", 0.001)
    min_total_engagement = signals_cfg.get("min_total_engagement", 10)
    reply_ratio_threshold = signals_cfg.get("reply_ratio_threshold", 0.25)

    rate_score = 0.0
    if avg_rate is not None and baseline_rate > 0:
        rate_score = min(100.0, (avg_rate / baseline_rate) * 40.0)
    volume_score = min(100.0, (avg_engagement / float(max(1, min_total_engagement))) * 40.0)
    reply_score = min(100.0, (avg_reply_ratio / float(max(0.01, reply_ratio_threshold))) * 20.0)

    engagement_score = min(100.0, rate_score + volume_score + reply_score)
    return engagement_score, {
        "avg_engagement": avg_engagement,
        "avg_engagement_rate": avg_rate,
        "avg_reply_ratio": avg_reply_ratio,
    }


def score_novelty(keywords, recent_topics, similarity_threshold, scoring_cfg):
    max_similarity = 0.0
    for recent in recent_topics:
        similarity = jaccard_similarity(keywords, recent.get("keywords", []))
        max_similarity = max(max_similarity, similarity)
    novelty_score = max(0.0, 100.0 - (max_similarity * 100.0))
    penalty = 0.0
    if max_similarity >= similarity_threshold:
        penalty = scoring_cfg.get("redundancy_penalty", 25.0)
        penalty += max_similarity * scoring_cfg.get("max_similarity_penalty", 15.0)
    return novelty_score, max_similarity, penalty


def weighted_score(scores, weights):
    total_weight = sum(weights.values()) if weights else 0.0
    if total_weight <= 0:
        return 0.0
    return sum(scores.get(key, 0.0) * weight for key, weight in weights.items()) / total_weight


def build_topic_description(keywords):
    if not keywords:
        return "emerging technology discussion"
    keyword_set = set(keywords)
    if {"agent", "agents", "coordination", "multi"}.intersection(keyword_set):
        return "coordination challenges in multi-agent systems"
    if {"startup", "founder", "funding", "vc"}.intersection(keyword_set):
        return "startup funding and execution tradeoffs"
    if {"developer", "software", "programming", "code"}.intersection(keyword_set):
        return "engineering discipline under delivery pressure"
    if {"ai", "llm", "model", "foundation"}.intersection(keyword_set):
        return "strategic risks in AI model deployment"
    if {"infrastructure", "cloud", "platform"}.intersection(keyword_set):
        return "infrastructure bottlenecks for AI workloads"
    return f"discussion around {', '.join(keywords[:2])}"


def build_topic_key(keywords):
    if not keywords:
        return "misc"
    return "-".join(sorted(keywords[:3]))


def load_recent_topics(path):
    if not os.path.exists(path):
        return []
    data = load_json(path)
    return data.get("topics", [])


def main():
    parser = argparse.ArgumentParser(description="Discover high-potential topics on X.")
    parser.add_argument(
        "--accounts",
        default=os.path.join("data", "reference_accounts.json"),
        help="Path to reference_accounts.json",
    )
    parser.add_argument(
        "--config",
        default=os.path.join("data", "topic_discovery_config.json"),
        help="Path to topic_discovery_config.json",
    )
    parser.add_argument(
        "--recent-topics",
        default=os.path.join("data", "recent_topics.json"),
        help="Path to recent_topics.json",
    )
    parser.add_argument(
        "--topic-stream-out",
        default=os.path.join("data", "topic_stream.json"),
        help="Output path for topic_stream.json",
    )
    parser.add_argument(
        "--topic-candidates-out",
        default=os.path.join("data", "topic_candidates.json"),
        help="Output path for topic_candidates.json",
    )
    parser.add_argument(
        "--topic-signals-out",
        default=os.path.join("data", "topic_signals.json"),
        help="Output path for topic_signals.json",
    )
    parser.add_argument(
        "--approved-topics-out",
        default=os.path.join("data", "approved_topics.json"),
        help="Output path for approved_topics.json",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Override max results per request",
    )
    args = parser.parse_args()

    config = load_json(args.config)
    accounts = load_reference_accounts(args.accounts)
    recent_topics = load_recent_topics(args.recent_topics)
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        print("Error: X_BEARER_TOKEN is required to call the X API.", file=sys.stderr)
        sys.exit(1)

    search_cfg = config.get("search", {})
    max_results = args.max_results or search_cfg.get("max_results_per_request", 50)
    lookback_hours = search_cfg.get("lookback_hours", 24)
    keyword_chunk_size = search_cfg.get("keyword_chunk_size", 6)

    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(hours=lookback_hours)).replace(microsecond=0).isoformat()
    fetched_at = utc_now_iso()

    topic_stream = []

    for username, account in accounts.items():
        user_id = get_user_id(username, token=token)
        if not user_id:
            continue
        tweets = get_recent_tweets(user_id, max_results, token=token)
        for tweet in tweets:
            topic_stream.append(
                {
                    "tweet_id": tweet.get("id"),
                    "author_id": user_id,
                    "author_username": username,
                    "author_followers": account.get("follower_count"),
                    "source_type": "reference_account",
                    "source_query": username,
                    "created_at": tweet.get("created_at"),
                    "text": tweet.get("text"),
                    "public_metrics": tweet.get("public_metrics", {}),
                    "url": f"https://x.com/{username}/status/{tweet.get('id')}",
                }
            )

    keywords = config.get("keywords", [])
    for chunk in chunk_list(keywords, keyword_chunk_size):
        query = " OR ".join(f'"{term}"' if " " in term else term for term in chunk)
        tweets, users = search_recent_tweets(query, start_time, max_results, token=token)
        for tweet in tweets:
            user = users.get(tweet.get("author_id"), {})
            followers = user.get("public_metrics", {}).get("followers_count")
            username = user.get("username")
            topic_stream.append(
                {
                    "tweet_id": tweet.get("id"),
                    "author_id": tweet.get("author_id"),
                    "author_username": username,
                    "author_followers": followers,
                    "source_type": "keyword_search",
                    "source_query": query,
                    "created_at": tweet.get("created_at"),
                    "text": tweet.get("text"),
                    "public_metrics": tweet.get("public_metrics", {}),
                    "url": f"https://x.com/{username}/status/{tweet.get('id')}"
                    if username
                    else None,
                }
            )

    write_json(
        args.topic_stream_out,
        {"dataset": "topic_stream", "generated_at": fetched_at, "tweets": topic_stream},
    )

    signals_cfg = config.get("signals", {})
    baseline_rate = signals_cfg.get("baseline_engagement_rate", 0.001)
    high_multiplier = signals_cfg.get("high_engagement_multiplier", 2.5)
    min_total_engagement = signals_cfg.get("min_total_engagement", 10)
    reply_ratio_threshold = signals_cfg.get("reply_ratio_threshold", 0.25)
    min_reply_count = signals_cfg.get("min_reply_count", 5)
    contrarian_markers = signals_cfg.get("contrarian_markers", [])
    scoring_cfg = config.get("scoring", {})

    candidates = []
    candidate_groups = defaultdict(list)

    for tweet in topic_stream:
        text = tweet.get("text") or ""
        total_engagement = compute_engagement(tweet)
        reply_count = tweet.get("public_metrics", {}).get("reply_count", 0)
        like_count = tweet.get("public_metrics", {}).get("like_count", 0)

        follower_count = tweet.get("author_followers")
        engagement_rate = compute_engagement_rate(tweet, follower_count)

        baseline = baseline_rate
        username = (tweet.get("author_username") or "").lower()
        account = accounts.get(username)
        if account and account.get("avg_engagement_rate"):
            baseline = account["avg_engagement_rate"]

        high_engagement = (
            engagement_rate is not None
            and total_engagement >= min_total_engagement
            and engagement_rate >= baseline * high_multiplier
        )
        debate_signal = (
            reply_count >= min_reply_count
            and like_count > 0
            and (reply_count / float(like_count)) >= reply_ratio_threshold
        )
        contrarian_signal = any(marker in text.lower() for marker in contrarian_markers)

        if not (high_engagement or debate_signal or contrarian_signal):
            continue

        keywords_found = extract_keywords(
            text,
            config.get("topic_extraction", {}).get("min_keyword_length", 3),
            config.get("topic_extraction", {}).get("max_keywords", 6),
        )
        topic_key = build_topic_key(keywords_found)
        candidate_groups[topic_key].append(
            {
                "tweet": tweet,
                "keywords": keywords_found,
                "signals": {
                    "high_engagement": high_engagement,
                    "debate": debate_signal,
                    "contrarian": contrarian_signal,
                },
            }
        )

    min_support = config.get("topic_extraction", {}).get("min_supporting_tweets", 2)
    for topic_key, items in candidate_groups.items():
        if len(items) < min_support:
            continue
        keyword_pool = Counter()
        for item in items:
            keyword_pool.update(item["keywords"])
        keywords_sorted = [word for word, _ in keyword_pool.most_common(6)]
        topic_description = build_topic_description(keywords_sorted)
        candidates.append(
            {
                "topic_key": topic_key,
                "topic_description": topic_description,
                "keywords": keywords_sorted,
                "supporting_tweets": [item["tweet"] for item in items],
                "signals": [item["signals"] for item in items],
            }
        )

    write_json(
        args.topic_candidates_out,
        {"dataset": "topic_candidates", "generated_at": fetched_at, "topics": candidates},
    )

    topic_signals = []
    approved_topics = []
    product_keywords = config.get("product_keywords", [])
    similarity_threshold = config.get("deduplication", {}).get("similarity_threshold", 0.5)
    weights = scoring_cfg.get(
        "weights",
        {
            "domain_relevance": 0.3,
            "engagement": 0.3,
            "controversy": 0.15,
            "dark_humor": 0.1,
            "novelty": 0.1,
            "product_relevance": 0.05,
        },
    )
    approval_threshold = scoring_cfg.get("threshold", 70)

    for candidate in candidates:
        domain, domain_score = score_domain_relevance(candidate["keywords"], config.get("topic_scope", []))
        if not domain or domain_score <= 0:
            continue

        product_relevant = detect_product_relevance(candidate["keywords"], product_keywords)
        controversy_score = score_controversy(candidate["signals"], candidate["keywords"], scoring_cfg)
        dark_humor_score = score_dark_humor(candidate["keywords"], scoring_cfg)
        engagement_score, engagement_stats = score_engagement(candidate["supporting_tweets"], signals_cfg)
        novelty_score, max_similarity, redundancy_penalty = score_novelty(
            candidate["keywords"], recent_topics, similarity_threshold, scoring_cfg
        )
        product_score = 100.0 if product_relevant else 0.0

        score_inputs = {
            "domain_relevance": domain_score,
            "engagement": engagement_score,
            "controversy": controversy_score,
            "dark_humor": dark_humor_score,
            "novelty": novelty_score,
            "product_relevance": product_score,
        }
        base_score = weighted_score(score_inputs, weights)
        product_boost = scoring_cfg.get("product_boost", 5.0) if product_relevant else 0.0
        final_score = max(0.0, min(100.0, base_score + product_boost - redundancy_penalty))

        topic_payload = {
            "topic_description": candidate["topic_description"],
            "domain": domain,
            "product_relevant": product_relevant,
            "keywords": candidate["keywords"],
            "supporting_tweets": candidate["supporting_tweets"],
            "signals": candidate["signals"],
            "scores": score_inputs,
            "score_meta": {
                "base_score": base_score,
                "final_score": final_score,
                "product_boost": product_boost,
                "max_similarity": max_similarity,
                "redundancy_penalty": redundancy_penalty,
                "engagement_stats": engagement_stats,
            },
        }

        topic_signals.append(topic_payload)
        if final_score >= approval_threshold:
            approved_topics.append(topic_payload)

    write_json(
        args.topic_signals_out,
        {"dataset": "topic_signals", "generated_at": fetched_at, "topics": topic_signals},
    )
    write_json(
        args.approved_topics_out,
        {"dataset": "approved_topics", "generated_at": fetched_at, "topics": approved_topics},
    )

    print(
        f"Wrote {len(topic_stream)} tweets to {args.topic_stream_out}, "
        f"{len(candidates)} candidates to {args.topic_candidates_out}, "
        f"{len(topic_signals)} signals to {args.topic_signals_out}, "
        f"{len(approved_topics)} approved to {args.approved_topics_out}."
    )


if __name__ == "__main__":
    main()
