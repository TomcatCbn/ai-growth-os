"""Contract tests — schemas are the source of truth; violations hard-fail."""

from __future__ import annotations

import pytest

from runtime.contracts import ContractViolation, validate, validate_signals
from runtime.mission.manager import MissionManager
from runtime.planner.planner import FrontierViolation, GrowthPlanner
from runtime.llm.base import LLMRequest, LLMResponse
from runtime.events.store import EventStore
from runtime.trace.trace import TrackedProvider
import json


def _valid_plan() -> dict:
    return {
        "plan_id": "plan_1",
        "child_id": "child_1",
        "trigger": "cold_start",
        "frontier_snapshot": ["mt_a"],
        "candidates": [{"topic_id": "mt_a", "rank": 1, "rationale": "r"}],
        "selected_topic_id": "mt_a",
        "rationale": "r",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _valid_arc() -> dict:
    chapter = {
        "chapter_id": "ch_1",
        "index": 1,
        "title": "t",
        "narration": "n",
        "real_world_task": "t",
        "return_prompt": "p",
        "observation_checklist": ["o1"],
        "difficulty": 1,
        "status": "pending",
    }
    return {
        "arc_id": "arc_1",
        "child_id": "child_1",
        "status": "draft",
        "primary_goal": {"topic_id": "mt_a"},
        "growth_hypothesis": {"statement": "s", "key_signal": "k"},
        "chapters": [chapter, dict(chapter, chapter_id="ch_2", index=2)],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_valid_plan_passes():
    assert validate("growth-plan", _valid_plan()) is not None


def test_plan_missing_fields_fails():
    plan = _valid_plan()
    del plan["plan_id"]
    with pytest.raises(ContractViolation):
        validate("growth-plan", plan)


def test_plan_bad_trigger_fails():
    with pytest.raises(ContractViolation):
        validate("growth-plan", _valid_plan() | {"trigger": "because_i_felt_like_it"})


def test_valid_arc_passes():
    assert validate("mission-arc", _valid_arc()) is not None


def test_arc_missing_child_id_fails():
    arc = _valid_arc()
    del arc["child_id"]
    with pytest.raises(ContractViolation):
        validate("mission-arc", arc)


def test_signals_validated():
    good = [{
        "target_type": "topic", "target_id": "mt_a",
        "signal_strength": 0.7, "confidence": 0.7, "quote": "q",
    }]
    assert validate_signals(good) == good
    bad = [dict(good[0], signal_strength=1.5)]
    with pytest.raises(ContractViolation):
        validate_signals(bad)


class _FixedProvider:
    model = "test-fixed"

    def __init__(self, content: str):
        self._content = content

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content=self._content, model=self.model)


def _planner_with(content: str) -> GrowthPlanner:
    store = EventStore()
    return GrowthPlanner(TrackedProvider(_FixedProvider(content), store, component="test"))


def test_planner_output_satisfies_contract():
    body = json.dumps({
        "candidates": [{"topic_id": "mt_a", "rank": 1, "rationale": "r"}],
        "selected_topic_id": "mt_a",
        "rationale": "r",
    })
    plan, _ = _planner_with(body).plan(
        child_id="c1", child_state={}, frontier=[{"topic_id": "mt_a"}],
        recent_evidence=[], trigger="cold_start")
    validate("growth-plan", plan)
    assert plan["plan_id"] and plan["child_id"] == "c1"
    assert plan["trigger"] == "cold_start" and plan["created_at"]


def test_planner_rejects_unknown_trigger():
    with pytest.raises(ValueError):
        _planner_with("{}").plan(
            child_id="c1", child_state={}, frontier=[{"topic_id": "mt_a"}],
            recent_evidence=[], trigger="nope")


def test_planner_frontier_violation():
    body = json.dumps({
        "candidates": [], "selected_topic_id": "mt_evil", "rationale": "r",
    })
    with pytest.raises(FrontierViolation):
        _planner_with(body).plan(
            child_id="c1", child_state={}, frontier=[{"topic_id": "mt_a"}],
            recent_evidence=[])


def test_manager_activate_fills_and_validates():
    arc = _valid_arc()
    del arc["arc_id"], arc["created_at"]
    activated = MissionManager().activate(arc)
    assert activated["arc_id"].startswith("arc_")
    assert activated["created_at"]
    validate("mission-arc", activated)


def test_manager_rejects_contract_breach():
    arc = _valid_arc()
    del arc["growth_hypothesis"]
    with pytest.raises(ContractViolation):
        MissionManager().activate(arc)
