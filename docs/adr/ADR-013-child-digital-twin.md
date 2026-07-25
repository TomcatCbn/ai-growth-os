# ADR-013: Child Digital Twin — Structured Projection Layer

- Status: Accepted
- Date: 2026-07-26

## Context

The personality-exploration blueprint (v2.1) upgrades "性格探索" into a Child
Digital Twin: the system's cumulative understanding of the child — interests,
capabilities, motivation, learning patterns, partner relationship — always
evidence-backed, never a label ("性格不是测出来的，是陪伴过程中发现的";
observation first, interpretation second).

Three tensions with existing ADRs were settled before design:

- **T1 (vs. blueprint Q13/Q21 hybrid structured+vector):** structured Twin
  only; vector store deferred per ADR-012. Conservative, reversible.
- **T2 (vs. ADR-004 two raw pockets):** the Twin is a *projection* over the
  event log, NOT a third raw pocket. Numeric state (mastery, capability
  levels) still comes ONLY from the Reducer. The Twin references those
  numbers; it never stores its own copy as truth.
- **T3 (tendencies):** tendencies are Insight-layer interpretations of
  existing evidence, not a new Reducer signal channel. They carry confidence
  and provenance, decay without reinforcement, and never override Event
  History (ADR-012 Growth Memory discipline, generalized).

## Decision

### 1. Twin = projection, with two kinds of content

- **Raw views** — references to Reducer output (topic_mastery, derived
  capability scores). Read-through, never duplicated as truth.
- **Insight entries** — LLM/rules-derived interpretations. Every entry carries
  `confidence`, `supporting_event_ids`, `last_reinforced_at`, and a `stale`
  flag. When Event History disagrees, history wins; the entry is marked stale.

### 2. Twin schema sections

`identity / interests / capabilities / motivation / learning_pattern /
relationship / family_goals / growth_priorities / constraints`
(schemas/child-twin.schema.json). Companion documents: tendency,
growth-pattern, partner-state, family-model schemas.

### 3. Update timing (blueprint Q20: B+C)

Session-end projection (deterministic code) + periodic trend analysis
(post-MVP Reflection job). LLM may propose insight entries; only code writes
them, with provenance.

### 4. Companion initiation (blueprint Q24: C)

The partner may proactively invite AND the child may summon it at any time.
Recorded here as product behavior for the future Experience Orchestrator;
no runtime change in this ADR.

### 5. Agent boundaries stay modular for now

Blueprint MVP agents (Partner / Adventure Generator / Memory) are module
interfaces in the single-process runtime; splitting into separate agents is
a later packaging decision, not an architecture change.

## Consequences

- Five new contracts under schemas/; all Twin writes validate via
  runtime/contracts.py.
- Reducer and ADR-004 unchanged — numeric discipline preserved.
- tendencies never become `signal target_type` in the Reducer.
- Relationship/partner state is a projection too (partner-state.schema.json),
  rebuilt from events like everything else.
