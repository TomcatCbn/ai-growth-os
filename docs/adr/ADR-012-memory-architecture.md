# ADR-012: Memory Architecture — Runtime State vs Growth Memory vs Event History

- Status: Accepted
- Date: 2026-07-25

## Context

"Memory" was a single vague layer in the original architecture. Three
different things were being conflated, with different lifetimes, owners, and
consistency needs.

## Decision: three distinct stores

### 1. Event History (facts, permanent)

The append-only event log (ADR-002). Immutable facts: "on 2026-07-24 the
child completed a puzzle mission; parent observed X". System of record for
everything. Owner: Event Store. Never mutated, never summarized in place.

### 2. Runtime State (present, short-lived, mutable)

Where the loop IS right now: `active_mission`, current chapter, chapter
progress, stall timers, pending evidence. Lives in SQLite rows/snapshots,
derived-or-checkpointed from events. Fully rebuildable from Event History.
Owner: Mission Manager + Reducer.

### 3. Growth Memory (long-term, derived, curated)

The relationship layer that makes the companion a companion:

- **Narrative memory**: past arcs, characters, story callbacks, orchestrator
  adaptations ("outdoor tasks get swapped 60% of the time").
- **Preference/personality memory**: "loves rabbits", "anxious when tasks
  feel like tests", "gives up on physical challenges but retries verbal
  ones".
- **Parent-coach memory**: past consultations, parent concerns, coaching
  history (ADR-009).

Growth Memory is *derived* from Event History (via LLM summarization jobs,
Decision-Traced) and *curated*: entries carry confidence and
last-reinforced-at, decay without reinforcement, and must always be able to
cite supporting events. It never overrides fact — when Growth Memory and
Event History disagree, history wins and the memory entry is marked stale.

## Boundary rules

1. Mastery/capability numbers come ONLY from the Reducer over Event History —
   Growth Memory never feeds numeric state (ADR-004 discipline).
2. Growth Memory feeds prompts (Planner, Mission Designer, Orchestrator,
   Coach) — it colors judgment, it doesn't move numbers.
3. No vector store in v1 (Q10); scale to it when narrative history outgrows
   recency queries.

## Consequences

- Storage layout: one `events` table; runtime tables; `growth_memory` table
  with provenance fields (`supporting_event_ids`, `confidence`,
  `last_reinforced_at`).
- A nightly/hygiene job (post-MVP) maintains Growth Memory: reinforce,
  decay, mark stale.
