# ADR-004: Capability State Model

- Status: Accepted
- Date: 2026-07-24

## Context

The original ChildState schema had three parallel pockets: `skills`,
`growth_state` (curiosity, persistence, ...), and `interests`. With the
adoption of os-taxonomy (ADR-001) two gaps appeared:

1. Topic mastery is per-topic, but parents, the Planner, and reports speak in
   *capabilities* (observation, persistence, storytelling). A capability layer
   did not exist.
2. A single topic→capability weight conflates three different questions:
   does the topic *train* the capability? is that training *observable*
   through the topic? how *important* is the capability at this age?

This is a load-bearing decision: Agent contracts, Memory, and parent reports
all build on it.

## Decision

### 1. Unified Capability State; `growth_state` pocket deleted

ChildState stores exactly **two raw pockets**:

- `topic_mastery` — sparse per-topic `{mastery, confidence, evidence_count,
  last_evidence_at}`; untouched topics fall back to an age-based prior.
- `interests` — label → weight (seeded taxonomy + controlled emergence).

`growth_state` as a stored pocket is removed. All capability scores are
**derived views**, never stored.

### 2. Capability taxonomy: charter + LLM candidates + expert adjudication

A human-authored **Capability Charter** defines the philosophy and boundaries
of each domain (what counts as a distinct capability, granularity rules,
boundary cases). LLM generates candidate capabilities from the topic set;
experts adjudicate (accept / reject / merge) against the charter. Target:
6 domains × 5-8 capabilities ≈ 30-40 capabilities.

### 3. Topic→Capability mapping: many-to-many, four dimensions

No single `weight`. Each mapping edge carries:

| Dimension | Question it answers | Consumed by |
|---|---|---|
| `relevance` | Does this topic train this capability? | Capability score aggregation: `score(c) = Σ(mastery × relevance) / Σ(relevance)` |
| `evidence_strength` | How observable is growth in this capability through this topic? | Evidence EMA step size (ADR-002) |
| `age_fit` | How developmentally appropriate is this topic as a vehicle for this capability at the child's age band? | Aggregation weighting + Planner ranking |
| `development_priority` | How important is this capability itself at this age band? | Planner frontier ranking (ADR-003) |

The two age-dependent dimensions (`age_fit`, `development_priority`) are
parameterized by age band. `development_priority` defaults come from a
(capability × age_band) priority table (~30 × 3 rows, human-reviewable) and
may be overridden per edge; the other dimensions are edge-local. Rationale
for keeping the two separate: the same capability (e.g. persistence) matters
differently at 4 vs. 10 (priority), and the same topic can be a good or poor
*vehicle* for a capability depending on age (age_fit).

### 4. Capabilities have two evidence sources

- **Topic-derived evidence (primary):** evidence lands on topics; capability
  scores aggregate via `relevance`.
- **Direct capability evidence (secondary/exception):** observations with no
  honest topic anchor (e.g., "kept at a puzzle for 40 minutes") may update a
  capability directly. Discipline: (a) evidence_strength for this channel is
  capped at 0.5 — soft-trait judgments detached from concrete behavior are
  the least reliable; (b) the golden set must include pure-soft-trait
  observations to test this channel's extraction discipline.

## Consequences

- `schemas/child-state.schema.json` updated: two raw pockets, no derived
  scores persisted.
- Parent reports and the Planner read the same derived capability view —
  one aggregation formula, defined once, versioned.
- Mapping data lives in its own file keyed by topic id, never mutating the
  upstream taxonomy (ADR-001 provenance discipline).
- Explainability cost accepted: "why did the cognitive score move?" is
  answered with a small weighted table, not one number.
