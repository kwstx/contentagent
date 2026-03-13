import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone


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
    ("startups", {"startup", "founder", "funding", "vc", "venture"}),
    ("business strategy", {"strategy", "growth", "pricing", "distribution", "market"}),
    ("technology news", {"release", "launch", "announce", "news", "update"}),
    ("technology", {"tech", "infrastructure", "cloud", "hardware", "platform"}),
]


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


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
    counts = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    keywords = sorted(counts.keys(), key=lambda k: counts[k], reverse=True)
    return keywords[:max_keywords]


def classify_domain(keywords, topic_scope):
    keyword_set = set(keywords)
    for domain, terms in DOMAIN_TERMS:
        if domain not in topic_scope:
            continue
        if keyword_set.intersection(terms):
            return domain
    return None


def detect_product_relevance(text, product_keywords):
    text_norm = normalize_text(text)
    for phrase in product_keywords:
        phrase_norm = normalize_text(phrase)
        if phrase_norm and phrase_norm in text_norm:
            return True, [phrase]
    token_set = set(text_norm.split())
    matches = []
    for phrase in product_keywords:
        parts = normalize_text(phrase).split()
        if token_set.intersection(parts):
            matches.append(phrase)
    if matches:
        return True, matches[:5]
    return False, []


def compute_engagement(metrics):
    return (
        metrics.get("like_count", 0)
        + metrics.get("reply_count", 0)
        + metrics.get("retweet_count", 0)
        + metrics.get("quote_count", 0)
    )


def compute_normalized_engagement(metrics, follower_count, impressions_weight):
    if not follower_count:
        return None
    engagement = compute_engagement(metrics)
    impressions = metrics.get("impression_count")
    weighted = engagement
    if impressions is not None:
        weighted += impressions * impressions_weight
    return weighted / float(follower_count)


def split_sentences(text):
    sentences = re.split(r"[.!?]+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def extract_punctuation(text):
    return {
        "question": text.count("?"),
        "exclamation": text.count("!"),
        "colon": text.count(":"),
        "semicolon": text.count(";"),
        "dash": text.count("-") + text.count("β€“") + text.count("β€”"),
    }


def detect_contrarian(text, contrarian_markers):
    text_lower = text.lower()
    for marker in contrarian_markers:
        if marker.lower() in text_lower:
            return True
    return False


def detect_opinionated(text):
    markers = [
        "must",
        "should",
        "never",
        "always",
        "stop",
        "broken",
        "wrong",
        "overrated",
        "underrated",
        "the real problem",
        "everyone is wrong",
        "nobody wants",
        "we keep pretending",
    ]
    text_lower = text.lower()
    return any(marker in text_lower for marker in markers)


def detect_professional_tone(text):
    casual_markers = ["lol", "lmao", "wtf", "omg", "idk", "smh"]
    text_lower = text.lower()
    if any(marker in text_lower for marker in casual_markers):
        return False
    return True


def detect_dark_humor(text, dark_humor_keywords):
    text_lower = text.lower()
    for marker in dark_humor_keywords:
        if marker.lower() in text_lower:
            return True
    return False


def build_features(text, contrarian_markers):
    sentences = split_sentences(text)
    hook_index = 0
    contrarian = detect_contrarian(text, contrarian_markers)
    if sentences:
        hook_index = 0
    return {
        "char_length": len(text),
        "sentence_count": len(sentences),
        "line_breaks": text.count("\n"),
        "hook_sentence_index": hook_index,
        "hook_is_opening": hook_index == 0,
        "strong_opening": bool(sentences) and (contrarian or len(sentences[0]) <= 120),
        "contrarian_claim": contrarian,
        "punctuation": extract_punctuation(text),
    }


def build_style_labels(text, contrarian_markers, dark_humor_keywords):
    professional = detect_professional_tone(text)
    opinionated = detect_opinionated(text)
    controversial = detect_contrarian(text, contrarian_markers) or opinionated
    dark_humor = detect_dark_humor(text, dark_humor_keywords)
    alignment = "high" if (professional and opinionated and controversial and dark_humor) else "low"
    return {
        "professional_tone": professional,
        "opinionated": opinionated,
        "controversial": controversial,
        "dark_humor": dark_humor,
        "alignment": alignment,
    }


def compute_recency_weight(created_at, half_life_days):
    if not created_at:
        return 0.5
    created = parse_iso(created_at)
    if created is None:
        return 0.5
    age_days = max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 86400.0)
    decay = 0.5 ** (age_days / max(1.0, float(half_life_days)))
    return max(0.1, min(1.0, decay))


