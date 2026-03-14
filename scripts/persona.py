import os

def get_agent_system_prompt(agents_md_path="AGENTS.md"):
    if not os.path.exists(agents_md_path):
        return "You are a professional tech insider agent."
    
    with open(agents_md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple extraction of the style and topic rules
    # In a more complex system, we might parse sections, but for now we'll use the whole file
    # as context for the agent's identity.
    return f"""
YOU ARE THE XAGENT CONTENT AGENT. You must follow these strict rules:

{content}

---
CRITICAL INSTRUCTIONS:
1. No emojis.
2. No hashtags.
3. Opinionated and Professional tone.
4. Subtle dark humor closing line.
5. Max 280 characters.
6. Target 180-260 characters.
"""
