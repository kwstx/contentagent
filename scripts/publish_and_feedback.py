import json
import os
import random
import argparse
from datetime import datetime, timezone

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

def simulate_metrics(predicted_score, product_mention):
    # Base impressions on predicted score (e.g., 90 score -> ~1000-2000 impressions)
    base_impressions = predicted_score * random.uniform(10, 25)
    
    # Engagement rates: normally 1-5%
    engagement_rate = random.uniform(0.01, 0.05)
    
    # Product mentions might have slightly lower engagement but high value
    if product_mention:
        engagement_rate *= random.uniform(0.7, 1.1)
    
    total_engagements = base_impressions * engagement_rate
    
    likes = int(total_engagements * random.uniform(0.6, 0.8))
    retweets = int(total_engagements * random.uniform(0.1, 0.2))
    replies = int(total_engagements * random.uniform(0.05, 0.15))
    
    return {
        "impressions": int(base_impressions),
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "normalized_engagement": round((total_engagements / base_impressions) * 100, 2) if base_impressions > 0 else 0
    }

def main():
    parser = argparse.ArgumentParser(description="Publish tweets and collect simulated feedback.")
    parser.add_argument("--optimized", default="data/optimized_tweets.json")
    parser.add_argument("--feedback", default="data/feedback_data.json")
    parser.add_argument("--recent", default="data/recent_tweets.json")
    parser.add_argument("--limit", type=int, default=5, help="Number of tweets to publish")
    args = parser.parse_args()

    optimized_data = load_json(args.optimized)
    if not optimized_data:
        print(f"Error: {args.optimized} not found.")
        return

    optimized_tweets = optimized_data.get("optimized_tweets", [])
    if not optimized_tweets:
        print("No optimized tweets found to publish.")
        return

    # Select top N tweets
    to_publish = optimized_tweets[:args.limit]
    
    feedback_entries = []
    recent_entries = []
    
    from safety import check_safety, log_agent_action
    
    print(f"Publishing {len(to_publish)} tweets...")
    
    for tweet in to_publish:
        # Safety / Autonomy Guard check
        is_safe, reason = check_safety(tweet["text"])
        if not is_safe:
            print(f"Skipping tweet {tweet['tweet_id']} - Safety Violation: {reason}")
            continue

        log_agent_action("publish_attempt", {"tweet_id": tweet["tweet_id"], "text": tweet["text"]})
        
        metrics = simulate_metrics(
            tweet["predicted_engagement_score"], 
            tweet["product_mention"]
        )
        
        entry = {
            "tweet_id": tweet["tweet_id"],
            "concept_id": tweet["concept_id"],
            "topic_id": tweet["topic_id"],
            "structural_template": tweet.get("structural_template"),
            "predicted_engagement_score": tweet["predicted_engagement_score"],
            "actual_engagement_metrics": metrics,
            "product_mention": tweet["product_mention"],
            "timestamp": utc_now_iso(),
            "text": tweet["text"]
        }
        feedback_entries.append(entry)
        
        # For recent_tweets.json
        recent_entries.append({
            "tweet_id": tweet["tweet_id"],
            "text": tweet["text"],
            "published_at": entry["timestamp"]
        })

    # Load existing feedback if any
    existing_feedback = load_json(args.feedback)
    if "feedback_data" not in existing_feedback:
        existing_feedback = {
            "dataset": "feedback_data",
            "updated_at": utc_now_iso(),
            "entries": []
        }
    
    existing_feedback["entries"].extend(feedback_entries)
    existing_feedback["updated_at"] = utc_now_iso()
    write_json(args.feedback, existing_feedback)
    
    # Update recent_tweets
    recent_data = load_json(args.recent)
    if "tweets" not in recent_data:
        recent_data = {
            "dataset": "recent_tweets",
            "updated_at": utc_now_iso(),
            "tweets": []
        }
    
    recent_data["tweets"].extend(recent_entries)
    # Keep only last 100
    recent_data["tweets"] = recent_data["tweets"][-100:]
    recent_data["updated_at"] = utc_now_iso()
    write_json(args.recent, recent_data)

    # Perform analysis
    print("\n--- Feedback Analysis Summary ---")
    template_perf = {}
    for entry in feedback_entries:
        tpl = entry["structural_template"]
        score = entry["actual_engagement_metrics"]["normalized_engagement"]
        if tpl not in template_perf:
            template_perf[tpl] = []
        template_perf[tpl].append(score)
    
    print("Template Performance (Avg Normalized Engagement):")
    for tpl, scores in template_perf.items():
        avg = sum(scores) / len(scores)
        print(f"  {tpl}: {avg:.2f}")

    product_stats = [e["actual_engagement_metrics"]["normalized_engagement"] for e in feedback_entries if e["product_mention"]]
    non_product_stats = [e["actual_engagement_metrics"]["normalized_engagement"] for e in feedback_entries if not e["product_mention"]]
    
    if product_stats:
        print(f"Product Mention Avg Engagement: {sum(product_stats)/len(product_stats):.2f}")
    if non_product_stats:
        print(f"Non-Product Avg Engagement: {sum(non_product_stats)/len(non_product_stats):.2f}")

    print(f"\nFeedback data written to {args.feedback}")
    print(f"Recent tweets updated in {args.recent}")

if __name__ == "__main__":
    main()
