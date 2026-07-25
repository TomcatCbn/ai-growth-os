# ADR-014: Scene DSL — Element-Level Declarative Scene Protocol

- Status: Accepted
- Date: 2026-07-26

## Context

The v4.5 blueprint froze a Scene DSL for the client Story Player: backend
describes WHAT happens (an ordered list of element nodes), the client decides
HOW to play it. Our Phase 6 emitter used a session-segment structure with
freeform narration/assets/actions per scene — a different shape for the same
purpose. Two scene protocols must not coexist.

## Decision

Adopt the blueprint's element-level Node DSL as THE scene content format
(schemas/scene-dsl.schema.json):

- `dialogue` — {speaker, text, voice} (voice: fixed identity, e.g. "doudou_v1")
- `choice` — {prompt, options[{id, text}]}
- `animation` — {asset, duration_seconds}
- `voice` — {prompt} (voice INTERACTION at key moments, not voice chat)
- `reward` — {kind, text} (celebration moments)

The five-segment SESSION (greeting → choice → adventure → memory → farewell)
remains the pacing container (schemas/runtime-json.schema.json); each
segment's scene is now expressed as a node sequence instead of
narration/assets/actions triples. Sessions answer "how long and in what
order"; nodes answer "what exactly plays".

Future node types (drawing/camera/drag/AR) extend the enum WITHOUT backend
shape changes — the client ignores unknown nodes gracefully.

## Consequences

- runtime/story/emitter.py emits nodes per segment; scene assets fold into
  animation nodes.
- Node definitions appear in both scene-dsl (standalone scene document) and
  runtime-json (embedded in sessions) schemas; they must be kept identical —
  drift is caught by contract tests.
- All node text remains Output-Guard territory; the emitter stays
  deterministic.
