import json
import os

def check_safety(tweet_text):
    """
    Simulates Autonomy Guard safety checks.
    In a real production environment, this would call the mcp_autonomy-guard_authorize_action tool.
    """
    # 1. Length Check
    if len(tweet_text) > 280:
        return False, "Exceeds 280 characters"
    
    # 2. No Hashtags/Emojis
    if "#" in tweet_text:
        return False, "Contains hashtags"
    
    # 3. Basic Toxicity/Topic check (Placeholder)
    # This is where the agent verifies the content aligns with its scope
    return True, None

def log_agent_action(action_type, payload):
    """Logs agent actions for transparency."""
    log_file = "data/agent_actions.json"
    logs = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            logs = json.load(f)
    
    logs.append({
        "timestamp": os.environ.get("CURRENT_TIME", "unknown"),
        "action": action_type,
        "payload": payload
    })
    
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)
