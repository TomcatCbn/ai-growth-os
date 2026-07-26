# 执行笔记 — Child Digital Twin / 性格探索 落地计划

来源：ChatGPT 对话《性格探索设计》（share 6a64e2be，下称"蓝图 v2.1"，24 轮决策记录）
项目基线：Phase 0 骨架已完成（contracts / 事件重放 / safety 深模块 / capability 派生 / 评估体系 / Parent Coach），54 测试通过，评估门槛 PASS。

## 路线偏离

> 开发纪律：任何逼迫偏离本计划的极端情况，选最保守退路，立刻在此栏记录，不隐瞒。

| 日期 | 偏离内容 | 原因 | 保守退路 |
|----|--------|----|--------|
| 2026-07-26 | **实施顺序调整**：原计划继续扩 Growth Intelligence（Twin/Agent/Knowledge），改为先做 Phase 0 儿童体验垂直闭环（Story Player + Session API + 真实事件 + 真实资产） | 第三份评审指出：长期方向对齐但顺序背离新北极星（Relationship First）；已建成的 Twin/Metrics 在"孩子尚未真正使用产品"的前提下语义不成立（child_retelling 被误当主动回访；trust 实为任务完成指标） | 不删任何已建模块（评审确认"已经对齐的部分"全部保留）；停止新增 Twin/Agent/Knowledge 模块；只做垂直闭环所需的最小增量 |

## 蓝图 vs 现状：差距分析

### 已收敛（无需返工）
- 事件溯源、单一 active mission、LLM 只作"皮层"、Arc 两阶段编排、证据纪律、重规划三触发点 — 蓝图与 ADR-002/003/006/007/010 一致。
- 蓝图"Agent 不直接改 Child Model，一律产 Evidence"= 现有 Reducer 唯一写者纪律。

### 缺口（蓝图要求、仓库没有）
1. **Child Digital Twin**：结构化 Twin（identity/interests/capabilities/motivation/learning_pattern/relationship + family_goals/constraints），Raw State vs Insight State 分离，Insight 带 confidence。对话 Q13 用户推翻 MVP 轻记忆，选了完整 Twin（"方便朝着最终目标走"）。
2. **Tendencies 层**：trait 证据 JSON（`{trait, evidence, confidence}`）；"性格不是测出来的，是陪伴中发现的"；不贴标签。
3. **Growth Pattern Library**：5 个成长模式（探索发现/创造建造/帮助伙伴/克服挑战/故事创作），Arc = 模式模板 + AI 个性化（Q18 选 B）。当前只有一个硬编码 ARC_TEMPLATES。
4. **Partner/Relationship Model**：豆豆兔关系记忆（trust_level、story_progress、剧情回调"还记得昨天的小星星吗"）。
5. **Mission Score 权重**：Child Engagement 40% + Growth Value 30% + Family Goal 20% + Novelty 10%；家长目标经"兴趣桥"转译为冒险。
6. **Agent 结构**：Orchestrator + Specialists；MVP 3 个 Agent（Partner / Adventure Generator / Memory）。当前 LLM 调用散落在 extractor/planner。
7. **Story Runtime JSON**：`GrowthArc → Chapter → Scene → Activity → Reflection`；客户端是消费 Runtime JSON 的 Story Runtime（非游戏引擎）；五段式 Session。
8. **关系指标**：主动回来率、伙伴记忆反馈、情绪连接 — 不看完成率/学习时长。

### 与现有 ADR 的张力（须在动手前定调）
- **T1**：Q13 完整 Twin + Q21 结构化+向量混合 vs ADR-012 "v1 无向量库"。定调：只做结构化 Twin，向量延后（与 Q21 长期方向不冲突，保守）。
- **T2**：Twin vs ADR-004 "只有两个 raw pocket"。定调：Twin 是事件投影层，不新增 Reducer 直写状态；数值状态仍只来自 Reducer；Insight 条目带 confidence + 溯源事件（沿用 ADR-012 Growth Memory 纪律）。
- **T3**：Tendencies 是否成为新的 signal target_type。定调：不进 Reducer；tendency 是 Insight 层对既有证据的解读（observation first, interpretation second），避免破坏数值纪律。

