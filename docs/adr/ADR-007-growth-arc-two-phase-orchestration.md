# ADR-007: Growth Arc & Two-Phase Experience Orchestration

- Status: Accepted
- Date: 2026-07-24

## Context

Per ADR-006, a Mission is the unit of the runtime loop and may span days.
Decision (Q20/Q21): a Mission is a chaptered **Growth Arc**, not a single
activity card; the target product is companion-led (voice + real-world +
return conversation), demo renders chapters as parent cards.

Key risk being prevented: the companion degrading into a hard-coded
"voice story + real task" gimmick, or — the opposite failure — a free-form
runtime improviser that invalidates the evidence measurement plan.

## Decision

### 1. Mission = Growth Arc

An Arc binds five things, all fixed at creation:

- **Goal set**: exactly one `primary_goal` (topic) plus optional
  `supporting_goals` (capabilities/topics). E.g. "Forest Code Adventure":
  primary `pattern_recognition`; supporting `persistence`,
  `language.expression`. A single-goal arc cannot carry a real narrative.
- **Narrative arc** (2-4 chapters: hook → obstacle → resolution)
- **Difficulty gradient** (easiest first)
- **Growth hypothesis** ("completing this arc should move topic X mastery
  0.4 → 0.6; key observable signal: child verbally predicts the next item")
- **Measurement plan** (per-chapter observation checklist derived from the
  topic's evidence criteria)

At arc close, Planner compares hypothesis vs. actual evidence. Confirmed /
refuted becomes **meta-evidence**: the system learns which kinds of arcs
work for this child, not just what the child knows.

### 2. Two-phase orchestration — "测什么静态，怎么陪动态"

| Phase | Owner | Output | Mutability |
|---|---|---|---|
| Design time | Mission Designer | **Growth Intent + Chapter Blueprint** (hypothesis, measurement plan, default modality per chapter) | Immutable contract |
| Run time | Experience Orchestrator | **Modality rendering** (voice / real-world task / drawing / mini-game / parent-child activity) | Limited adaptation rights |

The Orchestrator is an **Experience Orchestrator** — conductor of all
experience modalities, not a "voice companion" feature. It may substitute
registered modalities per chapter (rainy day → indoor variant) but may NOT
change the growth goal or measurement points. All adaptations are recorded
in narrative memory and become preference signals for the World Model
(e.g., "outdoor-task adaptation rate 60%").

### 3. Chapter runtime structure

Chapters model the companion-led triad (`narration` / `real_world_task` /
`return_prompt`) with an `interaction_mode` field and pluggable renderers.
Demo uses the parent-card renderer; adding TTS/voice-input later changes
renderers only — zero data-structure change. The return-conversation
(child's own retelling, possibly parent-transcribed) is a dedicated,
high-weight evidence channel — the highest signal-to-noise evidence source.

Dynamic per-chapter branching (evidence-driven next-chapter regeneration)
is architecturally reserved (schema must not preclude it) but out of scope
for v1: it couples narrative generation with pedagogical adaptation, the
two hardest generation risks at once.

## Consequences

- Next artifact: Mission Runtime Schema (Arc + Chapter + state machine).
- Experience Agent in docs/architecture.md is formally the Experience
  Orchestrator; Mission Designer and Orchestrator have separate contracts
  and separate quality bars.