def read_int(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def load_manual_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Build viral tweet dataset from manual CSV input."
    )
    parser.add_argument(
        "--config",
        default=os.path.join("data", "viral_tweet_config.json"),
        help="Path to viral_tweet_config.json",
    )
    parser.add_argument(
        "--topic-config",
        default=os.path.join("data", "topic_discovery_config.json"),
        help="Path to topic_discovery_config.json",
    )
    parser.add_argument(
        "--input",
        default=os.path.join("data", "manual_viral_tweets.csv"),
        help="Path to manual_viral_tweets.csv",
    )
    parser.add_argument(
        "--candidates-out",
        default=os.path.join("data", "candidate_viral_tweets.json"),
        help="Output path for candidate_viral_tweets.json",
    )
    parser.add_argument(
        "--dataset-out",
        default=os.path.join("data", "viral_tweet_dataset.json"),
        help="Output path for viral_tweet_dataset.json",
    )
    parser.add_argument("--no-append", action="store_true", help="Do not append to existing dataset")
    args = parser.parse_args()

    config = load_json(args.config)
    topic_cfg = load_json(args.topic_config)
    topic_scope = config.get("topic_scope") or topic_cfg.get("topic_scope", [])

    product_keywords = config.get("product_keywords") or topic_cfg.get("product_keywords", [])
    contrarian_markers = config.get("contrarian_markers") or topic_cfg.get("signals", {}).get(
        "contrarian_markers", []
    )
    dark_humor_keywords = config.get("dark_humor_keywords") or topic_cfg.get("scoring", {}).get(
        "dark_humor_keywords", []
    )

    normalization_cfg = config.get("normalization", {})
    min_followers = normalization_cfg.get("min_followers", 250)
    min_total_engagement = normalization_cfg.get("min_total_engagement", 20)
    normalized_threshold = normalization_cfg.get("normalized_engagement_threshold", 0.01)
    impressions_weight = normalization_cfg.get("impressions_weight", 0.02)
    half_life_days = normalization_cfg.get("recency_half_life_days", 120)

    min_keyword_length = config.get("feature_extraction", {}).get("min_keyword_length", 3)
    max_keywords = config.get("feature_extraction", {}).get("max_keywords", 8)

    fetched_at = utc_now_iso()
    rows = load_manual_csv(args.input)

    candidate_rows = []
    viral_rows = []

    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue

        metrics = {
            "like_count": read_int(row.get("like_count")) or 0,
            "reply_count": read_int(row.get("reply_count")) or 0,
            "retweet_count": read_int(row.get("retweet_count")) or 0,
            "quote_count": read_int(row.get("quote_count")) or 0,
        }
        impression_count = read_int(row.get("impression_count"))
        if impression_count is not None:
            metrics["impression_count"] = impression_count

        followers = read_int(row.get("author_followers"))
        engagement_total = compute_engagement(metrics)
        normalized = compute_normalized_engagement(metrics, followers, impressions_weight)

        keywords = extract_keywords(text, min_keyword_length, max_keywords)
        domain = classify_domain(keywords, topic_scope)
        if not domain:
            continue

        passes_threshold = (
            followers is not None
            and followers >= min_followers
            and engagement_total >= min_total_engagement
            and normalized is not None
            and normalized >= normalized_threshold
        )

        features = build_features(text, contrarian_markers)
        style = build_style_labels(text, contrarian_markers, dark_humor_keywords)
        product_relevant, product_matches = detect_product_relevance(text, product_keywords)

        record = {
            "tweet_id": row.get("tweet_id") or None,
            "text": text,
            "created_at": row.get("created_at") or None,
            "url": row.get("url") or None,
            "author_username": row.get("author_username") or None,
            "author_id": row.get("author_id") or None,
            "author_followers": followers,
            "public_metrics": metrics,
            "engagement_total": engagement_total,
            "normalized_engagement": normalized,
            "source_type": row.get("source_type") or "manual",
            "source_query": row.get("source_query") or "manual_collection",
            "topic": {"label": domain, "keywords": keywords[:6]},
            "features": features,
            "style": style,
            "product_context": {"relevant": product_relevant, "matched_keywords": product_matches},
            "recency_weight": compute_recency_weight(row.get("created_at"), half_life_days),
            "collected_at": fetched_at,
            "passes_threshold": passes_threshold,
        }

        candidate_rows.append(record)
        if passes_threshold:
            viral_rows.append(record)

    if not args.no_append and os.path.exists(args.dataset_out):
        existing = load_json(args.dataset_out)
        existing_rows = {row.get("tweet_id") or row.get("url"): row for row in existing.get("tweets", [])}
        for row in viral_rows:
            key = row.get("tweet_id") or row.get("url")
            if key:
                existing_rows[key] = row
        viral_rows = list(existing_rows.values())

    candidate_payload = {
        "dataset": "candidate_viral_tweets",
        "generated_at": fetched_at,
        "source_summary": {"manual_collection": len(candidate_rows)},
        "normalization": {
            "min_followers": min_followers,
            "min_total_engagement": min_total_engagement,
            "normalized_engagement_threshold": normalized_threshold,
            "impressions_weight": impressions_weight,
        },
        "candidates": candidate_rows,
    }

    viral_payload = {
        "dataset": "viral_tweet_dataset",
        "generated_at": fetched_at,
        "topic_scope": topic_scope,
        "normalization": {
            "min_followers": min_followers,
            "min_total_engagement": min_total_engagement,
            "normalized_engagement_threshold": normalized_threshold,
            "impressions_weight": impressions_weight,
            "recency_half_life_days": half_life_days,
        },
        "counts": {"candidates": len(candidate_rows), "accepted": len(viral_rows)},
        "tweets": viral_rows,
    }

    write_json(args.candidates_out, candidate_payload)
    write_json(args.dataset_out, viral_payload)

    print(
        f"Wrote {len(candidate_rows)} candidates to {args.candidates_out} "
        f"and {len(viral_rows)} viral tweets to {args.dataset_out}."
    )


if __name__ == "__main__":
    main()