## 分阶段计划

每阶段沿用既定顺序：Schema → 事件/投影 → 评估 → 接入 Runtime；全程 TDD。

### Phase 1 — Schema 与 ADR（纯契约，无运行时改动）
- ADR-013：Child Digital Twin（结构化投影层；记录 T1/T2/T3 定调）。
- 新 schema：`child-twin.schema.json`（identity/interests/capabilities/motivation/learning_pattern/relationship/family_goals/constraints）、`tendency.schema.json`、`growth-pattern.schema.json`、`partner-state.schema.json`、`family-model.schema.json`。
- 契约测试先行。
- 验收：schema 冻结 + ADR 评审通过；现有 54 测试不红。

### Phase 2 — Twin 投影 + Tendencies
- `runtime/twin/projection.py`：事件 → Twin（Raw 口袋引用 Reducer 结果；Insight 条目含 confidence、supporting_event_ids、last_reinforced_at；冲突时 Event History 赢，条目标 stale）。
- Tendency 推断：从 choice/证据事件生成 trait 条目（不贴结论标签，只累积证据）。
- 测试：投影确定性、重放一致性、stale 标记、溯源完整。

### Phase 3 — Growth Pattern Library
- `world-model/growth-patterns.yaml`：5 个模式模板（数据，不是代码），每个含章节骨架 + 难度梯度 + 关键信号。
- `generate_arc` 改为：模式模板 × 主题 × 孩子兴趣 实例化（蓝图 Q18 选 B）；现有 ARC_TEMPLATES 迁移为"克服挑战"模式。
- 评估：生成 arc 仍过契约 + Output Guard；黄金集不受影响。

### Phase 4 — Partner/Relationship Memory
- `partner-state` 投影：trust_level（来自 engagement 信号）、story_progress、可回调时刻库。
- Arc 生成时注入剧情回调（"还记得…"）；关系记忆进入 Planner/Orchestrator prompt（ADR-012 边界：上色不动数）。

### Phase 5 — Mission Score + Family Model 最小版
- Planner 评分接入四权重（40/30/20/10）；`family-model`：家长目标录入 → 兴趣桥转译（代码拼接，LLM 润色）。
- mock planner 同步实现权重，四个虚拟孩子验收测试更新。

### Phase 6 — Story Runtime JSON（契约先行，不做客户端）
- `runtime-json.schema.json`：scene/assets/actions（choose_one/drag_object/voice_answer）；arc → Runtime JSON 发射器；五段式 Session 结构进 schema。
- 客户端（RN/Flutter + 视频资产池）不在本仓库，另行立项。

### Phase 7 — 关系指标
- 事件类型：session.returned、partner.memory_callback_used、child.initiated；指标投影（主动回来率等）。
- 不做完成率/学习时长指标（蓝图明确）。

## 待用户确认的开放问题
1. ~~**Q24 未回答**：日常陪伴启动方式~~ → 已确认 **C：豆豆兔主动邀请 + 孩子随时召唤**（2026-07-26）。
2. 蓝图建议 MVP 3 个 Agent（Partner/Adventure/Memory）拆分 → 已确认 **先模块后拆分**：Phase 1-5 保持单进程模块，Agent 边界以模块接口预留。
3. 客户端（Phase 6 之后）是否另起仓库？（仍开放）

