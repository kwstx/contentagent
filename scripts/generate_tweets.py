import json
import re
from datetime import datetime, timezone

TARGET_MIN = 180
TARGET_MAX = 260
MAX_LEN = 280

DARK_CLOSES = [
    "The postmortem will blame process, and nothing will change.",
    "Everyone will agree on the root cause, then ignore it again.",
    "The dashboard will call it progress, right before the next incident.",
    "The roadmap will promise fixes, and the calendar will disagree.",
    "The retrofit will arrive right after the damage report.",
]

PRODUCT_CLOSES = [
    "Engram exists because coordination is engineering, not vibes. Meetings still happen.",
    "Engram shows coordination is a system problem, not a culture deck. The meetings remain.",
]

HOOK_VARIANTS = {
    "contrarian": [
        "Most teams blame tools for {subject}, but the friction is coordination, not capability.",
        "The popular take on {subject} is wrong. Coordination is the bottleneck, not capability.",
        "We keep blaming tools for {subject}. Coordination is the real tax.",
        "The real problem in {subject} is coordination, not capability.",
    ],
    "curiosity": [
        "The quiet part about {subject}: the hard part is rarely technical.",
        "What nobody admits about {subject} is that the hard part is rarely technical.",
        "If {subject} feels hard, it is rarely technical.",
        "The part nobody says about {subject}: it is rarely technical.",
    ],
    "analytical": [
        "The bottleneck in {subject} is the incentive structure, not the algorithm.",
        "{subject} fails when incentives beat the algorithm.",
        "In {subject}, incentives are the constraint, not the model.",
        "In {subject}, incentives beat the algorithm.",
    ],
}

CORE_SHORTEN = {
    "Infrastructure reality keeps refusing to match the slide deck.": "Infrastructure refuses to match the slide deck.",
    "Infrastructure keeps refusing to match the slide deck.": "Infrastructure refuses to match the slide deck.",
    "Teams ship clever agents, then wonder why they behave like strangers in a crowded room.": "Teams ship clever agents, then wonder why they drift apart.",
    "Teams ship clever agents, then wonder why they drift apart.": "Teams ship clever agents, then wonder why they drift.",
    "Regulation headlines promise safety while product teams keep shipping the same risks faster.": "Regulation headlines promise safety while risks ship faster.",
    "Regulation headlines promise safety while risks ship faster.": "Regulation headlines promise safety while risks ship.",
    "Speed hides design debt until the interest rate arrives in production incidents.": "Speed hides design debt until incidents collect interest.",
    "Founders optimize for headcount optics, then get surprised when burn rate optimizes them.": "Founders chase headcount optics, then burn rate chases them.",
    "Pricing is a positioning choice, not a spreadsheet outcome, which is why it keeps getting delayed.": "Pricing is positioning, not a spreadsheet outcome.",
}

CLOSE_SHORTEN = {
    "The postmortem will say \"process,\" which is how you know nobody fixed it.": "The postmortem will say \"process\" and nothing changes.",
}

FALLBACK_PATTERNS = {
    "contrarian": {
        "pattern_id": "fallback_contrarian_v1",
        "hook_strategy": "contrarian_hook",
        "argument_structure": "claim_with_contrast",
        "closing_style": "cynical_observation",
    },
    "curiosity": {
        "pattern_id": "fallback_curiosity_v1",
        "hook_strategy": "question_hook",
        "argument_structure": "claim_reason_implication",
        "closing_style": "ironic_twist",
    },
    "analytical": {
        "pattern_id": "fallback_analytical_v1",
        "hook_strategy": "observational_hook",
        "argument_structure": "claim_then_reason",
        "closing_style": "plain_close",
    },
}


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def normalize_ascii(text):
    text = text.replace("\u201c", "\"").replace("\u201d", "\"")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u2014", "-")
    text = text.replace("\u00a0", " ")
    return text.encode("ascii", errors="ignore").decode("ascii")


def shorten_line(line):
    line = re.sub(r"\bmost teams\b", "teams", line, flags=re.IGNORECASE)
    line = re.sub(r"\bthe popular take on\b", "", line, flags=re.IGNORECASE).strip()
    line = re.sub(r"\bwhat nobody admits about\b", "few admit about", line, flags=re.IGNORECASE)
    line = re.sub(r"\bthe quiet part about\b", "the quiet part of", line, flags=re.IGNORECASE)
    line = re.sub(r"\bthe real problem in\b", "the problem in", line, flags=re.IGNORECASE)
    line = re.sub(r"\s{2,}", " ", line).strip()
    return line


