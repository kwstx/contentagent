import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def split_sentences(text):
    sentences = re.split(r"[.!?]+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def split_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def contains_non_ascii(text):
    return any(ord(ch) > 127 for ch in text)


def bucket_char_length(char_len):
    if char_len <= 160:
        return "short_<=160"
    if char_len <= 200:
        return "mid_161_200"
    if char_len <= 240:
        return "long_201_240"
    return "near_limit_241_280"


def bucket_sentence_count(count):
    if count <= 1:
        return "single_sentence"
    if count == 2:
        return "two_sentences"
    if count == 3:
        return "three_sentences"
    return "four_plus_sentences"


def bucket_line_breaks(count):
    if count <= 0:
        return "no_breaks"
    if count == 1:
        return "single_break"
    return "multi_breaks"


def detect_hook_strategy(hook, contrarian_markers):
    hook_lower = hook.lower()

    if hook.strip().endswith("?") or hook_lower.startswith(("why ", "how ", "what ", "when ")):
        return "question_hook"

    if re.search(r"\b\d+%?\b", hook):
        return "metric_hook"

    if any(marker in hook_lower for marker in contrarian_markers):
        return "contrarian_hook"

    if hook_lower.startswith(("stop ", "start ", "build ", "ship ", "avoid ", "use ", "learn ")):
        return "imperative_hook"

    if any(term in hook_lower for term in ["turns out", "weird", "strange", "counterintuitive", "surprising"]):
        return "surprising_observation"

    if any(term in hook_lower for term in ["broken", "dead", "scam", "waste", "doesn't work", "fails"]):
        return "blunt_critique"

    if any(term in hook_lower for term in ["will ", "going to", "next ", "future", "is about to"]):
        return "prediction_hook"

    if any(term in hook_lower for term in ["i've", "after ", "years", "we shipped", "i spent"]):
        return "authority_hook"

    return "observational_hook"


def detect_argument_structure(sentences, lines):
    sentence_count = len(sentences)
    if sentence_count <= 1:
        return "single_punch"

    causal_terms = ["because", "so", "therefore", "which", "this means", "that's why", "hence"]
    contrast_terms = ["but", "however", "yet", "though"]
    has_causal = any(term in " ".join(sentences).lower() for term in causal_terms)
    has_contrast = any(term in " ".join(sentences).lower() for term in contrast_terms)

    if len(lines) >= 2 and all(len(line) <= 90 for line in lines):
        return "line_by_line_support"

    if sentence_count == 2 and has_causal:
        return "claim_then_reason"

    if sentence_count >= 3 and has_causal:
        return "claim_reason_implication"

    if has_contrast:
        return "claim_with_contrast"

    return "compact_explanation"


def detect_closing_style(last_sentence, dark_humor_keywords):
    last_lower = last_sentence.lower()

    if any(term in last_lower for term in dark_humor_keywords):
        return "dark_humor_close"

    if any(term in last_lower for term in ["of course", "as usual", "welcome to", "good luck"]):
        return "ironic_twist"

    if any(term in last_lower for term in ["nobody", "no one", "still", "yet", "anyway"]):
        return "cynical_observation"

    if last_lower.startswith(("stop ", "start ", "build ", "ship ", "avoid ")):
        return "call_to_action"

    return "plain_close"


def build_hook_template(strategy):
    templates = {
        "contrarian_hook": "Contrarian hook: '[Common belief] is overrated.'",
        "question_hook": "Question hook: 'Why does [domain] keep [habit]?'",
        "metric_hook": "Metric hook: '[X]% of [group] still [behavior].'",
        "imperative_hook": "Imperative hook: 'Stop [habit]. Start [alternative].'",
        "surprising_observation": "Surprising hook: 'The weird part is [unexpected fact].'",
        "blunt_critique": "Blunt hook: '[Practice] is broken.'",
        "prediction_hook": "Prediction hook: '[Trend] will [outcome] next.'",
        "authority_hook": "Authority hook: 'After [experience], the pattern is clear.'",
        "observational_hook": "Observation hook: '[Reality] keeps repeating.'",
    }
    return templates.get(strategy, "Hook: '[Contrarian or surprising statement].'")


def build_argument_template(structure):
    templates = {
        "single_punch": "Single-sentence punch that compresses claim and reason.",
        "claim_then_reason": "Claim, then one tight reason: 'Because [constraint], [outcome].'",
        "claim_reason_implication": "Claim, reason, implication in 2-3 sentences.",
        "claim_with_contrast": "Claim, then a contrast: 'But [counterpoint].'",
        "line_by_line_support": "2-3 short lines, each a supporting point.",
        "compact_explanation": "Compact explanation using one connector like 'because' or 'so'.",
    }
    return templates.get(structure, "Compact reasoning in 2-3 sentences.")


def build_closing_template(style):
    templates = {
        "dark_humor_close": "Dry twist: 'The spreadsheet will still call it progress.'",
        "ironic_twist": "Ironic close: 'Of course this is called strategy.'",
        "cynical_observation": "Cynical close: 'And nobody will fix it this quarter.'",
        "call_to_action": "Directive close: 'Fix it before it ships.'",
        "plain_close": "Neutral close: 'That is the tradeoff.'",
    }
    return templates.get(style, "Closing line with a subtle twist.")


def compute_weighted_score(rows):
    total_weight = 0.0
    weighted = 0.0
    for row in rows:
        norm = row.get("normalized_engagement") or 0.0
        weight = row.get("recency_weight") or 1.0
        total_weight += weight
        weighted += norm * weight
    if total_weight <= 0:
        return 0.0
    return weighted / total_weight


def main():
    parser = argparse.ArgumentParser(description="Analyze viral tweets into reusable patterns.")
    parser.add_argument(
        "--dataset",
        default=os.path.join("data", "viral_tweet_dataset.json"),
        help="Path to viral_tweet_dataset.json",
    )
    parser.add_argument(
        "--config",
        default=os.path.join("data", "viral_tweet_config.json"),
        help="Path to viral_tweet_config.json",
    )
    parser.add_argument(
        "--patterns-out",
        default=os.path.join("data", "tweet_patterns.json"),
        help="Output path for tweet_patterns.json",
    )
    parser.add_argument("--min-support", type=int, default=3, help="Minimum tweets per pattern")
    parser.add_argument("--top-patterns", type=int, default=30, help="Max patterns to keep")
    args = parser.parse_args()

    dataset = load_json(args.dataset)
    config = load_json(args.config)
    tweets = dataset.get("tweets", [])

    contrarian_markers = config.get("contrarian_markers", [])
    dark_humor_keywords = config.get("dark_humor_keywords", [])

    if not tweets:
        payload = {
            "dataset": "tweet_patterns",
            "generated_at": utc_now_iso(),
            "source_dataset": {"path": args.dataset, "tweet_count": 0},
            "patterns": [],
            "topic_mappings": {},
            "formatting_summary": {},
            "notes": [
                "viral_tweet_dataset is empty. Rebuild dataset before pattern extraction."
            ],
        }
        write_json(args.patterns_out, payload)
        print(f"Wrote empty pattern set to {args.patterns_out}.")
        return

    pattern_rows = defaultdict(list)
    topic_index = defaultdict(list)
    formatting_stats = defaultdict(int)

    for row in tweets:
        text = row.get("text") or ""
        sentences = split_sentences(text)
        lines = split_lines(text)
        hook = sentences[0] if sentences else ""
        last_sentence = sentences[-1] if sentences else ""

        hook_strategy = detect_hook_strategy(hook, contrarian_markers)
        argument_structure = detect_argument_structure(sentences, lines)
        closing_style = detect_closing_style(last_sentence, dark_humor_keywords)

        char_len = len(text)
        sentence_count = len(sentences)
        line_breaks = text.count("\n")

        pattern_key = (
            hook_strategy,
            argument_structure,
            closing_style,
            bucket_line_breaks(line_breaks),
            bucket_sentence_count(sentence_count),
            bucket_char_length(char_len),
        )

        pattern_rows[pattern_key].append(row)
        topic = (row.get("topic") or {}).get("label")
        if topic:
            topic_index[topic].append(pattern_key)

        formatting_stats["total"] += 1
        formatting_stats[f"line_breaks_{bucket_line_breaks(line_breaks)}"] += 1
        formatting_stats[f"sentences_{bucket_sentence_count(sentence_count)}"] += 1
        formatting_stats[f"length_{bucket_char_length(char_len)}"] += 1
        if contains_non_ascii(text):
            formatting_stats["non_ascii"] += 1

    patterns = []
    for idx, (key, rows) in enumerate(pattern_rows.items(), start=1):
        if len(rows) < args.min_support:
            continue

        hook_strategy, argument_structure, closing_style, line_bucket, sentence_bucket, length_bucket = key
        normalized_values = [row.get("normalized_engagement") or 0.0 for row in rows]
        avg_norm = sum(normalized_values) / float(len(normalized_values))
        weighted_score = compute_weighted_score(rows)
        topics = defaultdict(int)
        for row in rows:
            topic_label = (row.get("topic") or {}).get("label")
            if topic_label:
                topics[topic_label] += 1

        sorted_topics = sorted(topics.items(), key=lambda item: item[1], reverse=True)
        topic_labels = [label for label, _ in sorted_topics[:5]]

        patterns.append(
            {
                "pattern_id": f"pattern_{idx:03d}",
                "support": len(rows),
                "hook": {
                    "strategy": hook_strategy,
                    "template": build_hook_template(hook_strategy),
                },
                "argument": {
                    "structure": argument_structure,
                    "template": build_argument_template(argument_structure),
                },
                "closing": {
                    "style": closing_style,
                    "template": build_closing_template(closing_style),
                    "dark_humor_compatible": closing_style == "dark_humor_close",
                },
                "formatting": {
                    "line_breaks": line_bucket,
                    "sentence_count": sentence_bucket,
                    "char_length": length_bucket,
                },
                "topics": topic_labels,
                "performance": {
                    "avg_normalized_engagement": round(avg_norm, 6),
                    "weighted_score": round(weighted_score, 6),
                },
                "evidence": {
                    "sample_tweet_ids": [
                        row.get("tweet_id") for row in rows[:3] if row.get("tweet_id")
                    ]
                },
            }
        )

    patterns.sort(key=lambda item: item["performance"]["weighted_score"], reverse=True)
    patterns = patterns[: args.top_patterns]

    topic_mappings = {}
    for topic, keys in topic_index.items():
        scored = []
        for key in keys:
            for pattern in patterns:
                if (
                    pattern["hook"]["strategy"],
                    pattern["argument"]["structure"],
                    pattern["closing"]["style"],
                    pattern["formatting"]["line_breaks"],
                    pattern["formatting"]["sentence_count"],
                    pattern["formatting"]["char_length"],
                ) == key:
                    scored.append(
                        (pattern["pattern_id"], pattern["performance"]["weighted_score"])
                    )
        if scored:
            scored_sorted = sorted(scored, key=lambda item: item[1], reverse=True)
            topic_mappings[topic] = [pattern_id for pattern_id, _ in scored_sorted[:5]]

    formatting_summary = {
        "total": formatting_stats.get("total", 0),
        "line_breaks": {
            "no_breaks": formatting_stats.get("line_breaks_no_breaks", 0),
            "single_break": formatting_stats.get("line_breaks_single_break", 0),
            "multi_breaks": formatting_stats.get("line_breaks_multi_breaks", 0),
        },
        "sentence_counts": {
            "single_sentence": formatting_stats.get("sentences_single_sentence", 0),
            "two_sentences": formatting_stats.get("sentences_two_sentences", 0),
            "three_sentences": formatting_stats.get("sentences_three_sentences", 0),
            "four_plus_sentences": formatting_stats.get("sentences_four_plus_sentences", 0),
        },
        "length_buckets": {
            "short_<=160": formatting_stats.get("length_short_<=160", 0),
            "mid_161_200": formatting_stats.get("length_mid_161_200", 0),
            "long_201_240": formatting_stats.get("length_long_201_240", 0),
            "near_limit_241_280": formatting_stats.get("length_near_limit_241_280", 0),
        },
        "non_ascii_ratio": round(
            formatting_stats.get("non_ascii", 0) / float(max(1, formatting_stats.get("total", 1))), 4
        ),
    }

    payload = {
        "dataset": "tweet_patterns",
        "generated_at": utc_now_iso(),
        "source_dataset": {
            "path": args.dataset,
            "tweet_count": len(tweets),
            "generated_at": dataset.get("generated_at"),
        },
        "config_snapshot": {
            "topic_scope": config.get("topic_scope", []),
            "min_support": args.min_support,
            "top_patterns": args.top_patterns,
        },
        "patterns": patterns,
        "topic_mappings": topic_mappings,
        "formatting_summary": formatting_summary,
    }

    write_json(args.patterns_out, payload)
    print(f"Wrote {len(patterns)} patterns to {args.patterns_out}.")


if __name__ == "__main__":
    main()
