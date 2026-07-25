# Architecture

Final-review version (ADR-001 … ADR-012).

## Layers

```
                        AI Growth OS

                            Child
                              |
                     Experience Runtime        ← AI companion lives here
                              |
                    Mission Orchestrator       ← "怎么陪" (dynamic, ADR-007)
                              |
              ┌───────────────┴───────────────┐
       Growth Planner                  Parent Coach
       ("测什么", frontier,            (Family Growth Coach,
        goals, arcs)                    insight, ADR-009)
              │                              │
       Capability Model               Growth Insight
              │
       Evidence Engine                 ← understanding change (ADR-002)
              │
          Event Store                  ← facts, append-only (ADR-012)
              │
        Knowledge Layer
        os-taxonomy + Capability Taxonomy   (ADR-001/004/005)
              │
   ┌──────────┴──────────┐
 Safety Kernel      Evaluation System     ← cross-cutting (ADR-008/010)
```

## Components

| Component | Role |
|---|---|
| os-taxonomy | Knowledge source — Learning Ontology, upstream immutable |
| Capability Model | Growth language — 6 domains × ~30-40 capabilities, 4-dim mapping |
| Child Model | Understanding the child — 2 raw pockets + derived views |
| Evidence Engine | Understanding change — extraction contract, Reducer |
| Agents | Growth decisions — Planner, Mission Designer, Orchestrator, Coach |
| AI Companion | Experience — Doudou Rabbit, Experience Orchestrator |

## Agents

### Growth Planner
Input: Child State, frontier (code-computed), Growth Memory, recent evidence.
Output: Growth Plan (ranked within frontier + rationale). Long-term owner.
Must not: write ChildState, replace professional assessment.

### Mission Designer
Transforms the plan into a Growth Arc: goal set (primary + supporting),
narrative arc, difficulty gradient, growth hypothesis, measurement plan.
Emits the immutable Chapter Blueprint ("测什么", static).

### Mission Manager
Owns the present: exactly one `active_mission`, lifecycle transitions,
stall detection, re-plan triggers (evidence / stall / parent request).

### Experience Orchestrator
Runs chapters ("怎么陪", dynamic): modality rendering + limited adaptation
rights; never touches goals or measurement plan; logs adaptations.

### Parent Agent (Family Growth Coach)
Weekly growth narrative (moments → trends → one suggestion), on-demand
consultation, life-context intake. Iron rule: never compare.

## Core loop

```
Observe → Update Child Model (Reducer) → COMPUTE Growth Frontier (code)
→ Candidate Goals → Planner Decision (LLM, frontier-constrained)
→ Growth Arc → child experience (Orchestrator)
→ Evidence (check-in / free observation / child retelling)
→ Reducer → Event Store
```

## Invariants

1. Upstream knowledge immutable; our data is additive, id-keyed, versioned.
2. Event log is the only system of record; all state replayable.
3. Derived views are computed, never persisted.
4. LLMs make judgment calls; code computes constraints (frontier,
   aggregation, guards).
5. Human-facing text is Chinese; canonical knowledge stays English; runtime
   prompt language is a per-task choice.
6. **Every AI decision must be explainable (Decision Trace first):** any
   mission choice, capability change, or parent insight must answer — why,
   based on what, from which evidence.
