# ADR-003: Graph-Constrained Planner

- Status: Accepted
- Date: 2026-07-24

## Context

The Growth Planner selects the next growth opportunity from Child State +
Learning Ontology + recent evidence. Pure-LLM selection hallucinates invalid
prerequisite sequences; pure-rule selection ignores personalization signals
(interests, capability priorities).

## Decision

**Code computes constraints, LLM makes judgment.**

1. Deterministic graph traversal computes the **frontier**: topics whose
   prerequisites are mastered (per the dependency DAG, hard edges required,
   soft edges advisory) and which are not yet mastered.
2. The LLM chooses and ranks *within the frontier only*, given interests,
   capability priorities (development_priority), and recent evidence.
3. The LLM must output a **selection rationale** — consumed directly by the
   Parent Agent's weekly report.
4. Frontier legality is code-verified after LLM output; selecting a
   non-frontier topic is a hard failure (must be 0% in acceptance testing).
5. A pure-rule baseline ranking is one config flag away, enabling A/B
   measurement of the LLM's added value.

## Consequences

- The LLM can never prescribe a developmentally-impossible sequence.
- "What the LLM picks vs. what rules would pick" is a built-in evaluation
  metric for the demo.
