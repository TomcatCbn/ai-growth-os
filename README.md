# AI Growth OS v0.2

**Not an AI teacher assigning daily tasks — an AI companion (Doudou Rabbit)
leading children through growth adventures, while coaching families as a
Family Growth Coach.**

不是 AI 老师每天发任务，而是 AI 伙伴（豆豆兔）带孩子经历一段段成长冒险，
同时做家庭的成长协作者。

## Component map

| Component | Role |
|---|---|
| os-taxonomy | Knowledge source (知识来源) |
| Capability Model | Growth language (成长语言) |
| Child Model | Understanding the child (理解孩子) |
| Agents | Growth decisions (成长决策) |
| Evidence Engine | Understanding change (理解变化) |
| AI Companion | Experience (体验) |

Current target: MVP children aged 4-6; architecture supports 7-12+.

## Core loop (mission-centric)

```
Observe → Update Child Model → COMPUTE Growth Frontier (code)
→ Candidate Goals → Planner Decision (LLM, within frontier)
→ Generate Growth Arc (Doudou Rabbit adventure, 2-4 chapters)
→ Child experiences (Experience Orchestrator)
→ Collect Evidence (check-in + free observation + child retelling)
→ Reducer updates model → Event Store
```

The system always holds exactly one `active_mission`. Re-planning triggers
only on: evidence submitted, mission stalled, or parent request.

## Read next

- `docs/architecture.md` — layers, agents, invariants
- `docs/data-pipeline.md` — build-time + run-time data flow
- `docs/adr/` — ADR-001 … ADR-012 (all load-bearing decisions)
- `schemas/` — the contracts (source of truth)
