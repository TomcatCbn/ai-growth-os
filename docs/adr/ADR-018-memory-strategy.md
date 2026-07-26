# ADR-018: Memory Strategy — Session + Relationship + Growth, Importance-Scored

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-004 (renumbered)

## Context

"豆豆兔不是一直在线等待孩子的 AI，而是每次见面都会重新想起孩子的 AI。"
Unbounded context is costly and drifts; not everything is worth remembering.

## Decision

Three memory classes (refining ADR-012):

- **Session memory** — lives for one adventure; discarded except what the
  Memory pipeline promotes.
- **Relationship memory** — shared moments with the partner
  (runtime/twin/partner.py), importance-scored and tiered:
  ≥0.8 long_term, ≥0.5 standard, <0.5 fading, <0.1 not stored.
- **Growth memory** — arc verdicts and meta-evidence
  (runtime/state/memory.py), with mandatory provenance.

Every memory entry carries confidence, supporting event ids, and
last-reinforced-at. Memory feeds prompts; it never moves numeric state.

## Consequences

- partner-state.schema.json enforces importance + tier fields.
- A nightly hygiene job (post-MVP) decays unreinforced entries.
