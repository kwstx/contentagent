# Tweet Style Rules

The system must enforce a strict set of predefined style constraints that govern how every tweet is written. These constraints are implemented as a configuration object called `style_rules`, which is applied during the tweet generation stage and validated before a tweet is approved for publication.

The purpose of these rules is to ensure that all generated tweets maintain a consistent voice, tone, and structural identity, preventing the system from producing generic or inconsistent content. The tweet generator must treat these rules as hard constraints, meaning any tweet that violates them must be rejected or automatically rewritten.

## Character Length Constraint

All generated tweets must remain within the native platform limit of 280 characters. The system should enforce a stricter internal constraint by targeting tweets between 180 and 260 characters, which typically provides enough space to deliver a clear insight while maintaining strong readability.

Before a tweet is approved, a validation function must calculate the total character count and reject any output that exceeds the 280-character limit.

## Tone Constraint

The tone of every tweet must be professional but opinionated. The writing style should reflect the voice of a knowledgeable operator or industry insider rather than a casual commentator. Statements should be delivered with confidence and clarity.

Tweets should contain clear viewpoints rather than neutral observations. The system should favor statements that challenge common beliefs, critique popular narratives, or present unconventional insights. This creates intellectual tension that encourages discussion and engagement.

## Controversy Constraint

The system should intentionally incorporate a moderate level of controversy in tweet construction. Controversy should come from challenging mainstream assumptions or highlighting uncomfortable truths, rather than from offensive language or direct personal attacks.

Tweets should aim to trigger curiosity and disagreement while remaining intellectually grounded. For example, tweets may question widely accepted industry practices or expose inefficiencies that most people avoid discussing.

This constraint increases the probability of engagement by creating content that invites reactions and debate.

## Dark Humor Constraint

Each tweet should include a subtle layer of dark humor embedded within the statement. This humor must remain understated and dry rather than exaggerated. The purpose is to introduce a slight twist that makes the content memorable while preserving the professional tone.

Dark humor should appear as an ironic observation, cynical remark, or quiet commentary on an uncomfortable reality. It should not dominate the message but instead act as a final line or subtle implication that adds personality to the tweet.

## Formatting Constraints

The formatting rules should maintain a clean, minimal structure. Tweets must avoid decorative elements or visual noise. The system should enforce the following formatting restrictions:

- No emojis are allowed under any circumstances.
- No hashtags should appear in the tweet.
- Excessive punctuation such as multiple exclamation points must be avoided.
- Tweets should prioritize short sentences and natural line breaks to maintain readability.

These restrictions maintain a minimalist and serious tone, which aligns with the professional and opinionated style defined earlier.

## Structural Composition Rules

Every tweet should follow a simple rhetorical structure consisting of three logical components:

- Hook Statement
The opening sentence must capture attention by presenting a surprising claim, contrarian idea, or uncomfortable truth.
- Insight or Argument
The middle portion should briefly explain the reasoning or implication behind the hook.
- Dark Twist or Closing Line
The final sentence should introduce a subtle dark humor remark or cynical observation that reinforces the message.

This structure ensures that tweets are concise while still delivering a complete thought.

## Validation and Enforcement

Before any tweet is published, the system must run a validation step that verifies compliance with all style rules. The validator should check character length, formatting restrictions, tone alignment, and structural integrity. If a tweet fails any rule, it should either be automatically rewritten or rejected.

This validation layer ensures that the content agent consistently produces tweets that align with the defined identity and stylistic direction.

# Topic Scope Rules

The system must operate within a strictly defined content domain to ensure topical consistency and audience clarity. This domain should be implemented as a configuration object called `topic_scope`. The agent must only generate tweets about topics that fall within this predefined set of categories. Any topic discovered outside the defined scope must be discarded during the topic discovery stage.

The purpose of this constraint is to maintain a focused identity and ensure that the account consistently attracts an audience interested in a specific cluster of technological and entrepreneurial subjects.

## Topic Domain Categories

The `topic_scope` configuration must include the following approved categories:

- technology
- startups
- artificial intelligence
- AI agents
- autonomous systems
- programming and software engineering
- business strategy
- technology news

When the topic discovery system scans conversations or trending signals, it must classify each candidate topic into one of these categories. If the topic cannot be confidently mapped to at least one category in the scope, it should not be considered for tweet generation.

This filtering process ensures that the account remains tightly aligned with technology-driven innovation and entrepreneurship discussions.

## Topic Relevance Scoring

Each discovered topic must be evaluated for relevance before it enters the content generation stage. The evaluation should consider three primary dimensions:

- Domain relevance: how closely the topic aligns with the defined categories.
- Engagement potential: whether the topic is likely to provoke strong reactions or curiosity.
- Novelty: whether the topic introduces a new perspective or insight rather than repeating common observations.

Topics should be assigned a numeric score between 0 and 100. Only topics exceeding a predefined threshold should move forward to tweet concept generation.

## Product Relevance Detection

The system must include a rule set that determines when it is appropriate to mention your product. This rule set should be implemented as a classifier called `product_relevance_detector`.

The detector should analyze each approved topic and determine whether it intersects with concepts related to:

- AI agent infrastructure
- agent interoperability
- multi-agent systems
- communication between AI systems
- coordination between autonomous agents
- developer tools for building agent ecosystems

If a topic strongly overlaps with these areas, the system may generate a tweet that references your product.

Your product, Engram, is a platform for connecting AI agents and enabling communication between them. When a topic relates to the architecture or coordination of autonomous systems, the agent should treat this as an opportunity to introduce the product as a relevant solution.

## Product Mention Frequency Control

To avoid appearing overly promotional, the system must enforce strict limits on product mentions. A configuration parameter called `product_post_ratio` should define the maximum proportion of tweets that include a product reference.

For example, the system might allow product-related tweets to represent 10-15 percent of total content output. All other tweets should focus purely on insights, commentary, or industry observations.

This ensures that the account primarily delivers value and thought leadership, while product mentions appear naturally within relevant discussions.

## Product Integration Style Rules

When the system generates a tweet that references the product, the mention must appear organically within the argument or insight rather than as an advertisement.

The tweet should frame the product as an example or enabling technology that supports the broader claim being made. Direct promotional language should be avoided. Instead, the system should highlight the conceptual importance of agent communication infrastructure and reference the product as an implementation of that idea.

Example conceptual structure:

- Hook statement presenting a problem or insight about AI agents
- explanation of why the problem exists
- mention of the product as a solution or illustration of the concept

The product URL should only appear when it adds clarity or context to the statement.

Reference link (use only when needed for clarity): `https://www.useengram.com`

## Topic Diversity Enforcement

To maintain variety and prevent repetitive content, the system should track recently used topic categories. A topic category should not dominate the content feed over short periods. The agent must maintain diversity across the approved domain categories so that the content stream covers multiple aspects of technology and entrepreneurship.

This mechanism prevents the system from repeatedly posting about the same concept, which would reduce audience engagement.

## Topic Validation

Before a topic proceeds to the tweet generation stage, the system must run a final validation step to confirm:

- the topic belongs to an approved domain category
- the topic meets the minimum relevance score
- the topic has not been recently used
- product relevance rules have been evaluated

Only topics that pass this validation should enter the tweet concept generation stage.
