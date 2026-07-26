# ADR-015: Modular Monolith First

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-001 (renumbered into this repo's sequence)

## Context

Early-stage product risk is direction validation, not scale. Microservices
would tax every iteration; a big ball of mud would tax every later split.
The repo already runs as one Python process with strictly separated modules
(runtime/*, knowledge/*, evaluation/*).

## Decision

One deployable modular monolith. Module boundaries are enforced by contract:
modules communicate via events and validated contract objects, never by
reaching into each other's internals. Future service extraction
(Family / Twin / Growth Engine / Content / Runtime) splits along these
existing module lines.

## Consequences

- No new services without an ADR.
- Cross-module imports of private members are architecture bugs.
- Event Store remains the only inter-module write channel for state.
