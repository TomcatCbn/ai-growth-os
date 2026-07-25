# ADR-009: Parent Agent as Family Growth Coach

- Status: Accepted
- Date: 2026-07-25

## Context

Vision positions the product as "a growth advisor for parents" under the
principle "growth over scores". The commercial-risk question: if the Parent
Agent is merely a weekly-report generator, the feature is impressive once
and thin thereafter. Long-term value requires a relationship, not a
deliverable.

## Decision

### 1. Parent Agent = Family Growth Coach (家庭成长协作者)

The weekly report is one communication form of the Coach, not its job.
The Coach's continuous responsibilities:

- **Weekly growth narrative** (three-part: growth moments with verbatim
  evidence quotes → capability trends with expandable evidence chains →
  one low-cost actionable home suggestion)
- **On-demand consultation**: parents ask questions in context
  ("他最近不爱说话怎么办") — the Coach answers grounded in THIS child's
  state, evidence history, and development stage, not generic parenting
  content
- **Loop participation**: parents supply life context (starting
  kindergarten, a move, a new sibling) which becomes first-class planning
  signals for the Growth Planner; parents can request mission themes
- **Moment preparation**: proactively equips parents for upcoming
  transitions visible in the development model

### 2. Communication rules (iron rules)

- **Never compare**: no cross-child benchmarking, no "ahead/behind" framing.
  Only "vs. his own last week". Parent-side anxiety-driven retention is a
  dark pattern (same philosophy as ADR-008 Layer 3).
- **Data always carries its evidence chain**: every trend arrow expands to
  the raw observations behind it. Derived views are transparency tools,
  never judgments.
- **Suggestions must be low-cost and executable** ("at dinner, have him sort
  the chopsticks by color") — capability language translated back into
  daily family life.

### 3. Boundary

The Coach advises; it never diagnoses. Medical/psychological territory is
Layer-2-guarded (ADR-008) with referral language, consistent with the
Growth Planner's "must not replace professional assessment" constraint.

## Consequences

- Parent side has an input channel (life context, questions, requests) that
  feeds the Planner — parents are collaborators in the loop, not just
  evidence submitters.
- Parent Agent needs conversational memory (separate from child narrative
  memory): past consultations, parent concerns, coaching history.
- Demo scope unchanged: weekly narrative only; consultation is post-MVP.
