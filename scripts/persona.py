import os

def get_agent_system_prompt(agents_md_path="AGENTS.md"):
    if not os.path.exists(agents_md_path):
        return "You are a professional tech insider agent."
    
    with open(agents_md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract only the relevant sections (Style and Topic Scope)
    # Exclude Ranking Rules which are for a different stage
    sections = []
    current_section = []
    
    lines = content.split("\n")
    capturing = False
    for line in lines:
        if line.startswith("# Tweet Style Rules") or line.startswith("# Topic Scope Rules"):
            capturing = True
        elif line.startswith("# Tweet Ranking Rules"):
            capturing = False
            
        if capturing:
            current_section.append(line)
            
    relevant_content = "\n".join(current_section)
    
    return f"""
YOU ARE THE XAGENT CONTENT AGENT. You must follow these strict rules:

{relevant_content}

---
CRITICAL INSTRUCTIONS:
1. No emojis OR hashtags.
2. Tone: Professional, opinionated, insider.
3. Structure: Hook statement -> Argument/Insight -> Subtle dark humor/cynical twist.
4. Length: 180-260 characters.
5. Content: ONLY the tweet text. No meta-commentary.
"""
