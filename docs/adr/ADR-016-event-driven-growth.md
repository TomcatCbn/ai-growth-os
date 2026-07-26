# ADR-016: Event Driven Growth

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-002 (renumbered)

## Context

Agents must never mutate child state directly — both for correctness
(replay, audit) and for the safety story (every change is a traceable fact).
Already established in ADR-002/ADR-011; this ADR binds the *agent* layer to it.

## Decision

Every growth-relevant change flows: Agent → Decision/Event → State
Transition (Reducer/Projection) → New State. Agents emit events and read
projections; they hold no write path to state tables. This repo implements
full event sourcing (append-only log + deterministic replay) — a strictly
stronger form of the spec's "Event Log + Projection".

## Consequences

- Any agent found writing state directly is a release blocker.
- Projections (Twin, Partner State, Metrics) stay recomputable from the log.
