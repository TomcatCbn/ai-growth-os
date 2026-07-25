# Data Pipeline

End-to-end data flow, per ADR-001..005. Read top to bottom: build-time
knowledge assembly, then run-time growth loop.

## Build-time: knowledge assembly (import pipeline)

```
os-taxonomy (submodule, v1 pin, FROZEN)
  ├── topics.json            1,590 topics
  ├── dependencies.json      3,221 prereq edges (hard/soft)
  └── clusters.json
        │
        ▼  import_taxonomy (deterministic, re-runnable)
  filter: age 4-6 subset (426 topics)
        │
        ▼  merge our own files (all keyed by stable id, never mutating source)
  ┌─────────────────────────────────────────────────────────────┐
  │ topics-local.json        hand-authored additions            │
  │                          (physical dev, exec function,      │
  │                           creativity — same schema)         │
  │ capability-taxonomy.yaml charter + adjudicated capabilities │
  │                          (6 domains × ~5-8, ADR-004)        │
  │ topic-capability-map.yaml edges: (topic, capability) ->     │
  │                          {relevance, evidence_strength}     │
  │ priority-table.yaml      (capability × age_band) ->         │
  │                          development_priority               │
  │ interest-seeds.yaml      seed interest taxonomy             │
  │ i18n/zh-CN.yaml          Phase 0: topic/capability names;   │
  │                          evidence criteria = human-polished │
  │ china-adaptation.yaml    (later) cultural overlay           │
  └─────────────────────────────────────────────────────────────┘
        │
        ▼  emit
  knowledge-base/ (merged runtime artifact, versioned, checksummed)
```

## Run-time: the growth loop

```
                ┌──────────────────────────────────────────┐
                │  knowledge-base (from build-time)        │
                └───┬──────────────┬───────────────┬───────┘
                    │ topics+deps  │ capability map│ priority+i18n
                    ▼              ▼               ▼
   ChildState ───────────────► FRONTIER ──────► GROWTH PLANNER (LLM)
   (2 raw pockets:             (code: prereqs   ranks within frontier using
    topic_mastery,              satisfied,      interests, priority table,
    capability_direct,          not mastered)   recent evidence → rationale
    interests)                                     │
                    ▲                              ▼
                    │                    MISSION DESIGNER (LLM)
                    │                    goal topic × interest
                    │                    × narrative memory
                    │                    → parent card (zh):
                    │                      story hook, offline activity,
                    │                      materials, OBSERVATION
                    │                      CHECKLIST (from i18n evidence)
                    │                              │
                    │                              ▼
                    │                       parent + child (offline)
                    │                              │
                    │                              ▼
                    │                    EVIDENCE (two channels, ADR-002)
                    │                    a) check-in: done/partial/none
                    │                    b) free observation (text)
                    │                              │
                    │                              ▼
                    │                    EXTRACTION (LLM, contract:
                    │                    [(id, signal, confidence, quote)])
                    │                              │
                    │                              ▼
                    │                    EVENT LOG (append-only, immutable)
                    │                              │
                    │                              ▼
                    └────────────── REDUCER (pure code; EMA: α × confidence
                                     × evidence_strength, Δ ≤ 0.2)
                                     → topic_mastery (+ capability_direct
                                       for unanchored soft-trait evidence)

   DERIVED VIEWS (computed, never stored):
   capability scores = Σ(mastery × relevance)/Σrelevance  ⊕  capability_direct
        │
        ▼
   PARENT AGENT → weekly report (zh): capability deltas, mission history,
   planner rationales, suggested next focus
```

## Side channel: evaluation

```
golden-set.yaml (20-30 scripted observations, hand-labeled,
incl. multi-topic / pure-chit-chat / pure-soft-trait cases)
        │
        ▼  run against EXTRACTION + EMA on every prompt/model change
   extraction precision ≥ 0.8, frontier legality = 100%
```

## Invariants

1. Upstream knowledge immutable; our knowledge is additive files keyed by id,
   versioned artifacts.
2. Event log is the only system of record; all state replayable.
3. Derived views are computed, never persisted.
4. LLMs never compute constraints (frontier, aggregation) — code does;
   LLMs make judgment calls (ranking, extraction, generation).
5. Human-facing text is Chinese; canonical knowledge stays English; runtime
   prompt language is a per-task choice.
6. Every AI decision is Decision-Traced: why, based on what, from which
   evidence.
