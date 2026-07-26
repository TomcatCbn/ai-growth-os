# Project Constitution — AI Growth OS

唯一权威基线（v1.0，2026-07-26）。本文件合并此前三套并存基线：
README/architecture（Mission-Centric Growth OS）、execution-notes（Twin
落地计划）、Engineering-Spec v1.1（Relationship First）。冲突时以本文件为准。

## 项目身份

AI Growth OS 的首个产品：**Doudou Rabbit Companion** — 豆豆兔不是 AI 老师，
是孩子的 AI 成长伙伴。MVP 用户：4-6 岁儿童；家长是观察者，不是管理者。

## 北极星（不可协商）

**Relationship First：先证明孩子愿意持续回来见豆豆兔，再证明成长推断能力。**

- North Star Metric：Child Return Rate（`return_rate_d2`，D7/D14 窗口）
- 辅助：adventure continuation、callback recognized、家长看到变化
- 明确不衡量：任务完成率、学习时长、分数排名

## 阶段路线

- **Phase 0 关系验证（当前）**：Session API + Story Player + 第一次冒险 +
  关系记忆 + 真实资产 + 真实 Session/Relationship 事件。验收：一个孩子
  7–14 天连续回来、豆豆兔记得共同经历。
- **Phase 1 Growth MVP**：Child Twin 分层激活、Growth Decision、Pattern/
  Template Library、Parent Insight、Voice Interaction（非 voice chat）。
- **Phase 2 Growth OS**：Knowledge Graph（PG 表模拟起步）、Agent Runtime、
  Content OS、多模态 Evidence。

已建成的 Growth Intelligence 模块（Twin 投影 / Tendencies / Pattern
Library / Partner State / Family Model / 评估体系）是 Phase 1 资产，
随 Phase 0 垂直闭环逐步激活，不再孤立扩张。

## 架构不变量（援引现有 ADR，编号唯一）

- ADR-002 事件是唯一事实；Reducer 是唯一数值写者。
- ADR-003 Frontier 由代码计算，LLM 只在合法集合内选择。
- ADR-004 数值状态只有两个 raw pocket；能力分数是派生视图。
- ADR-007 Arc 契约不可变测量计划；编排只调"怎么陪"。
- ADR-008 所有进人眼内容过 Output Guard；PII 进不了事件库。
- ADR-010 LLM 全走 TrackedProvider + Prompt OS 版本化。
- ADR-012/013 Twin/Memory 是投影，带溯源，历史永远赢。
- ADR-014 Scene DSL 是唯一场景协议。
- ADR-015+ 见 docs/adr/（模块化单体、事件驱动、AI 组合、记忆策略、
  Growth Decision Engine、Agent Runtime、Content OS、AI 员工治理）。

## AI 组合边界

AI 负责：个性化剧情、对话、任务变化、推理。
AI 不负责：豆豆兔是谁（Character Bible 冻结）、核心成长目标、世界规则、
自由生成儿童内容流程。

## Non-goals

课程商城/题库/考试/排名；24 小时在线陪聊；AI 视频进主链路；多伙伴
（只有豆豆兔）；Neo4j/GraphRAG（PG 表模拟起步）；摄像头监控。

## AI Developer Rules

1. 动手前读本宪法 + 相关 ADR。
2. 架构变更必须先写新 ADR（编号唯一，不可复用）。
3. 禁止：新增服务、修改核心 Domain 契约、扩大当前 Phase 范围、引入
   复杂基础设施。
4. 每个变更必须有测试；契约违规必须硬失败。
5. 偏离既定路线时，选最保守退路并立即记录在
   docs/execution-notes.md 的「路线偏离」栏。
