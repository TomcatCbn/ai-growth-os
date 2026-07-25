# Capability Charter (能力本体宪章) v0.1

Status: DRAFT for expert adjudication (ADR-004 §2).
Humans legislate philosophy and boundaries; LLM generates candidates from the
topic set; experts adjudicate (accept / reject / merge) against this charter.
All adjudications are recorded in git.

## Legislation (the rules that outlive any single capability)

1. **A capability is an observable pattern of behavior, not a curriculum
   area.** "Pattern recognition" qualifies; "math" does not.
2. **One capability = one coherent measurement story.** If two candidate
   capabilities would be evidenced by the same observation 90% of the time,
   they are one capability (merge).
3. **Granularity test:** a parent must be able to answer "did I see this
   today?" after one activity. Too coarse ("cognition") fails; too fine
   ("sorts by color specifically") fails — that's a behavior, not a
   capability.
4. **Capabilities are age-band-annotated, not age-locked.** The same
   capability (persistence) looks different at 4 vs 6; the *definition* is
   stable, the *typical behaviors* and `development_priority` vary by band.
5. **Soft-trait capabilities carry a reliability warning.** Persistence,
   curiosity etc. are only evidenced through concrete behavior; the direct
   evidence channel is capped at 0.5 strength (ADR-004 §4).
6. **Every capability belongs to exactly one domain** (its home), though
   topics map to capabilities many-to-many.

## Domain 1: Cognitive (认知)

| id | 名称 | Definition | 4-6岁典型表现 | Boundary (什么不算) |
|---|---|---|---|---|
| capability.pattern_recognition | 规律识别 | Detects, extends, and creates regularities | 发现红黄红黄规律并预测下一个 | 背诵口诀不算，必须迁移到新情境 |
| capability.classification | 分类归纳 | Groups by attributes, invents own criteria | 按自创标准给玩具分类 | 按成人指令分类不算 |
| capability.causal_reasoning | 因果推理 | Links events, predicts outcomes | "因为没浇水所以花蔫了" | 背下来的常识不算 |
| capability.observation | 观察力 | Notices details, differences, changes | 发现两幅图的不同之处 | 扫一眼的"看到"不算 |
| capability.numeracy_sense | 数感 | Quantity intuition beyond rote counting | 一眼看出3个和5个谁多 | 机械数数到100不算 |
| capability.spatial_reasoning | 空间认知 | Mental rotation, maps, assembly | 拼图时预判哪块放哪 | 反复试错拼对不算 |

## Domain 2: Language (语言)

| id | 名称 | Definition | 典型表现 | Boundary |
|---|---|---|---|---|
| capability.storytelling | 叙事表达 | Constructs narratives with structure | 讲故事有开头结尾 | 复述听过的故事打折扣 |
| capability.verbal_explanation | 解释说明 | Explains own thinking and reasons | "我先找角因为这样快" | 描述动作 ≠ 解释理由 |
| capability.vocabulary_use | 词汇运用 | Uses new/precise words appropriately | 正确使用新学词汇 | 会背不会用不算 |
| capability.listening_comprehension | 倾听理解 | Follows multi-step spoken input | 听懂三步指令并执行 | 单步指令不算 |
| capability.dialogue_turn_taking | 对话轮替 | Sustains reciprocal conversation | 一问一答持续多个来回 | 单方面输出不算 |

## Domain 3: Social-Emotional (社会情感)

| id | 名称 | Definition | 典型表现 | Boundary |
|---|---|---|---|---|
| capability.emotion_regulation | 情绪调节 | Recovers from frustration, names feelings | 积木倒了不哭，说"我再试试" | 成人安抚后平静不算 |
| capability.empathy | 共情理解 | Reads and responds to others' feelings | 发现同伴难过并安慰 | 礼貌用语不算 |
| capability.social_negotiation | 社交协商 | Resolves conflict with words/proposals | "我们轮流玩好不好" | 找大人裁决不算 |
| capability.self_confidence | 自我效能 | Willingness to attempt new/hard things | 主动尝试没玩过的材料 | 熟悉领域的自信不算 |
| capability.cooperation | 合作参与 | Contributes to joint goals | 分工搭一座城堡 | 各玩各的平行游戏不算 |

## Domain 4: Creativity (创造力)

| id | 名称 | Definition | 典型表现 | Boundary |
|---|---|---|---|---|
| capability.imaginative_play | 想象游戏 | Creates and sustains pretend scenarios | 给积木赋予角色和情节 | 模仿动画片情节打折扣 |
| capability.divergent_ideas | 发散联想 | Generates multiple/unusual uses | 纸杯的十种玩法 | 一种答案不算 |
| capability.artistic_expression | 艺术表现 | Expresses ideas through art media | 画画讲故事、自编曲调 | 填色书不算 |
| capability.creative_combination | 创意组合 | Combines things in novel ways | 把两种玩具合成新玩法 | 成人示范后模仿不算 |

## Domain 5: Executive Function (执行功能)

| id | 名称 | Definition | 典型表现 | Boundary |
|---|---|---|---|---|
| capability.persistence | 坚持性 | Sustains effort through difficulty/failure | 倒了四次继续搭 | 喜欢的事上的投入需区分兴趣驱动 |
| capability.focused_attention | 专注力 | Maintains attention on non-preferred tasks | 完成需要耐心的任务 | 看电视不算（被动注意） |
| capability.planning | 计划性 | Sequences steps before acting | "我先搭底座再搭上面" | 成人给步骤不算 |
| capability.impulse_control | 冲动控制 | Waits, inhibits, follows turn rules | 游戏中等待轮到自己 | 被成人按住不算 |
| capability.working_memory | 工作记忆 | Holds and uses info over short spans | 记住游戏规则三条 | 单条规则不算 |

## Domain 6: Physical Development (身体发展)

| id | 名称 | Definition | 典型表现 | Boundary |
|---|---|---|---|---|
| capability.fine_motor | 精细动作 | Precise hand control | 串珠、使用剪刀 | 大动作代替不算 |
| capability.gross_motor | 大肌肉运动 | Whole-body coordination | 单脚跳、攀爬 | — |
| capability.hand_eye_coordination | 手眼协调 | Guides movement by vision | 接球、描线 | — |
| capability.body_control_rhythm | 身体节奏 | Moves with rhythm and balance | 随音乐打拍、走平衡木 | — |

## Adjudication workflow

1. LLM reads the 426-topic artifact + this charter → proposes:
   new candidates, merge proposals, gap report ("topics with no home").
2. Expert reviews each proposal: ACCEPT / REJECT / MERGE(target) with a
   one-line reason, committed to git.
3. Output: `world-model/capability-taxonomy.yaml` (the canonical list,
   versioned). Then 4-dim mapping annotation begins (ADR-004 §3).

## Open questions for adjudicators

- Is `capability.numeracy_sense` too curriculum-flavored for a 4-6 product
  that says "not a tutoring app"? (Recommendation: keep — it's about
  quantity intuition in play, not arithmetic instruction.)
- Should `capability.creative_combination` merge into `divergent_ideas`?
  (Recommendation: keep separate — combination is observable in
  construction play where divergent naming is not.)
