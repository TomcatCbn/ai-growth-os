# ADR-019: Growth Decision Engine — Rules + LLM, Never Free-Form LLM

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-005 (renumbered)

## Context

"LLM 负责创造，Growth Engine 负责方向。" Pure-LLM decisions are unstable
and unexplainable to parents; pure-rule systems can't personalize.

## Decision

The decision chain is: code constraints → LLM judgment within them →
code validation. Concretely in this repo:

- **Frontier** computed in code (ADR-003); the Planner may only rank inside it.
- **Rule guardrails** (blueprint Q43): age fit (frontier), capability-priority
  weighting (mission score 40/30/20/10), pattern selection rules,
  pace rules (consecutive refuted → ease, consecutive confirmed → push),
  safety rules (Output Guard on everything human-facing).
- **Growth memory** penalizes failed topics; family goals enter only via
  the interest bridge.
- Every plan validates against the growth-plan contract and carries a
  decision trace for the "为什么" explanation.

## Consequences

- A plan outside the frontier is a hard failure, never a warning.
- Rule changes are data/code changes with tests, not prompt edits.
