import argparse
import json
import math
import os
import re
from datetime import datetime, timezone


TARGET_MIN = 180
TARGET_MAX = 260
MAX_LEN = 280
DEFAULT_VARIANTS = 5
DEFAULT_TOP_PER_CONCEPT = 2
DEFAULT_PRODUCT_RATIO = 0.15

DARK_CLOSES = [
    "The postmortem will blame process, and nothing will change.",
    "Everyone will agree on the root cause, then ignore it again.",
    "The dashboard will call it progress, right before the next incident.",
    "The roadmap will promise fixes, and the calendar will disagree.",
    "The retrofit will arrive right after the damage report.",
]

PRODUCT_CLOSES = [
    "Engram exists because coordination is engineering, not vibes. Meetings still happen.",
    "Engram proves agent coordination is infrastructure, not a culture deck. The meetings remain.",
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

CORE_ALTERNATES = {
    "Infrastructure refuses to match the slide deck.": [
        "Infrastructure keeps refusing to match the slide deck.",
        "Infrastructure reality keeps rejecting the slide deck.",
    ],
    "Infrastructure reality keeps refusing to match the slide deck.": [
        "Infrastructure refuses to match the slide deck.",
        "Infrastructure reality keeps rejecting the slide deck.",
    ],
    "Teams ship clever agents, then wonder why they drift apart.": [
        "Teams ship clever agents, then wonder why they drift.",
        "Teams ship clever agents, then act surprised when they drift.",
    ],
    "Teams ship clever agents, then wonder why they drift.": [
        "Teams ship clever agents, then wonder why they drift apart.",
        "Teams ship clever agents, then act surprised when they drift.",
    ],
    "Regulation headlines promise safety while risks ship faster.": [
        "Regulation headlines promise safety while risks ship even faster.",
        "Regulation headlines promise safety while risks keep shipping.",
    ],
    "Speed hides design debt until incidents collect interest.": [
        "Speed hides design debt until incidents demand interest.",
        "Speed hides design debt until production charges interest.",
    ],
    "Founders chase headcount optics, then burn rate chases them.": [
        "Founders chase headcount optics, then burn rate does the chasing.",
        "Founders chase headcount optics, then the burn rate catches them.",
    ],
}

HOOK_SHORTEN = [
    (r"\bthe popular take on\b", ""),
    (r"\bmost teams\b", "teams"),
    (r"\bwhat nobody admits about\b", "few admit about"),
    (r"\bthe quiet part about\b", "the quiet part of"),
    (r"\bthe real problem in\b", "the problem in"),
]


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


def compute_model_score(text, hook_type, topic, config, viral_index):
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


def shorten_hook(line):
    output = line
    for pattern, repl in HOOK_SHORTEN:
        output = re.sub(pattern, repl, output, flags=re.IGNORECASE).strip()
    output = re.sub(r"\s{2,}", " ", output).strip()
    return output


def enforce_length(text):
    if len(text) <= TARGET_MAX:
        return text
    lines = text.split("\n")
    if lines:
        lines[0] = shorten_hook(lines[0])
    text = "\n".join(lines).strip()
    if len(text) > TARGET_MAX:
        text = text[: TARGET_MAX - 1].rstrip() + "."
    return text


def build_core_variants(core):
    variants = [core]
    for alt in CORE_ALTERNATES.get(core, []):
        if alt not in variants:
            variants.append(alt)
    for suffix in ["That is where delivery slows.", "That is why execution stalls."]:
        if len(core) + 1 + len(suffix) <= MAX_LEN and suffix not in core:
            variants.append(f"{core.rstrip('.')} {suffix}")
    return variants[:3]


def build_variants(base_text, topic_desc, hook_type, product_relevance):
    lines = [line.strip() for line in base_text.split("\n") if line.strip()]
    hook_line = lines[0] if lines else base_text
    core_line = lines[1] if len(lines) > 1 else base_text
    close_line = lines[2] if len(lines) > 2 else ""

    hooks = HOOK_VARIANTS.get(hook_type, [hook_line])
    hooks = [h.format(subject=topic_desc) for h in hooks]

    cores = build_core_variants(core_line)
    closes = [close_line] + DARK_CLOSES
    if product_relevance:
        closes = PRODUCT_CLOSES + closes

    variants = []
    seen = set()
    for hook in hooks:
        for core in cores:
            for close in closes:
                lines_out = [hook, core, close]
                text = normalize_ascii("\n".join(lines_out))
                text = enforce_length(text)
                if text in seen:
                    continue
                if not validate_style(text, ["professional", "opinionated", "controversial"], []):
                    continue
                seen.add(text)
                variants.append(text)
                if len(variants) >= DEFAULT_VARIANTS:
                    return variants
    if len(variants) < 3 and hook_line and core_line and close_line:
        text = normalize_ascii("\n".join([hook_line, core_line, close_line]))
        text = enforce_length(text)
        if text not in seen:
            variants.append(text)
    return variants[:DEFAULT_VARIANTS]


def parse_concept_id(concept_id):
    match = re.match(r"c-(\d+)", concept_id or "")
    if not match:
        return None
    return int(match.group(1))


def main():
    parser = argparse.ArgumentParser(description="Optimize ranked tweets with refined variants.")
    parser.add_argument("--ranked", default="data/ranked_tweets.json")
    parser.add_argument("--approved-topics", default="data/approved_topics.json")
    parser.add_argument("--concepts", default="data/tweet_concepts.json")
    parser.add_argument("--viral", default="data/viral_tweet_dataset.json")
    parser.add_argument("--patterns", default="data/tweet_patterns.json")
    parser.add_argument("--config", default="data/topic_discovery_config.json")
    parser.add_argument("--recent", default="data/recent_tweets.json")
    parser.add_argument("--out", default="data/optimized_tweets.json")
    parser.add_argument("--variants", type=int, default=DEFAULT_VARIANTS)
    parser.add_argument("--top-per-concept", type=int, default=DEFAULT_TOP_PER_CONCEPT)
    parser.add_argument("--product-ratio", type=float, default=DEFAULT_PRODUCT_RATIO)
    args = parser.parse_args()

    ranked = load_json(args.ranked)
    topics = load_json(args.approved_topics)
    concepts_data = load_json(args.concepts)
    config = load_json(args.config)
    viral = load_json(args.viral)

    patterns = []
    if os.path.exists(args.patterns):
        patterns = load_json(args.patterns).get("patterns", [])
    pattern_ids = {row.get("pattern_id") for row in patterns if row.get("pattern_id")}

    recent_texts = []
    recent_meta = {"path": args.recent, "count": 0, "loaded": False}
    if os.path.exists(args.recent):
        recent_data = load_json(args.recent)
        recent_texts = [row.get("text", "") for row in recent_data.get("tweets", []) if row.get("text")]
        recent_meta["count"] = len(recent_texts)
        recent_meta["loaded"] = True

    topic_lookup = {topic["topic_id"]: topic for topic in topics.get("topics", [])}
    topic_scope = config.get("topic_scope", [])

    concept_lookup = {}
    for idx, concept in enumerate(concepts_data.get("concepts", []), start=1):
        concept_lookup[f"c-{idx:03d}"] = concept

    viral_index = build_viral_index(viral.get("tweets", []))
    contrarian_markers = config.get("signals", {}).get("contrarian_markers", [])
    max_similarity_penalty = config.get("scoring", {}).get("max_similarity_penalty", 15)
    product_boost = config.get("scoring", {}).get("product_boost", 5)

    variants = []
    rejected = []
    variant_id = 0

    for row in ranked.get("ranked_tweets", []):
        topic_id = row.get("topic_id")
        topic = topic_lookup.get(topic_id)
        if not topic:
            rejected.append({"tweet_id": row.get("tweet_id"), "reason": "unknown_topic"})
            continue
        if topic.get("domain") not in topic_scope:
            rejected.append({"tweet_id": row.get("tweet_id"), "reason": "out_of_scope"})
            continue

        concept = concept_lookup.get(row.get("concept_id"))
        product_relevance = False
        if concept:
            product_relevance = bool(concept.get("product_relevance"))

        topic_desc = topic.get("topic_description", "the topic")
        hook_type = row.get("hook_type") or "contrarian"
        base_text = row.get("text", "")
        variant_texts = build_variants(base_text, topic_desc, hook_type, product_relevance)

        for text in variant_texts[: args.variants]:
            ok, reason = validate_style(text, row.get("tone_flags", []), contrarian_markers)
            if not ok:
                rejected.append({"tweet_id": row.get("tweet_id"), "reason": reason})
                continue

            base_score, viral_similarity = compute_model_score(text, hook_type, topic, config, viral_index)
            penalty, recent_similarity = similarity_penalty(text, recent_texts, max_similarity_penalty)
            product_mention = "Engram" in text
            product_ok = product_mention and product_integration_ok(text)
            final_score = base_score - penalty
            product_applied = False
            if product_ok:
                final_score += product_boost
                product_applied = True
            final_score = max(0.0, min(100.0, round(final_score, 2)))

            structural_template = row.get("structural_template")
            if structural_template not in pattern_ids:
                structural_template = row.get("structural_template") or "fallback_contrarian_v1"

            tone_flags = list(row.get("tone_flags", []))
            if detect_dark_humor(text, config.get("scoring", {}).get("dark_humor_keywords", [])):
                if "dark_humor" not in tone_flags:
                    tone_flags.append("dark_humor")

            variant_id += 1
            variants.append(
                {
                    "tweet_id": f"o-{variant_id:04d}",
                    "source_tweet_id": row.get("tweet_id"),
                    "concept_id": row.get("concept_id"),
                    "topic_id": topic_id,
                    "hook_type": hook_type,
                    "tone_flags": tone_flags,
                    "product_mention": product_mention,
                    "product_boost_applied": product_applied,
                    "structural_template": structural_template,
                    "predicted_engagement_score": final_score,
                    "score_breakdown": {
                        "model_score": base_score,
                        "product_boost": product_boost if product_applied else 0.0,
                        "diversity_penalty": round(penalty, 2),
                        "max_recent_similarity": round(recent_similarity, 3),
                        "max_viral_similarity": round(viral_similarity, 3),
                    },
                    "text": text,
                    "char_count": len(text),
                }
            )

    variants.sort(key=lambda row: row["predicted_engagement_score"], reverse=True)

    variants_by_concept = {}
    for row in variants:
        variants_by_concept.setdefault(row["concept_id"], []).append(row)

    selected = []
    for concept_id, rows in variants_by_concept.items():
        rows_sorted = sorted(rows, key=lambda item: item["predicted_engagement_score"], reverse=True)
        if not rows_sorted:
            continue
        selected.append(rows_sorted[0])
        if args.top_per_concept > 1:
            for candidate in rows_sorted[1:]:
                if candidate["text"].split("\n")[0] != rows_sorted[0]["text"].split("\n")[0]:
                    selected.append(candidate)
                    break

    selected.sort(key=lambda row: row["predicted_engagement_score"], reverse=True)

    product_cap = max(1, int(math.floor(len(selected) * args.product_ratio))) if selected else 0
    if product_cap:
        product_selected = [row for row in selected if row["product_mention"]]
        if len(product_selected) > product_cap:
            keep = []
            product_count = 0
            for row in selected:
                if row["product_mention"]:
                    if product_count >= product_cap:
                        continue
                    product_count += 1
                keep.append(row)
            selected = keep

    payload = {
        "dataset": "optimized_tweets",
        "generated_at": utc_now_iso(),
        "source_dataset": {
            "path": args.ranked,
            "ranked_count": len(ranked.get("ranked_tweets", [])),
        },
        "optimization_config": {
            "target_char_range": [TARGET_MIN, TARGET_MAX],
            "max_characters": MAX_LEN,
            "variants_per_tweet": args.variants,
            "top_per_concept": args.top_per_concept,
            "product_ratio_cap": args.product_ratio,
            "product_cap": product_cap,
            "recent_tweets": recent_meta,
        },
        "rejected_count": len(rejected),
        "rejections": rejected[:100],
        "variant_count": len(variants),
        "optimized_count": len(selected),
        "optimized_tweets": selected,
    }

    write_json(args.out, payload)
    print(f"Wrote {len(selected)} optimized tweets to {args.out}")


if __name__ == "__main__":
    main()
