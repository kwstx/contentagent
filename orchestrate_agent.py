import os
import subprocess
import time
import sys

def run_script(script_name, args=[]):
    print(f"\n>>> Running {script_name}...")
    cmd = [sys.executable, f"scripts/{script_name}.py"] + args
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"Error running {script_name}")
        return False
    return True

def main():
    print("=== Xagent Autonomy Loop Started ===")
    
    # 1. Topic Discovery
    if not run_script("topic_discovery"):
        print("Topic discovery failed. Check X_BEARER_TOKEN.")
    
    # 2. Build Concepts
    run_script("build_tweet_concepts")
    
    # 3. Generate Tweets via LLM
    # Note: Assumes local Ollama is running
    run_script("generate_tweets_llm")
    
    # 4. Rank Tweets (Currently uses heuristic, could be refactored to use LLM as judge)
    run_script("rank_tweets")
    
    # 5. Optimize (Polishing)
    run_script("optimize_tweets")
    
    # 6. Publish and Feedback
    run_script("publish_and_feedback", ["--limit", "2"])
    
    print("\n=== Xagent Cycle Complete ===")

if __name__ == "__main__":
    main()
