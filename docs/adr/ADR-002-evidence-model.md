# ADR-002: Evidence Model

- Status: Accepted
- Date: 2026-07-24

## Context

"Evidence over evaluation" is a core product principle. The state update loop
(Child State -> ... -> Evidence -> Memory) breaks without a defined evidence
model. Two capture channels with complementary failure modes were considered.

## Decision

1. **Two-layer evidence capture:**
   - *Structured check-in* per Mission (completed / partial / not completed +
     optional note). Anchors the loop, low ambiguity.
   - *Free-form parent observation*, submittable any time. Captures growth
     outside planned missions — the majority of real growth at ages 4-6.
2. **LLM extraction contract** for free-form observations:
   `[(topic_id | capability_id, signal_strength, confidence, verbatim_quote)]`.
   The mandatory verbatim quote enables human spot-checking.
   Pure-chit-chat observations must extract to empty (false-positive
   discipline is tested in the golden set).
3. **Mastery update: EMA**, `new = old + α * confidence * evidence_strength *
   (signal - old)`, with a per-update delta cap (≤ 0.2) and confidence growing
   with evidence count. Chosen over BKT (unfittable parameters at demo stage)
   and LLM-adjudicated updates (non-reproducible).
4. **Evidence is fact, not state.** Evidence never mutates state directly.
   The flow is `Evidence → Reducer → State`: the Reducer (pure, deterministic
   code — no LLM) applies the EMA. LLMs extract signals from raw text; only
   the Reducer writes state. This keeps state mutation testable and
   replayable.
5. **Append-only event log**: every evidence item and every resulting state
   update is an immutable event; all state is replayable. This preserves the
   option to swap in BKT or other models later without data loss.

## Consequences

- Evidence extraction quality is the system's top technical risk; it gets a
  dedicated golden-set evaluation (see demo acceptance criteria).
- The event log is the single source of truth; all views are derivable.
