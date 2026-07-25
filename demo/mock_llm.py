"""Deterministic mock LLM provider — runs the full demo loop offline.

Implements the LLMProvider protocol, so the loop exercises the REAL
components (extractor contract, planner frontier check, decision trace).
Swapping to Claude is a one-line change (ADR-010 provider abstraction).

Extraction: Chinese keyword → capability heuristics (mechanics, not quality).
Planning: centrality + interest-label overlap ranking (the rule-based
baseline of ADR-003 §5 — the thing the real LLM must beat).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime.llm.base import LLMRequest, LLMResponse

# Keywords are deliberately distinctive per capability — collisions would
# make the offline evaluation baseline meaningless (false-positive discipline).
CAP_KEYWORDS = {
    "pattern_recognition": ["规律", "排好", "红黄", "排序"],
    "verbal_explanation": ["解释", "因为"],
    "persistence": ["重新", "终于", "再试", "坚持"],
    "storytelling": ["故事"],
    "imaginative_play": ["假装", "角色", "玩偶"],
    "numeracy_sense": ["数数", "数到", "几个", "多少"],
    "observation": ["观察", "注意到"],
    "emotion_regulation": ["没有哭", "不哭"],
    "social_negotiation": ["轮流", "商量"],
    "curiosity": ["为什么", "问了"],
    "focused_attention": ["二十分钟", "蹲着", "专注"],
}


class MockLLMProvider:
    model = "mock-deterministic-v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "Growth Planner" in request.system:
            content = self._plan(request.user)
        else:
            content = self._extract(request.user)
        return LLMResponse(content=content, model=self.model)

    def _extract(self, user: str) -> str:
        payload = json.loads(user)
        text = payload["observation"]
        known = sorted(t["id"] for t in payload["known_targets"])  # deterministic
        signals = []
        sentences = [s for s in text.replace("。", "。").split("。") if s]
        for cap_id in known:
            cap = cap_id.split(".")[-1]
            for kw in CAP_KEYWORDS.get(cap, []):
                if kw in text:
                    quote = next((s for s in sentences if kw in s), kw)
                    signals.append(
                        {
                            "target_type": "capability" if cap_id.startswith("capability.") else "topic",
                            "target_id": cap_id,
                            "signal_strength": 0.7,
                            "confidence": 0.7,
                            "quote": quote,
                        }
                    )
                    break
        return json.dumps({"signals": signals}, ensure_ascii=False)

    def _plan(self, user: str) -> str:
        payload = json.loads(user)
        frontier = payload["frontier"]
        interests = payload["child_state"].get("interests", {})
        caps = payload.get("capabilities", {})
        # Growth memory: a refuted/inconclusive arc on a topic pushes the
        # baseline toward a different strategy (ADR-012).
        verdict_penalty = {"refuted": 1.0, "inconclusive": 0.4, "confirmed": 0.3}
        penalties: dict[str, float] = {}
        for arc in payload.get("growth_memory", {}).get("closed_arcs", []):
            tid = arc.get("topic_id")
            if tid:
                penalties[tid] = max(
                    penalties.get(tid, 0.0), verdict_penalty.get(arc.get("verdict"), 0.0))
        # interest label words that might appear in English topic names
        interest_words = set()
        for label, w in interests.items():
            if w >= 0.6:
                interest_words.update(label.split("."))

        def score(c):
            name = (c.get("name") or "").lower()
            overlap = sum(1 for w in interest_words if w in name)
            # capability-gap bonus: high development_priority × low current
            # score — different children, different rankings (ADR-004 §3).
            gap_bonus = sum(
                prio * (1.0 - caps.get(cap, {}).get("score", 0.3))
                for cap, prio in c.get("development_priorities", {}).items()
            )
            return (
                c.get("centrality", 0.0) + 0.5 * overlap + gap_bonus
                - penalties.get(c["topic_id"], 0.0)
            )

        ranked = sorted(frontier, key=score, reverse=True)[:5]
        candidates = [
            {
                "topic_id": c["topic_id"],
                "rank": i + 1,
                "capability_targets": c.get("capability_targets", []),
                "rationale": (
                    f"rule baseline: centrality={c.get('centrality', 0):.2f}, "
                    f"interest overlap, capability-gap bonus"
                ),
            }
            for i, c in enumerate(ranked)
        ]
        selected = candidates[0]["topic_id"] if candidates else None
        return json.dumps(
            {
                "candidates": candidates,
                "selected_topic_id": selected,
                "rationale": "Mock rule baseline: centrality + interest overlap + capability-gap bonus within frontier.",
            },
            ensure_ascii=False,
        )
