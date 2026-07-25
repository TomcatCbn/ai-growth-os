"""Growth Planner (ADR-003): LLM ranks WITHIN the code-computed frontier.

Contract: schemas/growth-plan.schema.json. Post-condition verified in code:
selected_topic_id ∈ frontier_snapshot — otherwise hard failure.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..contracts import validate
from ..llm.base import LLMRequest
from ..llm.prompts import PLANNER as PLANNER_PROMPT_VERSION
from ..llm.prompts import load_prompt
from ..trace.trace import TrackedProvider

TRIGGERS = ("evidence_submitted", "mission_stalled", "parent_request", "cold_start")

SYSTEM = load_prompt(PLANNER_PROMPT_VERSION)

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
        trigger: str = "evidence_submitted",
        capabilities: dict | None = None,
        family_goals: list[dict] | None = None,
    ) -> tuple[dict, str]:
        """Returns (plan, trace_id). Raises FrontierViolation on illegal pick,
        ContractViolation if the completed plan breaches the contract."""
        if trigger not in TRIGGERS:
            raise ValueError(f"unknown plan trigger: {trigger}")
        user = json.dumps(
            {
                "child_state": child_state,
                "capabilities": capabilities or {},
                "frontier": frontier,
                "recent_evidence": recent_evidence[-10:],
                "growth_memory": growth_memory or {},
                "family_goals": family_goals or [],
            },
            ensure_ascii=False,
        )
        resp, trace_id = self._llm.complete(
            LLMRequest(system=SYSTEM, user=user, response_schema=RESPONSE_SCHEMA),
            child_id=child_id,
            context={"frontier_size": len(frontier),
                     "prompt_version": PLANNER_PROMPT_VERSION},
        )
        plan = json.loads(resp.content)

        frontier_ids = {c["topic_id"] for c in frontier}
        selected = plan.get("selected_topic_id")
        if selected not in frontier_ids:
            raise FrontierViolation(f"Planner selected {selected} outside frontier")
        plan["plan_id"] = f"plan_{uuid.uuid4().hex[:10]}"
        plan["child_id"] = child_id
        plan["trigger"] = trigger
        plan["frontier_snapshot"] = sorted(frontier_ids)
        plan["decision_trace_id"] = trace_id
        plan["created_at"] = datetime.now(UTC).isoformat()
        validate("growth-plan", plan)
        return plan, trace_id
