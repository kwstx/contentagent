import argparse
import json
import math
import os
import re
from datetime import datetime, timezone


TARGET_MIN = 180
TARGET_MAX = 260
MAX_LEN = 280
DEFAULT_TOP_N = 12
DEFAULT_PRODUCT_RATIO = 0.15


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def token_set(text):
    return set(normalize_text(text).split())


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a.union(b))
    if not union:
        return 0.0
    return inter / float(union)


def detect_dark_humor(text, keywords):
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


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
    lower = text.lower()
    return any(marker in lower for marker in markers)


def detect_professional(text):
    casual = ["lol", "lmao", "wtf", "omg", "idk", "smh"]
    lower = text.lower()
    return not any(marker in lower for marker in casual)


def detect_controversial(text, contrarian_markers):
    lower = text.lower()
    if detect_opinionated(text):
        return True
    return any(marker.lower() in lower for marker in contrarian_markers)


def valid_ascii(text):
    return all(ord(ch) < 128 for ch in text)


def validate_style(text, tone_flags, contrarian_markers):
    if not (TARGET_MIN <= len(text) <= MAX_LEN):
        return False, "length"
    if len(text) > TARGET_MAX:
        return False, "target_range"
    if "#" in text:
        return False, "hashtag"
    if "!!" in text or "??" in text:
        return False, "excess_punct"
    if not valid_ascii(text):
        return False, "non_ascii"
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) < 3:
        return False, "structure"
    professional = "professional" in tone_flags or detect_professional(text)
    opinionated = "opinionated" in tone_flags or detect_opinionated(text)
    controversial = "controversial" in tone_flags or detect_controversial(text, contrarian_markers)
    if not (professional and opinionated and controversial):
        return False, "tone"
    return True, None


def product_integration_ok(text):
    if "Engram" not in text:
        return False
    lower = text.lower()
    blocked = ["signup", "sign up", "buy", "get started", "try now", "limited offer", "discount"]
    if any(token in lower for token in blocked):
        return False
    if "http" in lower:
        return False
    return True


def build_viral_index(viral_rows):
    index = []
    for row in viral_rows:
        text = row.get("text", "")
        norm_eng = row.get("normalized_engagement")
        if not text or norm_eng is None:
            continue
        index.append((token_set(text), float(norm_eng)))
    return index


def historical_engagement_score(tokens, viral_index):
    if not viral_index:
        return 0.0, 0.0
    best_sim = 0.0
    best_eng = 0.0
    for other_tokens, norm_eng in viral_index:
        sim = jaccard(tokens, other_tokens)
        if sim > best_sim:
            best_sim = sim
            best_eng = norm_eng
    scaled = min(1.0, best_eng * 50.0)
    return scaled, best_sim


def compute_model_score(candidate, topic, config, viral_index):
    text = candidate["text"]
    hook_type = candidate.get("hook_type")
    tokens = token_set(text)

    score = 50.0
    length = len(text)
    if TARGET_MIN <= length <= TARGET_MAX:
        score += 12
    else:
        score -= 12

    if hook_type == "contrarian":
        score += 8
    elif hook_type == "curiosity":
        score += 6
    else:
        score += 4

    if text.count("\n") >= 2:
        score += 6

    if "?" in text.split("\n")[0]:
        score += 3

    if "!" in text:
        score -= min(8, text.count("!") * 3)

    contrarian_markers = config.get("signals", {}).get("contrarian_markers", [])
    dark_humor_keywords = config.get("scoring", {}).get("dark_humor_keywords", [])

    if detect_controversial(text, contrarian_markers):
        score += 6

    if detect_dark_humor(text, dark_humor_keywords):
        score += 5

    topic_scores = topic.get("scores", {})
    score += (topic_scores.get("domain_relevance", 50.0) - 50.0) * 0.12
    score += (topic_scores.get("engagement", 50.0) - 50.0) * 0.1
    score += (topic_scores.get("novelty", 50.0) - 50.0) * 0.1
    score += (topic_scores.get("controversy", 50.0) - 50.0) * 0.08

    hist_score, viral_similarity = historical_engagement_score(tokens, viral_index)
    score += hist_score

    return max(0.0, min(100.0, round(score, 2))), viral_similarity


def similarity_penalty(text, recent_texts, max_penalty):
    tokens = token_set(text)
    max_sim = 0.0
    for recent in recent_texts:
        sim = jaccard(tokens, token_set(recent))
        max_sim = max(max_sim, sim)
    penalty = max_sim * max_penalty
    return penalty, max_sim


