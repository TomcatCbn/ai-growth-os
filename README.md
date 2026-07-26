# AI Growth OS v0.3

**Doudou Rabbit is not an AI teacher — it is the child's AI companion.
Relationship First: first prove a child keeps coming back to the rabbit,
then prove the growth-intelligence underneath.**

不是 AI 老师每天发任务，而是 AI 伙伴（豆豆兔）带孩子经历一段段成长冒险。
**唯一权威基线：`docs/constitution.md`。**

## North Star

Child Return Rate（`return_rate_d2` / `d7` / `d14`，真实日历日期）。
明确不衡量：任务完成率、学习时长、分数排名。

## Phase 路线

- **Phase 0 关系验证（当前）**：Session API + Story Player（消费 Scene DSL）
  + 真实关系事件（session.started / session.interaction /
  callback_offered·recognized / child.requested_doudou）+ 真实资产。
- **Phase 1 Growth MVP**：Child Twin 分层激活、Growth Decision、Parent
  Insight、Voice Interaction。
- **Phase 2 Growth OS**：Knowledge Graph、Agent Runtime、Content OS、多模态。

## Core loop

```
Child opens player → POST /api/v1/session/start → Runtime JSON (Scene DSL)
→ Story Player 展示豆豆兔 → child chooses / speaks → REAL interaction events
→ next day: voluntary return → Doudou references shared memory
→ callback recognized? → relationship metrics (return rate, trust)

后台成长闭环（Phase 1 资产，已建）：
Observe → Evidence → Reducer (state) → COMPUTE Frontier (code)
→ Planner Decision (LLM, within frontier) → Growth Arc → Evidence → Event Store
```

The system always holds exactly one `active_mission`. Re-planning triggers
only on: evidence submitted, mission stalled, or parent request.

## Read next

- `docs/constitution.md` — the single authoritative baseline
- `docs/architecture.md` — layers, agents, invariants
- `docs/adr/` — ADR-001 … ADR-022 (all load-bearing decisions)
- `docs/execution-notes.md` — running ledger incl. 「路线偏离」
- `schemas/` — the contracts (source of truth)