## 执行日志
- 2026-07-26 Phase 1 开始：ADR-013 + 5 个 schema + 契约测试。
- 2026-07-26 Phase 1 完成：ADR-013 落地（T1/T2/T3 定调 + Q24=C 记录）；child-twin / tendency / growth-pattern / partner-state / family-model 五个契约 + 14 个契约测试。68 测试全绿，ruff 干净。无路线偏离。
- 2026-07-26 Phase 2 完成：runtime/twin 投影 + 确定性 tendencies（证据链 + stale 纪律）；趋势计算收敛为共享 runtime/state/trends.py（coach/twin 共用）。75 测试全绿。无路线偏离。
- 2026-07-26 Phase 3 完成：growth-patterns.yaml 5 模式数据化（探索/建造/帮助/挑战/故事），select_pattern 按能力契合−近期使用选模式，generate_arc 实例化；四个孩子已呈现模式多样性。81 测试全绿。无路线偏离。
- 2026-07-26 Phase 4 完成：Partner 关系投影（trust、story_progress、callbacks、relationship_memory 带溯源）；未用回调织入 hook 叙述（"还记得我们的…吗"）并记 partner.callback_used 事件。87 测试全绿。无路线偏离。
- 2026-07-26 Phase 5 完成：Mission Score 四权重（engagement 40 / growth 30 / family 20 / novelty 10）进 mock 与 prompt；family-model + 兴趣桥（princess·数学）；朵朵全部 arc 收敛到数学主题。92 测试全绿。无路线偏离。
- 2026-07-26 Phase 6 完成：runtime-json.schema.json（五段式 session：greeting 30s → choice 60s → adventure 240s → memory 30s → farewell 30s）+ 确定性发射器。客户端不在本仓库。98 测试全绿。无路线偏离。
- 2026-07-26 Phase 7 完成：关系指标投影（主动回来、回调使用、孩子发起、trust）；明确不做完成率/学习时长。101 测试全绿，评估门槛 PASS，四个孩子全部 OK。无路线偏离。

## 第二次重审（对话 v4.5 + 架构评审 v1–v6 + 交付包 v1.1，share 6a64f48e）

新一致：Event Driven、模块化单体、Rule+LLM、固定资产+AI组合、Evidence First、Non-goals — 与现状吻合，无需返工。
新缺口（按优先级）：
- **G1** Family 一级对象（family_id、多孩子、Parent Profile；问题35）
- **G4/P5** Doudou Character Bible + Prompt OS 版本化（评审 v4.0/v5.0）
- **G2** Adventure Template Library 10 模板（评审 v4.0：探索3/创造2/社交2/情绪2/数学1）
- **G6** 节奏规则（连续失败降难度/连续成功加挑战；问题43）
- **G3** Scene DSL 对齐：对话冻结元素级 Node DSL（Dialogue/Choice/Animation/Voice/Reward），与本仓库 runtime-json（5段 session）形状不同 — 需 ADR-014 定夺
- **G7** Memory importance 评分与生命周期（评审 v3.0）
- **G8** North Star：D7/D14 Return Rate + Adventure Continuation 定义（问题47）
- **G9** Project Constitution + AI Developer Rules（交付包 v1.0/1.1）