def main():
    parser = argparse.ArgumentParser(description="Rank generated tweets for engagement.")
    parser.add_argument("--generated", default="data/generated_tweets.json")
    parser.add_argument("--approved-topics", default="data/approved_topics.json")
    parser.add_argument("--viral", default="data/viral_tweet_dataset.json")
    parser.add_argument("--config", default="data/topic_discovery_config.json")
    parser.add_argument("--recent", default="data/recent_tweets.json")
    parser.add_argument("--out", default="data/ranked_tweets.json")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--product-ratio", type=float, default=DEFAULT_PRODUCT_RATIO)
    args = parser.parse_args()

    generated = load_json(args.generated)
    approved = load_json(args.approved_topics)
    config = load_json(args.config)
    viral = load_json(args.viral)

    recent_texts = []
    recent_meta = {"path": args.recent, "count": 0, "loaded": False}
    if os.path.exists(args.recent):
        recent_data = load_json(args.recent)
        recent_texts = [row.get("text", "") for row in recent_data.get("tweets", []) if row.get("text")]
        recent_meta["count"] = len(recent_texts)
        recent_meta["loaded"] = True

    topic_scope = config.get("topic_scope", [])
    topic_lookup = {topic["topic_id"]: topic for topic in approved.get("topics", [])}

    viral_index = build_viral_index(viral.get("tweets", []))

    contrarian_markers = config.get("signals", {}).get("contrarian_markers", [])
    max_similarity_penalty = config.get("scoring", {}).get("max_similarity_penalty", 15)
    product_boost = config.get("scoring", {}).get("product_boost", 5)

    ranked_candidates = []
    rejected = []

    for candidate in generated.get("generated_tweets", []):
        topic_id = candidate.get("topic_id")
        topic = topic_lookup.get(topic_id)
        if not topic:
            rejected.append({"tweet_id": candidate.get("tweet_id"), "reason": "unknown_topic"})
            continue
        if topic.get("domain") not in topic_scope:
            rejected.append({"tweet_id": candidate.get("tweet_id"), "reason": "out_of_scope"})
            continue

        tone_flags = candidate.get("tone_flags", [])
        ok, reason = validate_style(candidate["text"], tone_flags, contrarian_markers)
        if not ok:
            rejected.append({"tweet_id": candidate.get("tweet_id"), "reason": reason})
            continue

        base_score, viral_similarity = compute_model_score(candidate, topic, config, viral_index)

        penalty, recent_similarity = similarity_penalty(candidate["text"], recent_texts, max_similarity_penalty)

        product_mention = candidate.get("product_mention", False)
        product_ok = product_mention and product_integration_ok(candidate["text"])
        final_score = base_score - penalty
        product_applied = False
        if product_ok:
            final_score += product_boost
            product_applied = True

        final_score = max(0.0, min(100.0, round(final_score, 2)))

        ranked_candidates.append(
            {
                "tweet_id": candidate["tweet_id"],
                "concept_id": candidate["concept_id"],
                "topic_id": topic_id,
                "hook_type": candidate.get("hook_type"),
                "tone_flags": candidate.get("tone_flags", []),
                "product_mention": product_mention,
                "product_boost_applied": product_applied,
                "structural_template": candidate.get("structural_template"),
                "predicted_engagement_score": final_score,
                "score_breakdown": {
                    "model_score": base_score,
                    "product_boost": product_boost if product_applied else 0.0,
                    "diversity_penalty": round(penalty, 2),
                    "max_recent_similarity": round(recent_similarity, 3),
                    "max_viral_similarity": round(viral_similarity, 3),
                },
                "text": candidate["text"],
                "char_count": candidate.get("char_count", len(candidate["text"])),
            }
        )

    ranked_candidates.sort(key=lambda row: row["predicted_engagement_score"], reverse=True)

    top_n = max(1, args.top)
    product_cap = max(1, int(math.floor(top_n * args.product_ratio)))
    selected = []
    product_count = 0

    for row in ranked_candidates:
        if len(selected) >= top_n:
            break
        if row["product_mention"] and product_count >= product_cap:
            continue
        selected.append(row)
        if row["product_mention"]:
            product_count += 1

    payload = {
        "dataset": "ranked_tweets",
        "generated_at": utc_now_iso(),
        "source_dataset": {
            "path": args.generated,
            "tweet_count": len(generated.get("generated_tweets", [])),
        },
        "ranking_config": {
            "target_char_range": [TARGET_MIN, TARGET_MAX],
            "max_characters": MAX_LEN,
            "top_n": top_n,
            "product_ratio_cap": args.product_ratio,
            "product_cap": product_cap,
            "recent_tweets": recent_meta,
        },
        "rejected_count": len(rejected),
        "rejections": rejected[:100],
        "candidate_count": len(ranked_candidates),
        "ranked_count": len(selected),
        "ranked_tweets": selected,
    }

    write_json(args.out, payload)
    print(f"Wrote {len(selected)} ranked tweets to {args.out}")


if __name__ == "__main__":
    main()
