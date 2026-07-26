# ADR-022: AI Worker Governance

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-009 (renumbered)

## Context

Development is done by AI workers (code agents). The biggest risk is not
code quality — it is each worker locally optimizing with no one guarding
product direction.

## Decision

Binding rules for every AI worker session (mirrors docs/constitution.md):

1. Read the constitution and relevant ADRs before touching code.
2. Architecture changes require a NEW ADR first — never reuse numbers.
3. Forbidden without explicit human approval: new services, changes to
   frozen contracts (schemas/), scope expansion beyond the current phase,
   new infrastructure dependencies.
4. Every change ships with tests; contract violations must hard-fail.
5. Forced deviations take the most conservative fallback AND are logged
   immediately in docs/execution-notes.md 「路线偏离」 — never silently.

## Consequences

- docs/execution-notes.md is the running ledger of route decisions.
- The human (CEO) arbitrates anything the rules don't cover.
