# ADR-020: Agent Runtime — Workflow Now, Platform Later

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-006 (renumbered)

## Context

The blueprint's MVP needs only a handful of agent behaviors (companion,
adventure, memory). LangGraph or a multi-agent platform now would be
infrastructure ahead of need; but agent boundaries must exist so later
extraction is packaging, not redesign.

## Decision

Plain Python workflows in the modular monolith; agents are module
interfaces with contract-typed inputs/outputs. MVP agent surface:

- **Companion behavior** — partner callbacks, persona-consistent narration
  (Prompt OS: doudou_persona_v1 + Character Bible).
- **Adventure behavior** — pattern/template instantiation into arcs and
  Scene DSL sessions.
- **Memory behavior** — projections (twin, partner state, tendencies)
  over the event log.

No agent framework, no inter-agent message bus. Re-evaluate when we need
parallel specialist agents or human-in-the-loop workflows.

## Consequences

- "Agent" is a role name for a module boundary, not a process.
- Activation order follows the Phase route in docs/constitution.md.
