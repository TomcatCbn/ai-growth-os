# ADR-008: Safety as Runtime Kernel — Three-Layer Guardrail Model

- Status: Accepted
- Date: 2026-07-25

## Context

AI Growth OS is a children's product. The ordering principle that
distinguishes children's AI from general AI:

> General AI optimizes first for answer quality; children's AI must optimize
> first for trustworthiness.

Safety is therefore not an add-on module or a prompt section — it is part of
the **Runtime Kernel**: the single channel through which all data enters and
all content leaves. Default-deny, explicit-pass, independently testable.

## Decision: three-layer guardrail model

### Layer 1 — Data Safety (Input Guard)

- PII redaction at ingestion, BEFORE anything touches the append-only event
  log (the log is immutable — PII written is PII kept forever).
- Data minimization: the system stores growth signals, not raw life records.
- Injection/abuse filtering on all free-text input.
- Retention & deletion policy: a parent's "delete my child's data" must be
  executable despite the append-only log (crypto-shredding or keyed
  pseudonymization — the event log stores pseudonymous ids).

### Layer 2 — Generation Safety (Output Guard)

- Independent review stage between any LLM output and any human eyeball
  (child or parent): age-appropriateness, fear/violence red lines, no
  medical/psychological diagnosis, no commercial inducement, no requests
  for personal information from the child.
- The guard is a separate component (rules + dedicated review prompt), with
  its own **red-line test set** — adversarial inputs and boundary outputs —
  run on every prompt/model change, mirroring the golden-set discipline
  (Q12).
- Never embedded inside generation prompts as the only defense.

### Layer 3 — Interaction Safety (relationship governance)

The layer generic AI products don't have: the companion has a *relationship*
with the child over months and years. Rules:

- **No engagement-maximizing mechanics** aimed at the child: no streaks, no
  loss-framed notifications, no guilt loops. Retention is a parent metric,
  never a child-side design goal.
- **Screen-time boundaries**: sessions are short by design; the companion
  itself closes interactions ("豆豆兔要去森林深处了，明天见") rather than
  maximizing dwell time.
- **No parasocial displacement**: the companion never positions itself as a
  replacement for parents or friends; it actively routes children toward
  real-world and human interaction (consistent with the real-world-activity
  principle).
- **Parent visibility & override**: parents can see everything the companion
  said and can interrupt/correct it; the companion has no private channel
  to the child.

## Safety Memory

Safety events are themselves tracked (dedicated safety event stream, part of
the event store but a separate, access-controlled table): every guard
rejection, near-miss, red-line test failure, and adaptation of guard
thresholds. Purpose: detect drift — e.g. "model X generated fear-content 3
times this week" — before it becomes an incident. Safety Memory feeds the
Evaluation module's red-line suite.

## Consequences

- Every component that produces or consumes text declares which guard layer
  it passes through; the pipeline diagram gains a mandatory guard band.
- Red-line test set becomes a first-class repo artifact alongside the
  golden set.
- Interaction-safety rules constrain future feature design (e.g., any
  gamification proposal must pass Layer 3 review).
