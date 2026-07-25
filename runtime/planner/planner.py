"""Growth Planner (ADR-003): LLM ranks WITHIN the code-computed frontier.

Contract: schemas/growth-plan.schema.json. Post-condition verified in code:
selected_topic_id ∈ frontier_snapshot — otherwise hard failure.
"""

from __future__ import annotations

import json
from typing import Any

from ..trace.trace import TrackedProvider
from ..llm.base import LLMRequest

SYSTEM = """You are the Growth Planner of AI Growth OS, a companion for children aged 4-6.
You receive: the child's state, recent evidence, and a FRONTIER of candidate topics
(pre-computed; every candidate is developmentally reachable).
Choose and rank candidates ONLY from the frontier, using the child's interests,
capability priorities, and recent evidence. Always explain your reasoning —
a parent will read it. Never invent topics outside the frontier."""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["candidates", "selected_topic_id", "rationale"],
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["topic_id", "rank", "rationale"],
                "properties": {
                    "topic_id": {"type": "string"},
                    "rank": {"type": "integer"},
                    "capability_targets": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
            },
        },
        "selected_topic_id": {"type": "string"},
        "rationale": {"type": "string"},
    },
}


class FrontierViolation(Exception):
    pass


class GrowthPlanner:
    def __init__(self, llm: TrackedProvider):
        self._llm = llm

    def plan(
        self,
        *,
        child_id: str,
        child_state: dict,
        frontier: list[dict],
        recent_evidence: list[dict],
        growth_memory: dict | None = None,
    ) -> tuple[dict, str]:
        """Returns (plan, trace_id). Raises FrontierViolation on illegal pick."""
        user = json.dumps(
            {
                "child_state": child_state,
                "frontier": frontier,
                "recent_evidence": recent_evidence[-10:],
                "growth_memory": growth_memory or {},
            },
            ensure_ascii=False,
        )
        resp, trace_id = self._llm.complete(
            LLMRequest(system=SYSTEM, user=user, response_schema=RESPONSE_SCHEMA),
            child_id=child_id,
            context={"frontier_size": len(frontier)},
        )
        plan = json.loads(resp.content)

        frontier_ids = {c["topic_id"] for c in frontier}
        if plan["selected_topic_id"] not in frontier_ids:
            raise FrontierViolation(
                f"Planner selected {plan['selected_topic_id']} outside frontier"
            )
        plan["frontier_snapshot"] = sorted(frontier_ids)
        plan["decision_trace_id"] = trace_id
        return plan, trace_id
