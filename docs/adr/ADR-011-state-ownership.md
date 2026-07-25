# ADR-011: State Ownership

- Status: Accepted
- Date: 2026-07-25

## Context

Multiple agents (Planner, Mission Designer, Orchestrator, Parent Coach) act
on shared state. Without explicit ownership, multi-agent systems drift into
"anyone writes anything" — un-debuggable and un-auditable.

## Decision: write permissions by module

| Module | May write | May NOT |
|---|---|---|
| Evidence Engine (extraction) | New evidence items (into Input Guard → event log) | State |
| Reducer (pure code) | State transitions derived from events | Raw evidence |
| Growth Planner | Growth Plans (proposals, with rationale) | ChildState, missions |
| Mission Manager | Mission lifecycle transitions (activate/close/stall) | Growth goals |
| Mission Designer | New Mission Arcs (draft) | State |
| Experience Orchestrator | Modality adaptations (logged to narrative memory) | Goals, measurement plan |
| Parent Coach | Parent insights, consultation replies | ChildState |
| Safety Kernel | Rejections + safety events | Content itself |

Hard rules:

1. **No agent writes ChildState directly.** State changes only via
   `Evidence → Reducer → State` (ADR-002). Planner proposing ≠ state change.
2. Every write goes through the Safety Kernel band (ADR-008).
3. Every LLM judgment emits a Decision Trace record (ADR-010).

## Consequences

- The runtime can enforce ownership mechanically (each module gets a narrow
  store interface, not the whole DB).
- "Who changed this and why" is always answerable from event log + traces.
