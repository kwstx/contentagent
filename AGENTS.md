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