### 待确认的 Phase 8–12（已全部执行完毕 2026-07-26）
- P8 Family 账号模型 ✅（family-account 契约 + builder + engine view；多孩子就绪）
- P9 Character Bible + Prompt OS ✅（content/doudou-bible.yaml 契约校验；prompts/*_v1.md 版本化，版本号进 decision trace）
- P10 Adventure Template Library ✅（10 模板数据化 + 节奏规则：连败 ease / 连胜 push；朵朵「princess·数学」线保持）
- P11 ADR-014 Scene DSL ✅（元素级 Node：dialogue/choice/animation/voice/reward；5 段 session 为节奏容器，scene 改为 Node 序列）
- P12 North Star + Memory importance ✅（return_rate_d2 / adventure_continuation 定义冻结；importance 三层 long_term/standard/fading，<0.1 不存）

G3 决策记录：对齐到 Scene DSL（用户拍板），落地为 ADR-014。
最终验证：121 测试全绿，ruff 干净，评估门槛 PASS，四个孩子全部 OK。无路线偏离。

## 第三次评审整改（Relationship First 顺序纠偏，2026-07-26）

1. ✅ 路线偏离已记录（见上方「路线偏离」栏）；docs/constitution.md 建立唯一基线。
2. ✅ 规范包重编号为 ADR-015~022 并提交（Scene DSL 已由 ADR-014 覆盖）；.DS_Store 清除。
3. ✅ 重启重复灌入修复（按 evidence day 幂等，防回归测试锁定）。
4. ✅ 真实 Session/Relationship 事件：session.started(initiated_by)/session.interaction/partner.callback_offered/recognized/child.requested_doudou；child_retelling 不再代理主动回访（评审用例已固化为测试）；trust 只由关系信号构成，与任务完成彻底脱钩。
5. ✅ P1 缺陷：append_safety/rationale 脱敏、trace 在 schema 校验之后写入、evidence.submitted 全契约校验、insight quotes 过 Output Guard、live 模式拒绝 mock 能力映射。
6. ✅ emit_session 接入 ChildEngine.start_session + POST /api/v1/session/start（+interaction +doudou/request）。
7. ✅ 最小儿童 Story Player（/player，消费 Scene DSL Node：dialogue/choice/voice/reward/animation）。
8. ✅ 真实豆豆兔 SVG 资产 4 个（happy/appear/explore/wave，符合 Character Bible 视觉规则），StaticFiles 挂载。
9. ⏳ 7–14 天真实使用数据验证回访 — 需真实孩子使用，非代码任务。

## 第四次评审整改（关系指标可测量化，2026-07-26）

1. ✅ 时间模型统一：session 事件用真实日历日期（ISO date）；回访定义冻结——首次启动是获客不是回访；session.returned 事件类型消除（去重）；新增 return_rate_d7/d14 窗口。
2. ✅ launch_source 诚实化：child_mode（player 启动按钮）vs parent_preview（家长仪表盘预览入口）；旧硬编码 initiated_by="child" 移除。
3. ✅ Callback 真实链路：offered/recognized 只由 player 实际交互产生（callback_shown/callback_recognized）；Arc 创建时不再提前记 offered。
4. ✅ Session 持久化：完整 session 文档存入 session.started payload；get_session 从事件日志重建；web demo 用每孩子持久 db，重启后旧 session 交互实测 OK。
5. ✅ Interaction 契约：session-interaction schema + 节点存在性 + choice 合法性 + callback moment 匹配，全部 ContractViolation 硬失败。
6. ✅ 重启幂等改为 (day, channel, raw_text) 稳定键，同日不同观察不再被误跳过。
7. ✅ 入口文档对齐：README v0.3 / architecture / next-steps 全部指向 constitution 与 Relationship First。

未采纳（记录）：scene-dsl 与 runtime-json 的节点定义重复（P3）——两文件已通过契约测试互相锁定，共享 $ref 需引入 schema registry，暂不值得。
最终验证：144 测试全绿，ruff 干净，评估门槛 PASS，重启重放实测通过。

## 第五次评审整改（事件完整性 + 留存语义，2026-07-26）

1. ✅ Interaction 契约：node_id 精确定位节点（emitter 节点 id 按 segment 唯一化）；voice.answer 必填；additionalProperties:false。
2. ✅ Callback 状态机：(session_id, moment) not_shown→shown→recognized|ignored，重复幂等、乱序硬失败（"recognized before shown"），首次答案生效。
3. ✅ 共享投影 runtime/state/relationship_events.py：metrics 与 trust 单源，WINDOWS 实际使用。
4. ✅ 留存语义：as_of_date 默认真实今天（停止回来指标会衰减，测试锁定）；cohort first_date + d2_returned（次日回访 T/F/None）；D7/D14 分母按可回来天数封顶；adventure_continuation 实现（次日同 arc）。
5. ✅ Evidence 幂等：稳定 source_key（profile timeline 序号），不再用内容指纹。
6. ✅ 入口分离：/player（child_mode，计入北极星）与 /preview（parent_preview，URL 参数不再决定来源）。
残留已知限制（记录）：launch_source 仍是客户端自报，真实验证需设备/账号级身份区分——属 Phase 0 真实部署事项，非 demo 可解决。
最终验证：150 测试全绿，ruff 干净，评估门槛 PASS。

最终验证：137 测试全绿，ruff 干净，评估门槛 PASS，四个孩子全部 OK，API 实测闭环（start→interaction→doudou/request→player 页面→资产 200）。
