import json
import os
import argparse
from datetime import datetime, timezone
from llm_client import LLMClient
from persona import get_agent_system_prompt

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def main():
    parser = argparse.ArgumentParser(description="Generate tweets using a local LLM.")
    parser.add_argument("--concepts", default="data/tweet_concepts.json")
    parser.add_argument("--topics", default="data/approved_topics.json")
    parser.add_argument("--model", default="qwen2.5-coder:1.5b", help="Model to use (default: qwen2.5-coder:1.5b)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of concepts to process (0 for all)")
    args = parser.parse_args()

    concepts_data = load_json(args.concepts)
    topics_data = load_json(args.topics)
    
    concepts = concepts_data.get("concepts", [])
    topic_lookup = {t["topic_id"]: t for t in topics_data.get("topics", [])}
    
    client = LLMClient(model=args.model)
    system_prompt = get_agent_system_prompt()
    
    generated_tweets = []
    
    to_process = concepts[:args.limit] if args.limit > 0 else concepts
    print(f"Generating tweets for {len(to_process)} concepts using LLM ({args.model})...")
    
    for i, concept in enumerate(to_process):
        topic_id = concept.get("topic_id", "unknown")
        topic = topic_lookup.get(topic_id, {})
        topic_desc = topic.get("topic_description", topic_id)
        
        print(f"[{i+1}/{len(to_process)}] Generating tweet for: {topic_desc[:50]}...")
        
        prompt = f"""
        Task: Write a new 3-line tweet about {topic_desc}.
        Line 1: A surprising or controversial claim.
        Line 2: An insight about: {concept['core_insight']}
        Line 3: A dark, cynical twist.
        
        Style Rules:
        - Exactly 3 lines (use Enter).
        - No bolding (**), no labels (Hook:), no hashtags.
        - Tone: Opinionated, professional, and cynical.
        - Length: 180-260 characters total.
        
        Example (DO NOT COPY THIS TEXT):
        Founders optimize for headcount optics instead of actual growth reality.
        Then they wonder why the burn rate bottleneck kills the product before launch.
        The postmortem will say "bad timing," which is how you know nobody learned.
        """
        # Note: We provide only ONE example to avoid confusing the small model.
        
        tweet_text = client.generate(prompt, system_prompt=system_prompt)
        if tweet_text:
            tweet_text = tweet_text.strip().strip('"')
            generated_tweets.append({
                "tweet_id": f"g-llm-{len(generated_tweets):04d}",
                "concept_id": concept.get("concept_id", "unknown"),
                "topic_id": topic_id,
                "text": tweet_text,
                "char_count": len(tweet_text),
                "model": args.model,
                "generated_at": utc_now_iso()
            })
            print(f"  > Created: {tweet_text[:60]}...")
        else:
            print(f"  > Failed to generate tweet for {topic_id}")

    write_json("data/generated_tweets.json", {
        "dataset": "generated_tweets",
        "generated_at": utc_now_iso(),
        "tweet_count": len(generated_tweets),
        "generated_tweets": generated_tweets
    })
    print(f"\nWrote {len(generated_tweets)} tweets to data/generated_tweets.json")

if __name__ == "__main__":
    main()
