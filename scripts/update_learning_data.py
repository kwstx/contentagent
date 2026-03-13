import json
import os
import argparse
import re
import math
from datetime import datetime, timezone
from collections import defaultdict

# Reuse some helper functions structure
def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_json(path):
    if not os.path.exists(path):
        return {}
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

def extract_keywords(text, stop_words, min_length=3, max_keywords=8):
    tokens = [
        token
        for token in normalize_text(text).split()
        if token not in stop_words and len(token) >= min_length
    ]
    if not tokens:
        return []
    counts = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    keywords = sorted(counts.keys(), key=lambda k: counts[k], reverse=True)
    return keywords[:max_keywords]

def main():
    parser = argparse.ArgumentParser(description="Iterative Learning: Update datasets based on tweet performance.")
    parser.add_argument("--feedback", default="data/feedback_data.json")
    parser.add_argument("--viral", default="data/viral_tweet_dataset.json")
    parser.add_argument("--topics", default="data/approved_topics.json")
    parser.add_argument("--patterns", default="data/tweet_patterns.json")
    parser.add_argument("--config", default="data/topic_discovery_config.json")
    parser.add_argument("--viral-config", default="data/viral_tweet_config.json")
    parser.add_argument("--threshold", type=float, default=3.0, help="Engagement threshold for high-performing tweets")
    args = parser.parse_args()

    # 1. Load Data
    feedback_data = load_json(args.feedback)
    if not feedback_data or "entries" not in feedback_data:
        print("No feedback data found.")
        return

    viral_dataset = load_json(args.viral)
    approved_topics = load_json(args.topics)
    patterns_data = load_json(args.patterns)
    topic_config = load_json(args.config)
    viral_config = load_json(args.viral_config)

    # 2. Performance-Based Tweet Selection & Dataset Augmentation
    print(f"Analyzing {len(feedback_data['entries'])} feedback entries...")
    
    stop_words = {"a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "we", "with", "you"}
    
    high_perf_count = 0
    topic_perf = defaultdict(list)
    template_perf = defaultdict(list)
    product_perf = {"true": [], "false": []}
    
    new_viral_tweets = []
    
    # Track existing viral tweets to avoid duplicates
    existing_ids = {t.get("tweet_id") for t in viral_dataset.get("tweets", []) if t.get("tweet_id")}
    
    for entry in feedback_data["entries"]:
        metrics = entry["actual_engagement_metrics"]
        norm_eng = metrics["normalized_engagement"]
        
        # Track statistics
        topic_perf[entry["topic_id"]].append(norm_eng)
        template_perf[entry["structural_template"]].append(norm_eng)
        product_perf[str(entry["product_mention"]).lower()].append(norm_eng)
        
        # Determine if high-performing
        passes_threshold = norm_eng >= args.threshold
        
        if passes_threshold:
            high_perf_count += 1
            if entry["tweet_id"] not in existing_ids:
                # Map feedback entry to viral tweet format
                # We need some fields that are in viral_tweet_dataset but not in feedback_data
                # We'll do a best-effort mapping
                record = {
                    "tweet_id": entry["tweet_id"],
                    "text": entry["text"],
                    "created_at": entry["timestamp"],
                    "public_metrics": {
                        "like_count": metrics["likes"],
                        "reply_count": metrics["replies"],
                        "retweet_count": metrics["retweets"],
                        "impression_count": metrics["impressions"]
                    },
                    "engagement_total": metrics["likes"] + metrics["replies"] + metrics["retweets"],
                    "normalized_engagement": norm_eng / 100.0, # Convert back to ratio for consistency with viral_tweet_dataset if needed? 
                    # Wait, build_viral_tweet_dataset uses ratio. Feedback uses percentage. 
                    # Let's check viral_tweet_dataset normalization threshold. It's 0.01 (1%).
                    # So 4.6 should be 0.046.
                    "source_type": "published_feedback",
                    "topic": {
                        "label": entry["topic_id"], # We'll use topic_id as label or look it up
                        "keywords": extract_keywords(entry["text"], stop_words)
                    },
                    "product_context": {
                        "relevant": entry["product_mention"],
                        "matched_keywords": ["Engram"] if entry["product_mention"] else []
                    },
                    "passes_threshold": True,
                    "collected_at": utc_now_iso()
                }
                
                # Try to fill in more details if we can find them from approved_topics
                for t in approved_topics.get("topics", []):
                    if t["topic_id"] == entry["topic_id"]:
                        record["topic"]["label"] = t["domain"]
                        break
                
                new_viral_tweets.append(record)

    # Update Viral Dataset
    if new_viral_tweets:
        if "tweets" not in viral_dataset:
            viral_dataset["tweets"] = []
        viral_dataset["tweets"].extend(new_viral_tweets)
        viral_dataset["generated_at"] = utc_now_iso()
        viral_dataset["counts"]["accepted"] = len(viral_dataset["tweets"])
        write_json(args.viral, viral_dataset)
        print(f"Added {len(new_viral_tweets)} high-performing tweets to viral_tweet_dataset.")

    # 3. Topic Performance Updating & Topic Scoring Adjustment
    print("\nUpdating topic performance scores...")
    for topic in approved_topics.get("topics", []):
        tid = topic["topic_id"]
        if tid in topic_perf:
            scores = topic_perf[tid]
            avg_eng = sum(scores) / len(scores)
            
            # Map avg_eng (0-10% range usually) to 0-100 score
            # 5% -> 100, 0% -> 0
            new_engagement_score = min(100, (avg_eng / 5.0) * 100)
            
            # Update scores with some smoothing (e.g., 0.3 alpha)
            old_score = topic["scores"].get("engagement", 50.0)
            topic["scores"]["engagement"] = round(0.7 * old_score + 0.3 * new_engagement_score, 2)
            
            # Update engagement_stats in score_meta
            if "engagement_stats" not in topic["score_meta"]:
                topic["score_meta"]["engagement_stats"] = {}
            
            topic["score_meta"]["engagement_stats"]["actual_avg"] = round(avg_eng, 3)
            topic["score_meta"]["engagement_stats"]["sample_count"] = len(scores)
            
            # Recalculate final_score
            # Simplified version of the complex scoring logic in build_approved_topics
            base_score = (
                topic["scores"].get("domain_relevance", 50) * 0.25 +
                topic["scores"].get("engagement", 50) * 0.25 +
                topic["scores"].get("controversy", 50) * 0.15 +
                topic["scores"].get("novelty", 50) * 0.2 +
                topic["scores"].get("dark_humor", 50) * 0.15
            )
            topic["score_meta"]["base_score"] = round(base_score, 2)
            topic["score_meta"]["final_score"] = round(base_score + topic["score_meta"].get("product_boost", 0), 2)

    approved_topics["generated_at"] = utc_now_iso()
    write_json(args.topics, approved_topics)
    print(f"Updated {len(topic_perf)} topics in approved_topics.json.")

    # 4. Product-Relevance Performance Analysis
    print("\nProduct-Relevance Analysis:")
    prod_avg = sum(product_perf["true"]) / len(product_perf["true"]) if product_perf["true"] else 0
    non_prod_avg = sum(product_perf["false"]) / len(product_perf["false"]) if product_perf["false"] else 0
    print(f"  Product Mention Avg: {prod_avg:.2f}%")
    print(f"  Non-Product Avg:    {non_prod_avg:.2f}%")
    
    # Adjust product boost if product tweets are performing significantly better or worse
    # (Optional: this could be saved to topic_discovery_config.json)

    # 5. Continuous Learning: Call Pattern Reinforcement
    # Instead of just calling the script, we'll let the user know they can run it
    # or we can try to run it via run_command after this script finishes.
    # But since we've updated viral_tweet_dataset, calling build_tweet_patterns.py is natural.
    print("\nLearning cycle complete. Suggestions:")
    print("1. Run 'python scripts/build_tweet_patterns.py' to reinforce successful patterns.")
    print("2. Run 'python scripts/optimize_tweets.py' to use updated topic weights.")

if __name__ == "__main__":
    main()
