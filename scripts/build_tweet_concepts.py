import json
from datetime import datetime, timezone


FALLBACK_PATTERNS = {
    "contrarian": [
        "People blame tools for {subject}, but {counter}.",
        "The popular take on {subject} is wrong. {counter}.",
        "{subject} isn’t broken. The incentives are.",
    ],
    "curiosity": [
        "What nobody says about {subject}: {counter}.",
        "Most people miss this about {subject}: {counter}.",
        "If {subject} feels hard, it’s because {counter}.",
    ],
    "analytical": [
        "The bottleneck in {subject} is {counter}.",
        "{subject} scales only after {counter}.",
        "{subject} fails when {counter}.",
    ],
}

TONE_FLAGS = ["professional", "opinionated", "controversial", "dark_humor"]


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def length_ok(text, minimum=180, maximum=280):
    return minimum <= len(text) <= maximum


def trim_to_limit(text, limit=280):
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "."


def pick_reference_inspiration(accounts):
    ordered = sorted(accounts, key=lambda a: a.get("weight", 0), reverse=True)
    return [acct.get("username") for acct in ordered[:3] if acct.get("username")]


def build_concepts_for_topic(topic, reference_inspiration, product_budget):
    subject = topic["topic_description"]
    domain = topic["domain"]
    keywords = topic.get("keywords", [])
    product_relevant = topic.get("product_relevant", False)

    hooks = [
        ("contrarian", FALLBACK_PATTERNS["contrarian"][0].format(
            subject=subject,
            counter="the friction is coordination, not capability"
        )),
        ("curiosity", FALLBACK_PATTERNS["curiosity"][0].format(
            subject=subject,
            counter="the hard part is rarely technical"
        )),
        ("analytical", FALLBACK_PATTERNS["analytical"][0].format(
            subject=subject,
            counter="the incentive structure, not the algorithm"
        )),
    ]

    concepts = []
    for idx, (hook_type, hook) in enumerate(hooks, start=1):
        core = ""
        close = ""

        if domain in ("AI agents", "autonomous systems"):
            core = "Teams ship clever agents, then wonder why they behave like strangers in a crowded room."
            short_core = "Teams ship clever agents, then wonder why they drift apart."
        elif domain == "startups":
            core = "Founders optimize for headcount optics, then get surprised when burn rate optimizes them."
            short_core = "Founders chase headcount optics, then burn rate chases them."
        elif domain == "programming and software engineering":
            core = "Speed hides design debt until the interest rate arrives in production incidents."
            short_core = "Speed hides design debt until incidents collect interest."
        elif domain == "technology news":
            core = "Regulation headlines promise safety while product teams keep shipping the same risks faster."
            short_core = "Regulation headlines promise safety while risks ship faster."
        elif domain == "business strategy":
            core = "Pricing is a positioning choice, not a spreadsheet outcome, which is why it keeps getting delayed."
            short_core = "Pricing is positioning, not spreadsheet output."
        else:
            core = "Infrastructure reality keeps refusing to match the slide deck."
            short_core = "Infrastructure refuses to match the slide deck."

        close_candidates = [
            "The postmortem will say “process,” which is how you know nobody fixed it.",
            "Everyone will agree on the root cause, right before ignoring it again.",
        ]

        if product_relevant and product_budget["remaining"] > 0 and idx == 2:
            close_candidates.insert(
                0,
                "Engram exists because agent coordination is engineering, not vibes. Meetings still happen.",
            )

        concept_text = None
        chosen_close = None
        for candidate_close in close_candidates:
            candidate = " ".join([hook, core, candidate_close])
            if len(candidate) <= 280:
                concept_text = candidate
                chosen_close = candidate_close
                break
            candidate = " ".join([hook, short_core, candidate_close])
            if len(candidate) <= 280:
                concept_text = candidate
                chosen_close = candidate_close
                core = short_core
                break

        if concept_text is None:
            concept_text = trim_to_limit(" ".join([hook, core, close_candidates[-1]]), 280)
            chosen_close = close_candidates[-1]

        if product_relevant and "Engram" in chosen_close and product_budget["remaining"] > 0:
            product_budget["remaining"] -= 1

        concepts.append(
            {
                "topic_id": topic["topic_id"],
                "hook_type": hook_type,
                "tone_flags": TONE_FLAGS,
                "product_relevance": bool(product_relevant and "Engram" in concept_text),
                "hook_statement": hook,
                "core_insight": core,
                "closing_twist": chosen_close,
                "concept_text": concept_text,
                "estimated_engagement_score": None,
                "reference_inspiration": reference_inspiration,
                "keywords": keywords,
            }
        )

    return concepts


def main():
    approved_topics = load_json("data/approved_topics.json")
    accounts = load_json("data/reference_accounts.json").get("accounts", [])
    reference_inspiration = pick_reference_inspiration(accounts)

    topics = approved_topics.get("topics", [])
    total_concepts = len(topics) * 3
    product_budget = {"remaining": max(1, int(total_concepts * 0.12))}

    concepts = []
    for topic in topics:
        concepts.extend(build_concepts_for_topic(topic, reference_inspiration, product_budget))

    payload = {
        "dataset": "tweet_concepts",
        "generated_at": utc_now_iso(),
        "concept_count": len(concepts),
        "source_dataset": {
            "path": "data/approved_topics.json",
            "topic_count": len(topics),
        },
        "concepts": concepts,
    }
    write_json("data/tweet_concepts.json", payload)


if __name__ == "__main__":
    main()
