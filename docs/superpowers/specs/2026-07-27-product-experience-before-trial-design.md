# Product Experience Before Trial — Design

**Status:** Approved direction
**Date:** 2026-07-27
**Phase:** Phase 0 — Relationship Validation
**Authority:** `docs/constitution.md`

## Goal

Raise the Doudou Rabbit web experience from a technically complete demo to a
child-usable experiment candidate, then run a 7–14 day real-child relationship
trial. The work must improve the experience without expanding into Phase 1
Growth MVP or Phase 2 infrastructure.

## Success boundary

The experience is ready for the trial when a 4–6-year-old can independently
enter, complete, and leave a short adventure; can understand Doudou through
visual and spoken feedback; cannot accidentally create misleading relationship
events; and an adult can verify the experiment data without inspecting SQLite.

The trial remains the Phase 0 product acceptance gate. Experience polish is a
prerequisite, not a replacement, for measuring `d2_returned`,
`active_days_d7`, `active_days_d14`, adventure continuation, and callback
recognition.

## Delivery approach

Use an experience-gate sequence rather than a broad product build:

1. Stabilize the local run contract on port 8767.
2. Make the child journey understandable, resilient, and touch-safe.
3. Add a coherent forest presentation and a small reusable Doudou motion set.
4. Add fixed Doudou voice playback and explicit pacing rules.
5. Prepare enough multi-day content and callbacks to make returning meaningful.
6. Add experiment identity and a minimal adult-facing data check.
7. Pass internal experience acceptance before recruiting a child participant.
8. Run the 7–14 day trial and review the relationship metrics.

This order is recommended because each stage creates a testable improvement and
keeps the experiment data trustworthy. Asset-first work would look better
sooner but could hide interaction defects; broad product work would delay the
Phase 0 learning goal.

## System boundaries

### Run contract

Port 8767 is the canonical local demo port. Runtime documentation, browser
regression scripts, and developer commands must agree. The application remains
a single FastAPI modular monolith served by Uvicorn.

### Child journey

`/player` remains the child entry and `/preview` remains the adult preview.
Both consume the same Scene DSL player, while server-issued entry IDs preserve
the existing `child_mode` and `parent_preview` event boundary. Work focuses on
clear start/resume/end states, large touch targets, disabled duplicate actions,
visible retry behavior, and a route back from recoverable failures.

### Visual experience

The forest becomes a layered, responsive stage rather than a plain gradient.
Doudou uses a bounded asset vocabulary based on the Character Bible: idle,
appear, explore, react, celebrate, and farewell. Assets remain reviewed static
files; unrestricted image generation does not enter the child runtime.

### Voice and pacing

Doudou uses one fixed voice identity, `doudou_v1`. Spoken lines are generated or
pre-rendered through a bounded adapter and cached by content/version key. The
player must remain usable when audio is unavailable. Scene advancement follows
explicit minimum display time, audio completion, and child-action rules; it must
not rely on arbitrary browser delays.

### Multi-day content

The existing Pattern and Adventure Template libraries remain the source of
structure. The experience set adds a small trial-ready sequence with meaningful
next-day callbacks and visible continuity. This work expands authored content,
not the Growth Intelligence architecture.

### Experiment readiness

Child and preview traffic remain isolated. A trial participant receives a
stable server-side identity and a documented start route. The adult view exposes
session days, callback outcomes, continuation, and data-health warnings. It does
not introduce completion-rate, study-time, score, or ranking metrics.

## Data flow

1. The child opens a server-issued child entry.
2. The server starts or resumes a session and persists the full Scene DSL
   document in `session.started`.
3. The player renders bounded assets, voice, and pacing metadata.
4. Each accepted action records one validated interaction; duplicate taps and
   preview actions cannot alter child relationship metrics.
5. Relationship projections update from the event log.
6. The adult readiness view reads those projections and reports missing or
   inconsistent data without rewriting source events.

## Failure handling

- Session start failures retain the start screen and offer retry.
- Interaction failures re-enable the relevant control and show a child-safe
  retry cue; the client does not advance optimistically.
- Missing image or audio assets fall back to the neutral Doudou image and text.
- Audio autoplay restrictions show an explicit sound-enable action.
- Unknown or expired entries fail closed and direct the adult to issue a new
  entry.
- Projection/data-health errors are visible to adults and never silently
  converted into successful relationship signals.

## Verification strategy

Every behavioral change follows test-first development. Contract and unit tests
cover entry identity, pacing state, asset fallback, interaction idempotency,
and relationship projections. Browser regression covers child start, each Scene
DSL node type, retry behavior, audio-disabled fallback, successful completion,
preview isolation, and persisted events.

Internal acceptance uses a device-oriented checklist on representative phone
and tablet viewport sizes. A trial starts only after automated checks pass and
an adult can complete the checklist without developer intervention.

## Milestones and gates

| Priority | Milestone | Outcome | Exit gate |
|---|---|---|---|
| P0 | Run baseline | Port and commands consistently use 8767 | Fresh-start smoke check passes |
| P1 | Child journey | Independent, touch-safe adventure flow | Browser journey and retry checks pass |
| P2 | Visual experience | Coherent forest and bounded motion language | Phone/tablet visual checklist passes |
| P3 | Voice and pacing | Fixed Doudou voice with text fallback | Audio-on/off journeys both pass |
| P4 | Multi-day content | Trial sequence has meaningful continuity | Callback matrix has no dead ends |
| P5 | Experiment readiness | Stable identity and inspectable metrics | Preview cannot contaminate trial data |
| P6 | Internal acceptance | Product is safe to put in a child's hands | Automated suite + acceptance checklist pass |
| P7 | Real-child trial | 7–14 days of relationship evidence | Metrics reviewed against Phase 0 baseline |

## Non-goals

- Flutter or another production client
- Open-ended voice chat
- Knowledge Graph, Agent Runtime, or vector-memory expansion
- Multiple companions
- Parent task assignment or child performance dashboards
- Completion, study-time, score, or ranking optimization

## Risks and controls

| Risk | Control |
|---|---|
| Polish expands indefinitely | Each milestone has a binary exit gate; defer work that does not unblock the trial |
| Audio introduces external fragility | Cache versioned output and preserve a complete text-only path |
| New visuals violate character consistency | Accept only Character Bible-reviewed bounded assets |
| Demo interactions pollute experiment data | Preserve server-issued identity and preview isolation tests |
| Content quantity delays learning | Build only the minimum coherent 7–14 day trial sequence |