def enforce_length(text):
    if len(text) > TARGET_MAX:
        lines = text.split("\n")
        if len(lines) >= 2:
            lines[1] = CORE_SHORTEN.get(lines[1], lines[1])
        if len(lines) >= 3:
            lines[2] = CLOSE_SHORTEN.get(lines[2], lines[2])
        lines[0] = shorten_line(lines[0])
        text = "\n".join(lines)

    if len(text) > TARGET_MAX:
        lines = text.split("\n")
        if len(lines) >= 2:
            lines[1] = lines[1].replace(" keeps ", " ").replace(" refusing ", " ").strip()
        text = "\n".join(lines)

    if len(text) > TARGET_MAX:
        text = text[: TARGET_MAX - 1].rstrip() + "."

    if len(text) < TARGET_MIN:
        lines = text.split("\n")
        if len(lines) >= 2:
            addon = " That is where delivery slows."
            if len(text) + len(addon) <= MAX_LEN:
                lines[1] = lines[1].rstrip(".") + addon
                text = "\n".join(lines)
    return text


def validate(text):
    if not (TARGET_MIN <= len(text) <= TARGET_MAX):
        return False
    if "#" in text:
        return False
    if "!!" in text or "??" in text:
        return False
    if any(ord(ch) > 127 for ch in text):
        return False
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) < 3:
        return False
    return True


def engagement_score(text, hook_type, product_mention):
    score = 50.0
    length = len(text)
    if TARGET_MIN <= length <= TARGET_MAX:
        score += 12
    else:
        score -= 10
    if hook_type == "contrarian":
        score += 8
    if hook_type == "curiosity" and "?" in text.split("\n")[0]:
        score += 6
    if "but" in text.lower() or "instead" in text.lower():
        score += 4
    if text.count("\n") >= 2:
        score += 4
    if any(term in text.lower() for term in ["postmortem", "burn", "layoff", "debt", "incident", "good luck"]):
        score += 6
    if product_mention:
        score += 4
    return max(0.0, min(100.0, round(score, 2)))


def build_variants(concept, topic_desc, include_product):
    hook_type = concept["hook_type"]
    core = CORE_SHORTEN.get(concept["core_insight"], concept["core_insight"])
    closing = CLOSE_SHORTEN.get(concept["closing_twist"], concept["closing_twist"])

    hooks = HOOK_VARIANTS.get(hook_type, [concept["hook_statement"]])
    hooks = [h.format(subject=topic_desc) for h in hooks]

    closes = [closing] + DARK_CLOSES
    if include_product:
        closes = PRODUCT_CLOSES + closes

    variants = []
    for hook in hooks:
        for close in closes[:2]:
            lines = [hook, core, close]
            text = "\n".join(lines)
            text = normalize_ascii(text)
            text = enforce_length(text)
            if validate(text):
                variants.append(text)
        if len(variants) >= 5:
            break

    if len(variants) < 3:
        extra_close = DARK_CLOSES[-1]
        lines = [hooks[0], core, extra_close]
        text = enforce_length(normalize_ascii("\n".join(lines)))
        if validate(text):
            variants.append(text)
    return variants[:5]


def main():
    concepts_data = load_json("data/tweet_concepts.json")
    topics_data = load_json("data/approved_topics.json")
    patterns_data = load_json("data/tweet_patterns.json")

    topic_lookup = {t["topic_id"]: t for t in topics_data.get("topics", [])}
    concepts = concepts_data.get("concepts", [])
    patterns = patterns_data.get("patterns", [])

    generated = []
    concept_id = 0
    tweet_id = 0

    for concept in concepts:
        concept_id += 1
        topic_id = concept["topic_id"]
        topic_desc = topic_lookup.get(topic_id, {}).get("topic_description", "the topic")
        hook_type = concept["hook_type"]
        product_relevance = concept.get("product_relevance", False)

        variants = build_variants(concept, topic_desc, product_relevance)
        fallback_pattern = FALLBACK_PATTERNS.get(hook_type, FALLBACK_PATTERNS["contrarian"])
        pattern_id = fallback_pattern["pattern_id"]

        for text in variants:
            tweet_id += 1
            product_mention = "Engram" in text
            score = engagement_score(text, hook_type, product_mention)
            generated.append(
                {
                    "tweet_id": f"g-{tweet_id:04d}",
                    "concept_id": f"c-{concept_id:03d}",
                    "topic_id": topic_id,
                    "hook_type": hook_type,
                    "tone_flags": concept.get("tone_flags", []),
                    "product_mention": product_mention,
                    "predicted_engagement_score": score,
                    "structural_template": pattern_id,
                    "text": text,
                    "char_count": len(text),
                }
            )

    payload = {
        "dataset": "generated_tweets",
        "generated_at": utc_now_iso(),
        "source_dataset": {
            "path": "data/tweet_concepts.json",
            "concept_count": len(concepts),
        },
        "config_snapshot": {
            "target_char_range": [TARGET_MIN, TARGET_MAX],
            "max_characters": MAX_LEN,
            "pattern_source": "tweet_patterns.json" if patterns else "fallback",
        },
        "tweet_count": len(generated),
        "generated_tweets": generated,
    }

    write_json("data/generated_tweets.json", payload)
    print(f"Wrote {len(generated)} tweets to data/generated_tweets.json")


if __name__ == "__main__":
    main()
